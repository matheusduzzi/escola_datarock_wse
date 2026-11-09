# Quanto custou cada modo

Data da rodada: ____

Saldo no painel do scrape.do antes da primeira rodada: ____

| Rodada | Comando | Chamadas | IPs diferentes | Custo por chamada (cabeçalho) | Total pelo cabeçalho | Saldo no painel depois |
|---|---|---|---|---|---|---|
| Direto | `python dez_ips.py --direto` | 10 | | 0 | 0 | não muda |
| Rotação | `python dez_ips.py` | 10 | | | | |
| País Brasil | `python dez_ips.py --pais br -n 3` | 3 | | | | |
| País Estados Unidos | `python dez_ips.py --pais us -n 3` | 3 | | | | |
| Sessão fixa | `python dez_ips.py --sessao 1234 -n 3` | 3 | | | | |
| /js sem navegador | `python citacoes_js.py --modo sem-render` | 1 | não se aplica | | | |
| /js com navegador | `python citacoes_js.py --modo render` | 1 | não se aplica | | | |
| Exercício: página inicial | `python escalada.py https://quotes.toscrape.com/ div.quote` | | não se aplica | | | |
| Exercício: /js | `python escalada.py https://quotes.toscrape.com/js/ div.quote` | | não se aplica | | | |

Caixas `div.quote` em /js: sem navegador ____, com navegador ____.

A soma dos cabeçalhos bate com a queda do saldo no painel? ____ Se não bate, o que mais gastou crédito? ____
