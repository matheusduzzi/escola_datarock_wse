"""Exercício: decidir se uma rodada do Firecrawl pode entrar no monitor.

    python aceite.py saida/firecrawl-pagina-2.json

Escreva a função aceitar_rodada. Os testes estão em test_aceite.py.
"""
import json
import sys
from pathlib import Path

import comparar
import gabarito as gab

# Os tipos de erro que reprovam a rodada. titulo_cortado não está aqui de propósito.
REPROVAM = ['faltando', 'a_mais', 'repetido', 'sem_url', 'item_invalido', 'tipo_errado',
            'titulo_diferente', 'preco_diferente', 'estoque_diferente']


def aceitar_rodada(relatorio, esperados=20):
    """Recebe o relatório de comparar.comparar_livros e retorna
    {'aceita': bool, 'motivos': [...], 'avisos': [...]}.

    Regras:
    1. Gabarito vazio, ou com um número de livros diferente de `esperados`: não aceita. Motivo
       'gabarito: N livros, esperado M'. Sem gabarito certo, a comparação não prova nada.
    2. Cada tipo de REPROVAM que aparece nos erros vira um motivo 'tipo: quantidade', na ordem de
       REPROVAM. Qualquer motivo: não aceita.
    3. titulo_cortado não reprova: vira o aviso 'titulo_cortado: quantidade'. A chave é o endereço,
       e o título inteiro vem do gabarito.
    4. Um tipo que não está em REPROVAM nem é titulo_cortado também reprova, com o motivo
       'tipo desconhecido: nome'. Na dúvida, não entra.
    5. A função não altera o relatório que recebeu.
    """
    raise NotImplementedError('escreva aceitar_rodada')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print('uso: python aceite.py saida/firecrawl-pagina-N.json')
        return 2
    rodada = json.loads(Path(argv[0]).read_text(encoding='utf-8'))
    from firecrawl_livros import nome_da_pagina
    caminho = Path(__file__).resolve().parent / f'gabarito-{nome_da_pagina(rodada["url"])}.csv'
    rel = comparar.comparar_livros(gab.ler(caminho), rodada['livros'], rodada['url'])
    decisao = aceitar_rodada(rel)
    print('aceita' if decisao['aceita'] else 'não aceita')
    for m in decisao['motivos']:
        print('  motivo:', m)
    for a in decisao['avisos']:
        print('  aviso:', a)
    return 0 if decisao['aceita'] else 1


if __name__ == '__main__':
    sys.exit(main())
