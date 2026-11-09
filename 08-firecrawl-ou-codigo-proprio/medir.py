"""Mede os dois caminhos no mesmo alvo e preenche as linhas da tabela: citações, campos certos, tempo e créditos.

    python medir.py proprio --so-padrao   # o código de antes da mudança: a regra da versão padrão nas três
    python medir.py proprio               # cada versão com o seu extrator
    python medir.py proprio --ao-vivo     # baixa as três do site e mede o tempo de verdade
    python medir.py firecrawl             # lê o que o firecrawl_citacoes.py gravou em saida/

Os campos certos são contados contra gabarito-page-1.csv: 10 citações, 3 campos cada, 30 no total.
A chave da comparação é o texto. Antes de comparar, o texto perde espaços repetidos e as aspas das
pontas; o resto precisa ser igual. Autor igual depois de tirar espaços das pontas. Tags iguais e na
mesma ordem. Grava saida/medida-<caminho>.csv com uma linha por versão.

Códigos de saída: 0 as versões medidas têm 30 de 30; 1 alguma versão tem campo errado, faltando ou não
foi medida; 2 não há o que medir (falta o arquivo do Firecrawl de todas as versões).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

import proprio

AQUI = Path(__file__).resolve().parent
GABARITO = AQUI / 'gabarito-page-1.csv'
CAMPOS = ['texto', 'autor', 'tags']


def normalizar(texto):
    return re.sub(r'\s+', ' ', str(texto)).strip().strip('“”"').strip()


def ler_gabarito(caminho=GABARITO):
    with open(caminho, newline='', encoding='utf-8') as f:
        return [{'texto': l['texto'], 'autor': l['autor'], 'tags': l['tags'].split(';') if l['tags'] else []}
                for l in csv.DictReader(f)]


def comparar(gabarito, extraidas):
    """Quantas citações do gabarito vieram e quantos campos vieram certos. A chave é o texto."""
    por_texto = {normalizar(g['texto']): g for g in gabarito}
    certos = {c: 0 for c in CAMPOS}
    vistas, a_mais, repetidas, erros = set(), 0, 0, []
    for item in extraidas:
        if not isinstance(item, dict):
            a_mais += 1
            erros.append(('item que não é objeto', repr(item)[:60]))
            continue
        chave = normalizar(item.get('texto', ''))
        if chave in vistas:
            repetidas += 1
            erros.append(('repetida', chave[:60]))
            continue
        certo = por_texto.get(chave)
        if certo is None:
            a_mais += 1
            erros.append(('texto fora do gabarito', chave[:60]))
            continue
        vistas.add(chave)
        certos['texto'] += 1
        if isinstance(item.get('autor'), str) and item['autor'].strip() == certo['autor']:
            certos['autor'] += 1
        else:
            erros.append(('autor diferente', f'{item.get("autor")!r} no lugar de {certo["autor"]!r}'))
        tags = item.get('tags')
        if isinstance(tags, list) and [str(t).strip() for t in tags] == certo['tags']:
            certos['tags'] += 1
        else:
            erros.append(('tags diferentes', f'{tags!r} no lugar de {certo["tags"]!r}'))
    faltando = [g['texto'] for k, g in por_texto.items() if k not in vistas]
    erros += [('faltando', t[:60]) for t in faltando]
    return {'gabarito': len(gabarito), 'extraidas': len(extraidas), 'certos': certos,
            'total_certos': sum(certos.values()), 'faltando': len(faltando), 'a_mais': a_mais,
            'repetidas': repetidas, 'erros': erros}


def linhas_proprio(ao_vivo, so_padrao):
    for versao in proprio.VERSOES:
        extrator = proprio.extrair_padrao if so_padrao else proprio.EXTRATORES[versao]
        citacoes, segundos, erro = proprio.rodar(versao, extrator, ao_vivo=ao_vivo)
        yield versao, citacoes, segundos, 0, erro


def linhas_firecrawl(pasta):
    for versao in proprio.VERSOES:
        arq = Path(pasta) / f'firecrawl-{versao}.json'
        if not arq.is_file():
            yield versao, [], None, None, f'falta {arq.name}: rode python firecrawl_citacoes.py'
            continue
        r = json.loads(arq.read_text(encoding='utf-8'))
        creditos = r.get('creditos')
        yield versao, r.get('citacoes') or [], r.get('segundos'), \
            (creditos if creditos is not None else proprio_creditos_tabela()), ''


def proprio_creditos_tabela():
    from firecrawl_citacoes import CREDITOS_TABELA
    return f'{CREDITOS_TABELA} (tabela)'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('caminho', choices=['proprio', 'firecrawl'])
    p.add_argument('--ao-vivo', action='store_true', help='código próprio: baixa as páginas do site')
    p.add_argument('--so-padrao', action='store_true', help='código próprio: usa a regra da versão padrão em todas')
    p.add_argument('--saida', default=str(AQUI / 'saida'))
    args = p.parse_args(argv)
    gabarito = ler_gabarito()
    if args.caminho == 'proprio':
        regra = 'a regra da versão padrão nas três' if args.so_padrao else 'cada versão com o seu extrator'
        origem = 'baixadas do site agora' if args.ao_vivo else 'páginas salvas em 08/11/2026'
        print(f'caminho: código próprio ({regra}); {origem}')
        linhas = list(linhas_proprio(args.ao_vivo, args.so_padrao))
    else:
        print('caminho: Firecrawl, o mesmo esquema nas três versões; arquivos de saida/')
        linhas = list(linhas_firecrawl(args.saida))
        if all(erro for *_, erro in linhas):
            for versao, *_, erro in linhas:
                print(f'{versao:<7} {erro}')
            return 2
    print(f'{"versão":<7} {"citações":<9} {"texto":>5} {"autor":>5} {"tags":>5} {"certos":>7}  {"tempo":>8}  créditos')
    tabela, codigo = [], 0
    for versao, citacoes, segundos, creditos, erro in linhas:
        if erro:
            print(f'{versao:<7} {erro}')
            tabela.append({'versao': versao, 'citacoes': '', 'certos': '', 'segundos': '', 'creditos': '', 'nota': erro})
            codigo = 1
            continue
        r = comparar(gabarito, citacoes)
        c = r['certos']
        tempo = f'{segundos:.3f} s' if isinstance(segundos, (int, float)) else '?'
        print(f'{versao:<7} {r["extraidas"]:>2} de {r["gabarito"]:<3} {c["texto"]:>5} {c["autor"]:>5} {c["tags"]:>5} '
              f'{r["total_certos"]:>4}/{3 * r["gabarito"]}  {tempo:>8}  {creditos}')
        outros = [(t, d) for t, d in r['erros'] if t != 'faltando']
        for tipo, detalhe in outros[:5]:
            print(f'          {tipo}: {detalhe}')
        if len(outros) > 5:
            print(f'          e mais {len(outros) - 5} erros')
        if r['faltando']:
            print(f'          faltando: {r["faltando"]} citações do gabarito')
        tabela.append({'versao': versao, 'citacoes': r['extraidas'], 'certos': r['total_certos'],
                       'segundos': '' if segundos is None else round(segundos, 3), 'creditos': creditos,
                       'nota': '; '.join(sorted({t for t, _ in r['erros']}))})
        if r['total_certos'] != 3 * r['gabarito'] or r['a_mais'] or r['repetidas']:
            codigo = 1
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f'medida-{args.caminho}' + ('-so-padrao' if args.so_padrao else '') + ('-ao-vivo' if args.ao_vivo else '')
    with open(pasta / f'{nome}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['versao', 'citacoes', 'certos', 'segundos', 'creditos', 'nota'])
        w.writeheader()
        w.writerows(tabela)
    print(f'gravado em {pasta.name}/{nome}.csv')
    return codigo


if __name__ == '__main__':
    sys.exit(main())
