import json
from selenium.webdriver.chrome.options import Options
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import time

METRIC_KEYWORDS_MAP = {
    'rating': ['rating', 'nota'],
    'goals': ['gols', 'goals', 'artilheiro'],
    'expectedGoals': ['xg', 'expected goals', 'gols esperados'],
    'assists': ['assistencias', 'assists'],
    'expectedAssists': ['xa', 'assistências esperadas'],
    'goalsAssistsSum': ['participações', 'g+a'],
    'penaltyGoals': ['penalti', 'penalty goals'],
    'freeKickGoal': ['bola parada', 'falta', 'gol de falta'],
    'scoringFrequency': ['frequência de gols', 'scoring frequency'],
    'totalShots': ['finalizações', 'total shots'],
    'shotsOnTarget': ['chutes no gol', 'shots on target'],
    'bigChancesMissed': ['chances perdidas'],
    'bigChancesCreated': ['chances criadas'],
    'accuratePasses': ['passes certos'],
    'keyPasses': ['passes decisivos', 'key passes'],
    'accurateLongBalls': ['bolas longas'],
    'successfulDribbles': ['dribles certos'],
    'penaltyWon': ['penalti sofrido'],
    'tackles': ['desarmes'],
    'interceptions': ['interceptações'],
    'clearances': ['cortes'],
    'possessionLost': ['posse perdida'],
    'yellowCards': ['cartões amarelos'],
    'redCards': ['cartões vermelhos'],
    'saves': ['defesas'],
    'goalsPrevented': ['gols evitados'],
    'mostConceded': ['mais gols sofridos'],
    'leastConceded': ['menos gols sofridos'],
    'cleanSheet': ['clean sheet', 'jogos sem sofrer gols'],
}

class PlayerOverallToolInput(BaseModel):
    metric: str = Field(..., description="Métrica desejada (ex: 'gols', 'xg', 'assistências')")

class PlayerOverallTool(BaseTool):
    name: str = "Estatísticas Individuais Brasileirão"
    description: str = (
        "Retorna estatísticas dos jogadores do Brasileirão com base em métricas como gols, xG, assistências, "
        "defesas, dribles, entre outras. Aceita entrada textual livre como 'top xg', 'melhor em gols', etc."
    )
    args_schema: Type[BaseModel] = PlayerOverallToolInput

    def _run(self, metric: str) -> str:
        # Normaliza e tenta encontrar a métrica correspondente
        metric_lower = metric.lower()
        selected_metric = None
        for key, keywords in METRIC_KEYWORDS_MAP.items():
            if any(k in metric_lower for k in keywords):
                selected_metric = key
                break

        if not selected_metric:
            return f"❌ Não consegui identificar a métrica com base em: '{metric}'"
        
        # Setup do navegador
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            url = "https://www.sofascore.com/api/v1/unique-tournament/325/season/72034/top-players/overall"
            driver.get(url)
            raw = driver.find_element("tag name", "pre").get_attribute("innerText")
            data = json.loads(raw)

            metric_data = data.get("topPlayers", {}).get(selected_metric, [])
            resultado = []

            for item in metric_data:
                player_info = {
                    "Jogador": item["player"]["name"],
                    "Time": item["team"]["name"],
                    "Jogos": item["statistics"].get("appearances", 0)
                }
                player_info.update(item["statistics"])
                resultado.append(player_info)

            return json.dumps(resultado, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"⚠️ Erro inesperado: {str(e)}"
        finally:
            driver.quit()
