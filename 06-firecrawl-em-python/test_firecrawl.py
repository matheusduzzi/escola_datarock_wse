"""Testes da aula: chave, chamada ao SDK, gabarito e comparador. Rodam sem internet, sem chave e sem o SDK.

    python -m pytest test_firecrawl.py

Onde precisa de resposta, o teste troca o Firecrawl por um cliente falso que responde com um documento
montado a partir do gabarito. Isso testa o script do kit, não o Firecrawl.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import comparar
import firecrawl_livros as fl
import gabarito as gab
from esquema import ESQUEMA_LIVROS

AQUI = Path(__file__).resolve().parent
URL = 'https://books.toscrape.com/catalogue/page-1.html'
CHAVE = 'fc-chave-de-teste-123'


class ClienteFalso:
    """Fica no lugar do Firecrawl: guarda cada chamada e responde o que o teste mandar."""

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.chamadas = resposta, erro, []

    def scrape(self, url, **opcoes):
        self.chamadas.append((url, opcoes))
        if self.erro:
            raise self.erro
        return self.resposta


def documento(livros, status=200, json_extra=None):
    dados = {'livros': livros} if json_extra is None else json_extra
    return SimpleNamespace(json=dados, markdown='# All products\n...',
                           metadata=SimpleNamespace(status_code=status, credits_used=None))


def gabarito_como_json():
    return [{**l, 'url': l['url']} for l in gab.ler(AQUI / 'gabarito-pagina-1.csv')]


# 1. A chave

def test_chave_vazia_para_antes_do_pedido(tmp_path):
    with pytest.raises(fl.ChaveVazia):
        fl.ler_chave({}, tmp_path / '.env')
    (tmp_path / '.env').write_text('SCRAPEDO_TOKEN=abc\nFIRECRAWL_API_KEY=\n', encoding='utf-8')
    with pytest.raises(fl.ChaveVazia):
        fl.ler_chave({}, tmp_path / '.env')


def test_chave_do_env_e_variavel_tem_preferencia(tmp_path):
    (tmp_path / '.env').write_text('FIRECRAWL_API_KEY="fc-do-arquivo"\n', encoding='utf-8')
    assert fl.ler_chave({}, tmp_path / '.env') == 'fc-do-arquivo'
    assert fl.ler_chave({'FIRECRAWL_API_KEY': 'fc-da-variavel'}, tmp_path / '.env') == 'fc-da-variavel'


def test_chave_de_outro_servico_e_recusada(tmp_path):
    with pytest.raises(fl.ChaveVazia, match='fc-'):
        fl.ler_chave({'FIRECRAWL_API_KEY': 'a1b2c3d4e5'}, tmp_path / '.env')


def test_sem_chave_o_main_sai_com_2_e_nao_chama(tmp_path, capsys):
    cliente = ClienteFalso(documento([]))
    codigo = fl.main(['--saida', str(tmp_path / 'saida')], cliente=cliente, ambiente={}, arquivo_env=tmp_path / '.env')
    assert codigo == 2
    assert cliente.chamadas == []
    assert not (tmp_path / 'saida').exists()


# 2. A chamada

def test_formatos_markdown_e_json_com_esquema():
    md, js = fl.formatos()
    assert md == 'markdown'
    assert js['type'] == 'json' and js['schema'] is ESQUEMA_LIVROS
    item = ESQUEMA_LIVROS['properties']['livros']['items']
    assert set(item['required']) == {'titulo', 'preco', 'em_estoque', 'url'}
    assert 'minItems' not in json.dumps(ESQUEMA_LIVROS)


def test_scrape_pede_pagina_nova():
    cliente = ClienteFalso(documento(gabarito_como_json()))
    r = fl.raspar(URL, cliente, CHAVE)
    (url, opcoes), = cliente.chamadas
    assert url == URL and opcoes['max_age'] == 0
    assert len(r['livros']) == 20 and r['status_code'] == 200


def test_status_diferente_de_200_falha():
    with pytest.raises(fl.ErroRodada, match='404'):
        fl.raspar(URL, ClienteFalso(documento([], status=404)), CHAVE)


@pytest.mark.parametrize('dados', [None, {}, {'livros': 'vinte livros'}, ['nada']])
def test_json_sem_a_lista_falha(dados):
    doc = documento([], json_extra=dados)
    doc.json = dados
    with pytest.raises(fl.ErroRodada, match='sem a lista'):
        fl.raspar(URL, ClienteFalso(doc), CHAVE)


def test_chave_some_da_mensagem_de_erro():
    erro = RuntimeError(f'Unauthorized: Invalid token (Authorization: Bearer {CHAVE})')
    with pytest.raises(fl.ErroRodada) as e:
        fl.raspar(URL, ClienteFalso(erro=erro), CHAVE)
    assert CHAVE not in str(e.value) and 'Bearer ***' in str(e.value)


def test_main_grava_markdown_e_json_sem_a_chave(tmp_path, capsys):
    cliente = ClienteFalso(documento(gabarito_como_json()))
    codigo = fl.main(['--saida', str(tmp_path)], cliente=cliente, ambiente={'FIRECRAWL_API_KEY': CHAVE})
    assert codigo == 0
    gravado = json.loads((tmp_path / 'firecrawl-pagina-1.json').read_text(encoding='utf-8'))
    assert gravado['url'] == URL and len(gravado['livros']) == 20
    assert (tmp_path / 'pagina-1.md').read_text(encoding='utf-8').startswith('# All products')
    tudo = capsys.readouterr().out + ''.join(p.read_text(encoding='utf-8') for p in tmp_path.iterdir())
    assert CHAVE not in tudo and '5 créditos' in tudo


# 3. O gabarito

def test_gabarito_da_pagina_salva():
    html = (AQUI / 'paginas/page-1.html').read_bytes().decode('utf-8')
    livros = gab.extrair(html, URL)
    assert len(livros) == 20 and all(l['em_estoque'] for l in livros)
    assert livros[0] == {'url': 'https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html',
                         'titulo': 'A Light in the Attic', 'preco': 51.77, 'em_estoque': True}
    assert gab.ler(AQUI / 'gabarito-pagina-1.csv') == livros


# 4. A comparação

def test_rodada_de_teste_tem_os_sete_erros():
    rodada = json.loads((AQUI / 'teste/rodada-de-teste.json').read_text(encoding='utf-8'))
    rel = comparar.comparar_livros(gab.ler(AQUI / 'gabarito-pagina-1.csv'), rodada['livros'], rodada['url'])
    assert rel['total_extraidos'] == 20 and rel['encontrados'] == 19
    assert rel['certos'] == {'titulo': 17, 'preco': 17, 'em_estoque': 18}
    assert sorted(e['tipo'] for e in rel['erros']) == sorted(
        ['titulo_cortado', 'preco_diferente', 'tipo_errado', 'estoque_diferente', 'titulo_diferente',
         'repetido', 'faltando'])


def test_gabarito_contra_ele_mesmo_nao_tem_erro():
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')
    rel = comparar.comparar_livros(certo, [dict(l) for l in certo], URL)
    assert rel['erros'] == [] and rel['certos'] == {'titulo': 20, 'preco': 20, 'em_estoque': 20}


def test_endereco_relativo_vale_o_mesmo_que_o_inteiro():
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')[:1]
    item = {**certo[0], 'url': 'a-light-in-the-attic_1000/index.html'}
    assert comparar.comparar_livros(certo, [item], URL)['erros'] == []


def test_item_sem_endereco_livro_de_fora_e_lixo():
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')[:1]
    itens = [{'titulo': 'Sem link', 'preco': 1.0, 'em_estoque': True},
             {'titulo': 'Outro', 'preco': 1.0, 'em_estoque': True, 'url': 'https://books.toscrape.com/catalogue/outro_1/index.html'},
             'texto solto']
    tipos = [e['tipo'] for e in comparar.comparar_livros(certo, itens, URL)['erros']]
    assert tipos == ['sem_url', 'a_mais', 'item_invalido', 'faltando']


def test_booleano_nao_passa_por_preco_nem_texto_por_estoque():
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')[:1]
    item = {**certo[0], 'preco': True, 'em_estoque': 'In stock'}
    erros = comparar.comparar_livros(certo, [item], URL)['erros']
    assert [(e['campo'], e['tipo']) for e in erros] == [('preco', 'tipo_errado'), ('em_estoque', 'tipo_errado')]


def test_codigos_de_saida_do_comparar(tmp_path, capsys):
    copia = tmp_path / 'rodada-de-teste.json'
    copia.write_bytes((AQUI / 'teste/rodada-de-teste.json').read_bytes())
    assert comparar.main([str(copia), '--gabarito', str(AQUI / 'gabarito-pagina-1.csv')]) == 1
    assert (tmp_path / 'erros-pagina-1.csv').read_text(encoding='utf-8').count('\n') == 8
    limpo = tmp_path / 'limpo.json'
    limpo.write_text(json.dumps({'url': URL, 'livros': gab.ler(AQUI / 'gabarito-pagina-1.csv')}), encoding='utf-8')
    assert comparar.main([str(limpo), '--gabarito', str(AQUI / 'gabarito-pagina-1.csv')]) == 0
    quebrado = tmp_path / 'quebrado.json'
    quebrado.write_text('{"url": "x"}', encoding='utf-8')
    assert comparar.main([str(quebrado)]) == 2
