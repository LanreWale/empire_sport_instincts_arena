"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
═══════════════════════════════════════════════════════════════════════════════
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

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION & API KEYS
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

    @staticmethod
    def _safe_int(value, default=0):
        """Safely convert any value to int, handling strings, floats, None."""
        if value is None or value == "" or value == "-":
            return default
        try:
            # Handle float strings like "2.0"
            return int(float(str(value)))
        except (ValueError, TypeError):
            return default

    API_SPORTS_KEY = _clean_key(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL = "https://v3.football.api-sports.io"
    API_SPORTS_PRIORITY = 1

    ODDS_API_KEY = _clean_key(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL = "https://api.the-odds-api.com/v4"
    ODDS_API_PRIORITY = 1

    SPORTMONKS_KEY = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL = "https://api.sportmonks.com/v3/football"
    SPORTMONKS_PRIORITY = 2

    MYSPORTSFEEDS_KEY = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL = "https://api.mysportsfeeds.com/v2.1/pull"
    MYSPORTSFEEDS_PRIORITY = 2

    FOOTBALL_DATA_KEY = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    FOOTBALL_DATA_PRIORITY = 3

    THESPORTSDB_KEY = _clean_key(os.getenv("TheSportDB_API_key", ""))
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
            "TheSportDB_API_key": cls.THESPORTSDB_KEY,
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
    # NEW: Form data for predictions
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
    """Team form data for prediction engine."""
    team_id: str
    team_name: str
    last_5_results: List[str]  # W, D, L
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
    """Structured prediction output for display."""
    match_id: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    over_25_prob: float
    btts_prob: float
    confidence: str  # HIGH, MEDIUM, LOW
    signal: str  # BUY, HOLD, AVOID
    reasoning: List[str]  # Human-readable analysis points
    home_form_rating: Optional[float] = None
    away_form_rating: Optional[float] = None
    h2h_advantage: Optional[str] = None  # home, away, none
    value_bet: Optional[str] = None  # home, draw, away, none
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

    def get_upcoming_matches(self, sport: str = "football", days: int = 1) -> List[Match]:
        raise NotImplementedError

    def get_team_form(self, team_id: str, league_id: str = None) -> Optional[TeamForm]:
        """Fetch team form data for predictions."""
        raise NotImplementedError

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        raise NotImplementedError

    def get_predictions(self, match_id: str) -> Optional[Match]:
        raise NotImplementedError

    def get_h2h(self, team1_id: str, team2_id: str) -> Optional[Dict]:
        """Fetch head-to-head history."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS (API-FOOTBALL) PROVIDER
# Primary football data: live scores, fixtures, statistics, form, predictions
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

    def get_upcoming_matches(self, sport: str = "football", days: int = 1) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("fixtures", {"from": today, "to": future})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_fixtures(cached)
        params = {"date": today, "season": datetime.now().year, "timezone": "UTC"}
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_team_form(self, team_id: str, league_id: str = None) -> Optional[TeamForm]:
        """Fetch last 5 fixtures for team to calculate form."""
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = self._get_cache_key("team_form", {"team": team_id, "league": league_id})
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
            
            # ─── FIXED: Use _safe_int to prevent string concatenation ─────────
            home_goals = APIConfig._safe_int(goals.get("home"), 0)
            away_goals = APIConfig._safe_int(goals.get("away"), 0)
            
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
        """Fetch head-to-head history between two teams."""
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
                home = draw = away = None
                for v in values:
                    if v.get("value") in ["Home", "1"]:
                        home = APIConfig._safe_float(v.get("odd"), 0)
                    elif v.get("value") in ["Draw", "X"]:
                        draw = APIConfig._safe_float(v.get("odd"), 0)
                    elif v.get("value") in ["Away", "2"]:
                        away = APIConfig._safe_float(v.get("odd"), 0)
                if home and away:
                    snapshots.append(OddsSnapshot(
                        match_id=match_id,
                        bookmaker=bookmaker,
                        market=market,
                        home_odds=home,
                        draw_odds=draw,
                        away_odds=away,
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
            home_win_prob=predictions.get("percent", {}).get("home"),
            draw_prob=predictions.get("percent", {}).get("draw"),
            away_win_prob=predictions.get("percent", {}).get("away"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# THE ODDS API PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class TheOddsAPIProvider(DataProvider):
    def __init__(self):
        super().__init__("TheOddsAPI", APIConfig.ODDS_API_PRIORITY)
        self.base_url = APIConfig.ODDS_API_URL
        self.rate_limit_delay = 1.0

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        return []

    def get_live_matches(self, sport: str = "soccer", league_id: str = None) -> List[Match]:
        if not APIConfig.ODDS_API_KEY:
            return []
        cache_key = self._get_cache_key("sports/events/inplay", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_events(cached, sport)
        data = self._make_request(f"{self.base_url}/sports/{sport}/events", params={"apiKey": APIConfig.ODDS_API_KEY, "regions": "eu", "oddsFormat": "decimal"})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_events(data, sport)

    def get_upcoming_matches(self, sport: str = "soccer", days: int = 1) -> List[Match]:
        if not APIConfig.ODDS_API_KEY:
            return []
        cache_key = self._get_cache_key("sports/events/upcoming", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_events(cached, sport)
        data = self._make_request(f"{self.base_url}/sports/{sport}/odds", params={"apiKey": APIConfig.ODDS_API_KEY, "regions": "eu", "markets": "h2h,totals", "oddsFormat": "decimal", "dateFormat": "iso"})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_events(data, sport)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        if not APIConfig.ODDS_API_KEY:
            return []
        cache_key = self._get_cache_key("event_odds", {"event": match_id})
        cached = self._get_cached(cache_key, ttl=APIConfig.ODDS_CACHE_TTL)
        if cached:
            return self._parse_event_odds(cached, match_id)
        data = self._make_request(f"{self.base_url}/sports/soccer/events/{match_id}/odds", params={"apiKey": APIConfig.ODDS_API_KEY, "regions": "eu", "markets": ",".join(markets) if markets else "h2h", "oddsFormat": "decimal"})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_event_odds(data, match_id)

    def _parse_events(self, data: List[Dict], sport: str) -> List[Match]:
        matches = []
        for event in data:
            commence = event.get("commence_time")
            start_time = datetime.fromisoformat(commence.replace("Z", "+00:00")) if commence else None
            home_odds = draw_odds = away_odds = None
            for bm in event.get("bookmakers", [])[:1]:
                for market in bm.get("markets", []):
                    if market.get("key") == "h2h":
                        for o in market.get("outcomes", []):
                            name = o.get("name", "").lower()
                            price = APIConfig._safe_float(o.get("price"), 0)
                            if "home" in name or event.get("home_team", "").lower() in name:
                                home_odds = price
                            elif "away" in name or event.get("away_team", "").lower() in name:
                                away_odds = price
                            elif "draw" in name:
                                draw_odds = price
            matches.append(Match(
                match_id=event.get("id", ""),
                provider="TheOddsAPI",
                league=event.get("sport_title", sport),
                league_id="",
                home_team=event.get("home_team", "Home"),
                away_team=event.get("away_team", "Away"),
                start_time=start_time,
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
            ))
        return matches

    def _parse_event_odds(self, data: Dict, match_id: str) -> List[OddsSnapshot]:
        snapshots = []
        for bm in data.get("bookmakers", []):
            for market in bm.get("markets", []):
                home = draw = away = over = under = None
                for o in market.get("outcomes", []):
                    name = o.get("name", "").lower()
                    price = APIConfig._safe_float(o.get("price"), 0)
                    if "home" in name:
                        home = price
                    elif "away" in name:
                        away = price
                    elif "draw" in name:
                        draw = price
                    elif market.get("key") == "totals" and "over" in name:
                        over = price
                    elif market.get("key") == "totals" and "under" in name:
                        under = price
                if home and away:
                    snapshots.append(OddsSnapshot(
                        match_id=match_id,
                        bookmaker=bm.get("title", "Unknown"),
                        market=market.get("key", "Unknown"),
                        home_odds=home,
                        draw_odds=draw,
                        away_odds=away,
                        over_odds=over,
                        under_odds=under,
                        timestamp=datetime.now()
                    ))
        return snapshots


# ═══════════════════════════════════════════════════════════════════════════════
# SPORTMONKS PROVIDER
# Advanced football analytics: xG, predictions, deep stats
# ════════════════════════════════════════════════════════════════════════════════

class SportmonksProvider(DataProvider):
    def __init__(self):
        super().__init__("Sportmonks", APIConfig.SPORTMONKS_PRIORITY)
        self.base_url = APIConfig.SPORTMONKS_URL
        self.rate_limit_delay = 1.5

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        return []

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        if not APIConfig.SPORTMONKS_KEY:
            return []
        cache_key = self._get_cache_key("livescores/inplay", {})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_livescores(cached)
        data = self._make_request(f"{self.base_url}/livescores/inplay", params={"api_token": APIConfig.SPORTMONKS_KEY, "include": "predictions"})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_livescores(data)

    def get_team_form(self, team_id: str, league_id: str = None) -> Optional[TeamForm]:
        """Sportmonks team form via fixtures endpoint."""
        if not APIConfig.SPORTMONKS_KEY:
            return None
        cache_key = self._get_cache_key("team_form_sportmonks", {"team": team_id})
        cached = self._get_cached(cache_key, ttl=1800)
        if cached:
            return self._parse_team_form(cached, team_id)
        data = self._make_request(f"{self.base_url}/fixtures", params={"api_token": APIConfig.SPORTMONKS_KEY, "team_id": team_id, "per_page": 5})
        if not data:
            return None
        self._set_cached(cache_key, data)
        return self._parse_team_form(data, team_id)

    def _parse_team_form(self, data: Dict, team_id: str) -> Optional[TeamForm]:
        fixtures = data.get("data", [])
        if not fixtures:
            return None
        results = []
        goals_scored = 0
        goals_conceded = 0
        team_name = ""
        for fixture in fixtures:
            participants = fixture.get("participants", [{}, {}])
            scores = fixture.get("scores", {})
            is_home = str(participants[0].get("id")) == str(team_id) if len(participants) > 0 else False
            if not team_name:
                team_name = participants[0].get("name", "") if is_home else participants[1].get("name", "")
            
            # ─── FIXED: Use _safe_int for type safety ─────────────────────────
            home_goals = APIConfig._safe_int(scores.get("home"), 0)
            away_goals = APIConfig._safe_int(scores.get("away"), 0)
            
            if is_home:
                team_goals = home_goals
                opp_goals = away_goals
            else:
                team_goals = away_goals
                opp_goals = home_goals
            
            goals_scored += team_goals
            goals_conceded += opp_goals
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
            clean_sheets=sum(1 for g in [goals_conceded] if g == 0),
        )

    def get_predictions(self, match_id: str) -> Optional[Match]:
        if not APIConfig.SPORTMONKS_KEY:
            return None
        cache_key = self._get_cache_key("predictions/probabilities", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=600)
        if cached:
            return self._parse_predictions(cached, match_id)
        data = self._make_request(f"{self.base_url}/predictions/probabilities/fixture/{match_id}", params={"api_token": APIConfig.SPORTMONKS_KEY})
        if not data:
            return None
        self._set_cached(cache_key, data)
        return self._parse_predictions(data, match_id)

    def _parse_livescores(self, data: Dict) -> List[Match]:
        matches = []
        for item in data.get("data", []):
            participants = item.get("participants", [{}, {}])
            home_team = participants[0].get("name", "Home") if len(participants) > 0 else "Home"
            away_team = participants[1].get("name", "Away") if len(participants) > 1 else "Away"
            matches.append(Match(
                match_id=str(item.get("id", "")),
                provider="Sportmonks",
                league=item.get("league", {}).get("name", "Unknown"),
                league_id=str(item.get("league_id", "")),
                home_team=home_team,
                away_team=away_team,
                home_score=item.get("scores", {}).get("home"),
                away_score=item.get("scores", {}).get("away"),
                status=item.get("state", {}).get("state", "SCH"),
                minute=item.get("minute"),
            ))
        return matches

    def _parse_predictions(self, data: Dict, match_id: str) -> Optional[Match]:
        pred = data.get("data", {})
        return Match(
            match_id=match_id,
            provider="Sportmonks",
            league="",
            league_id="",
            home_team="",
            away_team="",
            home_win_prob=pred.get("home_win_probability"),
            draw_prob=pred.get("draw_probability"),
            away_win_prob=pred.get("away_win_probability"),
            over_25_prob=pred.get("over_2_5_probability"),
            btts_prob=pred.get("both_teams_to_score_probability"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    def __init__(self):
        super().__init__("TheSportsDB", APIConfig.THESPORTSDB_PRIORITY)
        self.base_url_v1 = APIConfig.THESPORTSDB_URL_V1
        self.base_url_v2 = APIConfig.THESPORTSDB_URL
        self.headers_v2 = {"X-API-KEY": APIConfig.THESPORTSDB_KEY} if APIConfig.THESPORTSDB_KEY else {}
        self.rate_limit_delay = 2.0

    def _make_request_v1(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        key = APIConfig.THESPORTSDB_KEY or "123"
        url = f"{self.base_url_v1}/{key}/{endpoint}"
        return self._make_request(url, params=params)

    def _make_request_v2(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not APIConfig.THESPORTSDB_KEY:
            return None
        url = f"{self.base_url_v2}/{endpoint}"
        return self._make_request(url, headers=self.headers_v2, params=params)

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        """Fetch all leagues from TheSportsDB v2 with timeout fallback."""
        if not APIConfig.THESPORTSDB_KEY:
            return []
        cache_key = self._get_cache_key("all_leagues", {"sport": sport})
        cached = self._get_cached(cache_key, ttl=3600)
        if cached:
            return self._parse_leagues(cached)
        try:
            data = self._make_request_v2("all/leagues")
            if not data:
                return []
            self._set_cached(cache_key, data)
            return self._parse_leagues(data)
        except Exception as e:
            logger.warning(f"TheSportsDB /all/leagues failed: {e}")
            return []

    def _parse_leagues(self, data: Dict) -> List[League]:
        leagues = []
        raw_leagues = data.get("leagues", [])
        for item in raw_leagues:
            league_id = str(item.get("idLeague", item.get("id", "")))
            name = item.get("strLeague", item.get("strLeagueAlternate", "Unknown"))
            sport_name = item.get("strSport", "football")
            country = item.get("strCountry", item.get("strLeagueAlternate", ""))
            if league_id and name:
                leagues.append(League(league_id=league_id, name=name, sport=sport_name, country=country))
        return leagues

    def get_live_matches_by_league(self, league_id: str, sport: str = "Soccer") -> List[Match]:
        if not APIConfig.THESPORTSDB_KEY:
            return []
        if not league_id or league_id == "ALL":
            return self.get_live_matches(sport)
        cache_key = self._get_cache_key("livescore_by_league", {"league_id": league_id})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_livescores(cached)
        try:
            data = self._make_request_v2(f"livescore/{league_id}")
            if not data:
                return []
            self._set_cached(cache_key, data)
            return self._parse_livescores(data)
        except Exception as e:
            logger.warning(f"TheSportsDB livescore/{league_id} failed: {e}")
            return []

    def get_live_matches(self, sport: str = "Soccer", league_id: str = None) -> List[Match]:
        if league_id and league_id != "ALL":
            return self.get_live_matches_by_league(league_id, sport)
        if not APIConfig.THESPORTSDB_KEY:
            return []
        cache_key = self._get_cache_key("livescore", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_livescores(cached)
        data = self._make_request_v2(f"livescore/{sport}")
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_livescores(data)

    def get_upcoming_matches(self, sport: str = "Soccer", days: int = 1) -> List[Match]:
        cache_key = self._get_cache_key("eventsnextleague", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_events(cached)
        if APIConfig.THESPORTSDB_KEY:
            data = self._make_request_v2(f"schedule/{sport}")
        else:
            return []
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_events(data)

    def get_h2h(self, team1_id: str, team2_id: str) -> Optional[Dict]:
        """Fetch H2H via TheSportsDB V1 eventslast endpoint."""
        try:
            data = self._make_request_v1(f"eventslast.php?id={team1_id}")
            if data:
                return data
        except Exception:
            pass
        return None

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        return None

    def _parse_livescores(self, data: Dict) -> List[Match]:
        matches = []
        events = data.get("events", []) or data.get("livescore", [])
        for event in events:
            status = event.get("strStatus", "NS")
            is_live = status in ["1H", "2H", "HT", "Q1", "Q2", "Q3", "Q4", "OT", "P1", "P2", "P3", "IN1", "IN2", "IN3", "IN4", "IN5", "S1", "S2", "S3", "S4", "S5"]
            
            # ─── FIXED:
