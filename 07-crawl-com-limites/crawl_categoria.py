"""Roda um crawl do Firecrawl com os limites de um arquivo de filtro e acompanha o status até o fim.

    python crawl_categoria.py filtros/travel-3-profundidade-1.json
    python crawl_categoria.py filtros/travel-3-profundidade-1.json --espera 5 --tempo-maximo 600

O crawl é um trabalho: o Firecrawl devolve um id na hora e raspa as páginas do lado dele. O script
pergunta o status a cada --espera segundos e mostra status, páginas e créditos. Se passar de
--tempo-maximo, ele cancela o trabalho. No fim, lê a lista de erros do crawl e grava em saida/.

Cada página raspada custa 1 crédito (só markdown, tabela de cobrança de 08/11/2026).
Perguntar o status não custa crédito.

Códigos de saída: 0 o crawl terminou como completed; 1 o crawl falhou, foi cancelado, passou do
tempo ou o serviço deu erro (nada é gravado como resultado); 2 chave vazia, chave com cara de
outra coisa ou filtro sem limit, antes de qualquer pedido; 3 o SDK não está instalado.
"""
import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

from loja import caminho, ler_grafo, paginas_da_categoria
from simular import FiltroInvalido, ler_filtro

AQUI = Path(__file__).resolve().parent
RAIZ_KIT = AQUI.parent
TERMINAIS = ('completed', 'failed', 'cancelled')
TETO_LIMIT = 200  # nesta aula, nenhum crawl precisa de mais páginas do que isso


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


def conferir_limit(crawl):
    limite = crawl.get('limit')
    if not isinstance(limite, int) or isinstance(limite, bool) or limite <= 0:
        raise FiltroInvalido('o filtro não tem um "limit" inteiro e positivo. Sem ele, o Firecrawl usa '
                             '10.000 páginas. Ponha o número de páginas que você espera, com folga pequena.')
    if limite > TETO_LIMIT:
        raise FiltroInvalido(f'limit {limite} passa do teto de {TETO_LIMIT} desta aula. Se precisa mesmo, '
                             'mude TETO_LIMIT no script, sabendo quanto vai custar.')


def criar_cliente(chave):
    from firecrawl import Firecrawl  # importado aqui para os testes rodarem sem o SDK
    return Firecrawl(api_key=chave)


def acompanhar(cliente, id_crawl, espera, tempo_maximo, mostrar=print, relogio=time.monotonic, dormir=time.sleep):
    """Pergunta o status até um estado terminal. Passou do tempo: cancela e levanta ErroRodada."""
    inicio = relogio()
    while True:
        job = cliente.get_crawl_status(id_crawl)
        mostrar(f'  {job.status:<9} {job.completed}/{job.total} páginas, {job.credits_used} créditos')
        if job.status in TERMINAIS:
            return job
        if relogio() - inicio >= tempo_maximo:
            cancelado = cliente.cancel_crawl(id_crawl)
            raise ErroRodada(f'passou de {tempo_maximo} s sem terminar; cancelamento pedido '
                             f'({"aceito" if cancelado else "recusado, confira no painel"}). '
                             f'Até aqui: {job.credits_used} créditos.')
        dormir(espera)


def url_do_documento(doc):
    meta = getattr(doc, 'metadata', None)
    return getattr(meta, 'source_url', None) or getattr(meta, 'url', None)


def rodar(filtro, cliente, chave='', espera=5, tempo_maximo=600, mostrar=print, **relogio):
    crawl = dict(filtro['crawl'])
    try:
        inicio = cliente.start_crawl(formats=['markdown'], only_main_content=True, **crawl)
        mostrar(f'trabalho {inicio.id} criado')
        job = acompanhar(cliente, inicio.id, espera, tempo_maximo, mostrar, **relogio)
        erros = cliente.get_crawl_errors(inicio.id) if job.status == 'completed' else None
    except ErroRodada:
        raise
    except Exception as erro:  # o SDK levanta UnauthorizedError, PaymentRequiredError, RateLimitError...
        raise ErroRodada(f'{type(erro).__name__}: {esconder(erro, chave)}') from None
    if job.status != 'completed':
        raise ErroRodada(f'o crawl terminou como {job.status}, com {job.credits_used} créditos gastos. '
                         'Nada foi gravado como resultado.')
    paginas = [{'url': url_do_documento(d), 'status_code': getattr(getattr(d, 'metadata', None), 'status_code', None)}
               for d in job.data]
    return {'nome': filtro.get('nome'), 'id': inicio.id, 'status': job.status, 'total': job.total,
            'completed': job.completed, 'creditos': job.credits_used, 'paginas': paginas,
            'erros': [{'url': e.url, 'erro': esconder(e.error, chave)} for e in erros.errors],
            'robots': list(erros.robots_blocked), 'crawl': crawl,
            'quando': datetime.datetime.now().isoformat(timespec='seconds')}


def resumo(resultado, filtro):
    cams = [caminho(p['url']) for p in resultado['paginas'] if p['url']]
    linhas = [f'{resultado["status"]}: {len(cams)} páginas no resultado, total {resultado["total"]}, '
              f'{resultado["creditos"]} créditos',
              f'erros do crawl: {len(resultado["erros"])}; bloqueadas pelo robots.txt: {len(resultado["robots"])}']
    nao_200 = [p for p in resultado['paginas'] if p['status_code'] != 200]
    if nao_200:
        linhas.append(f'páginas com status diferente de 200 (cobradas): {len(nao_200)}')
    pasta = filtro.get('categoria')
    if pasta:
        _, links = ler_grafo()
        listas, livros = paginas_da_categoria(links, pasta)
        esperadas = set(listas) | set(livros)
        dentro = sum(c in esperadas for c in cams)
        faltam = sorted(esperadas - set(cams))
        linhas.append(f'da categoria {pasta}: {dentro} de {len(esperadas)}; fora dela: {len(cams) - dentro}')
        if faltam:
            linhas.append(f'faltaram {len(faltam)}, por exemplo {faltam[0]}')
    return '\n'.join(linhas)


def main(argv=None, cliente=None, ambiente=None, arquivo_env=None, **relogio):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('filtro')
    p.add_argument('--espera', type=float, default=5, help='segundos entre as perguntas de status')
    p.add_argument('--tempo-maximo', type=float, default=600, help='segundos até cancelar')
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    try:
        filtro = ler_filtro(args.filtro)
        conferir_limit(filtro['crawl'])
    except FiltroInvalido as erro:
        print('filtro recusado:', erro)
        return 2
    print(f'partida: {filtro["crawl"]["url"]} (limit {filtro["crawl"]["limit"]})')
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
        resultado = rodar(filtro, cliente, chave, args.espera, args.tempo_maximo, **relogio)
    except ErroRodada as erro:
        print('o crawl falhou:', erro)
        return 1
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f'crawl-{filtro.get("nome") or "sem-nome"}.json'
    arquivo.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(resumo(resultado, filtro))
    print(f'gravado em {pasta.name}/{arquivo.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
