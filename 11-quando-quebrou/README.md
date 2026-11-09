# 11. Saber quando a raspagem quebrou

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado. O fluxo você importa no seu n8n.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `monitor-com-trava.json` | o monitor da aula 10 com a trava: checa a página antes de virar rodada e, se quebrou, alerta, termina com erro e não grava nada |
| `checar-a-saude.js`, `uma-linha-por-livro.js`, `montar-o-alerta.js` | o código dos três nós Code novos ou mudados, igual ao que está dentro do fluxo |
| `comparar-com-a-anterior.js`, `montar-o-aviso.js` | o código dos dois nós Code que vieram da aula 10, sem mudança |
| `checar_pagina.py` | aplica as regras de saúde numa página salva e diz se a rodada pode ser gravada |
| `conferir_trava.py` | lê um fluxo exportado e diz se toda gravação passa pela trava, e se a saída de quebra alerta sem gravar |
| `conferir_alerta.py` | compara o alerta que o n8n montou com o que as regras dizem sobre a mesma página |
| `conferir_monitor.py`, `comparar.py` | os da aula 10, para ver que o monitor continua inteiro |
| `quebras/` | cinco páginas quebradas de propósito, feitas a partir da página 1 salva |
| `teste/monitor-sem-trava.json` | o monitor da aula 10, para rodar nas quebras e ver o que ele faz |
| `teste/trava-pendurada-do-lado.json` | o monitor com a trava num ramo paralelo, errado de propósito |
| `teste/alerta-errado.json` | um alerta montado à mão com dois erros de propósito. Não é saída do n8n |
| `exercicio/pagina-com-imposto.html` | a página do exercício: todos os preços 20% mais altos |
| `test_aula.py`, `test_exercicio.py` | os testes da aula e do exercício, sem internet e sem o n8n |
| `anotacao.md` | onde você anota as execuções do exercício |

As rodadas de preço ficam em `../historico/` e a página 1 salva em `../paginas/books/`.

## Os comandos da aula

```
python checar_pagina.py ../paginas/books/index.html
python checar_pagina.py quebras/preco-por-javascript.html
python conferir_trava.py monitor-com-trava.json
python conferir_trava.py teste/trava-pendurada-do-lado.json
python conferir_monitor.py monitor-com-trava.json
python conferir_alerta.py quebras/preco-por-javascript.html teste/alerta-errado.json
python ../conferir_exportacao.py monitor-com-trava.json
python -m pytest test_aula.py
```

A página salva termina com `rodada boa: pode gravar` e código 0; cada página de `quebras/` termina com `a rodada não deve ser gravada` e código 1. O `conferir_trava.py` diz `trava pronta` para o fluxo da pasta e acusa 2 itens no fluxo pendurado do lado, com código 1. O `conferir_alerta.py` com o alerta de teste mostra 2 erros e sai com código 1. Os testes da aula terminam com `26 passed`.

## A quebra simulada

O monitor continua gravando na pasta `monitor` da aula 10, em `../10-monitor-de-preco/monitor`. Para o n8n baixar uma página de `quebras/`, sirva essa pasta num terminal separado:

```
python3 -m http.server 8000
```

e use `http://host.docker.internal:8000/quebras/<página>.html` no nó "Baixar a página 1" de uma segunda cópia do fluxo, que você não publica. No Linux, o contêiner precisa da opção `--add-host host.docker.internal=host-gateway`. A seção 6 da aula tem o passo a passo e o que olhar na tela.

Depois de executar, copie a saída do nó "Montar o alerta de quebra" na visão JSON para `saida/alerta-1.json` e rode:

```
python conferir_alerta.py quebras/preco-por-javascript.html saida/alerta-1.json
```

## O exercício

```
python -m pytest test_exercicio.py
```

Antes de você salvar `meu-fluxo.json`, `meu-alerta.json` e `meu-aviso.json` nessa pasta, os testes terminam com `5 failed`. Pronto quer dizer `5 passed`.

## Os dados

As páginas de `quebras/` e `exercicio/` partem da página 1 da loja de treino `books.toscrape.com`, salva em 07/11/2026, com uma mudança feita de propósito em cada uma. A loja foi feita pela Zyte para quem está aprendendo a raspar, e os preços dela foram sorteados. Em 08/11/2026, a página 1 do site estava igual à salva.

A pasta `saida/` é sua: ela guarda o que você copiou do n8n.
