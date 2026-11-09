// Código do nó Code "Ver as respostas da loja", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Entra: uma resposta por página, do nó "Baixar as páginas da loja", com o
// corpo em "data" e o status em "statusCode" (o nó não para em status ruim).
// Sai: as mesmas respostas, com "situacao" igual em todas:
//   ok      todas vieram bem: segue para tirar os livros;
//   tentar  alguma veio 429 ou 5xx e ainda dá para tentar de novo;
//   parar   o site recusou, pediu login, mostrou captcha ou não melhorou.
const TENTATIVAS = 3; // a primeira e mais duas

const paginas = $('Páginas da loja').all().map((i) => i.json);
const tentativa = $runIndex + 1;
const respostas = $input.all().map((item, i) => {
  const r = item.json;
  const corpo = String(r.data ?? '');
  const status = Number(r.statusCode);
  let motivo = '';
  let tipo = 'ok';
  if ([401, 403, 407].includes(status)) {
    tipo = 'parar';
    motivo = `a loja recusou o pedido (${status})`;
  } else if (/type=["']?password/i.test(corpo)) {
    tipo = 'parar';
    motivo = 'a loja respondeu com um formulário de login';
  } else if (/captcha/i.test(corpo)) {
    tipo = 'parar';
    motivo = 'a loja respondeu com um captcha';
  } else if (status === 429 || status >= 500) {
    tipo = 'tentar';
    motivo = `a loja respondeu ${status}`;
  } else if (status !== 200) {
    tipo = 'parar';
    motivo = `a loja respondeu ${status}`;
  }
  return { ...r, ...paginas[i], tipo, motivo };
});

const recusa = respostas.find((r) => r.tipo === 'parar');
const ruim = respostas.find((r) => r.tipo === 'tentar');
let situacao = 'ok';
let detalhe = `tentativa ${tentativa}: as ${respostas.length} páginas vieram bem`;
if (recusa) {
  situacao = 'parar';
  detalhe = `Parei: na página ${recusa.pagina}, ${recusa.motivo}. Não tente passar por isso: veja o que mudou no site.`;
} else if (ruim && tentativa < TENTATIVAS) {
  situacao = 'tentar';
  detalhe = `tentativa ${tentativa}: na página ${ruim.pagina}, ${ruim.motivo}; vou esperar e pedir de novo`;
} else if (ruim) {
  situacao = 'parar';
  detalhe = `Parei: na página ${ruim.pagina}, ${ruim.motivo} nas ${TENTATIVAS} tentativas.`;
}

return respostas.map(({ tipo, motivo, ...r }) => ({ json: { ...r, situacao, detalhe, tentativa } }));
