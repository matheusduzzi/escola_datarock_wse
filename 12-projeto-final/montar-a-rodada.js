// Código do nó Code "Montar a rodada", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Entra: a resposta do Firecrawl (página 2). Lê também, pelos nomes dos nós,
// os livros das duas páginas baixadas com o código próprio e as citações que
// vieram pelo scrape.do.
// Sai: um item só, com as linhas da rodada dos três alvos, a lista "problemas",
// a conferência do Firecrawl contra o código próprio e o custo da rodada.
// Lista "problemas" vazia: a rodada pode ser gravada.

// As regras de saúde. Os números são decisão de quem usa o monitor.
const MAX_VAZIOS = 0.1; // até 10% de um campo vazio ainda passa
const MINIMO = { 'loja-pagina-1': 16, 'loja-pagina-2': 16, citacoes: 8 }; // as páginas trazem 20, 20 e 10
// Créditos pela tabela, para quando a resposta não diz quanto custou.
const TABELA_SCRAPEDO = 1; // datacenter, sem render
const TABELA_FIRECRAWL = 5; // scrape com JSON: 1 da página e 4 do JSON

const rodada = $now.toFormat('yyyy-MM-dd');
const problemas = [];
const linhas = [];

const lista = (v) => (Array.isArray(v) ? v : v == null || v === '' ? [] : [v]);
const lerPreco = (texto) => {
  const m = String(texto ?? '').match(/£\s*(\d+\.\d{2})/);
  return m ? m[1] : '';
};
const lerEstoque = (texto) => {
  const t = String(texto ?? '');
  if (/out of stock/i.test(t)) return 'nao';
  if (/\bin stock\b/i.test(t)) return 'sim';
  return '';
};
const lerEndereco = (href, base) => {
  const h = String(href ?? '').trim();
  return h ? new URL(h, base).href : '';
};
const checarVazios = (alvo, itens, nomes) => {
  if (!itens.length) return;
  for (const [campo, nome] of Object.entries(nomes)) {
    const vazios = itens.filter((l) => l[campo] === '').length;
    if (vazios / itens.length > MAX_VAZIOS) {
      problemas.push({
        alvo, regra: 'vazios', campo,
        detalhe: `${alvo}: ${vazios} de ${itens.length} sem ${nome} (${Math.round((100 * vazios) / itens.length)}%)`,
      });
    }
  }
};
const checarContagem = (alvo, total, coisa) => {
  if (total < MINIMO[alvo]) {
    problemas.push({ alvo, regra: 'contagem', detalhe: `${alvo}: ${total} ${coisa}; o mínimo é ${MINIMO[alvo]}` });
  }
};

// 1. As duas páginas da loja, pelo código próprio.
const paginas = $('Páginas da loja').all().map((i) => i.json);
const porPagina = {};
$('Tirar os livros').all().forEach((item, i) => {
  const { pagina, url: base } = paginas[i];
  const alvo = `loja-pagina-${pagina}`;
  const l = {
    titulo: lista(item.json.titulo),
    preco: lista(item.json.preco),
    disponibilidade: lista(item.json.disponibilidade),
    endereco: lista(item.json.endereco),
  };
  const total = Math.max(...Object.values(l).map((x) => x.length));
  const livros = [];
  for (let k = 0; k < total; k++) {
    livros.push({
      rodada, alvo,
      chave: lerEndereco(l.endereco[k], base),
      nome: String(l.titulo[k] ?? '').trim(),
      preco: lerPreco(l.preco[k]),
      disponivel: lerEstoque(l.disponibilidade[k]),
      firecrawl: '',
    });
  }
  checarContagem(alvo, total, 'livros na página');
  if (total > 0 && Object.values(l).some((x) => x.length !== total)) {
    problemas.push({
      alvo, regra: 'listas',
      detalhe: `${alvo}: as listas vieram com tamanhos diferentes: ${l.titulo.length} títulos, ${l.preco.length} preços, ` +
        `${l.disponibilidade.length} disponibilidades e ${l.endereco.length} endereços`,
    });
  }
  checarVazios(alvo, livros, { chave: 'endereço', nome: 'título', preco: 'preço', disponivel: 'disponibilidade' });
  porPagina[pagina] = livros;
});

