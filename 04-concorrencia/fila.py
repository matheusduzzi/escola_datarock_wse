"""Motor da aula: uma fila de páginas, N trabalhadores, retentativa e retomada.

    stats = asyncio.run(rodar(paginas, extrair, saida, limite=5))

- paginas: lista de URLs. As que já estão no arquivo de progresso nem entram na fila.
- extrair(texto, url): devolve as linhas da página (dicionários com os campos da Saida).
- saida: Saida(csv, campos, chave). Grava a página inteira e só depois marca a página como feita.
- limite: quantos trabalhadores, ou seja, quantos pedidos ao mesmo tempo, no máximo.
"""
import asyncio
import csv
import os
import time
from pathlib import Path

import httpx

import retentativa

CABECALHO = {'User-Agent': 'curso-web-scraping-em-escala (estudo)'}


class Parou(Exception):
    """Interrupção pedida (--parar-depois): o processo para como se tivesse caído."""


class Saida:
    """CSV com as linhas e, ao lado, um arquivo .progresso com uma página feita por linha."""

    def __init__(self, caminho, campos, chave):
        self.csv = Path(caminho)
        self.progresso = self.csv.with_suffix('.progresso')
        self.campos, self.chave = list(campos), chave
        self.chaves, self.feitas = set(), set()
        self.cortadas = 0
        self.csv.parent.mkdir(parents=True, exist_ok=True)
        self._consertar_fim(self.csv)
        self._consertar_fim(self.progresso)
        if self.csv.exists() and self.csv.stat().st_size:
            with open(self.csv, newline='', encoding='utf-8') as f:
                self.chaves = {linha[chave] for linha in csv.DictReader(f)}
        if self.progresso.exists():
            self.feitas = {l for l in self.progresso.read_text(encoding='utf-8').splitlines() if l}

    def _consertar_fim(self, arquivo):
        """Se o processo caiu no meio de uma linha, corta a linha incompleta."""
        if not arquivo.exists() or not arquivo.stat().st_size:
            return
        dados = arquivo.read_bytes()
        if dados.endswith(b'\n'):
            return
        arquivo.write_bytes(dados[:dados.rfind(b'\n') + 1])
        self.cortadas += 1

    def gravar_linhas(self, linhas):
        """Acrescenta só as linhas com chave nova. Devolve (novas, repetidas)."""
        novas = []
        for linha in linhas:
            if linha[self.chave] not in self.chaves:
                self.chaves.add(linha[self.chave])
                novas.append(linha)
        vazio = not self.csv.exists() or not self.csv.stat().st_size
        with open(self.csv, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=self.campos)
            if vazio:
                w.writeheader()
            w.writerows(novas)
            f.flush()
            os.fsync(f.fileno())
        return len(novas), len(linhas) - len(novas)

    def marcar(self, pagina):
        with open(self.progresso, 'a', encoding='utf-8') as f:
            f.write(pagina + '\n')
            f.flush()
            os.fsync(f.fileno())
        self.feitas.add(pagina)

    def gravar(self, pagina, linhas):
        novas, repetidas = self.gravar_linhas(linhas)
        self.marcar(pagina)
        return novas, repetidas


def apagar(caminho):
    """Começar do zero: apaga o CSV e o progresso."""
    for p in (Path(caminho), Path(caminho).with_suffix('.progresso')):
        if p.exists():
            p.unlink()


