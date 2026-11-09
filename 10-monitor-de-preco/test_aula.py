"""Testes da aula «Monitor de preço: agendar, comparar e avisar». Rodam sem internet e sem o n8n.

    python -m pytest test_aula.py

Os fluxos com defeito daqui são cópias do monitor.json com uma mudança cada, feitas no próprio teste.
Nenhum deles foi exportado de um n8n.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
HIST = AQUI.parent / 'historico'
MONITOR = json.loads((AQUI / 'monitor.json').read_text(encoding='utf-8'))


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=AQUI, capture_output=True, text=True)
    return r.returncode, r.stdout


def conferir(fluxo, tmp_path):
    arq = tmp_path / 'fluxo.json'
    arq.write_text(json.dumps(fluxo, ensure_ascii=False), encoding='utf-8')
    return rodar('conferir_monitor.py', arq)


def no(fluxo, nome):
    return next(n for n in fluxo['nodes'] if n['name'] == nome)


def test_monitor_do_kit_esta_pronto():
    codigo, saida = rodar('conferir_monitor.py', 'monitor.json')
    assert codigo == 0
    assert saida.strip().endswith('monitor pronto')
    assert 'FALTA' not in saida


def test_codigo_dos_nos_igual_aos_arquivos_js():
    for nome, arquivo in [('Uma linha por livro', 'uma-linha-por-livro.js'),
                          ('Comparar com a anterior', 'comparar-com-a-anterior.js'),
                          ('Montar o aviso', 'montar-o-aviso.js')]:
        assert no(MONITOR, nome)['parameters']['jsCode'] == (AQUI / arquivo).read_text(encoding='utf-8').rstrip('\n')


def test_trocar_a_anterior_antes_de_ler_e_acusado():
    codigo, saida = rodar('conferir_monitor.py', 'teste/monitor-grava-antes-de-ler.json')
    assert codigo == 1
    assert 'trocada ANTES de ser lida' in saida


def test_sem_agenda_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    del f['connections']['Todo dia às 7h']
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA gatilho agendado' in saida


def test_agenda_desligada_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    no(f, 'Todo dia às 7h')['disabled'] = True
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA gatilho agendado' in saida


def test_sem_fuso_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    del f['settings']['timezone']
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'vale o da instância' in saida


def test_sem_data_no_nome_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    no(f, 'Guardar a rodada do dia')['parameters']['fileName'] = '/home/node/.n8n-files/monitor/rodadas/rodada.csv'
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA um nó de arquivo que guarda a rodada do dia' in saida


def test_troca_em_outro_caminho_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    no(f, 'Trocar a rodada anterior')['parameters']['fileName'] = '/home/node/.n8n-files/monitor/anterior.csv'
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA um nó de arquivo que troca a rodada anterior' in saida


def test_aviso_no_falso_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    f['connections']['Mudou algo?']['main'] = [[], [{'node': 'Montar o aviso', 'type': 'main', 'index': 0}]]
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA um If sobre "mudancas"' in saida


def test_aviso_sem_if_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    f['nodes'] = [n for n in f['nodes'] if n['name'] != 'Mudou algo?']
    f['connections']['Trocar a rodada anterior'] = {'main': [[{'node': 'Montar o aviso', 'type': 'main', 'index': 0}]]}
    del f['connections']['Mudou algo?']
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA um If sobre "mudancas"' in saida


def test_arquivo_que_nao_e_fluxo(tmp_path):
    arq = tmp_path / 'x.json'
    arq.write_text('[1, 2, 3]', encoding='utf-8')
    codigo, saida = rodar('conferir_monitor.py', arq)
    assert codigo == 2 and 'não é um fluxo' in saida


def test_comparar_as_duas_rodadas_do_kit():
    codigo, saida = rodar('comparar.py', HIST / 'rodada-2026-11-05.csv', HIST / 'rodada-2026-11-06.csv')
    assert codigo == 0
    linhas = [l.strip() for l in saida.splitlines() if l.startswith('  ')]
    assert linhas == [
        'Soumission: o preço caiu de £50.10 para £45.10',
        'Sharp Objects: ficou sem estoque',
        'Set Me Free: o preço caiu de £17.46 para £15.99',
        'Olio: o preço subiu de £23.88 para £26.40',
    ]
    assert 'livros só na anterior: 1; só na de hoje: 0' in saida


def test_comparar_rodada_com_ela_mesma_nao_avisa():
    codigo, saida = rodar('comparar.py', HIST / 'rodada-2026-11-06.csv', HIST / 'rodada-2026-11-06.csv')
    assert codigo == 0 and 'nada mudou: o monitor não avisa' in saida


def test_comparar_preco_igual_com_zero_diferente():
    from comparar import comparar
    antes = [{'rodada': 'a', 'url': 'u', 'titulo': 't', 'preco': '50.1', 'disponivel': 'sim'}]
    hoje = [{'rodada': 'b', 'url': 'u', 'titulo': 't', 'preco': '50.10', 'disponivel': 'sim'}]
    assert comparar(antes, hoje) == []


def test_comparar_arquivo_que_nao_e_rodada(tmp_path):
    arq = tmp_path / 'x.csv'
    arq.write_text('a,b\n1,2\n', encoding='utf-8')
    codigo, saida = rodar('comparar.py', arq, HIST / 'rodada-2026-11-06.csv')
    assert codigo == 2 and 'não é uma rodada' in saida


def test_aviso_com_erros_acusa_os_tres():
    codigo, saida = rodar('conferir_aviso.py', HIST / 'rodada-2026-11-06.csv', 'teste/rodada-2026-11-08.csv',
                          'teste/aviso-com-erros.json')
    assert codigo == 1
    assert '3 erro(s)' in saida
    for tipo in ('faltando', 'a_mais', 'repetido'):
        assert re.search(rf'^\s+{tipo}\s', saida, flags=re.M)


def test_aviso_certo_passa(tmp_path):
    aviso = json.loads((AQUI / 'teste/aviso-com-erros.json').read_text(encoding='utf-8'))
    from comparar import comparar, ler_rodada
    aviso[0]['mudancas'] = comparar(ler_rodada(HIST / 'rodada-2026-11-06.csv'), ler_rodada(AQUI / 'teste/rodada-2026-11-08.csv'))
    arq = tmp_path / 'aviso.json'
    arq.write_text(json.dumps(aviso, ensure_ascii=False), encoding='utf-8')
    codigo, saida = rodar('conferir_aviso.py', HIST / 'rodada-2026-11-06.csv', 'teste/rodada-2026-11-08.csv', arq)
    assert codigo == 0 and 'mudanças pela regra: 4; no aviso: 4' in saida


def test_sem_mudanca_e_com_aviso_e_erro(tmp_path):
    arq = tmp_path / 'aviso.json'
    arq.write_text(json.dumps([{'assunto': 'x', 'texto': 'x', 'mudancas': []}]), encoding='utf-8')
    hoje = AQUI / 'teste/rodada-2026-11-08.csv'
    codigo, saida = rodar('conferir_aviso.py', hoje, hoje, arq)
    assert codigo == 1 and 'aviso_sem_mudanca' in saida
    codigo, saida = rodar('conferir_aviso.py', hoje, hoje, 'nenhum')
    assert codigo == 0 and '0 erro(s)' in saida


def test_mudou_e_nao_houve_aviso_e_erro():
    codigo, saida = rodar('conferir_aviso.py', HIST / 'rodada-2026-11-06.csv', 'teste/rodada-2026-11-08.csv', 'nenhum')
    assert codigo == 1 and 'sem_aviso' in saida


@pytest.mark.parametrize('arquivo', ['monitor.json', 'teste/monitor-grava-antes-de-ler.json'])
def test_fluxos_da_pasta_sem_chave(arquivo):
    codigo, saida = rodar(AQUI.parent / 'conferir_exportacao.py', arquivo)
    assert codigo == 0 and 'nada parecido com chave' in saida
