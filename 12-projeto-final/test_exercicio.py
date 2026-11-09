"""Testes do projeto final. Rodam na pasta entrega/, que você monta (veja o enunciado).

Com o kit como vem, sem a pasta entrega/, todos falham. Pronto quer dizer 6 passed.
Não mude os testes: eles chamam o conferir_projeto.py, seção por seção.
"""
from pathlib import Path

import pytest

import conferir_projeto as cp

ENTREGA = Path(__file__).resolve().parent / 'entrega'


@pytest.mark.parametrize('secao', cp.SECOES, ids=[s.__name__.removeprefix('secao_') for s in cp.SECOES])
def test_secao(secao):
    assert ENTREGA.is_dir(), 'falta a pasta entrega/ (veja o enunciado do projeto)'
    faltando = [t for ok, t in secao(ENTREGA) if not ok]
    assert not faltando, '\n'.join(faltando)
