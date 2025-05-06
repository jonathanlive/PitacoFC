# fastapi_server/tasks.py
from fastapi_server.celery_app import celery_app
from fastapi_server.brasileirao_connector import executar_crew
import requests
import os

BOT_URL = os.getenv("BOT_URL", "http://localhost:8080")  # Ajuste a porta onde seu bot rodar

@celery_app.task
def processar_pergunta_task(pergunta: str, sender: str):
    resposta = executar_crew(pergunta,sender)

    try:
        # Envia a resposta final para o bot
        payload = {
            "sender": sender,
            "resposta": resposta
        }
        requests.post(f"{BOT_URL}/responder", json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar resposta para o bot: {str(e)}")

    return "Mensagem enviada"

