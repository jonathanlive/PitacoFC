const crypto = require('crypto');
global.crypto = crypto;

const axios = require('axios');
const express = require('express');
const Redis = require('ioredis');
const redis = new Redis();
const bodyParser = require('body-parser');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

const fs = require('fs');
const authPath = './auth_info_multi';

if (!fs.existsSync(authPath)) {
  fs.mkdirSync(authPath, { recursive: true });
}

// 🎯 Nova mensagem especial de boas-vindas
const MENSAGEM_APRESENTACAO = `⚡ Salve, craque! Eu sou o PitacoFC, seu parceiro de resenha e análises boleiras! ⚽🔥

Tô aqui pra te ajudar com:
- Curiosidades e histórias do futebol 🧠
- Pitacos sobre o Brasileirão 2025 📈
- Análises de desempenho de jogadores e times 🎯
- E claro, trocar aquela ideia marota sobre o mundo da bola! 🎙️

Manda sua dúvida ou seu pitaco que a gente desenrola! 🚀
`;

// 🎯 Mensagens padrão centralizadas
const MENSAGENS = {
  saudacao: '🎯 Fala, craque! Bora trocar aquele pitaco de qualidade sobre futebol? ⚽🔥',
  geral: '🔎 Manda aí tua dúvida sobre o Brasileirão, os craques ou aquela resenha marota! 💬⚽',
  fora: '🚫 Aqui é só futebol, irmão! ⚽ Manda algo sobre o nosso mundão da bola que eu desenrolo pra você! 🎙️',
  aguardando: '⌛ Segura a emoção, parceiro! Tô revisando teu pitaco no VAR... já volto! 🧐⚽',
  analisando: '📊 Show! Tô no VAR agora... segura aí que vem insight de craque! ⚡⚽',
  erro: '💥 Deu um carrinho feio aqui no sistema! 😵‍💫 Tenta mandar de novo que a gente resolve!',
  invalida: '🤷‍♂️ Essa jogada aí eu não entendi... manda uma pergunta mais na moral, beleza? ⚽',
  incompreensivel: '🤔 Não saquei bem tua pergunta... reformula aí que eu tô na área! ⚽',
  fallback: '🔄 Rolou um drible inesperado... mas calma, que tô te respondendo no melhor esquema! ⚡',
};

// 🛑 Controle de filas por usuário
const filasDeMensagens = {}; // { sender: [ { texto, intencao } ] }
const processandoUsuario = {}; // { sender: true/false }
let sockGlobal; // Sock global para o Express acessar

// 🔍 Função de intenção
async function verificarIntencao(mensagem, sender) {
  try {
    const historico = await redis.lrange(`historico:${sender}`, 0, 9); // Pega últimas mensagens
    historico.reverse(); // Deixa na ordem correta (antiga ➔ nova)

    const payload = {
      mensagem,
      historico
    };

    const resposta = await axios.post(`${FASTAPI_URL}/intencao`, payload);
    return resposta.data.intencao;

  } catch (err) {
    console.warn('⚠️ Erro ao detectar intenção:', err.message);
    return 'desconhecida';
  }
}

// 🚀 Enfileira a mensagem recebida
async function enfileirarMensagem(sock, sender, texto) {
  if (!filasDeMensagens[sender]) {
    filasDeMensagens[sender] = [];
  }

  // 🔥 Se ainda não existe histórico no Redis, manda a apresentação!
  const historicoExistente = await redis.exists(`historico:${sender}`);
  if (!historicoExistente) {
    await sock.sendMessage(sender, { text: MENSAGEM_APRESENTACAO }).catch(console.error);
  }
  
  const intencao = await verificarIntencao(texto, sender);

  // Salvar no Redis o histórico da conversa
  await redis.lpush(`historico:${sender}`, texto);
  await redis.ltrim(`historico:${sender}`, 0, 9); // Mantém no máximo 10 mensagens

  // Se já estiver processando e for uma pergunta pesada, pede para aguardar
  if (processandoUsuario[sender] && intencao === 'pergunta') {
    await sock.sendMessage(sender, { text: MENSAGENS.aguardando }).catch(console.error);
    return;
  }

  filasDeMensagens[sender].push({ texto, intencao });

  if (!processandoUsuario[sender] || (processandoUsuario[sender] && intencao !== 'pergunta')) {
    processarFilaDeMensagens(sock, sender);
  }
}

