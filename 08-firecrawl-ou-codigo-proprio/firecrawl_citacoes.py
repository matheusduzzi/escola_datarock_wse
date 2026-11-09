"""O caminho do Firecrawl: o mesmo esquema nas três versões da página 1, sem mudar uma linha de código.

    python firecrawl_citacoes.py                 # as três versões, um scrape cada
    python firecrawl_citacoes.py --versao tabela # só uma

Para cada versão, faz um scrape com o formato JSON e o esquema abaixo, mede o tempo da chamada e grava
saida/firecrawl-<versao>.json com o endereço, o código que o site respondeu, os créditos, os segundos e
as citações. Cada scrape com JSON custa 5 créditos pela tabela de cobrança lida em 08/11/2026
(1 da página + 4 do JSON): as três versões, 15 créditos.

A chave vem da variável FIRECRAWL_API_KEY ou do .env da raiz do kit. Ela nunca é impressa.

Códigos de saída: 0 deu certo nas versões pedidas; 1 alguma rodada falhou (status do site, JSON sem a
lista, erro do serviço); 2 chave vazia ou com cara de outra coisa, antes de qualquer pedido; 3 o SDK
não está instalado.
"""
import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

from proprio import VERSOES

AQUI = Path(__file__).resolve().parent
RAIZ_KIT = AQUI.parent
CREDITOS_TABELA = 1 + 4  # página + JSON, tabela de 08/11/2026

# Sem minItems: a documentação avisa que ele faz o modelo inventar item para completar a conta.
ESQUEMA = {
    'type': 'object',
    'properties': {
        'citacoes': {
            'type': 'array',
            'description': 'Todas as citações da lista principal da página, na ordem em que aparecem.',
            'items': {
                'type': 'object',
                'properties': {
                    'texto': {'type': 'string', 'description': 'O texto da citação, sem o nome do autor.'},
                    'autor': {'type': 'string', 'description': 'Só o nome do autor. Ex.: Albert Einstein.'},
                    'tags': {'type': 'array', 'items': {'type': 'string'},
                             'description': 'As tags da citação, como aparecem na página. Ex.: ["change", "world"].'},
                },
                'required': ['texto', 'autor', 'tags'],
            },
        },
    },
    'required': ['citacoes'],
}
PROMPT = ('Extraia todas as citações da lista principal da página, sem pular nenhuma. '
          'Não inclua a lista das dez tags mais usadas. Não invente valor que não está na página.')


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
    return str(texto).replace(chave, '***') if chave else str(texto)


def criar_cliente(chave):
    from firecrawl import Firecrawl  # importado aqui para os testes rodarem sem o SDK
    return Firecrawl(api_key=chave)


def raspar(versao, cliente, chave='', relogio=time.perf_counter):
    """Um scrape com JSON. Retorna o dict que vai para saida/, ou levanta ErroRodada."""
    url = VERSOES[versao]
    inicio = relogio()
    try:
        doc = cliente.scrape(url, formats=[{'type': 'json', 'schema': ESQUEMA, 'prompt': PROMPT}],
                             max_age=0, timeout=120000)
    except Exception as erro:  # UnauthorizedError, PaymentRequiredError, RateLimitError...
        raise ErroRodada(f'{type(erro).__name__}: {esconder(erro, chave)}') from None
    segundos = relogio() - inicio
    meta = getattr(doc, 'metadata', None)
    status = getattr(meta, 'status_code', None)
    if status != 200:
        raise ErroRodada(f'o site respondeu {status} ao Firecrawl; a página foi cobrada mesmo assim.')
    dados = getattr(doc, 'json', None)
    citacoes = dados.get('citacoes') if isinstance(dados, dict) else None
    if not isinstance(citacoes, list):
        raise ErroRodada('o JSON voltou sem a lista "citacoes". Nada foi gravado como resultado.')
    return {'versao': versao, 'url': url, 'status_code': status,
            'creditos': getattr(meta, 'credits_used', None), 'segundos': round(segundos, 2),
            'citacoes': citacoes, 'quando': datetime.datetime.now().isoformat(timespec='seconds')}


def main(argv=None, cliente=None, ambiente=None, arquivo_env=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--versao', choices=['todas', *VERSOES], default='todas')
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    versoes = list(VERSOES) if args.versao == 'todas' else [args.versao]
    print(f'versões: {", ".join(versoes)}; custo pela tabela: {CREDITOS_TABELA * len(versoes)} créditos')
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
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    codigo = 0
    for versao in versoes:
        try:
            r = raspar(versao, cliente, chave)
        except ErroRodada as erro:
            print(f'{versao}: a rodada falhou: {erro}')
            codigo = 1
            continue
        destino = pasta / f'firecrawl-{versao}.json'
        destino.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        creditos = r['creditos'] if r['creditos'] is not None else 'não veio, veja o painel'
        print(f'{versao}: {len(r["citacoes"])} citações em {r["segundos"]:.1f} s; créditos na resposta: '
              f'{creditos}; gravado em {pasta.name}/{destino.name}')
    return codigo


if __name__ == '__main__':
    sys.exit(main())
