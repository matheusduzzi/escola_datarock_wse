"""Exercício: buscar a página sem navegador e ligar o render=true só quando precisa.

    python escalada.py https://quotes.toscrape.com/ div.quote
    python escalada.py https://quotes.toscrape.com/js/ div.quote

Você escreve a função coletar. Os testes de test_escalada.py dizem quando ela está pronta:

    python -m pytest test_escalada.py
"""
import sys

import scrapedo
from citacoes_js import contar_caixas


class SemDados(Exception):
    """Nem com o navegador o seletor achou o mínimo de itens."""


def coletar(url, seletor, chamar=scrapedo.chamar, minimo=1):
    """Retorna {'itens': quantos o seletor achou, 'render': se precisou do navegador,
    'custo': créditos somados pelos cabeçalhos, 'chamadas': quantos pedidos fez}.

    1. O primeiro pedido vai sem render.
    2. Resposta com status diferente de 200 levanta scrapedo.ErroScrapeDo, sem novo pedido.
    3. Se o seletor acha pelo menos `minimo` itens, para aí.
    4. Se não acha, faz um pedido com render=True. Status diferente de 200: ErroScrapeDo.
    5. Se ainda não acha, levanta SemDados. Nunca mais do que dois pedidos.

    Use contar_caixas(html, seletor) para contar. `chamar` tem a mesma assinatura
    de scrapedo.chamar: chamar(url, render=False) retorna uma Resposta.
    """
    raise NotImplementedError('é o exercício: escreva a função coletar')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    url, seletor = argv
    try:
        r = coletar(url, seletor)
    except scrapedo.ChaveVazia as erro:
        print(erro)
        return 2
    except (scrapedo.ErroScrapeDo, SemDados) as erro:
        print(f'parou: {erro}')
        return 1
    print(f'{url}: {r["itens"]} itens com {seletor}, render {"sim" if r["render"] else "não"}, '
          f'{r["chamadas"]} pedido(s), {r["custo"]} créditos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
