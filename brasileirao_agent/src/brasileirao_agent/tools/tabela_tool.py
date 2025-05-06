import json
import os
from selenium.webdriver.chrome.options import Options
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

class TabelaToolInput(BaseModel):
    """Input vazio para TabelaTool (nenhum argumento necessário)."""
    pass


class TabelaTool(BaseTool):
    name: str = "Tabela Atual do Brasileirão"
    description: str = (
        "Retorna a tabela atualizada do Campeonato Brasileiro com dados essenciais de cada time: "
        "jogos, vitórias, empates, derrotas, saldo de gols, gols feitos, gols sofridos, pontos."
    )
    args_schema: Type[BaseModel] = TabelaToolInput

    def _run(self) -> str:
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_argument('--single-process')
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

            # Usando o webdriver manager pra simplificar
            # Detecta se está rodando em container Linux
            if os.path.exists("/usr/bin/chromium"):
                options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
            else:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=options)

            url = "https://www.sofascore.com/api/v1/unique-tournament/325/season/72034/standings/total"
            driver.get(url)
            json_text = driver.find_element("tag name", "pre").get_attribute("innerText")
            driver.quit()
            data = json.loads(json_text)
            rows = data["standings"][0]["rows"]

            tabela = []
            for row in rows:
                nome = row["team"]["name"]
                jogos = row["matches"]
                vitorias = row["wins"]
                empates = row["draws"]
                derrotas = row["losses"]
                gols_pro = row["scoresFor"]
                gols_contra = row["scoresAgainst"]
                saldo = gols_pro - gols_contra
                pontos = row["points"]

                linha = (
                    f"{row['position']:>2}º - {nome} | "
                    f"Pontos: {pontos}, Jogos: {jogos}, "
                    f"V: {vitorias}, E: {empates}, D: {derrotas}, "
                    f"Gols Pró: {gols_pro}, Contra: {gols_contra}, "
                    f"Saldo: {saldo:+}"
                )
                tabela.append(linha)

            print(tabela)
            return "\n".join(tabela)

        except Exception as e:
            return f"⚠️ Erro inesperado: {str(e)}"
