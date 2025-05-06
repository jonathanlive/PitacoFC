import json
from selenium.webdriver.chrome.options import Options
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

class RoundInsightsInput(BaseModel):
    rodada: int = Field(..., ge=1, le=38, description="Número da rodada do Brasileirão (entre 1 e 38)")

class RoundInsightsTool(BaseTool):
    name: str = "Informações de Rodada Específica do Brasileirão"
    description: str = (
        "Retorna um resumo detalhado dos jogos de uma rodada específica do Brasileirão, "
        "incluindo resultados, placares parciais, quem venceu dentro/fora de casa, "
        "se houve acréscimos e número de expulsões."
    )
    args_schema: Type[BaseModel] = RoundInsightsInput

    def _run(self, rodada: int) -> str:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'
        )
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            # Buscar os jogos da rodada específica
            events_url = f"https://www.sofascore.com/api/v1/unique-tournament/325/season/72034/events/round/{rodada}"
            driver.get(events_url)
            raw_events = driver.find_element("tag name", "pre").get_attribute("innerText")
            data_events = json.loads(raw_events)

            jogos = []

            for event in data_events.get("events", []):
                home_team = event.get("homeTeam", {}).get("name")
                away_team = event.get("awayTeam", {}).get("name")
                home_score = event.get("homeScore", {})
                away_score = event.get("awayScore", {})
                injury_time1 = event.get("time", {}).get("injuryTime1", 0)
                injury_time2 = event.get("time", {}).get("injuryTime2", 0)

                vencedor = self._determinar_vencedor(event)
                vencedor_local = self._determinar_vencedor_local(event)

                jogo = {
                    "Rodada": rodada,
                    "Casa": home_team,
                    "Fora": away_team,
                    "Placar Casa 1T": home_score.get("period1", 0),
                    "Placar Casa 2T": home_score.get("period2", 0),
                    "Placar Fora 1T": away_score.get("period1", 0),
                    "Placar Fora 2T": away_score.get("period2", 0),
                    "Placar Final Casa": home_score.get("current", 0),
                    "Placar Final Fora": home_score.get("current", 0),
                    "Status": event.get("status", {}).get("description"),
                    "Vencedor": vencedor,
                    "Venceu Jogando": vencedor_local,
                    "Acréscimos 1T": injury_time1 if injury_time1 > 0 else 0,
                    "Acréscimos 2T": injury_time2 if injury_time2 > 0 else 0,
                    "Expulsões Casa": event.get("homeRedCards", 0),
                    "Expulsões Fora": event.get("awayRedCards", 0)
                }
                jogos.append(jogo)

            return json.dumps(jogos, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"⚠️ Erro inesperado: {str(e)}"

        finally:
            driver.quit()

    def _determinar_vencedor(self, event: dict) -> str:
        winner_code = event.get("winnerCode")
        if winner_code == 1:
            return event.get("homeTeam", {}).get("name", "Casa")
        elif winner_code == 2:
            return event.get("awayTeam", {}).get("name", "Fora")
        elif winner_code == 3:
            return "Empate"
        else:
            return "Indefinido"

    def _determinar_vencedor_local(self, event: dict) -> str:
        winner_code = event.get("winnerCode")
        if winner_code == 1:
            return "Casa"
        elif winner_code == 2:
            return "Fora"
        elif winner_code == 3:
            return "Empate"
        else:
            return "Indefinido"
