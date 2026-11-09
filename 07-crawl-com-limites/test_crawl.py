"""Testes da aula. Sem internet, sem chave e sem o SDK: onde precisa de resposta, um cliente falso
faz o papel do Firecrawl, respondendo com as páginas que o simulador acha no grafo salvo da loja.
"""
import json
from types import SimpleNamespace as NS

import pytest

import crawl_categoria as cc
import fora_do_filtro as ff
import mapa
from loja import ler_grafo, paginas_da_categoria, tipo
from simular import FiltroInvalido, ler_filtro, simular

INFO, LINKS = ler_grafo()
TRAVEL_1 = ler_filtro('filtros/travel-1-padrao.json')
TRAVEL_2 = ler_filtro('filtros/travel-2-sem-profundidade.json')
TRAVEL_3 = ler_filtro('filtros/travel-3-profundidade-1.json')
CHAVE = {'FIRECRAWL_API_KEY': 'fc-chave-de-teste-123'}


class ClienteFalso:
    """Faz o papel do Firecrawl: o status avança de 5 em 5 páginas até terminar."""

    def __init__(self, status_final='completed', nunca_termina=False, erro=None):
        self.status_final, self.nunca_termina, self.erro = status_final, nunca_termina, erro
        self.chamadas, self.cancelado, self.pedido = 0, False, None

    def start_crawl(self, **pedido):
        if self.erro:
            raise self.erro
        self.pedido = pedido
        self.paginas = [c for c, _ in simular(pedido, LINKS)['visitadas']]
        return NS(id='trabalho-falso-1', url='https://api.firecrawl.dev/v2/crawl/trabalho-falso-1')

    def get_crawl_status(self, id_crawl):
        self.chamadas += 1
        feitas = len(self.paginas) if not self.nunca_termina else 0
        feitas = min(feitas, 5 * self.chamadas)
        fim = not self.nunca_termina and feitas == len(self.paginas)
        docs = [NS(metadata=NS(source_url='https://books.toscrape.com' + c, url=None, status_code=200))
                for c in self.paginas[:feitas]]
        return NS(status=self.status_final if fim else 'scraping', completed=feitas,
                  total=len(self.paginas), credits_used=feitas, data=docs)

    def cancel_crawl(self, id_crawl):
        self.cancelado = True
        return True

    def get_crawl_errors(self, id_crawl):
        return NS(errors=[], robots_blocked=[])


def rodar(filtro_arquivo, cliente, tmp_path, *extra):
    relogio = {'relogio': iter(range(0, 10000, 5)).__next__, 'dormir': lambda s: None}
    return cc.main([filtro_arquivo, '--saida', str(tmp_path), *extra], cliente=cliente, ambiente=CHAVE,
                   arquivo_env=tmp_path / 'nao-existe.env', **relogio)


# O grafo e o simulador.

def test_grafo_tem_a_loja_inteira():
    conta = {t: sum(tipo(c) == t for c in LINKS) for t in ('livro', 'lista', 'inicial')}
    assert conta == {'livro': 1000, 'lista': 50, 'inicial': 1}


def test_categoria_travel_tem_uma_lista_e_onze_livros():
    listas, livros = paginas_da_categoria(LINKS, 'travel_2')
    assert len(listas) == 1 and len(livros) == 11


def test_livro_tem_seis_links_para_outros_livros():
    livro = '/catalogue/its-only-the-himalayas_981/index.html'
    assert sum(tipo(d) == 'livro' for d in LINKS[livro]) == 6


def test_padrao_so_traz_a_lista():
    assert [c for c, _ in simular(TRAVEL_1['crawl'], LINKS)['visitadas']] == ['/catalogue/category/books/travel_2/index.html']


def test_sem_profundidade_vaza_para_outras_categorias():
    r = simular(TRAVEL_2['crawl'], LINKS)
    _, livros = paginas_da_categoria(LINKS, 'travel_2')
    cams = [c for c, _ in r['visitadas']]
    assert len(cams) == 31 and r['parou_por'] == 'acabaram os links dentro das regras'
    assert sum(c not in livros and tipo(c) == 'livro' for c in cams) == 19


def test_com_limit_20_o_corte_entra_antes():
    r = simular(dict(TRAVEL_2['crawl'], limit=20), LINKS)
    assert len(r['visitadas']) == 20 and r['parou_por'] == 'limit'


def test_profundidade_1_traz_so_a_categoria():
    r = simular(TRAVEL_3['crawl'], LINKS)
    listas, livros = paginas_da_categoria(LINKS, 'travel_2')
    assert {c for c, _ in r['visitadas']} == set(listas) | set(livros)
    assert r['parou_por'] == 'acabaram os links dentro das regras'


def test_partida_fora_do_include_volta_vazio():
    crawl = dict(TRAVEL_3['crawl'], include_paths=['catalogue/[^/]+_\\d+/index\\.html$'])
    assert simular(crawl, LINKS)['visitadas'] == []


def test_exclude_tira_o_endereco():
    crawl = dict(TRAVEL_3['crawl'], exclude_paths=['its-only-the-himalayas'])
    cams = [c for c, _ in simular(crawl, LINKS)['visitadas']]
    assert len(cams) == 11 and not any('himalayas' in c for c in cams)


def test_simulador_recusa_crawl_sem_limit():
    crawl = {k: v for k, v in TRAVEL_3['crawl'].items() if k != 'limit'}
    with pytest.raises(FiltroInvalido):
        simular(crawl, LINKS)


# O crawl de verdade, com o cliente falso.

def test_sem_chave_para_antes_do_pedido(tmp_path, capsys):
    cliente = ClienteFalso()
    codigo = cc.main(['filtros/travel-3-profundidade-1.json', '--saida', str(tmp_path)], cliente=cliente,
                     ambiente={}, arquivo_env=tmp_path / 'nao-existe.env')
    assert codigo == 2 and cliente.pedido is None and not list(tmp_path.glob('*.json'))


@pytest.mark.parametrize('limite', [None, 0, 10000, True, '20'])
def test_filtro_sem_limit_razoavel_para_antes_do_pedido(tmp_path, limite):
    filtro = json.loads(open('filtros/travel-3-profundidade-1.json', encoding='utf-8').read())
    if limite is None:
        del filtro['crawl']['limit']
    else:
        filtro['crawl']['limit'] = limite
    arquivo = tmp_path / 'filtro.json'
    arquivo.write_text(json.dumps(filtro), encoding='utf-8')
    cliente = ClienteFalso()
    assert rodar(str(arquivo), cliente, tmp_path) == 2 and cliente.pedido is None


def test_crawl_completo_grava_e_confere_a_categoria(tmp_path, capsys):
    cliente = ClienteFalso()
    assert rodar('filtros/travel-3-profundidade-1.json', cliente, tmp_path) == 0
    saida = capsys.readouterr().out
    assert 'scraping  5/12 páginas, 5 créditos' in saida and 'completed 12/12 páginas, 12 créditos' in saida
    assert 'da categoria travel_2: 12 de 12; fora dela: 0' in saida
    gravado = json.loads((tmp_path / 'crawl-travel-3-profundidade-1.json').read_text(encoding='utf-8'))
    assert gravado['creditos'] == 12 and len(gravado['paginas']) == 12 and gravado['status'] == 'completed'
    assert cliente.pedido['formats'] == ['markdown'] and cliente.pedido['limit'] == 20


@pytest.mark.parametrize('status', ['failed', 'cancelled'])
def test_crawl_que_nao_completa_nao_grava(tmp_path, capsys, status):
    assert rodar('filtros/travel-3-profundidade-1.json', ClienteFalso(status_final=status), tmp_path) == 1
    assert f'terminou como {status}' in capsys.readouterr().out
    assert not list(tmp_path.glob('crawl-*.json'))


def test_passou_do_tempo_cancela(tmp_path, capsys):
    cliente = ClienteFalso(nunca_termina=True)
    assert rodar('filtros/travel-3-profundidade-1.json', cliente, tmp_path, '--tempo-maximo', '30') == 1
    assert cliente.cancelado and 'cancelamento pedido (aceito)' in capsys.readouterr().out
    assert not list(tmp_path.glob('crawl-*.json'))


def test_erro_do_sdk_sai_sem_a_chave(tmp_path, capsys):
    erro = RuntimeError('401 Unauthorized: Bearer fc-chave-de-teste-123 inválida')
    assert rodar('filtros/travel-3-profundidade-1.json', ClienteFalso(erro=erro), tmp_path) == 1
    saida = capsys.readouterr().out
    assert 'fc-chave-de-teste-123' not in saida and 'Bearer ***' in saida


# O map e os endereços fora do filtro.

def test_map_normaliza_e_compara():
    urls = ['https://books.toscrape.com/catalogue/category/books/travel_2/',
            'http://books.toscrape.com/index.html',
            'https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html?x=1',
            'https://books.toscrape.com/catalogue/nao-existe_9999/index.html',
            'https://www.zyte.com/']
    comp = mapa.comparar(urls, LINKS)
    assert comp['unicos'] == 4 and comp['fora_do_site'] == ['https://www.zyte.com/']
    assert comp['achados_por_tipo']['livro'] == 1 and comp['achados_por_tipo']['categoria'] == 1
    assert comp['fora_do_grafo'] == ['/catalogue/nao-existe_9999/index.html']


def test_map_sem_chave_para(tmp_path):
    assert mapa.main(['--saida', str(tmp_path)], ambiente={}, arquivo_env=tmp_path / 'x.env') == 2


def test_fora_do_filtro_separa_os_grupos():
    crawl = TRAVEL_3['crawl']
    visitadas = {c for c, _ in simular(crawl, LINKS)['visitadas']}
    linhas = ff.separar(set(LINKS), visitadas, crawl)
    grupos = {}
    for cam, grupo, motivo in linhas:
        grupos.setdefault(grupo, []).append(cam)
    assert len(grupos['visitada']) == 12
    assert all(tipo(c) == 'livro' for c in grupos['dentro do filtro, não visitada'])
    assert len(grupos['dentro do filtro, não visitada']) == 989
    assert '/catalogue/category/books/mystery_3/index.html' in grupos['fora do filtro']
    assert len(linhas) == len(LINKS)
