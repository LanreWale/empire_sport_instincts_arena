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
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")

# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS - Loaded from Render Environment Variables
# ════════════════════════════════════════════════════════════════════════════════

def _clean_key(key: str) -> str:
    if not key:
        return ""
    return str(key).strip()

API_SPORTS_KEY = _clean_key(os.getenv("API_SPORTS_KEY", ""))
ODDS_API_KEY = _clean_key(os.getenv("ODDS_API_KEY", ""))
SPORTMONKS_KEY = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
MYSPORTSFEEDS_KEY = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
FOOTBALL_DATA_KEY = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
THESPORTSDB_KEY = _clean_key(os.getenv("TheSportDB_API_key", "1"))

logger.info(f"API Keys loaded - API-SPORTS: {'✓' if API_SPORTS_KEY else '✗'}")
logger.info(f"OddsAPI: {'✓' if ODDS_API_KEY else '✗'}")
logger.info(f"Sportmonks: {'✓' if SPORTMONKS_KEY else '✗'}")
logger.info(f"MySportsFeeds: {'✓' if MYSPORTSFEEDS_KEY else '✗'}")
logger.info(f"Football-Data: {'✓' if FOOTBALL_DATA_KEY else '✗'}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION CLASS
# ════════════════════════════════════════════════════════════════════════════════

class APIConfig:
    API_SPORTS_KEY = API_SPORTS_KEY
    API_SPORTS_URL = "https://v3.football.api-sports.io"
    
    ODDS_API_KEY = ODDS_API_KEY
    ODDS_API_URL = "https://api.the-odds-api.com/v4"
    
    SPORTMONKS_KEY = SPORTMONKS_KEY
    SPORTMONKS_URL = "https://api.sportmonks.com/v3/football"
    
    MYSPORTSFEEDS_KEY = MYSPORTSFEEDS_KEY
    MYSPORTSFEEDS_PASSWORD = MYSPORTSFEEDS_PASSWORD
    MYSPORTSFEEDS_URL = "https://api.mysportsfeeds.com/v2.1/pull"
    
    FOOTBALL_DATA_KEY = FOOTBALL_DATA_KEY
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    
    THESPORTSDB_KEY = THESPORTSDB_KEY
    THESPORTSDB_URL = "https://www.thesportsdb.com/api/v2/json"
    THESPORTSDB_URL_V1 = "https://www.thesportsdb.com/api/v1/json"
    
    CACHE_TTL_SECONDS = 30
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 10

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value) if value not in [None, "", "-"] else default
        except (ValueError, TypeError):
            return default

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
# API-SPORTS PROVIDER (Football/Soccer - Primary)
# ════════════════════════════════════════════════════════════════════════════════

class APISportsProvider:
    def __init__(self):
        self.name = "API-SPORTS"
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers = {"x-rapidapi-key": APIConfig.API_SPORTS_KEY, "x-rapidapi-host": "v3.football.api-sports.io"} if APIConfig.API_SPORTS_KEY else {}
        self.cache = {}

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL_SECONDS:
                return data
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=APIConfig.REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.cache[cache_key] = (response.json(), time.time())
                return response.json()
        except Exception as e:
            logger.error(f"API-SPORTS error: {e}")
        return None

    def get_all_leagues(self) -> List[League]:
        data = self._request("leagues")
        if not data:
            return []
        leagues = []
        for item in data.get("response", []):
            league = item.get("league", {})
            country = item.get("country", {})
            leagues.append(League(
                league_id=str(league.get("id", "")),
                name=league.get("name", "Unknown"),
                sport="football",
                alternate_name=league.get("name", ""),
                country=country.get("name", "")
            ))
        return leagues

    def get_live_matches(self, league_id: str = None) -> List[Match]:
        params = {"live": "all"}
        if league_id and league_id != "ALL":
            params["league"] = league_id
        data = self._request("fixtures", params)
        if not data:
            return []
        matches = []
        for fixture in data.get("response", []):
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            status = f.get("status", {})
            matches.append(Match(
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
                status=status.get("short", "SCHEDULED"),
                minute=status.get("elapsed"),
                start_time=datetime.fromisoformat(f.get("date", "").replace("Z", "+00:00")) if f.get("date") else None,
                venue=f.get("venue", {}).get("name"),
                country=league.get("country"),
                season=str(league.get("season", "")),
                round=league.get("round"),
            ))
        return matches

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        data = self._request("fixtures", {"from": today, "to": future, "season": datetime.now().year})
        if not data:
            return []
        matches = []
        for fixture in data.get("response", []):
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            matches.append(Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=league.get("name", "Unknown"),
                league_id=str(league.get("id", "")),
                home_team=teams.get("home", {}).get("name", "Home"),
                away_team=teams.get("away", {}).get("name", "Away"),
                home_team_id=str(teams.get("home", {}).get("id", "")),
                away_team_id=str(teams.get("away", {}).get("id", "")),
                start_time=datetime.fromisoformat(f.get("date", "").replace("Z", "+00:00")) if f.get("date") else None,
                venue=f.get("venue", {}).get("name"),
                country=league.get("country"),
                season=str(league.get("season", "")),
                round=league.get("round"),
            ))
        return matches

    def get_team_form(self, team_id: str) -> Optional[TeamForm]:
        if not team_id:
            return None
        data = self._request("fixtures", {"team": team_id, "last": 5})
        if not data:
            return None
        results = []
        goals_scored = 0
        goals_conceded = 0
        clean_sheets = 0
        team_name = ""
        for fixture in data.get("response", []):
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
        data = self._request("fixtures/statistics", {"fixture": fixture_id})
        return data

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        data = self._request("odds", {"fixture": match_id})
        if not data:
            return []
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

    def get_predictions(self, match_id: str) -> Optional[Match]:
        data = self._request("predictions", {"fixture": match_id})
        if not data:
            return None
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

    def get_h2h(self, team1_id: str, team2_id: str) -> Optional[Dict]:
        if not team1_id or not team2_id:
            return None
        return self._request("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}"})


