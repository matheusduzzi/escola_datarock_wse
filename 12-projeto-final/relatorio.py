"""Monta o relatório de mudanças da semana a partir do histórico do monitor.

Uso, de dentro da pasta da aula:

    python relatorio.py saida/semana-aula
    python relatorio.py entrega/semana --gravar entrega/relatorio.md

A pasta é a que o semana.py grava, ou uma com o mesmo formato copiada do seu n8n: historico/ com uma
rodada por dia, custos.csv com uma linha por rodada montada e, se houver, alertas/. O relatório traz:
as rodadas da semana, só os itens que mudaram de preço ou de disponibilidade ou que saíram (com o
valor antigo e o novo), os erros do Firecrawl contra o código próprio e o custo em créditos.

Sai com 0 quando monta o relatório e com 2 quando a pasta não tem histórico.
"""
import argparse
import csv
import sys
from pathlib import Path

import monitor

TIPOS = {'preco': 'preço', 'disponibilidade': 'disponibilidade', 'sumiu': 'saiu da página'}


def ler_pasta(pasta):
    rodadas = []
    for arq in sorted((pasta / 'historico').glob('rodada-*.csv')):
        linhas = monitor.ler_csv(arq.read_text(encoding='utf-8'))
        rodadas.append((arq.stem.removeprefix('rodada-'), linhas))
    custos = []
    if (pasta / 'custos.csv').is_file():
        with (pasta / 'custos.csv').open(encoding='utf-8') as f:
            custos = list(csv.DictReader(f))
    alertas = {}
    if (pasta / 'alertas').is_dir():
        for arq in sorted((pasta / 'alertas').glob('*.txt')):
            alertas[arq.stem] = arq.read_text(encoding='utf-8').strip().splitlines()
    return rodadas, custos, alertas


def mudancas_da_semana(rodadas):
    """[(dia, anterior, mudança)] comparando cada rodada com a rodada boa anterior."""
    saida = []
    for (dia_antes, antes), (dia, hoje) in zip(rodadas, rodadas[1:]):
        for m in monitor.comparar(hoje, antes):
            saida.append((dia, dia_antes, m))
    return saida


def erros_firecrawl(rodadas):
    saida = []
    for dia, linhas in rodadas:
        for l in linhas:
            nota = l.get('firecrawl', '')
            if l['alvo'] != 'loja-pagina-2' or nota in ('', 'ok'):
                continue
            if nota == 'faltou':
                saida.append((dia, l['nome'], 'livro', 'faltou', 'estava na página'))
                continue
            for parte in nota.split('; '):
                campo, _, valor = parte.partition('=')
                saida.append((dia, l['nome'], campo, valor, l.get(campo, '')))
    return saida


def montar(pasta):
    rodadas, custos, alertas = ler_pasta(pasta)
    if not rodadas:
        return None
    por_dia = {c['rodada']: c for c in custos}
    dias = sorted({d for d, _ in rodadas} | set(por_dia) | set(alertas))
    tamanho = {d: len(l) for d, l in rodadas}
    mud = mudancas_da_semana(rodadas)
    conta = {}
    for dia, _, _ in mud:
        conta[dia] = conta.get(dia, 0) + 1
    erros = erros_firecrawl(rodadas)
    conta_erros = {}
    for e in erros:
        conta_erros[e[0]] = conta_erros.get(e[0], 0) + 1

    out = [f'# Relatório de mudanças: {dias[0]} a {dias[-1]}', '']
    out += ['## As rodadas', '', '| Dia | Situação | Itens gravados | Mudanças | Erros do Firecrawl | Créditos |',
            '|---|---|---|---|---|---|']
    for i, d in enumerate(dias):
        if d in tamanho and i == 0:
            out.append(f'| {d} | partida | {tamanho[d]} | | | |')
        elif d in tamanho:
            c = por_dia.get(d, {})
            out.append(f'| {d} | gravada | {tamanho[d]} | {conta.get(d, 0)} | {conta_erros.get(d, 0)} | {c.get("total", "?")} |')
        elif d in por_dia:
            motivo = '; '.join(x.removeprefix('- ') for x in alertas.get(d, []) if x.startswith('- ')) or 'quebrou'
            out.append(f'| {d} | não gravada: {motivo} | 0 | | | {por_dia[d]["total"]} |')
        else:
            motivo = ' '.join(alertas.get(d, ['parou']))
            out.append(f'| {d} | não gravada: {motivo} | 0 | | | 0 |')
    out += ['', '## O que mudou', '']
    if mud:
        out += ['| Dia | Comparado com | Alvo | Item | O que mudou | Antes | Depois |', '|---|---|---|---|---|---|---|']
        for dia, antes, m in mud:
            onde = monitor.NOMES_ALVO.get(m['alvo'], m['alvo'])
            out.append(f'| {dia} | {antes} | {onde} | {m["nome"]} | {TIPOS[m["tipo"]]} | {m["antes"]} | {m["depois"]} |')
    else:
        out.append('Nada mudou na semana.')
    out += ['', '## O Firecrawl contra o código próprio (página 2)', '']
    if erros:
        out += ['| Dia | Livro | Campo | Firecrawl | Código próprio |', '|---|---|---|---|---|']
        out += [f'| {d} | {n} | {c} | {f} | {g} |' for d, n, c, f, g in erros]
        out.append('')
        out.append('O histórico guardou o valor do código próprio nesses campos.')
    else:
        out.append('O Firecrawl bateu com o código próprio em todos os campos da semana.')
    total = sum(float(c['total']) for c in custos)
    sd = sum(float(c['scrapedo']) for c in custos)
    fc = sum(float(c['firecrawl']) for c in custos)
    montadas = len(custos)
    media = total / montadas if montadas else 0
    fmt = lambda x: f'{x:g}'.replace('.', ',')
    out += ['', '## O custo', '',
            f'- {montadas} rodadas montadas (as quebradas contam: os serviços já tinham sido chamados).',
            f'- scrape.do: {fmt(sd)} créditos; Firecrawl: {fmt(fc)} créditos; total: {fmt(total)} créditos.',
            f'- Média por rodada montada: {fmt(round(media, 2))} créditos; em 30 dias, perto de {fmt(round(media * 30))}.',
            '- Os números saem do cabeçalho do scrape.do e da tabela do Firecrawl. O que vale é o painel de cada serviço.']
    return '\n'.join(out) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description='Relatório de mudanças da semana.')
    p.add_argument('pasta', help='pasta com historico/ e custos.csv')
    p.add_argument('--gravar', help='arquivo .md onde gravar o relatório (sem isso, só mostra)')
    a = p.parse_args(argv)
    texto = montar(Path(a.pasta))
    if texto is None:
        print(f'{a.pasta}: não achei rodadas em historico/', file=sys.stderr)
        return 2
    if a.gravar:
        Path(a.gravar).write_text(texto, encoding='utf-8')
        print(f'gravado {a.gravar}')
    else:
        print(texto, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
