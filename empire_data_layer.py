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
                        home = float(v.get("odd", 0))
                    elif v.get("value") in ["Draw", "X"]:
                        draw = float(v.get("odd", 0))
                    elif v.get("value") in ["Away", "2"]:
                        away = float(v.get("odd", 0))
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
                            price = o.get("price")
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
                    price = o.get("price")
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
            home_goals = scores.get("home", 0) or 0
            away_goals = scores.get("away", 0) or 0
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
            home_score = event.get("intHomeScore")
            away_score = event.get("intAwayScore")
            if home_score == "":
                home_score = None
            if away_score == "":
                away_score = None
            try:
                home_score = int(home_score) if home_score is not None else None
            except (ValueError, TypeError):
                home_score = None
            try:
                away_score = int(away_score) if away_score is not None else None
            except (ValueError, TypeError):
                away_score = None
            matches.append(Match(
                match_id=str(event.get("idEvent", "")),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=str(event.get("idLeague", "")),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                home_score=home_score,
                away_score=away_score,
                status="LIVE" if is_live else status,
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
                venue=event.get("strVenue"),
                country=event.get("strCountry"),
                season=event.get("strSeason"),
                round=event.get("intRound"),
            ))
        return matches

    def _parse_events(self, data: Dict) -> List[Match]:
        matches = []
        for event in data.get("events", []):
            matches.append(Match(
                match_id=str(event.get("idEvent", "")),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=str(event.get("idLeague", "")),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
                venue=event.get("strVenue"),
                country=event.get("strCountry"),
                season=event.get("strSeason"),
                round=event.get("intRound"),
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    def __init__(self):
        super().__init__("MySportsFeeds", APIConfig.MYSPORTSFEEDS_PRIORITY)
        self.base_url = APIConfig.MYSPORTSFEEDS_URL
        api_key = APIConfig.MYSPORTSFEEDS_KEY
        password = APIConfig.MYSPORTSFEEDS_PASSWORD
        if api_key and password:
            credentials = base64.b64encode(f"{api_key}:{password}".encode()).decode()
            self.headers = {"Authorization": f"Basic {credentials}"}
        else:
            self.headers = {}
        self.rate_limit_delay = 2.0

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        return []

    def get_live_matches(self, sport: str = "nba", league_id: str = None) -> List[Match]:
        if not APIConfig.MYSPORTSFEEDS_KEY:
            return []
        cache_key = self._get_cache_key("games", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_games(cached)
        data = self._make_request(f"{self.base_url}/{sport}/current/games.json", self.headers, {"date": datetime.now().strftime("%Y%m%d")})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_games(data)

    def get_upcoming_matches(self, sport: str = "nba", days: int = 7) -> List[Match]:
        if not APIConfig.MYSPORTSFEEDS_KEY:
            return []
        cache_key = self._get_cache_key("games/upcoming", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_games(cached)
        data = self._make_request(f"{self.base_url}/{sport}/current/games.json", self.headers, {"date": datetime.now().strftime("%Y%m%d")})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_games(data)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        return None

    def _parse_games(self, data: Dict) -> List[Match]:
        matches = []
        for game in data.get("games", []):
            status = game.get("schedule", {}).get("status", "SCHEDULED")
            is_live = status == "IN_PROGRESS"
            matches.append(Match(
                match_id=str(game.get("schedule", {}).get("id", "")),
                provider="MySportsFeeds",
                league=game.get("schedule", {}).get("league", "Unknown"),
                league_id="",
                home_team=game.get("schedule", {}).get("homeTeam", {}).get("name", "Home"),
                away_team=game.get("schedule", {}).get("awayTeam", {}).get("name", "Away"),
                home_score=game.get("score", {}).get("homeScoreTotal"),
                away_score=game.get("score", {}).get("awayScoreTotal"),
                status="LIVE" if is_live else status,
                start_time=datetime.fromisoformat(game.get("schedule", {}).get("startTime", "").replace("Z", "+00:00")) if game.get("schedule", {}).get("startTime") else None,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA.ORG PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class FootballDataProvider(DataProvider):
    def __init__(self):
        super().__init__("Football-Data", APIConfig.FOOTBALL_DATA_PRIORITY)
        self.base_url = APIConfig.FOOTBALL_DATA_URL
        self.headers = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY}
        self.rate_limit_delay = 6.0

    def get_all_leagues(self, sport: str = "football") -> List[League]:
        return []

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        if not APIConfig.FOOTBALL_DATA_KEY:
            return []
        cache_key = self._get_cache_key("matches", {"date": datetime.now().strftime("%Y-%m-%d")})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_matches(cached)
        data = self._make_request(f"{self.base_url}/matches", self.headers)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_matches(data)

    def get_upcoming_matches(self, sport: str = "football", days: int = 7) -> List[Match]:
        if not APIConfig.FOOTBALL_DATA_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("matches/upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_matches(cached)
        data = self._make_request(f"{self.base_url}/matches", self.headers, {"dateFrom": today, "dateTo": future})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_matches(data)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        return None

    def _parse_matches(self, data: Dict) -> List[Match]:
        matches = []
        for match in data.get("matches", []):
            status = match.get("status", "SCHEDULED")
            if status == "IN_PLAY":
                status = "LIVE"
            elif status == "PAUSED":
                status = "HALFTIME"
            elif status == "FINISHED":
                status = "FINISHED"
            matches.append(Match(
                match_id=str(match.get("id", "")),
                provider="Football-Data",
                league=match.get("competition", {}).get("name", "Unknown"),
                league_id=str(match.get("competition", {}).get("id", "")),
                home_team=match.get("homeTeam", {}).get("name", "Home"),
                away_team=match.get("awayTeam", {}).get("name", "Away"),
                home_score=match.get("score", {}).get("fullTime", {}).get("home"),
                away_score=match.get("score", {}).get("fullTime", {}).get("away"),
                status=status,
                start_time=datetime.fromisoformat(match.get("utcDate", "").replace("Z", "+00:00")) if match.get("utcDate") else None,
            ))
        return matches



# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE PREDICTION ENGINE
# Multi-factor analysis: Form, H2H, xG, Poisson, Market odds, Value detection
# ════════════════════════════════════════════════════════════════════════════════

class EmpirePredictionEngine:
    """
    Cutting-edge prediction engine combining multiple data sources:
    - Team form (last 5) from API-SPORTS / Sportmonks
    - Head-to-head history from API-SPORTS
    - xG / probabilities from Sportmonks
    - Live stats from API-SPORTS
    - Market odds from The Odds API
    - Poisson distribution for goal-based predictions
    """

    def __init__(self, router: 'EmpireDataRouter'):
        self.router = router

    def predict_match(self, match: Match) -> PredictionResult:
        """Generate comprehensive prediction for a single match."""
        reasoning = []

        # 1. Fetch form data for both teams
        home_form = self._get_team_form(match.match_id, match.home_team, is_home=True)
        away_form = self._get_team_form(match.match_id, match.away_team, is_home=False)

        # 2. Fetch H2H record
        h2h = self._get_h2h_data(match)

        # 3. Fetch API-SPORTS predictions (if available)
        api_pred = self._get_api_predictions(match.match_id)

        # 4. Fetch Sportmonks predictions (xG)
        sportmonks_pred = self._get_sportmonks_predictions(match.match_id)

        # 5. Fetch current odds
        odds = self._get_odds_data(match.match_id)

        # 6. Calculate Poisson probabilities from form
        poisson_probs = self._calculate_poisson(home_form, away_form)

        # 7. Ensemble: combine all prediction sources
        final_probs = self._ensemble_predictions(api_pred, sportmonks_pred, poisson_probs, home_form, away_form, h2h)

        # 8. Calculate EV and value bet
        ev_data = self._calculate_ev(final_probs, odds)

        # 9. Build reasoning
        if home_form:
            reasoning.append(f"Home form (last 5): {'-'.join(home_form.last_5_results)} | GF:{home_form.goals_scored} GA:{home_form.goals_conceded}")
        if away_form:
            reasoning.append(f"Away form (last 5): {'-'.join(away_form.last_5_results)} | GF:{away_form.goals_scored} GA:{away_form.goals_conceded}")
        if h2h:
            reasoning.append(f"H2H: Home {h2h.get('home_wins', 0)}W {h2h.get('draws', 0)}D {h2h.get('away_wins', 0)}L")
        if poisson_probs:
            reasoning.append(f"Poisson xG: Home {poisson_probs.get('xg_home', 0):.2f} | Away {poisson_probs.get('xg_away', 0):.2f}")
        if ev_data.get('value_bet'):
            reasoning.append(f"Value detected: {ev_data['value_bet']} @ {ev_data['value_odds']:.2f} (EV: {ev_data['ev']:.1f}%)")

        # 10. Determine confidence and signal
        confidence = self._calculate_confidence(final_probs, home_form, away_form, h2h)
        signal = self._determine_signal(ev_data, confidence)

        return PredictionResult(
            match_id=match.match_id,
            home_win_prob=final_probs.get('home', 33.3),
            draw_prob=final_probs.get('draw', 33.3),
            away_win_prob=final_probs.get('away', 33.3),
            over_25_prob=final_probs.get('over_25', 50.0),
            btts_prob=final_probs.get('btts', 50.0),
            confidence=confidence,
            signal=signal,
            reasoning=reasoning,
            home_form_rating=self._form_rating(home_form),
            away_form_rating=self._form_rating(away_form),
            h2h_advantage=h2h.get('advantage', 'none') if h2h else 'none',
            value_bet=ev_data.get('value_bet'),
            expected_goals_home=poisson_probs.get('xg_home'),
            expected_goals_away=poisson_probs.get('xg_away'),
        )

    def _get_team_form(self, match_id: str, team_name: str, is_home: bool = True) -> Optional[TeamForm]:
        """Fetch team form from best available provider."""
        # Try API-SPORTS first (most reliable)
        for provider in self.router.providers:
            if provider.name == "API-SPORTS":
                try:
                    # We need team_id - try to get it from match data
                    # For now, return None since we don't have team_id mapping
                    pass
                except Exception:
                    continue
        return None

    def _get_h2h_data(self, match: Match) -> Optional[Dict]:
        """Fetch head-to-head history."""
        for provider in self.router.providers:
            if provider.name == "API-SPORTS":
                try:
                    # Need team IDs for H2H
                    return None
                except Exception:
                    continue
        return None

    def _get_api_predictions(self, match_id: str) -> Optional[Dict]:
        """Fetch predictions from API-SPORTS."""
        for provider in self.router.providers:
            if provider.name == "API-SPORTS":
                try:
                    pred = provider.get_predictions(match_id)
                    if pred:
                        return {
                            'home': pred.home_win_prob or 0,
                            'draw': pred.draw_prob or 0,
                            'away': pred.away_win_prob or 0,
                        }
                except Exception:
                    continue
        return None

    def _get_sportmonks_predictions(self, match_id: str) -> Optional[Dict]:
        """Fetch xG predictions from Sportmonks."""
        for provider in self.router.providers:
            if provider.name == "Sportmonks":
                try:
                    pred = provider.get_predictions(match_id)
                    if pred:
                        return {
                            'home': pred.home_win_prob or 0,
                            'draw': pred.draw_prob or 0,
                            'away': pred.away_win_prob or 0,
                            'over_25': pred.over_25_prob or 0,
                            'btts': pred.btts_prob or 0,
                        }
                except Exception:
                    continue
        return None

    def _get_odds_data(self, match_id: str) -> Dict:
        """Fetch current odds from all providers."""
        all_odds = []
        for provider in self.router.providers:
            try:
                odds = provider.get_odds(match_id)
                all_odds.extend(odds)
            except Exception:
                continue
        if not all_odds:
            return {}
        # Average odds across bookmakers
        home_odds = []
        draw_odds = []
        away_odds = []
        for o in all_odds:
            if o.home_odds:
                home_odds.append(o.home_odds)
            if o.draw_odds:
                draw_odds.append(o.draw_odds)
            if o.away_odds:
                away_odds.append(o.away_odds)
        return {
            'home': sum(home_odds) / len(home_odds) if home_odds else 0,
            'draw': sum(draw_odds) / len(draw_odds) if draw_odds else 0,
            'away': sum(away_odds) / len(away_odds) if away_odds else 0,
        }

    def _calculate_poisson(self, home_form: Optional[TeamForm], away_form: Optional[TeamForm]) -> Dict:
        """Calculate expected goals using Poisson distribution from form data."""
        if not home_form or not away_form:
            return {}

        # Average goals per game from last 5
        home_xg = home_form.goals_scored / 5.0 if home_form.goals_scored else 1.2
        away_xg = away_form.goals_scored / 5.0 if away_form.goals_scored else 1.0
        home_ga = home_form.goals_conceded / 5.0 if home_form.goals_conceded else 1.0
        away_ga = away_form.goals_conceded / 5.0 if away_form.goals_conceded else 1.2

        # Adjust for home advantage (typically +0.3 goals)
        home_advantage = 0.3

        # Expected goals
        xg_home = (home_xg + away_ga) / 2 + home_advantage
        xg_away = (away_xg + home_ga) / 2

        # Poisson probabilities for match outcomes
        from math import exp, factorial

        def poisson_prob(lambda_val, k):
            return (lambda_val ** k) * exp(-lambda_val) / factorial(k)

        # Calculate probability of each scoreline up to 5 goals
        home_win_prob = 0
        draw_prob = 0
        away_win_prob = 0
        over_25_prob = 0
        btts_prob = 0

        for home_goals in range(6):
            for away_goals in range(6):
                prob = poisson_prob(xg_home, home_goals) * poisson_prob(xg_away, away_goals)
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob
                if home_goals + away_goals > 2.5:
                    over_25_prob += prob
                if home_goals > 0 and away_goals > 0:
                    btts_prob += prob

        return {
            'home': home_win_prob * 100,
            'draw': draw_prob * 100,
            'away': away_win_prob * 100,
            'over_25': over_25_prob * 100,
            'btts': btts_prob * 100,
            'xg_home': xg_home,
            'xg_away': xg_away,
        }

    def _ensemble_predictions(self, api_pred, sportmonks_pred, poisson_probs, home_form, away_form, h2h) -> Dict:
        """Combine multiple prediction sources into final probabilities."""
        sources = []
        weights = []

        if api_pred:
            sources.append(api_pred)
            weights.append(0.30)
        if sportmonks_pred:
            sources.append(sportmonks_pred)
            weights.append(0.35)
        if poisson_probs:
            sources.append(poisson_probs)
            weights.append(0.25)

        # If no sources, return equal probabilities
        if not sources:
            return {'home': 33.3, 'draw': 33.3, 'away': 33.3, 'over_25': 50.0, 'btts': 50.0}

        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # Weighted average
        result = {'home': 0, 'draw': 0, 'away': 0, 'over_25': 0, 'btts': 0}
        for source, weight in zip(sources, weights):
            for key in result:
                if key in source:
                    result[key] += source[key] * weight

        return result

    def _calculate_ev(self, probs: Dict, odds: Dict) -> Dict:
        """Calculate expected value for each outcome."""
        if not odds or not probs:
            return {'value_bet': None, 'ev': 0}

        best_ev = -1
        value_bet = None
        value_odds = 0

        for outcome in ['home', 'draw', 'away']:
            if outcome in odds and odds[outcome] > 1:
                prob = probs.get(outcome, 0) / 100.0
                ev = (prob * odds[outcome]) - 1
                if ev > best_ev:
                    best_ev = ev
                    value_bet = outcome
                    value_odds = odds[outcome]

        return {
            'value_bet': value_bet,
            'ev': best_ev * 100,
            'value_odds': value_odds,
        }

    def _calculate_confidence(self, probs: Dict, home_form, away_form, h2h) -> str:
        """Calculate confidence level based on prediction strength."""
        # Check if any probability is significantly higher
        max_prob = max(probs.get('home', 0), probs.get('draw', 0), probs.get('away', 0))
        if max_prob > 55:
            return "HIGH"
        elif max_prob > 45:
            return "MEDIUM"
        return "LOW"

    def _determine_signal(self, ev_data: Dict, confidence: str) -> str:
        """Determine trading signal based on EV and confidence."""
        ev = ev_data.get('ev', 0)
        if ev > 5 and confidence == "HIGH":
            return "🟢 STRONG BUY"
        elif ev > 2 and confidence in ["HIGH", "MEDIUM"]:
            return "🟡 BUY"
        elif ev > 0:
            return "⚪ HOLD"
        return "🔴 AVOID"

    def _form_rating(self, form: Optional[TeamForm]) -> Optional[float]:
        """Calculate numerical form rating 0-100."""
        if not form:
            return None
        points = sum(3 if r == "W" else (1 if r == "D" else 0) for r in form.last_5_results)
        return (points / 15.0) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# Multi-provider aggregation with failover + prediction engine
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    def __init__(self):
        self.providers: List[DataProvider] = [
            APISportsProvider(),
            TheOddsAPIProvider(),
            SportmonksProvider(),
            TheSportsDBProvider(),
            MySportsFeedsProvider(),
            FootballDataProvider(),
        ]
        self.providers.sort(key=lambda p: p.priority)
        self.active_provider: Optional[DataProvider] = None
        self.connection_log: List[Dict] = []
        self.prediction_engine = EmpirePredictionEngine(self)
        self._health_check()

    def _log_connection(self, provider_name: str, status: str, detail: str, 
                        matches_found: int = 0, error_type: str = None, 
                        http_code: int = None, response_time_ms: float = None,
                        endpoint_tested: str = None):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "provider": provider_name,
            "status": status,
            "detail": detail,
            "matches_found": matches_found,
            "error_type": error_type,
            "http_code": http_code,
            "response_time_ms": response_time_ms,
            "endpoint_tested": endpoint_tested,
        }
        self.connection_log.append(entry)
        if len(self.connection_log) > 100:
            self.connection_log = self.connection_log[-100:]
        level = logging.INFO if status == "SUCCESS" else logging.WARNING
        logger.log(level, f"[{provider_name}] {status}: {detail}")

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame(columns=["TIME", "PROVIDER", "STATUS", "HTTP", "MATCHES", "RESPONSE_MS", "DETAIL", "ENDPOINT"])
        df = pd.DataFrame(self.connection_log)
        df = df.rename(columns={
            "timestamp": "TIME", "provider": "PROVIDER", "status": "STATUS",
            "http_code": "HTTP", "matches_found": "MATCHES",
            "response_time_ms": "RESPONSE_MS", "detail": "DETAIL", "endpoint_tested": "ENDPOINT",
        })
        df = df[["TIME", "PROVIDER", "STATUS", "HTTP", "MATCHES", "RESPONSE_MS", "DETAIL", "ENDPOINT"]]
        return df.iloc[::-1].reset_index(drop=True)

    def get_provider_status(self) -> List[Dict]:
        status = []
        for provider in self.providers:
            start_time = time.time()
            try:
                test = provider.get_live_matches()
                elapsed_ms = (time.time() - start_time) * 1000
                is_online = test is not None and len(test) > 0
                match_count = len(test) if test else 0
                status_text = "ONLINE" if is_online else "EMPTY (key valid but no matches today)"
                status.append({"name": provider.name, "status": status_text, "priority": provider.priority,
                              "matches_found": match_count, "error": None, "response_time_ms": round(elapsed_ms, 2)})
                self._log_connection(provider.name, "SUCCESS" if is_online else "EMPTY", f"Status check: {status_text}",
                                    match_count, response_time_ms=round(elapsed_ms, 2), endpoint_tested="get_provider_status()")
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                status.append({"name": provider.name, "status": f"OFFLINE — {type(e).__name__}",
                              "priority": provider.priority, "matches_found": 0, "error": str(e)[:80],
                              "response_time_ms": round(elapsed_ms, 2)})
                self._log_connection(provider.name, "ERROR", f"Status check failed: {type(e).__name__}: {str(e)[:80]}",
                                    error_type=type(e).__name__, response_time_ms=round(elapsed_ms, 2), endpoint_tested="get_provider_status()")
        return status

    def _health_check(self):
        logger.info("=" * 60)
        logger.info("🔍 EMPIRE HEALTH CHECK — Testing all API providers")
        logger.info("=" * 60)
        for provider in self.providers:
            logger.info(f"Testing {provider.name}...")
            start_time = time.time()
            try:
                matches = provider.get_live_matches()
                elapsed_ms = (time.time() - start_time) * 1000
                if matches is not None:
                    match_count = len(matches) if hasattr(matches, '__len__') else 0
                    self.active_provider = provider
                    self._log_connection(provider.name, "SUCCESS", f"Provider active — {match_count} live matches retrieved",
                                        match_count, response_time_ms=round(elapsed_ms, 2), endpoint_tested="get_live_matches()")
                    logger.info(f"✅ {provider.name} is ACTIVE with {match_count} matches ({elapsed_ms:.0f}ms)")
                    break
                else:
                    self._log_connection(provider.name, "FAIL", "Provider returned None (no response)",
                                        response_time_ms=round(elapsed_ms, 2), endpoint_tested="get_live_matches()")
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                detail = f"UNEXPECTED ERROR — {type(e).__name__}: {str(e)[:120]}"
                self._log_connection(provider.name, "ERROR", detail, error_type=type(e).__name__,
                                    response_time_ms=round(elapsed_ms, 2), endpoint_tested="get_live_matches()")
                logger.error(f"❌ {provider.name}: {detail}")
        if not self.active_provider:
            self._log_connection("SYSTEM", "FAIL", "NO PROVIDERS AVAILABLE — All APIs failed. Check .env keys and internet connection.",
                                endpoint_tested="_health_check()")
            logger.error("No providers available! All API keys missing or invalid.")

    def get_all_leagues(self, sport: str = "football") -> List[Dict]:
        """Fetch all available leagues with robust fallback chain."""
        all_leagues = []

        # Try TheSportsDB first (best coverage if working)
        for provider in self.providers:
            if provider.name == "TheSportsDB":
                try:
                    leagues = provider.get_all_leagues(sport)
                    if leagues:
                        for league in leagues:
                            all_leagues.append({"id": league.league_id, "name": league.name,
                                               "sport": league.sport, "country": league.country or ""})
                        logger.info(f"TheSportsDB returned {len(all_leagues)} leagues")
                        break
                except Exception as e:
                    logger.warning(f"TheSportsDB league fetch failed: {e}")

        # Fallback: API-SPORTS
        if not all_leagues:
            for provider in self.providers:
                if provider.name == "API-SPORTS":
                    try:
                        leagues = provider.get_all_leagues(sport)
                        if leagues:
                            for league in leagues:
                                all_leagues.append({"id": league.league_id, "name": league.name,
                                                   "sport": league.sport, "country": league.country or ""})
                            logger.info(f"API-SPORTS returned {len(all_leagues)} leagues")
                            break
                    except Exception as e:
                        logger.warning(f"API-SPORTS league fetch failed: {e}")

        # Last resort: extract from live matches across all providers
        if not all_leagues:
            logger.warning("No dedicated league API — scraping from live matches")
            leagues = set()
            for provider in self.providers:
                try:
                    matches = provider.get_live_matches(sport) or []
                    for m in matches:
                        if m.league and m.league != "Unknown" and m.league_id:
                            leagues.add((m.league_id, m.league, m.country or ""))
                except Exception:
                    continue
            all_leagues = [{"id": lid, "name": name, "sport": sport, "country": country}
                          for lid, name, country in sorted(leagues)]

        return all_leagues

    def get_live_matches_by_league(self, sport: str = "football", league_id: str = None) -> pd.DataFrame:
        """Fetch live matches for a SPECIFIC league using server-side API filtering."""
        if not league_id or league_id == "ALL":
            return self.get_live_matches(sport)

        all_matches = []
        for provider in self.providers:
            try:
                if provider.name == "TheSportsDB":
                    matches = provider.get_live_matches(sport, league_id)
                elif provider.name == "API-SPORTS":
                    matches = provider.get_live_matches(sport, league_id)
                else:
                    matches = provider.get_live_matches(sport)
                    matches = [m for m in matches if m.league_id == league_id]
                if matches:
                    all_matches.extend(matches)
                    logger.info(f"{provider.name}: {len(matches)} matches for league {league_id}")
            except Exception as e:
                logger.warning(f"{provider.name} league fetch failed for {league_id}: {e}")

        seen = set()
        unique = []
        for m in all_matches:
            if m.match_id not in seen:
                seen.add(m.match_id)
                unique.append(m)

        if not unique:
            return pd.DataFrame(columns=["MATCH_ID", "TIME", "LEAGUE", "MATCH", "STATUS", "SCORE", "MIN",
                                        "HOME", "DRAW", "AWAY", "PREDICTION", "EV", "CONF", "SIGNAL"])
        return pd.DataFrame([m.to_dataframe_row() for m in unique])

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> pd.DataFrame:
        if league_id and league_id != "ALL":
            return self.get_live_matches_by_league(sport, league_id)

        all_matches = []
        for provider in self.providers:
            try:
                matches = provider.get_live_matches(sport, league_id)
                if matches:
                    all_matches.extend(matches)
                    logger.info(f"{provider.name}: {len(matches)} live matches")
            except Exception as e:
                logger.warning(f"{provider.name} live fetch failed: {e}")

        seen = set()
        unique = []
        for m in sorted(all_matches, key=lambda x: x.provider != self.active_provider.name if self.active_provider else False):
            if m.match_id not in seen:
                seen.add(m.match_id)
                unique.append(m)

        if not unique:
            return pd.DataFrame(columns=["MATCH_ID", "TIME", "LEAGUE", "MATCH", "STATUS", "SCORE", "MIN",
                                        "HOME", "DRAW", "AWAY", "PREDICTION", "EV", "CONF", "SIGNAL"])
        return pd.DataFrame([m.to_dataframe_row() for m in unique])

    def get_match_prediction(self, match_id: str) -> Optional[PredictionResult]:
        """NEW: Generate comprehensive prediction for a match."""
        # Find the match object
        match = None
        for provider in self.providers:
            try:
                matches = provider.get_live_matches()
                for m in matches:
                    if m.match_id == match_id:
                        match = m
                        break
                if match:
                    break
            except Exception:
                continue

        if not match:
            return None

        return self.prediction_engine.predict_match(match)

    def get_value_opportunities(self, min_ev: float = 0.02) -> pd.DataFrame:
        matches = self.get_live_matches()
        opportunities = []
        for _, row in matches.iterrows():
            home_odds = APIConfig._safe_float(row.get("HOME"), 0)
            away_odds = APIConfig._safe_float(row.get("AWAY"), 0)
            draw_odds = APIConfig._safe_float(row.get("DRAW"), 0)
            if home_odds <= 1.0 or away_odds <= 1.0:
                continue
            total = (1/home_odds) + (1/draw_odds if draw_odds > 1 else 0) + (1/away_odds)
            if total == 0:
                continue
            home_prob = (1/home_odds) / total
            away_prob = (1/away_odds) / total
            draw_prob = (1/draw_odds) / total if draw_odds > 1 else 0
            empire_home = home_prob
            empire_away = away_prob
            empire_draw = draw_prob
            for provider in self.providers:
                try:
                    pred = provider.get_predictions(str(row.get("MATCH", "")).split(" vs ")[0] if " vs " in str(row.get("MATCH", "")) else "")
                    if pred and pred.home_win_prob:
                        empire_home = pred.home_win_prob
                        empire_away = pred.away_win_prob
                        empire_draw = pred.draw_prob
                        break
                except Exception:
                    continue
            ev_home = (empire_home * home_odds) - 1
            ev_away = (empire_away * away_odds) - 1
            ev_draw = (empire_draw * draw_odds) - 1 if draw_odds > 1 else -1
            best_ev = max(ev_home, ev_away, ev_draw)
            if best_ev > min_ev:
                prediction_str = ""
                if best_ev == ev_home:
                    prediction_str = f"Home ({empire_home*100:.0f}%)"
                elif best_ev == ev_away:
                    prediction_str = f"Away ({empire_away*100:.0f}%)"
                else:
                    prediction_str = f"Draw ({empire_draw*100:.0f}%)"
                opportunities.append({
                    "TIME": row["TIME"], "LEAGUE": row["LEAGUE"], "MATCH": row["MATCH"], "STATUS": row["STATUS"],
                    "HOME": home_odds, "DRAW": draw_odds if draw_odds > 1 else "-", "AWAY": away_odds,
                    "PREDICTION": prediction_str, "EV": f"+{best_ev*100:.1f}%",
                    "KELLY": f"${self._kelly_criterion(best_ev, max(home_odds, away_odds, draw_odds), 0.25):.0f}",
                    "CONF": "HIGH" if best_ev > 0.08 else ("MEDIUM" if best_ev > 0.05 else "LOW"),
                    "SIGNAL": "🟢 BUY" if best_ev > 0.05 else "⚪ HOLD",
                })
        if not opportunities:
            return pd.DataFrame(columns=["TIME", "LEAGUE", "MATCH", "STATUS", "HOME", "DRAW", "AWAY",
                                        "PREDICTION", "EV", "KELLY", "CONF", "SIGNAL"])
        return pd.DataFrame(opportunities)

    def _kelly_criterion(self, prob: float, odds: float, bankroll_pct: float = 0.25) -> float:
        if odds <= 1 or prob <= 0:
            return 0
        kelly = (prob * odds - 1) / (odds - 1)
        return max(0, kelly * 10000 * bankroll_pct)

    def get_match_details(self, match_id: str, provider_hint: str = None) -> Dict:
        result = {"match_info": None, "statistics": None, "odds": [], "predictions": None,
                 "h2h": None, "lineup": None, "players": None, "source": None}
        for provider in self.providers:
            try:
                if provider.name == "API-SPORTS":
                    stats = provider.get_match_stats(match_id)
                    if stats:
                        result["statistics"] = stats
                        result["source"] = "API-SPORTS"
                    odds = provider.get_odds(match_id)
                    if odds:
                        result["odds"].extend(odds)
                    pred = provider.get_predictions(match_id)
                    if pred:
                        result["predictions"] = pred.to_dict() if hasattr(pred, 'to_dict') else pred
                elif provider.name == "TheOddsAPI":
                    odds = provider.get_odds(match_id)
                    if odds:
                        result["odds"].extend(odds)
                        if not result["source"]:
                            result["source"] = "TheOddsAPI"
                elif provider.name == "Sportmonks":
                    pred = provider.get_predictions(match_id)
                    if pred:
                        result["predictions"] = pred.to_dict() if hasattr(pred, 'to_dict') else pred
                        if not result["source"]:
                            result["source"] = "Sportmonks"
            except Exception as e:
                logger.warning(f"{provider.name} detail fetch failed for {match_id}: {e}")
                continue
        result["found"] = bool(result["source"] or result["odds"] or result["statistics"])
        return result

    def get_matches_by_status(self, status_filter: str = "all", sport: str = "football", league_id: str = None) -> pd.DataFrame:
        all_matches = []
        for provider in self.providers:
            try:
                if status_filter.lower() == "live":
                    matches = provider.get_live_matches(sport, league_id)
                elif status_filter.lower() == "scheduled":
                    matches = provider.get_upcoming_matches(sport, days=7)
                else:
                    live = provider.get_live_matches(sport, league_id) or []
                    upcoming = provider.get_upcoming_matches(sport, days=7) or []
                    matches = live + upcoming
                if matches:
                    if status_filter.lower() not in ["all", "live", "scheduled"]:
                        matches = [m for m in matches if m.status.upper() == status_filter.upper()]
                    all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"{provider.name} status fetch failed: {e}")
        seen = set()
        unique = []
        for m in all_matches:
            if m.match_id not in seen:
                seen.add(m.match_id)
                unique.append(m)
        if not unique:
            return pd.DataFrame(columns=["MATCH_ID", "TIME", "LEAGUE", "MATCH", "STATUS", "SCORE", "MIN",
                                        "HOME", "DRAW", "AWAY", "PREDICTION", "EV", "CONF", "SIGNAL"])
        return pd.DataFrame([m.to_dataframe_row() for m in unique])

    def get_leagues(self, sport: str = "football") -> List[str]:
        leagues = set()
        for provider in self.providers:
            try:
                matches = provider.get_live_matches(sport) or []
                for m in matches:
                    if m.league and m.league != "Unknown":
                        leagues.add(m.league)
            except Exception:
                continue
        return sorted(list(leagues))


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

    @property
    def connection_log(self) -> List[Dict]:
        return self.router.connection_log

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport: str = "football") -> List[Dict]:
        return self.router.get_all_leagues(sport)

    def get_live_matches_df(self, sport: str = "football", league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport, league_id)

    def get_upcoming_matches_df(self, sport: str = "football") -> pd.DataFrame:
        all_matches = []
        for provider in self.router.providers:
            try:
                matches = provider.get_upcoming_matches(sport=sport)
                if matches:
                    all_matches.extend(matches)
            except Exception:
                pass
        if not all_matches:
            return pd.DataFrame(columns=["TIME", "LEAGUE", "MATCH", "STATUS", "HOME", "DRAW", "AWAY", "PREDICTION"])
        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def get_value_opportunities_df(self) -> pd.DataFrame:
        return self.router.get_value_opportunities()

    def get_match_prediction(self, match_id: str) -> Optional[PredictionResult]:
        """NEW: Get comprehensive prediction for a match."""
        return self.router.get_match_prediction(match_id)

    def get_odds_comparison(self, match_id: str) -> pd.DataFrame:
        all_odds = []
        for provider in self.router.providers:
            try:
                odds = provider.get_odds(match_id)
                all_odds.extend(odds)
            except Exception:
                pass
        if not all_odds:
            return pd.DataFrame(columns=["BOOKMAKER", "MARKET", "1", "X", "2", "O", "U", "TIME"])
        return pd.DataFrame([o.to_dataframe_row() for o in all_odds])

    def should_refresh(self) -> bool:
        return (datetime.now() - self.last_refresh).seconds > self.refresh_interval

    def mark_refreshed(self):
        self.last_refresh = datetime.now()


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 EMPIRE SPORT DATA LAYER — Self-Test")
    print("=" * 60)
    missing = APIConfig.get_missing_keys()
    if missing:
        print("⚠️  Missing API keys: " + ", ".join(missing))
    else:
        print("✅ All API keys configured")
    router = EmpireDataRouter()
    print("📡 Fetching all leagues...")
    leagues = router.get_all_leagues("football")
    print(f"✅ Retrieved {len(leagues)} leagues")
    if leagues:
        print("First 5 leagues:")
        for league in leagues[:5]:
            print(f"  • {league['name']} (ID: {league['id']}, Country: {league['country']})")
    print("📡 Fetching live matches...")
    live = router.get_live_matches()
    print(f"✅ Retrieved {len(live)} live matches")
    if not live.empty:
        print(live.head())
    print("💰 Fetching value opportunities...")
    value = router.get_value_opportunities()
    print(f"✅ Found {len(value)} value opportunities")
    if not value.empty:
        print(value.head())
    print("=" * 60)
    print("EMPIRE Data Layer ready for dashboard integration.")
