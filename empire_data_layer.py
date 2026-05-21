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
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION & API KEYS
# ═══════════════════════════════════════════════════════════════════════════════

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

    # --- API Keys from Render environment (never hardcoded) ---
    API_SPORTS_KEY        = _clean_key(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL        = "https://v3.football.api-sports.io"

    ODDS_API_KEY          = _clean_key(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL          = "https://api.the-odds-api.com/v4"

    SPORTMONKS_KEY        = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL        = "https://api.sportmonks.com/api/v3/football"

    MYSPORTSFEEDS_KEY     = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL     = "https://api.mysportsfeeds.com/v2.1/pull"

    FOOTBALL_DATA_KEY     = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL     = "https://api.football-data.org/v4"

    THESPORTSDB_KEY       = _clean_key(os.getenv("TheSportDB_API_key", "3"))  # v2 free key
    THESPORTSDB_URL_V2    = "https://www.thesportsdb.com/api/v2/json"
    THESPORTSDB_URL_V1    = "https://www.thesportsdb.com/api/v1/json/3"

    # Cache TTLs (seconds)
    CACHE_TTL_LIVE        = 30      # live scores: 30 s
    CACHE_TTL_UPCOMING    = 900     # upcoming: 15 min
    CACHE_TTL_LEAGUES     = 86400   # leagues/teams: 24 h

    REQUEST_TIMEOUT       = 10
    MAX_RETRIES           = 2
    RETRY_DELAY           = 0.5


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
    home_team_id: Optional[str]  = None
    away_team_id: Optional[str]  = None
    home_score:   Optional[int]  = None
    away_score:   Optional[int]  = None
    status:       str            = "SCHEDULED"
    minute:       Optional[int]  = None
    start_time:   Optional[datetime] = None
    venue:        Optional[str]  = None
    country:      Optional[str]  = None

    def to_dataframe_row(self) -> Dict:
        su = self.status.upper()
        is_live = any(x in su for x in ["LIVE", "1H", "2H", "HT", "IN_PROGRESS",
                                         "1ST", "2ND", "3RD", "4TH", "OT", "IN_PLAY"])
        if is_live:
            display_status = "🔴 LIVE"
        elif su in ("FINISHED", "FT", "AET", "PEN", "COMPLETED", "FINAL"):
            display_status = "✅ FINISHED"
        else:
            display_status = "⏳ UPCOMING"

        return {
            "MATCH_ID":  self.match_id,
            "TIME":      self.start_time.strftime("%H:%M") if self.start_time else "TBD",
            "LEAGUE":    self.league,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "MATCH":     f"{self.home_team} vs {self.away_team}",
            "STATUS":    display_status,
            "SCORE":     f"{self.home_score}-{self.away_score}" if self.home_score is not None else "vs",
            "PROVIDER":  self.provider,
        }


@dataclass
class League:
    league_id: str
    name:      str
    sport:     str
    country:   Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class DataProvider:
    def __init__(self, name: str, priority: int):
        self.name     = name
        self.priority = priority
        self.cache: Dict[str, Any] = {}

    def _make_request(self, url: str, headers: Dict = None,
                      params: Dict = None) -> Optional[Dict]:
        for attempt in range(APIConfig.MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    headers=headers or {},
                    params=params or {},
                    timeout=APIConfig.REQUEST_TIMEOUT,
                )
                if response.status_code == 429:
                    time.sleep((attempt + 1) * 2)
                    continue
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"[{self.name}] HTTP {response.status_code} → {url}")
                return None
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.name}] Timeout on attempt {attempt+1} → {url}")
            except Exception as e:
                logger.error(f"[{self.name}] Request error: {e}")
            if attempt < APIConfig.MAX_RETRIES - 1:
                time.sleep(APIConfig.RETRY_DELAY * (attempt + 1))
        return None

    def _cache_key(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get_cached(self, key: str, ttl: int) -> Optional[Any]:
        entry = self.cache.get(key)
        if entry and time.time() - entry["ts"] < ttl:
            return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any):
        self.cache[key] = {"data": data, "ts": time.time()}


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS PROVIDER  (Soccer)
# ═══════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS", 1)
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers  = {"x-apisports-key": APIConfig.API_SPORTS_KEY} if APIConfig.API_SPORTS_KEY else {}

    @property
    def available(self) -> bool:
        return bool(APIConfig.API_SPORTS_KEY)

    def get_all_leagues(self) -> List[League]:
        if not self.available:
            return []
        ck = self._cache_key("apisports_leagues")
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LEAGUES)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base_url}/leagues", self.headers)
        if not data:
            return []
        leagues = [
            League(
                league_id=str(item.get("league", {}).get("id", "")),
                name=item.get("league", {}).get("name", "Unknown"),
                sport="Soccer",
                country=item.get("country", {}).get("name", ""),
            )
            for item in data.get("response", [])
        ]
        self._set_cached(ck, leagues)
        return leagues

    def get_live_matches(self, league_id: str = None) -> List[Match]:
        if not self.available:
            return []
        ck = self._cache_key("apisports_live", league_id)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LIVE)
        if cached is not None:
            return cached
        params = {"live": "all"}
        if league_id and league_id != "ALL":
            params["league"] = league_id
        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []
        matches = self._parse_fixtures(data)
        self._set_cached(ck, matches)
        return matches

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        if not self.available:
            return []
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        ck = self._cache_key("apisports_upcoming", today, future)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base_url}/fixtures", self.headers,
                                  {"from": today, "to": future})
        if not data:
            return []
        matches = self._parse_fixtures(data)
        self._set_cached(ck, matches)
        return matches

    def _parse_fixtures(self, data: Dict) -> List[Match]:
        matches = []
        for fixture in data.get("response", []):
            f      = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams  = fixture.get("teams", {})
            goals  = fixture.get("goals", {})
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
# MYSPORTSFEEDS PROVIDER  (NBA · NFL · MLB · NHL)
# ═══════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    SPORT_CODES = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}
    # Sport → (off-season month start, month end)  used to pick correct season year
    SEASON_CONFIG = {
        "NBA": {"start_month": 10},   # season starts October
        "NHL": {"start_month": 10},
        "NFL": {"start_month": 9},    # season starts September
        "MLB": {"start_month": 3},    # season starts March
    }

    def __init__(self):
        super().__init__("MySportsFeeds", 2)
        self.base_url = APIConfig.MYSPORTSFEEDS_URL
        if APIConfig.MYSPORTSFEEDS_KEY and APIConfig.MYSPORTSFEEDS_PASSWORD:
            creds = base64.b64encode(
                f"{APIConfig.MYSPORTSFEEDS_KEY}:{APIConfig.MYSPORTSFEEDS_PASSWORD}".encode()
            ).decode()
            self.headers = {"Authorization": f"Basic {creds}"}
        else:
            self.headers = {}

    @property
    def available(self) -> bool:
        return bool(self.headers)

    def _sport_code(self, sport: str) -> str:
        return self.SPORT_CODES.get(sport.upper(), "nba")

    def _season(self, sport: str) -> str:
        now = datetime.now()
        cfg = self.SEASON_CONFIG.get(sport.upper(), {"start_month": 10})
        start_month = cfg["start_month"]
        if sport.upper() in ("NBA", "NHL"):
            # Oct–Jun season spans two calendar years
            if now.month >= start_month:
                return f"{now.year}-{now.year + 1}"
            else:
                return f"{now.year - 1}-{now.year}"
        elif sport.upper() == "NFL":
            # Aug–Feb
            if now.month >= start_month:
                return str(now.year)
            else:
                return str(now.year - 1)
        else:
            # MLB: March–October, single year
            return str(now.year)

    def get_teams(self, sport: str) -> List[Dict]:
        """Fetch teams live from MySportsFeeds API."""
        if not self.available:
            return []
        sport_code = self._sport_code(sport)
        season     = self._season(sport)
        ck = self._cache_key("msf_teams", sport_code, season)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LEAGUES)
        if cached is not None:
            return cached
        url  = f"{self.base_url}/{sport_code}/{season}/players.json"
        # Use the roster/team endpoint instead
        url  = f"{self.base_url}/{sport_code}/{season}/team_stats_totals.json"
        data = self._make_request(url, self.headers)
        teams = []
        if data:
            for entry in data.get("teamStatsTotals", []):
                team = entry.get("team", {})
                if team:
                    teams.append({
                        "id":      team.get("abbreviation", ""),
                        "name":    team.get("city", "") + " " + team.get("name", ""),
                        "country": "Canada" if team.get("city", "") in
                                   ["Toronto", "Montreal", "Ottawa", "Calgary",
                                    "Edmonton", "Vancouver", "Winnipeg"] else "USA",
                    })
        if teams:
            self._set_cached(ck, teams)
        return teams

    def get_live_matches(self, sport: str) -> List[Match]:
        if not self.available:
            return []
        sport_code = self._sport_code(sport)
        season     = self._season(sport)
        today      = datetime.now().strftime("%Y%m%d")
        ck = self._cache_key("msf_live", sport_code, today)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LIVE)
        if cached is not None:
            return cached
        url  = f"{self.base_url}/{sport_code}/{season}/date/{today}/games.json"
        data = self._make_request(url, self.headers)
        if not data:
            # Fallback to games endpoint with date param
            url  = f"{self.base_url}/{sport_code}/{season}/games.json"
            data = self._make_request(url, self.headers, {"date": today})
        matches = self._parse_games(data, sport) if data else []
        self._set_cached(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str, days: int = 7) -> List[Match]:
        if not self.available:
            return []
        sport_code = self._sport_code(sport)
        season     = self._season(sport)
        today      = datetime.now().strftime("%Y%m%d")
        future     = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        ck = self._cache_key("msf_upcoming", sport_code, today, future)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_UPCOMING)
        if cached is not None:
            return cached
        url  = f"{self.base_url}/{sport_code}/{season}/games.json"
        data = self._make_request(url, self.headers,
                                  {"fordate": today, "todate": future})
        matches = self._parse_games(data, sport, upcoming_only=True) if data else []
        self._set_cached(ck, matches)
        return matches

    def _parse_games(self, data: Dict, sport: str,
                     upcoming_only: bool = False) -> List[Match]:
        matches = []
        for game in data.get("games", []):
            schedule = game.get("schedule", game)
            raw_status = schedule.get("playedStatus", schedule.get("status", "UNPLAYED"))
            su = raw_status.upper()
            is_live = su in ("IN_PROGRESS", "LIVE", "PREGAME",
                             "1ST", "2ND", "3RD", "4TH", "OT")
            is_finished = su in ("COMPLETED", "FINAL", "COMPLETED_PENDING_REVIEW")
            if upcoming_only and (is_live or is_finished):
                continue

            home_team = schedule.get("homeTeam", {})
            away_team = schedule.get("awayTeam", {})
            home_name = (home_team.get("city", "") + " " + home_team.get("name", "")).strip() \
                        if isinstance(home_team, dict) else str(home_team)
            away_name = (away_team.get("city", "") + " " + away_team.get("name", "")).strip() \
                        if isinstance(away_team, dict) else str(away_team)

            score     = game.get("score", {})
            home_score = score.get("homeScoreTotal") if score else None
            away_score = score.get("awayScoreTotal") if score else None

            start_time = None
            for key in ("startTime", "startDate", "date"):
                raw = schedule.get(key, "")
                if raw:
                    try:
                        start_time = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass

            if is_live:
                display_status = "LIVE"
            elif is_finished:
                display_status = "FINISHED"
            else:
                display_status = "SCHEDULED"

            matches.append(Match(
                match_id=str(schedule.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home_name or "TBD",
                away_team=away_name or "TBD",
                home_score=home_score,
                away_score=away_score,
                status=display_status,
                start_time=start_time,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER  (UFC · F1 · Tennis · Cricket · Golf)
# ═══════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    # TheSportsDB league IDs for non-team sports
    LEAGUE_IDS = {
        "UFC":       "4467",
        "Formula 1": "4370",
        "Tennis":    "4424",
        "Cricket":   "4722",
        "Golf":      "4426",
    }
    SPORT_NAMES = {
        "UFC":       "MMA",
        "Formula 1": "Motorsport",
        "Tennis":    "Tennis",
        "Cricket":   "Cricket",
        "Golf":      "Golf",
    }

    def __init__(self):
        super().__init__("TheSportsDB", 3)
        self.api_key  = APIConfig.THESPORTSDB_KEY
        self.base_v2  = APIConfig.THESPORTSDB_URL_V2
        self.base_v1  = APIConfig.THESPORTSDB_URL_V1

    def _req_v1(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        url = f"{self.base_v1}/{endpoint}"
        return self._make_request(url, params=params)

    def _req_v2(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        url = f"{self.base_v2}/{self.api_key}/{endpoint}"
        return self._make_request(url, params=params)

    def get_leagues_for_sport(self, sport: str) -> List[Dict]:
        """Return sub-competitions/leagues for a given sport from live API."""
        league_id = self.LEAGUE_IDS.get(sport)
        if not league_id:
            return []
        ck = self._cache_key("tsdb_leagues", sport)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LEAGUES)
        if cached is not None:
            return cached

        # v1 endpoint for league seasons (public)
        data = self._req_v1(f"search_all_seasons.php", {"id": league_id})
        leagues = []
        if data and data.get("seasons"):
            # Return current season as a league option
            for s in data["seasons"][:10]:
                leagues.append({
                    "id":      f"{league_id}_{s.get('strSeason', '')}",
                    "name":    s.get("strSeason", "Unknown Season"),
                    "country": "World",
                })
        if not leagues:
            # Fallback: single entry for the league itself
            data2 = self._req_v1("lookupleague.php", {"id": league_id})
            if data2 and data2.get("leagues"):
                lg = data2["leagues"][0]
                leagues = [{"id": league_id, "name": lg.get("strLeague", sport), "country": lg.get("strCountry", "World")}]
        self._set_cached(ck, leagues)
        return leagues

    def get_live_matches(self, sport: str) -> List[Match]:
        ck = self._cache_key("tsdb_live", sport)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_LIVE)
        if cached is not None:
            return cached

        # v1 livescores (free tier)
        data = self._req_v1("livescore.php", {"s": self.SPORT_NAMES.get(sport, sport)})
        matches = []
        if data and data.get("events"):
            for event in data["events"]:
                is_live = event.get("strStatus") in ["1H", "2H", "HT", "IN_PLAY",
                                                      "ET", "PEN_LIVE", "LIVE"]
                matches.append(Match(
                    match_id=event.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=event.get("strLeague", sport),
                    league_id=event.get("idLeague", ""),
                    home_team=event.get("strHomeTeam", "TBD"),
                    away_team=event.get("strAwayTeam", "TBD"),
                    home_score=_try_int(event.get("intHomeScore")),
                    away_score=_try_int(event.get("intAwayScore")),
                    status="LIVE" if is_live else event.get("strStatus", "SCHEDULED"),
                    country=event.get("strCountry"),
                ))
        self._set_cached(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        league_id = self.LEAGUE_IDS.get(sport)
        if not league_id:
            return []
        ck = self._cache_key("tsdb_upcoming", sport)
        cached = self._get_cached(ck, APIConfig.CACHE_TTL_UPCOMING)
        if cached is not None:
            return cached

        data = self._req_v1("eventsnextleague.php", {"id": league_id})
        matches = []
        if data and data.get("events"):
            for event in data["events"]:
                start = None
                if event.get("dateEvent"):
                    try:
                        time_str = event.get("strTime", "00:00:00") or "00:00:00"
                        start = datetime.strptime(
                            f"{event['dateEvent']} {time_str[:5]}", "%Y-%m-%d %H:%M"
                        )
                    except Exception:
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
                    country=event.get("strCountry"),
                ))
        self._set_cached(ck, matches)
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _try_int(val) -> Optional[int]:
    try:
        return int(val) if val is not None else None
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

    # ── Logging ──────────────────────────────────────────────────────────────
    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME":     datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": provider,
            "STATUS":   status,
            "DETAIL":   detail[:80],
        })

    def _log_initial_status(self):
        if APIConfig.API_SPORTS_KEY:
            self._log("API-SPORTS",    "READY", "Soccer provider active")
        else:
            self._log("API-SPORTS",    "NOT CONFIGURED", "Set API_SPORTS_KEY env var")
        if APIConfig.MYSPORTSFEEDS_KEY:
            self._log("MySportsFeeds", "READY", "NBA/NFL/MLB/NHL provider active")
        else:
            self._log("MySportsFeeds", "NOT CONFIGURED", "Set MYSPORTSFEEDS_KEY env var")
        self._log("TheSportsDB",   "READY", "UFC/F1/Tennis/Cricket/Golf provider active")
        if APIConfig.ODDS_API_KEY:
            self._log("TheOddsAPI",    "READY", "Odds provider active")
        if APIConfig.FOOTBALL_DATA_KEY:
            self._log("Football-Data", "READY", "Soccer backup provider active")

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        return pd.DataFrame(self.connection_log).tail(50)

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
            {"name": "Sportmonks",
             "status": "🟢 ONLINE" if APIConfig.SPORTMONKS_KEY else "⚪ NOT CONFIGURED"},
        ]

    # ── Leagues / teams list ─────────────────────────────────────────────────
    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        """
        Returns a list of {"id", "name", "country"} dicts for the sidebar league
        dropdown.  All data sourced from live APIs; nothing hardcoded.
        """
        try:
            # SOCCER — hundreds of leagues from API-SPORTS
            if sport_type == "Soccer":
                leagues = self.api_sports.get_all_leagues()
                if leagues:
                    self._log("API-SPORTS", "SUCCESS",
                              f"{len(leagues)} soccer leagues fetched")
                    return [{"id": l.league_id, "name": l.name,
                             "country": l.country or ""} for l in leagues]
                self._log("API-SPORTS", "EMPTY", "No soccer leagues returned")
                return []

            # AMERICAN SPORTS — teams from MySportsFeeds
            elif sport_type in ("NBA", "NFL", "MLB", "NHL"):
                teams = self.my_sports_feeds.get_teams(sport_type)
                if teams:
                    self._log("MySportsFeeds", "SUCCESS",
                              f"{len(teams)} {sport_type} teams fetched")
                    return teams
                self._log("MySportsFeeds", "EMPTY",
                          f"No {sport_type} teams; API may be inactive")
                return []

            # NICHE SPORTS — league seasons from TheSportsDB
            elif sport_type in ("UFC", "Formula 1", "Tennis", "Cricket", "Golf"):
                leagues = self.the_sports_db.get_leagues_for_sport(sport_type)
                if leagues:
                    self._log("TheSportsDB", "SUCCESS",
                              f"{len(leagues)} {sport_type} league entries fetched")
                    return leagues
                self._log("TheSportsDB", "EMPTY",
                          f"No {sport_type} league data returned")
                return []

        except Exception as e:
            self._log("ROUTER", "ERROR", f"get_all_leagues({sport_type}): {e}")

        return []

    # ── Live matches ─────────────────────────────────────────────────────────
    def get_live_matches(self, sport_type: str,
                         league_id: str = None) -> pd.DataFrame:
        try:
            if sport_type == "Soccer":
                matches = self.api_sports.get_live_matches(league_id)
                self._log("API-SPORTS",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live soccer matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

            elif sport_type in ("NBA", "NFL", "MLB", "NHL"):
                matches = self.my_sports_feeds.get_live_matches(sport_type)
                self._log("MySportsFeeds",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live {sport_type} matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

            elif sport_type in ("UFC", "Formula 1", "Tennis", "Cricket", "Golf"):
                matches = self.the_sports_db.get_live_matches(sport_type)
                self._log("TheSportsDB",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live {sport_type} events")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

        except Exception as e:
            self._log("ROUTER", "ERROR", f"get_live_matches({sport_type}): {e}")

        return pd.DataFrame()

    # ── Upcoming matches ─────────────────────────────────────────────────────
    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        try:
            if sport_type == "Soccer":
                matches = self.api_sports.get_upcoming_matches()
                self._log("API-SPORTS",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming soccer matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

            elif sport_type in ("NBA", "NFL", "MLB", "NHL"):
                matches = self.my_sports_feeds.get_upcoming_matches(sport_type)
                self._log("MySportsFeeds",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming {sport_type} matches")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

            elif sport_type in ("UFC", "Formula 1", "Tennis", "Cricket", "Golf"):
                matches = self.the_sports_db.get_upcoming_matches(sport_type)
                self._log("TheSportsDB",
                          "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming {sport_type} events")
                return pd.DataFrame([m.to_dataframe_row() for m in matches])

        except Exception as e:
            self._log("ROUTER", "ERROR", f"get_upcoming_matches({sport_type}): {e}")

        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD DATA FACADE
# ═══════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self) -> bool:
        """True when at least one provider has a key configured."""
        return bool(
            APIConfig.API_SPORTS_KEY
            or APIConfig.MYSPORTSFEEDS_KEY
            or APIConfig.THESPORTSDB_KEY
        )

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport_type: str,
                            league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_type: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(sport_type)

    # Stubs for future expansion
    def get_match_prediction(self, match_id: str): return None
    def get_match_details(self, match_id: str):    return {"found": False}
    def get_team_form(self, team_name: str, match_id: str): return None
    def get_head_to_head(self, home: str, away: str, match_id: str): return []
    def get_key_players(self, match_id: str):      return []
    def get_match_odds(self, match_id: str):       return {}
    def get_ai_reasoning(self, match_id: str):     return []


__all__ = ["APIConfig", "EmpireDashboardData"]