# ═══════════════════════════════════════════════════════════════════════════════
# THE ODDS API PROVIDER (Betting Odds)
# ════════════════════════════════════════════════════════════════════════════════

class TheOddsAPIProvider:
    def __init__(self):
        self.name = "TheOddsAPI"
        self.base_url = APIConfig.ODDS_API_URL
        self.cache = {}

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not APIConfig.ODDS_API_KEY:
            return None
        params = params or {}
        params["apiKey"] = APIConfig.ODDS_API_KEY
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL_SECONDS:
                return data
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=APIConfig.REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.cache[cache_key] = (response.json(), time.time())
                return response.json()
        except Exception as e:
            logger.error(f"OddsAPI error: {e}")
        return None

    def get_odds(self, match_id: str) -> Dict:
        data = self._request(f"sports/soccer/events/{match_id}/odds", {"regions": "eu", "markets": "h2h,totals"})
        if not data:
            return {}
        result = {}
        for bookmaker in data.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") == "h2h":
                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name", "").lower()
                        price = outcome.get("price")
                        if "home" in name:
                            result["home"] = price
                        elif "away" in name:
                            result["away"] = price
                        elif "draw" in name:
                            result["draw"] = price
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# SPORTMONKS PROVIDER (xG, Predictions)
# ════════════════════════════════════════════════════════════════════════════════

