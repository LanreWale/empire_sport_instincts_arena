"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer (World-Class Multi-Sport v4.0)
Supports all 10 sports with live keys + feature engineering hooks
"""

import os
import time
import hashlib
import base64
import requests
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import pandas as pd

# Add ARENA_FORGE to path for feature imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ARENA_FORGE'))

from empire_ai_engine import EmpireAIEngine
from football_features import FootballFeatureEngineer
from nba_features import NBAFeatureEngineer
from nfl_features import NFLFeatureEngineer
from tennis_features import TennisFeatureEngineer

load_dotenv()
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
class APIConfig:
    @staticmethod
    def _e(k, d=""): return str(os.getenv(k, d)).strip()

    # API Keys
    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"
    
    FOOTBALL_DATA_KEY = _e("FOOTBALL_DATA_KEY")
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    
    TSDB_KEY          = _e("TheSportDB_API_key", "3")
    TSDB_URL          = "https://www.thesportsdb.com/api/v1/json"
    
    MSF_KEY           = _e("MYSPORTSFEEDS_KEY")
    MSF_PASS          = _e("MYSPORTSFEEDS_PASSWORD")
    MSF_URL           = "https://api.mysportsfeeds.com/v2.1/pull"
    
    APIFY_KEY         = _e("APIFY_API_KEY")

    # Cache TTLs
    TTL_LIVE     = 60
    TTL_UPCOMING = 900
    TTL_LEAGUES  = 86400
    TIMEOUT      = 12
    RETRIES      = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LISTS (Zero API calls - always available)
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Football": [
        {"id": "39",  "name": "Premier League",           "country": "England"},
        {"id": "140", "name": "La Liga",                  "country": "Spain"},
        {"id": "135", "name": "Serie A",                  "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",               "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                  "country": "France"},
        {"id": "2",   "name": "UEFA Champions League",    "country": "Europe"},
        {"id": "1",   "name": "FIFA World Cup",           "country": "World"},
        {"id": "10",  "name": "Friendlies International", "country": "World"},
    ],
    "NBA": [
        {"id": "NBA",  "name": "NBA",                     "country": "USA"},
        {"id": "WNBA", "name": "WNBA",                    "country": "USA"},
    ],
    "NFL": [
        {"id": "NFL",  "name": "NFL",                     "country": "USA"},
    ],
    "MLB": [
        {"id": "MLB",  "name": "MLB",                     "country": "USA/Canada"},
    ],
    "NHL": [
        {"id": "NHL",  "name": "NHL",                     "country": "USA/Canada"},
    ],
    "UFC": [
        {"id": "UFC_ALL", "name": "UFC",                  "country": "World"},
    ],
    "Formula 1": [
        {"id": "F1_ALL",   "name": "Formula 1",           "country": "World"},
    ],
    "Tennis": [
        {"id": "ATP_ALL",  "name": "ATP Tour",            "country": "World"},
        {"id": "WTA_ALL",  "name": "WTA Tour",            "country": "World"},
    ],
    "Cricket": [
        {"id": "ICC_WC",   "name": "World Cup",           "country": "World"},
        {"id": "IPL",      "name": "IPL",                 "country": "India"},
    ],
    "Golf": [
        {"id": "PGA_ALL",  "name": "PGA Tour",            "country": "USA"},
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
    home_score:   Optional[int]      = None
    away_score:   Optional[int]      = None
    status:       str                = "SCHEDULED"
    minute:       Optional[int]      = None
    start_time:   Optional[datetime] = None
    venue:        Optional[str]      = None
    country:      Optional[str]      = None

    def to_dataframe_row(self) -> Dict:
        su = self.status.upper()
        is_live = any(x in su for x in ["LIVE", "1H", "2H", "HT", "IN_PLAY"])
        is_done = any(x in su for x in ["FINISH", "FT", "FINAL", "COMPLETED"])
        if is_live:
            disp = "🔴 LIVE"
        elif is_done:
            disp = "✅ FINISHED"
        else:
            disp = "⏳ UPCOMING"
        t = ""
        if self.start_time:
            try:
                t = self.start_time.strftime("%d %b %H:%M")
            except:
                t = str(self.start_time)[:16]
        return {
            "MATCH_ID":  self.match_id,
            "TIME":      t or "TBD",
            "LEAGUE":    self.league,
            "LEAGUE_ID": self.league_id,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "MATCH":     f"{self.home_team} vs {self.away_team}",
            "STATUS":    disp,
            "SCORE":     f"{self.home_score}-{self.away_score}"
                         if self.home_score is not None else "vs",
            "PROVIDER":  self.provider,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════
class DataProvider:
    def __init__(self, name: str):
        self.name = name
        self._cache: Dict[str, Any] = {}

    def _req(self, url: str, headers: Dict = None, params: Dict = None, auth=None) -> Optional[Any]:
        for attempt in range(APIConfig.RETRIES):
            try:
                r = requests.get(url, headers=headers or {}, params=params or {},
                                 auth=auth, timeout=APIConfig.TIMEOUT)
                if r.status_code == 429:
                    time.sleep((attempt + 1) * 2)
                    continue
                if r.status_code == 200:
                    return r.json()
                logger.warning(f"[{self.name}] HTTP {r.status_code}")
                return None
            except Exception as e:
                logger.error(f"[{self.name}] {e}")
            time.sleep(0.5 * (attempt + 1))
        return None

    def _ck(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get(self, key: str, ttl: int) -> Optional[Any]:
        e = self._cache.get(key)
        return e["v"] if e and time.time() - e["t"] < ttl else None

    def _set(self, key: str, val: Any):
        self._cache[key] = {"v": val, "t": time.time()}

    def clear(self):
        self._cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS PROVIDER (Football - 100 requests/day)
# ═══════════════════════════════════════════════════════════════════════════════
class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.api_key = APIConfig.API_SPORTS_KEY
        self.headers = {"x-apisports-key": self.api_key} if self.api_key else {}
        self.request_count = 0
        self.last_reset = datetime.now()

    @property
    def ok(self):
        return bool(self.api_key)

    def _check_limit(self):
        now = datetime.now()
        if now.day != self.last_reset.day:
            self.request_count = 0
            self.last_reset = now
        return self.request_count < 100

    def get_remaining(self) -> int:
        now = datetime.now()
        if now.day != self.last_reset.day:
            return 100
        return max(0, 100 - self.request_count)

    def get_live_matches(self) -> List[Match]:
        if not self.ok or not self._check_limit():
            return []
        self.request_count += 1
        response = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.headers, {"live": "all"})
        return self._parse_response(response) if response else []

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        if not self.ok or not self._check_limit():
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        self.request_count += 1
        response = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.headers,
                              {"from": today, "to": future})
        return self._parse_response(response) if response else []

    def _parse_response(self, data: Dict) -> List[Match]:
        matches = []
        for fixture in data.get("response", []):
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            status = f.get("status", {})
            
            start = None
            if f.get("date"):
                try:
                    start = datetime.fromisoformat(f["date"].replace("Z", "+00:00"))
                except:
                    pass
            
            status_short = status.get("short", "NS")
            if status_short == "LIVE":
                match_status = "LIVE"
            elif status_short in ["FT", "AET", "PEN"]:
                match_status = "FINISHED"
            else:
                match_status = "SCHEDULED"
            
            matches.append(Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=league.get("name", "Unknown"),
                league_id=str(league.get("id", "")),
                home_team=teams.get("home", {}).get("name", "Home"),
                away_team=teams.get("away", {}).get("name", "Away"),
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                status=match_status,
                minute=status.get("elapsed"),
                start_time=start,
                country=league.get("country", ""),
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA PROVIDER (Backup - No daily limit)
# ═══════════════════════════════════════════════════════════════════════════════
class FootballDataProvider(DataProvider):
    def __init__(self):
        super().__init__("Football-Data")
        self.headers = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY} if APIConfig.FOOTBALL_DATA_KEY else {}
        self.request_timestamps = []

    @property
    def ok(self):
        return True

    def _check_rate_limit(self):
        now = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        if len(self.request_timestamps) >= 10:
            return False
        self.request_timestamps.append(now)
        return True

    def get_today_matches(self) -> List[Match]:
        if not self._check_rate_limit():
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        response = self._req(f"{APIConfig.FOOTBALL_DATA_URL}/matches", self.headers,
                              {"dateFrom": today, "dateTo": today})
        return self._parse_response(response) if response else []

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        if not self._check_rate_limit():
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        response = self._req(f"{APIConfig.FOOTBALL_DATA_URL}/matches", self.headers,
                              {"dateFrom": today, "dateTo": future})
        return self._parse_response(response) if response else []

    def _parse_response(self, data: Dict) -> List[Match]:
        matches = []
        for match in data.get("matches", []):
            comp = match.get("competition", {})
            home = match.get("homeTeam", {})
            away = match.get("awayTeam", {})
            score = match.get("score", {}).get("fullTime", {})
            
            start = None
            if match.get("utcDate"):
                try:
                    start = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
                except:
                    pass
            
            raw_status = match.get("status", "SCHEDULED").upper()
            if "IN_PLAY" in raw_status or "PAUSED" in raw_status:
                status = "LIVE"
            elif "FINISHED" in raw_status:
                status = "FINISHED"
            else:
                status = "SCHEDULED"
            
            matches.append(Match(
                match_id=str(match.get("id", "")),
                provider="Football-Data",
                league=comp.get("name", "Unknown"),
                league_id=str(comp.get("id", "")),
                home_team=home.get("name", "Home"),
                away_team=away.get("name", "Away"),
                home_score=score.get("home"),
                away_score=score.get("away"),
                status=status,
                start_time=start,
                country=comp.get("area", {}).get("name", ""),
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER (NBA, NFL, MLB, NHL)
# ═══════════════════════════════════════════════════════════════════════════════
class MySportsFeedsProvider(DataProvider):
    SPORT_MAP = {
        "NBA": "nba",
        "NFL": "nfl",
        "MLB": "mlb",
        "NHL": "nhl",
    }

    def __init__(self):
        super().__init__("MySportsFeeds")
        self.key = APIConfig.MSF_KEY
        self.password = APIConfig.MSF_PASS
        self.auth = (self.key, self.password) if self.key and self.password else None

    @property
    def ok(self):
        return bool(self.auth)

    def _get_season(self, sport: str) -> str:
        now = datetime.now()
        s = sport.upper()
        if s in ("NBA", "NHL"):
            return f"{now.year}-{now.year + 1}" if now.month >= 10 else f"{now.year - 1}-{now.year}"
        if s == "NFL":
            return str(now.year) if now.month >= 8 else str(now.year - 1)
        return str(now.year)

    def get_upcoming_matches(self, sport: str, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        code = self.SPORT_MAP.get(sport, "nba")
        season = self._get_season(sport)
        today = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        
        url = f"{APIConfig.MSF_URL}/{code}/{season}/games.json"
        params = {"fordate": today, "todate": future}
        response = self._req(url, params=params, auth=self.auth)
        return self._parse_response(response, sport) if response else []

    def _parse_response(self, data: Dict, sport: str) -> List[Match]:
        matches = []
        for game in data.get("games", []):
            sc = game.get("schedule", game)
            raw = sc.get("playedStatus", sc.get("status", "UNPLAYED")).upper()
            live = raw in ("IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT")
            done = raw in ("COMPLETED", "FINAL")
            
            home = sc.get("homeTeam", {})
            away = sc.get("awayTeam", {})
            home_name = f"{home.get('city', '')} {home.get('name', '')}".strip() or "Home"
            away_name = f"{away.get('city', '')} {away.get('name', '')}".strip() or "Away"
            
            score = game.get("score", {})
            start = None
            if sc.get("startTime"):
                try:
                    start = datetime.fromisoformat(sc["startTime"].replace("Z", "+00:00"))
                except:
                    pass
            
            matches.append(Match(
                match_id=str(sc.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home_name,
                away_team=away_name,
                home_score=score.get("homeScoreTotal"),
                away_score=score.get("awayScoreTotal"),
                status="LIVE" if live else ("FINISHED" if done else "SCHEDULED"),
                start_time=start,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER (UFC, F1, Tennis, Cricket, Golf - Completely Free)
# ═══════════════════════════════════════════════════════════════════════════════
class TheSportsDBProvider(DataProvider):
    SPORT_IDS = {
        "UFC": "4467",
        "Formula 1": "4370",
        "Tennis": "4424",
        "Cricket": "4722",
        "Golf": "4426",
    }

    def __init__(self):
        super().__init__("TheSportsDB")
        self.key = APIConfig.TSDB_KEY or "3"

    @property
    def ok(self):
        return True

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        league_id = self.SPORT_IDS.get(sport)
        if not league_id:
            return []
        url = f"{APIConfig.TSDB_URL}/{self.key}/eventsnextleague.php?id={league_id}"
        response = self._req(url)
        return self._parse_response(response, sport) if response else []

    def _parse_response(self, data: Dict, sport: str) -> List[Match]:
        matches = []
        for event in data.get("events", []):
            start = None
            if event.get("dateEvent"):
                try:
                    ts = (event.get("strTime") or "00:00:00")[:5]
                    start = datetime.strptime(f"{event['dateEvent']} {ts}", "%Y-%m-%d %H:%M")
                except:
                    pass
            
            matches.append(Match(
                match_id=event.get("idEvent", ""),
                provider="TheSportsDB",
                league=event.get("strLeague", sport),
                league_id=event.get("idLeague", ""),
                home_team=event.get("strHomeTeam", "TBD"),
                away_team=event.get("strAwayTeam", "TBD"),
                status="SCHEDULED",
                start_time=start,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER (Complete Multi-Sport Implementation)
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        # Football/Soccer Providers
        self.football_data = FootballDataProvider()
        self.api_sports = APISportsProvider()
        
        # US Sports Provider
        self.msf = MySportsFeedsProvider()
        
        # Other Sports Provider (Free)
        self.tsdb = TheSportsDBProvider()
        
        # Feature Engineers
        self.football_fe = FootballFeatureEngineer()
        self.nba_fe = NBAFeatureEngineer()
        self.nfl_fe = NFLFeatureEngineer()
        self.tennis_fe = TennisFeatureEngineer()
        
        self.log: List[Dict] = []
        self._log_startup()

    def _log(self, provider, status, detail):
        self.log.append({
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": str(detail)[:80]
        })

    def _log_startup(self):
        self._log("Football-Data", "READY", "Football backup - No daily limit")
        self._log("API-SPORTS", "READY" if self.api_sports.ok else "NO KEY", f"{self.api_sports.get_remaining()}/100 daily")
        self._log("MySportsFeeds", "READY" if self.msf.ok else "NO KEY", "NBA/NFL/MLB/NHL")
        self._log("TheSportsDB", "READY", "UFC/F1/Tennis/Cricket/Golf - Free unlimited")

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "Football-Data", "status": "🟢 ONLINE"},
            {"name": "API-SPORTS", "status": f"🟢 {self.api_sports.get_remaining()}/100 remaining" if self.api_sports.ok else "⚪ Add API_SPORTS_KEY"},
            {"name": "MySportsFeeds", "status": "🟢 ONLINE" if self.msf.ok else "⚪ Add MYSPORTSFEEDS_KEY"},
            {"name": "TheSportsDB", "status": "🟢 ONLINE"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-50:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        return STATIC_LEAGUES.get(sport, [{"id": "ALL", "name": "All Events", "country": "World"}])

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        try:
            if sport == "Football":
                matches = self.api_sports.get_live_matches()
                if not matches:
                    fd_matches = self.football_data.get_today_matches()
                    matches = [m for m in fd_matches if m.status == "LIVE"]
            elif sport in ["NBA", "NFL", "MLB", "NHL"]:
                matches = self.msf.get_upcoming_matches(sport, days=1)
                matches = [m for m in matches if m.status == "LIVE"]
            elif sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
                matches = self.tsdb.get_upcoming_matches(sport)
                matches = [m for m in matches if m.status == "LIVE"]
            
            self._log(sport, "SUCCESS" if matches else "EMPTY", f"{len(matches)} matches")
        except Exception as e:
            self._log("ROUTER", "ERROR", str(e)[:50])
        
        df = pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        
        # Filter by league if needed
        if league_id and league_id != "ALL" and not df.empty and "LEAGUE_ID" in df.columns:
            df = df[df["LEAGUE_ID"].astype(str) == str(league_id)]
        return df

    def get_upcoming_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        try:
            if sport == "Football":
                matches = self.api_sports.get_upcoming_matches(days=7)
                if not matches:
                    matches = self.football_data.get_upcoming_matches(days=7)
            elif sport in ["NBA", "NFL", "MLB", "NHL"]:
                matches = self.msf.get_upcoming_matches(sport, days=7)
            elif sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
                matches = self.tsdb.get_upcoming_matches(sport)
            
            self._log(sport, "SUCCESS" if matches else "EMPTY", f"{len(matches)} matches")
        except Exception as e:
            self._log("ROUTER", "ERROR", str(e)[:50])
        
        df = pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        
        # Filter by league if needed
        if league_id and league_id != "ALL" and not df.empty and "LEAGUE_ID" in df.columns:
            df = df[df["LEAGUE_ID"].astype(str) == str(league_id)]
        return df

    def enrich_with_features(self, df: pd.DataFrame, sport: str) -> pd.DataFrame:
        """Add feature engineering columns for AI predictions"""
        if df.empty:
            return df
        
        # Get the appropriate feature engineer
        fe = None
        if sport == "Football":
            fe = self.football_fe
        elif sport == "NBA":
            fe = self.nba_fe
        elif sport == "NFL":
            fe = self.nfl_fe
        elif sport == "Tennis":
            fe = self.tennis_fe
        
        if fe:
            # Add feature columns to dataframe
            feature_names = fe.get_feature_names()
            for fname in feature_names:
                if fname not in df.columns:
                    df[fname] = 0.5  # Default neutral value
        
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self):
        return True  # Free APIs are always considered live

    def get_connection_log_df(self):
        return self.router.get_connection_log_df()

    def get_all_leagues(self, s: str):
        return self.router.get_all_leagues(s)

    def get_live_matches_df(self, s: str, lid: str = None):
        return self.router.get_live_matches(s, lid)

    def get_upcoming_matches_df(self, s: str, lid: str = None):
        return self.router.get_upcoming_matches(s, lid)
    
    def enrich_with_features(self, df: pd.DataFrame, sport: str):
        return self.router.enrich_with_features(df, sport)


__all__ = ["APIConfig", "EmpireDashboardData"]
