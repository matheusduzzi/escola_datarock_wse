"""Testes da aula, sem internet, sem chave e sem o SDK.

Onde o teste precisa de uma resposta do Firecrawl, ele usa um cliente falso que responde com as citações
do gabarito. Esses testes mostram o que os scripts fazem com uma resposta; não medem o Firecrawl.
"""
import json
from types import SimpleNamespace

import pytest

import firecrawl_citacoes as fc
import medir
import proprio

GAB = medir.ler_gabarito()


def contar(citacoes):
    return medir.comparar(GAB, citacoes)


# O código próprio nas três versões salvas.

def test_padrao_na_versao_padrao_traz_30_de_30():
    r = contar(proprio.extrair_padrao(proprio.ler_salva('padrao')))
    assert (r['extraidas'], r['total_certos'], r['a_mais']) == (10, 30, 0)


@pytest.mark.parametrize('versao', ['tabela', 'js'])
def test_padrao_nas_outras_versoes_volta_vazio_sem_erro(versao):
    assert proprio.extrair_padrao(proprio.ler_salva(versao)) == []


def test_tabela_na_versao_tabela_traz_30_de_30_sem_as_dez_tags_do_lado():
    citacoes = proprio.extrair_tabela(proprio.ler_salva('tabela'))
    r = contar(citacoes)
    assert (r['extraidas'], r['total_certos']) == (10, 30)
    assert citacoes[0]['tags'] == ['change', 'deep-thoughts', 'thinking', 'world']


def test_tabela_na_versao_padrao_volta_vazio():
    assert proprio.extrair_tabela(proprio.ler_salva('padrao')) == []


def test_o_gabarito_tem_10_citacoes_e_texto_sem_aspas_curvas():
    assert len(GAB) == 10
    assert all(not g['texto'].startswith('“') and not g['texto'].endswith('”') for g in GAB)


# A comparação.

def test_aspas_e_espacos_nas_pontas_contam_como_texto_certo():
    item = dict(GAB[0], texto='  “' + GAB[0]['texto'].replace(' ', '  ') + '” ')
    r = contar([item])
    assert r['certos'] == {'texto': 1, 'autor': 1, 'tags': 1} and r['faltando'] == 9


def test_autor_com_o_rotulo_da_tabela_conta_errado():
    r = contar([dict(GAB[0], autor='Author: Albert Einstein')])
    assert r['certos']['autor'] == 0 and ('autor diferente' in {t for t, _ in r['erros']})


def test_tags_fora_de_ordem_contam_erradas():
    r = contar([dict(GAB[0], tags=list(reversed(GAB[0]['tags'])))])
    assert r['certos']['tags'] == 0


def test_texto_diferente_vira_uma_a_mais_e_uma_faltando():
    r = contar([dict(GAB[0], texto=GAB[0]['texto'].replace('thinking', 'thought'))] + GAB[1:])
    assert (r['a_mais'], r['faltando'], r['total_certos']) == (1, 1, 27)


def test_citacao_repetida_nao_conta_duas_vezes():
    r = contar(GAB + [GAB[3]])
    assert (r['repetidas'], r['total_certos']) == (1, 30)


# O script do Firecrawl, com um cliente falso.

class ClienteFalso:
    """Não é o Firecrawl: responde com o gabarito e o status que o teste pedir."""

    def __init__(self, status=200, json_dado=None, erro=None):
        self.status, self.json_dado, self.erro, self.pedidos = status, json_dado, erro, []

    def scrape(self, url, **opcoes):
        self.pedidos.append((url, opcoes))
        if self.erro:
            raise self.erro
        dado = {'citacoes': GAB} if self.json_dado is None else self.json_dado
        return SimpleNamespace(json=dado, metadata=SimpleNamespace(status_code=self.status, credits_used=5))


CHAVE = {'FIRECRAWL_API_KEY': 'fc-123456789teste'}


