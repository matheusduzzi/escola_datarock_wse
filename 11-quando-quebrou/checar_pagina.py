"""Aplica numa página salva as mesmas regras de saúde do nó "Checar a saúde da rodada".

Uso, de dentro da pasta da aula:

    python checar_pagina.py quebras/pela-metade.html
    python checar_pagina.py ../paginas/books/index.html

Tira os livros com os seletores do nó "Tirar os livros", lê preço e estoque do mesmo jeito que o nó
e diz se a rodada pode ser gravada. Não abre o n8n e não acessa a internet.

Sai com 0 quando a rodada está boa, com 1 quando quebrou e com 2 quando o arquivo não abre.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# As mesmas duas regras do checar-a-saude.js. O test_aula.py vê se os números batem.
CONTAGEM_MINIMA = 16
MAX_VAZIOS = 0.1
LOJA = 'https://books.toscrape.com/'
NOMES = {'url': 'endereço', 'titulo': 'título', 'preco': 'preço', 'disponivel': 'disponibilidade'}


def ler_preco(texto):
    m = re.search(r'£\s*(\d+\.\d{2})', texto or '')
    return m.group(1) if m else ''


def ler_estoque(texto):
    if re.search(r'out of stock', texto or '', flags=re.I):
        return 'nao'
    if re.search(r'\bin stock\b', texto or '', flags=re.I):
        return 'sim'
    return ''


def ler_endereco(href):
    h = (href or '').strip()
    if not h:
        return ''
    return h if h.startswith('http') else LOJA + re.sub(r'^\.?/', '', h)


def listas_da_pagina(html):
    """As quatro listas do nó "Tirar os livros"."""
    sopa = BeautifulSoup(html, 'lxml')
    links = sopa.select('article.product_pod h3 a')
    return {
        'titulo': [a.get('title', '') for a in links],
        'preco': [p.get_text().strip() for p in sopa.select('article.product_pod p.price_color')],
        'disponibilidade': [p.get_text().strip() for p in sopa.select('article.product_pod p.instock.availability')],
        'endereco': [a.get('href', '') for a in links],
    }


def checar(listas, rodada=''):
    """Retorna (linhas, problemas), com as mesmas regras e as mesmas frases do nó."""
    total = max(len(v) for v in listas.values())

    def pega(lista, i):
        return lista[i] if i < len(lista) else ''

    linhas = [{'rodada': rodada, 'url': ler_endereco(pega(listas['endereco'], i)),
               'titulo': pega(listas['titulo'], i).strip(), 'preco': ler_preco(pega(listas['preco'], i)),
               'disponivel': ler_estoque(pega(listas['disponibilidade'], i))} for i in range(total)]
    problemas = []
    if total < CONTAGEM_MINIMA:
        problemas.append({'regra': 'contagem', 'detalhe': f'{total} livros na página; o mínimo é {CONTAGEM_MINIMA}'})
    if total > 0 and any(len(v) != total for v in listas.values()):
        problemas.append({'regra': 'listas', 'detalhe': (
            f'as listas vieram com tamanhos diferentes: {len(listas["titulo"])} títulos, {len(listas["preco"])} preços, '
            f'{len(listas["disponibilidade"])} disponibilidades e {len(listas["endereco"])} endereços')})
    if total > 0:
        for campo, nome in NOMES.items():
            vazios = sum(1 for linha in linhas if linha[campo] == '')
            if vazios / total > MAX_VAZIOS:
                # Math.round do JavaScript arredonda .5 para cima; round() do Python, não.
                pct = int(100 * vazios / total + 0.5)
                problemas.append({'regra': 'vazios', 'campo': campo,
                                  'detalhe': f'{vazios} de {total} livros sem {nome} ({pct}%)'})
    return linhas, problemas


def main(args):
    if len(args) != 1:
        print('uso: python checar_pagina.py PAGINA.html')
        return 2
    try:
        html = Path(args[0]).read_text(encoding='utf-8')
    except OSError as e:
        print(f'não abri a página: {e}')
        return 2
    linhas, problemas = checar(listas_da_pagina(html))
    print(f'{len(linhas)} livros na página')
    print('; '.join(f'{nome}: {sum(1 for l in linhas if l[c] == "")} vazio(s)' for c, nome in NOMES.items()))
    for p in problemas:
        print(f'QUEBROU {p["detalhe"]}')
    print('rodada boa: pode gravar' if not problemas else 'a rodada não deve ser gravada')
    return 0 if not problemas else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
