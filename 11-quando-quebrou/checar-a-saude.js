// Código do nó Code "Checar a saúde da rodada", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-com-trava.json.
//
// Entra: um item do nó "Tirar os livros", com quatro listas (titulo, preco,
// disponibilidade, endereco). O nó HTML sempre retorna esse item, mesmo quando
// os seletores não acham nada: aí as listas vêm vazias.
// Sai: um item só, com a rodada em "linhas" e a lista "problemas".
// Lista vazia: a rodada está boa. Qualquer problema: o fluxo não grava e avisa.

// As duas regras de saúde. Os números são decisão de quem usa o monitor.
const CONTAGEM_MINIMA = 16; // a página 1 da loja traz 20 livros
const MAX_VAZIOS = 0.1; // até 10% de um campo vazio ainda passa

const LOJA = 'https://books.toscrape.com/';
const rodada = $now.toFormat('yyyy-MM-dd');
const lista = (v) => (Array.isArray(v) ? v : v == null || v === '' ? [] : [v]);
const { titulo, preco, disponibilidade, endereco } = $input.first().json;
const listas = {
  titulo: lista(titulo),
  preco: lista(preco),
  disponibilidade: lista(disponibilidade),
  endereco: lista(endereco),
};
const total = Math.max(...Object.values(listas).map((l) => l.length));

// Só aceita o formato que a loja usa. O que não reconhece fica vazio,
// para a regra de vazios ver. "£51.77" vira "51.77"; "51,77 €" fica vazio.
const lerPreco = (texto) => {
  const m = String(texto ?? '').match(/£\s*(\d+\.\d{2})/);
  return m ? m[1] : '';
};
// "In stock" vira sim, "Out of stock" vira nao. Texto novo fica vazio,
// em vez de virar "nao" e aparecer como livro sem estoque.
const lerEstoque = (texto) => {
  const t = String(texto ?? '');
  if (/out of stock/i.test(t)) return 'nao';
  if (/\bin stock\b/i.test(t)) return 'sim';
  return '';
};
const lerEndereco = (href) => {
  const h = String(href ?? '').trim();
  if (!h) return '';
  return h.startsWith('http') ? h : LOJA + h.replace(/^\.?\//, '');
};

const linhas = [];
for (let i = 0; i < total; i++) {
  linhas.push({
    rodada,
    url: lerEndereco(listas.endereco[i]),
    titulo: String(listas.titulo[i] ?? '').trim(),
    preco: lerPreco(listas.preco[i]),
    disponivel: lerEstoque(listas.disponibilidade[i]),
  });
}

const problemas = [];
// Regra 1: contagem mínima.
if (total < CONTAGEM_MINIMA) {
  problemas.push({ regra: 'contagem', detalhe: `${total} livros na página; o mínimo é ${CONTAGEM_MINIMA}` });
}
// Listas de tamanhos diferentes: um campo sumiu de algum livro, e os
// valores dos livros seguintes ficariam no livro errado.
const tamanhos = Object.values(listas).map((l) => l.length);
if (total > 0 && tamanhos.some((n) => n !== total)) {
  problemas.push({
    regra: 'listas',
    detalhe:
      `as listas vieram com tamanhos diferentes: ${listas.titulo.length} títulos, ${listas.preco.length} preços, ` +
      `${listas.disponibilidade.length} disponibilidades e ${listas.endereco.length} endereços`,
  });
}
// Regra 2: percentual de campos vazios.
if (total > 0) {
  const nomes = { url: 'endereço', titulo: 'título', preco: 'preço', disponivel: 'disponibilidade' };
  for (const campo of Object.keys(nomes)) {
    const vazios = linhas.filter((l) => l[campo] === '').length;
    if (vazios / total > MAX_VAZIOS) {
      problemas.push({
        regra: 'vazios',
        campo,
        detalhe: `${vazios} de ${total} livros sem ${nomes[campo]} (${Math.round((100 * vazios) / total)}%)`,
      });
    }
  }
}

return [{ json: { rodada, total, problemas, linhas } }];
