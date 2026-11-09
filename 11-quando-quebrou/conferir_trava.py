"""Lê um fluxo exportado do n8n e diz se ele tem a trava de saúde antes de gravar a rodada.

Uso, de dentro da pasta da aula:

    python conferir_trava.py monitor-com-trava.json
    python conferir_trava.py meu-fluxo.json --depois-da-comparacao

Não abre o n8n e não acessa a internet. Olha o arquivo:
- um nó Code depois da raspagem monta a lista "problemas", e um If olha essa lista;
- nenhum nó que grava arquivo roda sem passar pela saída boa desse If;
- a saída de quebra não chega a nenhuma gravação, monta o alerta e termina num Stop and Error.

Com --depois-da-comparacao, procura também uma segunda trava entre a comparação e as gravações
(a regra do exercício).

Sai com 0 e "trava pronta" quando tudo está no lugar, com 1 quando falta algo e com 2 quando o
arquivo não é um fluxo do n8n.
"""
import json
import sys

from conferir_monitor import depois_de, ler_fluxo, saidas, tipo

GATILHOS = ('scheduleTrigger', 'manualTrigger')


def grava(no):
    return tipo(no) == 'readWriteFile' and no['parameters'].get('operation') == 'write'


def saida_de_quebra(no_if):
    """Índice da saída do If que quer dizer "quebrou", ou None se a condição não é sobre problemas."""
    conds = no_if['parameters'].get('conditions', {}).get('conditions', [])
    if len(conds) != 1 or 'problemas' not in str(conds[0].get('leftValue', '')):
        return None
    op = conds[0].get('operator', {}).get('operation')
    valor = conds[0].get('rightValue')
    if (op, valor) in (('gt', 0), ('notEquals', 0), ('gte', 1)):
        return 0
    if (op, valor) in (('equals', 0), ('lt', 1), ('lte', 0)):
        return 1
    return None


def alcancaveis_sem(fluxo, nos, cortado):
    """Nós que os gatilhos alcançam quando o If `cortado` não deixa passar nada."""
    vistos = set()
    fila = [n for n in nos if tipo(nos[n]) in GATILHOS]
    while fila:
        atual = fila.pop()
        if atual in vistos or atual not in nos:
            continue
        vistos.add(atual)
        if atual == cortado:
            continue
        for saida in saidas(fluxo, atual):
            fila.extend(saida)
    return vistos


def conferir_um_if(fluxo, nos, no_if, rotulo):
    linhas = []
    quebra = saida_de_quebra(no_if)
    s = saidas(fluxo, no_if['name']) + [[], []]
    lado_quebra = [n for n in s[quebra] if n in nos]
    lado_bom = [n for n in s[1 - quebra] if n in nos]
    depois_quebra = set(lado_quebra).union(*(depois_de(fluxo, n) for n in lado_quebra)) if lado_quebra else set()
    depois_bom = set(lado_bom).union(*(depois_de(fluxo, n) for n in lado_bom)) if lado_bom else set()
    gravacoes = [n for n in nos.values() if grava(n)]

    soltas = [n['name'] for n in gravacoes if n['name'] in alcancaveis_sem(fluxo, nos, no_if['name'])]
    linhas.append((not soltas, f'{rotulo}: toda gravação passa antes por "{no_if["name"]}"',
                   f'{rotulo}: grava sem passar pela trava: {", ".join(soltas)}'))
    sem_bom = [n['name'] for n in gravacoes if n['name'] not in depois_bom]
    linhas.append((bool(gravacoes) and not sem_bom, f'{rotulo}: a rodada boa segue para as gravações',
                   f'{rotulo}: a saída boa de "{no_if["name"]}" não chega a ' + (', '.join(sem_bom) or 'nenhuma gravação')))
    na_quebra = [n['name'] for n in gravacoes if n['name'] in depois_quebra]
    linhas.append((bool(lado_quebra) and not na_quebra, f'{rotulo}: a saída de quebra não grava nada e vai para "{lado_quebra[0] if lado_quebra else ""}"',
                   f'{rotulo}: a saída de quebra ' + (f'grava: {", ".join(na_quebra)}' if na_quebra else 'não leva a nenhum alerta')))
    parada = [n for n in depois_quebra if tipo(nos.get(n, {})) == 'stopAndError']
    linhas.append((bool(parada), f'{rotulo}: a execução termina com erro em "{parada[0] if parada else ""}"',
                   f'{rotulo}: um Stop and Error depois do alerta, para a execução aparecer como erro'))
    return linhas


def conferir(fluxo, depois_da_comparacao=False):
    """Retorna a lista de (passou, texto)."""
    nos = {n['name']: n for n in fluxo['nodes'] if n.get('disabled') is not True}
    linhas = []
    raspa = {n['name'] for n in nos.values() if tipo(n) in ('httpRequest', 'html') or 'firecrawl' in n.get('type', '').lower()}
    depois_raspa = set().union(*(depois_de(fluxo, n) for n in raspa)) if raspa else set()
    ifs = [n for n in nos.values() if tipo(n) == 'if' and saida_de_quebra(n) is not None]
    saude = [n for n in nos.values() if tipo(n) == 'code' and n['name'] in depois_raspa
             and 'problemas' in n['parameters'].get('jsCode', '')
             and any(i['name'] in depois_de(fluxo, n['name']) for i in ifs)]
    comparadores = [n for n in nos.values() if tipo(n) == 'code' and 'mudancas' in n['parameters'].get('jsCode', '')
                    and '$(' in n['parameters'].get('jsCode', '')]
    depois_comp = set().union(*(depois_de(fluxo, n['name']) for n in comparadores)) if comparadores else set()

    primeira = [i for i in ifs if saude and i['name'] in depois_de(fluxo, saude[0]['name']) and i['name'] not in depois_comp]
    linhas.append((bool(saude), f'nó Code monta a lista "problemas" depois da raspagem: {saude[0]["name"] if saude else ""}',
                   'nó Code depois da raspagem que monta a lista "problemas", seguido de um If sobre ela'))
    linhas.append((bool(primeira), f'If sobre "problemas" antes da comparação: {primeira[0]["name"] if primeira else ""}',
                   'um If sobre "problemas" depois da checagem e antes da comparação ({{ $json.problemas.length }} maior que 0)'))
    if primeira:
        linhas += conferir_um_if(fluxo, nos, primeira[0], 'trava da página')
    if depois_da_comparacao:
        segunda = [i for i in ifs if i['name'] in depois_comp]
        linhas.append((bool(segunda), f'If sobre "problemas" depois da comparação: {segunda[0]["name"] if segunda else ""}',
                       'um If sobre "problemas" depois de "Comparar com a anterior" e antes das gravações'))
        if segunda:
            linhas += conferir_um_if(fluxo, nos, segunda[0], 'trava da comparação')
    return linhas


def main(args):
    extra = '--depois-da-comparacao' in args
    args = [a for a in args if a != '--depois-da-comparacao']
    if len(args) != 1:
        print('uso: python conferir_trava.py FLUXO.json [--depois-da-comparacao]')
        return 2
    try:
        fluxo = ler_fluxo(args[0])
    except ValueError as e:
        print(f'não é um fluxo do n8n: {e}')
        return 2
    linhas = conferir(fluxo, extra)
    for passou, ok, falta in linhas:
        print(f'{"ok   " if passou else "FALTA"} {ok if passou else falta}')
    faltando = sum(1 for passou, _, _ in linhas if not passou)
    print('trava pronta' if not faltando else f'{faltando} item(ns) faltando')
    return 0 if not faltando else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
