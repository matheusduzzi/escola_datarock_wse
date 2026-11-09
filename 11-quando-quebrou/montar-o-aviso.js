// Código do nó Code "Montar o aviso", no modo Run Once for All Items.
// É o mesmo código da aula 10, e o mesmo texto que está dentro de monitor-com-trava.json.
//
// Só roda quando o If "Mudou algo?" sai pelo verdadeiro.
// Entra: o resumo do nó "Comparar com a anterior" (os nós de gravar passam o resumo adiante).
// Sai: um item com o assunto, o texto do aviso e a lista do que mudou.
const r = $input.first().json;
const linhas = r.mudancas.map((m) => {
  if (m.tipo === 'preco') {
    const rumo = Number(m.depois) < Number(m.antes) ? 'caiu' : 'subiu';
    return `${m.titulo}: o preço ${rumo} de £${m.antes} para £${m.depois}`;
  }
  return `${m.titulo}: ${m.depois === 'sim' ? 'voltou ao estoque' : 'ficou sem estoque'}`;
});
return [
  {
    json: {
      assunto: `Monitor de preço: ${r.mudancas.length} mudança(s) na rodada de ${r.rodada}`,
      texto: [`Comparei ${r.livros_hoje} livros com a rodada de ${r.rodada_anterior}.`, ...linhas.map((l) => `- ${l}`)].join('\n'),
      mudancas: r.mudancas,
    },
  },
];
