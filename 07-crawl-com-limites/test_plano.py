"""Testes do exercício: o plano-mystery.json traz a categoria Mystery inteira, sem nada a mais.

Rodam pelo simulador, sobre o grafo salvo da loja: sem internet, sem chave e sem crédito.
Com o plano vazio do kit, os seis falham. Não mude os testes; mude o plano.
"""
import json
from pathlib import Path

from loja import caminho, ler_grafo, paginas_da_categoria
from plano import avaliar

AQUI = Path(__file__).resolve().parent
PLANO = AQUI / 'plano-mystery.json'
_, LINKS = ler_grafo()


def ler_plano():
    dados = json.loads(PLANO.read_text(encoding='utf-8'))
    assert dados.get('categoria') == 'mystery_3', 'o plano é da categoria mystery_3'
    assert dados.get('crawls'), 'o plano ainda não tem nenhum crawl'
    return dados


def test_cada_crawl_tem_limit_pequeno():
    plano = ler_plano()
    for item in plano['crawls']:
        limite = item['crawl'].get('limit')
        assert isinstance(limite, int) and 1 <= limite <= 50, f'{item.get("nome")}: limit {limite}'


def test_cada_crawl_parte_de_uma_lista_da_categoria():
    plano = ler_plano()
    listas, _ = paginas_da_categoria(LINKS, 'mystery_3')
    for item in plano['crawls']:
        assert caminho(item['crawl']['url']) in listas, f'{item.get("nome")}: partida fora das listas da categoria'


def test_traz_todas_as_paginas_da_categoria():
    plano = ler_plano()
    a = avaliar(plano, LINKS)
    assert len(a['esperadas']) == 34
    assert a['faltando'] == [], f'faltando {len(a["faltando"])}, por exemplo {a["faltando"][:2]}'


def test_nada_de_fora_da_categoria():
    plano = ler_plano()
    a = avaliar(plano, LINKS)
    assert a['fora'] == [], f'{len(a["fora"])} de fora, por exemplo {a["fora"][:2]}'


def test_nenhuma_pagina_paga_duas_vezes():
    plano = ler_plano()
    a = avaliar(plano, LINKS)
    assert a['repetidas'] == 0, f'{a["repetidas"]} página(s) paga(s) duas vezes'


def test_custo_igual_ao_tamanho_da_categoria():
    plano = ler_plano()
    a = avaliar(plano, LINKS)
    assert a['creditos'] == 34, f'{a["creditos"]} créditos'
