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

class PlayersStatsToolInput(BaseModel):
    jogador: str = Field(..., description="Nome(s) do jogador ou jogadores. Pode ser uma string como 'Memphis Depay, Neymar' ou JSON mal formatado.")

class PlayersStatsTool(BaseTool):
    name: str = "Estatísticas Completas Brasileirão por Jogador"
    description: str = (
        "Extrai estatísticas detalhadas dos jogadores do Brasileirão 2025 com base nos nomes fornecidos. "
        "Aceita múltiplos nomes separados por vírgulas ou estruturas misturadas. "
        "Retorna dados como gols, assistências, xG, rating, passes certos, desarmes, dribles e muito mais."
    )
    args_schema: Type[BaseModel] = PlayersStatsToolInput

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text

    def _run(self, jogador: str) -> str:
        jogador = self._normalize_text(jogador)
        palavras_busca = list(set(jogador.replace(',', ' ').split()))

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--single-process')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        )
        # Detecta se está rodando em container Linux
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)

        try:
            resultado = []
            encontrados = set()
            base_url = (
                "https://www.sofascore.com/api/v1/unique-tournament/325/season/72034/statistics?"
                "limit=100&order=-rating&offset={offset}&accumulation=total&"
                "fields=goals%2CsuccessfulDribblesPercentage%2CblockedShots%2CpenaltyWon%2CgoalsFromOutsideTheBox%2C"
                "hitWoodwork%2Crating%2CexpectedGoals%2CtotalShots%2CgoalConversionPercentage%2CshotFromSetPiece%2CheadedGoals%2C"
                "offsides%2CbigChancesMissed%2CshotsOnTarget%2CpenaltiesTaken%2CfreeKickGoal%2CleftFootGoals%2CpenaltyConversion%2C"
                "successfulDribbles%2CshotsOffTarget%2CpenaltyGoals%2CgoalsFromInsideTheBox%2CrightFootGoals%2CsetPieceConversion%2C"
                "tackles%2CerrorLeadToGoal%2CcleanSheet%2Cinterceptions%2CerrorLeadToShot%2CpenaltyConceded%2CownGoals%2Cclearances%2C"
                "dribbledPast%2CbigChancesCreated%2CtotalPasses%2CaccurateFinalThirdPasses%2CaccurateLongBalls%2Cassists%2C"
                "accuratePassesPercentage%2CkeyPasses%2CaccurateLongBallsPercentage%2CaccuratePasses%2CaccurateOwnHalfPasses%2C"
                "accurateCrosses%2CpassToAssist%2CinaccuratePasses%2CaccurateOppositionHalfPasses%2CaccurateCrossesPercentage%2C"
                "saves%2CsavedShotsFromInsideTheBox%2Cpunches%2CcrossesNotClaimed%2CsavedShotsFromOutsideTheBox%2CrunsOut%2C"
                "penaltyFaced%2CgoalsConcededInsideTheBox%2CsuccessfulRunsOut%2CpenaltySave%2CgoalsConcededOutsideTheBox%2C"
                "highClaims%2CyellowCards%2CaerialDuelsWon%2CminutesPlayed%2CpossessionLost%2CredCards%2CaerialDuelsWonPercentage%2C"
                "wasFouled%2Cappearances%2CgroundDuelsWon%2CtotalDuelsWon%2Cfouls%2CmatchesStarted%2CgroundDuelsWonPercentage%2C"
                "totalDuelsWonPercentage%2Cdispossessed&filters=position.in.G~D~M~F"
            )

            for page in range(0, 5):
                offset = page * 100
                url = base_url.format(offset=offset)
                driver.get(url)
                time.sleep(1)

                raw = driver.find_element("tag name", "pre").get_attribute("innerText")
                data = json.loads(raw)

                for player_data in data.get("results", []):
                    player_name_normalized = self._normalize_text(player_data["player"]["name"])

                    if any(palavra in player_name_normalized for palavra in palavras_busca):
                        if player_data["player"]["id"] not in encontrados:
                            jogador_info = {
                                "Jogador": player_data["player"]["name"],
                                "Time": player_data["team"]["name"],
                                "Gols": player_data.get("goals", 0),
                                "Assistências": player_data.get("assists", 0),
                                "Gols Esperados (xG)": player_data.get("expectedGoals", 0),
                                "Dribles Certos": player_data.get("successfulDribbles", 0),
                                "Dribles Certos (%)": player_data.get("successfulDribblesPercentage", 0),
                                "Finalizações Bloqueadas": player_data.get("blockedShots", 0),
                                "Penaltis Sofridos": player_data.get("penaltyWon", 0),
                                "Gols Fora da Área": player_data.get("goalsFromOutsideTheBox", 0),
                                "Bolas na Trave": player_data.get("hitWoodwork", 0),
                                "Finalizações Totais": player_data.get("totalShots", 0),
                                "Finalizações no Gol": player_data.get("shotsOnTarget", 0),
                                "Chances Claras Perdidas": player_data.get("bigChancesMissed", 0),
                                "Conversão de Finalização (%)": player_data.get("goalConversionPercentage", 0),
                                "Penaltis Marcados": player_data.get("penaltyGoals", 0),
                                "Penaltis Perdidos": player_data.get("penaltiesTaken", 0),
                                "Conversão de Penalti (%)": player_data.get("penaltyConversion", 0),
                                "Finalizações Fora do Gol": player_data.get("shotsOffTarget", 0),
                                "Gols de Cabeça": player_data.get("headedGoals", 0),
                                "Gols de Pé Esquerdo": player_data.get("leftFootGoals", 0),
                                "Gols de Pé Direito": player_data.get("rightFootGoals", 0),
                                "Desarmes": player_data.get("tackles", 0),
                                "Interceptações": player_data.get("interceptions", 0),
                                "Erros que Levaram a Gol": player_data.get("errorLeadToGoal", 0),
                                "Erros que Levaram a Finalização": player_data.get("errorLeadToShot", 0),
                                "Desarmes Sofridos": player_data.get("dribbledPast", 0),
                                "Cortes": player_data.get("clearances", 0),
                                "Perda de Posse": player_data.get("possessionLost", 0),
                                "Assistências para Finalização": player_data.get("keyPasses", 0),
                                "Passes Certos": player_data.get("accuratePasses", 0),
                                "Passes Certos (%)": player_data.get("accuratePassesPercentage", 0),
                                "Crosses Certos": player_data.get("accurateCrosses", 0),
                                "Crosses Certos (%)": player_data.get("accurateCrossesPercentage", 0),
                                "Cartões Amarelos": player_data.get("yellowCards", 0),
                                "Cartões Vermelhos": player_data.get("redCards", 0),
                                "Minutos Jogados": player_data.get("minutesPlayed", 0),
                                "Disputas de Bola Vencidas": player_data.get("groundDuelsWon", 0),
                                "Disputas de Bola Vencidas (%)": player_data.get("groundDuelsWonPercentage", 0),
                                "Total de Disputas Vencidas": player_data.get("totalDuelsWon", 0),
                                "Total de Disputas Vencidas (%)": player_data.get("totalDuelsWonPercentage", 0),
                                "Faltas Sofridas": player_data.get("wasFouled", 0),
                                "Faltas Cometidas": player_data.get("fouls", 0),
                                "Partidas Como Titular": player_data.get("matchesStarted", 0)
                            }
                            resultado.append(jogador_info)
                            encontrados.add(player_data["player"]["id"])

            if not resultado:
                return "⚽ Nenhuma estatística encontrada para o(s) jogador(es) informado(s) no Brasileirão 2025."

            return json.dumps(resultado, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"⚠️ Erro inesperado: {str(e)}"
        finally:
            driver.quit()
