"""Confere a pasta de entrega do projeto final, item por item.

Uso, de dentro da pasta da aula:

    python conferir_projeto.py entrega

A pasta precisa ter:
    meu-fluxo.json       o fluxo exportado do seu n8n, com as credenciais escolhidas e o custo anotado
    semana/              o histórico da semana (do seu n8n ou do semana.py): historico/, custos.csv
    relatorio.md         o relatório de mudanças dessa semana
    alerta-quebra.json   a saída do nó "Montar o alerta de quebra" na quebra que você provocou no n8n
    anotacao.md          o que você anotou: painel, memória antes e depois da quebra, leitura da semana

Não abre o n8n e não acessa a internet. Refaz o relatório a partir do histórico e compara com o seu.
Sai com 0 quando tudo está no lugar, com 1 quando falta algo e com 2 quando a pasta não existe.
"""
import json
import re
import sys
from pathlib import Path

import conferir_fluxo
import monitor
import relatorio

ALVOS = set(monitor.NOMES_ALVO)
NOME_ARQ = re.compile(r'rodada-(\d{4}-\d{2}-\d{2})\.csv$')


def tabela(texto, titulo):
    """As linhas (listas de células) da tabela logo depois do subtítulo, sem o cabeçalho."""
    partes = texto.split(f'## {titulo}', 1)
    if len(partes) < 2:
        return None
    linhas = []
    for linha in partes[1].split('\n## ', 1)[0].splitlines():
        if linha.startswith('|') and not linha.startswith('|---'):
            linhas.append([c.strip() for c in linha.strip().strip('|').split('|')])
    return linhas[1:] if linhas else []


def secao_fluxo(pasta):
    arq = pasta / 'meu-fluxo.json'
    try:
        fluxo = json.loads(arq.read_text(encoding='utf-8'))
        assert isinstance(fluxo, dict) and isinstance(fluxo.get('nodes'), list)
    except (OSError, ValueError, AssertionError):
        return [(False, 'meu-fluxo.json: não achei um fluxo exportado do n8n')]
    return [(ok, f'fluxo: {t}') for ok, t in conferir_fluxo.conferir(fluxo, com_custo=True)]


def secao_historico(pasta):
    hist = pasta / 'semana' / 'historico'
    arquivos = sorted(hist.glob('rodada-*.csv')) if hist.is_dir() else []
    itens = [(len(arquivos) >= 7, f'histórico: {len(arquivos)} rodadas em semana/historico (o mínimo é 7)')]
    ruins = []
    for arq in arquivos:
        m = NOME_ARQ.search(arq.name)
        texto = arq.read_text(encoding='utf-8')
        cabecalho = texto.splitlines()[0] if texto else ''
        linhas = monitor.ler_csv(texto)
        if not m or cabecalho != ','.join(monitor.COLUNAS):
            ruins.append(f'{arq.name}: cabeçalho diferente de {",".join(monitor.COLUNAS)}')
            continue
        if any(l['rodada'] != m.group(1) for l in linhas):
            ruins.append(f'{arq.name}: tem linha de outra rodada')
        if {l['alvo'] for l in linhas} != ALVOS:
            ruins.append(f'{arq.name}: alvos {sorted({l["alvo"] for l in linhas})}')
    itens.append((bool(arquivos) and not ruins, 'histórico: uma rodada por arquivo, no mesmo formato, com os três alvos'
                  + (f' ({"; ".join(ruins)})' if ruins else '')))
    return itens


