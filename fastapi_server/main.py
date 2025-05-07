import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_server.tasks import processar_pergunta_task
from fastapi_server.intencao_llm import classificar_intencao, responder_mensagem_geral, responder_noticia

app = FastAPI()

@app.post("/perguntar")
async def crew_handler(request: Request):
    try:
        body = await request.json()
        pergunta = body.get("pergunta", "").strip()
        sender = body.get("sender", "").strip()

        if not pergunta or not sender:
            return JSONResponse(status_code=400, content={"response": "❌ Dados inválidos."})

        # ✨ Dispara Celery com pergunta + sender
        processar_pergunta_task.delay(pergunta, sender)

        return JSONResponse(content={"response": "📡 Sua pergunta está sendo analisada! Assim que terminar, te mando a resposta! ⚽"})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"response": f"❌ Erro interno: {str(e)}"}
        )

@app.post("/intencao")
async def detectar_intencao(request: Request):
    try:
        body = await request.json()
        mensagem = body.get("mensagem", "").strip()
        historico = body.get("historico", [])

        if not mensagem:
            return JSONResponse(
                status_code=400,
                content={"intencao": "desconhecida", "motivo": "Mensagem vazia"}
            )

        intencao = classificar_intencao(mensagem, historico)

        print(f"\n[🔎 DEBUG] Mensagem recebida: '{mensagem}'")
        print(f"[🔎 DEBUG] Histórico recente: {historico}")
        print(f"[🔎 DEBUG] Intenção classificada: '{intencao}'\n")

        return JSONResponse(content={"intencao": intencao})

    except Exception as e:
        print(f"[⚠️ ERRO DETECTAR INTENÇÃO]: {e}")
        return JSONResponse(
            status_code=500,
            content={"intencao": "desconhecida", "erro": str(e)}
        )

@app.post("/futebol_geral")
async def futebol_geral_handler(request: Request):
    try:
        body = await request.json()
        pergunta = body.get("pergunta", "").strip()
        sender = body.get("sender", "").strip()

        if not pergunta or not sender:
            return JSONResponse(status_code=400, content={"response": "❌ Dados inválidos."})

        resposta = responder_mensagem_geral(pergunta, sender)
        return JSONResponse(content={"response": resposta})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"response": f"❌ Erro interno: {str(e)}"}
        )

@app.post("/noticia")
async def noticia_handler(request: Request):
    """
    Lida com perguntas classificadas como 'noticia' (lesões, escalações, rumores).
    Utiliza responder_noticia, que por sua vez chama Chat Completions
    com tool_choice={"type":"web_search"} para forçar a busca.
    """
    try:
        body = await request.json()
        pergunta = body.get("pergunta", "").strip()
        sender   = body.get("sender", "").strip()

        if not pergunta or not sender:
            return JSONResponse(status_code=400,
                                content={"response": "❌ Dados inválidos."})

        resposta = responder_noticia(pergunta, sender)
        return JSONResponse(content={"response": resposta})

    except Exception as e:
        return JSONResponse(status_code=500,
                            content={"response": f"❌ Erro interno: {str(e)}"})