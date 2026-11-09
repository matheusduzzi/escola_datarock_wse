"""Testes do exercício. Rodam sem internet e sem chave: o scrape.do é trocado por um falso.

    python -m pytest test_escalada.py

Enquanto a função coletar não existir, eles falham. É o esperado.
"""
import pathlib
import sys

import pytest

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import escalada  # noqa: E402
import scrapedo  # noqa: E402

CAIXA = "<div class='quote'><span class='text'>Uma citação</span><small class='author'>Alguém</small></div>"
COM_CAIXAS = '<html><body>' + CAIXA * 10 + '</body></html>'
SEM_CAIXAS = (AQUI / 'paginas/quotes-js.html').read_text(encoding='utf-8')  # a /js de verdade, sem navegador


class Falso:
    """Faz o papel do scrape.do: responde por ordem e guarda cada pedido."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.pedidos = []

    def __call__(self, url, render=False, **outros):
        self.pedidos.append({'url': url, 'render': render})
        status, html, custo = self.respostas.pop(0)
        return scrapedo.Resposta(status, html, {'Scrape.do-Request-Cost': str(custo)})


def test_pagina_sem_javascript_para_no_primeiro_pedido():
    falso = Falso((200, COM_CAIXAS, 1))
    r = escalada.coletar('https://quotes.toscrape.com/', 'div.quote', chamar=falso)
    assert r == {'itens': 10, 'render': False, 'custo': 1, 'chamadas': 1}
    assert falso.pedidos == [{'url': 'https://quotes.toscrape.com/', 'render': False}]


def test_pagina_com_javascript_liga_o_render_uma_vez():
    falso = Falso((200, SEM_CAIXAS, 1), (200, COM_CAIXAS, 5))
    r = escalada.coletar('https://quotes.toscrape.com/js/', 'div.quote', chamar=falso)
    assert r == {'itens': 10, 'render': True, 'custo': 6, 'chamadas': 2}
    assert [p['render'] for p in falso.pedidos] == [False, True]


def test_seletor_errado_para_depois_do_render_sem_terceiro_pedido():
    falso = Falso((200, SEM_CAIXAS, 1), (200, SEM_CAIXAS, 5))
    with pytest.raises(escalada.SemDados):
        escalada.coletar('https://quotes.toscrape.com/js/', 'div.citacao', chamar=falso)
    assert len(falso.pedidos) == 2


@pytest.mark.parametrize('status', [401, 429, 502])
def test_erro_no_primeiro_pedido_nao_liga_o_render(status):
    falso = Falso((status, '{"Message": ["erro"]}', 0))
    with pytest.raises(scrapedo.ErroScrapeDo):
        escalada.coletar('https://quotes.toscrape.com/js/', 'div.quote', chamar=falso)
    assert len(falso.pedidos) == 1


def test_erro_no_pedido_com_render_para():
    falso = Falso((200, SEM_CAIXAS, 1), (502, '{"Message": ["erro"]}', 0))
    with pytest.raises(scrapedo.ErroScrapeDo):
        escalada.coletar('https://quotes.toscrape.com/js/', 'div.quote', chamar=falso)
    assert len(falso.pedidos) == 2


def test_minimo_maior_que_o_achado_liga_o_render():
    falso = Falso((200, '<html>' + CAIXA * 3 + '</html>', 1), (200, COM_CAIXAS, 5))
    r = escalada.coletar('https://quotes.toscrape.com/js/', 'div.quote', chamar=falso, minimo=10)
    assert r['render'] is True and r['itens'] == 10 and r['custo'] == 6
