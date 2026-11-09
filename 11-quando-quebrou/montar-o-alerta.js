// Código do nó Code "Montar o alerta de quebra", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-com-trava.json.
//
// Só roda quando o If "A raspagem quebrou?" sai pelo verdadeiro.
// Entra: o item com "rodada" e "problemas".
// Sai: um item com o assunto, o texto do alerta e a lista de problemas.
const r = $input.first().json;
return [
  {
    json: {
      assunto: `Monitor de preço: a raspagem quebrou na rodada de ${r.rodada}`,
      texto: [
        'Nada foi gravado. A rodada anterior continua valendo.',
        ...r.problemas.map((p) => `- ${p.detalhe}`),
        'Abra a página da loja e veja se o layout mudou antes de mexer no fluxo.',
      ].join('\n'),
      problemas: r.problemas,
    },
  },
];
