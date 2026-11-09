"""Baixa quotes.toscrape.com/js/ e conta as citações de dois jeitos.

    python citacoes_js.py --modo direto       # requests, sem proxy, 0 crédito
    python citacoes_js.py --modo sem-render   # scrape.do sem navegador, 1 crédito
    python citacoes_js.py --modo render       # scrape.do com render=true, 5 créditos
    python citacoes_js.py --arquivo paginas/quotes-js.html   # a página salva, sem internet

Conta as caixas div.quote que estão no HTML recebido e as citações que estão
na lista de dados dentro do <script> da página. Sai com 0 quando acha 10 citações
de algum dos dois jeitos, com 1 quando não acha e com 2 sem chave.
"""
import argparse
import json
import pathlib
import re
import sys

import requests
from bs4 import BeautifulSoup

import scrapedo

AQUI = pathlib.Path(__file__).resolve().parent
ALVO = 'https://quotes.toscrape.com/js/'


def contar_caixas(html, seletor='div.quote'):
    return len(BeautifulSoup(html, 'html.parser').select(seletor))


def citacoes_do_script(html):
    """A lista `var data = [...]` que o JavaScript da página usa para montar as caixas."""
    m = re.search(r'var data = (\[.*?\]);\s*\n\s*for', html, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1))
    except ValueError:
        return []


def primeira_caixa(html):
    caixa = BeautifulSoup(html, 'html.parser').select_one('div.quote')
    if not caixa:
        return None
    return caixa.select_one('.text').get_text(strip=True), caixa.select_one('.author').get_text(strip=True)


def baixar(modo, chamar=scrapedo.chamar, get_direto=requests.get):
    if modo == 'direto':
        r = get_direto(ALVO, timeout=30)
        return r.status_code, r.text, 0
    r = chamar(ALVO, render=(modo == 'render'))
    if r.status != 200:
        print(f'{r.status}: {r.aviso or "resposta inesperada"}: {r.texto[:200]}')
    return r.status, r.texto, r.custo


def main(argv=None, **injetar):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modo', choices=['direto', 'sem-render', 'render'], default='direto')
    p.add_argument('--arquivo', help='ler uma página salva em vez de baixar')
    a = p.parse_args(argv)
    try:
        if a.arquivo:
            status, html, custo, modo = 200, pathlib.Path(a.arquivo).read_text(encoding='utf-8'), 0, 'arquivo'
        else:
            modo = a.modo
            if modo != 'direto':
                scrapedo.ler_chave(injetar.get('env'))
            status, html, custo = baixar(modo, **{k: v for k, v in injetar.items() if k != 'env'})
    except scrapedo.ChaveVazia as erro:
        print(erro)
        return 2
    except (scrapedo.ErroScrapeDo, requests.RequestException, OSError) as erro:
        print(f'parou: {erro}')
        return 1
    caixas = contar_caixas(html) if status == 200 else 0
    dados = citacoes_do_script(html) if status == 200 else []
    print(f'modo {modo}: status {status}, custo {custo if custo is not None else "?"}, '
          f'{len(html)} caracteres')
    print(f'  caixas div.quote no HTML: {caixas}')
    print(f'  citações na lista do script: {len(dados)}')
    primeira = primeira_caixa(html)
    if primeira:
        print(f'  primeira caixa: {primeira[0][:60]}… ({primeira[1]})')
    elif dados:
        print(f'  primeira da lista: {dados[0]["text"][:60]}… ({dados[0]["author"]["name"]})')
    return 0 if caixas == 10 or len(dados) == 10 else 1


if __name__ == '__main__':
    sys.exit(main())
