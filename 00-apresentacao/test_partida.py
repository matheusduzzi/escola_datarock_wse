"""Primeiros testes do curso. Rodam nas páginas salvas, sem internet e sem chave.

    python -m pytest
"""
import csv
import json
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
KIT = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(KIT))

import partida  # noqa: E402
import conferir_exportacao  # noqa: E402


def test_partida_le_as_duas_paginas_salvas():
    livros = [l for html in partida.paginas_salvas() for l in partida.extrair(html)]
    assert len(livros) == 40
    assert livros[0]['titulo'] == 'A Light in the Attic'
    assert livros[0]['preco'] == 51.77  # com o £ lido certo, o preço vira número


def test_rodadas_do_historico_tem_as_mesmas_colunas():
    colunas = None
    for arquivo in sorted((KIT / 'historico').glob('rodada-*.csv')):
        with open(arquivo, encoding='utf-8') as f:
            leitor = csv.DictReader(f)
            colunas = colunas or leitor.fieldnames
            assert leitor.fieldnames == colunas
            assert sum(1 for _ in leitor) > 0
    assert colunas == ['rodada', 'url', 'titulo', 'preco', 'disponivel']


def test_fluxo_de_partida_nao_tem_chave():
    assert conferir_exportacao.conferir(KIT / 'n8n' / 'monitor-partida.json') == []


def test_conferidor_acha_chave_esquecida(tmp_path):
    fluxo = {'nodes': [{'parameters': {'queryParameters': {'parameters': [
        {'name': 'token', 'value': 'abc123abc123abc123'}]}}}]}
    arquivo = tmp_path / 'fluxo.json'
    arquivo.write_text(json.dumps(fluxo))
    assert len(conferir_exportacao.conferir(arquivo)) == 1
