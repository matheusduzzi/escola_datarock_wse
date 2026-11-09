# 08. Firecrawl ou código próprio

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `paginas/` | a página 1 do quotes.toscrape.com nas três versões (padrão, tabela e js), salvas em 08/11/2026 |
| `gabarito-page-1.csv` | as 10 citações da página 1: texto, autor e tags |
| `proprio.py` | o código próprio: a regra da versão padrão e a da versão tabela |
| `proprio_js.py` | o exercício: a regra da versão js, que você escreve |
| `firecrawl_citacoes.py` | o caminho do Firecrawl: o mesmo esquema nas três versões, com o tempo medido |
| `medir.py` | conta citações e campos certos contra o gabarito, com tempo e créditos, para os dois caminhos |
| `tabela-medida.md` | a sua tabela e a sua regra |
| `test_aula.py` | os testes da aula, sem internet, sem chave e sem o SDK |
| `test_js.py` | os testes do exercício |

## Antes de rodar

O SDK é o `firecrawl-py` do `requirements.txt` da raiz do kit. A chave vai no `.env` da raiz, na linha `FIRECRAWL_API_KEY`, e começa com `fc-`. Sem ela, o `firecrawl_citacoes.py` para antes de qualquer pedido, com código 2.

## Os comandos da aula

```
python medir.py proprio --so-padrao
python medir.py proprio
python medir.py proprio --ao-vivo
python firecrawl_citacoes.py
python medir.py firecrawl
python -m pytest test_aula.py
```

Com as páginas salvas, `medir.py proprio --so-padrao` mostra 30 de 30 na versão padrão e 0 nas outras duas. `medir.py proprio` mostra 30 de 30 na padrão e na tabela, e a versão js aparece como não escrita até você fazer o exercício. Os dois saem com código 1 enquanto alguma versão não fecha 30 de 30. Os testes da aula terminam com `21 passed`.

O `firecrawl_citacoes.py` faz um scrape com JSON em cada versão: 5 créditos cada pela tabela de cobrança do Firecrawl lida em 08/11/2026, 15 nas três. Veja o saldo da sua conta no painel antes de começar.

## O exercício

```
python -m pytest test_js.py
```

Antes de você escrever a função, os testes terminam com `4 failed`. Pronto quer dizer `4 passed`. O resto do exercício está no enunciado, no fim da página da aula.

## Os dados

As páginas de `paginas/` foram baixadas de `quotes.toscrape.com` em 08/11/2026. O site foi feito pela Zyte para quem está aprendendo a raspar. O gabarito saiu da lista que a própria versão js traz no HTML, e as três versões trazem as mesmas 10 citações. A licença de redistribuição das páginas salvas ainda vai ser definida: use para estudar e não publique em outro lugar.

O `saida/` é seu: ele guarda o que os scripts gravaram nas suas rodadas.
