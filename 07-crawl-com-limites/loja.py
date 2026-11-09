"""O que a aula sabe da loja de treino: o tipo de cada endereço e o grafo de links salvo.

O grafo (grafo-loja.json) é o mapa da loja feito pelo nosso próprio crawler, o inventario.py:
cada página que existe e os links internos que ela tem. Ele serve de referência para o map do
Firecrawl e de terreno para o simular.py.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

AQUI = Path(__file__).resolve().parent
GRAFO = AQUI / 'grafo-loja.json'
SITE = 'https://books.toscrape.com/'
HOST = 'books.toscrape.com'

LIVRO = re.compile(r'^/catalogue/[^/]+_\d+/index\.html$')
LISTA = re.compile(r'^/catalogue/page-\d+\.html$')
CATEGORIA = re.compile(r'^/catalogue/category/')
TIPOS = ('livro', 'lista', 'categoria', 'inicial', 'outro')


def caminho(url, base=SITE):
    """O caminho do endereço, sem domínio, consulta nem âncora. Endereço de outro site: None."""
    partes = urlparse(urljoin(base, url))
    if partes.scheme not in ('http', 'https') or partes.hostname != HOST:
        return None
    return partes.path or '/'


def endereco(cam):
    return urljoin(SITE, cam)


def tipo(cam):
    if cam in ('/', '/index.html'):
        return 'inicial'
    if LIVRO.match(cam):
        return 'livro'
    if LISTA.match(cam):
        return 'lista'
    if CATEGORIA.match(cam):
        return 'categoria'
    return 'outro'


def categoria_de(cam):
    """A pasta da categoria, como 'travel_2', para endereços de categoria. Os outros: None."""
    m = re.match(r'^/catalogue/category/books/([^/]+)/', cam)
    return m.group(1) if m else None


def ler_grafo(arquivo=GRAFO):
    """Retorna (info, links): info do arquivo e um dict caminho -> lista de caminhos ligados."""
    dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    nos = dados['paginas']
    links = {cam: [nos[i] for i in dados['links'][n]] for n, cam in enumerate(nos)}
    info = {k: v for k, v in dados.items() if k not in ('paginas', 'links')}
    return info, links


def contar_tipos(caminhos):
    conta = {t: 0 for t in TIPOS}
    for cam in caminhos:
        conta[tipo(cam)] += 1
    return conta


def paginas_da_categoria(links, pasta):
    """As páginas de lista da categoria e os livros que elas mostram, pelo grafo.

    Uma página de lista da categoria é qualquer endereço dentro de /catalogue/category/books/<pasta>/,
    menos o page-1.html, que é o mesmo conteúdo do index.html com outro endereço.
    Os livros da categoria são os links de livro dessas páginas. Os 6 livros do quadro
    "Recently viewed" ficam nas páginas de livro, não nas listas, então não entram aqui.
    """
    prefixo = f'/catalogue/category/books/{pasta}/'
    listas = sorted(c for c in links if c.startswith(prefixo) and not c.endswith('/page-1.html'))
    livros = sorted({d for c in listas for d in links[c] if tipo(d) == 'livro'})
    return listas, livros


def mesma_pagina(cam):
    """O page-1.html de uma categoria é a mesma página do index.html dela, com outro endereço."""
    if CATEGORIA.match(cam) and cam.endswith('/page-1.html'):
        return cam[:-len('page-1.html')] + 'index.html'
    return cam
