"""Exercício: as 100 citações da API de treino, em paralelo, com retomada sem repetir linha.

    python citacoes.py --limite 1 --do-zero
    python citacoes.py --limite 5 --do-zero --parar-depois 4
    python citacoes.py --limite 5
    python contar.py saida/citacoes.csv chave

Você escreve duas funções: chave(texto, autor) e extrair(texto_json, url). O resto já funciona.
"""
import argparse
import asyncio
import json
import sys

import fila

API = 'https://quotes.toscrape.com/api/quotes?page={}'
CAMPOS = ['chave', 'texto', 'autor', 'tags', 'pagina']


def paginas(total=10):
    return [API.format(n) for n in range(1, total + 1)]


def chave(texto, autor):
    """Chave da citação: a mesma em qualquer execução e em qualquer página; diferente para citações diferentes.

    A API não traz id. Monte a chave com o que a citação tem.
    """
    raise NotImplementedError('é o exercício: escreva chave(texto, autor)')


def extrair(texto_json, url):
    """Uma linha por citação da resposta da API, com os campos de CAMPOS.

    chave: chave(texto, autor); texto e autor como vêm da API; tags juntas com ";"
    (["change", "world"] vira "change;world"); pagina: o número da página, como texto.
    """
    raise NotImplementedError('é o exercício: escreva extrair(texto_json, url)')


def main(argv=None, transporte=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--limite', type=int, default=5)
    p.add_argument('--saida', default='saida/citacoes.csv')
    p.add_argument('--do-zero', action='store_true')
    p.add_argument('--parar-depois', type=int, default=None)
    a = p.parse_args(argv)
    if a.limite < 1 or a.limite > 20:
        print('O limite vai de 1 a 20.')
        return 2
    if a.do_zero:
        fila.apagar(a.saida)
    saida = fila.Saida(a.saida, CAMPOS, 'chave')
    print(f'limite {a.limite}, {len(saida.feitas)} páginas já feitas, {len(saida.chaves)} citações no arquivo')
    st = asyncio.run(fila.rodar(paginas(), extrair, saida, limite=a.limite, transporte=transporte,
                                parar_depois=a.parar_depois))
    print(fila.resumo(st))
    print(f'arquivo: {a.saida} com {len(saida.chaves)} citações')
    return fila.codigo_de_saida(st)


if __name__ == '__main__':
    sys.exit(main())
