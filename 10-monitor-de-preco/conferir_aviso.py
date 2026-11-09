"""Compara o aviso que o n8n montou com o que a regra diz que mudou.

Uso, de dentro da pasta da aula:

    python conferir_aviso.py RODADA_ANTERIOR.csv RODADA_DE_HOJE.csv AVISO.json
    python conferir_aviso.py RODADA_ANTERIOR.csv RODADA_DE_HOJE.csv AVISO.json --entradas-e-saidas

RODADA_DE_HOJE.csv é o arquivo que o monitor gravou na pasta rodadas/. AVISO.json é a saída do nó
"Montar o aviso", copiada da visão JSON do n8n. Quando o If "Mudou algo?" saiu pelo falso, não há
aviso: passe a palavra nenhum no lugar do arquivo.

Sai com 0 quando o aviso traz exatamente o que mudou, com 1 quando falta, sobra ou vem errado,
e com 2 quando um arquivo não serve.
"""
import json
import sys
from pathlib import Path

from comparar import NaoERodada, comparar, ler_rodada


def chave(m):
    return (m.get('url'), m.get('tipo'), str(m.get('antes')), str(m.get('depois')))


def ler_aviso(caminho):
    if caminho == 'nenhum':
        return None
    try:
        dado = json.loads(Path(caminho).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f'{caminho}: {e}') from e
    # A visão JSON do n8n mostra uma lista de itens; o aviso é um item só.
    if isinstance(dado, list):
        if len(dado) != 1:
            raise ValueError(f'{caminho}: esperava 1 aviso, vieram {len(dado)} itens')
        dado = dado[0]
    if not isinstance(dado, dict) or not isinstance(dado.get('mudancas'), list):
        raise ValueError(f'{caminho}: não tem a lista "mudancas" do nó "Montar o aviso"')
    return dado


def conferir(antes, hoje, aviso, entradas_e_saidas=False):
    """Retorna (esperadas, erros). Cada erro é (tipo, descrição)."""
    esperadas = comparar(antes, hoje, entradas_e_saidas)
    erros = []
    if aviso is None:
        if esperadas:
            erros.append(('sem_aviso', f'{len(esperadas)} mudança(s) e nenhum aviso'))
        return esperadas, erros
    if not esperadas:
        erros.append(('aviso_sem_mudanca', 'nada mudou e mesmo assim saiu aviso: o If deveria parar'))
    no_aviso = {}
    for m in aviso['mudancas']:
        no_aviso.setdefault(chave(m), []).append(m)
    esperadas_por_chave = {chave(m): m for m in esperadas}
    for k, m in esperadas_por_chave.items():
        if k not in no_aviso:
            erros.append(('faltando', f'{m["titulo"]} ({m["tipo"]}: {m["antes"]} → {m["depois"]})'))
    for k, lista in no_aviso.items():
        m = lista[0]
        if k not in esperadas_por_chave:
            erros.append(('a_mais', f'{m.get("titulo")} ({m.get("tipo")}: {m.get("antes")} → {m.get("depois")})'))
        elif len(lista) > 1:
            erros.append(('repetido', f'{m.get("titulo")} ({m.get("tipo")}) veio {len(lista)} vezes'))
    if esperadas and not str(aviso.get('texto', '')).strip():
        erros.append(('sem_texto', 'o aviso não tem texto para mandar'))
    return esperadas, erros


def main(args):
    flags = [a for a in args if a.startswith('--')]
    args = [a for a in args if not a.startswith('--')]
    if len(args) != 3:
        print('uso: python conferir_aviso.py ANTERIOR.csv HOJE.csv AVISO.json [--entradas-e-saidas]')
        return 2
    try:
        antes, hoje = ler_rodada(args[0]), ler_rodada(args[1])
        aviso = ler_aviso(args[2])
    except (NaoERodada, ValueError) as e:
        print(f'não deu para ler: {e}')
        return 2
    esperadas, erros = conferir(antes, hoje, aviso, '--entradas-e-saidas' in flags)
    n_aviso = 0 if aviso is None else len(aviso['mudancas'])
    print(f'mudanças pela regra: {len(esperadas)}; no aviso: {n_aviso}')
    print(f'{len(erros)} erro(s)')
    for tipo, texto in erros:
        print(f'  {tipo:<18}{texto}')
    return 1 if erros else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
