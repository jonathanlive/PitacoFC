import json
import os
from selenium.webdriver.chrome.options import Options
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

class JogosToolInput(BaseModel):
    """Input vazio para JogosTool (nenhum argumento necessário)."""
    pass

class JogosTool(BaseTool):
    name: str = "Lista com todos os jogos do Brasileirão"
    description: str = (
        "Retorna a lista de jogos atualizada do Campeonato Brasileiro com dados essenciais de cada time: "
        "jogos, vitórias, empates, derrotas, gols feitos, gols sofridos, pontos e últimos 5 resultados, "
        "além de rankings de desempenho em casa e fora."
    )
    args_schema: Type[BaseModel] = JogosToolInput

    def _run(self) -> str:
        try:
            # --- Setup do Chrome headless ---
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_argument('--single-process')
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
            # Detecta se está rodando em container Linux
            if os.path.exists("/usr/bin/chromium"):
                options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
            else:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=options)

            # --- Busca os dados JSON ---
            url = "https://www.sofascore.com/api/v1/unique-tournament/325/season/72034/team-events/total"
            driver.get(url)
            raw = driver.find_element("tag name", "pre").get_attribute("innerText")
            driver.quit()
            data = json.loads(raw)

            # --- Estatísticas para ranking casa/fora ---
            stats = {}  # team_id -> {name, home_w, home_d, home_l, away_w, away_d, away_l}
            for torneio_id, times_map in data["tournamentTeamEvents"].items():
                for team_id, jogos in times_map.items():
                    if team_id not in stats:
                        # pega nome do time de um jogo qualquer futuro
                        nome = (
                            jogos[0]["homeTeam"]["name"]
                            if jogos[0]["homeTeam"]["id"] == int(team_id)
                            else jogos[0]["awayTeam"]["name"]
                        ) if jogos else f"Time {team_id}"
                        stats[team_id] = {
                            "name": nome,
                            "home_w": 0, "home_d": 0, "home_l": 0,
                            "away_w": 0, "away_d": 0, "away_l": 0,
                        }
                    for jogo in jogos:
                        sc_h = jogo["homeScore"]["normaltime"]
                        sc_a = jogo["awayScore"]["normaltime"]
                        if jogo["homeTeam"]["id"] == int(team_id):
                            # jogo em casa
                            if sc_h > sc_a:
                                stats[team_id]["home_w"] += 1
                            elif sc_h == sc_a:
                                stats[team_id]["home_d"] += 1
                            else:
                                stats[team_id]["home_l"] += 1
                        else:
                            # jogo fora
                            if sc_a > sc_h:
                                stats[team_id]["away_w"] += 1
                            elif sc_a == sc_h:
                                stats[team_id]["away_d"] += 1
                            else:
                                stats[team_id]["away_l"] += 1

            # calcula pontos e monta listas ordenadas
            ranking_casa = []
            ranking_fora = []
            for tid, s in stats.items():
                pts_casa = s["home_w"]*3 + s["home_d"]
                pts_fora = s["away_w"]*3 + s["away_d"]
                ranking_casa.append((s["name"], pts_casa, s["home_w"], s["home_d"], s["home_l"]))
                ranking_fora.append((s["name"], pts_fora, s["away_w"], s["away_d"], s["away_l"]))

            ranking_casa.sort(key=lambda x: x[1], reverse=True)
            ranking_fora.sort(key=lambda x: x[1], reverse=True)

            # --- Últimos 5 resultados de cada time ---
            ultimos5_por_time = {}
            for torneio_id, times_map in data["tournamentTeamEvents"].items():
                for team_id, jogos in times_map.items():
                    if not jogos:
                        continue
                    ordenados = sorted(
                        jogos, key=lambda e: e.get("startTimestamp", 0), reverse=True
                    )[:5]
                    # pega nome do time (de novo)
                    primeiro = ordenados[0]
                    nome = (
                        primeiro["homeTeam"]["name"]
                        if primeiro["homeTeam"]["id"] == int(team_id)
                        else primeiro["awayTeam"]["name"]
                    )
                    res = []
                    for j in ordenados:
                        sc_h = j["homeScore"]["normaltime"]
                        sc_a = j["awayScore"]["normaltime"]
                        is_home = int(team_id) == j["homeTeam"]["id"]
                        if sc_h == sc_a:
                            res.append("E")
                        elif (is_home and sc_h > sc_a) or (not is_home and sc_a > sc_h):
                            res.append("V")
                        else:
                            res.append("D")
                    ultimos5_por_time[nome] = "".join(res)

            # --- Monta texto de saída ---
            out = []

            out.append("=== Últimos 5 jogos de cada time ===")
            for nome, forma in ultimos5_por_time.items():
                out.append(f"{nome}: {forma}")

            out.append("\n=== Ranking Desempenho em Casa ===")
            for i, (nome, pts, w, d, l) in enumerate(ranking_casa, start=1):
                out.append(f"{i}. {nome} — {pts} pts (Vitórias: {w}, Empates: {d}, Derrotas: {l})")

            out.append("\n=== Ranking Desempenho Fora de Casa ===")
            for i, (nome, pts, w, d, l) in enumerate(ranking_fora, start=1):
                out.append(f"{i}. {nome} — {pts} pts (Vitórias: {w}, Empates: {d}, Derrotas: {l})")

            return "\n".join(out)

        except Exception as e:
            return f"⚠️ Erro inesperado: {str(e)}"
