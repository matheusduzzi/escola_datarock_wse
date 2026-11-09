# Por onde começar

São seis tarefas curtas. Elas mostram se você já tem o que o curso pede e quais aulas vão exigir mais de você. Não tem nota. Escreva as respostas numa cópia de [minhas-respostas.md](minhas-respostas.md), em tópicos se preferir.

As tarefas 2 a 4 pedem um script pequeno. Use o que você já sabe de Python, sem pedir o código pronto para uma IA: a ideia é ver como você resolve.

## Tarefa 1: o ambiente

Siga o `README.md` do kit, crie o seu `.env` a partir do `.env.exemplo` e rode, dentro dessa pasta:

```
python checar_ambiente.py
python -m pytest
```

Cole as duas saídas na sua resposta. As chaves podem aparecer como `VAZIA` por enquanto: você cria a conta do scrape.do na aula 03 e a do Firecrawl na aula 06. Com elas vazias, a última linha diz `falta algo` e o código de saída é 1. Não é erro seu: é o esperado até a aula 06. O resto precisa sair `ok`, sem a linha `.env não encontrado`, e o `pytest` precisa terminar com `4 passed`.

## Tarefa 2: o crawler de partida

Rode o crawler que já vem no kit e grave o resultado num CSV:

```
python partida.py --csv livros.csv
```

Ele lê as duas primeiras páginas salvas da loja de treino. Escreva um script que leia `livros.csv` e mostre:

1. quantos livros vieram;
2. quantos custam mais de £50;
3. o título do livro mais barato;
4. a nota média, com duas casas.

## Tarefa 3: o que o site respondeu

O arquivo `respostas_log.csv` tem doze pedidos feitos a uma loja, um por linha, com o endereço, o código de status, o tamanho da resposta em bytes, quantos livros vieram e, quando houve desvio, o endereço final.

Responda com um script:

1. quantas respostas vieram com cada código de status;
2. qual endereço respondeu 200 e veio sem nenhum livro;
3. qual endereço foi parar na página de login;
4. quantas páginas diferentes trouxeram livros.

## Tarefa 4: o que mudou de ontem para hoje

`precos_ontem.json` e `precos_hoje.json` têm o preço de alguns livros em dois dias, com o endereço do livro como chave. Escreva um script que diga:

1. quais livros mudaram de preço, com o preço de ontem e o de hoje;
2. qual livro sumiu hoje;
3. qual livro apareceu hoje.

## Tarefa 5: um fluxo do n8n por dentro

Não precisa abrir o n8n. Abra `../n8n/monitor-partida.json` num editor de texto e responda:

1. qual nó começa o fluxo sozinho e em que hora do dia;
2. qual endereço o fluxo baixa;
3. se o arquivo tem alguma chave de API escrita nele. Rode também, da pasta do kit, `python conferir_exportacao.py n8n/monitor-partida.json` e cole a saída.

## Tarefa 6: devagar, outro proxy ou parar

Para cada situação, escolha uma resposta (ir mais devagar, usar um proxy de outro país, ou parar) e diga por quê em uma linha:

1. Você raspa a loja de treino com 20 conexões ao mesmo tempo e começa a receber 429 com o cabeçalho `Retry-After: 30`.
2. Depois de 50 páginas, um site passa a mostrar um captcha em todas as respostas.
3. Um site de passagens permite a raspagem nos termos de uso e mostra o preço da moeda do país de quem acessa. Você precisa do preço que aparece para quem está em Portugal.

## Como usar suas respostas

- A tarefa 1 travou: comece pela aula «Apresentação» com o kit aberto e deixe um comentário nela com a saída do erro.
- As tarefas 2, 3 ou 4 não saíram: o curso parte do ponto em que você já raspa com requests e lê CSV e JSON em Python. Faça antes o curso Web scraping do zero.
- A tarefa 3 deu trabalho para ler o que cada código quer dizer: é o assunto da aula 01, e a aula 11 volta nele quando a raspagem quebra sem dar erro.
- A tarefa 4 é a ideia do monitor de preço da aula 10. Se você resolveu, a aula vai ser mais sobre o n8n do que sobre a comparação.
- A tarefa 5 ficou difícil: as aulas 09 a 11 mostram cada nó que você vai usar, mas ajuda passar antes pelo curso Automação com n8n.
- Na tarefa 6 você trocou de proxy em todas: faça com calma a aula 01. Nem toda recusa se resolve com outro IP.

Depois, volte à apresentação e siga para a aula 01.
