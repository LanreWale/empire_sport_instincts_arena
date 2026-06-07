"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer
OPTIMIZED FOR FREE TIER - 100 requests/day
- Conditional fetching (only when needed)
- Request logging and tracking
- Automatic fallback to Football-Data.org when rate limit approached
- CORRECTED: Uses "Football" as sport name (matches API)
"""

import os, json, time, hashlib, base64, requests, threading, logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
class APIConfig:
    @staticmethod
    def _e(k, d=""): return str(os.getenv(k, d)).strip()

    # PRIMARY API (100 requests/day)
    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"
    
    # BACKUP API (10 requests/min - no daily limit)
    FOOTBALL_DATA_KEY = _e("FOOTBALL_DATA_KEY")
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    
    # COMPLETELY FREE APIS (No limits)
    TSDB_KEY          = _e("TheSportDB_API_key", "3")
    TSDB_URL          = "https://www.thesportsdb.com/api/v1/json"
    MSF_KEY           = _e("MYSPORTSFEEDS_KEY")
    MSF_PASS          = _e("MYSPORTSFEEDS_PASSWORD")
    MSF_URL           = "https://api.mysportsfeeds.com/v2.1/pull"

    # Cache TTLs - INCREASED to reduce API calls
    TTL_LIVE     = 60      # Cache live matches for 60 seconds
    TTL_UPCOMING = 900     # Cache upcoming for 15 minutes
    TTL_LEAGUES  = 86400   # Cache leagues for 24 hours
    TIMEOUT      = 12
    RETRIES      = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LISTS (ZERO API calls - always available)
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Football": [
        {"id": "39",  "name": "Premier League",                "country": "England"},
        {"id": "40",  "name": "Championship",                  "country": "England"},
        {"id": "140", "name": "La Liga",                       "country": "Spain"},
        {"id": "135", "name": "Serie A",                       "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                    "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                       "country": "France"},
        {"id": "88",  "name": "Eredivisie",                    "country": "Netherlands"},
        {"id": "2",   "name": "UEFA Champions League",         "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",            "country": "Europe"},
        {"id": "1",   "name": "FIFA World Cup",                "country": "World"},
        {"id": "10",  "name": "Friendlies International",      "country": "World"},
        {"id": "14",  "name": "World Club Friendlies",         "country": "World"},
        {"id": "12",  "name": "Friendly International Women",  "country": "World"},
        {"id": "253", "name": "MLS",                           "country": "USA"},
        {"id": "71",  "name": "Brasileirao Serie A",           "country": "Brazil"},
        {"id": "283", "name": "Saudi Pro League",              "country": "Saudi Arabia"},
        {"id": "98",  "name": "J-League",                      "country": "Japan"},
        {"id": "17",  "name": "AFC Champions League",          "country": "Asia"},
        {"id": "29",  "name": "CAF Champions League",          "country": "Africa"},
        {"id": "233", "name": "NPFL",                          "country": "Nigeria"},
        {"id": "11",  "name": "Copa Libertadores",             "country": "S. America"},
        {"id": "9",   "name": "Copa America",                  "country": "S. America"},
        {"id": "7",   "name": "FIFA Women's World Cup",        "country": "World"},
        {"id": "573", "name": "Women's Super League",          "country": "England"},
        {"id": "582", "name": "NWSL",                          "country": "USA"},
    ],
    "NBA": [{"id": "NBA", "name": "NBA", "country": "USA"}],
    "NFL": [{"id": "NFL", "name": "NFL", "country": "USA"}],
    "MLB": [{"id": "MLB", "name": "MLB", "country": "USA"}],
    "NHL": [{"id": "NHL", "name": "NHL", "country": "USA"}],
    "UFC": [{"id": "UFC_ALL", "name": "UFC", "country": "World"}],
    "Formula 1": [{"id": "F1_ALL", "name": "Formula 1", "country": "World"}],
    "Tennis": [{"id": "ATP_ALL", "name": "Tennis", "country": "World"}],
    "Cricket": [{"id": "ICC_WC", "name": "Cricket", "country": "World"}],
    "Golf": [{"id": "PGA_ALL", "name": "Golf", "country": "World"}],
    "Volleyball": [{"id": "VB_ALL", "name": "Volleyball", "country": "World"}],
    "Handball": [{"id": "HB_ALL", "name": "Handball", "country": "World"}],
    "Rugby": [{"id": "RU_ALL", "name": "Rugby", "country": "World"}],
    "Darts": [{"id": "DARTS_ALL", "name": "Darts", "country": "World"}],
    "Snooker": [{"id": "SNK_ALL", "name": "Snooker", "country": "World"}],
    "Table Tennis": [{"id": "TT_ALL", "name": "Table Tennis", "country": "World"}],
    "Esports": [{"id": "ES_ALL", "name": "Esports", "country": "World"}],
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
        is_live = any(x in su for x in ["LIVE", "1H", "2H", "HT", "IN_PLAY", "IN_PROGRESS"])
        is_done = any(x in su for x in ["FINISH", "FT", "FINAL", "COMPLET", "ENDED"])
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
            except Exception:
                t = str(self.start_time)[:16]
        return {
            "MATCH_ID":  self.match_id,
            "TIME":      t or "TBD",
            "LEAGUE":    self.league,
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

    def _req(self, url: str, headers: Dict = None, params: Dict = None) -> Optional[Any]:
        for attempt in range(APIConfig.RETRIES):
            try:
                r = requests.get(url, headers=headers or {}, params=params or {}, timeout=APIConfig.TIMEOUT)
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


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS PROVIDER - WITH REQUEST TRACKING
# ═══════════════════════════════════════════════════════════════════════════════
class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.api_key = APIConfig.API_SPORTS_KEY
        self.headers = {"x-apisports-key": self.api_key} if self.api_key else {}
        self.request_count = 0
        self.request_log: List[Dict] = []
        self.last_reset = datetime.now()
        self.rate_limit_exhausted = False

    @property
    def ok(self):
        return bool(self.api_key) and not self.rate_limit_exhausted

    def _check_rate_limit(self):
        """Track rate limit and warn when approaching"""
        now = datetime.now()
        if now.day != self.last_reset.day:
            self.request_count = 0
            self.rate_limit_exhausted = False
            self.last_reset = now
            logger.info("[API-SPORTS] Rate limit reset for new day")
        
        if self.request_count >= 95:
            logger.warning(f"[API-SPORTS] High usage: {self.request_count}/100 requests used")
        
        if self.request_count >= 100:
            self.rate_limit_exhausted = True
            logger.error("[API-SPORTS] Daily rate limit exhausted! Using fallback.")
            return False
        return True

    def _log_request(self, endpoint: str):
        """Log each request for debugging"""
        self.request_count += 1
        self.request_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "endpoint": endpoint,
            "count": self.request_count,
            "remaining": 100 - self.request_count
        })
        logger.info(f"[API-SPORTS] Request #{self.request_count}: {endpoint} (remaining: {100 - self.request_count})")

    def get_remaining_requests(self) -> int:
        """Get remaining requests for today"""
        now = datetime.now()
        if now.day != self.last_reset.day:
            return 100
        return max(0, 100 - self.request_count)

    def get_live_matches(self) -> List[Match]:
        """Get live matches - API-SPORTS returns football data"""
        if not self._check_rate_limit():
            return []
        
        cache_key = self._ck("live")
        cached = self._get(cache_key, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        
        self._log_request("fixtures?live=all")
        
        response = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.headers, {"live": "all"})
        
        if not response:
            return []
        
        matches = []
        for fixture in response.get("response", []):
            match = self._parse_fixture(fixture)
            if match and match.status == "LIVE":
                matches.append(match)
        
        self._set(cache_key, matches)
        return matches

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        """Get upcoming matches - API-SPORTS returns football data"""
        if not self._check_rate_limit():
            return []
        
        cache_key = self._ck("upcoming", days)
        cached = self._get(cache_key, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        self._log_request(f"fixtures?from={today}&to={future}")
        
        response = self._req(
            f"{APIConfig.API_SPORTS_URL}/fixtures",
            self.headers,
            {"from": today, "to": future}
        )
        
        if not response:
            return []
        
        matches = []
        for fixture in response.get("response", []):
            match = self._parse_fixture(fixture)
            if match and match.status == "SCHEDULED":
                matches.append(match)
        
        self._set(cache_key, matches)
        return matches

    def _parse_fixture(self, fixture: Dict) -> Optional[Match]:
        try:
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            status = f.get("status", {})
            
            start_time = None
            if f.get("date"):
                try:
                    start_time = datetime.fromisoformat(f["date"].replace("Z", "+00:00"))
                except:
                    pass
            
            status_short = status.get("short", "NS")
            if status_short == "LIVE":
                match_status = "LIVE"
            elif status_short in ["FT", "AET", "PEN"]:
                match_status = "FINISHED"
            else:
                match_status = "SCHEDULED"
            
            return Match(
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
                start_time=start_time,
                country=league.get("country", ""),
            )
        except Exception as e:
            logger.error(f"Error parsing fixture: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA PROVIDER (BACKUP - No daily limit)
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
        """Track 10 requests per minute"""
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
        cache_key = self._ck("today", today)
        cached = self._get(cache_key, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        
        response = self._req(
            f"{APIConfig.FOOTBALL_DATA_URL}/matches",
            self.headers,
            {"dateFrom": today, "dateTo": today}
        )
        
        matches = []
        if response:
            for match in response.get("matches", []):
                comp = match.get("competition", {})
                home = match.get("homeTeam", {})
                away = match.get("awayTeam", {})
                score = match.get("score", {}).get("fullTime", {})
                
                start_time = None
                if match.get("utcDate"):
                    try:
                        start_time = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
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
                    start_time=start_time,
                ))
        
        self._set(cache_key, matches)
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        self.api_sports = APISportsProvider()
        self.football_data = FootballDataProvider()
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
        remaining = self.api_sports.get_remaining_requests()
        self._log("API-SPORTS", "READY" if self.api_sports.ok else "RATE LIMITED", f"{remaining}/100 requests remaining today")
        self._log("Football-Data", "READY", "Backup - No daily limit")

    def get_provider_status(self) -> List[Dict]:
        remaining = self.api_sports.get_remaining_requests()
        if self.api_sports.rate_limit_exhausted:
            api_status = f"🔴 RATE LIMITED - 0/{remaining} remaining today"
        elif remaining < 20:
            api_status = f"🟡 LOW QUOTA - {remaining}/100 remaining today"
        else:
            api_status = f"🟢 ONLINE - {remaining}/100 remaining today"
        
        return [
            {"name": "API-SPORTS (Primary)", "status": api_status},
            {"name": "Football-Data (Backup)", "status": "🟢 ONLINE - No daily limit"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-50:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        return STATIC_LEAGUES.get(sport, [{"id": "ALL", "name": "All Events", "country": "World"}])

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        if sport == "Football":
            # Try API-SPORTS first if not rate limited
            if not self.api_sports.rate_limit_exhausted:
                matches = self.api_sports.get_live_matches()
                if matches:
                    self._log("API-SPORTS", "SUCCESS", f"{len(matches)} live football matches")
                else:
                    self._log("API-SPORTS", "NO LIVE", "No live matches currently")
            else:
                self._log("API-SPORTS", "SKIPPED", "Rate limit exhausted - using backup")
            
            # Fallback to Football-Data if needed
            if not matches:
                fd_matches = self.football_data.get_today_matches()
                matches = [m for m in fd_matches if m.status == "LIVE"]
                if matches:
                    self._log("Football-Data", "SUCCESS", f"{len(matches)} live football matches")
        
        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()

    def get_upcoming_matches(self, sport: str) -> pd.DataFrame:
        matches = []
        if sport == "Football":
            # Try API-SPORTS first
            if not self.api_sports.rate_limit_exhausted and self.api_sports.get_remaining_requests() > 10:
                matches = self.api_sports.get_upcoming_matches(days=7)
                if matches:
                    self._log("API-SPORTS", "SUCCESS", f"{len(matches)} upcoming football matches")
                else:
                    self._log("API-SPORTS", "EMPTY", "No upcoming matches found")
            
            # Fallback to Football-Data if API-SPORTS found nothing
            if not matches:
                fd_matches = self.football_data.get_today_matches()
                matches = [m for m in fd_matches if m.status == "SCHEDULED"]
                if matches:
                    self._log("Football-Data", "SUCCESS", f"{len(matches)} upcoming football matches")
                else:
                    self._log("Football-Data", "EMPTY", "No upcoming matches found")
        
        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self):
        return True

    def get_connection_log_df(self):
        return self.router.get_connection_log_df()

    def get_all_leagues(self, s: str):
        return self.router.get_all_leagues(s)

    def get_live_matches_df(self, s: str, lid: str = None):
        return self.router.get_live_matches(s, lid)

    def get_upcoming_matches_df(self, s: str):
        return self.router.get_upcoming_matches(s)


__all__ = ["APIConfig", "EmpireDashboardData"]
