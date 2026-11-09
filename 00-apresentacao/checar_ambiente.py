"""Mostra a versão do Python, das bibliotecas e se as chaves estão no .env.

Nunca mostra a chave: só diz se ela está lá e como começa.

    python checar_ambiente.py

Sai com 0 quando o Python e as bibliotecas batem com o requirements.txt e as duas
chaves estão preenchidas. Sai com 1 e diz o que falta, se não.
"""
import importlib.metadata as md
import pathlib
import sys

KIT = pathlib.Path(__file__).resolve().parent.parent
CHAVES = {'SCRAPEDO_TOKEN': 'aula 03', 'FIRECRAWL_API_KEY': 'aula 06'}


def fixadas():
    pares = {}
    for linha in (KIT / 'requirements.txt').read_text().splitlines():
        linha = linha.split('#')[0].strip()
        if '==' in linha:
            nome, versao = linha.split('==')
            pares[nome] = versao
    return pares


def ler_env(caminho):
    """Lê KEY=valor do .env sem depender de biblioteca (o .env pode existir antes do pip)."""
    valores = {}
    if caminho.is_file():
        for linha in caminho.read_text(encoding='utf-8').splitlines():
            linha = linha.strip()
            if linha and not linha.startswith('#') and '=' in linha:
                chave, valor = linha.split('=', 1)
                valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def main():
    tudo_certo = True
    ok_python = sys.version_info >= (3, 10)
    tudo_certo &= ok_python
    print(f'Python {sys.version.split()[0]:<10} {"ok" if ok_python else "PRECISA DE 3.10 OU MAIS NOVO"}')
    for nome, esperada in fixadas().items():
        try:
            tem = md.version(nome)
        except md.PackageNotFoundError:
            tem = 'não instalada'
        bate = tem == esperada
        tudo_certo &= bate
        print(f'{nome:<16} {tem:<14} kit pede {esperada:<10} {"ok" if bate else "DIFERENTE"}')
    env = ler_env(KIT / '.env')
    if not (KIT / '.env').is_file():
        print('.env             não encontrado: copie .env.exemplo para .env')
    for chave, aula in CHAVES.items():
        valor = env.get(chave, '')
        tudo_certo &= bool(valor)
        estado = f'preenchida ({valor[:3]}…, {len(valor)} caracteres)' if valor else f'VAZIA (você cria na {aula})'
        print(f'{chave:<18} {estado}')
    print('tudo certo' if tudo_certo else 'falta algo: veja as linhas em maiúsculas')
    return 0 if tudo_certo else 1


if __name__ == '__main__':
    sys.exit(main())
