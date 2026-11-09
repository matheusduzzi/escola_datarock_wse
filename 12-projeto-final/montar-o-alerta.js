// Código do nó Code "Montar o alerta de quebra", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Só roda quando o If "A raspagem quebrou?" sai pelo verdadeiro.
// Entra: o item do nó "Montar a rodada", com "rodada", "problemas" e "custo".
// Sai: um item com o assunto, o texto do alerta, a lista de problemas e o custo.
const r = $input.first().json;
return [
  {
    json: {
      rodada: r.rodada,
      assunto: `Monitor de preço: a raspagem quebrou na rodada de ${r.rodada}`,
      texto: [
        'Nada foi gravado. A rodada anterior continua valendo.',
        ...r.problemas.map((p) => `- ${p.detalhe}`),
        `Créditos gastos mesmo assim: ${r.custo.total} (scrape.do ${r.custo.scrapedo}, Firecrawl ${r.custo.firecrawl}).`,
        'Abra a página que quebrou e veja o que mudou antes de mexer no fluxo.',
      ].join('\n'),
      problemas: r.problemas,
      custo: r.custo,
    },
  },
];
