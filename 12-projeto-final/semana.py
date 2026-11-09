"""Passa uma semana de respostas salvas pelas regras do monitor final e monta o histórico.

Uso, de dentro da pasta da aula:

    python semana.py semana-aula --saida saida/semana-aula
    python semana.py semana-exercicio --saida entrega/semana

Cada pasta de dia tem o que os nós de download do monitor receberiam naquele dia: as duas páginas da
loja, a resposta do Firecrawl e a do scrape.do (e, quando a loja falhou, as tentativas em loja.json).
O semana.py faz, dia a dia, o caminho do fluxo: as tentativas com espera crescente, a rodada, a trava,
a comparação com a última rodada boa e a gravação. Não abre o n8n, não acessa a internet e não espera
de verdade: as esperas aparecem só na tela.

Grava na pasta de saída:
    historico/rodada-AAAA-MM-DD.csv  as rodadas boas, começando pela de partida
    ultima-rodada.csv                a última rodada boa
    custos.csv                       uma linha por rodada montada, boa ou quebrada
    avisos/AAAA-MM-DD.txt            o aviso dos dias com mudança
    alertas/AAAA-MM-DD.txt           o alerta dos dias em que a raspagem quebrou ou o site recusou

Sai com 0 quando a semana rodou (mesmo com dias quebrados, que são o esperado), com 2 quando a pasta
não serve e com 3 quando a pasta de saída já tem um histórico (use --do-zero para apagar e refazer).
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import monitor


def carregar_dia(pasta):
    tentativas = [{'1': 200, '2': 200}]
    arq = pasta / 'loja.json'
    if arq.is_file():
        tentativas = json.loads(arq.read_text(encoding='utf-8'))['tentativas']
        if all(s == 200 for s in tentativas[-1].values()) is False and len(tentativas) < monitor.TENTATIVAS:
            tentativas = tentativas + [{'1': 200, '2': 200}]
    return tentativas


def rodar_dia(pasta, data, anterior):
    """Retorna um dict com o que aconteceu no dia. anterior: linhas da última rodada boa."""
    paginas = {1: (pasta / 'loja-pagina-1.html'), 2: (pasta / 'loja-pagina-2.html')}
    tentativas = carregar_dia(pasta)
    esperas = []
    for n, status in enumerate(tentativas, start=1):
        respostas = []
        for pagina in (1, 2):
            s = int(status.get(str(pagina), 200))
            corpo = paginas[pagina].read_text(encoding='utf-8') if s == 200 else ('Too Many Requests' if s == 429 else 'Service Unavailable')
            respostas.append((pagina, s, corpo))
        situacao, detalhe = monitor.ver_respostas(respostas, n)
        if situacao == 'tentar':
            esperas.append(monitor.espera(n))
            continue
        break
    if situacao == 'parar':
        return {'data': data, 'resultado': 'parou', 'detalhe': detalhe, 'esperas': esperas, 'tentativas': n}
    listas = {p: monitor.listas_da_pagina(c) for p, _, c in respostas}
    firecrawl = json.loads((pasta / 'firecrawl-pagina-2.json').read_text(encoding='utf-8'))
    scrapedo = json.loads((pasta / 'scrapedo-citacoes.json').read_text(encoding='utf-8'))
    r = monitor.montar_rodada(listas, firecrawl, scrapedo, data)
    base = {'data': data, 'esperas': esperas, 'tentativas': n, 'rodada': r}
    if r['problemas']:
        assunto, texto = monitor.texto_do_alerta(r)
        return {**base, 'resultado': 'quebrou', 'assunto': assunto, 'texto': texto}
    mudancas = monitor.comparar(r['linhas'], anterior)
    assunto, texto = monitor.texto_do_aviso(data, anterior[0]['rodada'] if anterior else '', len(r['linhas']),
                                            mudancas, r['conferencia']['erros'], r['custo'])
    return {**base, 'resultado': 'boa', 'mudancas': mudancas, 'assunto': assunto, 'texto': texto}


def main(argv=None):
    p = argparse.ArgumentParser(description='Passa uma semana salva pelas regras do monitor final.')
    p.add_argument('semana', help='pasta da semana (semana-aula ou semana-exercicio)')
    p.add_argument('--saida', required=True, help='pasta onde o histórico é gravado')
    p.add_argument('--do-zero', action='store_true', help='apaga o que já existe na pasta de saída')
    a = p.parse_args(argv)
    semana, saida = Path(a.semana), Path(a.saida)
    partida = semana / 'partida.csv'
    dias = sorted(d for d in semana.iterdir() if d.is_dir()) if semana.is_dir() else []
    if not partida.is_file() or not dias:
        print(f'{semana}: não achei partida.csv e as pastas dos dias', file=sys.stderr)
        return 2
    if (saida / 'historico').exists():
        if not a.do_zero:
            print(f'{saida} já tem um histórico. Use --do-zero para apagar e refazer.', file=sys.stderr)
            return 3
        shutil.rmtree(saida)
    for sub in ('historico', 'avisos', 'alertas'):
        (saida / sub).mkdir(parents=True, exist_ok=True)

    texto_partida = partida.read_text(encoding='utf-8')
    anterior = monitor.ler_csv(texto_partida)
    (saida / 'historico' / f'rodada-{anterior[0]["rodada"]}.csv').write_text(texto_partida, encoding='utf-8')
    (saida / 'ultima-rodada.csv').write_text(texto_partida, encoding='utf-8')
    print(f'{anterior[0]["rodada"]}  partida: {len(anterior)} itens')

    custos = []
    for pasta in dias:
        d = rodar_dia(pasta, pasta.name, anterior)
        espera = ''.join(f', esperou {s} s' for s in d['esperas'])
        tent = f'{d["tentativas"]} tentativa(s){espera}'
        if d['resultado'] == 'parou':
            (saida / 'alertas' / f'{d["data"]}.txt').write_text(d['detalhe'] + '\n', encoding='utf-8')
            print(f'{d["data"]}  parou na loja ({tent}): {d["detalhe"]} Nada gravado, sem custo.')
            continue
        c = d['rodada']['custo']
        custos.append({'rodada': d['data'], 'situacao': 'quebrou' if d['resultado'] == 'quebrou' else 'boa',
                       'scrapedo': c['scrapedo'], 'scrapedo_fonte': c['scrapedo_fonte'],
                       'firecrawl': c['firecrawl'], 'firecrawl_fonte': c['firecrawl_fonte'], 'total': c['total']})
        if d['resultado'] == 'quebrou':
            (saida / 'alertas' / f'{d["data"]}.txt').write_text(d['assunto'] + '\n' + d['texto'] + '\n', encoding='utf-8')
            problemas = '; '.join(p['detalhe'].rstrip('.') for p in d['rodada']['problemas'])
            print(f'{d["data"]}  QUEBROU ({tent}): {problemas}. Nada gravado, {c["total"]} créditos.')
            continue
        linhas = d['rodada']['linhas']
        texto = monitor.csv_da_rodada(linhas)
        (saida / 'historico' / f'rodada-{d["data"]}.csv').write_text(texto, encoding='utf-8')
        (saida / 'ultima-rodada.csv').write_text(texto, encoding='utf-8')
        erros = len(d['rodada']['conferencia']['erros'])
        if d['mudancas']:
            (saida / 'avisos' / f'{d["data"]}.txt').write_text(d['assunto'] + '\n' + d['texto'] + '\n', encoding='utf-8')
        print(f'{d["data"]}  boa ({tent}): {len(linhas)} itens, {len(d["mudancas"])} mudança(s), '
              f'{erros} erro(s) do Firecrawl, {c["total"]} créditos.')
        anterior = monitor.ler_csv(texto)

    with (saida / 'custos.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(custos[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(custos)
    gravadas = len(list((saida / 'historico').glob('rodada-*.csv')))
    print(f'{gravadas} rodadas no histórico; {sum(x["total"] for x in custos)} créditos em {len(custos)} rodadas montadas')
    return 0


if __name__ == '__main__':
    sys.exit(main())
