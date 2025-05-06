import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brasileirao_agent.crew import BrasileiraoAgent

def executar_crew(pergunta: str,sender: str) -> str:
    print(f"[🎯 CREW] Iniciando análise para pergunta: {pergunta} | Usuário: {sender}")
    inputs = { "pergunta": pergunta }
    try:
        output = BrasileiraoAgent().crew().kickoff(inputs=inputs)
        print(f"[📤 RESPOSTA FINAL] {output}")
        return str(output)
    except Exception as e:
        return f"⚠️ Erro ao rodar Crew: {e}"