def secao_custos(pasta):
    semana = pasta / 'semana'
    rodadas, custos, _ = relatorio.ler_pasta(semana) if (semana / 'historico').is_dir() else ([], [], {})
    if not custos:
        return [(False, 'custos: não achei semana/custos.csv com uma linha por rodada')]
    itens = []
    gravadas = {d for d, _ in rodadas[1:]}
    por_dia = {c.get('rodada'): c for c in custos}
    sem_custo = sorted(gravadas - set(por_dia))
    itens.append((not sem_custo, 'custos: toda rodada gravada tem o seu custo' + (f' (faltam {", ".join(sem_custo)})' if sem_custo else '')))
    contas = []
    for c in custos:
        try:
            if abs(float(c['scrapedo']) + float(c['firecrawl']) - float(c['total'])) > 1e-9:
                contas.append(c['rodada'])
        except (KeyError, TypeError, ValueError):
            contas.append(str(c.get('rodada')))
    itens.append((not contas, 'custos: scrape.do + Firecrawl = total em cada linha' + (f' (não bate em {", ".join(contas)})' if contas else '')))
    quebradas = [c['rodada'] for c in custos if c.get('situacao') == 'quebrou']
    no_hist = [d for d in quebradas if d in {x for x, _ in rodadas}]
    itens.append((bool(quebradas) and not no_hist, 'custos: pelo menos uma rodada quebrada, com custo e fora do histórico'
                  + (f' ({", ".join(no_hist)} está no histórico)' if no_hist else '' if quebradas else ' (nenhuma)')))
    return itens


def secao_relatorio(pasta):
    arq = pasta / 'relatorio.md'
    if not arq.is_file() or not (pasta / 'semana' / 'historico').is_dir():
        return [(False, 'relatório: não achei relatorio.md e semana/historico')]
    seu = arq.read_text(encoding='utf-8')
    refeito = relatorio.montar(pasta / 'semana') or ''
    itens = []
    for titulo, nome in (('O que mudou', 'as mudanças'), ('O Firecrawl contra o código próprio (página 2)', 'os erros do Firecrawl')):
        a, b = tabela(seu, titulo), tabela(refeito, titulo)
        if a is None:
            itens.append((False, f'relatório: falta a seção "{titulo}"'))
            continue
        faltam = [l for l in b if l not in a]
        sobram = [l for l in a if l not in b]
        detalhe = ''
        if faltam:
            detalhe += f'; faltam {len(faltam)}, a primeira: {" | ".join(faltam[0])}'
        if sobram:
            detalhe += f'; sobram {len(sobram)}, a primeira: {" | ".join(sobram[0])}'
        itens.append((not faltam and not sobram, f'relatório: {nome} batem com o histórico{detalhe}'))
    custo_ok = '## O custo' in seu and 'créditos' in seu.split('## O custo', 1)[-1]
    itens.append((custo_ok, 'relatório: tem a seção do custo em créditos'))
    return itens


def secao_alerta(pasta):
    arq = pasta / 'alerta-quebra.json'
    try:
        dado = json.loads(arq.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return [(False, 'alerta: não achei alerta-quebra.json (a saída de "Montar o alerta de quebra")')]
    item = dado[0] if isinstance(dado, list) and dado else dado
    item = item.get('json', item) if isinstance(item, dict) else {}
    ok = ('quebrou' in str(item.get('assunto', '')) and isinstance(item.get('problemas'), list) and item['problemas']
          and 'Nada foi gravado' in str(item.get('texto', '')))
    return [(bool(ok), 'alerta: saída do "Montar o alerta de quebra", com assunto, problemas e "Nada foi gravado"')]


def secao_anotacao(pasta):
    arq = pasta / 'anotacao.md'
    if not arq.is_file():
        return [(False, 'anotação: não achei anotacao.md')]
    texto = arq.read_text(encoding='utf-8')
    vazios = texto.count('(preencha)')
    return [(vazios == 0, 'anotação: sem nenhum "(preencha)" sobrando' + (f' (sobram {vazios})' if vazios else ''))]


SECOES = [secao_fluxo, secao_historico, secao_custos, secao_relatorio, secao_alerta, secao_anotacao]


def conferir(pasta):
    return [i for s in SECOES for i in s(pasta)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print('uso: python conferir_projeto.py PASTA_DA_ENTREGA (a pasta precisa existir)')
        return 2
    itens = conferir(Path(argv[0]))
    for ok, texto in itens:
        print(f'{"ok   " if ok else "FALTA"} {texto}')
    faltam = sum(1 for ok, _ in itens if not ok)
    print('projeto pronto' if not faltam else f'{faltam} item(ns) faltando')
    return 0 if not faltam else 1


if __name__ == '__main__':
    sys.exit(main())
