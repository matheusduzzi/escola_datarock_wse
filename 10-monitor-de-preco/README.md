# 10. Monitor de preço: agendar, comparar e avisar

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado. O fluxo você importa no seu n8n.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `monitor.json` | o monitor: gatilho às 7h (e um manual), baixa a página 1 da loja, guarda a rodada, compara com a anterior e monta o aviso só quando algo mudou |
| `uma-linha-por-livro.js`, `comparar-com-a-anterior.js`, `montar-o-aviso.js` | o código dos três nós Code, igual ao que está dentro do fluxo, para ler com calma |
| `comparar.py` | compara duas rodadas em CSV com a mesma regra do nó "Comparar com a anterior" |
| `conferir_monitor.py` | lê um fluxo exportado e diz se ele tem agenda, fuso, memória, comparação e aviso só quando muda |
| `conferir_aviso.py` | compara o aviso que o n8n montou com o que a regra diz que mudou |
| `teste/monitor-grava-antes-de-ler.json` | o monitor com a troca da rodada anterior antes da leitura, errado de propósito |
| `teste/rodada-2026-11-08.csv`, `teste/aviso-com-erros.json` | uma rodada e um aviso montados para ver o comparador funcionando; o aviso tem três erros de propósito. Não são saída do n8n |
| `exercicio/anterior.csv` | a rodada anterior do exercício: a de 06/11 com um livro da página 2 a mais |
| `test_aula.py`, `test_exercicio.py` | os testes da aula e do exercício, sem internet e sem o n8n |
| `anotacao.md` | onde você anota as execuções do exercício |

As duas rodadas de preço do kit ficam em `../historico/`.

## Preparar a pasta do monitor

```
mkdir -p monitor/rodadas
cp ../historico/rodada-2026-11-06.csv monitor/ultima-rodada.csv
```

A pasta `monitor` é montada dentro do n8n em `/home/node/.n8n-files/monitor`. O comando Docker está na seção 3 da aula.

## Os comandos da aula

```
python conferir_monitor.py monitor.json
python comparar.py ../historico/rodada-2026-11-05.csv ../historico/rodada-2026-11-06.csv
python conferir_aviso.py ../historico/rodada-2026-11-06.csv teste/rodada-2026-11-08.csv teste/aviso-com-erros.json
python ../conferir_exportacao.py monitor.json
python -m pytest test_aula.py
```

O `conferir_monitor.py` com o fluxo da pasta termina com `monitor pronto` e código 0. O `comparar.py` mostra 4 mudanças. O `conferir_aviso.py` com o aviso de teste mostra 3 erros e sai com código 1. Os testes da aula terminam com `21 passed`.

Depois de executar o monitor no n8n, copie a saída do nó "Montar o aviso" na visão JSON para `saida/aviso-1.json` e o arquivo de `monitor/rodadas/` para `saida/rodada-1.csv`, e rode:

```
python conferir_aviso.py ../historico/rodada-2026-11-06.csv saida/rodada-1.csv saida/aviso-1.json
```

## O exercício

```
python -m pytest test_exercicio.py
```

Antes de você salvar `meu-fluxo.json`, `minha-rodada.csv` e `meu-aviso.json` nessa pasta, os testes terminam com `4 failed`. Pronto quer dizer `4 passed`.

## Os dados

As rodadas de `../historico/` partem da página 1 da loja de treino `books.toscrape.com`, salva em 07/11/2026. A de 06/11 tem cinco diferenças feitas de propósito. Em 08/11/2026, a página 1 do site estava igual à rodada de 05/11. A loja foi feita pela Zyte para quem está aprendendo a raspar, e os preços dela foram sorteados. Se o site mudar, o aviso da sua execução muda junto: o `conferir_aviso.py` refaz a regra com a rodada que o seu monitor gravou.

As pastas `monitor/` e `saida/` são suas: elas guardam o que o seu n8n gravou e o que você copiou dele.
