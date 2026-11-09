// Código do nó Code "Páginas da loja", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Sai: um item por página da loja que o monitor baixa com o código próprio.
// A página 2 serve de gabarito para o Firecrawl, que raspa a mesma página.
// O nó ignora o que entra: quando o fluxo volta para cá depois de uma espera,
// as duas páginas são pedidas de novo.
return [
  { json: { pagina: 1, url: 'https://books.toscrape.com/' } },
  { json: { pagina: 2, url: 'https://books.toscrape.com/catalogue/page-2.html' } },
];
