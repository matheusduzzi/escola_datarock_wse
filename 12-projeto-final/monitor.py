"""As regras do monitor final, em Python, iguais às dos nós Code de monitor-final.json.

O semana.py, o relatorio.py e o conferir_projeto.py usam isto aqui. Os textos dos problemas, do
aviso e do alerta são os mesmos dos nós, letra por letra: o test_aula.py compara os números com os
arquivos .js, e quem produziu o kit comparou as saídas rodando o código dos nós no Node.js.

Nada aqui abre o n8n ou acessa a internet.
"""
import csv
import io
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

MAX_VAZIOS = 0.1
MINIMO = {'loja-pagina-1': 16, 'loja-pagina-2': 16, 'citacoes': 8}
TABELA_SCRAPEDO = 1
TABELA_FIRECRAWL = 5
TENTATIVAS = 3
PAGINAS = [(1, 'https://books.toscrape.com/'), (2, 'https://books.toscrape.com/catalogue/page-2.html')]
COLUNAS = ['rodada', 'alvo', 'chave', 'nome', 'preco', 'disponivel', 'firecrawl']
NOMES_ALVO = {'loja-pagina-1': 'loja, página 1', 'loja-pagina-2': 'loja, página 2', 'citacoes': 'citações'}


def numero_js(valor):
    """Number() do JavaScript para os textos que aparecem aqui: '' vira 0, texto ruim vira None (NaN)."""
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float)):
        return float(valor)
    if valor is None:
        return 0.0
    t = str(valor).strip()
    if t == '':
        return 0.0
    try:
        return float(t)
    except ValueError:
        return None


def texto_js(valor):
    """String() do JavaScript para o que vem do Firecrawl."""
    if valor is None:
        return 'null'
    if isinstance(valor, bool):
        return 'true' if valor else 'false'
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, float):
        return repr(valor)
    return str(valor)


def ler_preco(texto):
    m = re.search(r'£\s*(\d+\.\d{2})', texto or '')
    return m.group(1) if m else ''


def ler_estoque(texto):
    if re.search(r'out of stock', texto or '', flags=re.I):
        return 'nao'
    if re.search(r'\bin stock\b', texto or '', flags=re.I):
        return 'sim'
    return ''


def ler_endereco(href, base):
    h = (href or '').strip()
    return urljoin(base, h) if h else ''


def listas_da_pagina(html):
    """As quatro listas do nó "Tirar os livros"."""
    sopa = BeautifulSoup(html, 'lxml')
    links = sopa.select('article.product_pod h3 a')
    return {
        'titulo': [a.get('title', '') for a in links],
        'preco': [p.get_text().strip() for p in sopa.select('article.product_pod p.price_color')],
        'disponibilidade': [p.get_text().strip() for p in sopa.select('article.product_pod p.instock.availability')],
        'endereco': [a.get('href', '') for a in links],
    }


def ver_respostas(respostas, tentativa):
    """O nó "Ver as respostas da loja". respostas: [(pagina, status, corpo)]. Retorna (situacao, detalhe)."""
    achados = []
    for pagina, status, corpo in respostas:
        tipo, motivo = 'ok', ''
        if status in (401, 403, 407):
            tipo, motivo = 'parar', f'a loja recusou o pedido ({status})'
        elif re.search(r'type=["\']?password', corpo or '', flags=re.I):
            tipo, motivo = 'parar', 'a loja respondeu com um formulário de login'
        elif re.search(r'captcha', corpo or '', flags=re.I):
            tipo, motivo = 'parar', 'a loja respondeu com um captcha'
        elif status == 429 or status >= 500:
            tipo, motivo = 'tentar', f'a loja respondeu {status}'
        elif status != 200:
            tipo, motivo = 'parar', f'a loja respondeu {status}'
        achados.append((pagina, tipo, motivo))
    recusa = next((a for a in achados if a[1] == 'parar'), None)
    ruim = next((a for a in achados if a[1] == 'tentar'), None)
    if recusa:
        return 'parar', (f'Parei: na página {recusa[0]}, {recusa[2]}. '
                         'Não tente passar por isso: veja o que mudou no site.')
    if ruim and tentativa < TENTATIVAS:
        return 'tentar', f'tentativa {tentativa}: na página {ruim[0]}, {ruim[2]}; vou esperar e pedir de novo'
    if ruim:
        return 'parar', f'Parei: na página {ruim[0]}, {ruim[2]} nas {TENTATIVAS} tentativas.'
    return 'ok', f'tentativa {tentativa}: as {len(achados)} páginas vieram bem'