async def rodar(paginas, extrair, saida, limite=5, politica=None, transporte=None,
                parar_depois=None, avisar=print, timeout=20.0):
    if limite < 1:
        raise ValueError('limite precisa ser pelo menos 1')
    politica = politica or retentativa.Politica()
    fila = asyncio.Queue()
    for url in paginas:
        if url not in saida.feitas:
            fila.put_nowait(url)
    st = {'na_fila': fila.qsize(), 'ja_feitas': len(paginas) - fila.qsize(), 'feitas': 0, 'novas': 0,
          'repetidas': 0, 'pedidos': 0, 'retentativas': 0, 'em_voo': 0, 'max_em_voo': 0,
          'falhas': {}, 'parada': None, 'segundos': 0.0}
    freio = {'ate': 0.0}  # um 429 (ou 503 com Retry-After) segura o crawler inteiro até esse instante
    inicio = time.perf_counter()

    async def pedir(cliente, url):
        tentativa = 0
        while True:
            tentativa += 1
            falta = freio['ate'] - time.monotonic()
            if falta > 0:
                await asyncio.sleep(falta)
            st['pedidos'] += 1
            st['em_voo'] += 1
            st['max_em_voo'] = max(st['max_em_voo'], st['em_voo'])
            try:
                r = await cliente.get(url)
                status, pausa = r.status_code, r.headers.get('Retry-After')
            except httpx.TransportError as erro:
                r, status, pausa = None, None, None
                motivo = type(erro).__name__
            finally:
                st['em_voo'] -= 1
            if status == 200:
                return r.content.decode('utf-8')
            espera = politica.decidir(status, tentativa, pausa)  # pode levantar Parar ou Desistir
            st['retentativas'] += 1
            if status == 429 or (status == 503 and retentativa.ler_retry_after(pausa) is not None):
                freio['ate'] = max(freio['ate'], time.monotonic() + espera)  # vale para todos
            avisar(f'  {curto(url)}: {status or motivo}, nova tentativa em {retentativa.segundos(espera)}')
            await asyncio.sleep(espera)

    async def trabalhador(cliente):
        while True:
            url = await fila.get()
            try:
                if st['parada']:
                    continue
                texto = await pedir(cliente, url)
                if st['parada']:
                    continue  # outro trabalhador já mandou parar: essa página fica para a próxima rodada
                novas, repetidas = saida.gravar(url, extrair(texto, url))
                st['feitas'] += 1
                st['novas'] += novas
                st['repetidas'] += repetidas
                if parar_depois and st['feitas'] >= parar_depois:
                    st['parada'] = Parou(f'parei de propósito depois de {st["feitas"]} páginas')
                    raise st['parada']
            except retentativa.Parar as erro:
                st['parada'] = st['parada'] or erro
                raise
            except retentativa.Desistir as erro:
                st['falhas'][url] = str(erro)
                avisar(f'  {curto(url)}: desisti nessa rodada ({erro})')
            finally:
                fila.task_done()

    limites = httpx.Limits(max_connections=limite, max_keepalive_connections=limite)
    async with httpx.AsyncClient(transport=transporte, limits=limites, timeout=timeout,
                                 headers=CABECALHO) as cliente:
        tarefas = [asyncio.create_task(trabalhador(cliente)) for _ in range(limite)]
        fim = asyncio.create_task(fila.join())
        try:
            while not fim.done():
                feitas, _ = await asyncio.wait(tarefas + [fim], return_when=asyncio.FIRST_COMPLETED)
                for t in feitas:
                    if t is not fim and t.exception():
                        raise t.exception()
        except (Parou, retentativa.Parar) as erro:
            st['parada'] = st['parada'] or erro
        finally:
            for t in tarefas + [fim]:
                t.cancel()
            await asyncio.gather(*tarefas, fim, return_exceptions=True)
    st['segundos'] = time.perf_counter() - inicio
    return st


def curto(url):
    return url.split('//', 1)[-1].split('/', 1)[-1] or url


def resumo(st):
    return (f'{st["feitas"]} páginas feitas, {st["novas"]} linhas novas, {st["repetidas"]} repetidas, '
            f'{st["pedidos"]} pedidos, {st["retentativas"]} retentativas, '
            f'no máximo {st["max_em_voo"]} ao mesmo tempo, {retentativa.segundos(st["segundos"])}')


def codigo_de_saida(st, avisar=print):
    """0 tudo certo; 1 páginas falharam; 3 interrupção pedida; 4 o site mandou parar."""
    if isinstance(st['parada'], Parou):
        avisar(f'{st["parada"]}. Rode o mesmo comando sem --parar-depois para continuar.')
        return 3
    if isinstance(st['parada'], retentativa.Parar):
        avisar(f'PAROU: {st["parada"]} O que já foi gravado fica no arquivo.')
        return 4
    if st['falhas']:
        avisar(f'{len(st["falhas"])} páginas falharam. Rode o mesmo comando de novo para tentar só elas.')
        return 1
    return 0
