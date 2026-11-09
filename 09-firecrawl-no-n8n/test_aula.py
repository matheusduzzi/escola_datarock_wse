"""Testes da aula: os dois verificadores e os fluxos da pasta. Sem internet, sem chave e sem o n8n.

    python -m pytest test_aula.py

Os fluxos com credencial são cópias dos fluxos da pasta com o bloco "credentials" que o n8n grava
quando você escolhe a credencial no nó. Não são exportações de um n8n de verdade.
"""
import copy
import json
from pathlib import Path

import conferir_fluxo as cf
import conferir_saida as cs
import gabarito as gab

AQUI = Path(__file__).resolve().parent
NO = json.loads((AQUI / 'fluxo-no-firecrawl.json').read_text(encoding='utf-8'))
HTTP = json.loads((AQUI / 'fluxo-http-request.json').read_text(encoding='utf-8'))
CHAVE_FALSA = 'fc-' + 'a1b2c3d4' * 4


def scrape(fluxo):
    return next(n for n in fluxo['nodes'] if cf.caminho_do_scrape(n))


def com_credencial(fluxo, tipo):
    f = copy.deepcopy(fluxo)
    scrape(f)['credentials'] = {tipo: {'id': 'Xy12AbCd34EfGh56', 'name': 'Firecrawl (conta de teste)'}}
    return f


def faltas(fluxo, paginas=1):
    texto = json.dumps(fluxo, ensure_ascii=False)
    return [frase for passou, frase in cf.conferir(fluxo, texto, paginas) if not passou]


def gravar(tmp_path, nome, dado):
    caminho = tmp_path / nome
    caminho.write_text(json.dumps(dado, ensure_ascii=False), encoding='utf-8')
    return str(caminho)


# Os fluxos da pasta.

def test_fluxos_da_pasta_so_faltam_a_credencial():
    assert faltas(NO) == ['credencial Firecrawl API escolhida no nó']
    assert faltas(HTTP) == ['credencial genérica (Bearer Auth ou Header Auth) escolhida no HTTP Request']


def test_com_a_credencial_escolhida_os_dois_caminhos_passam():
    assert faltas(com_credencial(NO, 'firecrawlApi')) == []
    assert faltas(com_credencial(HTTP, 'httpBearerAuth')) == []
    # Credencial Header Auth com o nó ainda em Bearer Auth: o n8n não usaria essa credencial.
    assert faltas(com_credencial(HTTP, 'httpHeaderAuth')) == [
        'credencial genérica (Bearer Auth ou Header Auth) escolhida no HTTP Request']


def test_header_auth_passa_quando_o_no_diz_header_auth():
    f = com_credencial(HTTP, 'httpHeaderAuth')
    scrape(f)['parameters']['genericAuthType'] = 'httpHeaderAuth'
    assert faltas(f) == []


def test_os_dois_fluxos_tem_o_mesmo_codigo_do_arquivo_js():
    js = (AQUI / 'um-item-por-livro.js').read_text(encoding='utf-8')
    for fluxo in (NO, HTTP):
        codigo = next(n for n in fluxo['nodes'] if n['name'] == 'Um item por livro')
        assert codigo['parameters']['jsCode'] == js


def test_credencial_de_outro_servico_no_no_nao_vale():
    assert 'credencial Firecrawl API escolhida no nó' in faltas(com_credencial(NO, 'httpBearerAuth'))


# O que o verificador promete pegar.

def test_chave_colada_no_cabecalho_reprova_mesmo_com_credencial():
    f = com_credencial(HTTP, 'httpBearerAuth')
    p = scrape(f)['parameters']
    p['sendHeaders'] = True
    p['headerParameters'] = {'parameters': [{'name': 'Authorization', 'value': f'Bearer {CHAVE_FALSA}'}]}
    erros = faltas(f)
    assert 'nenhum cabeçalho Authorization escrito no nó' in erros
    assert any(e.startswith('nenhuma chave escrita no arquivo') for e in erros)


def test_chave_colada_no_corpo_reprova():
    f = com_credencial(HTTP, 'httpBearerAuth')
    p = scrape(f)['parameters']
    p['jsonBody'] = p['jsonBody'].replace('"formats"', f'"api_key": "{CHAVE_FALSA}",\n  "formats"')
    assert any(e.startswith('nenhuma chave escrita no arquivo') for e in faltas(f))


