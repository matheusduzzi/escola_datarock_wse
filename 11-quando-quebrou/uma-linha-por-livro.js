// Código do nó Code "Uma linha por livro", no modo Run Once for All Items.
// É o mesmo texto que está dentro de monitor-com-trava.json.
//
// Só roda quando a rodada passou na trava: o If "A raspagem quebrou?" saiu pelo falso.
// Entra: o item do nó "Checar a saúde da rodada", com a rodada pronta em "linhas".
// Sai: um item por livro, com as cinco colunas da rodada, como na aula 10.
return $input.first().json.linhas.map((linha) => ({ json: linha }));
