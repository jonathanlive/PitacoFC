# PitacoFC - Brasileirão 2025 🏀🚀

> Sistema inteligente de análise do Campeonato Brasileiro 2025 via WhatsApp, utilizando FastAPI, CrewAI (multiagentes), Celery, Redis e integração com Baileys.js.

---

## 👨‍💻 Sobre o Projeto

O **PitacoFC** é um bot de WhatsApp que:
- Recebe mensagens de torcedores.
- Classifica automaticamente a intenção da mensagem.
- Responde saudações e elogios imediatamente.
- Para análises complexas, dispara agentes inteligentes especializados usando **CrewAI**.
- Faz scraping em tempo real de dados do **Campeonato Brasileiro**.
- Entrega respostas naturais, como uma boa resenha boleira.


## 📊 Arquitetura Geral

```
Usuário WhatsApp → Bot Node.js (Baileys) → FastAPI (classifica intenção)
  └➤ Celery + CrewAI (processamento)
      └➤ Agentes de análise e resposta
          └➤ Bot responde automaticamente
```

- FastAPI para APIs REST.
- CrewAI para gestão de agentes especializados.
- Celery para processamento assíncrono das perguntas.
- Redis para mensageria e histórico de conversa.
- Node.js (Baileys) para integração com o WhatsApp.
- Selenium para scraping dos dados do Sofascore.


## 🔄 Estrutura de Pastas

```bash
/whatsapp-bot
|
├── brasileirao_agent/
|   ├── src/
|   |   └── brasileirao_agent/
|   |       ├── crew.py           # Definição de agentes e tarefas
|   |       ├── config/            # Configs YAML dos agentes e tarefas
|   |       └── tools/             # Ferramentas de scraping e análise
|   └── project.toml               # Projeto Python Hatchling
|
├── fastapi_server/
|   ├── main.py                   # Endpoints da API
|   ├── intencao_llm.py            # Classificação de intenção
|   ├── brasileirao_connector.py  # Conecta FastAPI à CrewAI
|   ├── celery_app.py             # Inicialização do Celery
|   ├── tasks.py                  # Tarefa para processamento de perguntas
|   └── thread_manager.py         # Gestão de threads OpenAI
|
├── index.cjs                         # Bot WhatsApp (Baileys)
|
└── .env                            # Variáveis de ambiente (Redis, APIs, etc)
```


## 🔄 Fluxo de Funcionamento

1. O usuário manda uma mensagem no WhatsApp.
2. O bot Node.js (Baileys) recebe e detecta a intenção via FastAPI.
3. Dependendo da intenção:
   - Responde diretamente (saudação, elogio, fora de contexto).
   - Enfileira para análise via CrewAI.
4. Celery processa a mensagem acionando agentes CrewAI especializados.
5. Agentes consultam dados atualizados do Brasileirão e geram a resposta.
6. Resposta é enviada de volta ao usuário via WhatsApp.


## 📢 Tecnologias Utilizadas

- **Python 3.11**
- **FastAPI**
- **Celery**
- **Redis**
- **CrewAI**
- **Node.js**
- **Baileys.js**
- **Selenium**
- **OpenAI GPT-4o**


## 🌐 Variáveis de Ambiente (.env)

```bash
OPENAI_API_KEY=your_openai_key
OPENAI_ASSISTANT_ID=your_assistant_id
REDIS_URL=redis://localhost:6379/0
BOT_URL=http://localhost:3000
```


## 🚀 Como Executar o Projeto Localmente

### 1. Instale as dependências do Python

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. Instale as dependências do Node.js

```bash
npm install
```

### 3. Suba o Redis localmente

```bash
# Se tiver Docker:
docker run -d --name redis -p 6379:6379 redis
```

### 4. Inicie a FastAPI Server

```bash
PYTHONPATH=brasileirao_agent/src uvicorn fastapi_server.main:app --host 0.0.0.0 --reload --port 8000
```

### 5. Inicie o Worker Celery

```bash
PYTHONPATH=brasileirao_agent/src celery -A fastapi_server.tasks worker --loglevel=info --concurrency=4
```

### 6. Inicie o Bot WhatsApp

```bash
node index.cjs
```


## 🔗 Agentes Configurados

| Agente | Função |
|:------|:------|
| `tabela_analyst` | Análise da tabela de classificação |
| `tabela_performance_analyst` | Performance recente dos times |
| `team_stats_analyst` | Estatísticas coletivas dos times |
| `player_stats_analyst` | Estatísticas individuais dos jogadores |
| `player_overall_analyst` | Comparativos competitivos entre jogadores |
| `round_insights_analyst` | Insights sobre a rodada atual |
| `brasileirao_senior_analyst` | Consolida e revisa as respostas |


## 📚 Documentação Complementar

- **Classificador de Intenção:** `fastapi_server/intencao_llm.py`
- **Orquestração de Crew:** `brasileirao_agent/src/brasileirao_agent/crew.py`
- **Ferramentas de Scraping:** `brasileirao_agent/src/brasileirao_agent/tools/`
- **Configurações YAML:** `brasileirao_agent/src/brasileirao_agent/config/`


## 🔧 Scripts úteis

| Ação | Comando |
|:-------|:--------|
| Rodar apenas a CrewAI | `python -m brasileirao_agent.main` |
| Iniciar FastAPI | `uvicorn fastapi_server.main:app --reload` |
| Iniciar Celery | `celery -A fastapi_server.tasks worker --loglevel=info --concurrency=4` |
| Subir bot WhatsApp | `node index.cjs` |


## 📊 Melhorias Futuras

- Criar Docker Compose para orquestração completa (FastAPI + Celery + Redis + Bot).
- Adicionar busca de notícias em tempo real com ferramenta própria.
- Caching de consultas de dados do Sofascore para otimização.


---

# 🏆 Status do Projeto

**PitacoFC** está operacional, pronto para receber mensagens no WhatsApp e entregar insights únicos sobre o Campeonato Brasileiro 2025, com uma arquitetura escalável, inteligente e responsiva! 🌟🏀

---

> Documentado com ❤️ por PitacoFC Dev Team
