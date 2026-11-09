"""Dez chamadas a httpbin.org/ip, para ver de que IP o pedido sai.

    python dez_ips.py --direto          # sem proxy: o seu IP, dez vezes, 0 crédito
    python dez_ips.py                   # scrape.do, datacenter, um IP por pedido
    python dez_ips.py --pais br -n 3    # scrape.do, IP do Brasil
    python dez_ips.py --sessao 1234 -n 3   # scrape.do, mesmo IP nas três

O seu IP de casa sai mascarado (203.x.x.x) na tela e no CSV, mas a conta de IPs diferentes
usa o endereço inteiro. Os IPs do scrape.do saem inteiros.
Cada rodada grava saida/ips-<modo>.csv para você anotar a conta.
Sai com 0 quando todas as chamadas voltam 200, com 1 se alguma falha e com 2 sem chave.
"""
import argparse
import csv
import pathlib
import sys
import time

import requests

import scrapedo

AQUI = pathlib.Path(__file__).resolve().parent
ALVO = 'https://httpbin.org/ip'


def nome_do_modo(a):
    if a.direto:
        return 'direto'
    partes = ['scrape-do']
    if a.pais:
        partes.append(f'pais-{a.pais.lower()}')
    if a.sessao is not None:
        partes.append(f'sessao-{a.sessao}')
    return '-'.join(partes)


def rodar(a, chamar=scrapedo.chamar, get_direto=requests.get, dormir=time.sleep):
    linhas = []
    for i in range(1, a.n + 1):
        if a.direto:
            r = get_direto(ALVO, timeout=30)
            status, texto, custo, saldo = r.status_code, r.text, 0, None
        else:
            r = chamar(ALVO, pais=a.pais, sessao=a.sessao)
            status, texto, custo, saldo = r.status, r.texto, r.custo, r.saldo
        ip = scrapedo.ip_do_httpbin(texto) if status == 200 else None
        mostrar = scrapedo.mascarar(ip) if a.direto else (ip or '(sem IP)')
        extra = f'custo {custo if custo is not None else "?"}' + (f'  saldo {saldo}' if saldo is not None else '')
        print(f'{i:>2}  {status}  {mostrar:<18} {extra}')
        if status != 200 and not a.direto:
            aviso = scrapedo.AVISOS.get(status, '')
            print(f'    {aviso or "resposta inesperada"}: {texto[:200]}')
        linhas.append({'chamada': i, 'status': status, 'ip': mostrar, 'custo': custo, 'saldo': saldo,
                       'ip_inteiro': ip})
        if i < a.n:
            dormir(a.pausa)
    return linhas


def resumo(linhas, modo):
    ips = [l['ip_inteiro'] for l in linhas if l['status'] == 200]
    custos = [l['custo'] for l in linhas if l['custo'] is not None]
    saldos = [l['saldo'] for l in linhas if l['saldo'] is not None]
    texto = (f'{len(linhas)} chamadas, {len(ips)} com resposta, {len(set(ips))} IPs diferentes, '
             f'{sum(custos)} créditos pelo cabeçalho')
    if modo == 'direto':
        n = len(set(ips))
        texto = (f'{len(linhas)} chamadas, {len(ips)} com resposta, {n} IP{"" if n == 1 else "s"} '
                 f'diferente{"" if n == 1 else "s"}, 0 crédito (sem proxy)')
    if len(saldos) >= 2:
        texto += f'; saldo foi de {saldos[0]} para {saldos[-1]}'
    return texto


def main(argv=None, **injetar):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--direto', action='store_true', help='sem proxy, para comparar')
    p.add_argument('--pais', help='código de duas letras, como br ou us')
    p.add_argument('--sessao', type=int, help='número da sessão fixa, de 0 a 1000000')
    p.add_argument('-n', type=int, default=10, help='quantas chamadas (padrão 10)')
    p.add_argument('--pausa', type=float, default=1.0, help='segundos entre as chamadas (padrão 1)')
    a = p.parse_args(argv)
    if a.direto and (a.pais or a.sessao is not None):
        p.error('--direto não usa proxy: tire --pais e --sessao')
    modo = nome_do_modo(a)
    print(f'modo: {modo}, alvo: {ALVO}')
    try:
        if not a.direto:
            scrapedo.ler_chave(injetar.get('env'))
            scrapedo.montar_parametros(ALVO, pais=a.pais, sessao=a.sessao)
        linhas = rodar(a, **{k: v for k, v in injetar.items() if k != 'env'})
    except scrapedo.ChaveVazia as erro:
        print(erro)
        return 2
    except (scrapedo.ErroScrapeDo, ValueError, requests.RequestException) as erro:
        print(f'parou: {erro}')
        return 1
    print(resumo(linhas, modo))
    saida = AQUI / 'saida'
    saida.mkdir(exist_ok=True)
    with open(saida / f'ips-{modo}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['chamada', 'status', 'ip', 'custo', 'saldo'],
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(linhas)
    print(f'gravado: saida/ips-{modo}.csv')
    return 0 if all(l['status'] == 200 for l in linhas) else 1


if __name__ == '__main__':
    sys.exit(main())