// 2. A página 2 pelo Firecrawl, conferida livro a livro com o código próprio.
const fc = $input.first().json;
const conferencia = { comparados: 0, campos: 0, certos: 0, erros: [] };
const fcLivros = fc && fc.success === true && fc.data && fc.data.json && fc.data.json.livros;
const fcStatus = fc && fc.data && fc.data.metadata ? fc.data.metadata.statusCode : undefined;
if (!Array.isArray(fcLivros) || fcStatus !== 200) {
  problemas.push({
    alvo: 'firecrawl', regra: 'firecrawl',
    detalhe: `firecrawl: a resposta veio sem a lista de livros (success ${fc && fc.success}, status da loja ${fcStatus})`,
  });
} else {
  const base = paginas.find((p) => p.pagina === 2).url;
  const doFirecrawl = new Map(fcLivros.map((b) => [lerEndereco(b.url, base), b]));
  for (const livro of porPagina[2] || []) {
    const b = doFirecrawl.get(livro.chave);
    if (!b) {
      conferencia.erros.push({ chave: livro.chave, nome: livro.nome, campo: 'livro', firecrawl: 'faltou', gabarito: livro.nome });
      livro.firecrawl = 'faltou';
      continue;
    }
    doFirecrawl.delete(livro.chave);
    conferencia.comparados++;
    const notas = [];
    const pares = [
      ['nome', String(b.titulo ?? '').trim(), livro.nome],
      ['preco', Number(b.preco), Number(livro.preco)],
      ['disponivel', b.em_estoque === true ? 'sim' : b.em_estoque === false ? 'nao' : '', livro.disponivel],
    ];
    for (const [campo, deles, nosso] of pares) {
      conferencia.campos++;
      if (deles === nosso) {
        conferencia.certos++;
      } else {
        conferencia.erros.push({ chave: livro.chave, nome: livro.nome, campo, firecrawl: String(deles), gabarito: String(nosso) });
        notas.push(`${campo}=${deles}`);
      }
    }
    livro.firecrawl = notas.length ? notas.join('; ') : 'ok';
  }
  for (const [chave, b] of doFirecrawl) {
    conferencia.erros.push({ chave, nome: String(b.titulo ?? ''), campo: 'livro', firecrawl: 'a mais', gabarito: '' });
  }
}

// 3. As citações, que vieram pelo scrape.do. A lista está num <script> da página.
const sd = $('Citações pelo scrape.do').first().json;
const corpo = String(sd.data ?? '');
const citacoes = [];
if (/type=["']?password/i.test(corpo) || /captcha/i.test(corpo)) {
  problemas.push({
    alvo: 'citacoes', regra: 'recusa',
    detalhe: 'citacoes: a página veio com login ou captcha. Pare: não tente passar por isso.',
  });
} else {
  const m = corpo.match(/var data = (\[[\s\S]*?\]);\s*for/);
  let dados = [];
  try {
    dados = m ? JSON.parse(m[1]) : [];
  } catch (erro) {
    dados = [];
  }
  for (const q of dados) {
    citacoes.push({
      rodada, alvo: 'citacoes',
      chave: String(q.text ?? '').replace(/^“|”$/g, '').trim(),
      nome: String((q.author && q.author.name) ?? '').trim(),
      preco: '', disponivel: '', firecrawl: '',
    });
  }
  checarContagem('citacoes', citacoes.length, 'citações na página');
  checarVazios('citacoes', citacoes, { chave: 'texto', nome: 'autor' });
}

// 4. O custo. O cabeçalho do scrape.do diz quanto aquele pedido custou.
const cabecalho = Number((sd.headers || {})['scrape.do-request-cost']);
const custo = {
  scrapedo: Number.isFinite(cabecalho) ? cabecalho : TABELA_SCRAPEDO,
  scrapedo_fonte: Number.isFinite(cabecalho) ? 'cabeçalho' : 'tabela',
  firecrawl: TABELA_FIRECRAWL,
  firecrawl_fonte: 'tabela',
};
custo.total = custo.scrapedo + custo.firecrawl;

linhas.push(...(porPagina[1] || []), ...(porPagina[2] || []), ...citacoes);
const totais = { 'loja-pagina-1': (porPagina[1] || []).length, 'loja-pagina-2': (porPagina[2] || []).length, citacoes: citacoes.length };
return [{ json: { rodada, totais, problemas, conferencia, custo, linhas } }];
