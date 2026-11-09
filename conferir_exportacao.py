"""Procura chave de API esquecida num arquivo antes de você compartilhar.

Uso, de dentro da pasta do kit:

    python conferir_exportacao.py n8n/monitor-partida.json

Sai com 0 quando não acha nada e com 1 quando acha algo que parece chave,
mostrando onde está sem mostrar o valor inteiro.
"""
import json
import pathlib
import re
import sys

# Nomes de campo que guardam segredo quando vêm com valor escrito à mão.
CAMPOS = re.compile(r'(?i)(api[_-]?key|token|secret|senha|password|authorization)')
# Formatos de chave conhecidos: Firecrawl (fc-...) e tokens longos soltos na URL.
PADROES = [
    ('chave do Firecrawl', re.compile(r'\bfc-[A-Za-z0-9]{16,}')),
    ('token na URL', re.compile(r'(?i)[?&]token=(?!\{\{)[A-Za-z0-9]{12,}')),
    ('cabeçalho Bearer', re.compile(r'(?i)bearer\s+(?!\{\{)[A-Za-z0-9._-]{16,}')),
]


def mascarar(valor):
    return valor[:4] + '…' if len(valor) > 4 else '…'


def achados_no_texto(texto):
    for nome, regra in PADROES:
        for m in regra.finditer(texto):
            yield f'{nome}: {mascarar(m.group(0))}'


def achados_nos_campos(dado, caminho='$'):
    if isinstance(dado, dict):
        # Parâmetro do HTTP Request do n8n: {"name": "token", "value": "..."}
        nome, valor = dado.get('name'), dado.get('value')
        if isinstance(nome, str) and CAMPOS.search(nome) and isinstance(valor, str) and valor and not valor.startswith('={{'):
            yield f'parâmetro {caminho} ({nome}) com valor escrito: {mascarar(valor)}'
        for chave, valor in dado.items():
            aqui = f'{caminho}.{chave}'
            # "credentials" do n8n só guarda id e nome da credencial: isso pode ir.
            if chave == 'credentials':
                continue
            if CAMPOS.search(str(chave)) and isinstance(valor, str) and valor and not valor.startswith('={{'):
                yield f'campo {aqui} com valor escrito: {mascarar(valor)}'
            yield from achados_nos_campos(valor, aqui)
    elif isinstance(dado, list):
        for i, item in enumerate(dado):
            yield from achados_nos_campos(item, f'{caminho}[{i}]')


def conferir(caminho):
    texto = pathlib.Path(caminho).read_text(encoding='utf-8')
    achados = list(achados_no_texto(texto))
    try:
        achados += list(achados_nos_campos(json.loads(texto)))
    except json.JSONDecodeError:
        pass
    return achados


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('uso: python conferir_exportacao.py ARQUIVO.json')
    achados = conferir(sys.argv[1])
    for a in achados:
        print('ATENÇÃO', a)
    print('nada parecido com chave' if not achados else f'{len(achados)} trecho(s) para apagar antes de compartilhar')
    sys.exit(1 if achados else 0)
