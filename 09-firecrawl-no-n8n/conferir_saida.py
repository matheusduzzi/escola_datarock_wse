"""Compara a saída do nó "Um item por livro" com o gabarito do crawler próprio, livro a livro.

    python conferir_saida.py saida/pagina-1.json
    python conferir_saida.py saida/duas-paginas.json --paginas 2

A entrada é o JSON que o n8n mostra na saída do nó Code, na visão JSON: uma lista com um objeto por
livro (pagina, titulo, preco, em_estoque, url). A chave da comparação é o endereço do livro; endereço
relativo é resolvido a partir do campo pagina. O comparador não conserta nada: ele aponta.

Sai com 0 quando todos os livros do gabarito vieram, sem nenhum a mais, e com os três campos certos;
1 quando tem erro; 2 quando o arquivo não dá para comparar.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gabarito as gab  # noqa: E402

CAMPOS = ['titulo', 'preco', 'em_estoque']
PAGINA_1 = gab.PAGINAS[1]


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def erros_do_livro(certo, item):
    erros = []
    t = item.get('titulo')
    if not isinstance(t, str):
        erros.append(('titulo', 'tipo_errado'))
    elif t.strip() != certo['titulo']:
        erros.append(('titulo', 'titulo_cortado' if t.strip().endswith('...') else 'titulo_diferente'))
    p = item.get('preco')
    if not _numero(p):
        erros.append(('preco', 'tipo_errado'))
    elif round(p, 2) != round(certo['preco'], 2):
        erros.append(('preco', 'preco_diferente'))
    e = item.get('em_estoque')
    if not isinstance(e, bool):
        erros.append(('em_estoque', 'tipo_errado'))
    elif e != certo['em_estoque']:
        erros.append(('em_estoque', 'estoque_diferente'))
    return erros


def comparar(gabarito, itens):
    por_url = {l['url']: l for l in gabarito}
    erros, vistos = [], set()
    certos = {c: 0 for c in CAMPOS}
    for n, item in enumerate(itens, start=1):
        if isinstance(item, dict) and isinstance(item.get('json'), dict) and len(item) <= 2:
            item = item['json']  # quem copiou o item inteiro, com a chave "json"
        if not isinstance(item, dict):
            erros.append((f'item {n}', '', 'item_invalido'))
            continue
        bruto = item.get('url')
        if not isinstance(bruto, str) or not bruto.strip():
            erros.append((f'item {n}', 'url', 'sem_url'))
            continue
        pagina = item.get('pagina') if isinstance(item.get('pagina'), str) and item['pagina'].startswith('http') else PAGINA_1
        url = urljoin(pagina, bruto.strip())
        if url in vistos:
            erros.append((url, 'url', 'repetido'))
            continue
        vistos.add(url)
        certo = por_url.get(url)
        if certo is None:
            erros.append((url, 'url', 'a_mais'))
            continue
        errados = erros_do_livro(certo, item)
        erros += [(url, campo, tipo) for campo, tipo in errados]
        for campo in CAMPOS:
            if campo not in {c for c, _ in errados}:
                certos[campo] += 1
    erros += [(url, 'url', 'faltando') for url in por_url if url not in vistos]
    return {'gabarito': len(gabarito), 'itens': len(itens), 'certos': certos, 'erros': erros}


def curto(url):
    return url.rsplit('/catalogue/', 1)[-1].replace('/index.html', '')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('saida')
    ap.add_argument('--paginas', type=int, choices=[1, 2], default=1)
    args = ap.parse_args(argv)
    try:
        itens = json.loads(Path(args.saida).read_text(encoding='utf-8'))
        if not isinstance(itens, list):
            raise ValueError('o arquivo não é uma lista; copie a saída do nó "Um item por livro" na visão JSON')
    except (OSError, ValueError) as erro:
        print(f'não dá para comparar {args.saida}: {erro}')
        return 2
    gabarito = []
    for n in range(1, args.paginas + 1):
        gabarito += gab.ler(AQUI / f'gabarito-pagina-{n}.csv')
    rel = comparar(gabarito, itens)
    print(f'gabarito: {rel["gabarito"]} livros; saída do n8n: {rel["itens"]} itens')
    for campo in CAMPOS:
        print(f'  {campo:<11} {rel["certos"][campo]:>2} certos de {rel["gabarito"]}')
    print(f'{len(rel["erros"])} erros')
    for onde, campo, tipo in rel['erros']:
        print(f'  {tipo:<17} {curto(onde)}' + (f' ({campo})' if campo not in ('', 'url') else ''))
    return 1 if rel['erros'] else 0


if __name__ == '__main__':
    sys.exit(main())