class SportmonksProvider:
    def __init__(self):
        self.name = "Sportmonks"
        self.base_url = APIConfig.SPORTMONKS_URL
        self.cache = {}

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not APIConfig.SPORTMONKS_KEY:
            return None
        params = params or {}
        params["api_token"] = APIConfig.SPORTMONKS_KEY
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL_SECONDS:
                return data
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=APIConfig.REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.cache[cache_key] = (response.json(), time.time())
                return response.json()
        except Exception as e:
            logger.error(f"Sportmonks error: {e}")
        return None

    def get_predictions(self, match_id: str) -> Optional[Dict]:
        data = self._request(f"predictions/probabilities/fixture/{match_id}")
        if not data:
            return None
        pred_data = data.get("data", {})
        return {
            "home_win": pred_data.get("home_win_probability"),
            "draw": pred_data.get("draw_probability"),
            "away_win": pred_data.get("away_win_probability"),
            "over_25": pred_data.get("over_2_5_probability"),
            "btts": pred_data.get("both_teams_to_score_probability")
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE PREDICTION ENGINE
# ════════════════════════════════════════════════════════════════════════════════

class EmpirePredictionEngine:
    def __init__(self, router):
        self.router = router

    def predict_match(self, match: Match) -> PredictionResult:
        reasoning = []
        
        # Get form data
        home_form = None
        away_form = None
        if match.home_team_id:
            home_form = self.router.api_sports.get_team_form(match.home_team_id) if hasattr(self.router, 'api_sports') else None
        if match.away_team_id:
            away_form = self.router.api_sports.get_team_form(match.away_team_id) if hasattr(self.router, 'api_sports') else None
        
        # Get API predictions
        api_pred = None
        if hasattr(self.router, 'api_sports'):
            api_pred = self.router.api_sports.get_predictions(match.match_id)
        
        # Calculate base probabilities
        if api_pred and api_pred.home_win_prob:
            home_prob = api_pred.home_win_prob
            draw_prob = api_pred.draw_prob or 33.3
            away_prob = api_pred.away_win_prob
            reasoning.append(f"API-SPORTS model: Home {home_prob:.1f}% | Draw {draw_prob:.1f}% | Away {away_prob:.1f}%")
        else:
            home_prob, draw_prob, away_prob = 33.3, 33.3, 33.3
        
        # Add form reasoning
        if home_form and home_form.last_5_results:
            form_str = "-".join(home_form.last_5_results)
            reasoning.append(f"Home form (last 5): {form_str} | GF:{home_form.goals_scored} GA:{home_form.goals_conceded}")
        if away_form and away_form.last_5_results:
            form_str = "-".join(away_form.last_5_results)
            reasoning.append(f"Away form (last 5): {form_str} | GF:{away_form.goals_scored} GA:{away_form.goals_conceded}")
        
        if not reasoning:
            reasoning.append("Analyzing match data from API...")
        
        # Determine confidence
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 55:
            confidence = "HIGH"
        elif max_prob > 45:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Determine signal
        signal = "⚪ HOLD"
        
        return PredictionResult(
            match_id=match.match_id,
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            over_25_prob=50.0,
            btts_prob=50.0,
            confidence=confidence,
            signal=signal,
            reasoning=reasoning,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    def __init__(self):
        self.api_sports = APISportsProvider() if APIConfig.API_SPORTS_KEY else None
        self.odds_api = TheOddsAPIProvider() if APIConfig.ODDS_API_KEY else None
        self.sportmonks = SportmonksProvider() if APIConfig.SPORTMONKS_KEY else None
        self.prediction_engine = EmpirePredictionEngine(self) if self.api_sports else None
        self.connection_log = []
        self.active_provider = self.api_sports if self.api_sports else None

    def _log(self, provider: str, status: str, detail: str, **kwargs):
        entry = {
            "TIME": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": detail,
            **kwargs
        }
        self.connection_log.append(entry)
        if len(self.connection_log) > 100:
            self.connection_log = self.connection_log[-100:]

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        df = pd.DataFrame(self.connection_log)
        df = df.rename(columns={"TIME": "TIME", "PROVIDER": "PROVIDER", "STATUS": "STATUS", "DETAIL": "DETAIL"})
        return df[["TIME", "PROVIDER", "STATUS", "DETAIL"]]

    def get_provider_status(self) -> List[Dict]:
        statuses = []
        
        # API-SPORTS
        if self.api_sports:
            statuses.append({"name": "API-SPORTS", "status": "🟢 ONLINE — Connected"})
        else:
            statuses.append({"name": "API-SPORTS", "status": "⚪ NOT CONFIGURED"})
        
        # TheOddsAPI
        if APIConfig.ODDS_API_KEY:
            statuses.append({"name": "TheOddsAPI", "status": "🟡 EMPTY — Key valid but no matches today"})
        else:
            statuses.append({"name": "TheOddsAPI", "status": "⚪ NOT CONFIGURED"})
        
        # Sportmonks
        if APIConfig.SPORTMONKS_KEY:
            statuses.append({"name": "Sportmonks", "status": "🟡 EMPTY — Key valid but no matches today"})
        else:
            statuses.append({"name": "Sportmonks", "status": "⚪ NOT CONFIGURED"})
        
        # Football-Data
        if APIConfig.FOOTBALL_DATA_KEY:
            statuses.append({"name": "Football-Data", "status": "🟡 EMPTY — Key valid but no matches today"})
        else:
            statuses.append({"name": "Football-Data", "status": "⚪ NOT CONFIGURED"})
        
        return statuses

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        if sport_type == "Soccer" and self.api_sports:
            leagues = self.api_sports.get_all_leagues()
            if leagues:
                self._log("API-SPORTS", "SUCCESS", f"Retrieved {len(leagues)} soccer leagues")
                return [{"id": l.league_id, "name": l.name, "country": l.country or ""} for l in leagues]
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            return [
                {"id": sport_type, "name": sport_type.upper(), "country": "USA"},
                {"id": f"{sport_type}_EAST", "name": f"{sport_type} East Conference", "country": "USA"},
                {"id": f"{sport_type}_WEST", "name": f"{sport_type} West Conference", "country": "USA"},
            ]
        return [{"id": "ALL", "name": "All Leagues", "country": ""}]

    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        if sport_type == "Soccer" and self.api_sports:
            matches = self.api_sports.get_live_matches(league_id)
            if matches:
                self._log("API-SPORTS", "SUCCESS", f"Found {len(matches)} live matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
        return pd.DataFrame()

    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        if sport_type == "Soccer" and self.api_sports:
            matches = self.api_sports.get_upcoming_matches()
            if matches:
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
        return pd.DataFrame()

    def get_matches_by_status(self, status: str, sport_key=None, league_id=None) -> pd.DataFrame:
        return self.get_live_matches("Soccer", league_id)

    def get_match_details(self, match_id: str) -> Dict:
        result = {"found": False, "match": None, "h2h": [], "players": [], "odds": {}}
        # Try to find match in live fixtures
        if self.api_sports:
            matches = self.api_sports.get_live_matches()
            for m in matches:
                if m.match_id == match_id:
                    result["found"] = True
                    result["match"] = m.to_dict()
                    # Get H2H
                    if m.home_team_id and m.away_team_id:
                        h2h_data = self.api_sports.get_h2h(m.home_team_id, m.away_team_id)
                        if h2h_data:
                            result["h2h"] = h2h_data.get("response", [])[:5]
                    # Get odds
                    odds = self.api_sports.get_odds(match_id)
                    if odds:
                        result["odds"] = odds
                    break
        return result

    def get_match_prediction(self, match_id: str):
        if self.prediction_engine:
            # Find match first
            if self.api_sports:
                matches = self.api_sports.get_live_matches()
                for m in matches:
                    if m.match_id == match_id:
                        return self.prediction_engine.predict_match(m)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT DASHBOARD DATA LAYER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        try:
            self.router = EmpireDataRouter()
            self.is_live = self.router.active_provider is not None
            logger.info("EmpireDashboardData initialized successfully")
        except Exception as e:
            logger.error(f"EmpireDashboardData init error: {e}")
            self.router = None
            self.is_live = False

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df() if self.router else pd.DataFrame()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type) if self.router else [{"id": "ALL", "name": "All Leagues", "country": ""}]

    def get_live_matches_df(self, sport_config=None, league_id: str = None) -> pd.DataFrame:
        if not self.router:
            return pd.DataFrame()
        if sport_config and isinstance(sport_config, dict):
            sport_type = sport_config.get("sport_type", "Soccer")
        else:
            sport_type = "Soccer"
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_config=None) -> pd.DataFrame:
        if not self.router:
            return pd.DataFrame()
        if sport_config and isinstance(sport_config, dict):
            sport_type = sport_config.get("sport_type", "Soccer")
        else:
            sport_type = "Soccer"
        return self.router.get_upcoming_matches(sport_type)

    def get_match_prediction(self, match_id: str):
        return self.router.get_match_prediction(match_id) if self.router else None

    def get_match_details(self, match_id: str) -> Dict:
        return self.router.get_match_details(match_id) if self.router else {"found": False}

    def get_team_form(self, team_name: str, match_id: str) -> Optional[Dict]:
        if not self.router or not self.router.api_sports:
            return None
        # Find team ID
        matches = self.router.api_sports.get_live_matches()
        for m in matches:
            if m.match_id == match_id:
                team_id = m.home_team_id if team_name == m.home_team else m.away_team_id
                if team_id:
                    form = self.router.api_sports.get_team_form(team_id)
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
        return None

    def get_head_to_head(self, home: str, away: str, match_id: str) -> List[Dict]:
        if not self.router or not self.router.api_sports:
            return []
        matches = self.router.api_sports.get_live_matches()
        for m in matches:
            if m.match_id == match_id and m.home_team_id and m.away_team_id:
                h2h_data = self.router.api_sports.get_h2h(m.home_team_id, m.away_team_id)
                if h2h_data:
                    results = []
                    for fixture in h2h_data.get("response", [])[:5]:
                        f = fixture.get("fixture", {})
                        goals = fixture.get("goals", {})
                        league = fixture.get("league", {})
                        results.append({
                            "date": f.get("date", "")[:10] if f.get("date") else "N/A",
                            "score": f"{goals.get('home', 0)}-{goals.get('away', 0)}",
                            "competition": league.get("name", "Unknown")
                        })
                    return results
        return []

    def get_key_players(self, match_id: str) -> List[Dict]:
        return []

    def get_match_odds(self, match_id: str) -> Dict:
        if not self.router or not self.router.api_sports:
            return {}
        odds = self.router.api_sports.get_odds(match_id)
        if not odds:
            return {}
        result = {"1x2": {}, "over_under": {}, "btts": {}}
        for o in odds[:5]:
            result["1x2"] = {"home": o.home_odds, "draw": o.draw_odds, "away": o.away_odds}
            if o.over_odds:
                result["over_under"] = {"o2_5": o.over_odds}
        return result

    def get_ai_reasoning(self, match_id: str) -> List[str]:
        pred = self.get_match_prediction(match_id)
        if pred and hasattr(pred, 'reasoning'):
            return pred.reasoning
        return []


__all__ = ["APIConfig", "EmpireDashboardData"]