def test_http_request_sem_autenticacao_reprova():
    f = com_credencial(HTTP, 'httpBearerAuth')
    scrape(f)['parameters']['authentication'] = 'none'
    assert faltas(f) == ['credencial genérica (Bearer Auth ou Header Auth) escolhida no HTTP Request']


def test_scrape_sem_o_formato_json_reprova():
    f = com_credencial(NO, 'firecrawlApi')
    scrape(f)['parameters']['scrapeOptions'] = {'options': {'formats': {'format': [{'type': 'markdown'}]}}}
    assert faltas(f) == ['formato JSON com o esquema da lista "livros"']


def test_outro_site_reprova():
    f = com_credencial(NO, 'firecrawlApi')
    scrape(f)['parameters']['url'] = 'https://example.com/'
    assert faltas(f) == ['raspa a loja de treino: https://example.com/']


def test_code_desligado_do_scrape_reprova():
    f = com_credencial(NO, 'firecrawlApi')
    f['connections'].pop(scrape(f)['name'])
    assert faltas(f) == ['nó Code ligado depois do scrape, lendo a lista "livros"']


def test_dois_nos_de_scrape_reprova():
    f = com_credencial(NO, 'firecrawlApi')
    outro = copy.deepcopy(scrape(f))
    outro['name'] = 'Raspar a página 2'
    f['nodes'].append(outro)
    assert faltas(f) == ['um nó de scrape do Firecrawl (achei 2)']


def test_arquivo_que_nao_e_fluxo_sai_com_2(tmp_path):
    assert cf.main([gravar(tmp_path, 'lista.json', [1, 2, 3])]) == 2


def test_fluxo_da_pasta_sai_com_1_e_com_credencial_sai_com_0(tmp_path):
    assert cf.main([str(AQUI / 'fluxo-no-firecrawl.json')]) == 1
    assert cf.main([gravar(tmp_path, 'f.json', com_credencial(NO, 'firecrawlApi'))]) == 0


# A saída.

def saida_do_gabarito(n=1, relativo=False):
    itens = []
    for l in gab.ler(AQUI / f'gabarito-pagina-{n}.csv'):
        url = l['url'].rsplit('/catalogue/', 1)[1] if relativo else l['url']
        itens.append({'pagina': gab.PAGINAS[n], 'titulo': l['titulo'], 'preco': l['preco'],
                      'em_estoque': l['em_estoque'], 'url': url})
    return itens


def test_gabaritos_iguais_as_paginas_salvas():
    for n, url in gab.PAGINAS.items():
        salva = gab.extrair((AQUI / 'paginas' / f'page-{n}.html').read_text(encoding='utf-8'), url)
        assert gab.ler(AQUI / f'gabarito-pagina-{n}.csv') == salva
        assert len(salva) == 20


def test_saida_igual_ao_gabarito_passa_com_endereco_relativo(tmp_path):
    assert cs.main([gravar(tmp_path, 's.json', saida_do_gabarito(1, relativo=True))]) == 0


def test_saida_de_teste_tem_os_cinco_erros():
    rel = cs.comparar(gab.ler(AQUI / 'gabarito-pagina-1.csv'),
                      json.loads((AQUI / 'teste/saida-com-erros.json').read_text(encoding='utf-8')))
    assert sorted(t for _, _, t in rel['erros']) == sorted(
        ['titulo_cortado', 'tipo_errado', 'estoque_diferente', 'repetido', 'faltando'])


def test_resposta_crua_do_scrape_no_lugar_da_saida_do_code_reprova(tmp_path):
    crua = [{'success': True, 'data': {'json': {'livros': saida_do_gabarito()}, 'metadata': {'statusCode': 200}}}]
    assert cs.main([gravar(tmp_path, 'crua.json', crua)]) == 1


def test_uma_pagina_nao_passa_quando_pede_duas(tmp_path):
    assert cs.main([gravar(tmp_path, 's.json', saida_do_gabarito(1)), '--paginas', '2']) == 1


def test_saida_que_nao_e_lista_sai_com_2(tmp_path):
    assert cs.main([gravar(tmp_path, 's.json', {'livros': []})]) == 2
