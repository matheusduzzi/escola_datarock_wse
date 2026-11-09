"""Testes do exercício «Preço que mudou demais». Rodam sem internet e sem o n8n.

    python -m pytest test_exercicio.py

Leem três arquivos que você salva nessa pasta depois de executar o monitor no n8n:
- meu-fluxo.json: o fluxo exportado, com a terceira regra;
- meu-alerta.json: a saída do nó "Montar o alerta de quebra" na execução com exercicio/pagina-com-imposto.html;
- meu-aviso.json: a saída do nó "Montar o aviso" na execução com o site, com a rodada de 06/11 como anterior.
"""
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FLUXO = AQUI / 'meu-fluxo.json'
ALERTA = AQUI / 'meu-alerta.json'
AVISO = AQUI / 'meu-aviso.json'


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=AQUI, capture_output=True, text=True)
    return r.returncode, r.stdout


def item(caminho):
    dado = json.loads(caminho.read_text(encoding='utf-8'))
    dado = dado[0] if isinstance(dado, list) and dado else dado
    return dado.get('json', dado)


def test_fluxo_continua_monitor_com_trava():
    assert FLUXO.is_file(), 'salve o fluxo exportado como meu-fluxo.json nessa pasta'
    for args in (['conferir_monitor.py', FLUXO], ['conferir_trava.py', FLUXO], [AQUI.parent / 'conferir_exportacao.py', FLUXO]):
        codigo, saida = rodar(*args)
        assert codigo == 0, saida


def test_terceira_regra_entre_a_comparacao_e_as_gravacoes():
    codigo, saida = rodar('conferir_trava.py', FLUXO, '--depois-da-comparacao')
    assert codigo == 0, saida


def test_alerta_do_imposto_bate_com_a_regra():
    assert ALERTA.is_file(), 'copie a saída do nó "Montar o alerta de quebra" para meu-alerta.json'
    codigo, saida = rodar('conferir_alerta.py', 'exercicio/pagina-com-imposto.html', ALERTA,
                          '--anterior', '../historico/rodada-2026-11-05.csv')
    assert codigo == 0, saida


def test_alerta_saiu_do_fluxo_exportado():
    fluxo = json.loads(FLUXO.read_text(encoding='utf-8'))
    codigos = ' '.join(n['parameters'].get('jsCode', '') for n in fluxo['nodes'] if n['type'].endswith('.code'))
    assert any(q + 'mudou_demais' + q in codigos for q in ("'", '"', '`')), (
        'o código dos nós do meu-fluxo.json não tem a regra "mudou_demais": o alerta veio de outro fluxo?')


def test_dia_normal_nao_foi_barrado():
    assert AVISO.is_file(), 'copie a saída do nó "Montar o aviso" da execução com o site para meu-aviso.json'
    aviso = item(AVISO)
    assert 'quebrou' not in aviso.get('assunto', ''), 'meu-aviso.json é um alerta, não o aviso do dia normal'
    precos = [m for m in aviso.get('mudancas', []) if m.get('tipo') == 'preco']
    assert precos, 'o aviso do dia normal precisa ter as mudanças de preço da rodada de 06/11 para o site'
