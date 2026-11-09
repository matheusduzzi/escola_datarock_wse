"""Testes do exercício: extrair_js, o código próprio para a versão js. Sem internet e sem navegador.

Com o proprio_js.py do kit, os quatro falham. Pronto quer dizer 4 passed, sem mudar esse arquivo.
"""
import medir
import proprio
from proprio_js import extrair_js

GAB = medir.ler_gabarito()


def test_traz_as_10_citacoes_da_pagina_salva():
    assert len(extrair_js(proprio.ler_salva('js'))) == 10


def test_texto_autor_e_tags_iguais_ao_gabarito_na_ordem():
    citacoes = extrair_js(proprio.ler_salva('js'))
    assert medir.comparar(GAB, citacoes)['total_certos'] == 30
    assert [c['autor'] for c in citacoes] == [g['autor'] for g in GAB]


def test_texto_sem_as_aspas_curvas_das_pontas():
    for c in extrair_js(proprio.ler_salva('js')):
        assert c['texto'] == c['texto'].strip().strip('“”')


def test_pagina_sem_a_lista_no_script_volta_vazia_sem_erro():
    """Se o site mudar de novo e o script sumir, a função volta vazia e o medir.py mostra 0 de 10."""
    assert extrair_js(proprio.ler_salva('padrao')) == []