def espera(tentativa):
    """Segundos do nó "Esperar mais a cada tentativa" antes da tentativa seguinte: 5, 10, 20..."""
    return 5 * 2 ** (tentativa - 1)


def _vazios(problemas, alvo, itens, nomes):
    if not itens:
        return
    for campo, nome in nomes.items():
        vazios = sum(1 for linha in itens if linha[campo] == '')
        if vazios / len(itens) > MAX_VAZIOS:
            pct = int(100 * vazios / len(itens) + 0.5)
            problemas.append({'alvo': alvo, 'regra': 'vazios', 'campo': campo,
                              'detalhe': f'{alvo}: {vazios} de {len(itens)} sem {nome} ({pct}%)'})


def _contagem(problemas, alvo, total, coisa):
    if total < MINIMO[alvo]:
        problemas.append({'alvo': alvo, 'regra': 'contagem',
                          'detalhe': f'{alvo}: {total} {coisa}; o mínimo é {MINIMO[alvo]}'})


def montar_rodada(listas_por_pagina, firecrawl, scrapedo, rodada):
    """O nó "Montar a rodada".

    listas_por_pagina: {1: listas, 2: listas} (as do nó HTML); firecrawl: a resposta da API em JSON;
    scrapedo: {'data': corpo, 'headers': {...}, 'statusCode': 200}.
    """
    problemas, linhas, por_pagina = [], [], {}
    for pagina, base in PAGINAS:
        alvo = f'loja-pagina-{pagina}'
        lst = {k: list(v) for k, v in listas_por_pagina[pagina].items()}
        total = max(len(v) for v in lst.values())
        livros = []
        for k in range(total):
            def em(nome):
                return lst[nome][k] if k < len(lst[nome]) else ''
            livros.append({'rodada': rodada, 'alvo': alvo, 'chave': ler_endereco(em('endereco'), base),
                           'nome': (em('titulo') or '').strip(), 'preco': ler_preco(em('preco')),
                           'disponivel': ler_estoque(em('disponibilidade')), 'firecrawl': ''})
        _contagem(problemas, alvo, total, 'livros na página')
        if total > 0 and any(len(v) != total for v in lst.values()):
            problemas.append({'alvo': alvo, 'regra': 'listas', 'detalhe': (
                f'{alvo}: as listas vieram com tamanhos diferentes: {len(lst["titulo"])} títulos, '
                f'{len(lst["preco"])} preços, {len(lst["disponibilidade"])} disponibilidades e '
                f'{len(lst["endereco"])} endereços')})
        _vazios(problemas, alvo, livros, {'chave': 'endereço', 'nome': 'título', 'preco': 'preço',
                                          'disponivel': 'disponibilidade'})
        por_pagina[pagina] = livros

    conferencia = {'comparados': 0, 'campos': 0, 'certos': 0, 'erros': []}
    fc = firecrawl or {}
    dados = fc.get('data') if isinstance(fc.get('data'), dict) else {}
    fc_livros = (dados.get('json') or {}).get('livros') if fc.get('success') is True else None
    fc_status = (dados.get('metadata') or {}).get('statusCode') if dados else None
    if not isinstance(fc_livros, list) or fc_status != 200:
        sucesso = texto_js(fc.get('success')) if 'success' in fc else 'undefined'
        status = texto_js(fc_status) if fc_status is not None else 'undefined'
        problemas.append({'alvo': 'firecrawl', 'regra': 'firecrawl', 'detalhe': (
            f'firecrawl: a resposta veio sem a lista de livros (success {sucesso}, status da loja {status})')})
    else:
        base = PAGINAS[1][1]
        do_fc = {}
        for b in fc_livros:
            do_fc[ler_endereco(b.get('url'), base)] = b
        for livro in por_pagina[2]:
            b = do_fc.pop(livro['chave'], None)
            if b is None:
                conferencia['erros'].append({'chave': livro['chave'], 'nome': livro['nome'], 'campo': 'livro',
                                             'firecrawl': 'faltou', 'gabarito': livro['nome']})
                livro['firecrawl'] = 'faltou'
                continue
            conferencia['comparados'] += 1
            notas = []
            em_estoque = b.get('em_estoque')
            pares = [
                ('nome', texto_js(b.get('titulo') if b.get('titulo') is not None else '').strip(), livro['nome']),
                ('preco', numero_js(b.get('preco')), numero_js(livro['preco'])),
                ('disponivel', 'sim' if em_estoque is True else 'nao' if em_estoque is False else '', livro['disponivel']),
            ]
            for campo, deles, nosso in pares:
                conferencia['campos'] += 1
                if deles == nosso and deles is not None:
                    conferencia['certos'] += 1
                else:
                    d = 'NaN' if deles is None else texto_js(deles)
                    n = 'NaN' if nosso is None else texto_js(nosso)
                    conferencia['erros'].append({'chave': livro['chave'], 'nome': livro['nome'], 'campo': campo,
                                                 'firecrawl': d, 'gabarito': n})
                    notas.append(f'{campo}={d}')
            livro['firecrawl'] = '; '.join(notas) if notas else 'ok'
        for chave, b in do_fc.items():
            conferencia['erros'].append({'chave': chave, 'nome': texto_js(b.get('titulo') or ''), 'campo': 'livro',
                                         'firecrawl': 'a mais', 'gabarito': ''})

    corpo = str((scrapedo or {}).get('data') or '')
    citacoes = []
    if re.search(r'type=["\']?password', corpo, flags=re.I) or re.search(r'captcha', corpo, flags=re.I):
        problemas.append({'alvo': 'citacoes', 'regra': 'recusa',
                          'detalhe': 'citacoes: a página veio com login ou captcha. Pare: não tente passar por isso.'})
    else:
        m = re.search(r'var data = (\[[\s\S]*?\]);\s*for', corpo)
        try:
            lista = json.loads(m.group(1)) if m else []
        except ValueError:
            lista = []
        for q in lista:
            texto = re.sub(r'^“|”$', '', str(q.get('text') or '')).strip()
            autor = str((q.get('author') or {}).get('name') or '').strip()
            citacoes.append({'rodada': rodada, 'alvo': 'citacoes', 'chave': texto, 'nome': autor,
                             'preco': '', 'disponivel': '', 'firecrawl': ''})
        _contagem(problemas, 'citacoes', len(citacoes), 'citações na página')
        _vazios(problemas, 'citacoes', citacoes, {'chave': 'texto', 'nome': 'autor'})

    cab = ((scrapedo or {}).get('headers') or {}).get('scrape.do-request-cost')
    valor = numero_js(cab) if cab is not None else None
    custo = {'scrapedo': valor if valor is not None else TABELA_SCRAPEDO,
             'scrapedo_fonte': 'cabeçalho' if valor is not None else 'tabela',
             'firecrawl': TABELA_FIRECRAWL, 'firecrawl_fonte': 'tabela'}
    custo['scrapedo'] = int(custo['scrapedo']) if float(custo['scrapedo']).is_integer() else custo['scrapedo']
    custo['total'] = custo['scrapedo'] + custo['firecrawl']
    linhas = por_pagina[1] + por_pagina[2] + citacoes
    totais = {'loja-pagina-1': len(por_pagina[1]), 'loja-pagina-2': len(por_pagina[2]), 'citacoes': len(citacoes)}
    return {'rodada': rodada, 'totais': totais, 'problemas': problemas, 'conferencia': conferencia,
            'custo': custo, 'linhas': linhas}


