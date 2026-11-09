"""Chamada ao scrape.do com a chave lida da variável de ambiente SCRAPEDO_TOKEN.

Os scripts dessa aula usam só isto aqui. A chave nunca aparece na tela: nem na
saída normal, nem numa mensagem de erro.

    from scrapedo import chamar
    r = chamar('https://httpbin.org/ip')                 # datacenter, rotação, 1 crédito
    r = chamar('https://httpbin.org/ip', pais='br')      # IP do Brasil
    r = chamar('https://httpbin.org/ip', sessao=1234)    # mesmo IP por alguns minutos
    r = chamar('https://quotes.toscrape.com/js/', render=True)  # com navegador, 5 créditos
"""
import json
import os
import pathlib
import re

import requests

API = 'https://api.scrape.do/'
KIT = pathlib.Path(__file__).resolve().parent.parent

# O que cada código do próprio scrape.do quer dizer (página Status Codes da documentação).
AVISOS = {
    400: 'pedido mal formado: veja a mensagem do scrape.do abaixo',
    401: 'sem créditos ou conta suspensa: olhe o painel do scrape.do',
    429: 'pedidos rápidos demais para o limite de conexões da sua conta: espere e mande um por vez',
    502: 'o pedido falhou no scrape.do: tente de novo daqui a pouco',
}


class ChaveVazia(Exception):
    pass


class ErroScrapeDo(Exception):
    pass


def ler_env(caminho):
    """Lê KEY=valor do .env do kit, sem biblioteca extra."""
    valores = {}
    if caminho.is_file():
        for linha in caminho.read_text(encoding='utf-8').splitlines():
            linha = linha.strip()
            if linha and not linha.startswith('#') and '=' in linha:
                nome, valor = linha.split('=', 1)
                valores[nome.strip()] = valor.strip().strip('"').strip("'")
    return valores


def ler_chave(env=None, arquivo=None):
    """A variável de ambiente vale primeiro; se ela não existe, o .env da raiz do kit."""
    env = os.environ if env is None else env
    chave = env.get('SCRAPEDO_TOKEN', '').strip()
    if not chave:
        chave = ler_env(arquivo or KIT / '.env').get('SCRAPEDO_TOKEN', '')
    if not chave:
        raise ChaveVazia('SCRAPEDO_TOKEN está vazia. Copie a chave do painel do scrape.do '
                         'para o .env da raiz do kit (veja o README do kit).')
    return chave


def esconder(texto, chave):
    """Troca a chave por *** em qualquer texto, inclusive na URL de uma mensagem de erro."""
    return texto.replace(chave, '***') if chave else texto


def montar_parametros(url, render=False, pais=None, sessao=None, residencial=False):
    """Os parâmetros do pedido, sem a chave. Só entra o que foi pedido."""
    if not url.startswith(('http://', 'https://')):
        raise ValueError(f'url precisa começar com http:// ou https://: {url!r}')
    p = {'url': url}
    if render:
        p['render'] = 'true'
    if residencial:
        p['super'] = 'true'
    if pais is not None:
        if not re.fullmatch(r'[A-Za-z]{2}', str(pais)):
            raise ValueError(f'país é o código de duas letras, como br ou us: {pais!r}')
        p['geoCode'] = str(pais).lower()
    if sessao is not None:
        if isinstance(sessao, bool) or not isinstance(sessao, int) or not 0 <= sessao <= 1_000_000:
            raise ValueError(f'sessão é um número inteiro de 0 a 1000000: {sessao!r}')
        p['sessionId'] = str(sessao)
    return p


def numero(valor):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


class Resposta:
    def __init__(self, status, texto, cabecalhos):
        self.status = status
        self.texto = texto
        self.custo = numero(cabecalhos.get('Scrape.do-Request-Cost'))
        self.saldo = numero(cabecalhos.get('Scrape.do-Remaining-Credits'))

    @property
    def aviso(self):
        return AVISOS.get(self.status, '')


def chamar(url, render=False, pais=None, sessao=None, residencial=False, timeout=90,
           get=None, env=None):
    """Um pedido pelo scrape.do. Retorna Resposta com status, texto, custo e saldo.

    O timeout padrão do scrape.do é de 60 segundos; o nosso espera um pouco mais,
    para receber a resposta dele em vez de desistir antes.
    """
    chave = ler_chave(env)
    parametros = dict(token=chave, **montar_parametros(url, render, pais, sessao, residencial))
    get = get or requests.get
    try:
        r = get(API, params=parametros, timeout=timeout)
    except requests.RequestException as erro:
        # A mensagem do requests traz a URL inteira, com a chave dentro.
        raise ErroScrapeDo(esconder(f'{type(erro).__name__}: {erro}', chave)) from None
    return Resposta(r.status_code, esconder(r.text, chave), r.headers)


def ip_do_httpbin(texto):
    """O campo origin do httpbin.org/ip. Pode vir com mais de um IP separado por vírgula."""
    try:
        return json.loads(texto)['origin']
    except (ValueError, KeyError, TypeError):
        return None


def mascarar(ip):
    """Mostra só o primeiro número do IP: 203.0.113.7 vira 203.x.x.x."""
    partes = (ip or '').split(',')[0].strip().split('.')
    return partes[0] + '.x.x.x' if len(partes) == 4 else '(sem IP)'
