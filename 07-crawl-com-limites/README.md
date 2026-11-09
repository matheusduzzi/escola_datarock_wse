# 07. Crawl de um site inteiro com limites

Os comandos rodam de dentro dessa pasta. A chave do Firecrawl fica no `.env` da raiz do kit, na linha `FIRECRAWL_API_KEY`, como na aula 06.

## O que tem aqui

| Arquivo | Para que serve | Gasta crédito? |
|---|---|---|
| `grafo-loja.json` | o mapa da loja de treino feito pelo nosso crawler em 08/11/2026: cada página e os links dela | não |
| `inventario.py` | resume o grafo; com `--ao-vivo`, percorre a loja de novo (cerca de 1.200 pedidos, uns 25 minutos) | não |
| `filtros/` | três filtros de crawl da categoria Travel, do mais ingênuo ao certo | |
| `simular.py` | diz o que um filtro visitaria, aplicando as regras da documentação ao grafo | não |
| `mapa.py` | chama o map do Firecrawl na loja e compara com o grafo | 1 por chamada |
| `crawl_categoria.py` | roda o crawl de um filtro, acompanha o status e grava o resultado | 1 por página |
| `fora_do_filtro.py` | separa os endereços que o crawl não visitou, com o motivo | não |
| `loja.py` | o tipo de cada endereço da loja e a leitura do grafo | não |
| `plano.py` e `plano-mystery.json` | o exercício: um plano de crawl para a categoria Mystery | não |
| `test_crawl.py` | os testes da aula: rodam sem internet, sem chave e sem o SDK | não |
| `test_plano.py` | os testes do exercício: falham até você escrever o plano | não |
| `anotacao.md` | onde você anota os números das suas rodadas | |

## Ordem

```
python inventario.py
python simular.py filtros/travel-1-padrao.json
python simular.py filtros/travel-2-sem-profundidade.json
python simular.py filtros/travel-3-profundidade-1.json
python mapa.py
python crawl_categoria.py filtros/travel-3-profundidade-1.json
python fora_do_filtro.py filtros/travel-3-profundidade-1.json saida/crawl-travel-3-profundidade-1.json --mapa saida/mapa.json
python -m pytest test_crawl.py
```

O `mapa.py` custa 1 crédito e o crawl do filtro 3 custa 12. Rode os filtros 1 e 2 no Firecrawl só se quiser ver com os próprios olhos: o 2 pode gastar até 50.

Os arquivos que os scripts gravam vão para `saida/`. Não publique a sua `saida/` com a chave em lugar nenhum: os scripts não gravam a chave, mas olhe o arquivo antes de mandar para alguém.

## O grafo da loja

O `grafo-loja.json` saiu do `inventario.py --ao-vivo` em 08/11/2026, com 0,25 segundo entre os pedidos. A loja é de treino, feita pela Zyte para quem aprende a raspar, e pode mudar. Se um número da aula não bater com o seu, rode `python inventario.py --ao-vivo` e compare o resumo. Ele grava em `grafo-loja-ao-vivo.json` e não apaga o arquivo do kit.
