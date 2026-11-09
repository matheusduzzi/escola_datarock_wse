# 01. Por que raspagem é bloqueada e onde está o limite

Arquivos da aula «Por que raspagem é bloqueada e onde está o limite». Os comandos rodam de dentro dessa pasta.

| Arquivo | Para que serve |
|---|---|
| `quadro-sinais.md` | o modelo do quadro dos cinco sinais e das cinco situações do exercício |
| `ver_resposta.py` | mostra o que o site respondeu: código, desvios, endereço final, tamanho e `Retry-After` |

`ver_resposta.py` usa o `requests` do `requirements.txt` do kit. Ele espera 1 segundo entre os pedidos e se apresenta no `User-Agent` com o nome do curso. Troque `seu-email` no começo do arquivo por um contato seu antes de usar fora dos sites de treino. Exemplos:

```
python ver_resposta.py https://httpbin.org/status/429
python ver_resposta.py --procurar 'class="quote"' https://quotes.toscrape.com/ https://quotes.toscrape.com/js/
```

Com `--procurar TEXTO`, ele conta quantas vezes o texto aparece no HTML que chegou. Sem endereço, mostra o jeito de usar e sai com código 2.

Ele só mostra a resposta. Quem diz qual é o sinal e o que fazer é você, com o quadro da aula. Use só nos sites de treino do curso e no `httpbin.org`.
