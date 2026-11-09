"""Antes de gastar crédito: o que um crawl com esses limites visitaria na loja de treino.

    python simular.py filtros/travel-3-profundidade-1.json
    python simular.py filtros/travel-3-profundidade-1.json --gravar saida/simulacao-travel-3.json

Não chama o Firecrawl. Aplica as regras de escopo da documentação do crawl ao grafo salvo
(grafo-loja.json), em largura a partir do endereço de partida:

- o endereço de partida também passa pelo include_paths; se não passar, o crawl volta vazio;
- include_paths e exclude_paths são expressões regulares procuradas no caminho do endereço;
- sem crawl_entire_domain, só entram endereços "filhos" da partida (aqui: mesma pasta para baixo);
- max_discovery_depth: a página na profundidade máxima é raspada, mas os links dela não são seguidos;
- limit: para de raspar quando chega no número de páginas;
- 1 crédito por página raspada, com formato só markdown.

O Firecrawl raspa várias páginas ao mesmo tempo, então a ordem real muda de uma rodada para outra.
Quando o limit corta, as páginas que entram podem ser outras. Sem corte, o conjunto é o mesmo.
"""
import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path

from loja import caminho, contar_tipos, endereco, ler_grafo, paginas_da_categoria

CREDITO_POR_PAGINA = 1  # só markdown, tabela de cobrança lida em 08/11/2026


def plural(n, palavra):
    return f'{n} {palavra}' if n == 1 else f'{n} {palavra}s'


class FiltroInvalido(Exception):
    pass


def ler_filtro(arquivo):
    dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    if 'crawl' not in dados or 'url' not in dados['crawl']:
        raise FiltroInvalido(f'{arquivo}: falta o bloco "crawl" com a "url" de partida')
    return dados


def regras(crawl):
    """Uma função que diz se um caminho passa pelos filtros, e por quê não passa."""
    incluir = [re.compile(p) for p in crawl.get('include_paths') or []]
    excluir = [re.compile(p) for p in crawl.get('exclude_paths') or []]
    partida = caminho(crawl['url'])
    pasta = partida.rsplit('/', 1)[0] + '/'
    inteiro = bool(crawl.get('crawl_entire_domain'))

    def motivo(cam):
        if incluir and not any(p.search(cam) for p in incluir):
            return 'não casa com include_paths'
        if any(p.search(cam) for p in excluir):
            return 'casa com exclude_paths'
        if not inteiro and not cam.startswith(pasta):
            return 'não é filho da partida'
        return None
    return motivo


def simular(crawl, links):
    """Retorna dict com visitadas [(caminho, profundidade)], parou_por e fila_restante."""
    limite = crawl.get('limit')
    if limite is None:
        raise FiltroInvalido('o crawl não tem "limit": o padrão do Firecrawl é 10.000 páginas')
    profundidade_max = crawl.get('max_discovery_depth')
    motivo = regras(crawl)
    partida = caminho(crawl['url'])
    if partida not in links:
        raise FiltroInvalido(f'a partida {partida} não está no grafo da loja')
    if motivo(partida) == 'não casa com include_paths':
        return {'visitadas': [], 'parou_por': 'a partida não passa no include_paths', 'fila_restante': 0}
    fila, vistos, visitadas = deque([(partida, 0)]), {partida}, []
    while fila and len(visitadas) < limite:
        cam, prof = fila.popleft()
        visitadas.append((cam, prof))
        if profundidade_max is not None and prof >= profundidade_max:
            continue
        for destino in links.get(cam, []):
            if destino not in vistos and motivo(destino) is None:
                vistos.add(destino)
                fila.append((destino, prof + 1))
    parou = 'limit' if fila else 'acabaram os links dentro das regras'
    return {'visitadas': visitadas, 'parou_por': parou, 'fila_restante': len(fila)}


def relatorio(filtro, resultado, links, info):
    crawl = filtro['crawl']
    cams = [c for c, _ in resultado['visitadas']]
    conta = contar_tipos(cams)
    linhas = [f'simulação pelas regras da documentação, sobre o grafo de {info["coletado_em"]} (não é resposta do Firecrawl)',
              f'partida: {caminho(crawl["url"])}',
              f'visitaria {plural(len(cams), "página")} (limit {crawl["limit"]})'
              + (': ' + ', '.join(f'{conta[t]} {t}' for t in conta if conta[t]) if cams else ''),
              f'custo: {plural(len(cams) * CREDITO_POR_PAGINA, "crédito")} (1 por página, só markdown)']
    pasta = filtro.get('categoria')
    if pasta:
        listas, livros = paginas_da_categoria(links, pasta)
        esperadas = set(listas) | set(livros)
        dentro = sum(c in esperadas for c in cams)
        linhas.append(f'da categoria {pasta}: {dentro} de {len(esperadas)}; fora dela: {len(cams) - dentro}')
    linhas.append(f'parou por: {resultado["parou_por"]}')
    return '\n'.join(linhas)


def gravar(filtro, resultado, arquivo, info):
    """Grava no mesmo formato do crawl_categoria.py, marcado como simulação."""
    corpo = {'origem': f'simulação sobre o grafo de {info["coletado_em"]}, não é resposta do Firecrawl',
             'nome': filtro.get('nome'), 'status': 'simulado',
             'creditos': len(resultado['visitadas']) * CREDITO_POR_PAGINA,
             'paginas': [{'url': endereco(c), 'profundidade': p} for c, p in resultado['visitadas']],
             'crawl': filtro['crawl']}
    Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
    Path(arquivo).write_text(json.dumps(corpo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('filtro')
    p.add_argument('--gravar', help='grava as páginas simuladas nesse arquivo JSON')
    args = p.parse_args(argv)
    info, links = ler_grafo()
    try:
        filtro = ler_filtro(args.filtro)
        resultado = simular(filtro['crawl'], links)
    except (FiltroInvalido, re.error) as erro:
        print('filtro recusado:', erro)
        return 2
    print(relatorio(filtro, resultado, links, info))
    if args.gravar:
        gravar(filtro, resultado, args.gravar, info)
        print(f'gravado em {args.gravar}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
