// Código do nó Code "Comparar com a anterior", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Entra: as linhas da rodada anterior, lidas do arquivo pelo nó "CSV para itens".
// Do arquivo, tudo chega como texto. Lê também a rodada de hoje, no nó
// "Uma linha por item", e a conferência e o custo, no nó "Montar a rodada".
// Sai: um item só, com o resumo e a lista do que mudou. O arquivo CSV da rodada
// de hoje vai junto, para os dois nós que gravam.
const hoje = $('Uma linha por item').all().map((item) => item.json);
const antes = $input.all().map((item) => item.json);
const r = $('Montar a rodada').first().json;
const chave = (l) => `${l.alvo}|${l.chave}`;
const hojePorChave = new Map(hoje.map((l) => [chave(l), l]));

const mudancas = [];
for (const velho of antes) {
  const novo = hojePorChave.get(chave(velho));
  if (!novo) {
    // Estava na anterior e não veio hoje.
    mudancas.push({ alvo: velho.alvo, chave: velho.chave, nome: velho.nome, tipo: 'sumiu', antes: velho.preco, depois: '' });
    continue;
  }
  // Compara como número: "50.1" e "50.10" são o mesmo preço. Citação não tem preço.
  if (velho.preco !== '' && novo.preco !== '' && Number(velho.preco) !== Number(novo.preco)) {
    mudancas.push({ alvo: novo.alvo, chave: novo.chave, nome: novo.nome, tipo: 'preco', antes: velho.preco, depois: novo.preco });
  }
  if (velho.disponivel !== '' && novo.disponivel !== '' && velho.disponivel !== novo.disponivel) {
    mudancas.push({
      alvo: novo.alvo, chave: novo.chave, nome: novo.nome, tipo: 'disponibilidade', antes: velho.disponivel, depois: novo.disponivel,
    });
  }
}

return [
  {
    json: {
      rodada: r.rodada,
      rodada_anterior: antes.length ? antes[0].rodada : '',
      itens_hoje: hoje.length,
      itens_antes: antes.length,
      mudancas,
      erros_firecrawl: r.conferencia.erros,
      custo: r.custo,
    },
    binary: $('Rodada de hoje em CSV').first().binary,
  },
];
