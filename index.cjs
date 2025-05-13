const crypto = require('crypto');
global.crypto = crypto;

const axios = require('axios');
const express = require('express');
const Redis = require('ioredis');
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
const bodyParser = require('body-parser');
const { proximaDica, saudacaoAleatoria } = require('./utils.cjs');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const QRCode = require('qrcode'); // ← adicione isso no topo com os outros imports
let qrCodeData = null; // ← para armazenar o QR gerado

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
        const texto = saudacaoAleatoria();   // sync, sem Redis
        await sock.sendMessage(sender, { text: texto });
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
          console.error(`[❌ ERRO AO CONSULTAR ${FASTAPI_URL}/futebol_geral]:`, err.message);
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
            `${FASTAPI_URL}/noticia`,
            { pergunta: texto, sender: sender },
            { timeout: 30_000 }
          );
      
          const resposta = respostaIA.data.response || MENSAGENS.incompreensivel;
      
          await sock.sendMessage(sender, { text: resposta }).catch(async (err) => {
            console.warn('[⚠️ FALLBACK] Erro ao enviar resposta principal (noticia):', err.message);
            await sock.sendMessage(sender, { text: resposta }, { useEncryptionFallback: true }).catch(console.error);
          });
      
        } catch (err) {
          console.error(`[❌ ERRO AO CONSULTAR ${FASTAPI_URL}/noticia]:`, err.message);
          await sock.sendMessage(sender, { text: MENSAGENS.erro }).catch(console.error);
        }
      
        continue; // 🔥 ESSENCIAL parar aqui depois de responder
      }

      if (intencao === 'sobre_bot') {
        const dica = await proximaDica(redis, sender);
        await sock.sendMessage(sender, { text: dica });
        continue; // volta pro loop
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
    printQRInTerminal: false, // ← Desativa o terminal quebrado
    browser: ['MeuBot', 'Chrome', '1.0.0'],
    emitOwnEvents: true,
    getMessage: async () => ({ conversation: "⚠️ Mensagem não encontrada para reenvio." })
  });

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      qrCodeData = qr; // ← guarda o QR atual para exibir na rota /qrcode
      const domain = process.env.RAILWAY_PUBLIC_DOMAIN || `http://localhost:${process.env.PORT || 8080}`;
      console.log(`📸 QR Code gerado! Escaneie aqui no navegador: ${domain}/qrcode`);
    }

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
  console.log('📨 [POST /responder] Requisição recebida:', JSON.stringify(req.body, null, 2));

  try {
    const { sender, resposta } = req.body;

    if (!sender || !resposta) {
      console.warn('⚠️ [POST /responder] Dados inválidos recebidos:', req.body);
      return res.status(400).send('Dados inválidos');
    }

    if (!sockGlobal) {
      console.error('❌ [POST /responder] socketGlobal está undefined. WhatsApp ainda não conectado?');
      return res.status(500).send('Socket WhatsApp não conectado');
    }

    console.log(`🚀 [POST /responder] Enviando mensagem para ${sender}...`);
    await sockGlobal.sendMessage(sender, { text: resposta });
    console.log(`✅ [POST /responder] Mensagem enviada com sucesso para ${sender}`);

    // Libera o usuário para novas perguntas
    processandoUsuario[sender] = false;

    // Verifica se há fila pendente
    if (filasDeMensagens[sender]?.length > 0) {
      console.log(`🔄 [POST /responder] Processando fila pendente para ${sender}...`);
      processarFilaDeMensagens(sockGlobal, sender);
    }

    res.send('Mensagem enviada');
  } catch (error) {
    console.error('🔥 [POST /responder] Erro ao enviar resposta:', error.stack || error.message);
    res.status(500).send('Erro interno');
  }
});

// 🖼️ Nova rota para exibir o QR Code no navegador
app.get('/qrcode', async (req, res) => {
  if (!qrCodeData) {
    return res.status(404).send('QR Code ainda não gerado. Tente novamente em instantes.');
  }

  try {
    const qrImageBuffer = await QRCode.toBuffer(qrCodeData, { type: 'png', width: 300 });
    res.set('Content-Type', 'image/png');
    res.send(qrImageBuffer);
  } catch (err) {
    console.error('Erro ao gerar QR Code:', err.message);
    res.status(500).send('Erro ao gerar QR Code');
  }
});

app.get('/', (req, res) => {
  res.send('✅ Pitaco FC está rodando!');
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`🛡️ Servidor Express rodando na porta ${PORT}`);
});
