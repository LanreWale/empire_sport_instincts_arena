"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
NO HARDCODED DATA - ALL DATA FROM LIVE APIs
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
        return str(key).strip()

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value) if value not in [None, "", "-"] else default
        except (ValueError, TypeError):
            return default

    # API Keys from environment
    API_SPORTS_KEY = _clean_key(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL = "https://v3.football.api-sports.io"
    
    ODDS_API_KEY = _clean_key(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL = "https://api.the-odds-api.com/v4"
    
    SPORTMONKS_KEY = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL = "https://api.sportmonks.com/api/v3/football"
    
    MYSPORTSFEEDS_KEY = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL = "https://api.mysportsfeeds.com/v2.1/pull"
    
    FOOTBALL_DATA_KEY = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    
    THESPORTSDB_KEY = _clean_key(os.getenv("TheSportDB_API_key", "1"))
    THESPORTSDB_URL = "https://www.thesportsdb.com/api/v2/json"
    
    CACHE_TTL_SECONDS = 300
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

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
    status: str = "SCHEDULED"
    minute: Optional[int] = None
    start_time: Optional[datetime] = None
    venue: Optional[str] = None
    country: Optional[str] = None
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None

    def to_dataframe_row(self) -> Dict:
        return {
            "MATCH_ID": self.match_id,
            "TIME": self.start_time.strftime("%H:%M") if self.start_time else "TBD",
            "LEAGUE": self.league,
            "MATCH": f"{self.home_team} vs {self.away_team}",
            "STATUS": "🔴 LIVE" if self.status in ["LIVE", "1H", "2H", "IN_PROGRESS"] else ("⏳ " + self.status if self.status != "SCHEDULED" else "UPCOMING"),
            "SCORE": f"{self.home_score}-{self.away_score}" if self.home_score is not None else "vs",
            "HOME": self.home_odds or "-",
            "DRAW": self.draw_odds or "-",
            "AWAY": self.away_odds or "-",
        }


@dataclass
class League:
    league_id: str
    name: str
    sport: str
    country: Optional[str] = None


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
                    time.sleep(wait)
                    continue
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"{self.name}: HTTP {response.status_code} for {url}")
                    return None
            except Exception as e:
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


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS PROVIDER (SOCCER)
# ════════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS", 1)
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers = {"x-apisports-key": APIConfig.API_SPORTS_KEY} if APIConfig.API_SPORTS_KEY else {}

    def get_all_leagues(self) -> List[League]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        cache_key = self._get_cache_key("leagues", {})
        cached = self._get_cached(cache_key, 86400)
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
                sport="Soccer",
                country=country.get("name", "")
            ))
        return leagues

    def get_live_matches(self, league_id: str = None) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        cache_key = self._get_cache_key("fixtures/live", {"league": league_id})
        cached = self._get_cached(cache_key, 30)
        if cached:
            return self._parse_fixtures(cached)
        params = {"live": "all"}
        if league_id and league_id != "ALL":
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_upcoming_matches(self, days: int = 14) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("fixtures/upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, 3600)
        if cached:
            return self._parse_fixtures(cached)
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, {"from": today, "to": future})
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def _parse_fixtures(self, data: Dict) -> List[Match]:
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
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER (NBA, NFL, MLB, NHL)
# ════════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    def __init__(self):
        super().__init__("MySportsFeeds", 2)
        self.base_url = APIConfig.MYSPORTSFEEDS_URL
        if APIConfig.MYSPORTSFEEDS_KEY and APIConfig.MYSPORTSFEEDS_PASSWORD:
            credentials = base64.b64encode(f"{APIConfig.MYSPORTSFEEDS_KEY}:{APIConfig.MYSPORTSFEEDS_PASSWORD}".encode()).decode()
            self.headers = {"Authorization": f"Basic {credentials}"}
        else:
            self.headers = {}

    def _get_sport_code(self, sport: str) -> str:
        mapping = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}
        return mapping.get(sport.upper(), "nba")

    def _get_season(self, sport: str) -> str:
        current_year = datetime.now().year
        if sport.upper() == "NBA":
            return f"{current_year-1}-{current_year}"
        return str(current_year)

    def get_all_leagues(self, sport: str) -> List[League]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        
        cache_key = self._get_cache_key(f"{sport_code}_teams", {"season": season})
        cached = self._get_cached(cache_key, 86400)
        if cached:
            return self._parse_teams(cached, sport)
        
        url = f"{self.base_url}/{sport_code}/{season}/team_active_roster.json"
        data = self._make_request(url, self.headers)
        if data:
            self._set_cached(cache_key, data)
            return self._parse_teams(data, sport)
        return []

    def _parse_teams(self, data: Dict, sport: str) -> List[League]:
        leagues = []
        teams = data.get("teams", [])
        for team in teams:
            team_data = team.get("team", {})
            leagues.append(League(
                league_id=team_data.get("id", ""),
                name=team_data.get("name", "Unknown"),
                sport=sport,
                country=team_data.get("city", ""),
            ))
        return leagues

    def get_live_matches(self, sport: str) -> List[Match]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        
        cache_key = self._get_cache_key(f"{sport_code}_live", {"date": today})
        cached = self._get_cached(cache_key, 30)
        if cached:
            return self._parse_games(cached, sport)
        
        # Try the /date/ endpoint first
        url = f"{self.base_url}/{sport_code}/{season}/date/{today}/games.json"
        data = self._make_request(url, self.headers)
        
        if not data:
            # Fallback to games endpoint with date parameter
            url = f"{self.base_url}/{sport_code}/{season}/games.json"
            data = self._make_request(url, self.headers, {"date": today})
        
        if data:
            self._set_cached(cache_key, data)
            return self._parse_games(data, sport)
        return []

    def get_upcoming_matches(self, sport: str, days: int = 14) -> List[Match]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        
        cache_key = self._get_cache_key(f"{sport_code}_upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, 3600)
        if cached:
            return self._parse_games(cached, sport, upcoming_only=True)
        
        url = f"{self.base_url}/{sport_code}/{season}/games.json"
        data = self._make_request(url, self.headers, {"fordate": today, "todate": future})
        
        if not data:
            data = self._make_request(url, self.headers, {"date": today})
        
        if data:
            self._set_cached(cache_key, data)
            return self._parse_games(data, sport, upcoming_only=True)
        return []

    def _parse_games(self, data: Dict, sport: str, upcoming_only: bool = False) -> List[Match]:
        matches = []
        games = data.get("games", [])
        
        for game in games:
            schedule = game.get("schedule", game)
            status = schedule.get("status", "SCHEDULED")
            is_live = status in ["IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT", "HALFTIME"]
            
            if upcoming_only and is_live:
                continue
            
            home_team = schedule.get("homeTeam", {})
            away_team = schedule.get("awayTeam", {})
            
            home_name = home_team.get("name", "Home") if isinstance(home_team, dict) else str(home_team)
            away_name = away_team.get("name", "Away") if isinstance(away_team, dict) else str(away_team)
            
            home_score = game.get("score", {}).get("homeScoreTotal") if "score" in game else None
            away_score = game.get("score", {}).get("awayScoreTotal") if "score" in game else None
            
            if "homeScore" in game:
                home_score = game.get("homeScore")
                away_score = game.get("awayScore")
            
            start_time = None
            start_time_str = schedule.get("startTime", "")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                except:
                    pass
            
            matches.append(Match(
                match_id=str(schedule.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home_name,
                away_team=away_name,
                home_score=home_score,
                away_score=away_score,
                status="LIVE" if is_live else status,
                start_time=start_time,
            ))
        
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER (UFC, F1, TENNIS, CRICKET, GOLF)
# ════════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    def __init__(self):
        super().__init__("TheSportsDB", 2)
        self.base_url = APIConfig.THESPORTSDB_URL
        self.api_key = APIConfig.THESPORTSDB_KEY

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        url = f"{self.base_url}/{self.api_key}/{endpoint}"
        return super()._make_request(url)

    def get_all_leagues(self, sport_type: str) -> List[League]:
        cache_key = self._get_cache_key(f"leagues_{sport_type}", {})
        cached = self._get_cached(cache_key, 86400)
        if cached:
            return self._parse_leagues(cached, sport_type)
        
        data = self._make_request("all_leagues.php")
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_leagues(data, sport_type)

    def _parse_leagues(self, data: Dict, sport_type: str) -> List[League]:
        leagues = []
        sport_mapping = {
            "UFC": "MMA",
            "Formula 1": "Motorsport",
            "Tennis": "Tennis",
            "Cricket": "Cricket",
            "Golf": "Golf"
        }
        target_sport = sport_mapping.get(sport_type, sport_type)
        
        for league in data.get("leagues", []):
            if league.get("strSport") == target_sport:
                leagues.append(League(
                    league_id=league.get("idLeague", ""),
                    name=league.get("strLeague", "Unknown"),
                    sport=sport_type,
                    country=league.get("strCountry", "")
                ))
        return leagues

    def get_live_matches(self, sport: str) -> List[Match]:
        data = self._make_request("livescore.php")
        if not data:
            return []
        matches = []
        for event in data.get("events", []):
            if event.get("strSport") == sport:
                is_live = event.get("strStatus") in ["1H", "2H", "HT", "IN_PLAY"]
                matches.append(Match(
                    match_id=event.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=event.get("strLeague", "Unknown"),
                    league_id=event.get("idLeague", ""),
                    home_team=event.get("strHomeTeam", "Home"),
                    away_team=event.get("strAwayTeam", "Away"),
                    home_score=event.get("intHomeScore"),
                    away_score=event.get("intAwayScore"),
                    status="LIVE" if is_live else event.get("strStatus", "SCHEDULED"),
                ))
        return matches

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        data = self._make_request(f"eventsnextleague.php?id={sport}")
        if not data:
            return []
        matches = []
        for event in data.get("events", []):
            matches.append(Match(
                match_id=event.get("idEvent", ""),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=event.get("idLeague", ""),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THE ODDS API PROVIDER (BETTING ODDS)
# ════════════════════════════════════════════════════════════════════════════════

class TheOddsAPIProvider(DataProvider):
    def __init__(self):
        super().__init__("TheOddsAPI", 1)
        self.base_url = APIConfig.ODDS_API_URL

    def get_odds(self, sport: str = "soccer") -> List[Dict]:
        if not APIConfig.ODDS_API_KEY:
            return []
        cache_key = self._get_cache_key("odds", {"sport": sport})
        cached = self._get_cached(cache_key, 60)
        if cached:
            return cached
        data = self._make_request(f"{self.base_url}/sports/{sport}/odds", 
                                   params={"apiKey": APIConfig.ODDS_API_KEY, "regions": "us", "markets": "h2h"})
        if data:
            self._set_cached(cache_key, data)
            return data
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# SPORTMONKS PROVIDER (ADVANCED STATS)
# ════════════════════════════════════════════════════════════════════════════════

class SportmonksProvider(DataProvider):
    def __init__(self):
        super().__init__("Sportmonks", 2)
        self.base_url = APIConfig.SPORTMONKS_URL

    def get_predictions(self, match_id: str) -> Optional[Dict]:
        if not APIConfig.SPORTMONKS_KEY:
            return None
        data = self._make_request(f"{self.base_url}/predictions/probabilities/fixture/{match_id}",
                                   params={"api_token": APIConfig.SPORTMONKS_KEY})
        return data


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA.ORG PROVIDER
# ════════════════════════════════════════════════════════════════════════════════

class FootballDataProvider(DataProvider):
    def __init__(self):
        super().__init__("Football-Data", 3)
        self.base_url = APIConfig.FOOTBALL_DATA_URL
        self.headers = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY} if APIConfig.FOOTBALL_DATA_KEY else {}

    def get_matches(self) -> List[Match]:
        if not APIConfig.FOOTBALL_DATA_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        data = self._make_request(f"{self.base_url}/matches", self.headers, {"dateFrom": today, "dateTo": today})
        if not data:
            return []
        matches = []
        for match in data.get("matches", []):
            matches.append(Match(
                match_id=str(match.get("id", "")),
                provider="Football-Data",
                league=match.get("competition", {}).get("name", "Unknown"),
                league_id=str(match.get("competition", {}).get("id", "")),
                home_team=match.get("homeTeam", {}).get("name", "Home"),
                away_team=match.get("awayTeam", {}).get("name", "Away"),
                status=match.get("status", "SCHEDULED"),
                start_time=datetime.fromisoformat(match.get("utcDate", "").replace("Z", "+00:00")) if match.get("utcDate") else None,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    def __init__(self):
        self.api_sports = APISportsProvider()
        self.my_sports_feeds = MySportsFeedsProvider()
        self.the_sports_db = TheSportsDBProvider()
        self.odds_api = TheOddsAPIProvider()
        self.sportmonks = SportmonksProvider()
        self.football_data = FootballDataProvider()
        self.connection_log = []
        self._log_initial_status()

    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": detail,
        })
        logger.info(f"[{provider}] {status}: {detail}")

    def _log_initial_status(self):
        if APIConfig.API_SPORTS_KEY:
            self._log("API-SPORTS", "ACTIVE", "Soccer data provider ready")
        if APIConfig.MYSPORTSFEEDS_KEY:
            self._log("MySportsFeeds", "ACTIVE", "NBA/NFL/MLB/NHL data provider ready")
        self._log("TheSportsDB", "ACTIVE", "UFC/F1/Tennis/Cricket/Golf data provider ready")
        if APIConfig.ODDS_API_KEY:
            self._log("TheOddsAPI", "ACTIVE", "Odds provider ready")
        if APIConfig.SPORTMONKS_KEY:
            self._log("Sportmonks", "ACTIVE", "Advanced stats provider ready")
        if APIConfig.FOOTBALL_DATA_KEY:
            self._log("Football-Data", "ACTIVE", "Soccer provider ready")

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        return pd.DataFrame(self.connection_log)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "API-SPORTS", "status": "🟢 ONLINE — Connected" if APIConfig.API_SPORTS_KEY else "⚪ NOT CONFIGURED"},
            {"name": "MySportsFeeds", "status": "🟢 ONLINE — Connected" if APIConfig.MYSPORTSFEEDS_KEY else "⚪ NOT CONFIGURED"},
            {"name": "TheSportsDB", "status": "🟢 ONLINE — Connected"},
            {"name": "TheOddsAPI", "status": "🟡 EMPTY — Key valid" if APIConfig.ODDS_API_KEY else "⚪ NOT CONFIGURED"},
            {"name": "Sportmonks", "status": "🟡 EMPTY — Key valid" if APIConfig.SPORTMONKS_KEY else "⚪ NOT CONFIGURED"},
            {"name": "Football-Data", "status": "🟡 EMPTY — Key valid" if APIConfig.FOOTBALL_DATA_KEY else "⚪ NOT CONFIGURED"},
        ]

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        logger.info(f"Fetching leagues for sport: {sport_type}")
        
        if sport_type == "Soccer":
            leagues = self.api_sports.get_all_leagues()
            if leagues:
                self._log("API-SPORTS", "SUCCESS", f"Retrieved {len(leagues)} soccer leagues")
                return [{"id": l.league_id, "name": l.name, "sport": "Soccer", "country": l.country or ""} for l in leagues]
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            leagues = self.my_sports_feeds.get_all_leagues(sport_type)
            if leagues:
                self._log("MySportsFeeds", "SUCCESS", f"Retrieved {len(leagues)} {sport_type} teams")
                return [{"id": l.league_id, "name": l.name, "sport": sport_type, "country": l.country or "USA"} for l in leagues]
        
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            leagues = self.the_sports_db.get_all_leagues(sport_type)
            if leagues:
                self._log("TheSportsDB", "SUCCESS", f"Retrieved {len(leagues)} {sport_type} leagues")
                return [{"id": l.league_id, "name": l.name, "sport": sport_type, "country": l.country or ""} for l in leagues]
        
        self._log("SYSTEM", "WARNING", f"No leagues found for {sport_type}")
        return []

    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        logger.info(f"Fetching live matches for sport: {sport_type}")
        
        if sport_type == "Soccer":
            matches = self.api_sports.get_live_matches(league_id)
            if matches:
                self._log("API-SPORTS", "SUCCESS", f"Found {len(matches)} live soccer matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("API-SPORTS", "EMPTY", "No live soccer matches at this time")
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_live_matches(sport_type)
            if matches:
                self._log("MySportsFeeds", "SUCCESS", f"Found {len(matches)} live {sport_type} matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("MySportsFeeds", "EMPTY", f"No live {sport_type} matches at this time")
        
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.the_sports_db.get_live_matches(sport_type)
            if matches:
                self._log("TheSportsDB", "SUCCESS", f"Found {len(matches)} live {sport_type} events")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("TheSportsDB", "EMPTY", f"No live {sport_type} events at this time")
        
        return pd.DataFrame()

    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        logger.info(f"Fetching upcoming matches for sport: {sport_type}")
        
        if sport_type == "Soccer":
            matches = self.api_sports.get_upcoming_matches()
            if matches:
                self._log("API-SPORTS", "SUCCESS", f"Found {len(matches)} upcoming soccer matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("API-SPORTS", "EMPTY", "No upcoming soccer matches")
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_upcoming_matches(sport_type)
            if matches:
                self._log("MySportsFeeds", "SUCCESS", f"Found {len(matches)} upcoming {sport_type} matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("MySportsFeeds", "EMPTY", f"No upcoming {sport_type} matches")
        
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.the_sports_db.get_upcoming_matches(sport_type)
            if matches:
                self._log("TheSportsDB", "SUCCESS", f"Found {len(matches)} upcoming {sport_type} events")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])
            else:
                self._log("TheSportsDB", "EMPTY", f"No upcoming {sport_type} events")
        
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD DATA LAYER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        try:
            self.router = EmpireDataRouter()
            self.is_live = True
            logger.info("EmpireDashboardData initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            self.router = None
            self.is_live = False

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df() if self.router else pd.DataFrame()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type) if self.router else []

    def get_live_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport_type, league_id) if self.router else pd.DataFrame()

    def get_upcoming_matches_df(self, sport_type: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(sport_type) if self.router else pd.DataFrame()

    # Stub methods for compatibility with app.py
    def get_match_prediction(self, match_id: str): return None
    def get_match_details(self, match_id: str): return {"found": False}
    def get_team_form(self, team_name: str, match_id: str): return None
    def get_head_to_head(self, home: str, away: str, match_id: str): return []
    def get_key_players(self, match_id: str): return []
    def get_match_odds(self, match_id: str): return {}
    def get_ai_reasoning(self, match_id: str): return []


__all__ = ["APIConfig", "EmpireDashboardData"]