// 🔥 Processa a fila de mensagens do usuário
async function processarFilaDeMensagens(sock, sender) {
  while (filasDeMensagens[sender] && filasDeMensagens[sender].length > 0) {
    const { texto, intencao } = filasDeMensagens[sender].shift();

    try {
      if (intencao === 'saudacao') {
        await sock.sendMessage(sender, { text: MENSAGENS.saudacao });
        continue;
      }

      if (intencao === 'futebol_geral') {
        try {
          const respostaIA = await axios.post(
            `${FASTAPI_URL}/futebol_geral`,
            { pergunta: texto, sender: sender },
            { timeout: 30_000 }
          );
      
          const resposta = respostaIA.data.response || MENSAGENS.incompreensivel;
      
          await sock.sendMessage(sender, { text: resposta }).catch(async (err) => {
            console.warn('[⚠️ FALLBACK] Erro ao enviar resposta principal:', err.message);
            await sock.sendMessage(sender, { text: resposta }, { useEncryptionFallback: true }).catch(console.error);
          });
      
        } catch (err) {
          console.error('[❌ ERRO AO CONSULTAR /futebol_geral]:', err.message);
          await sock.sendMessage(sender, { text: MENSAGENS.erro }).catch(console.error);
        }
      
        continue;
      }      

      if (intencao === 'fora_de_contexto') {
        await sock.sendMessage(sender, { text: MENSAGENS.fora });
        continue;
      }

      if (intencao === 'elogio') {
        await sock.sendMessage(sender, { text: '🔥 Valeu, craque! Tamo junto nessa resenha boleira! ⚽🤝' });
        continue;
      }
      
      if (intencao === 'ofensa') {
        await sock.sendMessage(sender, { text: '😔 Relaxa, craque! Bora focar no futebol que é isso que importa! ⚽' });
        continue;
      }

      if (intencao === 'noticia') {
        try {
          const respostaIA = await axios.post(
            `${FASTAPI_URL}/futebol_geral`,
            { pergunta: texto, sender: sender },
            { timeout: 30_000 }
          );
      
          const resposta = respostaIA.data.response || MENSAGENS.incompreensivel;
      
          await sock.sendMessage(sender, { text: resposta }).catch(async (err) => {
            console.warn('[⚠️ FALLBACK] Erro ao enviar resposta principal (noticia):', err.message);
            await sock.sendMessage(sender, { text: resposta }, { useEncryptionFallback: true }).catch(console.error);
          });
      
        } catch (err) {
          console.error('[❌ ERRO AO CONSULTAR /futebol_geral para noticia]:', err.message);
          await sock.sendMessage(sender, { text: MENSAGENS.erro }).catch(console.error);
        }
      
        continue; // 🔥 ESSENCIAL parar aqui depois de responder
      }

      // Se for pergunta pesada, marca como processando
      processandoUsuario[sender] = true;
      await sock.sendMessage(sender, { text: MENSAGENS.analisando });

      await axios.post(
        `${FASTAPI_URL}/perguntar`,
        { pergunta: texto, sender: sender },
        { timeout: 20_000 }
      ).catch((err) => {
        console.warn('⚠️ Erro ao enviar pergunta para análise:', err.message);
        sock.sendMessage(sender, { text: MENSAGENS.erro }).catch(console.error);
      });

      // Depois que disparar a pergunta pesada, para aqui: só libera depois no /responder!
      break;

    } catch (err) {
      console.error('Erro ao enviar para análise:', err.message);
      await sock.sendMessage(sender, { text: MENSAGENS.erro }).catch(console.error);
    }
  }
}

// 🌟 Inicializa conexão WhatsApp
async function startSock() {
  const { state, saveCreds } = await useMultiFileAuthState('./auth_info_multi');
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: true,
    browser: ['MeuBot', 'Chrome', '1.0.0'],
    defaultQueryTimeoutMs: 620_000,
    msgRetryCounterMap: {},
    shouldIgnoreJid: () => false,
    emitOwnEvents: true,
    getMessage: async (key) => ({ conversation: "⚠️ Mensagem não encontrada para reenvio." })
  });

  sock.ev.on('connection.update', ({ connection, lastDisconnect }) => {
    if (connection === 'close') {
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('❌ Conexão encerrada.', { shouldReconnect });
      if (shouldReconnect) {
        setTimeout(() => {
          console.log('🔄 Tentando reconectar...');
          startSock();
        }, 6000);
      }
    } else if (connection === 'open') {
      console.log('✅ Conectado com sucesso ao WhatsApp!');
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', (m) => {
    const msg = m.messages[0];
    if (!msg.message || msg.key.fromMe) return;

    const texto = msg.message.conversation || msg.message.extendedTextMessage?.text || '';
    const sender = msg.key.remoteJid;

    if (!texto.trim()) {
      sock.sendMessage(sender, { text: MENSAGENS.invalida }).catch(console.error);
      return;
    }

    enfileirarMensagem(sock, sender, texto);
  });

  sockGlobal = sock;
}

startSock().catch(console.error);

// 🚀 Servidor Express para receber respostas
const app = express();
app.use(bodyParser.json());

app.post('/responder', async (req, res) => {
  try {
    const { sender, resposta } = req.body;
    if (!sender || !resposta) {
      return res.status(400).send('Dados inválidos');
    }

    if (!sockGlobal) {
      return res.status(500).send('Socket WhatsApp não conectado');
    }

    await sockGlobal.sendMessage(sender, { text: resposta });

    // ✅ Agora sim, libera o usuário para novas perguntas
    processandoUsuario[sender] = false;

    // Após liberar, processa a fila novamente, caso tenha ficado mensagens pendentes
    if (filasDeMensagens[sender] && filasDeMensagens[sender].length > 0) {
      processarFilaDeMensagens(sockGlobal, sender);
    }

    res.send('Mensagem enviada');
  } catch (error) {
    console.error('Erro ao enviar resposta:', error.message);
    res.status(500).send('Erro interno');
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🛡️ Servidor Express rodando na porta ${PORT}`);
});
