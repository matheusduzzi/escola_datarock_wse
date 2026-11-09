"""Testes do exercício «Livro que entra e livro que sai». Rodam sem internet e sem o n8n.

    python -m pytest test_exercicio.py

Leem três arquivos que você salva nessa pasta depois de executar o monitor no n8n:
- meu-fluxo.json: o fluxo exportado;
- minha-rodada.csv: o arquivo que o monitor gravou em monitor/rodadas/;
- meu-aviso.json: a saída do nó "Montar o aviso", na visão JSON.
"""
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FLUXO = AQUI / 'meu-fluxo.json'
RODADA = AQUI / 'minha-rodada.csv'
AVISO = AQUI / 'meu-aviso.json'
ANTERIOR = AQUI / 'exercicio/anterior.csv'


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=AQUI, capture_output=True, text=True)
    return r.returncode, r.stdout


def test_fluxo_exportado_e_um_monitor():
    assert FLUXO.is_file(), 'salve o fluxo exportado como meu-fluxo.json nessa pasta'
    codigo, saida = rodar('conferir_monitor.py', FLUXO)
    assert codigo == 0, saida
    codigo, saida = rodar(AQUI.parent / 'conferir_exportacao.py', FLUXO)
    assert codigo == 0, saida


def test_rodada_gravada_e_a_pagina_1():
    assert RODADA.is_file(), 'copie o arquivo de monitor/rodadas/ como minha-rodada.csv'
    from comparar import ler_rodada
    linhas = ler_rodada(RODADA)
    assert len(linhas) == 20, f'a página 1 tem 20 livros; a rodada tem {len(linhas)}'
    assert len({l['url'] for l in linhas}) == 20, 'livro repetido na rodada'
    assert all(l['url'].startswith('https://books.toscrape.com/catalogue/') for l in linhas)
    assert all(l['disponivel'] in ('sim', 'nao') for l in linhas)
    for l in linhas:
        float(l['preco'])
    assert len({l['rodada'] for l in linhas}) == 1


def test_aviso_igual_a_regra_com_entradas_e_saidas():
    assert AVISO.is_file(), 'copie a saída do nó "Montar o aviso" para meu-aviso.json'
    codigo, saida = rodar('conferir_aviso.py', ANTERIOR, RODADA, AVISO, '--entradas-e-saidas')
    assert codigo == 0, saida
    tipos = {m['tipo'] for m in json.loads(AVISO.read_text(encoding='utf-8'))[0]['mudancas']}
    assert {'entrou', 'saiu'} <= tipos, f'o aviso precisa ter livro que entrou e livro que saiu; tipos: {sorted(tipos)}'


def test_aviso_saiu_do_fluxo_exportado():
    fluxo = json.loads(FLUXO.read_text(encoding='utf-8'))
    codigos = ' '.join(n['parameters'].get('jsCode', '') for n in fluxo['nodes'] if n['type'].endswith('.code'))
    for tipo in ("'entrou'", "'saiu'"):
        assert tipo in codigos or tipo.replace("'", '"') in codigos or tipo.replace("'", '`') in codigos, (
            f'o código dos nós do meu-fluxo.json não tem o tipo {tipo}: o aviso veio de outro fluxo?')
