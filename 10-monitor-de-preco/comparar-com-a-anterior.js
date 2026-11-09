// Código do nó Code "Comparar com a anterior", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor.json.
//
// Entra: as linhas da rodada anterior, lidas do arquivo pelo nó "CSV para itens".
// Do arquivo, tudo chega como texto: "50.10", "sim".
// Lê também a rodada de hoje, direto no nó "Uma linha por livro".
// Sai: um item só, com o resumo e a lista do que mudou. O arquivo CSV da rodada
// de hoje vai junto, para os dois nós que gravam.
const hoje = $('Uma linha por livro').all().map((item) => item.json);
const antes = $input.all().map((item) => item.json);
const antesPorUrl = new Map(antes.map((linha) => [linha.url, linha]));

const mudancas = [];
for (const livro of hoje) {
  const velho = antesPorUrl.get(livro.url);
  // Livro que não estava na rodada anterior: essa versão do monitor não avisa.
  if (!velho) continue;
  // Compara como número: "50.1" e "50.10" são o mesmo preço.
  if (Number(velho.preco) !== Number(livro.preco)) {
    mudancas.push({ url: livro.url, titulo: livro.titulo, tipo: 'preco', antes: velho.preco, depois: livro.preco });
  }
  if (velho.disponivel !== livro.disponivel) {
    mudancas.push({
      url: livro.url, titulo: livro.titulo, tipo: 'disponibilidade', antes: velho.disponivel, depois: livro.disponivel,
    });
  }
}

return [
  {
    json: {
      rodada: hoje.length ? hoje[0].rodada : '',
      rodada_anterior: antes.length ? antes[0].rodada : '',
      livros_hoje: hoje.length,
      livros_antes: antes.length,
      mudancas,
    },
    binary: $('Rodada de hoje em CSV').first().binary,
  },
];
