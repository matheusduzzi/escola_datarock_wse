// Código do nó Code "Montar o aviso", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Só roda quando o If "Mudou algo?" sai pelo verdadeiro.
// Entra: o resumo do nó "Comparar com a anterior" (os nós de gravar passam o resumo adiante).
// Sai: um item com o assunto, o texto do aviso, a lista do que mudou e o custo.
const r = $input.first().json;
const NOMES = { 'loja-pagina-1': 'loja, página 1', 'loja-pagina-2': 'loja, página 2', citacoes: 'citações' };
const linhas = r.mudancas.map((m) => {
  const onde = NOMES[m.alvo] || m.alvo;
  if (m.tipo === 'preco') {
    const rumo = Number(m.depois) < Number(m.antes) ? 'caiu' : 'subiu';
    return `${onde}: ${m.nome}: o preço ${rumo} de £${m.antes} para £${m.depois}`;
  }
  if (m.tipo === 'disponibilidade') {
    return `${onde}: ${m.nome}: ${m.depois === 'sim' ? 'voltou ao estoque' : 'ficou sem estoque'}`;
  }
  return `${onde}: ${m.nome}: saiu da página`;
});
const erros = r.erros_firecrawl.map((e) => `${e.nome}: ${e.campo} veio ${e.firecrawl}, o código próprio leu ${e.gabarito}`);
return [
  {
    json: {
      assunto: `Monitor de preço: ${r.mudancas.length} mudança(s) na rodada de ${r.rodada}`,
      texto: [
        `Comparei ${r.itens_hoje} itens dos três alvos com a rodada de ${r.rodada_anterior}.`,
        ...linhas.map((l) => `- ${l}`),
        ...(erros.length ? ['O Firecrawl errou na página 2 (o histórico ficou com o valor do código próprio):', ...erros.map((e) => `- ${e}`)] : []),
        `Créditos dessa rodada: ${r.custo.total} (scrape.do ${r.custo.scrapedo}, pelo ${r.custo.scrapedo_fonte}; Firecrawl ${r.custo.firecrawl}, pela ${r.custo.firecrawl_fonte}).`,
      ].join('\n'),
      mudancas: r.mudancas,
      erros_firecrawl: r.erros_firecrawl,
      custo: r.custo,
    },
  },
];
