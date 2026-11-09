"""Testes da aula «Saber quando a raspagem quebrou». Rodam sem internet e sem o n8n.

    python -m pytest test_aula.py

Os fluxos e páginas com defeito daqui são cópias do monitor-com-trava.json e da página salva com uma
mudança cada, feitas no próprio teste. Nenhum deles foi exportado de um n8n.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
PAGINA = AQUI.parent / 'paginas/books/index.html'
MONITOR = json.loads((AQUI / 'monitor-com-trava.json').read_text(encoding='utf-8'))
QUEBRAS = {
    'layout-novo.html': ['0 livros na página; o mínimo é 16'],
    'pela-metade.html': ['8 livros na página; o mínimo é 16'],
    'preco-por-javascript.html': ['20 de 20 livros sem preço (100%)'],
    'um-livro-sem-preco.html': ['as listas vieram com tamanhos diferentes: 20 títulos, 19 preços, '
                                '20 disponibilidades e 20 endereços'],
    'estoque-em-portugues.html': ['20 de 20 livros sem disponibilidade (100%)'],
}


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=AQUI, capture_output=True, text=True)
    return r.returncode, r.stdout


def conferir(fluxo, tmp_path):
    arq = tmp_path / 'fluxo.json'
    arq.write_text(json.dumps(fluxo, ensure_ascii=False), encoding='utf-8')
    return rodar('conferir_trava.py', arq)


def no(fluxo, nome):
    return next(n for n in fluxo['nodes'] if n['name'] == nome)


def para(nome):
    return [{'node': nome, 'type': 'main', 'index': 0}]


# O fluxo

def test_monitor_com_trava_esta_pronto():
    codigo, saida = rodar('conferir_trava.py', 'monitor-com-trava.json')
    assert codigo == 0 and saida.strip().endswith('trava pronta') and 'FALTA' not in saida
    codigo, saida = rodar('conferir_monitor.py', 'monitor-com-trava.json')
    assert codigo == 0 and saida.strip().endswith('monitor pronto')


def test_codigo_dos_nos_igual_aos_arquivos_js():
    for nome, arquivo in [('Checar a saúde da rodada', 'checar-a-saude.js'),
                          ('Uma linha por livro', 'uma-linha-por-livro.js'),
                          ('Comparar com a anterior', 'comparar-com-a-anterior.js'),
                          ('Montar o aviso', 'montar-o-aviso.js'),
                          ('Montar o alerta de quebra', 'montar-o-alerta.js')]:
        assert no(MONITOR, nome)['parameters']['jsCode'] == (AQUI / arquivo).read_text(encoding='utf-8').rstrip('\n')


def test_monitor_da_aula_10_nao_tem_trava():
    codigo, saida = rodar('conferir_trava.py', 'teste/monitor-sem-trava.json')
    assert codigo == 1 and 'FALTA nó Code depois da raspagem' in saida


def test_trava_pendurada_do_lado_e_acusada():
    codigo, saida = rodar('conferir_trava.py', 'teste/trava-pendurada-do-lado.json')
    assert codigo == 1 and 'grava sem passar pela trava: Guardar a rodada do dia, Trocar a rodada anterior' in saida


def test_alerta_que_segue_para_gravar_e_acusado(tmp_path):
    f = copy.deepcopy(MONITOR)
    f['connections']['Montar o alerta de quebra'] = {'main': [para('Parar com erro') + para('Uma linha por livro')]}
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'a saída de quebra grava' in saida


def test_if_com_as_saidas_trocadas_e_acusado(tmp_path):
    f = copy.deepcopy(MONITOR)
    f['connections']['A raspagem quebrou?']['main'].reverse()
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'a saída de quebra grava' in saida


def test_condicao_igual_a_zero_tambem_vale(tmp_path):
    f = copy.deepcopy(MONITOR)
    cond = no(f, 'A raspagem quebrou?')['parameters']['conditions']['conditions'][0]
    cond['operator']['operation'] = 'equals'
    f['connections']['A raspagem quebrou?']['main'].reverse()
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 0, saida


def test_sem_stop_and_error_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    f['nodes'] = [n for n in f['nodes'] if n['name'] != 'Parar com erro']
    del f['connections']['Montar o alerta de quebra']
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA trava da página: um Stop and Error' in saida


def test_trava_desligada_falta(tmp_path):
    f = copy.deepcopy(MONITOR)
    no(f, 'A raspagem quebrou?')['disabled'] = True
    codigo, saida = conferir(f, tmp_path)
    assert codigo == 1 and 'FALTA um If sobre "problemas"' in saida


def test_arquivo_que_nao_e_fluxo(tmp_path):
    arq = tmp_path / 'x.json'
    arq.write_text('[1, 2, 3]', encoding='utf-8')
    codigo, saida = rodar('conferir_trava.py', arq)
    assert codigo == 2 and 'não é um fluxo' in saida


# As regras na página

def test_pagina_salva_passa():
    codigo, saida = rodar('checar_pagina.py', PAGINA)
    assert codigo == 0 and 'rodada boa: pode gravar' in saida


@pytest.mark.parametrize('pagina,detalhes', QUEBRAS.items())
def test_cada_quebra_dispara(pagina, detalhes):
    codigo, saida = rodar('checar_pagina.py', f'quebras/{pagina}')
    assert codigo == 1 and 'a rodada não deve ser gravada' in saida
    assert [l.removeprefix('QUEBROU ') for l in saida.splitlines() if l.startswith('QUEBROU')] == detalhes


def test_numeros_iguais_aos_do_no():
    js = (AQUI / 'checar-a-saude.js').read_text(encoding='utf-8')
    import checar_pagina
    assert f'CONTAGEM_MINIMA = {checar_pagina.CONTAGEM_MINIMA};' in js
    assert f'MAX_VAZIOS = {checar_pagina.MAX_VAZIOS};' in js


def pagina_com(tmp_path, funcao):
    arq = tmp_path / 'pagina.html'
    arq.write_text(funcao(PAGINA.read_text(encoding='utf-8')), encoding='utf-8')
    return arq


def sem_preco(n):
    return lambda html: re.sub(r'<p class="price_color">£\d+\.\d{2}</p>', '<p class="price_color"></p>', html, count=n)


def so_os_primeiros(n):
    artigo = re.compile(r'<li class="col-xs-6[^"]*">\s*<article class="product_pod">.*?</article>\s*</li>', re.S)

    def corta(html):
        for a in artigo.findall(html)[n:]:
            html = html.replace(a, '', 1)
        return html
    return corta


def test_dois_precos_vazios_passam_tres_nao(tmp_path):
    assert rodar('checar_pagina.py', pagina_com(tmp_path, sem_preco(2)))[0] == 0
    codigo, saida = rodar('checar_pagina.py', pagina_com(tmp_path, sem_preco(3)))
    assert codigo == 1 and '3 de 20 livros sem preço (15%)' in saida


def test_dezesseis_livros_passam_quinze_nao(tmp_path):
    assert rodar('checar_pagina.py', pagina_com(tmp_path, so_os_primeiros(16)))[0] == 0
    codigo, saida = rodar('checar_pagina.py', pagina_com(tmp_path, so_os_primeiros(15)))
    assert codigo == 1 and '15 livros na página; o mínimo é 16' in saida


def test_preco_em_outro_formato_fica_vazio():
    from checar_pagina import ler_estoque, ler_preco
    assert ler_preco('£51.77') == '51.77' and ler_preco('Â£51.77') == '51.77'
    assert ler_preco('51,77 €') == '' and ler_preco('') == ''
    assert ler_estoque('In stock') == 'sim' and ler_estoque('Out of stock') == 'nao'
    assert ler_estoque('Em estoque') == ''


# O alerta

def test_alerta_errado_acusa_os_dois():
    codigo, saida = rodar('conferir_alerta.py', 'quebras/preco-por-javascript.html', 'teste/alerta-errado.json')
    assert codigo == 1 and '2 erro(s)' in saida
    assert re.search(r'^\s+faltando\s+vazios \(preco\)', saida, flags=re.M)
    assert re.search(r'^\s+a_mais\s+contagem', saida, flags=re.M)


def test_alerta_certo_passa(tmp_path):
    from checar_pagina import checar, listas_da_pagina
    html = (AQUI / 'quebras/preco-por-javascript.html').read_text(encoding='utf-8')
    arq = tmp_path / 'alerta.json'
    arq.write_text(json.dumps([{'assunto': 'x', 'texto': 'x', 'problemas': checar(listas_da_pagina(html))[1]}],
                              ensure_ascii=False), encoding='utf-8')
    codigo, saida = rodar('conferir_alerta.py', 'quebras/preco-por-javascript.html', arq)
    assert codigo == 0 and '0 erro(s)' in saida


def test_quebra_sem_alerta_e_erro():
    codigo, saida = rodar('conferir_alerta.py', 'quebras/pela-metade.html', 'nenhum')
    assert codigo == 1 and 'sem_alerta' in saida


def test_pagina_boa_com_alerta_e_erro():
    codigo, saida = rodar('conferir_alerta.py', PAGINA, 'teste/alerta-errado.json')
    assert codigo == 1 and 'alerta_sem_quebra' in saida
    codigo, saida = rodar('conferir_alerta.py', PAGINA, 'nenhum')
    assert codigo == 0 and '0 erro(s)' in saida


@pytest.mark.parametrize('arquivo', ['monitor-com-trava.json', 'teste/trava-pendurada-do-lado.json'])
def test_fluxos_da_pasta_sem_chave(arquivo):
    codigo, saida = rodar(AQUI.parent / 'conferir_exportacao.py', arquivo)
    assert codigo == 0 and 'nada parecido com chave' in saida
