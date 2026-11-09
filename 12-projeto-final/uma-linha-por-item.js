// Código do nó Code "Uma linha por item", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-final.json.
//
// Só roda quando a rodada passou nas regras de saúde.
// Entra: o item do nó "Montar a rodada". Sai: um item por linha da rodada,
// nos três alvos, com as colunas do histórico.
return $input.first().json.linhas.map((linha) => ({ json: linha }));
