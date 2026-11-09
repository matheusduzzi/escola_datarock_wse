// Código do nó Code "Uma linha por livro", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor.json: aqui fica mais fácil de ler.
//
// Entra: um item do nó "Tirar os livros", com quatro listas do mesmo tamanho
// (titulo, preco, disponibilidade, endereco).
// Sai: um item por livro, com as cinco colunas da rodada.
const LOJA = 'https://books.toscrape.com/';
// $now segue o fuso do fluxo (Settings > Timezone). O Date() do JavaScript não segue.
const rodada = $now.toFormat('yyyy-MM-dd');
const linhas = [];
for (const item of $input.all()) {
  const { titulo = [], preco = [], disponibilidade = [], endereco = [] } = item.json;
  const tamanhos = [preco.length, disponibilidade.length, endereco.length];
  if (tamanhos.some((n) => n !== titulo.length)) {
    throw new Error(
      `As listas vieram com tamanhos diferentes: ${titulo.length} títulos, ${preco.length} preços, ` +
        `${disponibilidade.length} disponibilidades e ${endereco.length} endereços. Veja os seletores do nó "Tirar os livros".`,
    );
  }
  titulo.forEach((t, i) => {
    // "£51.77" vira "51.77". Se a página vier com o símbolo trocado, o número continua certo.
    const numero = String(preco[i]).match(/\d+(\.\d+)?/);
    linhas.push({
      json: {
        rodada,
        url: endereco[i].startsWith('http') ? endereco[i] : LOJA + endereco[i].replace(/^\.?\//, ''),
        titulo: t,
        preco: numero ? Number(numero[0]).toFixed(2) : '',
        disponivel: /in stock/i.test(disponibilidade[i]) ? 'sim' : 'nao',
      },
    });
  });
}
return linhas;
