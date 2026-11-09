"""Crawler do catálogo da loja de treino: 50 páginas de lista, 20 livros cada, com limite de pedidos.

    python catalogo.py --limite 1 --do-zero     um pedido por vez (sequencial)
    python catalogo.py --limite 5 --do-zero     cinco ao mesmo tempo
    python catalogo.py --limite 5 --do-zero --parar-depois 20   para no meio, como se caísse
    python catalogo.py --limite 5               continua de onde parou
    python catalogo.py --falhar-uma-vez 7,23    as páginas 7 e 23 recebem um 503 de mentira no 1º pedido

O resultado fica em saida/catalogo.csv, uma linha por livro, com a URL do livro como chave.
"""
import argparse
import asyncio
import sys
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

import fila

LISTA = 'https://books.toscrape.com/catalogue/page-{}.html'
CAMPOS = ['url', 'titulo', 'preco', 'disponivel', 'pagina']


def paginas(total=50):
    return [LISTA.format(n) for n in range(1, total + 1)]


def extrair(html, url):
    sopa = BeautifulSoup(html, 'lxml')
    livros = []
    for card in sopa.select('article.product_pod'):
        link = card.select_one('h3 a')
        livros.append({
            'url': urljoin(url, link['href']),
            'titulo': link['title'],
            'preco': card.select_one('p.price_color').get_text(strip=True).replace('£', ''),
            'disponivel': 'In stock' in card.select_one('p.availability').get_text(),
            'pagina': url.rsplit('-', 1)[-1].split('.')[0],
        })
    return livros


class FalharUmaVez(httpx.AsyncBaseTransport):
    """Responde 503 no primeiro pedido das páginas escolhidas, sem ir ao site. O resto passa direto."""

    def __init__(self, numeros, por_baixo=None):
        self.faltam = {LISTA.format(n) for n in numeros}
        self.por_baixo = por_baixo or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request):
        if str(request.url) in self.faltam:
            self.faltam.discard(str(request.url))
            return httpx.Response(503, request=request)
        return await self.por_baixo.handle_async_request(request)

    async def aclose(self):
        await self.por_baixo.aclose()


def main(argv=None, transporte=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--limite', type=int, default=5, help='pedidos ao mesmo tempo, no máximo (padrão 5)')
    p.add_argument('--paginas', type=int, default=50, help='quantas páginas de lista (o catálogo tem 50)')
    p.add_argument('--saida', default='saida/catalogo.csv')
    p.add_argument('--do-zero', action='store_true', help='apaga o resultado anterior antes de começar')
    p.add_argument('--parar-depois', type=int, default=None, help='para depois de N páginas gravadas')
    p.add_argument('--falhar-uma-vez', default='', help='números de página que levam um 503 no 1º pedido')
    a = p.parse_args(argv)
    if a.limite < 1 or a.limite > 20:
        print('O limite vai de 1 a 20. Acima disso você só aperta o site sem ganhar tempo.')
        return 2
    if a.do_zero:
        fila.apagar(a.saida)
    if a.falhar_uma_vez:
        transporte = FalharUmaVez([int(n) for n in a.falhar_uma_vez.split(',')], transporte)
    saida = fila.Saida(a.saida, CAMPOS, 'url')
    lista = paginas(a.paginas)
    ja = len([u for u in lista if u in saida.feitas])
    print(f'limite {a.limite}, {len(lista)} páginas, {ja} já feitas, {len(saida.chaves)} livros no arquivo'
          + (f', {saida.cortadas} linha cortada removida' if saida.cortadas else ''))
    st = asyncio.run(fila.rodar(lista, extrair, saida, limite=a.limite, transporte=transporte,
                                parar_depois=a.parar_depois))
    print(fila.resumo(st))
    print(f'arquivo: {a.saida} com {len(saida.chaves)} livros')
    return fila.codigo_de_saida(st)


if __name__ == '__main__':
    sys.exit(main())
