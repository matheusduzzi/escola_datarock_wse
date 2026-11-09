"""Testes do exercício. Rodam sem internet e sem chave.

    python -m pytest test_aceite.py
"""
import copy
import json
from pathlib import Path

import comparar
import gabarito as gab
from aceite import aceitar_rodada

AQUI = Path(__file__).resolve().parent
URL = 'https://books.toscrape.com/catalogue/page-1.html'


def relatorio(livros=None):
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')
    livros = [dict(l) for l in certo] if livros is None else livros
    return comparar.comparar_livros(certo, livros, URL)


def rodada_de_teste():
    return json.loads((AQUI / 'teste/rodada-de-teste.json').read_text(encoding='utf-8'))['livros']


def test_sem_erros_aceita():
    assert aceitar_rodada(relatorio()) == {'aceita': True, 'motivos': [], 'avisos': []}


def test_titulo_cortado_vira_aviso_e_nao_reprova():
    livros = [dict(l) for l in gab.ler(AQUI / 'gabarito-pagina-1.csv')]
    livros[0]['titulo'] = 'A Light in the ...'
    d = aceitar_rodada(relatorio(livros))
    assert d == {'aceita': True, 'motivos': [], 'avisos': ['titulo_cortado: 1']}


def test_um_preco_errado_reprova():
    livros = [dict(l) for l in gab.ler(AQUI / 'gabarito-pagina-1.csv')]
    livros[1]['preco'] = 53.47
    d = aceitar_rodada(relatorio(livros))
    assert d['aceita'] is False
    assert d['motivos'] == ['preco_diferente: 1']


def test_vinte_itens_com_faltando_e_repetido_reprova():
    d = aceitar_rodada(relatorio(rodada_de_teste()))
    assert d['aceita'] is False
    assert d['motivos'] == ['faltando: 1', 'repetido: 1', 'tipo_errado: 1', 'titulo_diferente: 1',
                            'preco_diferente: 1', 'estoque_diferente: 1']
    assert d['avisos'] == ['titulo_cortado: 1']


def test_json_vazio_reprova_com_vinte_faltando():
    d = aceitar_rodada(relatorio([]))
    assert d['aceita'] is False
    assert d['motivos'] == ['faltando: 20']


def test_gabarito_vazio_ou_do_tamanho_errado_reprova():
    vazio = comparar.comparar_livros([], [], URL)
    assert aceitar_rodada(vazio) == {'aceita': False, 'motivos': ['gabarito: 0 livros, esperado 20'], 'avisos': []}
    certo = gab.ler(AQUI / 'gabarito-pagina-1.csv')[:19]
    curto = comparar.comparar_livros(certo, [dict(l) for l in certo], URL)
    assert aceitar_rodada(curto)['motivos'] == ['gabarito: 19 livros, esperado 20']
    assert aceitar_rodada(curto, esperados=19)['aceita'] is True


def test_tipo_desconhecido_reprova():
    rel = relatorio()
    rel['erros'].append({'url': 'x', 'campo': 'preco', 'tipo': 'moeda_diferente', 'gabarito': '', 'firecrawl': ''})
    d = aceitar_rodada(rel)
    assert d['aceita'] is False
    assert d['motivos'] == ['tipo desconhecido: moeda_diferente']


def test_nao_altera_o_relatorio():
    rel = relatorio(rodada_de_teste())
    antes = copy.deepcopy(rel)
    aceitar_rodada(rel)
    assert rel == antes
