"""Conta linhas e chaves repetidas de um CSV.

    python contar.py saida/catalogo.csv url
    python contar.py saida/citacoes.csv chave
"""
import collections
import csv
import sys


def contar(caminho, chave):
    with open(caminho, newline='', encoding='utf-8') as f:
        linhas = list(csv.DictReader(f))
    vezes = collections.Counter(l[chave] for l in linhas)
    repetidas = {k: n for k, n in vezes.items() if n > 1}
    return len(linhas), len(vezes), repetidas


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    total, diferentes, repetidas = contar(*argv)
    print(f'{total} linhas, {diferentes} chaves diferentes, {len(repetidas)} chaves repetidas')
    for k, n in list(repetidas.items())[:5]:
        print(f'  {n}x {k}')
    return 0 if not repetidas else 1


if __name__ == '__main__':
    sys.exit(main())
