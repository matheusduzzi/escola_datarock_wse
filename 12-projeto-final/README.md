# 12. Projeto final: monitor de preços de três alvos

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado. O fluxo você importa no seu n8n.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `monitor-final.json` | o monitor de três alvos: a loja pelo código próprio, as citações pelo scrape.do e a página 2 da loja pelo Firecrawl, comparada com o código próprio |
| `paginas-da-loja.js`, `ver-as-respostas.js`, `montar-a-rodada.js`, `uma-linha-por-item.js`, `comparar-com-a-anterior.js`, `montar-o-aviso.js`, `montar-o-alerta.js` | o código dos nós Code, igual ao que está dentro do fluxo |
| `monitor.py` | as mesmas regras dos nós, em Python, para rodar a semana sem o n8n |
| `semana.py` | passa uma semana de respostas salvas pelas regras do monitor e monta o histórico |
| `relatorio.py` | monta o relatório de mudanças da semana a partir do histórico |
| `conferir_fluxo.py` | lê um fluxo exportado e diz se ele tem o que o projeto pede |
| `conferir_projeto.py` | confere a pasta de entrega inteira |
| `semana-aula/` | a semana da aula: a rodada de partida e oito dias de respostas |
| `semana-exercicio/` | a semana do projeto, no mesmo formato |
| `quebra/layout-novo.html` | a página 1 com a classe dos cartões trocada, para a quebra provocada no n8n |
| `teste/monitor-gerado-por-ia.json` | o monitor com três defeitos de propósito |
| `anotacao.md` | o modelo da anotação que vai na entrega |
| `test_aula.py`, `test_exercicio.py` | os testes da aula e do projeto, sem internet e sem o n8n |

## Os comandos da aula

```
python conferir_fluxo.py monitor-final.json
python conferir_fluxo.py teste/monitor-gerado-por-ia.json
python ../conferir_exportacao.py monitor-final.json
python semana.py semana-aula --saida saida/semana-aula
python relatorio.py saida/semana-aula
python -m pytest test_aula.py
```

O `conferir_fluxo.py` acusa 2 itens no fluxo do kit, as duas credenciais, que são suas, e sai com código 1. No fluxo gerado por IA, acusa 5. O `semana.py` termina com `8 rodadas no histórico; 48 créditos em 8 rodadas montadas`. Os testes da aula terminam com `28 passed`. Se a pasta `saida/semana-aula` já existir, use `--do-zero`.

## O n8n

A memória do monitor final fica numa pasta nova, `monitor-final`, dentro dessa pasta:

```
mkdir -p monitor-final/rodadas monitor-final/custos
cp semana-aula/partida.csv monitor-final/ultima-rodada.csv
```

O contêiner precisa enxergar essa pasta. A seção 6 da aula, «O monitor no seu n8n», tem o comando.

## O projeto

```
python semana.py semana-exercicio --saida entrega/semana
python relatorio.py entrega/semana --gravar entrega/relatorio.md
python conferir_projeto.py entrega
python -m pytest test_exercicio.py
```

O enunciado está no fim da página da aula. Antes de você montar a pasta `entrega/`, os testes do projeto terminam com `6 failed`. Pronto quer dizer `6 passed`.

## Os dados

As páginas das semanas partem das páginas 1 e 2 da loja de treino `books.toscrape.com` e da página 1 da versão js de `quotes.toscrape.com`, salvas entre 07 e 08/11/2026, com mudanças feitas de propósito em alguns dias. O "Out of stock" foi escrito no lugar do "In stock", com a mesma marcação: as páginas de lista da loja não mostram livro sem estoque. A página de login é a do site de citações, baixada em 08/11/2026. As respostas do Firecrawl e do scrape.do foram montadas no formato da documentação de cada serviço, a partir dessas páginas. Não são respostas dos serviços.

A pasta `saida/` e a pasta `entrega/` são suas.
