"""Raspa uma página de lista da loja de treino pelo Firecrawl: markdown e JSON com o esquema.

    python firecrawl_livros.py
    python firecrawl_livros.py --url https://books.toscrape.com/catalogue/page-2.html

Grava em saida/: o markdown da página (pagina-N.md) e o JSON com os livros (firecrawl-pagina-N.json).
Cada rodada é um scrape com markdown e JSON: 5 créditos pela tabela de cobrança do Firecrawl
(1 da página + 4 do JSON), lida em 08/11/2026.

A chave vem da variável FIRECRAWL_API_KEY ou do .env da raiz do kit. Ela nunca é impressa.

Códigos de saída: 0 deu certo; 1 a rodada falhou (status do site, JSON sem a lista, erro do serviço);
2 chave vazia ou com cara de outra coisa, antes de qualquer pedido; 3 o SDK não está instalado.
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

from esquema import ESQUEMA_LIVROS, PROMPT_LIVROS

AQUI = Path(__file__).resolve().parent
RAIZ_KIT = AQUI.parent
URL_PADRAO = 'https://books.toscrape.com/catalogue/page-1.html'
CREDITOS_TABELA = 1 + 4  # página + JSON, tabela de 08/11/2026


class ChaveVazia(Exception):
    pass


class ErroRodada(Exception):
    pass


def ler_chave(ambiente=None, arquivo_env=None):
    """A chave do Firecrawl: primeiro a variável de ambiente, depois o .env da raiz do kit."""
    ambiente = os.environ if ambiente is None else ambiente
    arquivo_env = RAIZ_KIT / '.env' if arquivo_env is None else Path(arquivo_env)
    chave = (ambiente.get('FIRECRAWL_API_KEY') or '').strip()
    if not chave and arquivo_env.is_file():
        for linha in arquivo_env.read_text(encoding='utf-8').splitlines():
            nome, _, valor = linha.partition('=')
            if nome.strip() == 'FIRECRAWL_API_KEY':
                chave = valor.strip().strip('"').strip("'")
    if not chave:
        raise ChaveVazia('FIRECRAWL_API_KEY está vazia. Copie a chave do painel do Firecrawl para o .env '
                         'da raiz do kit (veja o README do kit).')
    if not chave.startswith('fc-'):
        raise ChaveVazia('FIRECRAWL_API_KEY não começa com fc-. Veja se você não colou a chave de outro '
                         'serviço nessa linha do .env.')
    return chave


def esconder(texto, chave):
    """Troca a chave por *** em qualquer mensagem antes de mostrar."""
    return str(texto).replace(chave, '***') if chave else str(texto)


def formatos():
    """Markdown e JSON com o esquema, no formato do v2: o esquema vai dentro do objeto do formato."""
    return ['markdown', {'type': 'json', 'schema': ESQUEMA_LIVROS, 'prompt': PROMPT_LIVROS}]


def criar_cliente(chave):
    from firecrawl import Firecrawl  # importado aqui para os testes rodarem sem o SDK
    return Firecrawl(api_key=chave)


def raspar(url, cliente, chave=''):
    """Um scrape. Retorna dict com status_code, creditos, livros e markdown, ou levanta ErroRodada."""
    try:
        doc = cliente.scrape(url, formats=formatos(), max_age=0, timeout=120000)
    except Exception as erro:  # o SDK levanta UnauthorizedError, PaymentRequiredError, RateLimitError...
        raise ErroRodada(f'{type(erro).__name__}: {esconder(erro, chave)}') from None
    meta = getattr(doc, 'metadata', None)
    status = getattr(meta, 'status_code', None)
    creditos = getattr(meta, 'credits_used', None)
    if status != 200:
        raise ErroRodada(f'o site respondeu {status} ao Firecrawl; a página foi cobrada mesmo assim. '
                         'Olhe o endereço antes de tentar de novo.')
    dados = getattr(doc, 'json', None)
    livros = dados.get('livros') if isinstance(dados, dict) else None
    if not isinstance(livros, list):
        raise ErroRodada('o JSON voltou sem a lista "livros". Nada foi gravado como resultado.')
    return {'url': url, 'status_code': status, 'creditos': creditos, 'livros': livros,
            'markdown': getattr(doc, 'markdown', None) or ''}


def nome_da_pagina(url):
    m = re.search(r'page-(\d+)\.html', url)
    return f'pagina-{m.group(1)}' if m else 'pagina'


def gravar(resultado, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = nome_da_pagina(resultado['url'])
    md = pasta / f'{nome}.md'
    js = pasta / f'firecrawl-{nome}.json'
    md.write_text(resultado['markdown'], encoding='utf-8')
    corpo = {k: resultado[k] for k in ('url', 'status_code', 'creditos', 'livros')}
    corpo['quando'] = datetime.datetime.now().isoformat(timespec='seconds')
    js.write_text(json.dumps(corpo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return md, js


def main(argv=None, cliente=None, ambiente=None, arquivo_env=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--url', default=URL_PADRAO)
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    print(f'alvo: {args.url}')
    try:
        chave = ler_chave(ambiente, arquivo_env)
    except ChaveVazia as erro:
        print(erro)
        return 2
    if cliente is None:
        try:
            cliente = criar_cliente(chave)
        except ImportError:
            print('O SDK do Firecrawl não está instalado. Na raiz do kit: python -m pip install -r requirements.txt')
            return 3
    try:
        resultado = raspar(args.url, cliente, chave)
    except ErroRodada as erro:
        print('a rodada falhou:', erro)
        return 1
    md, js = gravar(resultado, args.saida)
    creditos = resultado['creditos']
    print(f'status {resultado["status_code"]}, {len(resultado["livros"])} livros no JSON, '
          f'markdown com {len(resultado["markdown"])} caracteres')
    print(f'custo pela tabela: {CREDITOS_TABELA} créditos (1 da página + 4 do JSON); '
          f'na resposta: {creditos if creditos is not None else "não veio, veja o painel"}')
    print(f'gravado: {md.name} e {js.name} em {Path(args.saida).name}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