def test_sem_chave_para_com_codigo_2_e_nada_gravado(tmp_path):
    cliente = ClienteFalso()
    codigo = fc.main(['--saida', str(tmp_path / 'saida')], cliente=cliente, ambiente={},
                     arquivo_env=tmp_path / 'nao-existe')
    assert codigo == 2 and cliente.pedidos == [] and not (tmp_path / 'saida').exists()


def test_chave_de_outro_servico_para_com_codigo_2(tmp_path):
    codigo = fc.main(['--saida', str(tmp_path)], cliente=ClienteFalso(), ambiente={'FIRECRAWL_API_KEY': 'sk-abc'},
                     arquivo_env=tmp_path / 'x')
    assert codigo == 2


def test_sem_o_sdk_sai_com_codigo_3(tmp_path, monkeypatch):
    def sem_sdk(chave):
        raise ImportError('firecrawl')
    monkeypatch.setattr(fc, 'criar_cliente', sem_sdk)
    assert fc.main(['--saida', str(tmp_path)], ambiente=CHAVE, arquivo_env=tmp_path / 'x') == 3


def test_tres_versoes_com_o_mesmo_esquema_e_o_tempo_medido(tmp_path):
    cliente = ClienteFalso()
    assert fc.main(['--saida', str(tmp_path)], cliente=cliente, ambiente=CHAVE, arquivo_env=tmp_path / 'x') == 0
    assert [u for u, _ in cliente.pedidos] == list(proprio.VERSOES.values())
    formatos = [o['formats'] for _, o in cliente.pedidos]
    assert all(f == formatos[0] for f in formatos) and formatos[0][0]['schema'] is fc.ESQUEMA
    gravado = json.loads((tmp_path / 'firecrawl-tabela.json').read_text(encoding='utf-8'))
    assert gravado['creditos'] == 5 and isinstance(gravado['segundos'], float)
    assert medir.main(['firecrawl', '--saida', str(tmp_path)]) == 0


def test_o_relogio_mede_so_a_chamada():
    tempos = iter([10.0, 12.5])
    r = fc.raspar('padrao', ClienteFalso(), relogio=lambda: next(tempos))
    assert r['segundos'] == 2.5


def test_status_404_nao_grava_aquela_versao(tmp_path):
    codigo = fc.main(['--versao', 'js', '--saida', str(tmp_path)], cliente=ClienteFalso(status=404),
                     ambiente=CHAVE, arquivo_env=tmp_path / 'x')
    assert codigo == 1 and not (tmp_path / 'firecrawl-js.json').exists()


def test_json_sem_a_lista_nao_grava(tmp_path):
    codigo = fc.main(['--versao', 'padrao', '--saida', str(tmp_path)], cliente=ClienteFalso(json_dado={'quotes': []}),
                     ambiente=CHAVE, arquivo_env=tmp_path / 'x')
    assert codigo == 1 and not (tmp_path / 'firecrawl-padrao.json').exists()


def test_erro_do_sdk_nao_mostra_a_chave(capsys, tmp_path):
    erro = RuntimeError('Unauthorized: Bearer fc-123456789teste')
    fc.main(['--versao', 'padrao', '--saida', str(tmp_path)], cliente=ClienteFalso(erro=erro),
            ambiente=CHAVE, arquivo_env=tmp_path / 'x')
    saida = capsys.readouterr().out
    assert 'fc-123456789teste' not in saida and 'Bearer ***' in saida


def test_medir_firecrawl_sem_nenhum_arquivo_sai_com_2(tmp_path):
    assert medir.main(['firecrawl', '--saida', str(tmp_path)]) == 2


def test_medir_firecrawl_com_campo_errado_sai_com_1(tmp_path):
    ruim = [dict(g, autor='Author: ' + g['autor']) for g in GAB]
    for versao in proprio.VERSOES:
        (tmp_path / f'firecrawl-{versao}.json').write_text(
            json.dumps({'citacoes': ruim, 'segundos': 3.0, 'creditos': 5}), encoding='utf-8')
    assert medir.main(['firecrawl', '--saida', str(tmp_path)]) == 1
