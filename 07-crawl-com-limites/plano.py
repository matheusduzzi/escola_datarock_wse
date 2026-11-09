"""Simula um plano com um ou mais crawls e diz se ele traz a categoria inteira, sem nada a mais.

    python plano.py plano-mystery.json

Não chama o Firecrawl. Cada crawl do plano passa pelo simular.py, sobre o grafo da loja. O plano
fecha quando: todas as páginas da categoria aparecem, nenhuma página de fora entra e nenhuma página
é paga duas vezes (o page-1.html de uma categoria conta como o index.html dela).
"""
import json
import sys
from pathlib import Path

from loja import caminho, ler_grafo, mesma_pagina, paginas_da_categoria
from simular import FiltroInvalido, simular


def avaliar(plano, links):
    """Retorna dict com o que cada crawl visitaria e as contas do plano inteiro."""
    pasta = plano.get('categoria')
    listas, livros = paginas_da_categoria(links, pasta)
    esperadas = set(listas) | set(livros)
    crawls, visitas = [], []
    for item in plano.get('crawls', []):
        r = simular(item['crawl'], links)
        cams = [mesma_pagina(c) for c, _ in r['visitadas']]
        crawls.append({'nome': item.get('nome'), 'partida': caminho(item['crawl']['url']),
                       'limit': item['crawl'].get('limit'), 'paginas': len(cams), 'parou_por': r['parou_por']})
        visitas += cams
    unicas = set(visitas)
    return {'categoria': pasta, 'listas': listas, 'esperadas': esperadas, 'crawls': crawls,
            'creditos': len(visitas), 'faltando': sorted(esperadas - unicas),
            'fora': sorted(unicas - esperadas), 'repetidas': len(visitas) - len(unicas)}


def relatorio(a):
    linhas = [f'categoria {a["categoria"]}: {len(a["esperadas"])} páginas ({len(a["listas"])} listas e '
              f'{len(a["esperadas"]) - len(a["listas"])} livros)']
    for c in a['crawls']:
        linhas.append(f'  {c["nome"]}: partida {c["partida"]}, limit {c["limit"]}, {c["paginas"]} páginas, parou por {c["parou_por"]}')
    linhas.append(f'créditos do plano: {a["creditos"]}')
    linhas.append(f'faltando: {len(a["faltando"])}; fora da categoria: {len(a["fora"])}; pagas duas vezes: {a["repetidas"]}')
    fecha = a['crawls'] and not (a['faltando'] or a['fora'] or a['repetidas'])
    linhas.append('o plano fecha' if fecha else 'o plano ainda não fecha')
    return '\n'.join(linhas), bool(fecha)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    arquivo = argv[0] if argv else 'plano-mystery.json'
    plano = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    _, links = ler_grafo()
    try:
        a = avaliar(plano, links)
    except FiltroInvalido as erro:
        print('plano recusado:', erro)
        return 2
    texto, fecha = relatorio(a)
    print(texto)
    return 0 if fecha else 1


if __name__ == '__main__':
    sys.exit(main())
