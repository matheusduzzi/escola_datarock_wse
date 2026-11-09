"""O mapa da loja de treino feito pelo nosso crawler: todas as páginas e os links de cada uma.

    python inventario.py              # resume o grafo salvo no kit (grafo-loja.json)
    python inventario.py --ao-vivo    # percorre a loja inteira de novo e grava o grafo

O --ao-vivo começa na página inicial e segue todo link interno, uma página por vez, com 1 segundo
entre os pedidos. São cerca de 1.200 pedidos: leva uns 25 minutos. Não gasta crédito nenhum.
Ele grava em grafo-loja-ao-vivo.json, para não apagar o arquivo do kit.
"""
import argparse
import datetime
import json
import sys
import time
from collections import deque
from pathlib import Path

from loja import AQUI, GRAFO, caminho, contar_tipos, endereco, ler_grafo

AGENTE = 'curso-web-scraping-em-escala (estudo)'


def baixar(url, sessao):
    r = sessao.get(url, headers={'User-Agent': AGENTE}, timeout=30)
    return r.status_code, r.text


def links_da_pagina(html, url):
    from bs4 import BeautifulSoup
    achados = []
    for a in BeautifulSoup(html, 'lxml').select('a[href]'):
        cam = caminho(a['href'], base=url)
        if cam and cam.endswith('.html') and cam not in achados:
            achados.append(cam)
    return achados


def percorrer(espera=1.0, baixar_pagina=None, mostrar=print):
    """Visita a loja a partir da página inicial, em largura. Retorna (paginas, links, status)."""
    if baixar_pagina is None:
        import requests
        sessao = requests.Session()
        baixar_pagina = lambda url: baixar(url, sessao)  # noqa: E731
    fila, vistos = deque(['/index.html']), {'/index.html'}
    paginas, links, status = [], {}, {}
    while fila:
        cam = fila.popleft()
        codigo, html = baixar_pagina(endereco(cam))
        paginas.append(cam)
        status[cam] = codigo
        links[cam] = links_da_pagina(html, endereco(cam)) if codigo == 200 else []
        for destino in links[cam]:
            if destino not in vistos:
                vistos.add(destino)
                fila.append(destino)
        if len(paginas) % 100 == 0:
            mostrar(f'  {len(paginas)} páginas, {len(fila)} na fila')
        time.sleep(espera)
    return paginas, links, status


def gravar(paginas, links, status, arquivo):
    indice = {cam: i for i, cam in enumerate(paginas)}
    corpo = {
        'site': 'https://books.toscrape.com/',
        'coletado_em': datetime.date.today().isoformat(),
        'como': 'inventario.py --ao-vivo: busca em largura a partir de /index.html, todo link interno .html',
        'status_diferente_de_200': {c: s for c, s in status.items() if s != 200},
        'paginas': paginas,
        'links': [[indice[d] for d in links[c] if d in indice] for c in paginas],
    }
    Path(arquivo).write_text(json.dumps(corpo, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def resumo(info, links):
    conta = contar_tipos(links)
    total_links = sum(len(v) for v in links.values())
    linhas = [f'grafo de {info["coletado_em"]}: {len(links)} endereços, {total_links} links',
              '  ' + ', '.join(f'{conta[t]} {t}' for t in conta if conta[t])]
    if info.get('status_diferente_de_200'):
        linhas.append(f'  status diferente de 200: {info["status_diferente_de_200"]}')
    return '\n'.join(linhas)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--ao-vivo', action='store_true')
    p.add_argument('--espera', type=float, default=1.0, help='segundos entre os pedidos (padrão 1)')
    p.add_argument('--saida', default=str(AQUI / 'grafo-loja-ao-vivo.json'))
    args = p.parse_args(argv)
    if args.ao_vivo:
        if args.espera < 0.2:
            print('espera mínima de 0,2 segundo: a loja é de treino, mas tem gente usando.')
            return 2
        paginas, links, status = percorrer(args.espera)
        gravar(paginas, links, status, args.saida)
        arquivo = args.saida
    else:
        arquivo = GRAFO
    info, links = ler_grafo(arquivo)
    print(resumo(info, links))
    if args.ao_vivo:
        print(f'gravado em {Path(arquivo).name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
