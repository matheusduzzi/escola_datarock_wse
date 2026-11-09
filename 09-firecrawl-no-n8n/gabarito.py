"""O gabarito das páginas 1 e 2 da loja de treino, pelo crawler próprio (a mesma regra da aula 06).

    python gabarito.py
    python gabarito.py --ao-vivo

Sem --ao-vivo, lê paginas/page-1.html e paginas/page-2.html, salvas do site. Com --ao-vivo, baixa as
duas páginas agora, com 1 segundo entre os pedidos, e avisa se alguma coisa mudou em relação às salvas.
Grava gabarito-pagina-1.csv e gabarito-pagina-2.csv nessa pasta.
"""
import argparse
import csv
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

AQUI = Path(__file__).resolve().parent
PAGINAS = {
    1: 'https://books.toscrape.com/catalogue/page-1.html',
    2: 'https://books.toscrape.com/catalogue/page-2.html',
}
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
            'preco': float(preco.replace('£', '').replace('Â', '')),
            'em_estoque': 'In stock' in card.select_one('p.availability').get_text(),
        })
    return livros


def baixar(url):
    pedido = urllib.request.Request(url, headers={'User-Agent': 'curso-web-scraping-em-escala (estudo)'})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return r.read().decode('utf-8')


def ler(caminho):
    with open(caminho, newline='', encoding='utf-8') as f:
        return [{'url': l['url'], 'titulo': l['titulo'], 'preco': float(l['preco']),
                 'em_estoque': l['em_estoque'] == 'sim'} for l in csv.DictReader(f)]


def gravar(livros, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for l in livros:
            w.writerow({**l, 'preco': f'{l["preco"]:.2f}', 'em_estoque': 'sim' if l['em_estoque'] else 'não'})


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--ao-vivo', action='store_true', help='baixa as duas páginas do site agora')
    args = p.parse_args(argv)
    mudou = False
    for n, url in PAGINAS.items():
        salva = extrair((AQUI / 'paginas' / f'page-{n}.html').read_text(encoding='utf-8'), url)
        livros = salva
        if args.ao_vivo:
            if n > 1:
                time.sleep(1)
            livros = extrair(baixar(url), url)
            if livros != salva:
                mudou = True
                print(f'página {n}: o site mudou em relação à página salva; o gabarito usa o site de agora')
        gravar(livros, AQUI / f'gabarito-pagina-{n}.csv')
        estoque = sum(l['em_estoque'] for l in livros)
        print(f'página {n}: {len(livros)} livros; {estoque} em estoque; '
              f'primeiro: {livros[0]["titulo"]} por £{livros[0]["preco"]:.2f}')
    print('gravado em gabarito-pagina-1.csv e gabarito-pagina-2.csv')
    return 1 if mudou else 0


if __name__ == '__main__':
    sys.exit(main())
