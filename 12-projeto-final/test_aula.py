"""Testes da aula «Projeto final: monitor de preços de três alvos». Sem internet e sem o n8n.

Os fluxos com defeito daqui são cópias do monitor-final.json alteradas no próprio teste. Os números
do Python (monitor.py) são comparados com os dos arquivos .js, que são o código dos nós.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import conferir_fluxo
import monitor
import relatorio

AQUI = Path(__file__).resolve().parent
FLUXO = json.loads((AQUI / 'monitor-final.json').read_text(encoding='utf-8'))
CREDENCIAIS = {'Citações pelo scrape.do': {'httpQueryAuth': {'id': '1', 'name': 'scrape.do'}},
               'Página 2 pelo Firecrawl': {'httpBearerAuth': {'id': '2', 'name': 'Firecrawl'}}}


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=AQUI, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def com_credenciais(fluxo=None):
    f = copy.deepcopy(fluxo or FLUXO)
    for n in f['nodes']:
        if n['name'] in CREDENCIAIS:
            n['credentials'] = CREDENCIAIS[n['name']]
    return f


def no(fluxo, nome):
    return next(n for n in fluxo['nodes'] if n['name'] == nome)


def faltas(fluxo, com_custo=False):
    return [t for ok, t in conferir_fluxo.conferir(fluxo, com_custo) if not ok]


def test_fluxo_do_kit_so_falta_a_credencial():
    codigo, saida = rodar('conferir_fluxo.py', 'monitor-final.json')
    assert codigo == 1 and '2 item(ns) faltando' in saida
    assert faltas(com_credenciais()) == []


def test_codigo_dos_nos_igual_aos_arquivos():
    pares = {'Páginas da loja': 'paginas-da-loja.js', 'Ver as respostas da loja': 'ver-as-respostas.js',
             'Montar a rodada': 'montar-a-rodada.js', 'Uma linha por item': 'uma-linha-por-item.js',
             'Comparar com a anterior': 'comparar-com-a-anterior.js', 'Montar o aviso': 'montar-o-aviso.js',
             'Montar o alerta de quebra': 'montar-o-alerta.js'}
    for nome, arq in pares.items():
        assert no(FLUXO, nome)['parameters']['jsCode'] == (AQUI / arq).read_text(encoding='utf-8').rstrip('\n')


def test_gerado_por_ia_tem_tres_defeitos():
    f = com_credenciais(json.loads((AQUI / 'teste/monitor-gerado-por-ia.json').read_text(encoding='utf-8')))
    f2 = faltas(f)
    assert len(f2) == 4  # a credencial do scrape.do saiu junto com a chave escrita
    assert any('chave escrita' in t for t in f2)
    assert any('Execute Once' in t for t in f2)
    assert any('espera que cresce' in t for t in f2)


def test_gravar_antes_da_trava_falha():
    f = com_credenciais()
    f['connections']['Montar a rodada'] = {'main': [[{'node': 'Uma linha por item', 'type': 'main', 'index': 0},
                                                     {'node': 'A raspagem quebrou?', 'type': 'main', 'index': 0}]]}
    assert any('grava sem passar' in t for t in faltas(f))


def test_trava_com_saidas_trocadas_falha():
    f = com_credenciais()
    f['connections']['A raspagem quebrou?']['main'].reverse()
    assert len(faltas(f)) >= 2


def test_espera_que_nao_volta_ao_download_falha():
    f = com_credenciais()
    f['connections']['Esperar mais a cada tentativa'] = {'main': [[{'node': 'Tirar os livros', 'type': 'main', 'index': 0}]]}
    assert any('espera que cresce' in t for t in faltas(f))


def test_sem_parada_na_recusa_falha():
    f = com_credenciais()
    no(f, 'Parar: o site recusou')['disabled'] = True
    assert any('para com erro quando a loja recusa' in t for t in faltas(f))


def test_loja_sem_um_pedido_por_vez_falha():
    f = com_credenciais()
    no(f, 'Baixar as páginas da loja')['parameters']['options']['batching']['batch']['batchSize'] = 50
    assert any('uma página por vez' in t for t in faltas(f))


def test_firecrawl_sem_conferencia_falha():
    f = com_credenciais()
    codigo = no(f, 'Montar a rodada')['parameters']['jsCode']
    no(f, 'Montar a rodada')['parameters']['jsCode'] = codigo.replace("$('Tirar os livros')", '$input')
    assert any('gabarito do código próprio' in t for t in faltas(f))


def test_sem_agenda_falha():
    f = com_credenciais()
    f['nodes'] = [n for n in f['nodes'] if n['name'] != 'Todo dia às 7h']
    assert any('gatilho agendado' in t for t in faltas(f))


def test_kit_ainda_nao_anota_o_custo():
    assert any('custos/' in t for t in faltas(com_credenciais(), com_custo=True))


def test_arquivo_que_nao_e_fluxo(tmp_path):
    (tmp_path / 'x.json').write_text('[1, 2]', encoding='utf-8')
    assert rodar('conferir_fluxo.py', tmp_path / 'x.json')[0] == 2


def test_fluxos_sem_chave():
    assert rodar('../conferir_exportacao.py', 'monitor-final.json')[0] == 0
    assert rodar('../conferir_exportacao.py', 'teste/monitor-gerado-por-ia.json')[0] == 1


def constante(arquivo, nome):
    m = re.search(rf'const {nome} = ([^;]+);', (AQUI / arquivo).read_text(encoding='utf-8'))
    return m.group(1).strip()


def test_numeros_do_python_iguais_aos_do_js():
    assert float(constante('montar-a-rodada.js', 'MAX_VAZIOS')) == monitor.MAX_VAZIOS
    assert int(constante('montar-a-rodada.js', 'TABELA_SCRAPEDO')) == monitor.TABELA_SCRAPEDO
    assert int(constante('montar-a-rodada.js', 'TABELA_FIRECRAWL')) == monitor.TABELA_FIRECRAWL
    assert int(constante('ver-as-respostas.js', 'TENTATIVAS')) == monitor.TENTATIVAS
    minimo = constante('montar-a-rodada.js', 'MINIMO')
    for alvo, n in monitor.MINIMO.items():
        assert re.search(rf"'?{alvo}'?: {n}\b", minimo), (alvo, minimo)
    assert no(FLUXO, 'Esperar mais a cada tentativa')['parameters']['amount'] == '={{ 5 * Math.pow(2, $runIndex) }}'
    assert [monitor.espera(n) for n in (1, 2)] == [5, 10]


@pytest.mark.parametrize('respostas,tentativa,situacao,trecho', [
    ([(1, 200, '<html>'), (2, 200, '<html>')], 1, 'ok', 'as 2 páginas vieram bem'),
    ([(1, 403, ''), (2, 200, '')], 1, 'parar', 'recusou o pedido (403)'),
    ([(1, 200, '<input type="password">'), (2, 200, '')], 1, 'parar', 'formulário de login'),
    ([(1, 200, 'g-recaptcha'), (2, 200, '')], 1, 'parar', 'captcha'),
    ([(1, 429, ''), (2, 200, '')], 1, 'tentar', 'vou esperar'),
    ([(1, 200, ''), (2, 503, '')], 3, 'parar', 'nas 3 tentativas'),
    ([(1, 404, ''), (2, 200, '')], 1, 'parar', 'respondeu 404'),
])
def test_ver_as_respostas(respostas, tentativa, situacao, trecho):
    s, d = monitor.ver_respostas(respostas, tentativa)
    assert s == situacao and trecho in d


def rodada_de(pasta_dia, firecrawl=None, scrapedo=None):
    dia = AQUI / 'semana-aula' / pasta_dia
    listas = {p: monitor.listas_da_pagina((dia / f'loja-pagina-{p}.html').read_text(encoding='utf-8')) for p in (1, 2)}
    fc = firecrawl if firecrawl is not None else json.loads((dia / 'firecrawl-pagina-2.json').read_text(encoding='utf-8'))
    sd = scrapedo if scrapedo is not None else json.loads((dia / 'scrapedo-citacoes.json').read_text(encoding='utf-8'))
    return monitor.montar_rodada(listas, fc, sd, pasta_dia)


def test_dia_bom_passa_e_custa_seis():
    r = rodada_de('2026-10-26')
    assert r['problemas'] == [] and r['totais'] == {'loja-pagina-1': 20, 'loja-pagina-2': 20, 'citacoes': 10}
    assert r['custo']['total'] == 6 and r['custo']['scrapedo_fonte'] == 'cabeçalho'


def test_firecrawl_sem_lista_quebra_a_rodada():
    r = rodada_de('2026-10-26', firecrawl={'success': False, 'error': 'Payment Required'})
    assert [p['regra'] for p in r['problemas']] == ['firecrawl']


def test_custo_sem_cabecalho_vem_da_tabela():
    sd = json.loads((AQUI / 'semana-aula/2026-10-26/scrapedo-citacoes.json').read_text(encoding='utf-8'))
    del sd['headers']['scrape.do-request-cost']
    r = rodada_de('2026-10-26', scrapedo=sd)
    assert r['custo']['scrapedo_fonte'] == 'tabela' and r['custo']['total'] == 6


def test_erro_do_firecrawl_nao_entra_no_historico():
    r = rodada_de('2026-10-29')
    maude = next(l for l in r['linhas'] if l['nome'].startswith('Maude'))
    assert r['problemas'] == [] and maude['preco'] == '18.02' and maude['firecrawl'] == 'preco=18.2'


def test_citacoes_vazias_quebram():
    r = rodada_de('2026-10-26', scrapedo={'data': '<html></html>', 'headers': {}, 'statusCode': 200})
    assert any(p['detalhe'] == 'citacoes: 0 citações na página; o mínimo é 8' for p in r['problemas'])


def test_semana_da_aula(tmp_path):
    codigo, saida = rodar('semana.py', 'semana-aula', '--saida', tmp_path / 's')
    assert codigo == 0 and '8 rodadas no histórico; 48 créditos em 8 rodadas montadas' in saida
    assert '2026-10-30  QUEBROU' in saida
    assert not (tmp_path / 's/historico/rodada-2026-10-30.csv').exists()
    assert rodar('semana.py', 'semana-aula', '--saida', tmp_path / 's')[0] == 3


def test_relatorio_da_semana_da_aula(tmp_path):
    rodar('semana.py', 'semana-aula', '--saida', tmp_path / 's')
    texto = relatorio.montar(tmp_path / 's')
    assert '| 2026-10-31 | 2026-10-29 | loja, página 2 | The Four Agreements: A Practical Guide to Personal Freedom | saiu da página | 17.66 |  |' in texto
    assert '| 2026-10-29 | Maude (1883-1993):She Grew Up with the country | preco | 18.2 | 18.02 |' in texto
    assert 'total: 48 créditos' in texto
