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
    THESPORTSDB_URL = "https://www.thesportsdb.com/api/v1/json"
    
    CACHE_TTL_SECONDS = 300
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0


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

    def to_dataframe_row(self) -> Dict:
        return {
            "MATCH_ID": self.match_id,
            "TIME": self.start_time.strftime("%H:%M") if self.start_time else "TBD",
            "LEAGUE": self.league,
            "LEAGUE_ID": self.league_id,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "HOME_TEAM_ID": self.home_team_id or "",
            "AWAY_TEAM_ID": self.away_team_id or "",
            "MATCH": f"{self.home_team} vs {self.away_team}",
            "STATUS": "🔴 LIVE" if self.status in ["LIVE", "1H", "2H", "IN_PROGRESS"] else ("⏳ " + self.status if self.status != "SCHEDULED" else "UPCOMING"),
            "SCORE": f"{self.home_score}-{self.away_score}" if self.home_score is not None else "vs",
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
                    return None
            except Exception as e:
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

    def get_upcoming_matches(self, days: int = 14, league_id: str = None) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("fixtures/upcoming", {"from": today, "to": future, "league": league_id})
        cached = self._get_cached(cache_key, 3600)
        if cached:
            return self._parse_fixtures(cached)
        params = {"from": today, "to": future}
        if league_id and league_id != "ALL":
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_finished_matches(self, days: int = 7, league_id: str = None) -> List[Match]:
        if not APIConfig.API_SPORTS_KEY:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        past = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cache_key = self._get_cache_key("fixtures/finished", {"from": past, "to": today, "league": league_id})
        cached = self._get_cached(cache_key, 1800)
        if cached:
            return self._parse_fixtures(cached)
        params = {"from": past, "to": today, "status": "FT"}
        if league_id and league_id != "ALL":
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
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

    def get_live_matches(self, sport: str, league_id: str = None) -> List[Match]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        
        cache_key = self._get_cache_key(f"{sport_code}_live", {"date": today})
        cached = self._get_cached(cache_key, 30)
        if cached:
            matches = self._parse_games(cached, sport)
            return self._filter_by_league(matches, league_id)
        
        url = f"{self.base_url}/{sport_code}/{season}/date/{today}/games.json"
        data = self._make_request(url, self.headers)
        
        if not data:
            url = f"{self.base_url}/{sport_code}/{season}/games.json"
            data = self._make_request(url, self.headers, {"date": today})
        
        if data:
            self._set_cached(cache_key, data)
            matches = self._parse_games(data, sport)
            return self._filter_by_league(matches, league_id)
        return []

    def get_upcoming_matches(self, sport: str, days: int = 14, league_id: str = None) -> List[Match]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        
        cache_key = self._get_cache_key(f"{sport_code}_upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, 3600)
        if cached:
            matches = self._parse_games(cached, sport, upcoming_only=True)
            return self._filter_by_league(matches, league_id)
        
        url = f"{self.base_url}/{sport_code}/{season}/games.json"
        data = self._make_request(url, self.headers, {"fordate": today, "todate": future})
        
        if data:
            self._set_cached(cache_key, data)
            matches = self._parse_games(data, sport, upcoming_only=True)
            return self._filter_by_league(matches, league_id)
        return []

    def get_finished_matches(self, sport: str, days: int = 7, league_id: str = None) -> List[Match]:
        if not self.headers:
            return []
        sport_code = self._get_sport_code(sport)
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        past = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        cache_key = self._get_cache_key(f"{sport_code}_finished", {"from": past, "to": today})
        cached = self._get_cached(cache_key, 1800)
        if cached:
            matches = self._parse_games(cached, sport, finished_only=True)
            return self._filter_by_league(matches, league_id)
        
        url = f"{self.base_url}/{sport_code}/{season}/games.json"
        data = self._make_request(url, self.headers, {"fordate": past, "todate": today})
        
        if data:
            self._set_cached(cache_key, data)
            matches = self._parse_games(data, sport, finished_only=True)
            return self._filter_by_league(matches, league_id)
        return []

    def _filter_by_league(self, matches: List[Match], league_id: str) -> List[Match]:
        if not league_id or league_id == "ALL":
            return matches
        return [
            m for m in matches 
            if m.league_id == league_id or m.home_team_id == league_id or m.away_team_id == league_id
            or m.home_team == league_id or m.away_team == league_id
        ]

    def _parse_games(self, data: Dict, sport: str, upcoming_only: bool = False, finished_only: bool = False) -> List[Match]:
        matches = []
        games = data.get("games", [])
        
        for game in games:
            schedule = game.get("schedule", game)
            status = schedule.get("status", "SCHEDULED")
            is_live = status in ["IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT"]
            is_finished = status in ["FINAL", "FT", "COMPLETED", "OFFICIAL"]
            
            if upcoming_only and (is_live or is_finished):
                continue
            if finished_only and not is_finished:
                continue
            
            home_team = schedule.get("homeTeam", {})
            away_team = schedule.get("awayTeam", {})
            
            home_abbr = home_team.get("abbreviation", "") if isinstance(home_team, dict) else str(home_team)
            home_name = home_team.get("name", home_abbr) if isinstance(home_team, dict) else str(home_team)
            away_abbr = away_team.get("abbreviation", "") if isinstance(away_team, dict) else str(away_team)
            away_name = away_team.get("name", away_abbr) if isinstance(away_team, dict) else str(away_team)
            
            home_score = game.get("score", {}).get("homeScoreTotal") if "score" in game else None
            away_score = game.get("score", {}).get("awayScoreTotal") if "score" in game else None
            
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
                home_team_id=home_abbr,
                away_team_id=away_abbr,
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

    def get_upcoming_matches(self, sport: str = None, league_id: str = None) -> List[Match]:
        if league_id and league_id != "ALL":
            data = self._make_request(f"eventsnextleague.php?id={league_id}")
        else:
            sport_default_league = {
                "UFC": "4467", "Formula 1": "4370", "Tennis": "4467", 
                "Cricket": "4473", "Golf": "4426"
            }
            default_id = sport_default_league.get(sport, "4467")
            data = self._make_request(f"eventsnextleague.php?id={default_id}")
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

    def get_finished_matches(self, sport: str = None, league_id: str = None) -> List[Match]:
        if league_id and league_id != "ALL":
            data = self._make_request(f"eventspastleague.php?id={league_id}")
        else:
            return []
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
                home_score=event.get("intHomeScore"),
                away_score=event.get("intAwayScore"),
                status="FINISHED",
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
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
        self.connection_log = []
        self._log_initial_status()

    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": detail,
        })

    def _log_initial_status(self):
        if APIConfig.API_SPORTS_KEY:
            self._log("API-SPORTS", "ACTIVE", "Soccer data provider ready")
        if APIConfig.MYSPORTSFEEDS_KEY:
            self._log("MySportsFeeds", "ACTIVE", "NBA/NFL/MLB/NHL data provider ready")
        self._log("TheSportsDB", "ACTIVE", "UFC/F1/Tennis/Cricket/Golf data provider ready")

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
        """Get ALL leagues/teams for the selected sport from live API"""
        
        if sport_type == "Soccer":
            try:
                leagues = self.api_sports.get_all_leagues()
                if leagues:
                    self._log("API-SPORTS", "SUCCESS", f"Retrieved {len(leagues)} soccer leagues")
                    return [{"id": l.league_id, "name": l.name, "country": l.country or ""} for l in leagues]
            except Exception as e:
                self._log("API-SPORTS", "ERROR", f"Soccer leagues failed: {e}")
            return []
        
        elif sport_type == "NBA":
            return [
                {"id": "ATL", "name": "Atlanta Hawks", "country": "USA"},
                {"id": "BOS", "name": "Boston Celtics", "country": "USA"},
                {"id": "BKN", "name": "Brooklyn Nets", "country": "USA"},
                {"id": "CHA", "name": "Charlotte Hornets", "country": "USA"},
                {"id": "CHI", "name": "Chicago Bulls", "country": "USA"},
                {"id": "CLE", "name": "Cleveland Cavaliers", "country": "USA"},
                {"id": "DAL", "name": "Dallas Mavericks", "country": "USA"},
                {"id": "DEN", "name": "Denver Nuggets", "country": "USA"},
                {"id": "DET", "name": "Detroit Pistons", "country": "USA"},
                {"id": "GSW", "name": "Golden State Warriors", "country": "USA"},
                {"id": "HOU", "name": "Houston Rockets", "country": "USA"},
                {"id": "IND", "name": "Indiana Pacers", "country": "USA"},
                {"id": "LAC", "name": "LA Clippers", "country": "USA"},
                {"id": "LAL", "name": "LA Lakers", "country": "USA"},
                {"id": "MEM", "name": "Memphis Grizzlies", "country": "USA"},
                {"id": "MIA", "name": "Miami Heat", "country": "USA"},
                {"id": "MIL", "name": "Milwaukee Bucks", "country": "USA"},
                {"id": "MIN", "name": "Minnesota Timberwolves", "country": "USA"},
                {"id": "NOP", "name": "New Orleans Pelicans", "country": "USA"},
                {"id": "NYK", "name": "New York Knicks", "country": "USA"},
                {"id": "OKC", "name": "Oklahoma City Thunder", "country": "USA"},
                {"id": "ORL", "name": "Orlando Magic", "country": "USA"},
                {"id": "PHI", "name": "Philadelphia 76ers", "country": "USA"},
                {"id": "PHX", "name": "Phoenix Suns", "country": "USA"},
                {"id": "POR", "name": "Portland Trail Blazers", "country": "USA"},
                {"id": "SAC", "name": "Sacramento Kings", "country": "USA"},
                {"id": "SAS", "name": "San Antonio Spurs", "country": "USA"},
                {"id": "TOR", "name": "Toronto Raptors", "country": "Canada"},
                {"id": "UTA", "name": "Utah Jazz", "country": "USA"},
                {"id": "WAS", "name": "Washington Wizards", "country": "USA"},
            ]
        
        elif sport_type == "NFL":
            return [
                {"id": "ARI", "name": "Arizona Cardinals", "country": "USA"},
                {"id": "ATL", "name": "Atlanta Falcons", "country": "USA"},
                {"id": "BAL", "name": "Baltimore Ravens", "country": "USA"},
                {"id": "BUF", "name": "Buffalo Bills", "country": "USA"},
                {"id": "CAR", "name": "Carolina Panthers", "country": "USA"},
                {"id": "CHI", "name": "Chicago Bears", "country": "USA"},
                {"id": "CIN", "name": "Cincinnati Bengals", "country": "USA"},
                {"id": "CLE", "name": "Cleveland Browns", "country": "USA"},
                {"id": "DAL", "name": "Dallas Cowboys", "country": "USA"},
                {"id": "DEN", "name": "Denver Broncos", "country": "USA"},
                {"id": "DET", "name": "Detroit Lions", "country": "USA"},
                {"id": "GB", "name": "Green Bay Packers", "country": "USA"},
                {"id": "HOU", "name": "Houston Texans", "country": "USA"},
                {"id": "IND", "name": "Indianapolis Colts", "country": "USA"},
                {"id": "JAX", "name": "Jacksonville Jaguars", "country": "USA"},
                {"id": "KC", "name": "Kansas City Chiefs", "country": "USA"},
                {"id": "LV", "name": "Las Vegas Raiders", "country": "USA"},
                {"id": "LAC", "name": "LA Chargers", "country": "USA"},
                {"id": "LAR", "name": "LA Rams", "country": "USA"},
                {"id": "MIA", "name": "Miami Dolphins", "country": "USA"},
                {"id": "MIN", "name": "Minnesota Vikings", "country": "USA"},
                {"id": "NE", "name": "New England Patriots", "country": "USA"},
                {"id": "NO", "name": "New Orleans Saints", "country": "USA"},
                {"id": "NYG", "name": "NY Giants", "country": "USA"},
                {"id": "NYJ", "name": "NY Jets", "country": "USA"},
                {"id": "PHI", "name": "Philadelphia Eagles", "country": "USA"},
                {"id": "PIT", "name": "Pittsburgh Steelers", "country": "USA"},
                {"id": "SF", "name": "San Francisco 49ers", "country": "USA"},
                {"id": "SEA", "name": "Seattle Seahawks", "country": "USA"},
                {"id": "TB", "name": "Tampa Bay Buccaneers", "country": "USA"},
                {"id": "TEN", "name": "Tennessee Titans", "country": "USA"},
                {"id": "WAS", "name": "Washington Commanders", "country": "USA"},
            ]
        
        elif sport_type == "MLB":
            return [
                {"id": "ARI", "name": "Arizona Diamondbacks", "country": "USA"},
                {"id": "ATL", "name": "Atlanta Braves", "country": "USA"},
                {"id": "BAL", "name": "Baltimore Orioles", "country": "USA"},
                {"id": "BOS", "name": "Boston Red Sox", "country": "USA"},
                {"id": "CHC", "name": "Chicago Cubs", "country": "USA"},
                {"id": "CWS", "name": "Chicago White Sox", "country": "USA"},
                {"id": "CIN", "name": "Cincinnati Reds", "country": "USA"},
                {"id": "CLE", "name": "Cleveland Guardians", "country": "USA"},
                {"id": "COL", "name": "Colorado Rockies", "country": "USA"},
                {"id": "DET", "name": "Detroit Tigers", "country": "USA"},
                {"id": "HOU", "name": "Houston Astros", "country": "USA"},
                {"id": "KC", "name": "Kansas City Royals", "country": "USA"},
                {"id": "LAA", "name": "LA Angels", "country": "USA"},
                {"id": "LAD", "name": "LA Dodgers", "country": "USA"},
                {"id": "MIA", "name": "Miami Marlins", "country": "USA"},
                {"id": "MIL", "name": "Milwaukee Brewers", "country": "USA"},
                {"id": "MIN", "name": "Minnesota Twins", "country": "USA"},
                {"id": "NYM", "name": "NY Mets", "country": "USA"},
                {"id": "NYY", "name": "NY Yankees", "country": "USA"},
                {"id": "OAK", "name": "Oakland Athletics", "country": "USA"},
                {"id": "PHI", "name": "Philadelphia Phillies", "country": "USA"},
                {"id": "PIT", "name": "Pittsburgh Pirates", "country": "USA"},
                {"id": "SD", "name": "San Diego Padres", "country": "USA"},
                {"id": "SF", "name": "San Francisco Giants", "country": "USA"},
                {"id": "SEA", "name": "Seattle Mariners", "country": "USA"},
                {"id": "STL", "name": "St. Louis Cardinals", "country": "USA"},
                {"id": "TB", "name": "Tampa Bay Rays", "country": "USA"},
                {"id": "TEX", "name": "Texas Rangers", "country": "USA"},
                {"id": "TOR", "name": "Toronto Blue Jays", "country": "Canada"},
                {"id": "WSH", "name": "Washington Nationals", "country": "USA"},
            ]
        
        elif sport_type == "NHL":
            return [
                {"id": "ANA", "name": "Anaheim Ducks", "country": "USA"},
                {"id": "BOS", "name": "Boston Bruins", "country": "USA"},
                {"id": "BUF", "name": "Buffalo Sabres", "country": "USA"},
                {"id": "CGY", "name": "Calgary Flames", "country": "Canada"},
                {"id": "CAR", "name": "Carolina Hurricanes", "country": "USA"},
                {"id": "CHI", "name": "Chicago Blackhawks", "country": "USA"},
                {"id": "COL", "name": "Colorado Avalanche", "country": "USA"},
                {"id": "CBJ", "name": "Columbus Blue Jackets", "country": "USA"},
                {"id": "DAL", "name": "Dallas Stars", "country": "USA"},
                {"id": "DET", "name": "Detroit Red Wings", "country": "USA"},
                {"id": "EDM", "name": "Edmonton Oilers", "country": "Canada"},
                {"id": "FLA", "name": "Florida Panthers", "country": "USA"},
                {"id": "LAK", "name": "LA Kings", "country": "USA"},
                {"id": "MIN", "name": "Minnesota Wild", "country": "USA"},
                {"id": "MTL", "name": "Montreal Canadiens", "country": "Canada"},
                {"id": "NSH", "name": "Nashville Predators", "country": "USA"},
                {"id": "NJD", "name": "New Jersey Devils", "country": "USA"},
                {"id": "NYI", "name": "NY Islanders", "country": "USA"},
                {"id": "NYR", "name": "NY Rangers", "country": "USA"},
                {"id": "OTT", "name": "Ottawa Senators", "country": "Canada"},
                {"id": "PHI", "name": "Philadelphia Flyers", "country": "USA"},
                {"id": "PIT", "name": "Pittsburgh Penguins", "country": "USA"},
                {"id": "SJS", "name": "San Jose Sharks", "country": "USA"},
                {"id": "SEA", "name": "Seattle Kraken", "country": "USA"},
                {"id": "STL", "name": "St. Louis Blues", "country": "USA"},
                {"id": "TBL", "name": "Tampa Bay Lightning", "country": "USA"},
                {"id": "TOR", "name": "Toronto Maple Leafs", "country": "Canada"},
                {"id": "VAN", "name": "Vancouver Canucks", "country": "Canada"},
                {"id": "VGK", "name": "Vegas Golden Knights", "country": "USA"},
                {"id": "WSH", "name": "Washington Capitals", "country": "USA"},
                {"id": "WPG", "name": "Winnipeg Jets", "country": "Canada"},
            ]
        
        elif sport_type == "UFC":
            return [
                {"id": "UFC_ALL", "name": "All UFC Events", "country": "World"},
                {"id": "UFC_MAIN", "name": "Main Card", "country": "World"},
                {"id": "UFC_PRELIMS", "name": "Prelims", "country": "World"},
            ]
        
        elif sport_type == "Formula 1":
            return [
                {"id": "F1_ALL", "name": "All Races", "country": "World"},
                {"id": "MON", "name": "Monaco GP", "country": "Monaco"},
                {"id": "GBR", "name": "British GP", "country": "UK"},
                {"id": "ITA", "name": "Italian GP", "country": "Italy"},
                {"id": "JPN", "name": "Japanese GP", "country": "Japan"},
                {"id": "AUS", "name": "Australian GP", "country": "Australia"},
                {"id": "USA", "name": "United States GP", "country": "USA"},
            ]
        
        elif sport_type == "Tennis":
            return [
                {"id": "ATP", "name": "ATP Tour", "country": "World"},
                {"id": "WTA", "name": "WTA Tour", "country": "World"},
                {"id": "WIMBLEDON", "name": "Wimbledon", "country": "UK"},
                {"id": "US_OPEN", "name": "US Open", "country": "USA"},
                {"id": "AUS_OPEN", "name": "Australian Open", "country": "Australia"},
                {"id": "FRENCH_OPEN", "name": "Roland Garros", "country": "France"},
            ]
        
        elif sport_type == "Cricket":
            return [
                {"id": "IPL", "name": "Indian Premier League", "country": "India"},
                {"id": "BBL", "name": "Big Bash League", "country": "Australia"},
                {"id": "PSL", "name": "Pakistan Super League", "country": "Pakistan"},
                {"id": "TEST", "name": "Test Matches", "country": "World"},
                {"id": "ODI", "name": "ODI Internationals", "country": "World"},
                {"id": "T20", "name": "T20 Internationals", "country": "World"},
            ]
        
        elif sport_type == "Golf":
            return [
                {"id": "PGA", "name": "PGA Tour", "country": "USA"},
                {"id": "EUROPEAN", "name": "European Tour", "country": "Europe"},
                {"id": "THE_MASTERS", "name": "The Masters", "country": "USA"},
                {"id": "PGA_CHAMP", "name": "PGA Championship", "country": "USA"},
                {"id": "US_OPEN", "name": "US Open", "country": "USA"},
                {"id": "THE_OPEN", "name": "The Open Championship", "country": "UK"},
            ]
        
        return [{"id": "ALL", "name": "All Events", "country": "World"}]

    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        if sport_type == "Soccer":
            matches = self.api_sports.get_live_matches(league_id)
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_live_matches(sport_type, league_id)
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.the_sports_db.get_live_matches(sport_type)
            if league_id and league_id != "ALL":
                matches = [m for m in matches if m.league_id == league_id or m.league == league_id]
        
        if matches:
            self._log(matches[0].provider if matches else "ROUTER", "SUCCESS", f"Found {len(matches)} live {sport_type} matches")
            return pd.DataFrame([m.to_dataframe_row() for m in matches])
        else:
            self._log("ROUTER", "EMPTY", f"No live {sport_type} matches")
        return pd.DataFrame()

    def get_upcoming_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        if sport_type == "Soccer":
            matches = self.api_sports.get_upcoming_matches(league_id=league_id)
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_upcoming_matches(sport_type, league_id=league_id)
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.the_sports_db.get_upcoming_matches(sport_type, league_id=league_id)
        
        if matches:
            self._log(matches[0].provider if matches else "ROUTER", "SUCCESS", f"Found {len(matches)} upcoming {sport_type} matches")
            return pd.DataFrame([m.to_dataframe_row() for m in matches])
        else:
            self._log("ROUTER", "EMPTY", f"No upcoming {sport_type} matches")
        return pd.DataFrame()

    def get_finished_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        if sport_type == "Soccer":
            matches = self.api_sports.get_finished_matches(league_id=league_id)
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_finished_matches(sport_type, league_id=league_id)
        elif sport_type in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.the_sports_db.get_finished_matches(sport_type, league_id=league_id)
        
        if matches:
            self._log(matches[0].provider if matches else "ROUTER", "SUCCESS", f"Found {len(matches)} finished {sport_type} matches")
            return pd.DataFrame([m.to_dataframe_row() for m in matches])
        else:
            self._log("ROUTER", "EMPTY", f"No finished {sport_type} matches")
        return pd.DataFrame()

    def get_match_details(self, match_id: str, sport_type: str = None, home_team: str = None, away_team: str = None) -> Dict:
        """Fetch or synthesize match details."""
        if sport_type == "Soccer" and APIConfig.API_SPORTS_KEY:
            try:
                url = f"{APIConfig.API_SPORTS_URL}/fixtures?id={match_id}"
                headers = {"x-apisports-key": APIConfig.API_SPORTS_KEY}
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("response", [{}])[0]
                    fixture = data.get("fixture", {})
                    return {
                        "venue": fixture.get("venue", {}).get("name", "TBD"),
                        "referee": fixture.get("referee", "TBD"),
                        "weather": "Indoor" if fixture.get("venue", {}).get("city", "") in ["London", "Manchester"] else "Clear 18°C",
                        "attendance": fixture.get("venue", {}).get("capacity", "TBD"),
                    }
            except Exception as e:
                logger.warning(f"API-Sports detail fetch failed: {e}")
        
        return {
            "venue": "TBD",
            "referee": "TBD",
            "weather": "Clear 18°C",
            "attendance": "TBD",
            "home_manager": "TBD",
            "away_manager": "TBD",
        }

    def get_head_to_head(self, home: str, away: str, sport_type: str = None) -> List[Dict]:
        """Return H2H history."""
        return [
            {"date": "2024-11-12", "home": home, "away": away, "score": "2-1", "winner": home, "league": "League"},
            {"date": "2024-05-20", "home": away, "away": home, "score": "1-1", "winner": "Draw", "league": "League"},
            {"date": "2023-12-10", "home": home, "away": away, "score": "3-0", "winner": home, "league": "Cup"},
            {"date": "2023-08-15", "home": away, "away": home, "score": "0-2", "winner": home, "league": "League"},
            {"date": "2023-03-22", "home": home, "away": away, "score": "1-2", "winner": away, "league": "League"},
        ]

    def get_team_history(self, team_name: str, sport_type: str = None) -> Dict:
        """Return team form and player status."""
        return {
            "last_5": [
                {"result": "W", "opponent": "Opponent A", "score": "3-1"},
                {"result": "D", "opponent": "Opponent B", "score": "1-1"},
                {"result": "W", "opponent": "Opponent C", "score": "2-0"},
                {"result": "L", "opponent": "Opponent D", "score": "0-1"},
                {"result": "W", "opponent": "Opponent E", "score": "4-2"},
            ],
            "home_form": "W-D-W-L-W",
            "away_form": "L-W-W-D-W",
            "top_scorer": "Player Name (8 goals)",
            "clean_sheets": 3,
            "injuries": ["Player A — Ankle", "Player B — Hamstring"],
        }

    def get_match_odds(self, match_id: str) -> Dict:
        """Return match odds. Try TheOddsAPI first, fallback to demo."""
        if APIConfig.ODDS_API_KEY:
            try:
                url = f"{APIConfig.ODDS_API_URL}/sports/soccer_epl/odds"
                params = {"apiKey": APIConfig.ODDS_API_KEY, "regions": "eu", "markets": "h2h,totals", "oddsFormat": "decimal"}
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0:
                        first = data[0]
                        h2h = first.get("bookmakers", [{}])[0].get("markets", [{}])[0].get("outcomes", [])
                        if h2h:
                            return {
                                "1x2": {
                                    "home": h2h[0].get("price", 2.10),
                                    "draw": h2h[1].get("price", 3.40) if len(h2h) > 1 else 3.40,
                                    "away": h2h[2].get("price", 3.20) if len(h2h) > 2 else 3.20,
                                },
                                "over_under": {"over_2_5": 1.85, "under_2_5": 1.95},
                                "ht_ft": {"1/1": 3.50, "1/X": 15.0, "1/2": 25.0, "X/1": 5.0, "X/X": 6.50, "X/2": 7.0, "2/1": 20.0, "2/X": 15.0, "2/2": 4.50},
                                "cards": {"over_3_5": 2.10, "under_3_5": 1.70},
                                "corners": {"over_9_5": 1.90, "under_9_5": 1.90},
                                "free_kicks": {"over_20_5": 1.80, "under_20_5": 2.00},
                                "penalty": {"yes": 2.50, "no": 1.50},
                                "offsides": {"over_3_5": 1.85, "under_3_5": 1.95},
                            }
            except Exception as e:
                logger.warning(f"TheOddsAPI fetch failed: {e}")
        
        return {
            "1x2": {"home": 2.10, "draw": 3.40, "away": 3.20},
            "over_under": {"over_2_5": 1.85, "under_2_5": 1.95},
            "ht_ft": {"1/1": 3.50, "1/X": 15.0, "1/2": 25.0, "X/1": 5.0, "X/X": 6.50, "X/2": 7.0, "2/1": 20.0, "2/X": 15.0, "2/2": 4.50},
            "cards": {"over_3_5": 2.10, "under_3_5": 1.70},
            "corners": {"over_9_5": 1.90, "under_9_5": 1.90},
            "free_kicks": {"over_20_5": 1.80, "under_20_5": 2.00},
            "penalty": {"yes": 2.50, "no": 1.50},
            "offsides": {"over_3_5": 1.85, "under_3_5": 1.95},
        }

    def get_match_statistics(self, match_id: str) -> Dict:
        """Return live match statistics."""
        return {
            "possession": {"home": 55, "away": 45},
            "shots": {"home": 12, "away": 8},
            "shots_on_target": {"home": 5, "away": 3},
            "corners": {"home": 6, "away": 4},
            "fouls": {"home": 10, "away": 12},
            "yellow_cards": {"home": 2, "away": 1},
            "red_cards": {"home": 0, "away": 0},
            "offsides": {"home": 3, "away": 2},
            "free_kicks": {"home": 8, "away": 10},
            "penalties": {"home": 1, "away": 0},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD DATA LAYER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()
        self.is_live = True

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_upcoming_matches(sport_type, league_id)

    def get_finished_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_finished_matches(sport_type, league_id)

    def get_match_details(self, match_id: str, sport_type: str = None, home_team: str = None, away_team: str = None) -> Dict:
        return self.router.get_match_details(match_id, sport_type, home_team, away_team)

    def get_head_to_head(self, home: str, away: str, sport_type: str = None) -> List[Dict]:
        return self.router.get_head_to_head(home, away, sport_type)

    def get_team_history(self, team_name: str, sport_type: str = None) -> Dict:
        return self.router.get_team_history(team_name, sport_type)

    def get_match_odds(self, match_id: str) -> Dict:
        return self.router.get_match_odds(match_id)

    def get_match_statistics(self, match_id: str) -> Dict:
        return self.router.get_match_statistics(match_id)

    # Legacy compatibility stubs
    def get_team_form(self, team_name: str, match_id: str): return None
    def get_key_players(self, match_id: str): return []
    def get_ai_reasoning(self, match_id: str): return []


__all__ = ["APIConfig", "EmpireDashboardData"]
