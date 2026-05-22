"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
═══════════════════════════════════════════════════════════════════════════════
Architecture:
  - Instant static fallbacks guarantee dropdowns always populate immediately
  - Live API data enriches / replaces static lists when keys are active
  - All API calls are cached aggressively to avoid blocking the sidebar
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import hashlib
import base64
import requests
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class APIConfig:
    @staticmethod
    def _clean(key: str) -> str:
        return str(key).strip() if key else ""

    API_SPORTS_KEY        = _clean(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL        = "https://v3.football.api-sports.io"

    ODDS_API_KEY          = _clean(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL          = "https://api.the-odds-api.com/v4"

    SPORTMONKS_KEY        = _clean(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL        = "https://api.sportmonks.com/api/v3/football"

    MYSPORTSFEEDS_KEY     = _clean(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL     = "https://api.mysportsfeeds.com/v2.1/pull"

    FOOTBALL_DATA_KEY     = _clean(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL     = "https://api.football-data.org/v4"

    THESPORTSDB_KEY       = _clean(os.getenv("TheSportDB_API_key", "3"))
    THESPORTSDB_URL_V1    = "https://www.thesportsdb.com/api/v1/json"

    # TTLs
    TTL_LIVE    = 30
    TTL_UPCOMING = 600
    TTL_LEAGUES  = 86400

    REQUEST_TIMEOUT = 8
    MAX_RETRIES     = 2
    RETRY_DELAY     = 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# INSTANT STATIC FALLBACKS — always populated, never empty
# ═══════════════════════════════════════════════════════════════════════════════

STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Soccer": [
        {"id": "39",  "name": "Premier League",       "country": "England"},
        {"id": "140", "name": "La Liga",               "country": "Spain"},
        {"id": "135", "name": "Serie A",               "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",            "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",               "country": "France"},
        {"id": "2",   "name": "UEFA Champions League", "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",    "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League","country": "Europe"},
        {"id": "253", "name": "MLS",                   "country": "USA"},
        {"id": "71",  "name": "Brasileirao",           "country": "Brazil"},
        {"id": "128", "name": "Algerian Ligue Pro",    "country": "Algeria"},
        {"id": "233", "name": "Nigerian NPFL",         "country": "Nigeria"},
        {"id": "29",  "name": "CAF Champions League",  "country": "Africa"},
        {"id": "20",  "name": "Coupe de France",       "country": "France"},
        {"id": "45",  "name": "FA Cup",                "country": "England"},
        {"id": "143", "name": "Copa del Rey",          "country": "Spain"},
        {"id": "88",  "name": "Eredivisie",            "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",         "country": "Portugal"},
        {"id": "144", "name": "Belgian Pro League",    "country": "Belgium"},
        {"id": "197", "name": "Super Lig",             "country": "Turkey"},
        {"id": "119", "name": "Superliga",             "country": "Denmark"},
        {"id": "113", "name": "Allsvenskan",           "country": "Sweden"},
        {"id": "283", "name": "Saudi Pro League",      "country": "Saudi Arabia"},
        {"id": "307", "name": "UAE Pro League",        "country": "UAE"},
        {"id": "169", "name": "Egyptian Premier League","country": "Egypt"},
    ],
    "NBA": [
        {"id": "NBA", "name": "NBA — All Teams", "country": "USA/Canada"},
        {"id": "ATL", "name": "Atlanta Hawks",           "country": "USA"},
        {"id": "BOS", "name": "Boston Celtics",          "country": "USA"},
        {"id": "BKN", "name": "Brooklyn Nets",           "country": "USA"},
        {"id": "CHA", "name": "Charlotte Hornets",       "country": "USA"},
        {"id": "CHI", "name": "Chicago Bulls",           "country": "USA"},
        {"id": "CLE", "name": "Cleveland Cavaliers",     "country": "USA"},
        {"id": "DAL", "name": "Dallas Mavericks",        "country": "USA"},
        {"id": "DEN", "name": "Denver Nuggets",          "country": "USA"},
        {"id": "DET", "name": "Detroit Pistons",         "country": "USA"},
        {"id": "GSW", "name": "Golden State Warriors",   "country": "USA"},
        {"id": "HOU", "name": "Houston Rockets",         "country": "USA"},
        {"id": "IND", "name": "Indiana Pacers",          "country": "USA"},
        {"id": "LAC", "name": "LA Clippers",             "country": "USA"},
        {"id": "LAL", "name": "LA Lakers",               "country": "USA"},
        {"id": "MEM", "name": "Memphis Grizzlies",       "country": "USA"},
        {"id": "MIA", "name": "Miami Heat",              "country": "USA"},
        {"id": "MIL", "name": "Milwaukee Bucks",         "country": "USA"},
        {"id": "MIN", "name": "Minnesota Timberwolves",  "country": "USA"},
        {"id": "NOP", "name": "New Orleans Pelicans",    "country": "USA"},
        {"id": "NYK", "name": "New York Knicks",         "country": "USA"},
        {"id": "OKC", "name": "Oklahoma City Thunder",   "country": "USA"},
        {"id": "ORL", "name": "Orlando Magic",           "country": "USA"},
        {"id": "PHI", "name": "Philadelphia 76ers",      "country": "USA"},
        {"id": "PHX", "name": "Phoenix Suns",            "country": "USA"},
        {"id": "POR", "name": "Portland Trail Blazers",  "country": "USA"},
        {"id": "SAC", "name": "Sacramento Kings",        "country": "USA"},
        {"id": "SAS", "name": "San Antonio Spurs",       "country": "USA"},
        {"id": "TOR", "name": "Toronto Raptors",         "country": "Canada"},
        {"id": "UTA", "name": "Utah Jazz",               "country": "USA"},
        {"id": "WAS", "name": "Washington Wizards",      "country": "USA"},
    ],
    "NFL": [
        {"id": "NFL", "name": "NFL — All Teams", "country": "USA"},
        {"id": "ARI", "name": "Arizona Cardinals",       "country": "USA"},
        {"id": "ATL", "name": "Atlanta Falcons",         "country": "USA"},
        {"id": "BAL", "name": "Baltimore Ravens",        "country": "USA"},
        {"id": "BUF", "name": "Buffalo Bills",           "country": "USA"},
        {"id": "CAR", "name": "Carolina Panthers",       "country": "USA"},
        {"id": "CHI", "name": "Chicago Bears",           "country": "USA"},
        {"id": "CIN", "name": "Cincinnati Bengals",      "country": "USA"},
        {"id": "CLE", "name": "Cleveland Browns",        "country": "USA"},
        {"id": "DAL", "name": "Dallas Cowboys",          "country": "USA"},
        {"id": "DEN", "name": "Denver Broncos",          "country": "USA"},
        {"id": "DET", "name": "Detroit Lions",           "country": "USA"},
        {"id": "GB",  "name": "Green Bay Packers",       "country": "USA"},
        {"id": "HOU", "name": "Houston Texans",          "country": "USA"},
        {"id": "IND", "name": "Indianapolis Colts",      "country": "USA"},
        {"id": "JAX", "name": "Jacksonville Jaguars",    "country": "USA"},
        {"id": "KC",  "name": "Kansas City Chiefs",      "country": "USA"},
        {"id": "LV",  "name": "Las Vegas Raiders",       "country": "USA"},
        {"id": "LAC", "name": "LA Chargers",             "country": "USA"},
        {"id": "LAR", "name": "LA Rams",                 "country": "USA"},
        {"id": "MIA", "name": "Miami Dolphins",          "country": "USA"},
        {"id": "MIN", "name": "Minnesota Vikings",       "country": "USA"},
        {"id": "NE",  "name": "New England Patriots",    "country": "USA"},
        {"id": "NO",  "name": "New Orleans Saints",      "country": "USA"},
        {"id": "NYG", "name": "NY Giants",               "country": "USA"},
        {"id": "NYJ", "name": "NY Jets",                 "country": "USA"},
        {"id": "PHI", "name": "Philadelphia Eagles",     "country": "USA"},
        {"id": "PIT", "name": "Pittsburgh Steelers",     "country": "USA"},
        {"id": "SF",  "name": "San Francisco 49ers",     "country": "USA"},
        {"id": "SEA", "name": "Seattle Seahawks",        "country": "USA"},
        {"id": "TB",  "name": "Tampa Bay Buccaneers",    "country": "USA"},
        {"id": "TEN", "name": "Tennessee Titans",        "country": "USA"},
        {"id": "WAS", "name": "Washington Commanders",   "country": "USA"},
    ],
    "MLB": [
        {"id": "MLB", "name": "MLB — All Teams", "country": "USA/Canada"},
        {"id": "ARI", "name": "Arizona Diamondbacks",    "country": "USA"},
        {"id": "ATL", "name": "Atlanta Braves",          "country": "USA"},
        {"id": "BAL", "name": "Baltimore Orioles",       "country": "USA"},
        {"id": "BOS", "name": "Boston Red Sox",          "country": "USA"},
        {"id": "CHC", "name": "Chicago Cubs",            "country": "USA"},
        {"id": "CWS", "name": "Chicago White Sox",       "country": "USA"},
        {"id": "CIN", "name": "Cincinnati Reds",         "country": "USA"},
        {"id": "CLE", "name": "Cleveland Guardians",     "country": "USA"},
        {"id": "COL", "name": "Colorado Rockies",        "country": "USA"},
        {"id": "DET", "name": "Detroit Tigers",          "country": "USA"},
        {"id": "HOU", "name": "Houston Astros",          "country": "USA"},
        {"id": "KC",  "name": "Kansas City Royals",      "country": "USA"},
        {"id": "LAA", "name": "LA Angels",               "country": "USA"},
        {"id": "LAD", "name": "LA Dodgers",              "country": "USA"},
        {"id": "MIA", "name": "Miami Marlins",           "country": "USA"},
        {"id": "MIL", "name": "Milwaukee Brewers",       "country": "USA"},
        {"id": "MIN", "name": "Minnesota Twins",         "country": "USA"},
        {"id": "NYM", "name": "NY Mets",                 "country": "USA"},
        {"id": "NYY", "name": "NY Yankees",              "country": "USA"},
        {"id": "OAK", "name": "Oakland Athletics",       "country": "USA"},
        {"id": "PHI", "name": "Philadelphia Phillies",   "country": "USA"},
        {"id": "PIT", "name": "Pittsburgh Pirates",      "country": "USA"},
        {"id": "SD",  "name": "San Diego Padres",        "country": "USA"},
        {"id": "SF",  "name": "San Francisco Giants",    "country": "USA"},
        {"id": "SEA", "name": "Seattle Mariners",        "country": "USA"},
        {"id": "STL", "name": "St. Louis Cardinals",     "country": "USA"},
        {"id": "TB",  "name": "Tampa Bay Rays",          "country": "USA"},
        {"id": "TEX", "name": "Texas Rangers",           "country": "USA"},
        {"id": "TOR", "name": "Toronto Blue Jays",       "country": "Canada"},
        {"id": "WSH", "name": "Washington Nationals",    "country": "USA"},
    ],
    "NHL": [
        {"id": "NHL", "name": "NHL — All Teams", "country": "USA/Canada"},
        {"id": "ANA", "name": "Anaheim Ducks",           "country": "USA"},
        {"id": "BOS", "name": "Boston Bruins",           "country": "USA"},
        {"id": "BUF", "name": "Buffalo Sabres",          "country": "USA"},
        {"id": "CGY", "name": "Calgary Flames",          "country": "Canada"},
        {"id": "CAR", "name": "Carolina Hurricanes",     "country": "USA"},
        {"id": "CHI", "name": "Chicago Blackhawks",      "country": "USA"},
        {"id": "COL", "name": "Colorado Avalanche",      "country": "USA"},
        {"id": "CBJ", "name": "Columbus Blue Jackets",   "country": "USA"},
        {"id": "DAL", "name": "Dallas Stars",            "country": "USA"},
        {"id": "DET", "name": "Detroit Red Wings",       "country": "USA"},
        {"id": "EDM", "name": "Edmonton Oilers",         "country": "Canada"},
        {"id": "FLA", "name": "Florida Panthers",        "country": "USA"},
        {"id": "LAK", "name": "LA Kings",                "country": "USA"},
        {"id": "MIN", "name": "Minnesota Wild",          "country": "USA"},
        {"id": "MTL", "name": "Montreal Canadiens",      "country": "Canada"},
        {"id": "NSH", "name": "Nashville Predators",     "country": "USA"},
        {"id": "NJD", "name": "New Jersey Devils",       "country": "USA"},
        {"id": "NYI", "name": "NY Islanders",            "country": "USA"},
        {"id": "NYR", "name": "NY Rangers",              "country": "USA"},
        {"id": "OTT", "name": "Ottawa Senators",         "country": "Canada"},
        {"id": "PHI", "name": "Philadelphia Flyers",     "country": "USA"},
        {"id": "PIT", "name": "Pittsburgh Penguins",     "country": "USA"},
        {"id": "SJS", "name": "San Jose Sharks",         "country": "USA"},
        {"id": "SEA", "name": "Seattle Kraken",          "country": "USA"},
        {"id": "STL", "name": "St. Louis Blues",         "country": "USA"},
        {"id": "TBL", "name": "Tampa Bay Lightning",     "country": "USA"},
        {"id": "TOR", "name": "Toronto Maple Leafs",     "country": "Canada"},
        {"id": "VAN", "name": "Vancouver Canucks",       "country": "Canada"},
        {"id": "VGK", "name": "Vegas Golden Knights",    "country": "USA"},
        {"id": "WSH", "name": "Washington Capitals",     "country": "USA"},
        {"id": "WPG", "name": "Winnipeg Jets",           "country": "Canada"},
    ],
    "UFC": [
        {"id": "UFC_ALL",    "name": "All UFC Events",       "country": "World"},
        {"id": "UFC_FW",     "name": "Featherweight",        "country": "World"},
        {"id": "UFC_LW",     "name": "Lightweight",          "country": "World"},
        {"id": "UFC_WW",     "name": "Welterweight",         "country": "World"},
        {"id": "UFC_MW",     "name": "Middleweight",         "country": "World"},
        {"id": "UFC_LHW",    "name": "Light Heavyweight",    "country": "World"},
        {"id": "UFC_HW",     "name": "Heavyweight",          "country": "World"},
        {"id": "UFC_WMSTRAW","name": "Women's Strawweight",  "country": "World"},
        {"id": "UFC_WMFLY",  "name": "Women's Flyweight",    "country": "World"},
        {"id": "UFC_WMBW",   "name": "Women's Bantamweight", "country": "World"},
    ],
    "Formula 1": [
        {"id": "F1_ALL",  "name": "All Races",           "country": "World"},
        {"id": "F1_AUS",  "name": "Australian GP",       "country": "Australia"},
        {"id": "F1_CHN",  "name": "Chinese GP",          "country": "China"},
        {"id": "F1_JPN",  "name": "Japanese GP",         "country": "Japan"},
        {"id": "F1_BHR",  "name": "Bahrain GP",          "country": "Bahrain"},
        {"id": "F1_SAU",  "name": "Saudi Arabian GP",    "country": "Saudi Arabia"},
        {"id": "F1_MIA",  "name": "Miami GP",            "country": "USA"},
        {"id": "F1_ITA",  "name": "Emilia Romagna GP",   "country": "Italy"},
        {"id": "F1_MON",  "name": "Monaco GP",           "country": "Monaco"},
        {"id": "F1_CAN",  "name": "Canadian GP",         "country": "Canada"},
        {"id": "F1_ESP",  "name": "Spanish GP",          "country": "Spain"},
        {"id": "F1_AUT",  "name": "Austrian GP",         "country": "Austria"},
        {"id": "F1_GBR",  "name": "British GP",          "country": "England"},
        {"id": "F1_HUN",  "name": "Hungarian GP",        "country": "Hungary"},
        {"id": "F1_BEL",  "name": "Belgian GP",          "country": "Belgium"},
        {"id": "F1_NLD",  "name": "Dutch GP",            "country": "Netherlands"},
        {"id": "F1_ITA2", "name": "Italian GP",          "country": "Italy"},
        {"id": "F1_AZE",  "name": "Azerbaijan GP",       "country": "Azerbaijan"},
        {"id": "F1_SGP",  "name": "Singapore GP",        "country": "Singapore"},
        {"id": "F1_USA",  "name": "United States GP",    "country": "USA"},
        {"id": "F1_MEX",  "name": "Mexico City GP",      "country": "Mexico"},
        {"id": "F1_BRA",  "name": "São Paulo GP",        "country": "Brazil"},
        {"id": "F1_LVG",  "name": "Las Vegas GP",        "country": "USA"},
        {"id": "F1_QAT",  "name": "Qatar GP",            "country": "Qatar"},
        {"id": "F1_UAE",  "name": "Abu Dhabi GP",        "country": "UAE"},
    ],
    "Tennis": [
        {"id": "ATP",          "name": "ATP Tour",           "country": "World"},
        {"id": "WTA",          "name": "WTA Tour",           "country": "World"},
        {"id": "WIMBLEDON",    "name": "Wimbledon",          "country": "England"},
        {"id": "US_OPEN",      "name": "US Open",            "country": "USA"},
        {"id": "FRENCH_OPEN",  "name": "Roland Garros",      "country": "France"},
        {"id": "AUS_OPEN",     "name": "Australian Open",    "country": "Australia"},
        {"id": "ATP_FINALS",   "name": "ATP Finals",         "country": "Italy"},
        {"id": "DAVIS_CUP",    "name": "Davis Cup",          "country": "World"},
        {"id": "UNITED_CUP",   "name": "United Cup",         "country": "Australia"},
    ],
    "Cricket": [
        {"id": "IPL",     "name": "Indian Premier League",   "country": "India"},
        {"id": "BBL",     "name": "Big Bash League",         "country": "Australia"},
        {"id": "PSL",     "name": "Pakistan Super League",   "country": "Pakistan"},
        {"id": "CPL",     "name": "Caribbean Premier League","country": "Caribbean"},
        {"id": "SA20",    "name": "SA20",                    "country": "South Africa"},
        {"id": "ILT20",   "name": "ILT20",                   "country": "UAE"},
        {"id": "TEST",    "name": "Test Matches",            "country": "World"},
        {"id": "ODI",     "name": "ODI Internationals",      "country": "World"},
        {"id": "T20I",    "name": "T20 Internationals",      "country": "World"},
        {"id": "CT",      "name": "Champions Trophy",        "country": "World"},
        {"id": "WC",      "name": "ICC World Cup",           "country": "World"},
    ],
    "Golf": [
        {"id": "PGA",      "name": "PGA Tour",               "country": "USA"},
        {"id": "EUROPEAN", "name": "DP World Tour",          "country": "Europe"},
        {"id": "MASTERS",  "name": "The Masters",            "country": "USA"},
        {"id": "PGA_CHAMP","name": "PGA Championship",       "country": "USA"},
        {"id": "US_OPEN",  "name": "US Open",                "country": "USA"},
        {"id": "THE_OPEN", "name": "The Open Championship",  "country": "UK"},
        {"id": "PLAYERS",  "name": "The Players Championship","country": "USA"},
        {"id": "RYDER_CUP","name": "Ryder Cup",              "country": "World"},
        {"id": "LIV",      "name": "LIV Golf",               "country": "World"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Match:
    match_id:     str
    provider:     str
    league:       str
    league_id:    str
    home_team:    str
    away_team:    str
    home_team_id: Optional[str]      = None
    away_team_id: Optional[str]      = None
    home_score:   Optional[int]      = None
    away_score:   Optional[int]      = None
    status:       str                = "SCHEDULED"
    minute:       Optional[int]      = None
    start_time:   Optional[datetime] = None
    venue:        Optional[str]      = None
    country:      Optional[str]      = None

    def to_dataframe_row(self) -> Dict:
        su = self.status.upper()
        is_live = any(x in su for x in [
            "LIVE", "1H", "2H", "HT", "IN_PROGRESS",
            "1ST", "2ND", "3RD", "4TH", "OT", "IN_PLAY",
        ])
        is_done = any(x in su for x in [
            "FINISHED", "FT", "AET", "PEN", "COMPLETED", "FINAL",
        ])
        if is_live:
            display = "🔴 LIVE"
        elif is_done:
            display = "✅ FINISHED"
        else:
            display = "⏳ UPCOMING"

        return {
            "MATCH_ID":  self.match_id,
            "TIME":      self.start_time.strftime("%d %b %H:%M") if self.start_time else "TBD",
            "LEAGUE":    self.league,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "MATCH":     f"{self.home_team} vs {self.away_team}",
            "STATUS":    display,
            "SCORE":     f"{self.home_score}-{self.away_score}"
                         if self.home_score is not None else "vs",
            "PROVIDER":  self.provider,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class DataProvider:
    def __init__(self, name: str):
        self.name  = name
        self.cache: Dict[str, Any] = {}

    def _make_request(self, url: str, headers: Dict = None,
                      params: Dict = None) -> Optional[Dict]:
        for attempt in range(APIConfig.MAX_RETRIES):
            try:
                r = requests.get(
                    url,
                    headers=headers or {},
                    params=params or {},
                    timeout=APIConfig.REQUEST_TIMEOUT,
                )
                if r.status_code == 429:
                    time.sleep((attempt + 1) * 2)
                    continue
                if r.status_code == 200:
                    return r.json()
                logger.warning(f"[{self.name}] HTTP {r.status_code} {url}")
                return None
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.name}] Timeout attempt {attempt+1}")
            except Exception as e:
                logger.error(f"[{self.name}] {e}")
            if attempt < APIConfig.MAX_RETRIES - 1:
                time.sleep(APIConfig.RETRY_DELAY * (attempt + 1))
        return None

    def _ck(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get(self, key: str, ttl: int) -> Optional[Any]:
        e = self.cache.get(key)
        return e["v"] if e and time.time() - e["t"] < ttl else None

    def _set(self, key: str, val: Any):
        self.cache[key] = {"v": val, "t": time.time()}


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS  (Soccer)
# ═══════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.base    = APIConfig.API_SPORTS_URL
        self.headers = {"x-apisports-key": APIConfig.API_SPORTS_KEY} \
                       if APIConfig.API_SPORTS_KEY else {}

    @property
    def ok(self) -> bool:
        return bool(APIConfig.API_SPORTS_KEY)

    def get_leagues(self) -> List[Dict]:
        """Return soccer leagues from API, merged over static fallback."""
        if not self.ok:
            return []
        ck = self._ck("apisports_leagues")
        cached = self._get(ck, APIConfig.TTL_LEAGUES)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base}/leagues", self.headers)
        if not data:
            return []
        leagues = []
        for item in data.get("response", []):
            lg = item.get("league", {})
            co = item.get("country", {})
            leagues.append({
                "id":      str(lg.get("id", "")),
                "name":    lg.get("name", "Unknown"),
                "country": co.get("name", ""),
            })
        self._set(ck, leagues)
        return leagues

    def get_live_matches(self, league_id: str = None) -> List[Match]:
        if not self.ok:
            return []
        ck = self._ck("apisports_live", league_id)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        params = {"live": "all"}
        if league_id and league_id not in ("ALL", ""):
            params["league"] = league_id
        data = self._make_request(f"{self.base}/fixtures", self.headers, params)
        matches = self._parse_fixtures(data) if data else []
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        ck = self._ck("apisports_upcoming", today)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base}/fixtures", self.headers,
                                  {"from": today, "to": future})
        matches = self._parse_fixtures(data) if data else []
        self._set(ck, matches)
        return matches

    def _parse_fixtures(self, data: Dict) -> List[Match]:
        matches = []
        for fx in data.get("response", []):
            f      = fx.get("fixture", {})
            league = fx.get("league", {})
            teams  = fx.get("teams", {})
            goals  = fx.get("goals", {})
            status = f.get("status", {})
            start  = None
            if f.get("date"):
                try:
                    start = datetime.fromisoformat(f["date"].replace("Z", "+00:00"))
                except Exception:
                    pass
            matches.append(Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=league.get("name", "Unknown"),
                league_id=str(league.get("id", "")),
                home_team=teams.get("home", {}).get("name", "Home"),
                away_team=teams.get("away", {}).get("name", "Away"),
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                status=status.get("short", "NS"),
                minute=status.get("elapsed"),
                start_time=start,
                venue=f.get("venue", {}).get("name"),
                country=league.get("country"),
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS  (NBA · NFL · MLB · NHL)
# ═══════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    CODES = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}

    def __init__(self):
        super().__init__("MySportsFeeds")
        self.base = APIConfig.MYSPORTSFEEDS_URL
        if APIConfig.MYSPORTSFEEDS_KEY and APIConfig.MYSPORTSFEEDS_PASSWORD:
            creds = base64.b64encode(
                f"{APIConfig.MYSPORTSFEEDS_KEY}:{APIConfig.MYSPORTSFEEDS_PASSWORD}".encode()
            ).decode()
            self.headers = {"Authorization": f"Basic {creds}"}
        else:
            self.headers = {}

    @property
    def ok(self) -> bool:
        return bool(self.headers)

    def _season(self, sport: str) -> str:
        now = datetime.now()
        s   = sport.upper()
        if s in ("NBA", "NHL"):
            return f"{now.year}-{now.year+1}" if now.month >= 10 else f"{now.year-1}-{now.year}"
        if s == "NFL":
            return str(now.year) if now.month >= 8 else str(now.year - 1)
        return str(now.year)  # MLB

    def _code(self, sport: str) -> str:
        return self.CODES.get(sport.upper(), "nba")

    def get_live_matches(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        code  = self._code(sport)
        season = self._season(sport)
        today = datetime.now().strftime("%Y%m%d")
        ck = self._ck("msf_live", code, today)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        url  = f"{self.base}/{code}/{season}/date/{today}/games.json"
        data = self._make_request(url, self.headers)
        if not data:
            data = self._make_request(
                f"{self.base}/{code}/{season}/games.json", self.headers, {"date": today}
            )
        matches = self._parse(data, sport) if data else []
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        code  = self._code(sport)
        season = self._season(sport)
        today  = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        ck = self._ck("msf_upcoming", code, today)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._make_request(
            f"{self.base}/{code}/{season}/games.json", self.headers,
            {"fordate": today, "todate": future},
        )
        matches = self._parse(data, sport, upcoming_only=True) if data else []
        self._set(ck, matches)
        return matches

    def _parse(self, data: Dict, sport: str, upcoming_only: bool = False) -> List[Match]:
        matches = []
        for game in data.get("games", []):
            sched      = game.get("schedule", game)
            raw_status = sched.get("playedStatus", sched.get("status", "UNPLAYED")).upper()
            is_live    = raw_status in ("IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT")
            is_done    = raw_status in ("COMPLETED", "FINAL", "COMPLETED_PENDING_REVIEW")
            if upcoming_only and (is_live or is_done):
                continue
            ht = sched.get("homeTeam", {})
            at = sched.get("awayTeam", {})
            home = (f"{ht.get('city','')} {ht.get('name','')}".strip()
                    if isinstance(ht, dict) else str(ht)) or "TBD"
            away = (f"{at.get('city','')} {at.get('name','')}".strip()
                    if isinstance(at, dict) else str(at)) or "TBD"
            sc = game.get("score", {}) or {}
            start = None
            for key in ("startTime", "startDate", "date"):
                raw = sched.get(key, "")
                if raw:
                    try:
                        start = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass
            matches.append(Match(
                match_id=str(sched.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home,
                away_team=away,
                home_score=sc.get("homeScoreTotal"),
                away_score=sc.get("awayScoreTotal"),
                status="LIVE" if is_live else ("FINISHED" if is_done else "SCHEDULED"),
                start_time=start,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB  (UFC · F1 · Tennis · Cricket · Golf)
# ═══════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    LEAGUE_IDS = {
        "UFC":       "4467",
        "Formula 1": "4370",
        "Tennis":    "4424",
        "Cricket":   "4722",
        "Golf":      "4426",
    }

    def __init__(self):
        super().__init__("TheSportsDB")
        self.key  = APIConfig.THESPORTSDB_KEY or "3"
        self.base = APIConfig.THESPORTSDB_URL_V1

    def _req(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        url = f"{self.base}/{self.key}/{endpoint}"
        return self._make_request(url, params=params)

    def get_live_matches(self, sport: str) -> List[Match]:
        ck = self._ck("tsdb_live", sport)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        sport_map = {
            "UFC": "MMA", "Formula 1": "Motorsport",
            "Tennis": "Tennis", "Cricket": "Cricket", "Golf": "Golf",
        }
        data = self._req("livescore.php", {"s": sport_map.get(sport, sport)})
        matches = []
        if data and data.get("events"):
            for ev in data["events"]:
                is_live = ev.get("strStatus") in [
                    "1H", "2H", "HT", "IN_PLAY", "ET", "PEN_LIVE", "LIVE"
                ]
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(
                            f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M"
                        )
                    except Exception:
                        pass
                matches.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    home_score=_toint(ev.get("intHomeScore")),
                    away_score=_toint(ev.get("intAwayScore")),
                    status="LIVE" if is_live else (ev.get("strStatus") or "SCHEDULED"),
                    start_time=start,
                ))
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        league_id = self.LEAGUE_IDS.get(sport)
        if not league_id:
            return []
        ck = self._ck("tsdb_upcoming", sport)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._req("eventsnextleague.php", {"id": league_id})
        matches = []
        if data and data.get("events"):
            for ev in data["events"]:
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(
                            f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M"
                        )
                    except Exception:
                        pass
                matches.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    status="SCHEDULED",
                    start_time=start,
                ))
        self._set(ck, matches)
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _toint(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    def __init__(self):
        self.api_sports      = APISportsProvider()
        self.my_sports_feeds = MySportsFeedsProvider()
        self.the_sports_db   = TheSportsDBProvider()
        self.connection_log: List[Dict] = []
        self._log_initial_status()

    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME":     datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": provider,
            "STATUS":   status,
            "DETAIL":   str(detail)[:80],
        })

    def _log_initial_status(self):
        checks = [
            ("API-SPORTS",    bool(APIConfig.API_SPORTS_KEY),    "Soccer live data"),
            ("MySportsFeeds", bool(APIConfig.MYSPORTSFEEDS_KEY), "NBA/NFL/MLB/NHL data"),
            ("TheSportsDB",   True,                               "UFC/F1/Tennis/Cricket/Golf"),
            ("TheOddsAPI",    bool(APIConfig.ODDS_API_KEY),       "Odds data"),
            ("Football-Data", bool(APIConfig.FOOTBALL_DATA_KEY),  "Soccer backup"),
        ]
        for name, active, detail in checks:
            self._log(name, "READY" if active else "NOT CONFIGURED", detail)

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        return pd.DataFrame(self.connection_log).tail(60)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "API-SPORTS",
             "status": "🟢 ONLINE" if APIConfig.API_SPORTS_KEY else "⚪ NOT CONFIGURED"},
            {"name": "MySportsFeeds",
             "status": "🟢 ONLINE" if APIConfig.MYSPORTSFEEDS_KEY else "⚪ NOT CONFIGURED"},
            {"name": "TheSportsDB",
             "status": "🟢 ONLINE"},
            {"name": "TheOddsAPI",
             "status": "🟢 ONLINE" if APIConfig.ODDS_API_KEY else "⚪ NOT CONFIGURED"},
            {"name": "Football-Data",
             "status": "🟢 ONLINE" if APIConfig.FOOTBALL_DATA_KEY else "⚪ NOT CONFIGURED"},
        ]

    # ── Leagues  ──────────────────────────────────────────────────────────────
    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        """
        ALWAYS returns instantly from static fallback.
        If API-SPORTS key is live and sport is Soccer, enriches asynchronously
        and returns full API list on subsequent calls (already cached).
        """
        static = STATIC_LEAGUES.get(sport_type, [{"id": "ALL", "name": "All Events", "country": "World"}])

        # For Soccer with an active API key: try cache first, then return static
        if sport_type == "Soccer" and self.api_sports.ok:
            ck = self.api_sports._ck("apisports_leagues")
            cached = self.api_sports._get(ck, APIConfig.TTL_LEAGUES)
            if cached:
                self._log("API-SPORTS", "CACHE HIT", f"{len(cached)} soccer leagues")
                return cached
            # Return static immediately; warm cache in background thread
            def _warm():
                try:
                    leagues = self.api_sports.get_leagues()
                    if leagues:
                        self._log("API-SPORTS", "ENRICHED",
                                  f"{len(leagues)} soccer leagues cached")
                except Exception as e:
                    self._log("API-SPORTS", "ERROR", str(e))
            threading.Thread(target=_warm, daemon=True).start()

        return static

    # ── Live matches  ─────────────────────────────────────────────────────────
    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        try:
            if sport_type == "Soccer":
                matches = self.api_sports.get_live_matches(league_id)
                self._log("API-SPORTS", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live soccer")
            elif sport_type in ("NBA", "NFL", "MLB", "NHL"):
                matches = self.my_sports_feeds.get_live_matches(sport_type)
                self._log("MySportsFeeds", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live {sport_type}")
            elif sport_type in ("UFC", "Formula 1", "Tennis", "Cricket", "Golf"):
                matches = self.the_sports_db.get_live_matches(sport_type)
                self._log("TheSportsDB", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live {sport_type}")
            else:
                return pd.DataFrame()

            return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        except Exception as e:
            self._log("ROUTER", "ERROR", f"live {sport_type}: {e}")
            return pd.DataFrame()

    # ── Upcoming matches  ─────────────────────────────────────────────────────
    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        try:
            if sport_type == "Soccer":
                matches = self.api_sports.get_upcoming_matches()
                self._log("API-SPORTS", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming soccer")
            elif sport_type in ("NBA", "NFL", "MLB", "NHL"):
                matches = self.my_sports_feeds.get_upcoming_matches(sport_type)
                self._log("MySportsFeeds", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming {sport_type}")
            elif sport_type in ("UFC", "Formula 1", "Tennis", "Cricket", "Golf"):
                matches = self.the_sports_db.get_upcoming_matches(sport_type)
                self._log("TheSportsDB", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming {sport_type}")
            else:
                return pd.DataFrame()

            return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        except Exception as e:
            self._log("ROUTER", "ERROR", f"upcoming {sport_type}: {e}")
            return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD FACADE
# ═══════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self) -> bool:
        return bool(
            APIConfig.API_SPORTS_KEY
            or APIConfig.MYSPORTSFEEDS_KEY
            or APIConfig.THESPORTSDB_KEY
        )

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_type: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(sport_type)

    # Stubs
    def get_match_prediction(self, match_id: str): return None
    def get_match_details(self, match_id: str):    return {"found": False}
    def get_team_form(self, team_name: str, match_id: str): return None
    def get_head_to_head(self, home: str, away: str, match_id: str): return []
    def get_key_players(self, match_id: str):      return []
    def get_match_odds(self, match_id: str):       return {}
    def get_ai_reasoning(self, match_id: str):     return []


__all__ = ["APIConfig", "EmpireDashboardData"]
