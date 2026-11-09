"""Compara o alerta que o n8n montou com o que as regras de saúde dizem sobre a mesma página.

Uso, de dentro da pasta da aula:

    python conferir_alerta.py quebras/preco-por-javascript.html saida/alerta-1.json
    python conferir_alerta.py ../paginas/books/index.html nenhum

ALERTA.json é a saída do nó "Montar o alerta de quebra", copiada na visão JSON (uma lista com um item,
ou o item sozinho). Quando o If não foi pelo verdadeiro e não houve alerta, passe "nenhum".

Com --anterior RODADA.csv, ele também aplica a regra do exercício: preço diferente da rodada anterior em
mais da metade dos livros comparados.

Compara a regra e o campo de cada problema, não o texto. Sai com 0 e "0 erro(s)" quando bate, com 1
quando não bate e com 2 quando um arquivo não abre.
"""
import json
import sys
from pathlib import Path

from checar_pagina import checar, listas_da_pagina
from comparar import ler_rodada

LIMITE_MUDOU_DEMAIS = 0.5


def esperados(pagina, anterior=None):
    linhas, problemas = checar(listas_da_pagina(Path(pagina).read_text(encoding='utf-8')))
    if anterior and not problemas:
        antes = {l['url']: l for l in ler_rodada(anterior)}
        comparados = [l for l in linhas if l['url'] in antes]
        mudados = sum(1 for l in comparados if float(antes[l['url']]['preco']) != float(l['preco']))
        if comparados and mudados / len(comparados) > LIMITE_MUDOU_DEMAIS:
            problemas.append({'regra': 'mudou_demais'})
    return problemas


def chave(p):
    return (p.get('regra'), p.get('campo'))


def ler_alerta(caminho):
    if caminho == 'nenhum':
        return None
    dado = json.loads(Path(caminho).read_text(encoding='utf-8'))
    item = dado[0] if isinstance(dado, list) and dado else dado
    item = item.get('json', item) if isinstance(item, dict) else item
    if not isinstance(item, dict) or not isinstance(item.get('problemas'), list):
        raise ValueError('não tem a lista "problemas": é a saída do nó "Montar o alerta de quebra"?')
    return item


def main(args):
    anterior = None
    if '--anterior' in args:
        i = args.index('--anterior')
        anterior = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
        if not anterior:
            print('uso: --anterior RODADA.csv')
            return 2
    if len(args) != 2:
        print('uso: python conferir_alerta.py PAGINA.html ALERTA.json|nenhum [--anterior RODADA.csv]')
        return 2
    try:
        regra = esperados(args[0], anterior)
        alerta = ler_alerta(args[1])
    except (OSError, ValueError, KeyError) as e:
        print(f'não abri um dos arquivos: {e}')
        return 2
    erros = []
    if alerta is None:
        if regra:
            erros.append(('sem_alerta', 'a página quebrou, e não houve alerta: ' + ', '.join(r for r, _ in map(chave, regra))))
    else:
        if not regra:
            erros.append(('alerta_sem_quebra', 'a página está boa, e saiu alerta: a rodada boa deixou de ser gravada'))
        no_alerta = [chave(p) for p in alerta['problemas']]
        for k in sorted({chave(p) for p in regra} - set(no_alerta), key=str):
            erros.append(('faltando', f'{k[0]}' + (f' ({k[1]})' if k[1] else '')))
        for k in sorted(set(no_alerta) - {chave(p) for p in regra}, key=str):
            erros.append(('a_mais', f'{k[0]}' + (f' ({k[1]})' if k[1] else '')))
    print(f'problemas pela regra: {len(regra)}; no alerta: {"nenhum alerta" if alerta is None else len(alerta["problemas"])}')
    print(f'{len(erros)} erro(s)')
    for tipo, texto in erros:
        print(f'  {tipo:<17} {texto}')
    return 0 if not erros else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
