# Kit do curso Web scraping em escala: proxies, Firecrawl e n8n

Esse é o projeto que você usa do começo ao fim do curso. Ele tem as bibliotecas com a versão fixada, o lugar das suas chaves, um crawler de partida, páginas salvas da loja de treino, um fluxo do n8n para começar e duas rodadas de preço para o exercício de comparação.

## O que tem aqui

| Pasta ou arquivo | Para que serve |
|---|---|
| `requirements.txt` | as bibliotecas do curso, com a versão fixada |
| `.env.exemplo` | os nomes das duas chaves (scrape.do e Firecrawl); você copia para `.env` |
| `.gitignore` | deixa o `.env` fora do Git |
| `conferir_exportacao.py` | procura chave esquecida num fluxo exportado do n8n antes de você compartilhar |
| `paginas/books/` | as duas primeiras páginas da loja de treino `books.toscrape.com`, salvas |
| `n8n/monitor-partida.json` | fluxo do n8n de partida: gatilho diário, baixa a loja e tira título e preço |
| `historico/` | duas rodadas de preço da página 1 da loja, em dias seguidos, para a aula 10 |
| `00-apresentacao/` | o crawler de partida, a checagem do ambiente, os primeiros testes e as tarefas de preparação |

Cada aula que traz arquivos ganha uma pasta com o número e o nome dela, como `00-apresentacao`. Os comandos do texto da aula rodam de dentro dessa pasta. As pastas das outras aulas entram aqui conforme as aulas saem.

## Instalar

Você precisa do Python 3.10 ou mais novo. Veja a sua versão com:

```
python3 --version
```

Na pasta do kit, crie um ambiente virtual, ative e instale as bibliotecas:

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Windows, a ativação é `.venv\Scripts\activate`. Se você fez o curso Web scraping do zero e já tem o Playwright instalado lá, pode continuar usando aquele ambiente para as aulas que voltam nele.

## As chaves

Copie o arquivo de exemplo e abra o `.env` num editor:

```
cp .env.exemplo .env
```

No Windows (PowerShell): `Copy-Item .env.exemplo .env`. Cole cada chave depois do sinal de igual, sem aspas e sem espaço. Você cria a conta do scrape.do na aula 03 e a do Firecrawl na aula 06; até lá, deixe em branco.

O `.env` fica só na sua máquina. Ele está no `.gitignore` e nunca vai no fluxo exportado do n8n: no n8n, a chave entra como credencial, e o arquivo exportado guarda só o nome da credencial. Antes de mandar um fluxo para alguém, rode:

```
python conferir_exportacao.py n8n/monitor-partida.json
```

Ele sai com `nada parecido com chave` e código 0 quando está limpo, e aponta o campo quando acha algo parecido com chave, sem mostrar o valor inteiro.

## Rodar o primeiro teste

```
cd 00-apresentacao
python checar_ambiente.py
python partida.py
python -m pytest
```

`checar_ambiente.py` mostra a versão do Python e de cada biblioteca, lado a lado com a do `requirements.txt`, e diz se cada chave está preenchida, sem mostrar a chave. Enquanto as chaves estiverem em branco, ele termina com `falta algo` e código 1: é o esperado até a aula 06.

`partida.py` lê as duas páginas salvas e precisa mostrar `40 livros; primeiro: A Light in the Attic por £51.77`. Com `--ao-vivo`, ele baixa as mesmas duas páginas do site, com 1 segundo entre os pedidos. Se você tem o crawler do projeto final do Web scraping do zero, pode usar o seu no lugar desse: o curso só pede que ele devolva título, preço e disponibilidade.

O `pytest` roda sem internet e sem chave e precisa terminar com `4 passed`.

## O fluxo do n8n

Para abrir o fluxo de partida no n8n, crie um fluxo vazio, abra o menu do fluxo e use a importação de arquivo, escolhendo `n8n/monitor-partida.json`. Ele não pede credencial: baixa a página 1 da loja de treino e tira título e preço. As aulas 09 a 11 completam esse fluxo.

## Os dados

As páginas de `paginas/books/` foram baixadas de `books.toscrape.com` em 07/11/2026. A loja foi feita pela Zyte para quem está aprendendo a raspar e avisa na própria página que preços e notas foram sorteados. O site pode mudar depois dessa data: quando uma aula raspar ao vivo e o número não bater, olhe primeiro se o site mudou.

As duas rodadas de `historico/` partem da página 1 salva. A segunda tem mudanças feitas de propósito, para você achar na aula 10. Os arquivos `precos_ontem.json`, `precos_hoje.json` e `respostas_log.csv` da apresentação foram montados do mesmo jeito, só para as tarefas de preparação.

A licença de redistribuição das páginas salvas ainda vai ser definida. Use o kit para estudar e não publique essas páginas em outro lugar.

## Ajuda

Deixe um comentário na aula com o seu objetivo, o comando que você rodou, a saída que apareceu e o que já tentou. Cole a mensagem de erro inteira, sem dados pessoais e sem nenhuma chave.

## Aulas com arquivos neste kit

| Pasta | Aula |
|---|---|
| [00-apresentacao/](00-apresentacao/) | Apresentação |
| [01-sinais-de-bloqueio/](01-sinais-de-bloqueio/) | Por que raspagem é bloqueada e onde está o limite |
| [02-tipos-de-proxy/](02-tipos-de-proxy/) | Proxies: datacenter, residencial, rotação e país |
| [03-scrape-do/](03-scrape-do/) | Rotacionador de proxy como serviço: scrape.do |
| [04-concorrencia/](04-concorrencia/) | Concorrência controlada, filas e retentativas |
| [05-o-que-o-firecrawl-entrega/](05-o-que-o-firecrawl-entrega/) | O que o Firecrawl entrega |
| [06-firecrawl-em-python/](06-firecrawl-em-python/) | Firecrawl em Python: da página ao JSON com esquema |
| [07-crawl-com-limites/](07-crawl-com-limites/) | Crawl de um site inteiro com limites |
| [08-firecrawl-ou-codigo-proprio/](08-firecrawl-ou-codigo-proprio/) | Firecrawl ou código próprio |
| [09-firecrawl-no-n8n/](09-firecrawl-no-n8n/) | Firecrawl no n8n |
| [10-monitor-de-preco/](10-monitor-de-preco/) | Monitor de preço: agendar, comparar e avisar |
| [11-quando-quebrou/](11-quando-quebrou/) | Saber quando a raspagem quebrou |
| [12-projeto-final/](12-projeto-final/) | Projeto final: monitor de preços de três alvos |
