"""Testes da aula: limite, espera crescente, parada, retomada e chave. Sem internet.

No lugar do site, um transporte do httpx (MockTransport) responde as páginas na hora.
"""
import asyncio
import time

import httpx
import pytest

import catalogo
import fila
import retentativa

RAPIDA = retentativa.Politica(base=0.01, teto=0.05, tentativas=4, maior_pausa=1.0, sorteio=lambda: 1.0)


def pagina_html(n, livros=20):
    cards = ''.join(
        f'<article class="product_pod"><h3><a href="livro-{n}-{i}/index.html" title="Livro {n}.{i}">x</a></h3>'
        f'<p class="price_color">£{10 + i}.00</p><p class="instock availability">In stock</p></article>'
        for i in range(livros))
    return f'<html><body>{cards}</body></html>'


class Site:
    """Responde as páginas de lista. respostas[n] = lista de status para os pedidos da página n."""

    def __init__(self, atraso=0.0, respostas=None):
        self.atraso, self.respostas = atraso, respostas or {}
        self.em_voo = self.maximo = 0
        self.pedidos = []

    async def __call__(self, request):
        n = int(str(request.url).rsplit('-', 1)[-1].split('.')[0])
        self.pedidos.append((n, time.monotonic()))
        self.em_voo += 1
        self.maximo = max(self.maximo, self.em_voo)
        try:
            await asyncio.sleep(self.atraso)
        finally:
            self.em_voo -= 1
        fila_n = self.respostas.get(n, [])
        status = fila_n.pop(0) if fila_n else 200
        if status == 'rede':
            raise httpx.ConnectError('conexão caiu', request=request)
        if isinstance(status, tuple):
            return httpx.Response(status[0], headers={'Retry-After': status[1]}, request=request)
        if status != 200:
            return httpx.Response(status, request=request)
        return httpx.Response(200, content=pagina_html(n).encode('utf-8'), request=request)


def rodar(tmp_path, site, total=20, limite=5, **kw):
    saida = fila.Saida(tmp_path / 'c.csv', catalogo.CAMPOS, 'url')
    st = asyncio.run(fila.rodar(catalogo.paginas(total), catalogo.extrair, saida, limite=limite,
                                politica=kw.pop('politica', RAPIDA), transporte=httpx.MockTransport(site),
                                avisar=lambda m: None, **kw))
    return st, saida


def linhas(tmp_path):
    return (tmp_path / 'c.csv').read_text(encoding='utf-8').splitlines()[1:]


def test_nunca_passa_do_limite(tmp_path):
    site = Site(atraso=0.02)
    st, _ = rodar(tmp_path, site, total=20, limite=3)
    assert site.maximo == 3 and st['max_em_voo'] == 3
    assert st['feitas'] == 20 and len(linhas(tmp_path)) == 400


def test_limite_1_e_sequencial_e_mais_lento(tmp_path):
    lento = Site(atraso=0.05)
    st1, _ = rodar(tmp_path / 'a', lento, total=12, limite=1)
    rapido = Site(atraso=0.05)
    st5, _ = rodar(tmp_path / 'b', rapido, total=12, limite=4)
    assert lento.maximo == 1 and rapido.maximo == 4
    assert st1['segundos'] > 2.5 * st5['segundos']


def test_503_tenta_de_novo_e_grava(tmp_path):
    site = Site(respostas={3: [503, 503]})
    st, _ = rodar(tmp_path, site, total=5)
    assert st['feitas'] == 5 and st['retentativas'] == 2 and st['pedidos'] == 7 and not st['falhas']


def test_erro_de_rede_tenta_de_novo(tmp_path):
    site = Site(respostas={2: ['rede']})
    st, _ = rodar(tmp_path, site, total=3)
    assert st['feitas'] == 3 and st['retentativas'] == 1


def test_404_nao_tenta_de_novo_e_fica_para_a_proxima(tmp_path):
    site = Site(respostas={4: [404]})
    st, saida = rodar(tmp_path, site, total=5)
    assert st['pedidos'] == 5 and st['retentativas'] == 0
    assert list(st['falhas']) == [catalogo.LISTA.format(4)]
    assert catalogo.LISTA.format(4) not in saida.feitas
    assert fila.codigo_de_saida(st, avisar=lambda m: None) == 1


def test_desiste_depois_das_tentativas(tmp_path):
    site = Site(respostas={2: [503] * 10})
    st, _ = rodar(tmp_path, site, total=3)
    assert sum(1 for n, _ in site.pedidos if n == 2) == 4
    assert 'em 4 tentativas' in st['falhas'][catalogo.LISTA.format(2)]


def test_403_para_tudo_e_mantem_o_que_foi_gravado(tmp_path):
    site = Site(atraso=0.01, respostas={8: [403]})
    st, saida = rodar(tmp_path, site, total=30, limite=2)
    assert isinstance(st['parada'], retentativa.Parar)
    assert fila.codigo_de_saida(st, avisar=lambda m: None) == 4
    assert sum(1 for n, _ in site.pedidos if n == 8) == 1
    assert len(site.pedidos) < 30 and len(linhas(tmp_path)) == 20 * len(saida.feitas)


