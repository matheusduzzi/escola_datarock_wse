// Código do nó Code "Um item por livro", no modo Run Once for All Items.
// É o mesmo texto que está dentro dos dois fluxos da pasta: aqui fica mais fácil de ler.
//
// Entra: uma resposta do scrape do Firecrawl por página raspada.
// Sai: um item por livro, com a página de onde ele veio.
// Se a resposta não serve, o nó para com erro e nada segue adiante no fluxo.
const livrosSaida = [];
for (const item of $input.all()) {
  const resposta = item.json;
  const meta = (resposta.data && resposta.data.metadata) || {};
  const pagina = meta.sourceURL || meta.url || '(página sem endereço)';
  if (resposta.success !== true) {
    throw new Error(`O Firecrawl não raspou ${pagina}: ${resposta.error || 'success não veio true'}`);
  }
  if (meta.statusCode !== 200) {
    throw new Error(`A loja respondeu ${meta.statusCode} em ${pagina}. Nenhum livro dessa rodada segue.`);
  }
  const livros = resposta.data.json && resposta.data.json.livros;
  if (!Array.isArray(livros)) {
    throw new Error(`A resposta de ${pagina} veio sem a lista "livros". Veja o esquema no nó do scrape.`);
  }
  for (const livro of livros) {
    livrosSaida.push({
      json: {
        pagina,
        titulo: livro.titulo,
        preco: livro.preco,
        em_estoque: livro.em_estoque,
        url: livro.url,
      },
    });
  }
}
return livrosSaida;