def comparar(hoje, antes):
    """O nó "Comparar com a anterior": a lista de mudanças."""
    por_chave = {(l['alvo'], l['chave']): l for l in hoje}
    mudancas = []
    for velho in antes:
        novo = por_chave.get((velho['alvo'], velho['chave']))
        if novo is None:
            mudancas.append({'alvo': velho['alvo'], 'chave': velho['chave'], 'nome': velho['nome'],
                             'tipo': 'sumiu', 'antes': velho['preco'], 'depois': ''})
            continue
        if velho['preco'] != '' and novo['preco'] != '' and numero_js(velho['preco']) != numero_js(novo['preco']):
            mudancas.append({'alvo': novo['alvo'], 'chave': novo['chave'], 'nome': novo['nome'],
                             'tipo': 'preco', 'antes': velho['preco'], 'depois': novo['preco']})
        if velho['disponivel'] != '' and novo['disponivel'] != '' and velho['disponivel'] != novo['disponivel']:
            mudancas.append({'alvo': novo['alvo'], 'chave': novo['chave'], 'nome': novo['nome'],
                             'tipo': 'disponibilidade', 'antes': velho['disponivel'], 'depois': novo['disponivel']})
    return mudancas


def texto_do_aviso(rodada, anterior, itens_hoje, mudancas, erros, custo):
    linhas = []
    for m in mudancas:
        onde = NOMES_ALVO.get(m['alvo'], m['alvo'])
        if m['tipo'] == 'preco':
            rumo = 'caiu' if float(m['depois']) < float(m['antes']) else 'subiu'
            linhas.append(f'{onde}: {m["nome"]}: o preço {rumo} de £{m["antes"]} para £{m["depois"]}')
        elif m['tipo'] == 'disponibilidade':
            linhas.append(f'{onde}: {m["nome"]}: ' + ('voltou ao estoque' if m['depois'] == 'sim' else 'ficou sem estoque'))
        else:
            linhas.append(f'{onde}: {m["nome"]}: saiu da página')
    partes = [f'Comparei {itens_hoje} itens dos três alvos com a rodada de {anterior}.'] + [f'- {l}' for l in linhas]
    if erros:
        partes.append('O Firecrawl errou na página 2 (o histórico ficou com o valor do código próprio):')
        partes += [f'- {e["nome"]}: {e["campo"]} veio {e["firecrawl"]}, o código próprio leu {e["gabarito"]}' for e in erros]
    partes.append(f'Créditos dessa rodada: {custo["total"]} (scrape.do {custo["scrapedo"]}, pelo {custo["scrapedo_fonte"]}; '
                  f'Firecrawl {custo["firecrawl"]}, pela {custo["firecrawl_fonte"]}).')
    return f'Monitor de preço: {len(mudancas)} mudança(s) na rodada de {rodada}', '\n'.join(partes)


def texto_do_alerta(r):
    partes = ['Nada foi gravado. A rodada anterior continua valendo.']
    partes += [f'- {p["detalhe"]}' for p in r['problemas']]
    partes.append(f'Créditos gastos mesmo assim: {r["custo"]["total"]} '
                  f'(scrape.do {r["custo"]["scrapedo"]}, Firecrawl {r["custo"]["firecrawl"]}).')
    partes.append('Abra a página que quebrou e veja o que mudou antes de mexer no fluxo.')
    return f'Monitor de preço: a raspagem quebrou na rodada de {r["rodada"]}', '\n'.join(partes)


def csv_da_rodada(linhas):
    """O arquivo que o "Rodada de hoje em CSV" monta: cabeçalho com as colunas do primeiro item."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUNAS, lineterminator='\n')
    w.writeheader()
    w.writerows(linhas)
    return buf.getvalue()


def ler_csv(texto):
    return list(csv.DictReader(io.StringIO(texto)))
