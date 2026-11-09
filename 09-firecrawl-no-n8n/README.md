# 09. Firecrawl no n8n

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado. Os fluxos você importa no seu n8n.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `fluxo-no-firecrawl.json` | fluxo de três nós com o nó do Firecrawl: gatilho manual, scrape da página 1 da loja com o esquema dos livros, e o nó Code que faz um item por livro |
| `fluxo-http-request.json` | o mesmo fluxo com o HTTP Request no lugar do nó do Firecrawl, chamando a API do Firecrawl direto |
| `um-item-por-livro.js` | o código do nó Code, igual ao que está dentro dos dois fluxos, para ler com calma |
| `conferir_fluxo.py` | lê um fluxo exportado e diz se ele raspa a loja pelo Firecrawl, com credencial e sem chave escrita |
| `conferir_saida.py` | compara a saída do nó Code com o gabarito, livro a livro |
| `gabarito.py` | o crawler próprio das páginas 1 e 2 da loja; grava os dois gabaritos |
| `gabarito-pagina-1.csv`, `gabarito-pagina-2.csv` | os gabaritos, gerados das páginas salvas |
| `paginas/` | as páginas 1 e 2 da loja de treino, salvas |
| `teste/saida-com-erros.json` | uma saída montada à mão, com cinco erros de propósito, para ver o comparador funcionando. Não é saída do n8n |
| `test_aula.py` | os testes da aula, sem internet, sem chave e sem o n8n |
| `test_exercicio.py` | os testes do exercício |
| `anotacao.md` | onde você anota a sua execução e os créditos |

Os dois fluxos vêm sem credencial. Quem escolhe a credencial é você, no n8n, e a chave fica guardada lá.

## Os comandos da aula

```
python conferir_fluxo.py fluxo-no-firecrawl.json
python ../conferir_exportacao.py fluxo-http-request.json
python conferir_saida.py teste/saida-com-erros.json
python -m pytest test_aula.py
```

O `conferir_fluxo.py` com o fluxo da pasta mostra uma linha `FALTA`, a da credencial, e sai com código 1. O `conferir_saida.py` com a saída de teste mostra 5 erros e sai com código 1. Os testes da aula terminam com `20 passed`.

Depois de executar o fluxo no n8n, copie a saída do nó "Um item por livro" na visão JSON para `saida/pagina-1.json` e rode:

```
python conferir_saida.py saida/pagina-1.json
```

Cada execução do fluxo faz um scrape com JSON: 5 créditos pela tabela de cobrança do Firecrawl lida em 08/11/2026 (1 da página e 4 do JSON). A aula roda uma página e o exercício duas: 15 créditos se cada execução der certo de primeira. Veja o saldo no painel antes de começar.

## O exercício

```
python -m pytest test_exercicio.py
```

Antes de você salvar `meu-fluxo.json` e `minha-saida.json` nessa pasta, os testes terminam com `4 failed`. Pronto quer dizer `4 passed`.

## Os dados

As páginas de `paginas/` foram baixadas de `books.toscrape.com`, a página 1 em 08/11/2026 e a página 2 em 07/11/2026. A loja foi feita pela Zyte para quem está aprendendo a raspar e avisa na própria página que preços e notas foram sorteados. Se o site mudar, `python gabarito.py --ao-vivo` refaz os dois gabaritos com o site de agora e avisa o que mudou. A licença de redistribuição das páginas salvas ainda vai ser definida: use para estudar e não publique em outro lugar.

O `saida/` é seu: ele guarda o que você copiou das suas execuções.
