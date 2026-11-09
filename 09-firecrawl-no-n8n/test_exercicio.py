"""Testes do exercício: o seu fluxo de duas páginas e a saída da sua execução.

    python -m pytest test_exercicio.py

Antes de você salvar os dois arquivos nessa pasta, os quatro testes falham. Pronto quer dizer 4 passed:
  meu-fluxo.json    o fluxo exportado do seu n8n (menu do fluxo, Download)
  minha-saida.json  a saída do nó "Um item por livro", copiada da visão JSON depois da execução
"""
import json
from pathlib import Path

import conferir_fluxo as cf
import conferir_saida as cs
import gabarito as gab

AQUI = Path(__file__).resolve().parent
FLUXO = AQUI / 'meu-fluxo.json'
SAIDA = AQUI / 'minha-saida.json'


def test_os_dois_arquivos_estao_na_pasta():
    faltando = [p.name for p in (FLUXO, SAIDA) if not p.is_file()]
    assert not faltando, f'salve nessa pasta: {", ".join(faltando)}'


def test_o_fluxo_raspa_as_duas_paginas_com_credencial():
    assert FLUXO.is_file(), 'falta meu-fluxo.json'
    assert cf.main([str(FLUXO), '--paginas', '2']) == 0


def test_a_saida_bate_com_o_gabarito_das_duas_paginas():
    assert SAIDA.is_file(), 'falta minha-saida.json'
    assert cs.main([str(SAIDA), '--paginas', '2']) == 0


def test_cada_livro_diz_de_que_pagina_veio():
    assert SAIDA.is_file(), 'falta minha-saida.json'
    itens = json.loads(SAIDA.read_text(encoding='utf-8'))
    paginas = {i.get('pagina') for i in itens if isinstance(i, dict)}
    assert paginas == set(gab.PAGINAS.values())
