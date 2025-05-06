# fastapi_server/tasks.py
from fastapi_server.celery_app import celery_app
from fastapi_server.brasileirao_connector import executar_crew
import requests
import os

BOT_URL = os.getenv("BOT_URL", "http://localhost:8080")  # Ajuste a porta onde seu bot rodar

@celery_app.task
def processar_pergunta_task(pergunta: str, sender: str):
    print(f"[🧠 Pergunta recebida] '{pergunta}' de {sender}")

    resposta = executar_crew(pergunta, sender)
    print(f"[✅ Resposta gerada] {resposta[:200]}...")  # Trunca pra evitar poluir os logs

    payload = {
        "sender": sender,
        "resposta": resposta
    }

    try:
        print(f"[📡 Enviando para BOT_URL: {BOT_URL}/responder] Payload: {payload}")
        response = requests.post(f"{BOT_URL}/responder", json=payload, timeout=10)
        print(f"[✅ RESPOSTA HTTP] Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"[❌ ERRO AO ENVIAR RESPOSTA PARA O BOT] {str(e)}")

    return "Mensagem enviada"

