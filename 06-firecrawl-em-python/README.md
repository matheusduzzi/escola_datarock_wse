# 06. Firecrawl em Python: da página ao JSON com esquema

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `esquema.py` | o esquema dos livros (título, preço, estoque e endereço) e o prompt que vai junto |
| `firecrawl_livros.py` | chama o Firecrawl pelo SDK e grava o markdown e o JSON em `saida/` |
| `gabarito.py` | o crawler próprio: título, preço e estoque da mesma página, pela regra do `partida.py` |
| `gabarito-pagina-1.csv` | o gabarito da página 1, gerado pelo `gabarito.py` a partir da página salva |
| `comparar.py` | junta o JSON e o gabarito pelo endereço do livro e lista os erros campo a campo |
| `teste/rodada-de-teste.json` | um arquivo montado à mão, com sete erros de propósito, para ver o comparador funcionando. Não é resposta do Firecrawl |
| `test_firecrawl.py` | os testes da aula, sem internet, sem chave e sem o SDK |
| `aceite.py` e `test_aceite.py` | o exercício: a regra que decide se a rodada entra no monitor |
| `anotacao-erros.md` | onde você anota os erros e o saldo das duas páginas |
| `paginas/page-1.html` | a página 1 da loja de treino, salva em 08/11/2026 |

## Antes de rodar

O SDK é o `firecrawl-py` do `requirements.txt` da raiz do kit. A chave vai no `.env` da raiz, na linha `FIRECRAWL_API_KEY`, e começa com `fc-`. Sem ela, o `firecrawl_livros.py` para antes de qualquer pedido, com código 2.

## Os comandos da aula

```
python gabarito.py
python firecrawl_livros.py
python comparar.py teste/rodada-de-teste.json
python comparar.py saida/firecrawl-pagina-1.json
python -m pytest test_firecrawl.py
```

`gabarito.py` mostra `20 livros; 20 em estoque; primeiro: A Light in the Attic por £51.77`. O `comparar.py` com a rodada de teste mostra 7 erros e sai com código 1. Os testes da aula terminam com `20 passed`.

Cada rodada do `firecrawl_livros.py` faz um scrape com markdown e JSON: 5 créditos pela tabela de cobrança do Firecrawl lida em 08/11/2026 (1 da página e 4 do JSON). A aula e o exercício juntos rodam duas páginas, 10 créditos. Veja o saldo da sua conta no painel antes de começar.

## O exercício

```
python -m pytest test_aceite.py
```

Antes de você escrever a função, os testes terminam com `8 failed`. Pronto quer dizer `8 passed`. A parte ao vivo está no enunciado do exercício, no fim da página da aula.

## Os dados

A página de `paginas/` foi baixada de `books.toscrape.com` em 08/11/2026. A loja foi feita pela Zyte para quem está aprendendo a raspar e avisa na própria página que preços e notas foram sorteados. A licença de redistribuição da página salva ainda vai ser definida: use para estudar e não publique em outro lugar.

O `saida/` é seu: ele guarda o que os scripts gravaram nas suas rodadas.