def test_429_com_retry_after_freia_o_crawler_inteiro(tmp_path):
    site = Site(atraso=0.01, respostas={1: [(429, '1')]})
    st, _ = rodar(tmp_path, site, total=8, limite=2, politica=retentativa.Politica(
        base=0.01, teto=0.05, maior_pausa=5.0, sorteio=lambda: 1.0))
    t429 = site.pedidos[0][1]
    depois = [t for n, t in site.pedidos[2:]]
    assert st['feitas'] == 8 and st['retentativas'] == 1
    assert len([t for t in depois if t >= t429 + 0.95]) >= len(depois) - 1


def test_retry_after_longo_demais_para(tmp_path):
    site = Site(respostas={1: [(429, '600')]})
    st, _ = rodar(tmp_path, site, total=3, limite=1)
    assert isinstance(st['parada'], retentativa.Parar) and '600 s' in str(st['parada'])


def test_retomada_depois_da_interrupcao_sem_repetir(tmp_path):
    st, _ = rodar(tmp_path, Site(atraso=0.01), total=20, limite=4, parar_depois=7)
    assert isinstance(st['parada'], fila.Parou) and fila.codigo_de_saida(st, avisar=lambda m: None) == 3
    assert len(linhas(tmp_path)) == 7 * 20
    site = Site()
    st, saida = rodar(tmp_path, site, total=20, limite=4)
    assert st['ja_feitas'] == 7 and len(site.pedidos) == 13
    todas = linhas(tmp_path)
    assert len(todas) == 400 and len(set(todas)) == 400 and len(saida.feitas) == 20


def test_parar_depois_grava_exatamente_n_paginas(tmp_path):
    for _ in range(5):
        st, saida = rodar(tmp_path, Site(atraso=0.0), total=10, limite=5, parar_depois=4)
        assert st['feitas'] == 4 and len(saida.feitas) == 4 and len(linhas(tmp_path)) == 80
        fila.apagar(tmp_path / 'c.csv')


def test_queda_entre_gravar_e_marcar_nao_duplica(tmp_path, monkeypatch):
    original = fila.Saida.marcar
    chamadas = {'n': 0}

    def cai_na_terceira(self, pagina):
        chamadas['n'] += 1
        if chamadas['n'] == 3:
            raise fila.Parou('caiu depois de gravar e antes de marcar')
        original(self, pagina)

    monkeypatch.setattr(fila.Saida, 'marcar', cai_na_terceira)
    st, saida = rodar(tmp_path, Site(), total=5, limite=1)
    assert len(saida.feitas) == 2 and len(linhas(tmp_path)) == 60
    monkeypatch.setattr(fila.Saida, 'marcar', original)
    st, saida = rodar(tmp_path, Site(), total=5, limite=1)
    assert st['repetidas'] == 20 and len(linhas(tmp_path)) == 100 and len(set(linhas(tmp_path))) == 100


def test_linha_cortada_no_fim_e_removida(tmp_path):
    rodar(tmp_path, Site(), total=2, limite=1)
    arq = tmp_path / 'c.csv'
    arq.write_bytes(arq.read_bytes() + b'https://books.toscrape.com/catalogue/meio-de-li')
    saida = fila.Saida(arq, catalogo.CAMPOS, 'url')
    assert saida.cortadas == 1 and len(saida.chaves) == 40 and arq.read_bytes().endswith(b'\n')


def test_espera_cresce_com_teto_e_sorteio():
    p = retentativa.Politica(base=1, teto=30, sorteio=lambda: 1.0)
    assert [p.espera(t) for t in range(1, 8)] == [1, 2, 4, 8, 16, 30, 30]
    p.sorteio = lambda: 0.0
    assert [p.espera(t) for t in range(1, 4)] == [0.5, 1, 2]


def test_retry_after_do_503_vale_mais_que_a_conta():
    p = retentativa.Politica(base=1, teto=30, sorteio=lambda: 1.0)
    assert p.decidir(503, 1, '7') == 7 and p.decidir(503, 1) == 1
    assert p.decidir(500, 1, '7') == 1


def test_ler_retry_after():
    assert retentativa.ler_retry_after('120') == 120
    assert retentativa.ler_retry_after('Sun, 08 Nov 2026 20:00:30 GMT', agora=1794168000) == 30
    assert retentativa.ler_retry_after('amanhã') is None and retentativa.ler_retry_after(None) is None


def test_limite_fora_da_faixa_nao_roda(capsys):
    assert catalogo.main(['--limite', '50', '--saida', '/nao/existe/c.csv']) == 2
    assert 'de 1 a 20' in capsys.readouterr().out
