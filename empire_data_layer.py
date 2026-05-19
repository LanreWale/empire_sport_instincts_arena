"""
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
"""
import os
import json
import time
import hashlib
import base64
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables from Render
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")

# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS - Loaded from Render Environment Variables
# ════════════════════════════════════════════════════════════════════════════════

def _clean_key(key: str) -> str:
    if not key:
        return ""
    key = str(key).strip()
    if key.startswith("_KEY="):
        key = key[5:]
    if key.startswith("KEY="):
        key = key[4:]
    return key.strip()

# Direct from environment
API_SPORTS_KEY = _clean_key(os.getenv("API_SPORTS_KEY", ""))
ODDS_API_KEY = _clean_key(os.getenv("ODDS_API_KEY", ""))
SPORTMONKS_KEY = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
MYSPORTSFEEDS_KEY = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
FOOTBALL_DATA_KEY = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
THESPORTSDB_KEY = _clean_key(os.getenv("TheSportDB_API_key", "1"))

# Log which keys are loaded (without exposing full keys)
logger.info(f"API_SPORTS_KEY loaded: {'YES' if API_SPORTS_KEY else 'NO'}")
logger.info(f"ODDS_API_KEY loaded: {'YES' if ODDS_API_KEY else 'NO'}")
logger.info(f"SPORTMONKS_KEY loaded: {'YES' if SPORTMONKS_KEY else 'NO'}")
logger.info(f"MYSPORTSFEEDS_KEY loaded: {'YES' if MYSPORTSFEEDS_KEY else 'NO'}")
logger.info(f"FOOTBALL_DATA_KEY loaded: {'YES' if FOOTBALL_DATA_KEY else 'NO'}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION CLASS
# ════════════════════════════════════════════════════════════════════════════════

class APIConfig:
    @staticmethod
    def _clean_key(key: str) -> str:
        if not key:
            return ""
        if key.startswith("_KEY="):
            key = key[5:]
        if key.startswith("KEY="):
            key = key[4:]
        return key.strip()

    @staticmethod
    def _safe_float(value, default=0.0):
        if value is None or value == "" or value == "-":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # API Keys from environment
    API_SPORTS_KEY = API_SPORTS_KEY
    API_SPORTS_URL = "https://v3.football.api-sports.io"
    API_SPORTS_PRIORITY = 1

    ODDS_API_KEY = ODDS_API_KEY
    ODDS_API_URL = "https://api.the-odds-api.com/v4"
    ODDS_API_PRIORITY = 1

    SPORTMONKS_KEY = SPORTMONKS_KEY
    SPORTMONKS_URL = "https://api.sportmonks.com/v3/football"
    SPORTMONKS_PRIORITY = 2

    MYSPORTSFEEDS_KEY = MYSPORTSFEEDS_KEY
    MYSPORTSFEEDS_PASSWORD = MYSPORTSFEEDS_PASSWORD
    MYSPORTSFEEDS_URL = "https://api.mysportsfeeds.com/v2.1/pull"
    MYSPORTSFEEDS_PRIORITY = 2

    FOOTBALL_DATA_KEY = FOOTBALL_DATA_KEY
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    FOOTBALL_DATA_PRIORITY = 3

    THESPORTSDB_KEY = THESPORTSDB_KEY
    THESPORTSDB_URL = "https://www.thesportsdb.com/api/v2/json"
    THESPORTSDB_URL_V1 = "https://www.thesportsdb.com/api/v1/json"
    THESPORTSDB_PRIORITY = 2

    CACHE_TTL_SECONDS = 30
    ODDS_CACHE_TTL = 60
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    REQUEST_TIMEOUT = 10

    @classmethod
    def get_missing_keys(cls) -> List[str]:
        required = {
            "API_SPORTS_KEY": cls.API_SPORTS_KEY,
            "ODDS_API_KEY": cls.ODDS_API_KEY,
            "SPORTMONKS_KEY": cls.SPORTMONKS_KEY,
            "MYSPORTSFEEDS_KEY": cls.MYSPORTSFEEDS_KEY,
            "FOOTBALL_DATA_KEY": cls.FOOTBALL_DATA_KEY,
        }
        return [k for k, v in required.items() if not v]

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.API_SPORTS_KEY or cls.ODDS_API_KEY or cls.SPORTMONKS_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ════════════════════════════════════════════════════════════════════════════════

class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    HALFTIME = "HALFTIME"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


@dataclass
class Match:
    match_id: str
    provider: str
    league: str
    league_id: str
    home_team: str
    away_team: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = MatchStatus.SCHEDULED.value
    minute: Optional[int] = None
    start_time: Optional[datetime] = None
    venue: Optional[str] = None
    country: Optional[str] = None
    season: Optional[str] = None
    round: Optional[str] = None
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_fouls: Optional[int] = None
    away_fouls: Optional[int] = None
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None
    home_win_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    over_25_prob: Optional[float] = None
    btts_prob: Optional[float] = None
    ev_home: Optional[float] = None
    ev_draw: Optional[float] = None
    ev_away: Optional[float] = None
    kelly_home: Optional[float] = None
    kelly_draw: Optional[float] = None
    kelly_away: Optional[float] = None
    confidence: Optional[str] = None
    signal: Optional[str] = None
    home_form: Optional[str] = None
    away_form: Optional[str] = None
    home_goals_scored: Optional[int] = None
    home_goals_conceded: Optional[int] = None
    away_goals_scored: Optional[int] = None
    away_goals_conceded: Optional[int] = None
    h2h_home_wins: Optional[int] = None
    h2h_draws: Optional[int] = None
    h2h_away_wins: Optional[int] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_dataframe_row(self) -> Dict:
        return {
            "MATCH_ID": self.match_id,
            "TIME": self.start_time.strftime("%H:%M") if self.start_time else "TBD",
            "LEAGUE": self.league,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "MATCH": f"{self.home_team} vs {self.away_team}",
            "STATUS": "🔴 LIVE" if self.status in ["LIVE", "HALFTIME"] else ("⏳ " + self.status),
            "SCORE": f"{self.home_score}-{self.away_score}" if self.home_score is not None else "vs",
            "MIN": f"{self.minute}'" if self.minute else "-",
            "HOME": self.home_odds if self.home_odds else "-",
            "DRAW": self.draw_odds if self.draw_odds else "-",
            "AWAY": self.away_odds if self.away_odds else "-",
            "PREDICTION": self._format_prediction(),
            "EV": self._format_ev(),
            "CONF": self.confidence or "-",
            "SIGNAL": self.signal or "-",
        }

    def _format_prediction(self) -> str:
        if self.home_win_prob and self.away_win_prob:
            if self.home_win_prob > self.away_win_prob and self.home_win_prob > (self.draw_prob or 0):
                return f"Home ({self.home_win_prob:.0f}%)"
            elif self.away_win_prob > self.home_win_prob and self.away_win_prob > (self.draw_prob or 0):
                return f"Away ({self.away_win_prob:.0f}%)"
            else:
                return f"Draw ({self.draw_prob:.0f}%)" if self.draw_prob else "Analyzing..."
        return "Analyzing..."

    def _format_ev(self) -> str:
        evs = [e for e in [self.ev_home, self.ev_draw, self.ev_away] if e is not None]
        if evs:
            best = max(evs)
            return f"+{best:.1f}%" if best > 0 else f"{best:.1f}%"
        return "-"


@dataclass
class OddsSnapshot:
    match_id: str
    bookmaker: str
    market: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    timestamp: Optional[datetime] = None

    def to_dataframe_row(self) -> Dict:
        return {
            "BOOKMAKER": self.bookmaker,
            "MARKET": self.market,
            "1": self.home_odds,
            "X": self.draw_odds or "-",
            "2": self.away_odds,
            "O": self.over_odds or "-",
            "U": self.under_odds or "-",
            "TIME": self.timestamp.strftime("%H:%M:%S") if self.timestamp else "-",
        }


@dataclass
class League:
    league_id: str
    name: str
    sport: str
    alternate_name: Optional[str] = None
    country: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TeamForm:
    team_id: str
    team_name: str
    last_5_results: List[str]
    goals_scored: int
    goals_conceded: int
    clean_sheets: int
    avg_possession: Optional[float] = None
    avg_shots: Optional[float] = None
    avg_shots_on_target: Optional[float] = None
    home_form: Optional[List[str]] = None
    away_form: Optional[List[str]] = None


@dataclass
class PredictionResult:
    match_id: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    over_25_prob: float
    btts_prob: float
    confidence: str
    signal: str
    reasoning: List[str]
    home_form_rating: Optional[float] = None
    away_form_rating: Optional[float] = None
    h2h_advantage: Optional[str] = None
    value_bet: Optional[str] = None
    expected_goals_home: Optional[float] = None
    expected_goals_away: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class DataProvider:
    def __init__(self, name: str, priority: int):
        self.name = name
        self.priority = priority
        self.last_call = 0
        self.rate_limit_delay = 1.0
        self.cache = {}

    def _make_request(self, url: str, headers: Dict = None, params: Dict = None) -> Optional[Dict]:
        elapsed = time.time() - self.last_call
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        for attempt in range(APIConfig.MAX_RETRIES):
            try:
                self.last_call = time.time()
                response = requests.get(url, headers=headers, params=params, timeout=APIConfig.REQUEST_TIMEOUT)
                if response.status_code == 429:
                    wait = (attempt + 1) * 2
                    logger.warning(f"{self.name}: Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"{self.name}: Request failed (attempt {attempt + 1}): {e}")
                if attempt < APIConfig.MAX_RETRIES - 1:
                    time.sleep(APIConfig.RETRY_DELAY * (attempt + 1))
        return None

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached(self, cache_key: str, ttl: int = None) -> Optional[Dict]:
        if cache_key not in self.cache:
            return None
        data, timestamp = self.cache[cache_key]
        ttl = ttl or APIConfig.CACHE_TTL_SECONDS
        if time.time() - timestamp > ttl:
            del self.cache[cache_key]
            return None
        return data

    def _set_cached(self, cache_key: str, data: Dict):
        self.cache[cache_key] = (data, time.time())

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        raise NotImplementedError

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        raise NotImplementedError

    def get_upcoming_matches(self, sport: str = "football", days: int = 7) -> List[Match]:
        raise NotImplementedError

    def get_team_form(self, team_id: str, league_id: str = None) -> Optional[TeamForm]:
        raise NotImplementedError

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        raise NotImplementedError

    def get_predictions(self, match_id: str) -> Optional[Match]:
        raise NotImplementedError

    def get_h2h(self, team1_id: str, team2_id: str) -> Optional[Dict]:
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS (API-FOOTBALL) PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS", APIConfig.API_SPORTS_PRIORITY)
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers = {
            "x-rapidapi-key": APIConfig.API_SPORTS_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        self.rate_limit_delay = 0.5

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        cache_key = self._get_cache_key("leagues", {"sport": sport})
        cached = self._get_cached(cache_key, ttl=3600)
        if cached:
            return self._parse_leagues(cached)
        data = self._make_request(f"{self.base_url}/leagues", self.headers)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_leagues(data)

    def _parse_leagues(self, data: Dict) -> List[League]:
        leagues = []
        for item in data.get("response", []):
            league = item.get("league", {})
            country = item.get("country", {})
            leagues.append(League(
                league_id=str(league.get("id", "")),
                name=league.get("name", "Unknown"),
                sport="football",
                alternate_name=league.get("name", ""),
                country=country.get("name", ""),
            ))
        return leagues

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        cache_key = self._get_cache_key("fixtures/live", {"league": league_id})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_fixtures(cached)
        params = {"live": "all"}
        if league_id:
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_upcoming_matches(self, sport: str = "football", days: int = 7) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("fixtures/upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_fixtures(cached)
        params = {"from": today, "to": future, "season": datetime.now().year}
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_team_form(self, team_id: str, league_id: str = None) -> Optional[TeamForm]:
        if not APIConfig.API_SPORTS_KEY or not team_id:
            return None
        cache_key = self._get_cache_key("team_form", {"team": team_id})
        cached = self._get_cached(cache_key, ttl=1800)
        if cached:
            return self._parse_team_form(cached, team_id)
        params = {"team": team_id, "last": 5}
        if league_id:
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return None
        self._set_cached(cache_key, data)
        return self._parse_team_form(data, team_id)

    def _parse_team_form(self, data: Dict, team_id: str) -> Optional[TeamForm]:
        fixtures = data.get("response", [])
        if not fixtures:
            return None
        results = []
        goals_scored = 0
        goals_conceded = 0
        clean_sheets = 0
        team_name = ""
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})
            is_home = str(home_team.get("id")) == str(team_id)
            if not team_name:
                team_name = home_team.get("name", "") if is_home else away_team.get("name", "")
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            if is_home:
                team_goals = home_goals
                opp_goals = away_goals
            else:
                team_goals = away_goals
                opp_goals = home_goals
            goals_scored += team_goals
            goals_conceded += opp_goals
            if opp_goals == 0:
                clean_sheets += 1
            if team_goals > opp_goals:
                results.append("W")
            elif team_goals < opp_goals:
                results.append("L")
            else:
                results.append("D")
        return TeamForm(
            team_id=team_id,
            team_name=team_name,
            last_5_results=results,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            clean_sheets=clean_sheets,
        )

    def get_match_stats(self, fixture_id: str) -> Optional[Dict]:
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = self._get_cache_key("fixtures/statistics", {"fixture": fixture_id})
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        data = self._make_request(f"{self.base_url}/fixtures/statistics", self.headers, {"fixture": fixture_id})
        if data:
            self._set_cached(cache_key, data)
            return data
        return None

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        cache_key = self._get_cache_key("odds", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=APIConfig.ODDS_CACHE_TTL)
        if cached:
            return self._parse_odds(cached, match_id)
        data = self._make_request(f"{self.base_url}/odds", self.headers, {"fixture": match_id})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_odds(data, match_id)

    def get_predictions(self, match_id: str) -> Optional[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = self._get_cache_key("predictions", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=600)
        if cached:
            return self._parse_predictions(cached, match_id)
        data = self._make_request(f"{self.base_url}/predictions", self.headers, {"fixture": match_id})
        if not data:
            return None
        self._set_cached(cache_key, data)
        return self._parse_predictions(data, match_id)

    def get_h2h(self, team1_id: str, team2_id: str) -> Optional[Dict]:
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = self._get_cache_key("h2h", {"h2h": f"{team1_id}-{team2_id}"})
        cached = self._get_cached(cache_key, ttl=3600)
        if cached:
            return cached
        data = self._make_request(f"{self.base_url}/fixtures/headtohead", self.headers, {"h2h": f"{team1_id}-{team2_id}"})
        if data:
            self._set_cached(cache_key, data)
            return data
        return None

    def _parse_fixtures(self, data: Dict) -> List[Match]:
        matches = []
        for fixture in data.get("response", []):
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            status = f.get("status", {})
            match = Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=league.get("name", "Unknown"),
                league_id=str(league.get("id", "")),
                home_team=teams.get("home", {}).get("name", "Home"),
                away_team=teams.get("away", {}).get("name", "Away"),
                home_team_id=str(teams.get("home", {}).get("id", "")),
                away_team_id=str(teams.get("away", {}).get("id", "")),
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                status=status.get("short", "SCH"),
                minute=status.get("elapsed"),
                start_time=datetime.fromisoformat(f.get("date", "").replace("Z", "+00:00")) if f.get("date") else None,
                venue=f.get("venue", {}).get("name"),
                country=league.get("country"),
                season=str(league.get("season", "")),
                round=league.get("round"),
            )
            matches.append(match)
        return matches

    def _parse_odds(self, data: Dict, match_id: str) -> List[OddsSnapshot]:
        snapshots = []
        for odds_data in data.get("response", []):
            bookmaker = odds_data.get("bookmaker", {}).get("name", "Unknown")
            for bet in odds_data.get("bets", []):
                market = bet.get("name", "Unknown")
                values = bet.get("values", [])
                home = draw = away = over = under = None
                for v in values:
                    val = v.get("value", "")
                    odd = v.get("odd")
                    if val in ["Home", "1"]:
                        home = APIConfig._safe_float(odd)
                    elif val in ["Draw", "X"]:
                        draw = APIConfig._safe_float(odd)
                    elif val in ["Away", "2"]:
                        away = APIConfig._safe_float(odd)
                    elif "Over" in str(val):
                        over = APIConfig._safe_float(odd)
                    elif "Under" in str(val):
                        under = APIConfig._safe_float(odd)
                if home and away:
                    snapshots.append(OddsSnapshot(
                        match_id=match_id,
                        bookmaker=bookmaker,
                        market=market,
                        home_odds=home,
                        draw_odds=draw,
                        away_odds=away,
                        over_odds=over,
                        under_odds=under,
                        timestamp=datetime.now()
                    ))
        return snapshots

    def _parse_predictions(self, data: Dict, match_id: str) -> Optional[Match]:
        response = data.get("response", [])
        if not response:
            return None
        pred = response[0]
        predictions = pred.get("predictions", {})
        return Match(
            match_id=match_id,
            provider="API-SPORTS",
            league=pred.get("league", {}).get("name", ""),
            league_id=str(pred.get("league", {}).get("id", "")),
            home_team=pred.get("teams", {}).get("home", {}).get("name", ""),
            away_team=pred.get("teams", {}).get("away", {}).get("name", ""),
            home_team_id=str(pred.get("teams", {}).get("home", {}).get("id", "")),
            away_team_id=str(pred.get("teams", {}).get("away", {}).get("id", "")),
            home_win_prob=predictions.get("percent", {}).get("home"),
            draw_prob=predictions.get("percent", {}).get("draw"),
            away_win_prob=predictions.get("percent", {}).get("away"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER (Keep your existing router - truncated for brevity)
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    def __init__(self):
        self.providers: List[DataProvider] = [
            APISportsProvider(),
            # Add other providers here as you have them
        ]
        self.providers.sort(key=lambda p: p.priority)
        self.active_provider: Optional[DataProvider] = None
        self.connection_log: List[Dict] = []
        self._health_check()

    def _log_connection(self, provider_name: str, status: str, detail: str, **kwargs):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "provider": provider_name,
            "status": status,
            "detail": detail,
            **kwargs
        }
        self.connection_log.append(entry)
        if len(self.connection_log) > 100:
            self.connection_log = self.connection_log[-100:]

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        df = pd.DataFrame(self.connection_log)
        df = df.rename(columns={"timestamp": "TIME", "provider": "PROVIDER", "status": "STATUS"})
        return df[["TIME", "PROVIDER", "STATUS", "detail"]]

    def get_provider_status(self) -> List[Dict]:
        statuses = []
        for provider in self.providers:
            statuses.append({
                "name": provider.name,
                "status": "ONLINE — Connected" if provider.name == "API-SPORTS" and APIConfig.API_SPORTS_KEY else "EMPTY — key valid but no matches today",
                "priority": provider.priority
            })
        return statuses

    def get_all_leagues(self, sport: str = "football") -> List[Dict]:
        for provider in self.providers:
            if provider.name == "API-SPORTS":
                leagues = provider.get_all_leagues(sport)
                if leagues:
                    return [{"id": l.league_id, "name": l.name, "country": l.country or ""} for l in leagues]
        return []

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> pd.DataFrame:
        all_matches = []
        for provider in self.providers:
            try:
                matches = provider.get_live_matches(sport, league_id)
                if matches:
                    all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"{provider.name} live fetch failed: {e}")
        if not all_matches:
            return pd.DataFrame()
        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def _find_match_by_id(self, match_id: str) -> Optional[Match]:
        for provider in self.providers:
            try:
                matches = provider.get_live_matches() or []
                for m in matches:
                    if m.match_id == match_id:
                        return m
            except Exception:
                continue
        return None

    def get_match_details(self, match_id: str) -> Dict:
        match = self._find_match_by_id(match_id)
        if match:
            return {"found": True, "match": match.to_dict()}
        return {"found": False}

    def get_match_prediction(self, match_id: str):
        return None

    def _health_check(self):
        logger.info("EMPIRE DATA ROUTER initialized")


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT INTEGRATION HELPERS
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()
        self.last_refresh = datetime.now()
        self.refresh_interval = 30

    @property
    def is_live(self) -> bool:
        return self.router.active_provider is not None

    @property
    def missing_keys(self) -> List[str]:
        return APIConfig.get_missing_keys()

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport: Dict) -> List[Dict]:
        sport_type = sport.get("sport_type", "Soccer") if sport else "Soccer"
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport: Dict = None, league_id: str = None) -> pd.DataFrame:
        sport_type = sport.get("sport_type", "Soccer") if sport else "Soccer"
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport: Dict = None) -> pd.DataFrame:
        sport_type = sport.get("sport_type", "Soccer") if sport else "Soccer"
        all_matches = []
        for provider in self.router.providers:
            try:
                matches = provider.get_upcoming_matches(sport=sport_type, days=7)
                if matches:
                    all_matches.extend(matches)
            except Exception:
                pass
        if not all_matches:
            return pd.DataFrame()
        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def get_match_prediction(self, match_id: str):
        return self.router.get_match_prediction(match_id)

    def get_match_details(self, match_id: str) -> Dict:
        return self.router.get_match_details(match_id)

    def get_team_form(self, team_name: str, match_id: str) -> Optional[Dict]:
        match = self.router._find_match_by_id(match_id)
        if match and match.home_team_id and team_name == match.home_team:
            team_id = match.home_team_id
        elif match and match.away_team_id and team_name == match.away_team:
            team_id = match.away_team_id
        else:
            return None
        
        for provider in self.router.providers:
            if provider.name == "API-SPORTS":
                try:
                    form = provider.get_team_form(team_id)
                    if form:
                        return {
                            "form": form.last_5_results,
                            "stats": {
                                "record": f"{form.last_5_results.count('W')}W-{form.last_5_results.count('D')}D-{form.last_5_results.count('L')}L",
                                "goals_scored": form.goals_scored,
                                "goals_conceded": form.goals_conceded,
                                "clean_sheets": form.clean_sheets
                            }
                        }
                except Exception:
                    continue
        return None

    def get_head_to_head(self, home: str, away: str, match_id: str) -> List[Dict]:
        match = self.router._find_match_by_id(match_id)
        if not match or not match.home_team_id or not match.away_team_id:
            return []
        
        for provider in self.router.providers:
            if provider.name == "API-SPORTS":
                try:
                    h2h_data = provider.get_h2h(match.home_team_id, match.away_team_id)
                    if h2h_data:
                        fixtures = h2h_data.get("response", [])
                        results = []
                        for f in fixtures[:5]:
                            fixture = f.get("fixture", {})
                            goals = f.get("goals", {})
                            league = f.get("league", {})
                            results.append({
                                "date": fixture.get("date", "")[:10] if fixture.get("date") else "N/A",
                                "score": f"{goals.get('home', 0)} - {goals.get('away', 0)}",
                                "competition": league.get("name", "Unknown")
                            })
                        return results
                except Exception:
                    continue
        return []

    def get_key_players(self, match_id: str) -> List[Dict]:
        return []

    def get_match_odds(self, match_id: str) -> Dict:
        return {}

    def get_ai_reasoning(self, match_id: str) -> List[str]:
        pred = self.get_match_prediction(match_id)
        if pred and hasattr(pred, 'reasoning'):
            return pred.reasoning
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ════════════════════════════════════════════════════════════════════════════════

__all__ = [
    "APIConfig",
    "EmpireDashboardData",
    "EmpireDataRouter",
    "DataProvider",
    "APISportsProvider",
    "Match",
    "OddsSnapshot",
    "League",
    "TeamForm",
    "PredictionResult",
    "MatchStatus",
]
