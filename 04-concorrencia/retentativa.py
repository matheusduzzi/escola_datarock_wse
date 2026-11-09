"""Quando tentar de novo, quanto esperar e quando parar.

    decidir(status, tentativa, retry_after) -> segundos de espera
    levanta Parar     -> o site recusou ou pediu uma pausa longa: o crawler inteiro para
    levanta Desistir  -> essa página não melhora tentando de novo: anota e segue com as outras

status None quer dizer erro de rede (conexão caiu, tempo esgotado).
"""
import email.utils
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

# Vale tentar de novo: limite de taxa e falhas do servidor que costumam passar.
REPETE = {429, 500, 502, 503, 504}
# Recusa: tentar de novo é insistir contra um não. O crawler para tudo.
PARA_TUDO = {401, 403, 407}


class Parar(Exception):
    """O crawler inteiro precisa parar."""


class Desistir(Exception):
    """Essa página falhou de vez nessa rodada."""


def ler_retry_after(valor, agora=None):
    """Segundos pedidos pelo cabeçalho Retry-After, ou None se não veio ou não dá para ler.

    O cabeçalho vem em segundos ("120") ou como data HTTP ("Sun, 08 Nov 2026 20:00:00 GMT").
    """
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor.isdigit():
        return float(valor)
    try:
        quando = email.utils.parsedate_to_datetime(valor)
    except (TypeError, ValueError, IndexError):
        return None
    if quando is None or quando.tzinfo is None:
        return None
    agora = time.time() if agora is None else agora
    return max(0.0, quando.timestamp() - agora)


@dataclass
class Politica:
    base: float = 1.0          # espera depois da primeira falha, em segundos
    teto: float = 30.0         # a espera nunca passa disso
    tentativas: int = 4        # pedidos por página, contando o primeiro
    maior_pausa: float = 120.0 # Retry-After acima disso: parar e voltar depois
    sorteio: Callable[[], float] = field(default=random.random)

    def espera(self, tentativa):
        """Espera crescente com sorteio: entre metade e o valor cheio de base * 2^(tentativa-1)."""
        cheia = min(self.teto, self.base * 2 ** (tentativa - 1))
        return cheia / 2 + self.sorteio() * cheia / 2

    def decidir(self, status, tentativa, retry_after=None, agora=None):
        """Segundos de espera antes do próximo pedido. Retry-After de um 429 ou 503 vale mais que a conta."""
        if status in PARA_TUDO:
            raise Parar(f'{status}: o site recusou o pedido. Pare e veja a aula sobre bloqueio.')
        if status is not None and status not in REPETE:
            raise Desistir(f'{status}: tentar de novo não muda a resposta')
        if tentativa >= self.tentativas:
            raise Desistir(f'{status or "erro de rede"} em {tentativa} tentativas')
        pedido = ler_retry_after(retry_after, agora) if status in (429, 503) else None
        if pedido is not None:
            if pedido > self.maior_pausa:
                raise Parar(f'{status}: o site pediu {pedido:.0f} s de pausa. Rode de novo depois disso.')
            return pedido
        return self.espera(tentativa)


def segundos(valor: Optional[float]) -> str:
    return f'{valor:.1f}'.replace('.', ',') + ' s'
