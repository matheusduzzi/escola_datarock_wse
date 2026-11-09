"""Compara, campo a campo, o JSON do Firecrawl com o gabarito do crawler próprio e lista os erros.

    python comparar.py saida/firecrawl-pagina-1.json
    python comparar.py rodada-de-teste.json

A chave é o endereço do livro. O comparador não conserta nada: ele aponta. Grava os erros num CSV
ao lado do JSON (erros-pagina-N.csv).

Códigos de saída: 0 nenhum erro; 1 tem erro na lista; 2 a entrada não dá para comparar.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import gabarito as gab

AQUI = Path(__file__).resolve().parent
CAMPOS = ['titulo', 'preco', 'em_estoque']

# Cada tipo de erro, com o que ele quer dizer.
TIPOS = {
    'faltando': 'livro do gabarito que não veio no JSON',
    'a_mais': 'livro no JSON que não está no gabarito da página',
    'repetido': 'o mesmo livro (mesmo endereço) veio mais de uma vez',
    'sem_url': 'item sem endereço; sem a chave, não dá para comparar',
    'item_invalido': 'item que não é um objeto',
    'tipo_errado': 'campo com o tipo errado (texto no lugar de número, por exemplo)',
    'titulo_cortado': 'título cortado com "...", como aparece na lista',
    'titulo_diferente': 'título diferente do gabarito, sem ser o corte da lista',
    'preco_diferente': 'preço diferente do gabarito',
    'estoque_diferente': 'estoque diferente do gabarito',
}


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def comparar_campos(certo, item):
    """Erros de um livro encontrado: lista de (campo, tipo)."""
    erros = []
    t = item.get('titulo')
    if not isinstance(t, str):
        erros.append(('titulo', 'tipo_errado'))
    elif t.strip() != certo['titulo']:
        inicio = t.strip()[:-3].rstrip()
        if t.strip().endswith('...') and inicio and certo['titulo'].startswith(inicio):
            erros.append(('titulo', 'titulo_cortado'))
        else:
            erros.append(('titulo', 'titulo_diferente'))
    p = item.get('preco')
    if not _numero(p):
        erros.append(('preco', 'tipo_errado'))
    elif round(p, 2) != round(certo['preco'], 2):
        erros.append(('preco', 'preco_diferente'))
    e = item.get('em_estoque')
    if not isinstance(e, bool):
        erros.append(('em_estoque', 'tipo_errado'))
    elif e != certo['em_estoque']:
        erros.append(('em_estoque', 'estoque_diferente'))
    return erros


def comparar_livros(gabarito, extraidos, url_da_pagina):
    """Relatório da comparação: totais, erros e quantos livros do gabarito vieram certos em cada campo."""
    por_url = {l['url']: l for l in gabarito}
    erros, vistos = [], set()
    certos = {c: 0 for c in CAMPOS}

    def anotar(url, campo, tipo, certo=None, veio=None):
        erros.append({'url': url, 'campo': campo, 'tipo': tipo,
                      'gabarito': '' if certo is None else certo, 'firecrawl': '' if veio is None else veio})

    for n, item in enumerate(extraidos, start=1):
        if not isinstance(item, dict):
            anotar(f'item {n}', '', 'item_invalido', veio=json.dumps(item, ensure_ascii=False))
            continue
        bruto = item.get('url')
        if not isinstance(bruto, str) or not bruto.strip():
            anotar(f'item {n}', 'url', 'sem_url', veio=item.get('titulo'))
            continue
        url = urljoin(url_da_pagina, bruto.strip())
        if url in vistos:
            anotar(url, 'url', 'repetido', veio=item.get('titulo'))
            continue
        vistos.add(url)
        certo = por_url.get(url)
        if certo is None:
            anotar(url, 'url', 'a_mais', veio=item.get('titulo'))
            continue
        errados = comparar_campos(certo, item)
        for campo, tipo in errados:
            anotar(url, campo, tipo, certo[campo], item.get(campo))
        for campo in CAMPOS:
            if campo not in {c for c, _ in errados}:
                certos[campo] += 1
    for url, certo in por_url.items():
        if url not in vistos:
            anotar(url, 'url', 'faltando', certo['titulo'])
    return {'total_gabarito': len(gabarito), 'total_extraidos': len(extraidos),
            'encontrados': len(vistos & set(por_url)), 'certos': certos, 'erros': erros}


def gravar_erros(relatorio, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['url', 'campo', 'tipo', 'gabarito', 'firecrawl'])
        w.writeheader()
        w.writerows(relatorio['erros'])


def curto(url):
    return url.rsplit('/catalogue/', 1)[-1].replace('/index.html', '')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('json_firecrawl')
    p.add_argument('--gabarito', default='', help='CSV do gabarito; o padrão vem do endereço do JSON')
    args = p.parse_args(argv)
    try:
        rodada = json.loads(Path(args.json_firecrawl).read_text(encoding='utf-8'))
        url_da_pagina, livros = rodada['url'], rodada['livros']
        if not isinstance(livros, list):
            raise TypeError('"livros" não é uma lista')
    except (OSError, ValueError, KeyError, TypeError) as erro:
        print(f'não dá para comparar {args.json_firecrawl}: {type(erro).__name__} {erro}')
        return 2
    from firecrawl_livros import nome_da_pagina
    nome = nome_da_pagina(url_da_pagina)
    caminho_gab = Path(args.gabarito) if args.gabarito else AQUI / f'gabarito-{nome}.csv'
    if not caminho_gab.is_file():
        print(f'falta o gabarito {caminho_gab.name}. Rode antes: python gabarito.py --ao-vivo --url {url_da_pagina}')
        return 2
    rel = comparar_livros(gab.ler(caminho_gab), livros, url_da_pagina)
    print(f'gabarito: {rel["total_gabarito"]} livros; JSON: {rel["total_extraidos"]} itens; '
          f'livros do gabarito encontrados: {rel["encontrados"]}')
    for campo in CAMPOS:
        print(f'  {campo:<11} {rel["certos"][campo]:>2} certos de {rel["total_gabarito"]}')
    print(f'{len(rel["erros"])} erros')
    for e in rel['erros']:
        detalhe = f'gabarito {e["gabarito"]!r}, firecrawl {e["firecrawl"]!r}' if e['campo'] not in ('', 'url') else repr(e['gabarito'] or e['firecrawl'])
        print(f'  {e["tipo"]:<17} {curto(e["url"])}: {detalhe}')
    destino = Path(args.json_firecrawl).with_name(f'erros-{nome}.csv')
    gravar_erros(rel, destino)
    print('erros gravados em', destino.name)
    return 1 if rel['erros'] else 0


if __name__ == '__main__':
    sys.exit(main())
