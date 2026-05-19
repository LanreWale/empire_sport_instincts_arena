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

logger.info(f"API Keys: API-SPORTS={'✓' if API_SPORTS_KEY else '✗'} OddsAPI={'✓' if ODDS_API_KEY else '✗'} Sportmonks={'✓' if SPORTMONKS_KEY else '✗'} MySportsFeeds={'✓' if MYSPORTSFEEDS_KEY else '✗'}")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
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
    CACHE_TTL = 30
    REQUEST_TIMEOUT = 10

    @staticmethod
    def safe_float(val, default=0.0):
        try:
            return float(val) if val not in [None, "", "-"] else default
        except:
            return default


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
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None

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
            "STATUS": "🔴 LIVE" if self.status in ["LIVE", "IN_PLAY", "1H", "2H"] else self.status,
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
# API-SPORTS PROVIDER (Soccer)
# ════════════════════════════════════════════════════════════════════════════════

class APISportsProvider:
    def __init__(self):
        self.name = "API-SPORTS"
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers = {"x-rapidapi-key": APIConfig.API_SPORTS_KEY, "x-rapidapi-host": "v3.football.api-sports.io"}
        self.cache = {}

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not APIConfig.API_SPORTS_KEY:
            return None
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL:
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
                sport="Soccer",
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
            ))
        return matches

    def get_team_form(self, team_id: str) -> Optional[Dict]:
        data = self._request("fixtures", {"team": team_id, "last": 5})
        if not data:
            return None
        results = []
        goals_scored = 0
        goals_conceded = 0
        for fixture in data.get("response", []):
            goals = fixture.get("goals", {})
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            if str(fixture.get("teams", {}).get("home", {}).get("id")) == team_id:
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
        return {"form": results, "goals_scored": goals_scored, "goals_conceded": goals_conceded}

    def get_h2h(self, team1_id: str, team2_id: str) -> List[Dict]:
        data = self._request("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}"})
        if not data:
            return []
        results = []
        for fixture in data.get("response", [])[:5]:
            f = fixture.get("fixture", {})
            goals = fixture.get("goals", {})
            league = fixture.get("league", {})
            results.append({
                "date": f.get("date", "")[:10] if f.get("date") else "N/A",
                "score": f"{goals.get('home', 0)}-{goals.get('away', 0)}",
                "competition": league.get("name", "Unknown")
            })
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER (NBA, NFL, MLB, NHL)
# ════════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider:
    def __init__(self):
        self.name = "MySportsFeeds"
        self.base_url = APIConfig.MYSPORTSFEEDS_URL
        self.cache = {}
        if APIConfig.MYSPORTSFEEDS_KEY and APIConfig.MYSPORTSFEEDS_PASSWORD:
            credentials = base64.b64encode(f"{APIConfig.MYSPORTSFEEDS_KEY}:{APIConfig.MYSPORTSFEEDS_PASSWORD}".encode()).decode()
            self.headers = {"Authorization": f"Basic {credentials}"}
        else:
            self.headers = {}

    def _request(self, sport: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not self.headers:
            return None
        cache_key = f"{sport}:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL:
                return data
        try:
            url = f"{self.base_url}/{sport}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=APIConfig.REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.cache[cache_key] = (response.json(), time.time())
                return response.json()
        except Exception as e:
            logger.error(f"MySportsFeeds error: {e}")
        return None

    def get_live_matches(self, sport: str) -> List[Match]:
        sport_map = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}
        sport_key = sport_map.get(sport, "nba")
        data = self._request(sport_key, "current/games.json", {"date": datetime.now().strftime("%Y%m%d")})
        if not data:
            return []
        matches = []
        for game in data.get("games", []):
            schedule = game.get("schedule", {})
            home = schedule.get("homeTeam", {})
            away = schedule.get("awayTeam", {})
            status = schedule.get("status", "SCHEDULED")
            matches.append(Match(
                match_id=str(schedule.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id="",
                home_team=home.get("name", "Home"),
                away_team=away.get("name", "Away"),
                home_score=game.get("score", {}).get("homeScoreTotal"),
                away_score=game.get("score", {}).get("awayScoreTotal"),
                status="LIVE" if status == "IN_PROGRESS" else status,
            ))
        return matches

    def get_upcoming_matches(self, sport: str, days: int = 7) -> List[Match]:
        sport_map = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}
        sport_key = sport_map.get(sport, "nba")
        data = self._request(sport_key, "current/games.json", {"date": datetime.now().strftime("%Y%m%d")})
        if not data:
            return []
        matches = []
        for game in data.get("games", []):
            schedule = game.get("schedule", {})
            if schedule.get("status") != "IN_PROGRESS":
                matches.append(Match(
                    match_id=str(schedule.get("id", "")),
                    provider="MySportsFeeds",
                    league=sport,
                    league_id="",
                    home_team=schedule.get("homeTeam", {}).get("name", "Home"),
                    away_team=schedule.get("awayTeam", {}).get("name", "Away"),
                ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER (All Sports)
# ════════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider:
    def __init__(self):
        self.name = "TheSportsDB"
        self.base_url = APIConfig.THESPORTSDB_URL
        self.cache = {}

    def _request(self, endpoint: str) -> Optional[Dict]:
        cache_key = endpoint
        if cache_key in self.cache:
            data, ts = self.cache[cache_key]
            if time.time() - ts < APIConfig.CACHE_TTL:
                return data
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, timeout=APIConfig.REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.cache[cache_key] = (response.json(), time.time())
                return response.json()
        except Exception as e:
            logger.error(f"TheSportsDB error: {e}")
        return None

    def get_all_leagues(self) -> List[League]:
        data = self._request("all/leagues")
        if not data:
            return []
        leagues = []
        for league in data.get("leagues", []):
            leagues.append(League(
                league_id=str(league.get("idLeague", "")),
                name=league.get("strLeague", "Unknown"),
                sport=league.get("strSport", "Unknown"),
                country=league.get("strCountry", "")
            ))
        return leagues

    def get_live_matches(self) -> List[Match]:
        data = self._request("livescore/all")
        if not data:
            return []
        matches = []
        for event in data.get("events", []):
            is_live = event.get("strStatus") in ["1H", "2H", "HT", "IN_PLAY"]
            matches.append(Match(
                match_id=str(event.get("idEvent", "")),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=str(event.get("idLeague", "")),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                home_score=event.get("intHomeScore"),
                away_score=event.get("intAwayScore"),
                status="LIVE" if is_live else event.get("strStatus", "SCHEDULED"),
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

    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": detail,
            "HTTP": None,
            "MATCHES": None
        })
        if len(self.connection_log) > 100:
            self.connection_log = self.connection_log[-100:]

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame(columns=["TIME", "PROVIDER", "STATUS", "DETAIL"])
        return pd.DataFrame(self.connection_log)

    def get_provider_status(self, sport_type: str = "Soccer") -> List[Dict]:
        statuses = []
        
        # API-SPORTS (Soccer)
        if sport_type == "Soccer":
            try:
                matches = self.api_sports.get_live_matches()
                if matches and len(matches) > 0:
                    statuses.append({"name": "API-SPORTS", "status": "🟢 ONLINE — Connected", "matches": len(matches)})
                elif APIConfig.API_SPORTS_KEY:
                    statuses.append({"name": "API-SPORTS", "status": "🟡 EMPTY — Key valid but no matches today"})
                else:
                    statuses.append({"name": "API-SPORTS", "status": "⚪ NOT CONFIGURED"})
            except Exception as e:
                statuses.append({"name": "API-SPORTS", "status": f"🔴 OFFLINE — {str(e)[:30]}"})
            
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
        
        # MySportsFeeds (NBA, NFL, MLB, NHL)
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            try:
                matches = self.my_sports_feeds.get_live_matches(sport_type)
                if matches and len(matches) > 0:
                    statuses.append({"name": "MySportsFeeds", "status": "🟢 ONLINE — Connected", "matches": len(matches)})
                elif APIConfig.MYSPORTSFEEDS_KEY:
                    statuses.append({"name": "MySportsFeeds", "status": "🟡 EMPTY — Key valid but no matches today"})
                else:
                    statuses.append({"name": "MySportsFeeds", "status": "⚪ NOT CONFIGURED"})
            except Exception as e:
                statuses.append({"name": "MySportsFeeds", "status": f"🔴 OFFLINE — {str(e)[:30]}"})
        
        # TheSportsDB (All sports fallback)
        try:
            matches = self.the_sports_db.get_live_matches()
            if matches and len(matches) > 0:
                statuses.append({"name": "TheSportsDB", "status": "🟢 ONLINE — Connected", "matches": len(matches)})
            else:
                statuses.append({"name": "TheSportsDB", "status": "🟡 EMPTY — No live matches"})
        except Exception as e:
            statuses.append({"name": "TheSportsDB", "status": f"🔴 OFFLINE — {str(e)[:30]}"})
        
        return statuses

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        """Get all leagues for a given sport"""
        if sport_type == "Soccer":
            leagues = self.api_sports.get_all_leagues()
            if leagues:
                self._log("API-SPORTS", "SUCCESS", f"Retrieved {len(leagues)} soccer leagues")
                return [{"id": l.league_id, "name": l.name, "country": l.country or ""} for l in leagues]
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            # Return league structure for US sports
            leagues = [
                {"id": sport_type, "name": sport_type.upper(), "country": "USA"},
                {"id": f"{sport_type}_EAST", "name": f"{sport_type} East Conference", "country": "USA"},
                {"id": f"{sport_type}_WEST", "name": f"{sport_type} West Conference", "country": "USA"},
            ]
            return leagues
        
        else:
            # Try TheSportsDB for other sports
            leagues = self.the_sports_db.get_all_leagues()
            if leagues:
                return [{"id": l.league_id, "name": l.name, "country": l.country or ""} for l in leagues[:50]]
        
        return [{"id": "ALL", "name": "All Leagues", "country": ""}]

    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        all_matches = []
        
        if sport_type == "Soccer":
            matches = self.api_sports.get_live_matches(league_id if league_id != "ALL" else None)
            if matches:
                all_matches.extend(matches)
                self._log("API-SPORTS", "SUCCESS", f"Found {len(matches)} live soccer matches")
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_live_matches(sport_type)
            if matches:
                all_matches.extend(matches)
                self._log("MySportsFeeds", "SUCCESS", f"Found {len(matches)} live {sport_type} matches")
        
        # TheSportsDB fallback
        if not all_matches:
            matches = self.the_sports_db.get_live_matches()
            if matches:
                all_matches.extend(matches)
                self._log("TheSportsDB", "SUCCESS", f"Found {len(matches)} live matches")
        
        if not all_matches:
            return pd.DataFrame()
        
        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        all_matches = []
        
        if sport_type == "Soccer":
            matches = self.api_sports.get_upcoming_matches()
            if matches:
                all_matches.extend(matches)
        
        elif sport_type in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.my_sports_feeds.get_upcoming_matches(sport_type)
            if matches:
                all_matches.extend(matches)
        
        if not all_matches:
            return pd.DataFrame()
        
        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def _find_match_by_id(self, match_id: str):
        """Find a match by ID across all providers"""
        # Try soccer
        matches = self.api_sports.get_live_matches()
        for m in matches:
            if m.match_id == match_id:
                return m
        return None

    def get_match_details(self, match_id: str) -> Dict:
        match = self._find_match_by_id(match_id)
        if match:
            return {"found": True, "match": match.to_dict(), "h2h": [], "players": [], "odds": {}}
        return {"found": False}

    def get_match_prediction(self, match_id: str):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DASHBOARD DATA LAYER
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()
        self.is_live = True

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        """sport_type can be 'Soccer', 'NBA', 'NFL', 'MLB', 'NHL', etc."""
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport_config=None, league_id: str = None) -> pd.DataFrame:
        if sport_config and isinstance(sport_config, dict):
            sport_type = sport_config.get("sport_type", "Soccer")
        else:
            sport_type = "Soccer"
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_config=None) -> pd.DataFrame:
        if sport_config and isinstance(sport_config, dict):
            sport_type = sport_config.get("sport_type", "Soccer")
        else:
            sport_type = "Soccer"
        return self.router.get_upcoming_matches(sport_type)

    def get_match_prediction(self, match_id: str):
        return self.router.get_match_prediction(match_id)

    def get_match_details(self, match_id: str) -> Dict:
        return self.router.get_match_details(match_id)

    def get_team_form(self, team_name: str, match_id: str) -> Optional[Dict]:
        match = self.router._find_match_by_id(match_id)
        if match and match.home_team_id:
            return self.router.api_sports.get_team_form(match.home_team_id)
        return None

    def get_head_to_head(self, home: str, away: str, match_id: str) -> List[Dict]:
        match = self.router._find_match_by_id(match_id)
        if match and match.home_team_id and match.away_team_id:
            return self.router.api_sports.get_h2h(match.home_team_id, match.away_team_id)
        return []

    def get_key_players(self, match_id: str) -> List[Dict]:
        return []

    def get_match_odds(self, match_id: str) -> Dict:
        return {}

    def get_ai_reasoning(self, match_id: str) -> List[str]:
        return []


__all__ = ["APIConfig", "EmpireDashboardData"]
