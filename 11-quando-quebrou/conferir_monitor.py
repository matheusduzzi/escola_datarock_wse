"""Lê um fluxo exportado do n8n e diz se ele é um monitor: agenda, memória, comparação e aviso só quando muda.

Uso, de dentro da pasta da aula:

    python conferir_monitor.py monitor.json

Não abre o n8n e não acessa a internet. Olha o arquivo:
- um gatilho agendado leva até a raspagem, e o fuso do fluxo está escrito;
- a rodada anterior é lida de um arquivo e só depois trocada pela de hoje;
- a rodada do dia fica guardada num arquivo com a data no nome;
- um nó Code compara a rodada de hoje com a anterior;
- o aviso só sai pela saída verdadeira de um If.

Sai com 0 e "monitor pronto" quando tudo está no lugar, com 1 quando falta algo e com 2 quando o
arquivo não é um fluxo do n8n.
"""
import json
import sys
from pathlib import Path

FUSO = 'America/Sao_Paulo'
BASE = 'n8n-nodes-base.'


def ler_fluxo(caminho):
    try:
        dado = json.loads(Path(caminho).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(str(e)) from e
    if not isinstance(dado, dict) or not isinstance(dado.get('nodes'), list) or not isinstance(dado.get('connections'), dict):
        raise ValueError('não tem "nodes" e "connections"')
    return dado


def saidas(fluxo, nome):
    """Lista de saídas do nó; cada saída é a lista de nós ligados a ela."""
    main = fluxo['connections'].get(nome, {}).get('main', [])
    return [[c['node'] for c in (saida or [])] for saida in main]


def depois_de(fluxo, nome):
    """Todos os nós que vêm depois de `nome`, por qualquer saída."""
    vistos, fila = set(), [nome]
    while fila:
        for saida in saidas(fluxo, fila.pop()):
            for n in saida:
                if n not in vistos:
                    vistos.add(n)
                    fila.append(n)
    return vistos


def tipo(no):
    return no.get('type', '').removeprefix(BASE)


def descrever_agenda(no):
    regras = no.get('parameters', {}).get('rule', {}).get('interval', [{}])
    partes = []
    for r in regras:
        campo = r.get('field', 'days')
        if campo == 'cronExpression':
            partes.append(f'cron {r.get("expression")}')
        elif campo == 'days':
            partes.append(f'a cada {r.get("daysInterval", 1)} dia(s), às {r.get("triggerAtHour", 0)}h{r.get("triggerAtMinute", 0):02}')
        else:
            partes.append(campo)
    return '; '.join(partes)


def conferir(fluxo):
    """Retorna a lista de (passou, texto)."""
    nos = {n['name']: n for n in fluxo['nodes'] if n.get('disabled') is not True}
    linhas = []

    def item(passou, texto_ok, texto_falta):
        linhas.append((passou, texto_ok if passou else texto_falta))

    raspa = [n for n in nos.values() if tipo(n) in ('httpRequest', 'html') or 'firecrawl' in n.get('type', '').lower()]
    primeiro_raspa = {n['name'] for n in raspa}
    agendas = [n for n in nos.values() if tipo(n) == 'scheduleTrigger' and depois_de(fluxo, n['name']) & primeiro_raspa]
    item(bool(agendas), f'gatilho agendado: {agendas[0]["name"]} ({descrever_agenda(agendas[0])})' if agendas else '',
         'gatilho agendado (Schedule Trigger) ligado à raspagem')
    manual = [n for n in nos.values() if tipo(n) == 'manualTrigger' and depois_de(fluxo, n['name']) & primeiro_raspa]
    item(bool(manual), f'gatilho manual para testar: {manual[0]["name"]}' if manual else '',
         'gatilho manual ligado à raspagem, para testar sem esperar a agenda')
    fuso = fluxo.get('settings', {}).get('timezone')
    item(fuso == FUSO, f'fuso do fluxo: {fuso}',
         f'fuso do fluxo {FUSO} em Settings > Timezone (está {fuso or "sem fuso: vale o da instância"})')

    leituras = [n for n in nos.values() if tipo(n) == 'readWriteFile' and n['parameters'].get('operation', 'read') == 'read']
    escritas = [n for n in nos.values() if tipo(n) == 'readWriteFile' and n['parameters'].get('operation') == 'write']
    leitura = leituras[0] if len(leituras) == 1 else None
    caminho = leitura['parameters'].get('fileSelector', '') if leitura else ''
    item(bool(leitura) and not caminho.startswith('='), f'lê a rodada anterior: {caminho}',
         f'um nó de arquivo que lê a rodada anterior num caminho fixo (achei {len(leituras)})')
    do_dia = [n for n in escritas if n['parameters'].get('fileName', '').startswith('=') and '{{' in n['parameters']['fileName']]
    item(bool(do_dia), f'guarda a rodada do dia com a data no nome: {do_dia[0]["parameters"]["fileName"]}' if do_dia else '',
         'um nó de arquivo que guarda a rodada do dia com a data no nome (expressão no caminho)')
    trocas = [n for n in escritas if n['parameters'].get('fileName', '').lstrip('=') == caminho and caminho]
    troca_depois = bool(leitura) and any(n['name'] in depois_de(fluxo, leitura['name']) for n in trocas)
    if trocas and not troca_depois:
        item(False, '', f'a rodada anterior é trocada ANTES de ser lida ("{trocas[0]["name"]}" vem antes de "{leitura["name"]}"): '
                        'o fluxo compara hoje com hoje')
    else:
        item(troca_depois, f'troca a rodada anterior depois de ler: {trocas[0]["name"]}' if troca_depois else '',
             'um nó de arquivo que troca a rodada anterior pela de hoje, depois da leitura e no mesmo caminho')

    depois_leitura = depois_de(fluxo, leitura['name']) if leitura else set()
    comparadores = [n for n in nos.values() if tipo(n) == 'code' and n['name'] in depois_leitura
                    and '$(' in n['parameters'].get('jsCode', '') and 'mudancas' in n['parameters'].get('jsCode', '')]
    item(bool(comparadores), f'nó Code compara a rodada de hoje com a anterior: {comparadores[0]["name"]}' if comparadores else '',
         'nó Code depois da leitura que junta a rodada de hoje e a anterior numa lista "mudancas"')

    ifs = [n for n in nos.values() if tipo(n) == 'if' and comparadores and n['name'] in depois_de(fluxo, comparadores[0]['name'])
           and 'mudancas' in json.dumps(n['parameters'])]
    aviso_ok = False
    if ifs:
        s = saidas(fluxo, ifs[0]['name']) + [[], []]
        no_falso = [n for n in s[1] if tipo(nos.get(n, {})) != 'noOp']
        aviso_ok = bool(s[0]) and not no_falso
    item(aviso_ok, f'o aviso só sai pelo verdadeiro de "{ifs[0]["name"]}"' if aviso_ok else '',
         'um If sobre "mudancas" depois da comparação, com o aviso só na saída verdadeira')
    return linhas


def main(args):
    if len(args) != 1:
        print('uso: python conferir_monitor.py FLUXO.json')
        return 2
    try:
        fluxo = ler_fluxo(args[0])
    except ValueError as e:
        print(f'não é um fluxo do n8n: {e}')
        return 2
    linhas = conferir(fluxo)
    for passou, texto in linhas:
        print(f'{"ok   " if passou else "FALTA"} {texto}')
    faltando = sum(1 for passou, _ in linhas if not passou)
    print('monitor pronto' if not faltando else f'{faltando} item(ns) faltando')
    return 0 if not faltando else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
