"""Testes do exercício. Antes de você escrever chave e extrair, eles falham. Sem internet.

As páginas da API estão salvas em paginas/citacoes/. No lugar do site, um MockTransport responde com elas.
"""
import asyncio
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

import citacoes
import contar
import fila
import retentativa

AQUI = Path(__file__).resolve().parent
SALVAS = [json.loads((AQUI / f'paginas/citacoes/page-{n}.json').read_text(encoding='utf-8')) for n in range(1, 11)]
TODAS = [q for p in SALVAS for q in p['quotes']]
RAPIDA = retentativa.Politica(base=0.01, teto=0.05, sorteio=lambda: 1.0)


def site(citacoes_do_site):
    """Responde /api/quotes?page=N com 10 citações por página, como a API de treino."""
    def responder(request):
        n = int(request.url.params['page'])
        corpo = {'has_next': n < 10, 'page': n, 'quotes': citacoes_do_site[(n - 1) * 10:n * 10]}
        return httpx.Response(200, json=corpo, request=request)
    return httpx.MockTransport(responder)


def rodar(tmp_path, transporte, parar_depois=None):
    saida = fila.Saida(tmp_path / 'citacoes.csv', citacoes.CAMPOS, 'chave')
    st = asyncio.run(fila.rodar(citacoes.paginas(), citacoes.extrair, saida, limite=1, politica=RAPIDA,
                                transporte=transporte, parar_depois=parar_depois, avisar=lambda m: None))
    return st, saida


def test_extrair_a_pagina_salva():
    linhas = citacoes.extrair(json.dumps(SALVAS[0]), citacoes.API.format(1))
    assert len(linhas) == 10 and all(list(l) == citacoes.CAMPOS for l in linhas)
    primeira = linhas[0]
    assert primeira['autor'] == 'Albert Einstein' and primeira['pagina'] == '1'
    assert primeira['tags'] == 'change;deep-thoughts;thinking;world'
    assert primeira['texto'].startswith('“The world as we have created it')
    assert primeira['chave'] == citacoes.chave(primeira['texto'], primeira['autor'])


def test_chave_e_texto_curto_e_repete_igual():
    k = citacoes.chave('“Uma frase.”', 'Alguém')
    assert isinstance(k, str) and 0 < len(k) <= 200
    assert k == citacoes.chave('“Uma frase.”', 'Alguém')


def test_chave_igual_em_outra_execucao():
    codigo = "import citacoes; print(citacoes.chave('“Uma frase.”', 'Alguém'))"
    saidas = set()
    for valor in ('1', '2', '3'):
        env = dict(os.environ, PYTHONHASHSEED=valor)
        r = subprocess.run([sys.executable, '-c', codigo], cwd=AQUI, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        saidas.add(r.stdout.strip())
    assert len(saidas) == 1, f'a chave mudou de uma execução para outra: {saidas}'


def test_mesmo_texto_com_outro_autor_muda_a_chave():
    assert citacoes.chave('“Uma frase.”', 'Alguém') != citacoes.chave('“Uma frase.”', 'Outra pessoa')


def test_chave_nao_depende_da_pagina_nem_da_posicao():
    pagina = dict(SALVAS[0], page=5, quotes=list(reversed(SALVAS[0]['quotes'])))
    antes = {l['texto']: l['chave'] for l in citacoes.extrair(json.dumps(SALVAS[0]), citacoes.API.format(1))}
    depois = {l['texto']: l['chave'] for l in citacoes.extrair(json.dumps(pagina), citacoes.API.format(5))}
    assert antes == depois


def test_cem_chaves_diferentes_nas_paginas_salvas():
    chaves = {l['chave'] for p in SALVAS for l in citacoes.extrair(json.dumps(p), citacoes.API.format(p['page']))}
    assert len(chaves) == 100


def test_interrompe_e_retoma_sem_repetir(tmp_path):
    st, _ = rodar(tmp_path, site(TODAS), parar_depois=4)
    assert isinstance(st['parada'], fila.Parou)
    st, saida = rodar(tmp_path, site(TODAS))
    assert st['ja_feitas'] == 4 and st['feitas'] == 6
    total, diferentes, repetidas = contar.contar(tmp_path / 'citacoes.csv', 'chave')
    assert (total, diferentes, repetidas) == (100, 100, {})


def test_site_mudou_a_ordem_entre_a_queda_e_a_retomada(tmp_path):
    rodar(tmp_path, site(TODAS), parar_depois=4)
    nova = {'text': '“Uma citação que entrou ontem.”', 'tags': [],
            'author': {'name': 'Alguém Novo', 'slug': 'Alguem-Novo', 'goodreads_link': ''}}
    st, saida = rodar(tmp_path, site([nova] + TODAS))
    with open(tmp_path / 'citacoes.csv', newline='', encoding='utf-8') as f:
        pares = [(l['texto'], l['autor']) for l in csv.DictReader(f)]
    assert len(pares) == len(set(pares)), 'a mesma citação entrou duas vezes'
    assert st['repetidas'] == 1 and len(pares) == 99
