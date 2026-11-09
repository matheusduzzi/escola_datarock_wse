"""Os endereços do map que o crawl não visitou, separados pelo motivo.

    python fora_do_filtro.py filtros/travel-3-profundidade-1.json saida/crawl-travel-3-profundidade-1.json --mapa saida/mapa.json
    python fora_do_filtro.py filtros/travel-3-profundidade-1.json saida/simulacao-travel-3.json --inventario

Cada endereço do map (ou do grafo da loja, com --inventario) cai em um grupo:

- visitada: está no resultado do crawl;
- fora do filtro: as regras do filtro recusam o endereço (include_paths, exclude_paths ou "filho da
  partida"). O crawl não visitaria nem se achasse o link;
- dentro do filtro, não visitada: as regras deixariam entrar, mas o crawl não chegou nela (a
  profundidade parou os links, o limit cortou ou nenhum link levava até ela).

E mais um, de conferência: visitada pelo crawl e faltando no map.
Grava tudo em saida/fora-do-filtro-<nome>.csv, um endereço por linha.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from loja import TIPOS, caminho, contar_tipos, endereco, ler_grafo, tipo
from mapa import normalizar
from simular import ler_filtro, regras

AQUI = Path(__file__).resolve().parent
GRUPOS = ('visitada', 'fora do filtro', 'dentro do filtro, não visitada', 'visitada, faltando no map')


def separar(mapa, visitadas, crawl):
    """mapa e visitadas são conjuntos de caminhos. Retorna lista de (caminho, grupo, motivo)."""
    motivo = regras(crawl)
    linhas = []
    for cam in sorted(mapa):
        if cam in visitadas:
            linhas.append((cam, 'visitada', ''))
        elif motivo(cam):
            linhas.append((cam, 'fora do filtro', motivo(cam)))
        else:
            linhas.append((cam, 'dentro do filtro, não visitada', ''))
    linhas += [(cam, 'visitada, faltando no map', '') for cam in sorted(visitadas - mapa)]
    return linhas


def relatorio(linhas, origem_mapa):
    linhas_txt = [f'endereços comparados: {len(linhas)} ({origem_mapa})']
    for grupo in GRUPOS:
        do_grupo = [c for c, g, _ in linhas if g == grupo]
        if not do_grupo:
            continue
        conta = contar_tipos(do_grupo)
        linhas_txt.append(f'  {grupo}: {len(do_grupo)} (' + ', '.join(f'{conta[t]} {t}' for t in TIPOS if conta[t]) + ')')
    motivos = {}
    for _, g, m in linhas:
        if g == 'fora do filtro':
            motivos[m] = motivos.get(m, 0) + 1
    for m, n in sorted(motivos.items()):
        linhas_txt.append(f'    {m}: {n}')
    return '\n'.join(linhas_txt)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('filtro')
    p.add_argument('crawl', help='o JSON gravado pelo crawl_categoria.py ou pelo simular.py --gravar')
    origem = p.add_mutually_exclusive_group(required=True)
    origem.add_argument('--mapa', help='o saida/mapa.json gravado pelo mapa.py')
    origem.add_argument('--inventario', action='store_true', help='usa o grafo da loja no lugar do map')
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    filtro = ler_filtro(args.filtro)
    resultado = json.loads(Path(args.crawl).read_text(encoding='utf-8'))
    visitadas = {caminho(pg['url']) for pg in resultado['paginas'] if pg.get('url')}
    if args.inventario:
        info, links = ler_grafo()
        mapa, origem_mapa = set(links), f'grafo da loja de {info["coletado_em"]}'
    else:
        urls = json.loads(Path(args.mapa).read_text(encoding='utf-8'))['links']
        mapa = {c for c in (normalizar(u) for u in urls) if c}
        origem_mapa = f'map gravado em {Path(args.mapa).name}'
    linhas = separar(mapa, visitadas, filtro['crawl'])
    print(relatorio(linhas, origem_mapa))
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f'fora-do-filtro-{filtro.get("nome") or "sem-nome"}.csv'
    with arquivo.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['url', 'tipo', 'grupo', 'motivo'])
        for cam, grupo, motivo in linhas:
            w.writerow([endereco(cam), tipo(cam), grupo, motivo])
    print(f'gravado em {pasta.name}/{arquivo.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
