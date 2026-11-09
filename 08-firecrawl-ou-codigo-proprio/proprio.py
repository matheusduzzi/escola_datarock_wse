"""O código próprio: tira texto, autor e tags das citações de uma página do quotes.toscrape.com.

O site de treino tem a mesma lista de citações em três versões. Para essa aula, cada versão faz o papel
de um layout novo do mesmo site:

    padrao  https://quotes.toscrape.com/page/1/           cada citação num bloco div.quote
    tabela  https://quotes.toscrape.com/tableful/page/1/  uma tabela; texto e autor na mesma célula
    js      https://quotes.toscrape.com/js/page/1/        a lista vem num script e o navegador monta a página

Cada função recebe o HTML como o requests baixa e retorna uma lista de dicts com texto, autor e tags.
O texto sai sem as aspas curvas do começo e do fim. Página que não tem o formato esperado retorna lista
vazia: quem olha a contagem é o medir.py.
"""
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

from proprio_js import extrair_js

AQUI = Path(__file__).resolve().parent
VERSOES = {
    'padrao': 'https://quotes.toscrape.com/page/1/',
    'tabela': 'https://quotes.toscrape.com/tableful/page/1/',
    'js': 'https://quotes.toscrape.com/js/page/1/',
}


def limpar(texto):
    """Espaços em sequência viram um; tira as aspas curvas das pontas."""
    return re.sub(r'\s+', ' ', texto).strip().strip('“”').strip()


def extrair_padrao(html):
    """A versão padrão: um div.quote por citação. É o código que já rodava antes da mudança."""
    sopa = BeautifulSoup(html, 'lxml')
    citacoes = []
    for bloco in sopa.select('div.quote'):
        citacoes.append({
            'texto': limpar(bloco.select_one('span.text').get_text()),
            'autor': bloco.select_one('small.author').get_text(strip=True),
            'tags': [a.get_text(strip=True) for a in bloco.select('a.tag')],
        })
    return citacoes


def extrair_tabela(html):
    """A versão em tabela. Escrita depois que a versão padrão parou de funcionar nela.

    Não tem classe nenhuma para segurar. Cada citação ocupa duas linhas da tabela: uma célula com
    o texto e "Author: Nome", e embaixo uma célula que começa com "Tags:". A coluna da direita, com as
    dez tags mais usadas, também tem links de tag; ela fica de fora porque não começa com "Tags:".
    """
    sopa = BeautifulSoup(html, 'lxml')
    citacoes = []
    for celula in sopa.select('td'):
        conteudo = celula.get_text(' ', strip=True)
        if ' Author: ' in conteudo:
            texto, autor = conteudo.rsplit(' Author: ', 1)
            citacoes.append({'texto': limpar(texto), 'autor': autor.strip(), 'tags': []})
        elif conteudo.startswith('Tags:') and citacoes:
            citacoes[-1]['tags'] = [a.get_text(strip=True) for a in celula.select('a')]
    return citacoes


EXTRATORES = {'padrao': extrair_padrao, 'tabela': extrair_tabela, 'js': extrair_js}


def ler_salva(versao):
    """A página 1 salva no kit em 08/11/2026."""
    return (AQUI / 'paginas' / f'{versao}-page-1.html').read_bytes().decode('utf-8')


def baixar(url):
    """Um pedido ao site, como no curso Web scraping do zero, com 1 segundo de espera depois."""
    import requests
    r = requests.get(url, headers={'User-Agent': 'curso-web-scraping-em-escala (estudo)'}, timeout=20)
    r.raise_for_status()
    texto = r.content.decode('utf-8')
    return texto


def rodar(versao, extrator, ao_vivo=False, espera=1.0):
    """Baixa (ou lê a salva) e extrai, medindo o tempo. Retorna (citações, segundos, erro)."""
    inicio = time.perf_counter()
    html = baixar(VERSOES[versao]) if ao_vivo else ler_salva(versao)
    try:
        citacoes = extrator(html)
        erro = ''
    except NotImplementedError as e:
        citacoes, erro = [], f'não escrita: {e}'
    segundos = time.perf_counter() - inicio
    if ao_vivo:
        time.sleep(espera)
    return citacoes, segundos, erro
