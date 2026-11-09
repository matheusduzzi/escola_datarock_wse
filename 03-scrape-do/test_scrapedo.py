"""Testes da aula. Rodam sem internet e sem chave: onde precisa, o scrape.do é trocado por um falso.

    python -m pytest test_scrapedo.py

Precisa terminar com 13 passed.
"""
import pathlib
import sys

import pytest
import requests

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import citacoes_js  # noqa: E402
import dez_ips  # noqa: E402
import scrapedo  # noqa: E402

CHAVE = 'chave-de-teste-0123456789abcdef'
PAGINA_JS = (AQUI / 'paginas/quotes-js.html').read_text(encoding='utf-8')


def test_render_so_entra_quando_pedido():
    assert scrapedo.montar_parametros('https://httpbin.org/ip') == {'url': 'https://httpbin.org/ip'}
    assert scrapedo.montar_parametros('https://quotes.toscrape.com/js/', render=True)['render'] == 'true'


def test_pais_vira_geocode_em_minusculas():
    assert scrapedo.montar_parametros('https://httpbin.org/ip', pais='BR')['geoCode'] == 'br'


@pytest.mark.parametrize('pais', ['bra', 'b', '12', ''])
def test_pais_invalido_para_antes_do_pedido(pais):
    with pytest.raises(ValueError):
        scrapedo.montar_parametros('https://httpbin.org/ip', pais=pais)


def test_sessao_fora_da_faixa_para_antes_do_pedido():
    assert scrapedo.montar_parametros('https://httpbin.org/ip', sessao=0)['sessionId'] == '0'
    for errada in (-1, 1_000_001, True, '12'):
        with pytest.raises(ValueError):
            scrapedo.montar_parametros('https://httpbin.org/ip', sessao=errada)


def test_chave_vazia_para_antes_do_pedido(tmp_path):
    with pytest.raises(scrapedo.ChaveVazia):
        scrapedo.ler_chave(env={}, arquivo=tmp_path / '.env')
    vazio = tmp_path / '.env'
    vazio.write_text('SCRAPEDO_TOKEN=\n', encoding='utf-8')
    with pytest.raises(scrapedo.ChaveVazia):
        scrapedo.ler_chave(env={}, arquivo=vazio)


def test_chave_nao_aparece_na_mensagem_de_erro():
    def get_que_cai(url, params, timeout):
        raise requests.ConnectionError(f'Max retries exceeded with url: /?token={params["token"]}&url=x')
    with pytest.raises(scrapedo.ErroScrapeDo) as erro:
        scrapedo.chamar('https://httpbin.org/ip', get=get_que_cai, env={'SCRAPEDO_TOKEN': CHAVE})
    assert CHAVE not in str(erro.value) and '***' in str(erro.value)


def test_custo_e_saldo_vem_dos_cabecalhos():
    class R:
        status_code, text = 200, '{"origin": "203.0.113.7"}'
        headers = {'Scrape.do-Request-Cost': '1', 'Scrape.do-Remaining-Credits': '990'}
    r = scrapedo.chamar('https://httpbin.org/ip', get=lambda *a, **k: R(), env={'SCRAPEDO_TOKEN': CHAVE})
    assert (r.status, r.custo, r.saldo) == (200, 1, 990)
    assert scrapedo.ip_do_httpbin(r.texto) == '203.0.113.7'
    assert scrapedo.mascarar('203.0.113.7') == '203.x.x.x'


def test_pagina_js_salva_nao_tem_caixas_mas_tem_a_lista():
    assert citacoes_js.contar_caixas(PAGINA_JS) == 0
    dados = citacoes_js.citacoes_do_script(PAGINA_JS)
    assert len(dados) == 10 and dados[0]['author']['name'] == 'Albert Einstein'


def test_dez_ips_conta_os_diferentes(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(dez_ips, 'AQUI', tmp_path)
    ips = iter(['203.0.113.1', '203.0.113.2', '203.0.113.2'])

    def falso(url, pais=None, sessao=None):
        return scrapedo.Resposta(200, '{"origin": "%s"}' % next(ips), {'Scrape.do-Request-Cost': '1'})
    codigo = dez_ips.main(['-n', '3', '--pausa', '0'], env={'SCRAPEDO_TOKEN': CHAVE}, chamar=falso)
    saida = capsys.readouterr().out
    assert codigo == 0
    assert '3 chamadas, 3 com resposta, 2 IPs diferentes, 3 créditos pelo cabeçalho' in saida
    assert (tmp_path / 'saida/ips-scrape-do.csv').is_file()


def test_dez_ips_direto_conta_o_ip_inteiro_e_mostra_mascarado(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(dez_ips, 'AQUI', tmp_path)
    ips = iter(['203.0.113.1', '203.0.113.2', '203.0.113.2'])

    class R:
        def __init__(self):
            self.status_code, self.text = 200, '{"origin": "%s"}' % next(ips)
    codigo = dez_ips.main(['--direto', '-n', '3', '--pausa', '0'], get_direto=lambda *a, **k: R())
    saida = capsys.readouterr().out
    assert codigo == 0
    assert '3 chamadas, 3 com resposta, 2 IPs diferentes, 0 crédito (sem proxy)' in saida
    assert '203.0.113' not in saida and saida.count('203.x.x.x') == 3
    csv_texto = (tmp_path / 'saida/ips-direto.csv').read_text(encoding='utf-8')
    assert '203.0.113' not in csv_texto and 'ip_inteiro' not in csv_texto
