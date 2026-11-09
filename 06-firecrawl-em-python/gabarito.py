"""O gabarito: título, preço e estoque da mesma página, pelo crawler próprio (a regra do partida.py).

    python gabarito.py
    python gabarito.py --ao-vivo --url https://books.toscrape.com/catalogue/page-2.html

Sem --ao-vivo, lê paginas/page-1.html, salva em 08/11/2026. O título sai do atributo title do link,
que tem o título inteiro; o endereço do livro sai inteiro, para servir de chave na comparação.
Grava gabarito-pagina-N.csv nessa pasta.
"""
import argparse
import csv
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

AQUI = Path(__file__).resolve().parent
URL_PADRAO = 'https://books.toscrape.com/catalogue/page-1.html'
SALVA = AQUI / 'paginas' / 'page-1.html'
CAMPOS = ['url', 'titulo', 'preco', 'em_estoque']


def extrair(html, url_da_pagina):
    sopa = BeautifulSoup(html, 'lxml')
    livros = []
    for card in sopa.select('article.product_pod'):
        link = card.select_one('h3 a')
        preco = card.select_one('p.price_color').get_text(strip=True)
        livros.append({
            'url': urljoin(url_da_pagina, link['href']),
            'titulo': link['title'],
            'preco': float(preco.replace('£', '')),
            'em_estoque': 'In stock' in card.select_one('p.availability').get_text(),
        })
    return livros


def baixar(url):
    import requests
    r = requests.get(url, headers={'User-Agent': 'curso-web-scraping-em-escala (estudo)'}, timeout=20)
    r.raise_for_status()
    time.sleep(1)
    return r.content.decode('utf-8')  # o servidor não manda o charset; a página é UTF-8


def gravar(livros, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for l in livros:
            w.writerow({**l, 'preco': f'{l["preco"]:.2f}', 'em_estoque': 'sim' if l['em_estoque'] else 'nao'})


def ler(caminho):
    with open(caminho, newline='', encoding='utf-8') as f:
        return [{'url': l['url'], 'titulo': l['titulo'], 'preco': float(l['preco']),
                 'em_estoque': l['em_estoque'] == 'sim'} for l in csv.DictReader(f)]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--url', default=URL_PADRAO)
    p.add_argument('--ao-vivo', action='store_true', help='baixa a página do site em vez de ler a salva')
    args = p.parse_args(argv)
    if args.ao_vivo:
        html = baixar(args.url)
    elif args.url == URL_PADRAO:
        html = SALVA.read_bytes().decode('utf-8')
    else:
        print('Só a página 1 está salva no kit. Para outra página, use --ao-vivo.')
        return 2
    livros = extrair(html, args.url)
    from firecrawl_livros import nome_da_pagina
    destino = AQUI / f'gabarito-{nome_da_pagina(args.url)}.csv'
    gravar(livros, destino)
    estoque = sum(l['em_estoque'] for l in livros)
    print(f'{len(livros)} livros; {estoque} em estoque; primeiro: {livros[0]["titulo"]} por £{livros[0]["preco"]:.2f}')
    print('gravado em', destino.name)
    return 0 if livros else 1


if __name__ == '__main__':
    sys.exit(main())
