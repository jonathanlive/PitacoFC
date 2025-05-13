// utils.js
const TIPS      = require('./tips_sobre_bot');
const SAUDACOES = require('./greetings');

/**
 * Retorna uma dica aleatória, diferente da última enviada a esse usuário.
 */
async function proximaDica(redis, sender) {
  const ultimoIdx = parseInt(await redis.get(`ultimo_tip:${sender}`) || '-1', 10);
  let novoIdx;

  do {
    novoIdx = Math.floor(Math.random() * TIPS.length);
  } while (TIPS.length > 1 && novoIdx === ultimoIdx);

  await redis.set(`ultimo_tip:${sender}`, novoIdx, 'EX', 60 * 60 * 24); // 24 h TTL
  return TIPS[novoIdx];
}

/**
 * Retorna uma saudação aleatória.
 * – Se quiser impedir repetição, basta copiar a lógica de proximaDica.
 */
function saudacaoAleatoria() {
  return SAUDACOES[Math.floor(Math.random() * SAUDACOES.length)];
}

// (Opcional) mantenha o objeto aqui, caso não exista em outro módulo
const MENSAGENS = {
  saudacao: saudacaoAleatoria,   // agora é função
  geral:   '🔎 Manda aí tua dúvida sobre o Brasileirão, os craques...',
  // … resto igual
};

module.exports = {
  proximaDica,
  saudacaoAleatoria,
  // MENSAGENS,             // exporte se quiser usar de fora
};
