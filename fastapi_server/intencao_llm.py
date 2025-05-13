import time
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Literal
from fastapi_server import thread_manager

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

thread_manager = thread_manager.ThreadManager()

def classificar_intencao(mensagem: str, historico: list = None) -> Literal["pergunta", "saudacao", "futebol_geral", "fora_de_contexto", "elogio", "ofensa", "noticia", "sobre_bot","ack" ]:
    historico = historico or []
    contexto = "\n".join(historico[-10:]) if historico else ""

    prompt = f"""
Você é um classificador de mensagens para o PitacoFC, um assistente descontraído de futebol.

Analise a mensagem recebida, considerando o histórico recente (se existir).

Classifique com apenas UMA palavra, escolhendo entre:

- "saudacao" → Cumprimentos ou conversas informais tipo "e aí", "beleza", "salve", "tudo certo?".
- "futebol_geral" → comentários, brincadeiras ou curiosidades sobre futebol no geral (história, zoeiras, Copa, mitos, jogadores famosos).
- "pergunta" → Pedidos de análise técnica de desempenho no Brasileirão 2025 (ex: aproveitamento dos times, ranking de artilharia, saldo de gols, quem tem mais chances matemáticas).
- "noticia" → Perguntas sobre atualizações recentes: jogadores lesionados, suspensos, se vai jogar, escalações, trocas de técnicos, rumores de transferência.
- "fora_de_contexto" → Mensagens que não falam de futebol (ex: "qual a capital da Alemanha?", "como investir dinheiro").
- "elogio" → Quando o usuário elogia o assistente ("Você é bom!", "Resposta rápida!", "Mandou bem!").
- "ofensa" → Quando o usuário desrespeita, xinga ou insulta ("burro", "inútil", "lixo").
- "sobre_bot" → Mensagens pedindo ajuda, que expresse duvidas ou explicação de comandos, "como funciona","o que você faz?","como assim?, "não entendi".
- "ack" → Mensagens de confirmação sem pedido extra.

Exemplos sobre_bot:
- "como funciona esse bot?"
- "dá uma ajuda aí"
- "quais comandos eu posso usar?"

Exemplos ack:
- "entendi"
- "blz, valeu"
- "show de bola"

⚠️ **Dica importante:**  
Se a mensagem perguntar "Fulano vai jogar?", "Time X vai ter reforço?", "Quem tá lesionado?", classifique como "noticia", e não "pergunta".

Analise o Histórico recente da conversa:
{contexto}

E compare com a Mensagem nova:
"{mensagem}"

E Classifique a intenção do usuário:
"""

    try:
        resposta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        resposta_final = resposta.choices[0].message.content.strip().lower()
        return resposta_final if resposta_final in ["pergunta", "saudacao", "futebol_geral", "fora_de_contexto", "elogio", "ofensa", "noticia", "sobre_bot","ack" ] else "fora_de_contexto"

    except Exception as e:
        print(f"[⚠️ INTENÇÃO ERRO]: {e}")
        return "fora_de_contexto"

def responder_mensagem_geral(mensagem: str, sender: str) -> str:
    try:
        # 1. Verifica se já existe thread para o usuário
        thread_id = thread_manager.get_thread(sender)

        # 2. Se não tiver, cria nova thread
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            thread_manager.register_thread(sender, thread_id)

        # 3. Envia mensagem para a thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=mensagem
        )

        # 4. Executa o assistente
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=os.getenv("OPENAI_ASSISTANT_ID")
        )

        # 5. Aguarda conclusão
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(0.5)

        # 6. Busca última mensagem gerada
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        resposta = messages.data[0].content[0].text.value

        # 7. Atualiza contador
        thread_manager.increment_message_count(sender)

        return resposta.strip()

    except Exception as e:
        print(f"[⚠️ ERRO AO RESPONDER GERAL]: {e}")
        return "⚠️ Deu erro ao tentar responder agora. Tente de novo mais tarde."

def responder_noticia(mensagem: str, sender: str) -> str:
    """
    Responde perguntas de notícia (lesões, escalação, rumores, etc.)
    usando Chat Completions + web_search embutido.
    """
    try:
        # 1. Verifica se já existe thread para o usuário
        thread_id = thread_manager.get_thread(sender)

        # 2. Se não tiver, cria nova thread
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            thread_manager.register_thread(sender, thread_id)

        # 3. Faz a chamada com o tool de busca habilitado
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": mensagem}],
            web_search_options={          # opcional
                "user_location": {
                    "type": "approximate",
                    "approximate": {
                        "country": "BR"
                    }
                }
            }
        )

        resposta = response.choices[0].message.content.strip()

        # 4. Atualiza o histórico local
        thread_manager.increment_message_count(sender)

        return resposta

    except Exception as e:
        print(f"[⚠️ ERRO AO RESPONDER NOTÍCIA]: {e}")
        return "⚠️ Deu erro ao buscar notícias agora. Tente de novo mais tarde."