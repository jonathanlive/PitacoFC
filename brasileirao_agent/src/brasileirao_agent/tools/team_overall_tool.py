import json
import os
import re
import unicodedata
from selenium.webdriver.chrome.options import Options
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import time

# Dicionário com ID dos times
TIMES_BRASILEIRAO_2025 = {
    "palmeiras": 1963,
    "flamengo": 5981,
    "red bull bragantino": 1999,
    "fluminense": 1961,
    "internacional": 1966,
    "botafogo": 1958,
    "ceara": 2001,
    "sao paulo": 1981,
    "cruzeiro": 1954,
    "corinthians": 1957,
    "vasco": 1974,
    "juventude": 1980,
    "mirassol": 21982,
    "fortaleza": 2020,
    "atletico mineiro": 1977,
    "bahia": 1955,
    "vitoria": 1962,
    "santos": 1968,
    "gremio": 5926,
    "sport recife": 1959
}

# Traduções de métricas
STATISTICS_TRANSLATION = {
    "goalsScored": "Gols Marcados",
    "goalsConceded": "Gols Sofridos",
    "ownGoals": "Gols Contra",
    "assists": "Assistências",
    "shots": "Total de Finalizações",
    "penaltyGoals": "Gols de Pênalti",
    "penaltiesTaken": "Pênaltis Cobrados",
    "freeKickGoals": "Gols de Falta",
    "freeKickShots": "Finalizações de Falta",
    "goalsFromInsideTheBox": "Gols Dentro da Área",
    "goalsFromOutsideTheBox": "Gols Fora da Área",
    "shotsFromInsideTheBox": "Finalizações Dentro da Área",
    "shotsFromOutsideTheBox": "Finalizações Fora da Área",
    "headedGoals": "Gols de Cabeça",
    "leftFootGoals": "Gols com o Pé Esquerdo",
    "rightFootGoals": "Gols com o Pé Direito",
    "bigChances": "Grandes Chances Criadas",
    "bigChancesCreated": "Grandes Chances de Gol Criadas",
    "bigChancesMissed": "Grandes Chances Perdidas",
    "shotsOnTarget": "Chutes no Gol",
    "shotsOffTarget": "Chutes para Fora",
    "blockedScoringAttempt": "Finalizações Bloqueadas",
    "successfulDribbles": "Dribles Certos",
    "dribbleAttempts": "Tentativas de Drible",
    "corners": "Escanteios",
    "hitWoodwork": "Bolas na Trave",
    "fastBreaks": "Contra-Ataques",
    "fastBreakGoals": "Gols em Contra-Ataque",
    "fastBreakShots": "Chutes em Contra-Ataque",
    "averageBallPossession": "Posse de Bola (%)",
    "totalPasses": "Total de Passes",
    "accuratePasses": "Passes Certos",
    "accuratePassesPercentage": "Precisão de Passes (%)",
    "cleanSheets": "Jogos sem Sofrer Gol",
    "tackles": "Desarmes",
    "interceptions": "Interceptações",
    "saves": "Defesas",
    "errorsLeadingToGoal": "Erros que Levaram a Gol",
    "errorsLeadingToShot": "Erros que Levaram a Finalização",
    "penaltiesCommited": "Pênaltis Cometidos",
    "penaltyGoalsConceded": "Gols de Pênalti Sofridos",
    "clearances": "Cortes",
    "duelsWonPercentage": "Disputas Vencidas (%)",
    "groundDuelsWonPercentage": "Disputas no Chão Vencidas (%)",
    "aerialDuelsWonPercentage": "Disputas Aéreas Vencidas (%)",
    "totalDuels": "Total de Disputas",
    "duelsWon": "Disputas Vencidas",
    "yellowCards": "Cartões Amarelos",
    "redCards": "Cartões Vermelhos",
    "possessionLost": "Perdas de Bola",
    "fouls": "Faltas Cometidas",
    "offsides": "Impedimentos",
    "avgRating": "Nota Média Sofascore"
}

class TeamOverallToolInput(BaseModel):
    name: str = Field(..., description="Nome(s) do(s) time(s) desejado(s). Exemplo: 'Flamengo e Palmeiras'.")

class TeamOverallTool(BaseTool):
    name: str = "Estatísticas Completas de Times Brasileirão"
    description: str = (
        "Retorna estatísticas gerais do Brasileirão 2025 para um ou mais times especificados, "
        "incluindo métricas traduzidas como gols, assistências, posse de bola, entre outras."
    )
    args_schema: Type[BaseModel] = TeamOverallToolInput

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text

    def _run(self, name: str) -> str:
        time_normalizado = self._normalize_text(name)
        ids_encontrados = []

        for nome_time, id_time in TIMES_BRASILEIRAO_2025.items():
            if nome_time in time_normalizado:
                ids_encontrados.append((nome_time, id_time))

        if not ids_encontrados:
            return "⚽ Não encontrei nenhum time informado no Brasileirão 2025."

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--single-process')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36')
        # Detecta se está rodando em container Linux
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)

        try:
            resultados_finais = {}

            for nome_time, id_time in ids_encontrados:
                url = f"https://www.sofascore.com/api/v1/team/{id_time}/unique-tournament/325/season/72034/statistics/overall"
                driver.get(url)
                time.sleep(1)

                raw = driver.find_element("tag name", "pre").get_attribute("innerText")
                data = json.loads(raw)

                estatisticas_raw = data.get("statistics", {})
                if not estatisticas_raw:
                    resultados_finais[nome_time.title()] = "⚽ Nenhuma estatística encontrada."
                    continue

                estatisticas_traduzidas = {}
                for key, value in estatisticas_raw.items():
                    nome_traduzido = STATISTICS_TRANSLATION.get(key)
                    if nome_traduzido:
                        # Verifica se é um campo percentual
                        if "%" in nome_traduzido and isinstance(value, (float, int)):
                            estatisticas_traduzidas[nome_traduzido] = round(value, 1)  # Arredonda para 1 casa decimal
                        else:
                            estatisticas_traduzidas[nome_traduzido] = value

                resultados_finais[nome_time.title()] = estatisticas_traduzidas

            return json.dumps(resultados_finais, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"⚠️ Erro inesperado ao buscar estatísticas dos times: {str(e)}"
        finally:
            driver.quit()
