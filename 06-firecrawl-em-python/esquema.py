"""O esquema que o Firecrawl preenche para cada página de lista da loja de treino.

O esquema segue o JSON Schema. A lista de livros fica dentro de um objeto, como a documentação
do Firecrawl pede para extrair vários itens. Não tem minItems: a documentação avisa que ele faz
o modelo inventar item para completar a conta. Quem pede "todos" é o prompt.
"""

ESQUEMA_LIVROS = {
    'type': 'object',
    'properties': {
        'livros': {
            'type': 'array',
            'description': 'Todos os livros da lista, na ordem em que aparecem na página.',
            'items': {
                'type': 'object',
                'properties': {
                    'titulo': {
                        'type': 'string',
                        'description': 'Título do livro como aparece na lista.',
                    },
                    'preco': {
                        'type': 'number',
                        'description': 'Preço em libras, só o número, sem o símbolo. Ex.: 51.77.',
                    },
                    'em_estoque': {
                        'type': 'boolean',
                        'description': 'true se o livro aparece como "In stock"; false se não.',
                    },
                    'url': {
                        'type': 'string',
                        'description': 'Endereço do link da página do livro.',
                    },
                },
                'required': ['titulo', 'preco', 'em_estoque', 'url'],
            },
        },
    },
    'required': ['livros'],
}

PROMPT_LIVROS = 'Extraia todos os livros da lista da página, sem pular nenhum. Não invente valor que não está na página.'
