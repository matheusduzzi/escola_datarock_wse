"""Compara duas rodadas de preço e diz o que mudou, com a mesma regra do nó "Comparar com a anterior".

Uso, de dentro da pasta da aula:

    python comparar.py ../historico/rodada-2026-11-05.csv ../historico/rodada-2026-11-06.csv

A regra: para cada livro que está nas duas rodadas, avisa quando o preço muda ou quando a
disponibilidade muda. Livro que só está numa das rodadas não entra no aviso, mas aparece na conta
do fim, para você saber que ele existe.

Sai com 0 sempre que conseguiu ler as duas rodadas; sai com 2 quando um arquivo não é uma rodada.
"""
import csv
import sys
from pathlib import Path

COLUNAS = ['rodada', 'url', 'titulo', 'preco', 'disponivel']


class NaoERodada(Exception):
    pass


def ler_rodada(caminho):
    """Lê uma rodada em CSV, como o monitor grava: uma linha por livro, tudo como texto."""
    try:
        with open(caminho, encoding='utf-8', newline='') as f:
            leitor = csv.DictReader(f)
            if leitor.fieldnames is None or any(c not in leitor.fieldnames for c in COLUNAS):
                raise NaoERodada(f'{caminho}: precisa das colunas {", ".join(COLUNAS)}')
            return [dict(linha) for linha in leitor]
    except (OSError, UnicodeDecodeError) as e:
        raise NaoERodada(f'{caminho}: {e}') from e


def mudou_preco(antes, depois):
    try:
        return float(antes) != float(depois)
    except ValueError:
        return antes != depois


def comparar(antes, hoje, entradas_e_saidas=False):
    """Lista o que mudou de `antes` para `hoje`, na ordem da rodada de hoje.

    Com entradas_e_saidas=True, também lista o livro que entrou (só hoje) e o que saiu (só antes).
    """
    antes_por_url = {linha['url']: linha for linha in antes}
    urls_de_hoje = {linha['url'] for linha in hoje}
    mudancas = []
    for livro in hoje:
        velho = antes_por_url.get(livro['url'])
        if velho is None:
            if entradas_e_saidas:
                mudancas.append({'url': livro['url'], 'titulo': livro['titulo'], 'tipo': 'entrou',
                                 'antes': '', 'depois': livro['disponivel']})
            continue
        if mudou_preco(velho['preco'], livro['preco']):
            mudancas.append({'url': livro['url'], 'titulo': livro['titulo'], 'tipo': 'preco',
                             'antes': velho['preco'], 'depois': livro['preco']})
        if velho['disponivel'] != livro['disponivel']:
            mudancas.append({'url': livro['url'], 'titulo': livro['titulo'], 'tipo': 'disponibilidade',
                             'antes': velho['disponivel'], 'depois': livro['disponivel']})
    if entradas_e_saidas:
        for velho in antes:
            if velho['url'] not in urls_de_hoje:
                mudancas.append({'url': velho['url'], 'titulo': velho['titulo'], 'tipo': 'saiu',
                                 'antes': velho['disponivel'], 'depois': ''})
    return mudancas


def frase(m):
    if m['tipo'] == 'preco':
        rumo = 'caiu' if float(m['depois']) < float(m['antes']) else 'subiu'
        return f'{m["titulo"]}: o preço {rumo} de £{m["antes"]} para £{m["depois"]}'
    if m['tipo'] == 'entrou':
        return f'{m["titulo"]}: entrou na página'
    if m['tipo'] == 'saiu':
        return f'{m["titulo"]}: saiu da página'
    return f'{m["titulo"]}: {"voltou ao estoque" if m["depois"] == "sim" else "ficou sem estoque"}'


def main(args):
    if len(args) != 2:
        print('uso: python comparar.py RODADA_ANTERIOR.csv RODADA_DE_HOJE.csv')
        return 2
    try:
        antes, hoje = ler_rodada(args[0]), ler_rodada(args[1])
    except NaoERodada as e:
        print(f'não é uma rodada: {e}')
        return 2
    mudancas = comparar(antes, hoje)
    print(f'rodada anterior: {Path(args[0]).name} ({len(antes)} livros); de hoje: {Path(args[1]).name} ({len(hoje)} livros)')
    if mudancas:
        print(f'{len(mudancas)} mudança(s):')
        for m in mudancas:
            print(f'  {frase(m)}')
    else:
        print('nada mudou: o monitor não avisa')
    so_antes = {l['url'] for l in antes} - {l['url'] for l in hoje}
    so_hoje = {l['url'] for l in hoje} - {l['url'] for l in antes}
    print(f'livros só na anterior: {len(so_antes)}; só na de hoje: {len(so_hoje)} (essa regra não avisa)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
