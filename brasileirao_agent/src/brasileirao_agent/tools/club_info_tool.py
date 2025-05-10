import os, json, math, collections, statistics as stats, unicodedata, re
from datetime import datetime, timezone
from difflib import get_close_matches
from typing import Type, Dict, List
from pydantic import BaseModel, Field
from crewai_tools import BaseTool

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver


# ---------- HELPERS -------------------------------------------------
def _normalize(txt: str) -> str:
    """lowercase + sem acento + só alfanumérico (p/ fuzzy robusto)."""
    nfkd = unicodedata.normalize("NFKD", txt.lower())
    sem_acento = u"".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r"[^a-z0-9]", "", sem_acento)

def _age(ts: int) -> int:
    return math.floor((datetime.now(timezone.utc).timestamp() - ts) / 31_556_952)

def _date(ts: int) -> str:
    try:
        return datetime.utcfromtimestamp(ts).strftime("%d/%m/%Y")
    except Exception:
        return "?"

def _val(player: dict) -> int:
    raw = player.get("proposedMarketValue", 0)
    return raw.get("value", 0) if isinstance(raw, dict) else (raw or 0)

def _fee(t: dict) -> int:
    return t.get("transferFeeRaw", {}).get("value", 0)

def _fetch(url: str) -> dict:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")

    if os.path.exists("/usr/bin/chromium"):
        opts.binary_location = "/usr/bin/chromium"
        svc = Service("/usr/bin/chromedriver")
    else:
        from webdriver_manager.chrome import ChromeDriverManager
        svc = Service(ChromeDriverManager().install())

    drv = webdriver.Chrome(service=svc, options=opts)
    drv.get(url)
    raw = drv.find_element("tag name", "pre").get_attribute("innerText")
    drv.quit()
    return json.loads(raw)


# ---------- ALIAS → ID ---------------------------------------------
_clubes: Dict[int, List[str]] = {
    1963: ["palmeiras", "verdão", "porco"],
    5981: ["flamengo", "mengão", "mengo", "urubu"],
    1977: ["atletico mineiro", "atlético mineiro", "galo"],
    1958: ["botafogo", "fogão", "glorioso"],
    5926: ["gremio", "grêmio", "imortal", "tricolor gaúcho"],
    2020: ["fortaleza", "leão do pici"],
    1966: ["internacional", "inter", "colorado"],
    1961: ["fluminense", "flu", "tricolor carioca"],
    1981: ["sao paulo", "são paulo", "tricolor paulista", "soberano"],
    1957: ["corinthians", "timão", "timao"],
    1999: ["red bull bragantino", "bragantino", "massa bruta"],
    1954: ["cruzeiro", "raposa"],
    1974: ["vasco da gama", "vasco", "vascão", "gigante da colina"],
    1955: ["bahia", "esquadrão"],
    1968: ["santos", "peixe", "alvinegro praiano"],
    1980: ["juventude"],
    1962: ["vitoria", "vitória", "leão da barra"],
    21982: ["mirassol", "leão mirassolense"],
    2001: ["ceará", "ceara", "vozão", "vozao"]
}

# gera alias2id normalizado
alias2id = {
    _normalize(alias): cid
    for cid, aliases in _clubes.items()
    for alias in aliases
}


# ---------- INPUT ---------------------------------------------------
class ClubInfoInput(BaseModel):
    nome_time: str = Field(..., description="Nome (mesmo incompleto ou apelido) do clube")


