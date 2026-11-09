"""O map do Firecrawl na loja de treino, comparado com o mapa feito pelo nosso crawler.

    python mapa.py                       # chama o map (1 crédito) e grava saida/mapa.json
    python mapa.py --arquivo saida/mapa.json   # só compara um map já gravado, sem crédito

O map devolve uma lista de endereços, sem o conteúdo, por 1 crédito a chamada. A documentação avisa
que ele tira os endereços do sitemap, de buscas e de páginas que o Firecrawl já visitou, e que a
lista pode vir incompleta. A loja de treino não tem sitemap. A comparação com o grafo-loja.json
mostra quantos endereços de cada tipo o map achou e quais ele trouxe que a loja não tem.

Códigos de saída: 0 deu certo; 1 o serviço deu erro; 2 chave vazia ou com cara de outra coisa;
3 o SDK não está instalado.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

from crawl_categoria import ChaveVazia, criar_cliente, esconder, ler_chave
from loja import SITE, TIPOS, caminho, contar_tipos, ler_grafo

AQUI = Path(__file__).resolve().parent


def normalizar(url):
    """O caminho do endereço como no grafo: pasta vira pasta/index.html. De outro site: None."""
    cam = caminho(url)
    if cam is None:
        return None
    return cam + 'index.html' if cam.endswith('/') else cam


def comparar(urls, links):
    """Compara os endereços do map com o grafo. Retorna dict com contagens e listas."""
    achados, fora_do_site = set(), []
    for url in urls:
        cam = normalizar(url)
        if cam is None:
            fora_do_site.append(url)
        else:
            achados.add(cam)
    no_grafo = achados & set(links)
    return {'enderecos': len(urls), 'unicos': len(achados), 'fora_do_site': fora_do_site,
            'achados_por_tipo': contar_tipos(no_grafo), 'loja_por_tipo': contar_tipos(links),
            'fora_do_grafo': sorted(achados - set(links)), 'faltando': sorted(set(links) - achados)}


def relatorio(comp, info):
    linhas = [f'o map trouxe {comp["enderecos"]} endereços ({comp["unicos"]} caminhos diferentes da loja)',
              f'comparado com o grafo de {info["coletado_em"]}:']
    for t in TIPOS:
        if comp['loja_por_tipo'][t]:
            linhas.append(f'  {t:<10} {comp["achados_por_tipo"][t]} de {comp["loja_por_tipo"][t]}')
    linhas.append(f'faltando no map: {len(comp["faltando"])}')
    linhas.append(f'no map e fora do grafo: {len(comp["fora_do_grafo"])}'
                  + (f', por exemplo {comp["fora_do_grafo"][0]}' if comp['fora_do_grafo'] else ''))
    if comp['fora_do_site']:
        linhas.append(f'de outro site: {len(comp["fora_do_site"])}')
    return '\n'.join(linhas)


def chamar_map(cliente, chave, limite):
    try:
        res = cliente.map(SITE, limit=limite, sitemap='include', include_subdomains=False)
    except Exception as erro:
        raise RuntimeError(f'{type(erro).__name__}: {esconder(erro, chave)}') from None
    return [link.url for link in res.links]


def main(argv=None, cliente=None, ambiente=None, arquivo_env=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--arquivo', help='um map já gravado: compara sem chamar o Firecrawl')
    p.add_argument('--limite', type=int, default=5000)
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    info, links = ler_grafo()
    if args.arquivo:
        urls = json.loads(Path(args.arquivo).read_text(encoding='utf-8'))['links']
    else:
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
            urls = chamar_map(cliente, chave, args.limite)
        except RuntimeError as erro:
            print('o map falhou:', erro)
            return 1
        pasta = Path(args.saida)
        pasta.mkdir(parents=True, exist_ok=True)
        corpo = {'url': SITE, 'limite': args.limite, 'creditos_pela_tabela': 1, 'links': urls,
                 'quando': datetime.datetime.now().isoformat(timespec='seconds')}
        (pasta / 'mapa.json').write_text(json.dumps(corpo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'gravado em {pasta.name}/mapa.json (1 crédito pela tabela)')
    print(relatorio(comparar(urls, links), info))
    return 0


if __name__ == '__main__':
    sys.exit(main())
