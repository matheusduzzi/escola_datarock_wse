"""O exercício da aula: o código próprio para a versão js do site.

    https://quotes.toscrape.com/js/page/1/

Abra paginas/js-page-1.html num editor de texto (não no navegador) e procure as citações. Elas estão
lá, só que não estão em nenhum div.quote.

Escreva extrair_js sem navegador: ela recebe o HTML como o requests baixa e retorna a mesma lista que
extrair_padrao retorna, na ordem da página. Cada item é um dict com:

    texto  o texto da citação, sem as aspas curvas do começo e do fim
    autor  o nome do autor
    tags   a lista das tags, na ordem da página

Se a página não tiver a lista, a função retorna uma lista vazia, sem erro, como as outras regras do
proprio.py: quem acusa é a contagem do medir.py.

Pronto quer dizer: python -m pytest test_js.py termina com 4 passed.
"""


def extrair_js(html):
    raise NotImplementedError('extrair_js ainda não foi escrita (é o exercício da aula)')