# ---------- TOOL ----------------------------------------------------
class ClubInfoTool(BaseTool):
    name: str = "Informacoes Gerais do Clube"               # ✅
    description: str = (                                    # ✅  <-- agora com 'str'
        "Retorna, em texto compacto, dados do clube, elenco, "
        "transferências e métricas agregadas prontas para análise."
    )
    args_schema: Type[BaseModel] = ClubInfoInput

    # ----------------------------------------------------------------
    def _run(self, nome_time: str) -> str:
        try:
            buscado = _normalize(nome_time)
            # fuzzy sobre aliases normalizados
            candidatos = get_close_matches(buscado, alias2id.keys(), n=1, cutoff=0.6)
            if not candidatos:
                return f"⚠️ Clube '{nome_time}' não encontrado."
            tid = alias2id[candidatos[0]]

            # --- 2. Endpoints ---------------------------------------
            info   = _fetch(f"https://www.sofascore.com/api/v1/team/{tid}")
            squad  = _fetch(f"https://www.sofascore.com/api/v1/team/{tid}/players")
            trans  = _fetch(f"https://www.sofascore.com/api/v1/team/{tid}/transfers")

            team   = info["team"]
            pre    = info.get("pregameForm", {})
            players        = squad.get("players", [])
            transfers_in   = trans.get("transfersIn", [])
            transfers_out  = trans.get("transfersOut", [])

            # ---------- 3. Cabeçalho clube --------------------------
            txt = f"\n📊 Informações do clube: {team['name']}\n"
            txt += f"Fundado em: {_date(team.get('foundationDateTimestamp', 0))}\n"

            cores = team.get("teamColors", {})
            txt += f"Cores: {cores.get('primary')} | {cores.get('secondary')}\n"

            mgr = team.get("manager", {})
            venue = team.get("venue", {})
            txt += (
                f"Treinador: {mgr.get('name')} "
                f"({mgr.get('country', {}).get('name')})\n"
            )
            txt += (
                f"Estádio: {venue.get('name')} | Cap.: {venue.get('capacity')} | "
                f"{venue.get('city', {}).get('name')}\n"
            )

            comps = {c.get('name') for c in (
                team.get('tournament', {}),
                team.get('primaryUniqueTournament', {})
            ) if c}
            txt += f"Competições: {', '.join(comps)}\n"

            form = ' - '.join(pre.get('form', [])) or "–"
            txt += (
                f"Forma: {form} | Posição: {pre.get('position')} | "
                f"Nota média: {pre.get('avgRating')}\n\n"
            )

            # ---------- 4. Elenco ----------------------------------
            roster = [
                f"{p['player']['name']} | {p['player'].get('position', '??')} | "
                f"{_age(p['player'].get('dateOfBirthTimestamp',0))}a | "
                f"€{_val(p['player'])/1e6:.1f}M"
                for p in players
            ]
            txt += "🗒️ Elenco (nome | pos | idade | valor):\n" + "\n".join(roster) + "\n"

            # ---------- 5. Métricas elenco --------------------------
            ages   = [_age(p["player"]["dateOfBirthTimestamp"])
                      for p in players if p["player"].get("dateOfBirthTimestamp")]
            values = [_val(p["player"]) for p in players]
            pos_cnt = collections.Counter(
                p["player"].get("position", "??")
                for p in players if p.get("player")
            )

            txt += "\n➕ Métricas do elenco:\n"
            txt += f"- Tamanho: {len(players)} jogadores\n"
            txt += f"- Idade média: {round(stats.mean(ages),1) if ages else '?'} anos\n"
            txt += f"- Valor de mercado total: €{sum(values):,}\n"
            txt += "- Por posição: " + ", ".join(f"{p}: {q}" for p,q in pos_cnt.items()) + "\n"

            # ---------- 6. Transferências ---------------------------
            spent   = sum(_fee(t) for t in transfers_in)
            revenue = sum(_fee(t) for t in transfers_out)
            net     = spent - revenue

            linhas_in = [
                f"{_date(t['transferDateTimestamp'])} | "
                f"{t['player']['name']} ({t['player'].get('position','??')}) <- {t['fromTeamName']} | "
                f"€{_fee(t)/1e6:.1f}M"
                for t in transfers_in
            ]
            linhas_out = [
                f"{_date(t['transferDateTimestamp'])} | "
                f"{t['player']['name']} ({t['player'].get('position','??')}) -> {t['toTeamName']} | "
                f"€{_fee(t)/1e6:.1f}M"
                for t in transfers_out
            ]

            free_in  = sum(1 for t in transfers_in  if _fee(t) == 0)
            free_out = sum(1 for t in transfers_out if _fee(t) == 0)

            biggest_buy  = max(transfers_in,  key=_fee, default=None)
            biggest_sale = max(transfers_out, key=_fee, default=None)
            pos_in_cnt   = collections.Counter(
                t["player"].get("position", "??") for t in transfers_in
            )

            txt += "\n💸 Transferências (última janela):\n"
            txt += (f"- Entradas: {len(transfers_in)} | Saídas: {len(transfers_out)} | "
                    f"Saldo atletas: {len(transfers_in)-len(transfers_out)}\n")
            txt += f"- Gasto: €{spent:,} | Receita: €{revenue:,} | **Net spend: €{net:,}**\n"
            txt += f"- Gratuitas/Empréstimo: {free_in} in, {free_out} out\n"
            txt += "- Compras por posição: " + ", ".join(f"{p}: {q}" for p,q in pos_in_cnt.items()) + "\n"

            if biggest_buy:
                txt += (f"- Maior compra: {biggest_buy['player']['name']} "
                        f"({biggest_buy['transferFeeDescription']})\n")
            if biggest_sale:
                txt += (f"- Maior venda: {biggest_sale['player']['name']} "
                        f"({biggest_sale['transferFeeDescription']})\n")

            txt += "\n➡️ Entradas:\n" + "\n".join(linhas_in or ["–"])
            txt += "\n⬅️ Saídas:\n"  + "\n".join(linhas_out or ["–"])

            return txt

        except Exception as e:
            return f"❌ Erro ao buscar dados: {e}"
