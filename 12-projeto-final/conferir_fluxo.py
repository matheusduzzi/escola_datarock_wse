"""Lê um fluxo exportado do n8n e diz se ele tem o que o projeto final pede.

Uso, de dentro da pasta da aula:

    python conferir_fluxo.py monitor-final.json
    python conferir_fluxo.py entrega/meu-fluxo.json --com-custo

Não abre o n8n, não roda o código dos nós e não gasta crédito. Segue as ligações do arquivo e olha:
o gatilho diário, os três alvos, as credenciais, a chave escrita, o Execute Once nos nós pagos, um
pedido por vez na loja, a espera que cresce a cada tentativa, a parada quando o site recusa, o
Firecrawl conferido com o código próprio antes da trava e a trava antes de toda gravação. Com
--com-custo, olha também se o custo de cada rodada vai para custos/ antes da trava (o exercício).

Sai com 0 quando está tudo no lugar, com 1 quando falta algo e com 2 quando o arquivo não é um fluxo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conferir_exportacao import achados_no_texto, achados_nos_campos  # noqa: E402

MEMORIA = re.compile(r'(ultima-rodada\.csv|/rodadas/)')


def tipo(no):
    return no.get('type', '').removeprefix('n8n-nodes-base.')


def ativo(no):
    return not no.get('disabled')


def ligacoes(fluxo, nos):
    """{nome: [(saida, destino)]}, só entre nós ativos."""
    saida = {}
    for origem, por_tipo in (fluxo.get('connections') or {}).items():
        if origem not in nos or not ativo(nos[origem]):
            continue
        for idx, alvos in enumerate((por_tipo or {}).get('main') or []):
            for a in alvos or []:
                if a.get('node') in nos and ativo(nos[a['node']]):
                    saida.setdefault(origem, []).append((idx, a['node']))
    return saida


def alcancaveis(liga, inicio, cortar=(), so_saida=None):
    """Nós alcançáveis a partir de inicio. cortar: nós que não deixam passar. so_saida: {nó: saída permitida}."""
    vistos, pilha = set(), list(inicio)
    while pilha:
        atual = pilha.pop()
        if atual in vistos:
            continue
        vistos.add(atual)
        if atual in cortar:
            continue
        for idx, dest in liga.get(atual, []):
            if so_saida and atual in so_saida and idx != so_saida[atual]:
                continue
            pilha.append(dest)
    return vistos


def http(no):
    return tipo(no) == 'httpRequest'


def texto_do_no(no):
    return json.dumps(no.get('parameters', {}), ensure_ascii=False)


def conferir(fluxo, com_custo=False):
    itens = []

    def item(ok, texto):
        itens.append((ok, texto))

    nos = {n['name']: n for n in fluxo.get('nodes', []) if isinstance(n, dict) and 'name' in n}
    ativos = {k: v for k, v in nos.items() if ativo(v)}
    liga = ligacoes(fluxo, nos)
    gatilhos = [k for k, v in ativos.items() if tipo(v) in ('scheduleTrigger', 'manualTrigger')]
    agenda = [k for k, v in ativos.items() if tipo(v) == 'scheduleTrigger']
    regras = [r for k in agenda for r in ativos[k]['parameters'].get('rule', {}).get('interval', [])]
    diario = any(('triggerAtHour' in r and r.get('field', 'days') == 'days') for r in regras)
    item(bool(agenda) and diario, f'gatilho agendado uma vez por dia: {", ".join(agenda) or "nenhum"}')
    fuso = (fluxo.get('settings') or {}).get('timezone')
    item(bool(fuso), f'fuso do fluxo definido: {fuso or "nenhum"}')
    chega = alcancaveis(liga, gatilhos)

    # Os três alvos.
    loja = [k for k, v in ativos.items() if http(v) and k in chega
            and ('books.toscrape.com' in texto_do_no(v) or '$json.url' in texto_do_no(v))
            and 'api.firecrawl.dev' not in texto_do_no(v) and 'api.scrape.do' not in texto_do_no(v)]
    codigo_das_paginas = ' '.join(texto_do_no(v) for v in ativos.values() if tipo(v) == 'code')
    duas_paginas = 'books.toscrape.com/' in codigo_das_paginas and 'catalogue/page-2.html' in codigo_das_paginas
    item(len(loja) == 1 and duas_paginas,
         f'alvo 1, a loja pelo código próprio (páginas 1 e 2): {", ".join(loja) or "nenhum"}')
    sd = [k for k, v in ativos.items() if http(v) and k in chega and 'api.scrape.do' in texto_do_no(v)]
    item(len(sd) == 1 and all('quotes.toscrape.com/js' in texto_do_no(ativos[k]) for k in sd),
         f'alvo 2, as citações pelo scrape.do: {", ".join(sd) or "nenhum"}')
    fc = [k for k, v in ativos.items() if k in chega and (
        (http(v) and 'api.firecrawl.dev/v2/scrape' in texto_do_no(v)) or 'firecrawl' in v.get('type', '').lower())]
    item(len(fc) == 1 and all('catalogue/page-2.html' in texto_do_no(ativos[k]) for k in fc),
         f'alvo 3, a página 2 pelo Firecrawl: {", ".join(fc) or "nenhum"}')

    # Credenciais e chave escrita.
    for k in sd:
        p = ativos[k]['parameters']
        cred = (ativos[k].get('credentials') or {}).get('httpQueryAuth')
        item(p.get('genericAuthType') == 'httpQueryAuth' and bool(cred),
             f'{k}: a chave vem da credencial Query Auth' + ('' if cred else ' (escolha a credencial no nó)'))
    for k in fc:
        v = ativos[k]
        credenciais = v.get('credentials') or {}
        if http(v):
            ok = v['parameters'].get('genericAuthType') == 'httpBearerAuth' and 'httpBearerAuth' in credenciais
        else:
            ok = bool(credenciais)
        item(ok, f'{k}: a chave vem da credencial' + ('' if ok else ' (escolha a credencial no nó)'))
    achados = list(achados_no_texto(json.dumps(fluxo, ensure_ascii=False))) + list(achados_nos_campos(fluxo))
    item(not achados, 'nenhuma chave escrita no arquivo' + (f': {"; ".join(achados)}' if achados else ''))
    for k in sd + fc:
        item(bool(ativos[k].get('executeOnce')), f'{k}: Execute Once ligado (uma chamada paga por rodada)')

    # Um pedido por vez, espera que cresce, parada na recusa.
    for k in loja:
        lote = ativos[k]['parameters'].get('options', {}).get('batching', {}).get('batch', {})
        um = lote.get('batchSize') in (0, 1) and (lote.get('batchInterval') or 0) >= 1000
        item(um, f'{k}: uma página por vez, com pelo menos 1 s entre elas (Batching)')
        resp = ativos[k]['parameters'].get('options', {}).get('response', {}).get('response', {})
        item(bool(resp.get('neverError')) and bool(resp.get('fullResponse')),
             f'{k}: recebe o status de cada resposta (Never Error e Include Response Headers and Status)')
    esperas = [k for k, v in ativos.items() if tipo(v) == 'wait']
    cresce = [k for k in esperas if '$runIndex' in str(ativos[k]['parameters'].get('amount', ''))]
    volta = [k for k in cresce if any(l in alcancaveis(liga, [k]) for l in loja)]
    item(bool(volta), f'espera que cresce a cada tentativa e volta ao download da loja: {", ".join(volta) or "nenhuma"}')
    ver = [k for k in loja for _, d in liga.get(k, []) if tipo(ativos[d]) == 'code']
    ver_codigo = ' '.join(ativos[d]['parameters'].get('jsCode', '') for k in loja for _, d in liga.get(k, [])
                          if tipo(ativos[d]) == 'code')
    sabe = all(t in ver_codigo for t in ('password', 'captcha', '403', '429')) and '$runIndex' in ver_codigo
    paradas = [k for k, v in ativos.items() if tipo(v) == 'stopAndError']
    para_antes = bool(ver) and any(p in alcancaveis(liga, ver, cortar=set(fc) | set(sd)) for p in paradas)
    item(sabe and para_antes, 'para com erro quando a loja recusa, pede login, mostra captcha ou não melhora '
         'nas tentativas, antes de chamar os serviços pagos')

    # A trava antes de gravar.
    gravam = [k for k, v in ativos.items() if tipo(v) == 'readWriteFile' and v['parameters'].get('operation') == 'write'
              and MEMORIA.search(str(v['parameters'].get('fileName', '')))]
    travas = [k for k, v in ativos.items() if tipo(v) == 'if' and 'problemas' in texto_do_no(v)]
    if not travas or not gravam:
        item(False, f'trava: If sobre "problemas" ({", ".join(travas) or "nenhum"}) e gravação da rodada '
             f'({", ".join(gravam) or "nenhuma"})')
    else:
        sem_trava = alcancaveis(liga, gatilhos, cortar=set(travas))
        furam = [g for g in gravam if g in sem_trava]
        item(not furam, 'toda gravação da rodada passa antes pela trava' + (f': grava sem passar por {", ".join(furam)}' if furam else ''))
        boa = alcancaveis(liga, travas, so_saida={t: 1 for t in travas})
        item(all(g in boa for g in gravam), 'a rodada boa (saída falsa da trava) chega às gravações')
        quebra = alcancaveis(liga, travas, so_saida={t: 0 for t in travas}) - set(travas)
        item(not (set(gravam) & quebra) and any(p in quebra for p in paradas),
             'a saída de quebra não grava a rodada e termina com erro')

        # O Firecrawl conferido com o código próprio antes da trava.
        html = [k for k, v in ativos.items() if tipo(v) == 'html']
        depois_fc = alcancaveis(liga, fc, cortar=set(travas)) - set(fc)
        confere = [k for k in depois_fc if tipo(ativos[k]) == 'code' and any(
            f"$('{h}')" in ativos[k]['parameters'].get('jsCode', '') for h in html)]
        item(bool(confere), 'o Firecrawl passa pelo gabarito do código próprio antes da trava: ' + (', '.join(confere) or 'nenhum nó'))

        if com_custo:
            custos = [k for k, v in ativos.items() if tipo(v) == 'readWriteFile' and v['parameters'].get('operation') == 'write'
                      and '/custos/' in str(v['parameters'].get('fileName', ''))]
            antes = alcancaveis(liga, confere, cortar=set(custos)) if confere else set()
            pulam = [x for x in gravam + paradas if x in antes and x not in custos]
            item(bool(custos) and not pulam,
                 f'o custo vai para custos/ em toda rodada montada, antes da trava: {", ".join(custos) or "nenhum nó"}'
                 + (f' (chega a {", ".join(pulam)} sem anotar)' if custos and pulam else ''))
            if custos:
                na_memoria = [c for c in custos if MEMORIA.search(str(ativos[c]['parameters'].get('fileName', '')))]
                item(not na_memoria, 'o arquivo do custo fica fora da memória do monitor (rodadas/ e ultima-rodada.csv)')
    return itens


def main(argv=None):
    p = argparse.ArgumentParser(description='Confere um fluxo exportado do monitor final.')
    p.add_argument('fluxo')
    p.add_argument('--com-custo', action='store_true', help='cobra também o custo anotado em custos/ (o exercício)')
    a = p.parse_args(argv)
    try:
        fluxo = json.loads(Path(a.fluxo).read_text(encoding='utf-8'))
        assert isinstance(fluxo, dict) and isinstance(fluxo.get('nodes'), list)
    except (OSError, ValueError, AssertionError):
        print(f'{a.fluxo}: não é um fluxo exportado do n8n')
        return 2
    itens = conferir(fluxo, a.com_custo)
    for ok, texto in itens:
        print(f'{"ok   " if ok else "FALTA"} {texto}')
    faltam = sum(1 for ok, _ in itens if not ok)
    print('monitor final pronto' if not faltam else f'{faltam} item(ns) faltando')
    return 0 if not faltam else 1


if __name__ == '__main__':
    sys.exit(main())
