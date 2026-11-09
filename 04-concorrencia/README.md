# Aula 04: Concorrência controlada, filas e retentativas

Os comandos rodam de dentro dessa pasta, com o ambiente do kit ativado (veja o README da raiz do kit). Nenhum script dessa aula usa chave.

| Arquivo | Para que serve |
|---|---|
| `fila.py` | o motor: fila de páginas, trabalhadores, limite de pedidos ao mesmo tempo, gravação da página inteira e retomada |
| `retentativa.py` | quando tentar de novo, quanto esperar e quando parar |
| `catalogo.py` | o crawler das 50 páginas de lista de `books.toscrape.com` |
| `contar.py` | conta as linhas de um CSV e as chaves repetidas |
| `test_fila.py` | os testes da aula, sem internet |
| `citacoes.py` | o exercício: as 100 citações da API de `quotes.toscrape.com` (você escreve `chave` e `extrair`) |
| `test_citacoes.py` | os testes do exercício |
| `paginas/citacoes/` | as 10 páginas da API de citações, salvas em 08/11/2026, para os testes |

## Rodar

```
python -m pytest test_fila.py
python catalogo.py --limite 1 --do-zero
python catalogo.py --limite 5 --do-zero
python catalogo.py --limite 5 --do-zero --parar-depois 20
python catalogo.py --limite 5
python contar.py saida/catalogo.csv url
```

`test_fila.py` termina com `17 passed`. O `catalogo.py` grava em `saida/catalogo.csv` e marca as páginas feitas em `saida/catalogo.progresso`. Sem `--do-zero`, ele continua de onde parou. A pasta `saida/` é sua: não vai para o Git.

O limite vai de 1 a 20. Os sites de treino aguentam isso. Num site de outra pessoa, comece por 1 ou 2 e leia o que ele permite antes de subir.

Códigos de saída do `catalogo.py` e do `citacoes.py`: 0 tudo certo; 1 alguma página falhou e fica para a próxima rodada; 2 opção errada; 3 parou de propósito com `--parar-depois`; 4 o site recusou (401, 403, 407) ou pediu uma pausa longa demais, e o crawler parou.

## O exercício

```
python -m pytest test_citacoes.py
```

Antes de você escrever as duas funções, o resultado é `8 failed`. Pronto é `8 passed`. Depois, as rodadas ao vivo estão no enunciado do exercício.

As páginas de `paginas/citacoes/` vêm do site de treino da Zyte. A licença de redistribuição ainda vai ser definida: use para estudar e não publique em outro lugar.
