"""Olha um fluxo exportado do n8n e diz se ele raspa a loja de treino pelo Firecrawl com credencial.

    python conferir_fluxo.py fluxo-no-firecrawl.json
    python conferir_fluxo.py meu-fluxo.json --paginas 2

Aceita os dois caminhos da aula: o nó do Firecrawl (pacote @mendable/n8n-nodes-firecrawl) ou o
HTTP Request chamando https://api.firecrawl.dev/v2/scrape. Com --paginas 2, pede também que as
páginas 1 e 2 venham de um nó anterior e que o endereço do scrape seja uma expressão.

Não abre o n8n nem chama o Firecrawl: só lê o arquivo. Sai com 0 quando todos os itens passam,
1 quando algum falta e 2 quando o arquivo não é um fluxo do n8n.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from conferir_exportacao import achados_no_texto, achados_nos_campos  # noqa: E402

PACOTE = '@mendable/n8n-nodes-firecrawl.'
API = 'https://api.firecrawl.dev/v2/scrape'
PAGINAS = ['https://books.toscrape.com/catalogue/page-1.html', 'https://books.toscrape.com/catalogue/page-2.html']
GATILHOS = ('n8n-nodes-base.manualTrigger', 'n8n-nodes-base.scheduleTrigger')
CREDENCIAIS_HTTP = ('httpBearerAuth', 'httpHeaderAuth')


def caminho_do_scrape(no):
    """'nó', 'http' ou None: se esse nó é o scrape do Firecrawl."""
    p = no.get('parameters') or {}
    if no.get('type', '').startswith(PACOTE):
        if p.get('resource', 'Scraping') == 'Scraping' and p.get('operation', 'scrape') == 'scrape':
            return 'nó'
    if no.get('type') == 'n8n-nodes-base.httpRequest' and str(p.get('url', '')).lstrip('=').strip().rstrip('/') == API:
        return 'http'
    return None


def tem_formato_json(valor):
    """Procura um formato {"type": "json", "schema": ...} com a lista livros, como o nó exporta."""
    if isinstance(valor, dict):
        if valor.get('type') == 'json' and 'livros' in str(valor.get('schema', '')):
            return True
        return any(tem_formato_json(v) for v in valor.values())
    if isinstance(valor, list):
        return any(tem_formato_json(v) for v in valor)
    return False


def depois_de(conexoes, origem):
    """Nomes dos nós ligados à saída de origem."""
    saidas = (conexoes.get(origem) or {}).get('main') or []
    return [c.get('node') for ramo in saidas for c in (ramo or [])]


def antes_de(conexoes, destino):
    return [o for o in conexoes if destino in depois_de(conexoes, o)]


def conferir(fluxo, texto, paginas=1):
    """Lista de (passou, frase) para cada item. Recebe o fluxo já lido e o texto do arquivo."""
    itens = []
    nos = fluxo['nodes']
    conexoes = fluxo.get('connections') or {}
    por_nome = {n.get('name'): n for n in nos}
    scrapes = [(n, caminho_do_scrape(n)) for n in nos if caminho_do_scrape(n)]
    itens.append((len(scrapes) == 1, f'um nó de scrape do Firecrawl (achei {len(scrapes)})'))
    if len(scrapes) != 1:
        return itens
    no, caminho = scrapes[0]
    p = no.get('parameters') or {}
    nome_caminho = 'nó do Firecrawl' if caminho == 'nó' else 'HTTP Request'
    itens.append((True, f'caminho: {nome_caminho} ("{no.get("name")}")'))

    cred = no.get('credentials') or {}
    if caminho == 'nó':
        escolhida = cred.get('firecrawlApi') or {}
        itens.append((bool(escolhida.get('id')), 'credencial Firecrawl API escolhida no nó'))
    else:
        tipo = p.get('genericAuthType')
        escolhida = cred.get(tipo) or {} if tipo in CREDENCIAIS_HTTP else {}
        itens.append((p.get('authentication') == 'genericCredentialType' and bool(escolhida.get('id')),
                      'credencial genérica (Bearer Auth ou Header Auth) escolhida no HTTP Request'))
        itens.append((str(p.get('method', 'GET')).upper() == 'POST', 'HTTP Request com método POST'))
        cabecalhos = json.dumps(p.get('headerParameters') or {}).lower()
        itens.append(('authorization' not in cabecalhos, 'nenhum cabeçalho Authorization escrito no nó'))

    achados = procurar_chave_no_texto(texto)
    itens.append((not achados, 'nenhuma chave escrita no arquivo' + (f': {"; ".join(achados)}' if achados else '')))

    if caminho == 'nó':
        formato = tem_formato_json(p)
        alvo = str(p.get('url', ''))
    else:
        corpo = str(p.get('jsonBody', ''))
        formato = bool(re.search(r'"type"\s*:\s*"json"', corpo)) and '"livros"' in corpo
        m = re.search(r'"url"\s*:\s*"([^"]*)"', corpo)
        alvo = m.group(1) if m else ''
    itens.append((formato, 'formato JSON com o esquema da lista "livros"'))

    if paginas == 1:
        itens.append(('books.toscrape.com' in alvo and '{{' not in alvo, f'raspa a loja de treino: {alvo or "(vazio)"}'))
    else:
        itens.append(('$json' in alvo and '{{' in alvo, f'endereço do scrape vem do item que chega: {alvo or "(vazio)"}'))
        anteriores = antes_de(conexoes, no.get('name'))
        texto_antes = json.dumps([por_nome.get(a, {}).get('parameters') for a in anteriores], ensure_ascii=False)
        faltam = [u for u in PAGINAS if u not in texto_antes]
        itens.append((bool(anteriores) and not faltam,
                      'as páginas 1 e 2 saem do nó ligado antes do scrape' + (f' (faltam: {", ".join(faltam)})' if faltam else '')))

    seguintes = [por_nome.get(d, {}) for d in depois_de(conexoes, no.get('name'))]
    codigo = [s for s in seguintes if s.get('type') == 'n8n-nodes-base.code'
              and 'livros' in str((s.get('parameters') or {}).get('jsCode', ''))]
    itens.append((bool(codigo), 'nó Code ligado depois do scrape, lendo a lista "livros"'))

    def chega_de_gatilho(nome, vistos=()):
        if por_nome.get(nome, {}).get('type') in GATILHOS:
            return True
        return any(chega_de_gatilho(a, vistos + (nome,)) for a in antes_de(conexoes, nome) if a not in vistos)
    itens.append((chega_de_gatilho(no.get('name')), 'um gatilho (manual ou agendado) leva até o scrape'))
    return itens


def procurar_chave_no_texto(texto):
    """A mesma busca do conferir_exportacao.py da raiz do kit."""
    return list(achados_no_texto(texto)) + list(achados_nos_campos(json.loads(texto)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivo')
    ap.add_argument('--paginas', type=int, choices=[1, 2], default=1)
    args = ap.parse_args(argv)
    try:
        texto = Path(args.arquivo).read_text(encoding='utf-8')
        fluxo = json.loads(texto)
        if not isinstance(fluxo, dict) or not isinstance(fluxo.get('nodes'), list):
            raise ValueError('não tem a lista "nodes" de um fluxo do n8n')
    except (OSError, ValueError) as erro:
        print(f'não dá para ler {args.arquivo} como fluxo do n8n: {erro}')
        return 2
    itens = conferir(fluxo, texto, args.paginas)
    for passou, frase in itens:
        print(('ok    ' if passou else 'FALTA ') + frase)
    faltam = sum(not passou for passou, _ in itens)
    print('fluxo pronto' if not faltam else f'{faltam} item(ns) faltando')
    return 0 if not faltam else 1


if __name__ == '__main__':
    sys.exit(main())
