"""Mostra o que um site respondeu a um pedido: código, desvios, endereço final, tamanho e Retry-After.

Só lê e mostra. Quem decide o que o sinal quer dizer é você, com o quadro da aula.
Uso: python ver_resposta.py [--procurar TEXTO] URL [URL ...]   (1 segundo entre os pedidos)
Com --procurar, conta quantas vezes o TEXTO aparece no HTML que chegou.
"""
import sys
import time

import requests

CABECALHOS = {'User-Agent': 'curso-web-scraping-em-escala (aula 01; contato: seu-email)'}


def ver(url, sessao, procurar=None):
    r = sessao.get(url, headers=CABECALHOS, timeout=20)
    print(f'pedido     {url}')
    for passo in r.history:
        print(f'  desvio   {passo.status_code} -> {passo.headers.get("Location")}')
    print(f'código     {r.status_code}')
    print(f'final      {r.url}')
    print(f'tamanho    {len(r.content)} bytes')
    print(f'Retry-After {r.headers.get("Retry-After", "(não veio)")}')
    if procurar:
        print(f'achei      {r.text.count(procurar)} vez(es) {procurar}')
    print()


def main(args):
    procurar = None
    if args[:1] == ['--procurar'] and len(args) > 1:
        procurar, args = args[1], args[2:]
    urls = args
    if not urls:
        print(__doc__.strip())
        return 2
    with requests.Session() as sessao:
        for i, url in enumerate(urls):
            if i:
                time.sleep(1)
            ver(url, sessao, procurar)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
