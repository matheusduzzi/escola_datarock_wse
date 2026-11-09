"""Crawler de partida: título, preço e estoque das páginas de lista da loja de treino.

É o ponto de onde o curso sai. Sem argumento, lê as páginas salvas em ../paginas/books/
(sem internet). Com --ao-vivo, baixa as duas primeiras páginas de books.toscrape.com,
com 1 segundo entre os pedidos.

    python partida.py
    python partida.py --ao-vivo
"""
import argparse
import csv
import pathlib
import sys
import time

from bs4 import BeautifulSoup

AQUI = pathlib.Path(__file__).resolve().parent
PAGINAS = AQUI.parent / 'paginas' / 'books'
SALVAS = ['index.html', 'page-2.html']
AO_VIVO = ['https://books.toscrape.com/', 'https://books.toscrape.com/catalogue/page-2.html']
NOTAS = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}


def extrair(html):
    """Lista de livros de uma página de lista."""
    sopa = BeautifulSoup(html, 'lxml')
    livros = []
    for card in sopa.select('article.product_pod'):
        link = card.select_one('h3 a')
        preco = card.select_one('p.price_color').get_text(strip=True)
        nota = [c for c in card.select_one('p.star-rating')['class'] if c in NOTAS]
        livros.append({
            'titulo': link['title'],
            'url': link['href'].replace('catalogue/', ''),
            'preco': float(preco.replace('£', '')),
            'disponivel': 'In stock' in card.select_one('p.availability').get_text(),
            'nota': NOTAS[nota[0]],
        })
    return livros


def paginas_salvas():
    # O servidor não manda o charset; a página é UTF-8. Ler os bytes evita o "Â£".
    return [(PAGINAS / nome).read_bytes().decode('utf-8') for nome in SALVAS]


def paginas_ao_vivo():
    import requests
    cabecalho = {'User-Agent': 'curso-web-scraping-em-escala (estudo)'}
    textos = []
    for url in AO_VIVO:
        r = requests.get(url, headers=cabecalho, timeout=20)
        r.raise_for_status()
        textos.append(r.content.decode('utf-8'))
        time.sleep(1)
    return textos


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ao-vivo', action='store_true', help='baixa do site em vez de ler as páginas salvas')
    p.add_argument('--csv', default='', help='grava os livros nesse arquivo CSV')
    args = p.parse_args()
    livros = [l for html in (paginas_ao_vivo() if args.ao_vivo else paginas_salvas()) for l in extrair(html)]
    print(f'{len(livros)} livros; primeiro: {livros[0]["titulo"]} por £{livros[0]["preco"]:.2f}')
    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(livros[0]))
            w.writeheader()
            w.writerows(livros)
        print('gravado em', args.csv)
    return 0 if livros else 1


if __name__ == '__main__':
    sys.exit(main())
