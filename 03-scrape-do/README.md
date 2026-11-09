# Aula 03. Rotacionador de proxy como serviço: scrape.do

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado. A chave do scrape.do fica no `.env` da raiz do kit, na linha `SCRAPEDO_TOKEN=` (veja o README do kit). Se você preferir, exporte a variável no terminal: ela vale antes do `.env`.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `scrapedo.py` | a chamada ao scrape.do: lê a chave, monta os parâmetros, lê o custo e o saldo dos cabeçalhos e esconde a chave de qualquer mensagem |
| `dez_ips.py` | dez chamadas a `httpbin.org/ip`, direto ou pelo scrape.do, com país e sessão fixa |
| `citacoes_js.py` | baixa `quotes.toscrape.com/js/` direto, pelo scrape.do sem navegador ou com `render=true`, e conta as citações |
| `escalada.py` | o exercício: tentar sem navegador e ligar o `render=true` só quando precisa |
| `test_scrapedo.py` | testes da aula, sem internet e sem chave |
| `test_escalada.py` | testes do exercício; falham até você escrever a função |
| `anotacao-custos.md` | a tabela em que você anota o custo de cada modo e o saldo do painel |
| `paginas/quotes-js.html` | a página `quotes.toscrape.com/js/` salva em 08/11/2026, como chega sem navegador |

## Primeiro, sem gastar crédito

```
python -m pytest test_scrapedo.py
python dez_ips.py --direto
python citacoes_js.py --modo direto
```

O `pytest` precisa terminar com `13 passed`. O `dez_ips.py --direto` mostra o seu IP dez vezes, só com o primeiro número. O `citacoes_js.py --modo direto` mostra `caixas div.quote no HTML: 0` e `citações na lista do script: 10`.

## Depois, pelo scrape.do

```
python dez_ips.py
python dez_ips.py --pais br -n 3
python dez_ips.py --pais us -n 3
python dez_ips.py --sessao 1234 -n 3
python citacoes_js.py --modo sem-render
python citacoes_js.py --modo render
```

Pela tabela de custos do scrape.do lida em 08/11/2026, essas seis rodadas gastam 25 créditos: 10 + 3 + 3 + 3 + 1 + 5. O exercício gasta mais 7. O valor que vale é o do cabeçalho `Scrape.do-Request-Cost`, que os scripts mostram em cada linha.

Cada rodada do `dez_ips.py` grava `saida/ips-<modo>.csv`. A pasta `saida/` está no `.gitignore`.

## Se der erro

| O que aparece | O que fazer |
|---|---|
| `SCRAPEDO_TOKEN está vazia`, código 2 | cole a chave no `.env` da raiz do kit e rode de novo |
| `401` | sem créditos ou conta suspensa: olhe o painel |
| `429` | pedidos rápidos demais para a sua conta: rode um script por vez |
| `502` | o pedido falhou no scrape.do e não custou crédito: tente de novo daqui a pouco |
| `parou: ConnectionError ...` | a internet caiu ou o endereço está bloqueado na sua rede; a chave aparece como `***` |

A página salva é do site de treino `quotes.toscrape.com`, feito pela Zyte para quem aprende a raspar. Use para estudar e não publique em outro lugar.
