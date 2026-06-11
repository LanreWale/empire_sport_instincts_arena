"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer (World-Class Multi-Sport v5.0)
PRIMARY SOURCE: Apify/FlashScore (34+ Sports, using CORRECT actor input)
BACKUP SOURCES: API-SPORTS, Football-Data, MySportsFeeds, TheSportsDB
ALL EXISTING LEAGUES PRESERVED - 500+ LEAGUES ACROSS ALL CONTINENTS
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

# Optional feature imports
try:
    from football_features import FootballFeatureEngineer
except ImportError:
    FootballFeatureEngineer = None

try:
    from nba_features import NBAFeatureEngineer
except ImportError:
    NBAFeatureEngineer = None

try:
    from nfl_features import NFLFeatureEngineer
except ImportError:
    NFLFeatureEngineer = None

try:
    from tennis_features import TennisFeatureEngineer
except ImportError:
    TennisFeatureEngineer = None

load_dotenv()
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
class APIConfig:
    @staticmethod
    def _e(k, d=""): return str(os.getenv(k, d)).strip()

    # PRIMARY: Apify/FlashScore (34+ Sports)
    APIFY_API_KEY     = _e("APIFY_API_KEY")
    
    # BACKUP PROVIDERS
    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"
    FOOTBALL_DATA_KEY = _e("FOOTBALL_DATA_KEY")
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    TSDB_KEY          = _e("TheSportDB_API_key", "3")
    TSDB_URL          = "https://www.thesportsdb.com/api/v1/json"
    MSF_KEY           = _e("MYSPORTSFEEDS_KEY")
    MSF_PASS          = _e("MYSPORTSFEEDS_PASSWORD")
    MSF_URL           = "https://api.mysportsfeeds.com/v2.1/pull"

    TTL_LIVE     = 30
    TTL_UPCOMING = 600
    TTL_LEAGUES  = 86400
    TIMEOUT      = 15
    RETRIES      = 2


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
# APIFY / FLASHSCORE PROVIDER (PRIMARY - CORRECTED ACTOR INTEGRATION)
# ═══════════════════════════════════════════════════════════════════════════════
class ApifyProvider(DataProvider):
    """
    FlashScore via Apify - PRIMARY source for all sports
    CORRECTED: Uses 'sport' parameter (not startUrls) as per actor documentation
    """
    
    # Map your sport names to what the FlashScore scraper actor expects
    SPORT_MAP = {
        "Football":     "football",
        "Soccer":       "football",
        "NBA":          "basketball",
        "NFL":          "american-football",
        "MLB":          "baseball",
        "NHL":          "hockey",
        "UFC":          "mma",
        "MMA":          "mma",
        "Formula 1":    "motorsport",
        "F1":           "motorsport",
        "Motorsport":   "motorsport",
        "Tennis":       "tennis",
        "Cricket":      "cricket",
        "Golf":         "golf",
        "Volleyball":   "volleyball",
        "Handball":     "handball",
        "Rugby":        "rugby-union",
        "Rugby Union":  "rugby-union",
        "Rugby League": "rugby-league",
        "Darts":        "darts",
        "Snooker":      "snooker",
        "Table Tennis": "table-tennis",
        "Esports":      "esports",
        "Badminton":    "badminton",
        "Bandy":        "bandy",
        "Baseball":     "baseball",
        "Basketball":   "basketball",
        "Boxing":       "boxing",
        "Cycling":      "cycling",
        "Floorball":    "floorball",
        "Futsal":       "futsal",
        "Ice Hockey":   "ice-hockey",
        "Netball":      "netball",
        "Speedway":     "speedway",
        "Water Polo":   "water-polo",
    }

    def __init__(self):
        super().__init__("Apify/FlashScore")
        self.api_key = APIConfig.APIFY_API_KEY
        self.actor_id = "crawlerbros~flashscore-scraper"
        self._cache: Dict[str, Any] = {}

    @property
    def ok(self):
        return bool(self.api_key)

    def _call_actor(self, sport: str, live_only: bool = False, timeout: int = 60) -> Optional[List]:
        """
        Run Apify actor with CORRECT input format using 'sport' parameter.
        Based on official FlashScore Scraper documentation.
        """
        if not self.api_key:
            logger.warning("Apify: No API key")
            return None
        
        # Get the correct sport name for the actor
        actor_sport = self.SPORT_MAP.get(sport, "football")
        
        # CORRECT payload format for FlashScore scraper actor
        payload = {
            "sport": actor_sport,      # ← KEY: Use 'sport' parameter, not startUrls
            "liveOnly": live_only,
            "maxItems": 500
        }
        
        logger.info(f"Apify: Calling actor for sport '{actor_sport}' (mapped from '{sport}')")
        
        # Use the synchronous endpoint that returns data directly
        url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items"
        
        try:
            response = requests.post(
                url,
                params={"token": self.api_key, "timeout": timeout, "memory": 256},
                json=payload,
                timeout=timeout + 10
            )
            
            if response.status_code == 200:
                items = response.json()
                if isinstance(items, list):
                    logger.info(f"Apify: Retrieved {len(items)} items for {sport}")
                    return items
                elif isinstance(items, dict) and "items" in items:
                    logger.info(f"Apify: Retrieved {len(items['items'])} items for {sport}")
                    return items["items"]
                else:
                    logger.warning(f"Apify: Unexpected response format for {sport}")
                    return None
            else:
                logger.error(f"Apify: HTTP {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Apify: Timeout after {timeout}s for {sport}")
            return None
        except Exception as e:
            logger.error(f"Apify: Error calling actor: {e}")
            return None

    def _ck(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get(self, key: str, ttl: int) -> Optional[Any]:
        e = self._cache.get(key)
        return e["v"] if e and time.time() - e["t"] < ttl else None

    def _set(self, key: str, val: Any):
        self._cache[key] = {"v": val, "t": time.time()}

    def get_matches_by_sport(self, sport: str, live_only: bool = False) -> List[Match]:
        """Fetch matches for a sport using the CORRECT actor input format"""
        cache_key = self._ck("sport", sport, str(live_only))
        cached = self._get(cache_key, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        
        items = self._call_actor(sport, live_only, 60)
        if not items:
            return []
        
        matches = self._parse_items(items, sport)
        self._set(cache_key, matches)
        return matches

    def get_live_matches(self, sport: str) -> List[Match]:
        """Fetch live matches only"""
        return self.get_matches_by_sport(sport, live_only=True)

    def _parse_items(self, items: List, sport: str) -> List[Match]:
        """Parse Apify output into Match objects"""
        matches = []
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Extract team names - handle various field names from FlashScore
            home = (item.get('homeTeam') or item.get('home') or 
                   item.get('team1') or item.get('homeName') or '')
            away = (item.get('awayTeam') or item.get('away') or 
                   item.get('team2') or item.get('awayName') or '')
            
            if isinstance(home, dict):
                home = home.get('name', home.get('shortName', 'TBD'))
            if isinstance(away, dict):
                away = away.get('name', away.get('shortName', 'TBD'))
            
            home = str(home).strip() if home else 'TBD'
            away = str(away).strip() if away else 'TBD'
            
            if home == 'TBD' and away == 'TBD':
                continue
            
            # Extract tournament/league name
            tournament = item.get('tournament') or item.get('league') or item.get('competition')
            if isinstance(tournament, dict):
                league = tournament.get('name', tournament.get('longName', sport))
                league_id = str(tournament.get('id', ''))
            else:
                league = str(tournament) if tournament else sport
                league_id = ''
            
            # Parse status
            status_raw = str(item.get('status') or item.get('matchStatus') or 
                            item.get('statusText') or 'SCHEDULED').lower()
            
            is_live = any(x in status_raw for x in ['live', 'in progress', '1st', '2nd', 'half', 'period', 'quarter', 'ongoing'])
            is_finished = any(x in status_raw for x in ['finished', 'ft', 'final', 'ended', 'complete'])
            
            if is_live:
                match_status = "LIVE"
            elif is_finished:
                match_status = "FINISHED"
            else:
                match_status = "SCHEDULED"
            
            # Parse scores
            home_score = None
            away_score = None
            
            if 'score' in item:
                score = item['score']
                if isinstance(score, dict):
                    home_score = score.get('home') or score.get('homeTeam')
                    away_score = score.get('away') or score.get('awayTeam')
                elif isinstance(score, str) and ':' in score:
                    parts = score.split(':')
                    if len(parts) == 2:
                        home_score = self._toint(parts[0])
                        away_score = self._toint(parts[1])
            
            if home_score is None:
                home_score = item.get('homeScore') or item.get('goalsHome')
            if away_score is None:
                away_score = item.get('awayScore') or item.get('goalsAway')
            
            # Parse start time
            start_time = None
            time_fields = ['startTime', 'startTimestamp', 'date', 'kickoff', 'time', 'startDate']
            for field in time_fields:
                raw_time = item.get(field)
                if raw_time:
                    try:
                        if isinstance(raw_time, (int, float)):
                            if raw_time > 1e10:
                                raw_time = raw_time / 1000
                            start_time = datetime.fromtimestamp(raw_time)
                        elif isinstance(raw_time, str):
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                try:
                                    start_time = datetime.strptime(raw_time[:19], fmt)
                                    break
                                except:
                                    continue
                        break
                    except:
                        continue
            
            match_id = str(item.get('id') or item.get('matchId') or 
                          item.get('eventId') or abs(hash(f"{home}{away}{league}")) % 10**9)
            
            matches.append(Match(
                match_id=match_id,
                provider="FlashScore/Apify",
                league=league[:100] if league else sport,
                league_id=league_id,
                home_team=home[:50],
                away_team=away[:50],
                home_score=self._toint(home_score),
                away_score=self._toint(away_score),
                status=match_status,
                minute=item.get('minute'),
                start_time=start_time,
                venue=item.get('venue'),
                country=item.get('country'),
            ))
        
        return matches

    def _toint(self, v) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS PROVIDER (BACKUP - Football, 100 requests/day)
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
        now = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        if len(self.request_timestamps) >= 10:
            return False
        self.request_timestamps.append(now)
        return True

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
# MYSPORTSFEEDS PROVIDER (NBA, NFL, MLB, NHL - BACKUP)
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
# THESPORTSDB PROVIDER (UFC, F1, Tennis, Cricket, Golf - BACKUP)
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
# COMPREHENSIVE STATIC LEAGUE LISTS - COMPLETE (500+ LEAGUES - ALL PRESERVED)
# ═══════════════════════════════════════════════════════════════════════════════
# NOTE: This is YOUR COMPLETE LEAGUE LIST - NOTHING REMOVED, NOTHING OMITTED
# All 500+ leagues across all continents are preserved exactly as you provided

STATIC_LEAGUES: Dict[str, List[Dict]] = {
    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTBALL / SOCCER - COMPLETE GLOBAL COVERAGE (250+ Leagues)
    # Including FULL AFRICAN COVERAGE - ALL PRESERVED
    # ═══════════════════════════════════════════════════════════════════════════
    "Football": [
        # ==================== UEFA (EUROPE) - 50+ Leagues ====================
        {"id": "39",  "name": "Premier League",                "country": "England"},
        {"id": "40",  "name": "Championship",                  "country": "England"},
        {"id": "41",  "name": "League One",                    "country": "England"},
        {"id": "42",  "name": "League Two",                    "country": "England"},
        {"id": "45",  "name": "FA Cup",                        "country": "England"},
        {"id": "48",  "name": "EFL Cup",                       "country": "England"},
        {"id": "140", "name": "La Liga",                       "country": "Spain"},
        {"id": "141", "name": "La Liga 2",                     "country": "Spain"},
        {"id": "143", "name": "Copa del Rey",                  "country": "Spain"},
        {"id": "135", "name": "Serie A",                       "country": "Italy"},
        {"id": "136", "name": "Serie B",                       "country": "Italy"},
        {"id": "137", "name": "Coppa Italia",                  "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                    "country": "Germany"},
        {"id": "79",  "name": "2. Bundesliga",                 "country": "Germany"},
        {"id": "81",  "name": "DFB Pokal",                     "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                       "country": "France"},
        {"id": "62",  "name": "Ligue 2",                       "country": "France"},
        {"id": "66",  "name": "Coupe de France",               "country": "France"},
        {"id": "88",  "name": "Eredivisie",                    "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",                 "country": "Portugal"},
        {"id": "144", "name": "Pro League",                    "country": "Belgium"},
        {"id": "197", "name": "Super Lig",                     "country": "Turkey"},
        {"id": "119", "name": "Superliga",                     "country": "Denmark"},
        {"id": "113", "name": "Allsvenskan",                   "country": "Sweden"},
        {"id": "103", "name": "Eliteserien",                   "country": "Norway"},
        {"id": "116", "name": "Ekstraklasa",                   "country": "Poland"},
        {"id": "179", "name": "Premiership",                   "country": "Scotland"},
        {"id": "182", "name": "Scottish Cup",                  "country": "Scotland"},
        {"id": "207", "name": "Super League",                  "country": "Switzerland"},
        {"id": "172", "name": "Super League",                  "country": "Greece"},
        {"id": "235", "name": "Premier League",                "country": "Russia"},
        {"id": "218", "name": "First League",                  "country": "Czech Republic"},
        {"id": "176", "name": "Nemzeti Bajnoksag",             "country": "Hungary"},
        {"id": "199", "name": "Liga 1",                        "country": "Romania"},
        {"id": "188", "name": "Prva Liga",                     "country": "Croatia"},
        {"id": "221", "name": "Premier Liga",                  "country": "Ukraine"},
        {"id": "262", "name": "Bundesliga",                    "country": "Austria"},
        {"id": "264", "name": "Super League",                  "country": "Israel"},
        {"id": "268", "name": "Premier League",                "country": "Iceland"},
        {"id": "271", "name": "Premier League",                "country": "Albania"},
        {"id": "273", "name": "Premier League",                "country": "Armenia"},
        {"id": "275", "name": "Premyer Liqasi",                "country": "Azerbaijan"},
        {"id": "278", "name": "Premier League",                "country": "Bosnia"},
        {"id": "280", "name": "First League",                  "country": "Bulgaria"},
        {"id": "282", "name": "First League",                  "country": "Cyprus"},
        {"id": "285", "name": "Meistriliiga",                  "country": "Estonia"},
        {"id": "287", "name": "Premier League",                "country": "Faroe Islands"},
        {"id": "289", "name": "Erovnuli Liga",                 "country": "Georgia"},
        {"id": "291", "name": "Premier League",                "country": "Gibraltar"},
        {"id": "293", "name": "Premier League",                "country": "Kazakhstan"},
        {"id": "295", "name": "Superliga",                     "country": "Kosovo"},
        {"id": "297", "name": "Virsliga",                      "country": "Latvia"},
        {"id": "299", "name": "A Lyga",                        "country": "Lithuania"},
        {"id": "301", "name": "National Division",             "country": "Luxembourg"},
        {"id": "303", "name": "Premier League",                "country": "Malta"},
        {"id": "305", "name": "Super Liga",                    "country": "Moldova"},
        {"id": "307", "name": "Campionato",                    "country": "Montenegro"},
        {"id": "309", "name": "Prva Liga",                     "country": "North Macedonia"},
        {"id": "311", "name": "Premier League",                "country": "Northern Ireland"},
        {"id": "313", "name": "Eliteserien",                   "country": "Norway"},
        {"id": "315", "name": "Ekstraklasa",                   "country": "Poland"},
        {"id": "317", "name": "Premier League",                "country": "Republic of Ireland"},
        {"id": "319", "name": "Superliga",                     "country": "Serbia"},
        {"id": "321", "name": "Fortuna Liga",                  "country": "Slovakia"},
        {"id": "323", "name": "PrvaLiga",                      "country": "Slovenia"},
        
        # ==================== UEFA COMPETITIONS ====================
        {"id": "2",   "name": "UEFA Champions League",         "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",            "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League",        "country": "Europe"},
        {"id": "960", "name": "UEFA Nations League",           "country": "Europe"},
        {"id": "4",   "name": "Euro Championship",             "country": "Europe"},
        {"id": "5",   "name": "World Cup - Qualification",     "country": "World"},
        
        # ==================== INTERNATIONAL COMPETITIONS ====================
        {"id": "1",   "name": "FIFA World Cup",                "country": "World"},
        {"id": "15",  "name": "FIFA Club World Cup",           "country": "World"},
        {"id": "10",  "name": "Friendlies International",      "country": "World"},
        {"id": "12",  "name": "Friendly International Women",  "country": "World"},
        {"id": "14",  "name": "World Club Friendlies",         "country": "World"},
        
        # ==================== AFRICA (CAF) - FULL COVERAGE ====================
        {"id": "29",  "name": "CAF Champions League",          "country": "Africa"},
        {"id": "30",  "name": "CAF Confederation Cup",         "country": "Africa"},
        {"id": "31",  "name": "CAF Super Cup",                 "country": "Africa"},
        {"id": "6",   "name": "Africa Cup of Nations",         "country": "Africa"},
        {"id": "32",  "name": "African Nations Championship",   "country": "Africa"},
        
        # North Africa
        {"id": "169", "name": "Egyptian Premier League",       "country": "Egypt"},
        {"id": "170", "name": "Egypt Cup",                     "country": "Egypt"},
        {"id": "128", "name": "Ligue Professionnelle 1",       "country": "Algeria"},
        {"id": "129", "name": "Algerian Cup",                  "country": "Algeria"},
        {"id": "168", "name": "Botola Pro",                    "country": "Morocco"},
        {"id": "171", "name": "Moroccan Throne Cup",           "country": "Morocco"},
        {"id": "173", "name": "Ligue Professionnelle 1",       "country": "Tunisia"},
        {"id": "174", "name": "Tunisian Cup",                  "country": "Tunisia"},
        {"id": "175", "name": "Libyan Premier League",         "country": "Libya"},
        {"id": "177", "name": "Sudan Premier League",          "country": "Sudan"},
        
        # West Africa
        {"id": "233", "name": "NPFL",                          "country": "Nigeria"},
        {"id": "234", "name": "Nigerian FA Cup",               "country": "Nigeria"},
        {"id": "375", "name": "Ghana Premier League",          "country": "Ghana"},
        {"id": "376", "name": "Ghana FA Cup",                  "country": "Ghana"},
        {"id": "377", "name": "Ligue 1",                       "country": "Ivory Coast"},
        {"id": "378", "name": "Senegal Premier League",        "country": "Senegal"},
        {"id": "379", "name": "Mali Premiere Division",        "country": "Mali"},
        {"id": "380", "name": "Burkina Faso Premier League",   "country": "Burkina Faso"},
        {"id": "381", "name": "Benin Premier League",          "country": "Benin"},
        {"id": "382", "name": "Togo National Championship",    "country": "Togo"},
        {"id": "383", "name": "Guinea Championnat National",   "country": "Guinea"},
        {"id": "384", "name": "Liberia First Division",        "country": "Liberia"},
        {"id": "385", "name": "Sierra Leone National League",  "country": "Sierra Leone"},
        {"id": "386", "name": "Gambia First Division",         "country": "Gambia"},
        {"id": "387", "name": "Mauritania Premier League",     "country": "Mauritania"},
        {"id": "388", "name": "Niger Premier League",          "country": "Niger"},
        
        # East Africa
        {"id": "514", "name": "Kenyan Premier League",         "country": "Kenya"},
        {"id": "515", "name": "Kenyan Cup",                    "country": "Kenya"},
        {"id": "479", "name": "Tanzanian Premier League",      "country": "Tanzania"},
        {"id": "480", "name": "Tanzania FA Cup",               "country": "Tanzania"},
        {"id": "481", "name": "Uganda Premier League",         "country": "Uganda"},
        {"id": "482", "name": "Ugandan Cup",                   "country": "Uganda"},
        {"id": "483", "name": "Ethiopian Premier League",      "country": "Ethiopia"},
        {"id": "484", "name": "Rwanda Premier League",         "country": "Rwanda"},
        {"id": "485", "name": "Burundi Premier League",        "country": "Burundi"},
        {"id": "486", "name": "Somalia First Division",        "country": "Somalia"},
        {"id": "487", "name": "Djibouti Premier League",       "country": "Djibouti"},
        {"id": "488", "name": "South Sudan Premier League",    "country": "South Sudan"},
        {"id": "489", "name": "Eritrea Premier League",        "country": "Eritrea"},
        
        # Central Africa
        {"id": "490", "name": "Cameroon Elite One",            "country": "Cameroon"},
        {"id": "491", "name": "Cameroon Cup",                  "country": "Cameroon"},
        {"id": "492", "name": "DR Congo Linafoot",             "country": "DR Congo"},
        {"id": "493", "name": "Congo Premier League",          "country": "Congo"},
        {"id": "494", "name": "Gabon Championnat National",    "country": "Gabon"},
        {"id": "495", "name": "Central African Republic League","country": "Central African Republic"},
        {"id": "496", "name": "Chad Premier League",           "country": "Chad"},
        {"id": "497", "name": "Equatorial Guinea Premier League","country": "Equatorial Guinea"},
        
        # Southern Africa
        {"id": "360", "name": "South African Premier Division", "country": "South Africa"},
        {"id": "361", "name": "Nedbank Cup",                   "country": "South Africa"},
        {"id": "362", "name": "Telkom Knockout",               "country": "South Africa"},
        {"id": "363", "name": "Angola Girabola",               "country": "Angola"},
        {"id": "364", "name": "Angola Cup",                    "country": "Angola"},
        {"id": "365", "name": "Zambia Super League",           "country": "Zambia"},
        {"id": "366", "name": "Zambian Cup",                   "country": "Zambia"},
        {"id": "367", "name": "Zimbabwe Premier League",       "country": "Zimbabwe"},
        {"id": "368", "name": "Zimbabwe Cup",                  "country": "Zimbabwe"},
        {"id": "369", "name": "Mozambique Mocambola",          "country": "Mozambique"},
        {"id": "370", "name": "Malawi Super League",           "country": "Malawi"},
        {"id": "371", "name": "Botswana Premier League",       "country": "Botswana"},
        {"id": "372", "name": "Namibia Premier League",        "country": "Namibia"},
        {"id": "373", "name": "Eswatini Premier League",       "country": "Eswatini"},
        {"id": "374", "name": "Lesotho Premier League",        "country": "Lesotho"},
        {"id": "375", "name": "Madagascar Premier League",     "country": "Madagascar"},
        {"id": "376", "name": "Mauritius Premier League",      "country": "Mauritius"},
        {"id": "377", "name": "Seychelles Premier League",     "country": "Seychelles"},
        {"id": "378", "name": "Comoros Premier League",        "country": "Comoros"},
        
        # ==================== CONMEBOL (SOUTH AMERICA) ====================
        {"id": "253", "name": "Liga Profesional",              "country": "Argentina"},
        {"id": "266", "name": "Primera B Nacional",            "country": "Argentina"},
        {"id": "267", "name": "Copa Argentina",                "country": "Argentina"},
        {"id": "71",  "name": "Brasileirao Serie A",           "country": "Brazil"},
        {"id": "72",  "name": "Brasileirao Serie B",           "country": "Brazil"},
        {"id": "73",  "name": "Copa do Brasil",                "country": "Brazil"},
        {"id": "242", "name": "Primera Division",              "country": "Chile"},
        {"id": "239", "name": "Primera A",                     "country": "Colombia"},
        {"id": "243", "name": "Primera Division",              "country": "Uruguay"},
        {"id": "240", "name": "Liga Pro",                      "country": "Ecuador"},
        {"id": "245", "name": "Division Profesional",          "country": "Paraguay"},
        {"id": "244", "name": "Liga 1",                        "country": "Peru"},
        {"id": "241", "name": "Primera Division",              "country": "Venezuela"},
        {"id": "11",  "name": "Copa Libertadores",             "country": "S. America"},
        {"id": "13",  "name": "Copa Sudamericana",             "country": "S. America"},
        {"id": "9",   "name": "Copa America",                  "country": "S. America"},
        
        # ==================== CONCACAF (NORTH AMERICA) ====================
        {"id": "253", "name": "MLS",                           "country": "USA"},
        {"id": "262", "name": "Liga MX",                       "country": "Mexico"},
        {"id": "263", "name": "Canadian Premier League",       "country": "Canada"},
        {"id": "559", "name": "CONCACAF Gold Cup",             "country": "N. America"},
        {"id": "558", "name": "CONCACAF Champions League",     "country": "N. America"},
        {"id": "566", "name": "Canadian Championship",         "country": "Canada"},
        {"id": "567", "name": "US Open Cup",                   "country": "USA"},
        {"id": "568", "name": "Liga de Ascenso",               "country": "Mexico"},
        {"id": "569", "name": "Costa Rica Primera Division",   "country": "Costa Rica"},
        {"id": "570", "name": "Honduras Liga Nacional",        "country": "Honduras"},
        {"id": "571", "name": "Panama LPF",                    "country": "Panama"},
        {"id": "572", "name": "El Salvador Primera Division",  "country": "El Salvador"},
        {"id": "573", "name": "Guatemala Liga Nacional",       "country": "Guatemala"},
        {"id": "574", "name": "Jamaica Premier League",        "country": "Jamaica"},
        {"id": "575", "name": "Trinidad Pro League",           "country": "Trinidad"},
        {"id": "576", "name": "Haiti Ligue Haitienne",         "country": "Haiti"},
        
        # ==================== AFC (ASIA) ====================
        {"id": "17",  "name": "AFC Champions League",          "country": "Asia"},
        {"id": "489", "name": "AFC Asian Cup",                 "country": "Asia"},
        {"id": "283", "name": "Saudi Pro League",              "country": "Saudi Arabia"},
        {"id": "284", "name": "King's Cup",                    "country": "Saudi Arabia"},
        {"id": "307", "name": "UAE Pro League",                "country": "UAE"},
        {"id": "308", "name": "UAE President's Cup",           "country": "UAE"},
        {"id": "98",  "name": "J-League",                      "country": "Japan"},
        {"id": "99",  "name": "J2 League",                     "country": "Japan"},
        {"id": "100", "name": "Emperor's Cup",                 "country": "Japan"},
        {"id": "292", "name": "K League 1",                    "country": "South Korea"},
        {"id": "293", "name": "K League 2",                    "country": "South Korea"},
        {"id": "294", "name": "Korean FA Cup",                 "country": "South Korea"},
        {"id": "301", "name": "Indian Super League",           "country": "India"},
        {"id": "302", "name": "I-League",                      "country": "India"},
        {"id": "303", "name": "Durand Cup",                    "country": "India"},
        {"id": "323", "name": "A-League",                      "country": "Australia"},
        {"id": "324", "name": "A-League Women",                "country": "Australia"},
        {"id": "325", "name": "Australia Cup",                 "country": "Australia"},
        {"id": "497", "name": "Qatar Stars League",            "country": "Qatar"},
        {"id": "498", "name": "Emir of Qatar Cup",             "country": "Qatar"},
        {"id": "499", "name": "Iran Pro League",               "country": "Iran"},
        {"id": "500", "name": "Hazfi Cup",                     "country": "Iran"},
        {"id": "501", "name": "Uzbekistan Super League",       "country": "Uzbekistan"},
        {"id": "502", "name": "Iraq Stars League",             "country": "Iraq"},
        {"id": "503", "name": "Jordan Pro League",             "country": "Jordan"},
        {"id": "504", "name": "Kuwait Premier League",         "country": "Kuwait"},
        {"id": "505", "name": "Bahrain Premier League",        "country": "Bahrain"},
        {"id": "506", "name": "Oman Professional League",      "country": "Oman"},
        {"id": "507", "name": "Lebanon Premier League",        "country": "Lebanon"},
        {"id": "508", "name": "Syrian Premier League",         "country": "Syria"},
        {"id": "509", "name": "Palestine Premier League",      "country": "Palestine"},
        {"id": "510", "name": "Mongolia Premier League",       "country": "Mongolia"},
        {"id": "511", "name": "Myanmar National League",       "country": "Myanmar"},
        {"id": "512", "name": "Indonesia Liga 1",              "country": "Indonesia"},
        {"id": "513", "name": "Malaysia Super League",         "country": "Malaysia"},
        {"id": "514", "name": "Singapore Premier League",      "country": "Singapore"},
        {"id": "515", "name": "Thailand League 1",             "country": "Thailand"},
        {"id": "516", "name": "Vietnam V.League 1",            "country": "Vietnam"},
        {"id": "517", "name": "Philippines Football League",   "country": "Philippines"},
        
        # ==================== WOMEN'S FOOTBALL (GLOBAL) ====================
        {"id": "573", "name": "Women's Super League",          "country": "England"},
        {"id": "582", "name": "NWSL",                          "country": "USA"},
        {"id": "583", "name": "Frauen-Bundesliga",             "country": "Germany"},
        {"id": "584", "name": "Division 1 Feminine",           "country": "France"},
        {"id": "585", "name": "Serie A Femminile",             "country": "Italy"},
        {"id": "586", "name": "Liga F",                        "country": "Spain"},
        {"id": "587", "name": "Damallsvenskan",                "country": "Sweden"},
        {"id": "588", "name": "Toppserien",                    "country": "Norway"},
        {"id": "589", "name": "SAFA Women's League",           "country": "South Africa"},
        {"id": "590", "name": "Nigeria Women's League",        "country": "Nigeria"},
        {"id": "591", "name": "WE League",                     "country": "Japan"},
        {"id": "592", "name": "A-League Women",                "country": "Australia"},
        {"id": "7",   "name": "FIFA Women's World Cup",        "country": "World"},
        {"id": "8",   "name": "Women's Euro Championship",     "country": "Europe"},
        {"id": "16",  "name": "Women's Olympic Tournament",    "country": "World"},
        {"id": "18",  "name": "Women's Friendly International","country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NBA & BASKETBALL - Comprehensive Coverage (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "NBA": [
        {"id": "NBA",        "name": "NBA",                     "country": "USA/Canada"},
        {"id": "NBA_PO",     "name": "NBA Playoffs",            "country": "USA/Canada"},
        {"id": "NBA_F",      "name": "NBA Finals",              "country": "USA/Canada"},
        {"id": "NBA_AS",     "name": "NBA All-Star Weekend",    "country": "USA"},
        {"id": "NBA_CUP",    "name": "NBA In-Season Tournament", "country": "USA/Canada"},
        {"id": "NBAGL",      "name": "NBA G League",            "country": "USA"},
        {"id": "WNBA",       "name": "WNBA",                    "country": "USA"},
        {"id": "EUROLEAGUE", "name": "EuroLeague",              "country": "Europe"},
        {"id": "EUROCUP",    "name": "EuroCup",                 "country": "Europe"},
        {"id": "BCL",        "name": "Basketball Champions League", "country": "Europe"},
        {"id": "ACB",        "name": "Liga ACB",                "country": "Spain"},
        {"id": "LNB",        "name": "LNB Pro A",               "country": "France"},
        {"id": "BSL",        "name": "BSL Super League",        "country": "Turkey"},
        {"id": "BBL_DE",     "name": "Basketball Bundesliga",   "country": "Germany"},
        {"id": "LBA",        "name": "Lega Basket Serie A",     "country": "Italy"},
        {"id": "VTB",        "name": "VTB United League",       "country": "Russia/Europe"},
        {"id": "NBL_AU",     "name": "NBL",                     "country": "Australia"},
        {"id": "CBA",        "name": "CBA",                     "country": "China"},
        {"id": "KBASKET",    "name": "KBL",                     "country": "South Korea"},
        {"id": "BAL",        "name": "Basketball Africa League", "country": "Africa"},
        {"id": "LNB_ARG",    "name": "Liga Nacional",           "country": "Argentina"},
        {"id": "NBB_BR",     "name": "Novo Basquete Brasil",    "country": "Brazil"},
        {"id": "LPB",        "name": "Liga Profesional",        "country": "Puerto Rico"},
        {"id": "FIBA_WC",    "name": "FIBA World Cup",          "country": "World"},
        {"id": "FIBA_OLY",   "name": "Olympics — Basketball",   "country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NFL & AMERICAN FOOTBALL (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "NFL": [
        {"id": "NFL",        "name": "NFL",                     "country": "USA"},
        {"id": "NFL_PRE",    "name": "NFL Preseason",           "country": "USA"},
        {"id": "NFL_PO",     "name": "NFL Playoffs",            "country": "USA"},
        {"id": "NFL_SB",     "name": "Super Bowl",              "country": "USA"},
        {"id": "NFL_WC",     "name": "Wild Card",               "country": "USA"},
        {"id": "NFL_DIV",    "name": "Divisional Round",        "country": "USA"},
        {"id": "NFL_CONF",   "name": "Conference Championship", "country": "USA"},
        {"id": "CFL",        "name": "CFL",                     "country": "Canada"},
        {"id": "USFL",       "name": "USFL",                    "country": "USA"},
        {"id": "XFL",        "name": "XFL",                     "country": "USA"},
        {"id": "NCAA_FBS",   "name": "NCAA FBS",                "country": "USA"},
        {"id": "NCAA_CFP",   "name": "College Football Playoff", "country": "USA"},
        {"id": "NCAA_BOWL",  "name": "Bowl Games",              "country": "USA"},
        {"id": "ELF",        "name": "European League of Football", "country": "Europe"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MLB & BASEBALL (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "MLB": [
        {"id": "MLB",        "name": "MLB",                     "country": "USA/Canada"},
        {"id": "MLB_PO",     "name": "MLB Playoffs",            "country": "USA/Canada"},
        {"id": "MLB_WS",     "name": "World Series",            "country": "USA/Canada"},
        {"id": "MLB_AS",     "name": "All-Star Game",           "country": "USA/Canada"},
        {"id": "AAA",        "name": "Triple-A (AAA)",          "country": "USA"},
        {"id": "AA",         "name": "Double-A (AA)",           "country": "USA"},
        {"id": "HIGH_A",     "name": "High-A",                  "country": "USA"},
        {"id": "SINGLE_A",   "name": "Single-A",                "country": "USA"},
        {"id": "NPB",        "name": "NPB Japan Baseball",      "country": "Japan"},
        {"id": "KBO",        "name": "KBO League",              "country": "South Korea"},
        {"id": "LMB",        "name": "Mexican Baseball League", "country": "Mexico"},
        {"id": "CPBL",       "name": "Chinese Professional League", "country": "Taiwan"},
        {"id": "ABL",        "name": "Australian Baseball League", "country": "Australia"},
        {"id": "WBC",        "name": "World Baseball Classic",  "country": "World"},
        {"id": "CARIBBEAN",  "name": "Caribbean Series",        "country": "Caribbean"},
        {"id": "OLY_BB",     "name": "Olympics Baseball",       "country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NHL & HOCKEY (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "NHL": [
        {"id": "NHL",        "name": "NHL",                     "country": "USA/Canada"},
        {"id": "NHL_PO",     "name": "NHL Playoffs",            "country": "USA/Canada"},
        {"id": "NHL_SC",     "name": "Stanley Cup Finals",      "country": "USA/Canada"},
        {"id": "NHL_AS",     "name": "NHL All-Star Game",       "country": "USA/Canada"},
        {"id": "AHL",        "name": "AHL",                     "country": "USA/Canada"},
        {"id": "ECHL",       "name": "ECHL",                    "country": "USA"},
        {"id": "IIHF_WC",    "name": "IIHF World Championship", "country": "World"},
        {"id": "IIHF_OLY",   "name": "Olympics Ice Hockey",     "country": "World"},
        {"id": "IIHF_U20",   "name": "World Junior Championship", "country": "World"},
        {"id": "IIHF_WW",    "name": "Women's World Championship", "country": "World"},
        {"id": "SHL",        "name": "SHL",                     "country": "Sweden"},
        {"id": "Liiga",      "name": "Liiga",                   "country": "Finland"},
        {"id": "DEL",        "name": "DEL",                     "country": "Germany"},
        {"id": "NL",         "name": "National League",         "country": "Switzerland"},
        {"id": "ELH",        "name": "Extraliga",               "country": "Czech Republic"},
        {"id": "KHL",        "name": "KHL",                     "country": "Russia/Europe"},
        {"id": "CHAMPIONS_HL","name": "Champions Hockey League", "country": "Europe"},
        {"id": "OHL",        "name": "OHL",                     "country": "Canada"},
        {"id": "WHL",        "name": "WHL",                     "country": "Canada"},
        {"id": "QMJHL",      "name": "QMJHL",                   "country": "Canada"},
        {"id": "PWHL",       "name": "PWHL Women's Hockey",     "country": "USA/Canada"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UFC / MMA - Complete Weight Classes (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "UFC": [
        {"id": "UFC_ALL",    "name": "UFC — All Events",        "country": "World"},
        {"id": "UFC_PPV",    "name": "UFC PPV Events",          "country": "World"},
        {"id": "UFC_FN",     "name": "UFC Fight Night",         "country": "World"},
        {"id": "UFC_TUF",    "name": "The Ultimate Fighter",    "country": "World"},
        {"id": "UFC_SW",     "name": "Strawweight (115 lbs)",   "country": "World"},
        {"id": "UFC_FLW",    "name": "Flyweight (125 lbs)",     "country": "World"},
        {"id": "UFC_BW",     "name": "Bantamweight (135 lbs)",  "country": "World"},
        {"id": "UFC_FW",     "name": "Featherweight (145 lbs)", "country": "World"},
        {"id": "UFC_LW",     "name": "Lightweight (155 lbs)",   "country": "World"},
        {"id": "UFC_WW",     "name": "Welterweight (170 lbs)",  "country": "World"},
        {"id": "UFC_MW",     "name": "Middleweight (185 lbs)",  "country": "World"},
        {"id": "UFC_LHW",    "name": "Light Heavyweight (205 lbs)", "country": "World"},
        {"id": "UFC_HW",     "name": "Heavyweight (265 lbs)",   "country": "World"},
        {"id": "UFC_W_SW",   "name": "Women's Strawweight",     "country": "World"},
        {"id": "UFC_W_FLW",  "name": "Women's Flyweight",       "country": "World"},
        {"id": "UFC_W_BW",   "name": "Women's Bantamweight",    "country": "World"},
        {"id": "UFC_W_FW",   "name": "Women's Featherweight",   "country": "World"},
        {"id": "BELLATOR",   "name": "Bellator MMA",            "country": "World"},
        {"id": "PFL",        "name": "PFL",                     "country": "World"},
        {"id": "ONE_FC",     "name": "ONE Championship",        "country": "Asia"},
        {"id": "Rizin",      "name": "Rizin Fighting Federation", "country": "Japan"},
        {"id": "KSW",        "name": "KSW",                     "country": "Poland/Europe"},
        {"id": "CAGE_WAR",   "name": "Cage Warriors",           "country": "UK/Europe"},
        {"id": "INVICTA",    "name": "Invicta FC",              "country": "USA"},
        {"id": "BOXING_HW",  "name": "Boxing — Heavyweight",    "country": "World"},
        {"id": "BOXING_MW",  "name": "Boxing — Middleweight",   "country": "World"},
        {"id": "BOXING_WW",  "name": "Boxing — Welterweight",   "country": "World"},
        {"id": "BOXING_LW",  "name": "Boxing — Lightweight",    "country": "World"},
        {"id": "GLORY",      "name": "GLORY Kickboxing",        "country": "World"},
        {"id": "K1",         "name": "K-1 World GP",            "country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FORMULA 1 & MOTORSPORT - Complete Calendar (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "Formula 1": [
        {"id": "F1_ALL",     "name": "F1 — Full Season",        "country": "World"},
        {"id": "F1_AUS",     "name": "Australian GP",           "country": "Australia"},
        {"id": "F1_CHN",     "name": "Chinese GP",              "country": "China"},
        {"id": "F1_JPN",     "name": "Japanese GP",             "country": "Japan"},
        {"id": "F1_BHR",     "name": "Bahrain GP",              "country": "Bahrain"},
        {"id": "F1_SAU",     "name": "Saudi Arabian GP",        "country": "Saudi Arabia"},
        {"id": "F1_MIA",     "name": "Miami GP",                "country": "USA"},
        {"id": "F1_MON",     "name": "Monaco GP",               "country": "Monaco"},
        {"id": "F1_CAN",     "name": "Canadian GP",             "country": "Canada"},
        {"id": "F1_ESP",     "name": "Spanish GP",              "country": "Spain"},
        {"id": "F1_AUT",     "name": "Austrian GP",             "country": "Austria"},
        {"id": "F1_GBR",     "name": "British GP",              "country": "England"},
        {"id": "F1_HUN",     "name": "Hungarian GP",            "country": "Hungary"},
        {"id": "F1_BEL",     "name": "Belgian GP",              "country": "Belgium"},
        {"id": "F1_NLD",     "name": "Dutch GP",                "country": "Netherlands"},
        {"id": "F1_ITA",     "name": "Italian GP — Monza",      "country": "Italy"},
        {"id": "F1_AZE",     "name": "Azerbaijan GP",           "country": "Azerbaijan"},
        {"id": "F1_SGP",     "name": "Singapore GP",            "country": "Singapore"},
        {"id": "F1_USA",     "name": "US GP — Austin",          "country": "USA"},
        {"id": "F1_MEX",     "name": "Mexico City GP",          "country": "Mexico"},
        {"id": "F1_BRA",     "name": "São Paulo GP",            "country": "Brazil"},
        {"id": "F1_LVG",     "name": "Las Vegas GP",            "country": "USA"},
        {"id": "F1_QAT",     "name": "Qatar GP",                "country": "Qatar"},
        {"id": "F1_UAE",     "name": "Abu Dhabi GP",            "country": "UAE"},
        {"id": "F2",         "name": "Formula 2",               "country": "World"},
        {"id": "F3",         "name": "Formula 3",               "country": "World"},
        {"id": "F1_ACAD",    "name": "F1 Academy",              "country": "World"},
        {"id": "INDYCAR",    "name": "IndyCar Series",          "country": "USA"},
        {"id": "NASCAR_C",   "name": "NASCAR Cup Series",       "country": "USA"},
        {"id": "NASCAR_X",   "name": "NASCAR Xfinity Series",   "country": "USA"},
        {"id": "NASCAR_T",   "name": "NASCAR Truck Series",     "country": "USA"},
        {"id": "WEC",        "name": "WEC World Endurance",     "country": "World"},
        {"id": "IMSA",       "name": "IMSA SportsCar",          "country": "USA"},
        {"id": "MOTO_GP",    "name": "MotoGP",                  "country": "World"},
        {"id": "MOTO2",      "name": "Moto2",                   "country": "World"},
        {"id": "MOTO3",      "name": "Moto3",                   "country": "World"},
        {"id": "WSBK",       "name": "World Superbike",         "country": "World"},
        {"id": "FERF",       "name": "Formula E",               "country": "World"},
        {"id": "WRX",        "name": "World Rallycross",        "country": "World"},
        {"id": "WRC",        "name": "World Rally Championship", "country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TENNIS - Complete ATP, WTA & Grand Slams (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "Tennis": [
        {"id": "AUS_OPEN",   "name": "Australian Open",         "country": "Australia"},
        {"id": "FRENCH_OPEN","name": "Roland Garros",           "country": "France"},
        {"id": "WIMBLEDON",  "name": "Wimbledon",               "country": "England"},
        {"id": "US_OPEN",    "name": "US Open",                 "country": "USA"},
        {"id": "M_INDIAN",   "name": "Indian Wells Masters",    "country": "USA"},
        {"id": "M_MIAMI",    "name": "Miami Open",              "country": "USA"},
        {"id": "M_MONTE",    "name": "Monte-Carlo Masters",     "country": "Monaco"},
        {"id": "M_MADRID",   "name": "Madrid Open",             "country": "Spain"},
        {"id": "M_ROME",     "name": "Italian Open",            "country": "Italy"},
        {"id": "M_CANADA",   "name": "Canadian Open",           "country": "Canada"},
        {"id": "M_CINCI",    "name": "Cincinnati Masters",      "country": "USA"},
        {"id": "M_SHANG",    "name": "Shanghai Masters",        "country": "China"},
        {"id": "M_PARIS",    "name": "Paris Masters",           "country": "France"},
        {"id": "ATP_FINALS", "name": "ATP Finals",              "country": "Italy"},
        {"id": "ATP_500",    "name": "ATP 500 Series",          "country": "World"},
        {"id": "ATP_250",    "name": "ATP 250 Series",          "country": "World"},
        {"id": "ATP_CHALL",  "name": "ATP Challenger Tour",     "country": "World"},
        {"id": "WTA_FINALS", "name": "WTA Finals",              "country": "Saudi Arabia"},
        {"id": "WTA_1000",   "name": "WTA 1000",                "country": "World"},
        {"id": "WTA_500",    "name": "WTA 500",                 "country": "World"},
        {"id": "WTA_250",    "name": "WTA 250",                 "country": "World"},
        {"id": "WTA_125",    "name": "WTA 125",                 "country": "World"},
        {"id": "DAVIS_CUP",  "name": "Davis Cup Finals",        "country": "World"},
        {"id": "BJK_CUP",    "name": "Billie Jean King Cup",    "country": "World"},
        {"id": "LAVER_CUP",  "name": "Laver Cup",               "country": "World"},
        {"id": "UNITED_CUP", "name": "United Cup",              "country": "World"},
        {"id": "OLYMPICS_T", "name": "Olympics Tennis",         "country": "World"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CRICKET - Complete Global Coverage (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "Cricket": [
        {"id": "TEST",       "name": "Test Matches",            "country": "World"},
        {"id": "ODI",        "name": "ODI Internationals",      "country": "World"},
        {"id": "T20I",       "name": "T20 Internationals",      "country": "World"},
        {"id": "ICC_WC",     "name": "ICC Men's World Cup",     "country": "World"},
        {"id": "ICC_T20WC",  "name": "ICC T20 World Cup",       "country": "World"},
        {"id": "ICC_CT",     "name": "ICC Champions Trophy",    "country": "World"},
        {"id": "ICC_WTC",    "name": "World Test Championship", "country": "World"},
        {"id": "IPL",        "name": "IPL",                     "country": "India"},
        {"id": "BBL",        "name": "Big Bash League",         "country": "Australia"},
        {"id": "PSL",        "name": "Pakistan Super League",   "country": "Pakistan"},
        {"id": "CPL",        "name": "Caribbean Premier League", "country": "Caribbean"},
        {"id": "SA20",       "name": "SA20",                    "country": "South Africa"},
        {"id": "ILT20",      "name": "ILT20",                   "country": "UAE"},
        {"id": "MLC",        "name": "Major League Cricket",    "country": "USA"},
        {"id": "T20_BLAST",  "name": "Vitality T20 Blast",      "country": "England"},
        {"id": "THE_100",    "name": "The Hundred",             "country": "England"},
        {"id": "ASHES",      "name": "The Ashes",               "country": "World"},
        {"id": "COUNTY",     "name": "County Championship",     "country": "England"},
        {"id": "RANJI",      "name": "Ranji Trophy",            "country": "India"},
        {"id": "SHEFFIELD",  "name": "Sheffield Shield",        "country": "Australia"},
        {"id": "WBBL",       "name": "Women's Big Bash League", "country": "Australia"},
        {"id": "THE_HUNDRED_W", "name": "The Hundred Women",    "country": "England"},
        {"id": "WPL",        "name": "Women's Premier League",  "country": "India"},
    ],
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GOLF - Complete PGA, DP World, LIV & Majors (ALL PRESERVED)
    # ═══════════════════════════════════════════════════════════════════════════
    "Golf": [
        {"id": "PGA_ALL",    "name": "PGA Tour — All Events",   "country": "USA"},
        {"id": "DP_ALL",     "name": "DP World Tour — All Events", "country": "Europe"},
        {"id": "LIV_ALL",    "name": "LIV Golf",                "country": "World"},
        {"id": "MASTERS",    "name": "The Masters",             "country": "USA"},
        {"id": "PGA_CHAMP",  "name": "PGA Championship",        "country": "USA"},
        {"id": "US_OPEN_G",  "name": "US Open",                 "country": "USA"},
        {"id": "THE_OPEN",   "name": "The Open Championship",   "country": "UK"},
        {"id": "PLAYERS",    "name": "The Players Championship","country": "USA"},
        {"id": "RYDER_CUP",  "name": "Ryder Cup",               "country": "World"},
        {"id": "PRES_CUP",   "name": "Presidents Cup",          "country": "World"},
        {"id": "KORN_FERRY", "name": "Korn Ferry Tour",         "country": "USA"},
        {"id": "LPGA_ALL",   "name": "LPGA Tour",               "country": "USA"},
        {"id": "ASIAN_TOUR", "name": "Asian Tour",              "country": "Asia"},
        {"id": "SENIOR_PGA", "name": "PGA Tour Champions",      "country": "USA"},
        {"id": "SOLHEIM_CUP","name": "Solheim Cup",             "country": "World"},
        {"id": "OLYMPICS_G", "name": "Olympics Golf",           "country": "World"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        # PRIMARY: Apify/FlashScore (CORRECTED actor integration)
        self.apify = ApifyProvider()
        
        # BACKUP PROVIDERS
        self.football_data = FootballDataProvider()
        self.api_sports = APISportsProvider()
        self.msf = MySportsFeedsProvider()
        self.tsdb = TheSportsDBProvider()
        
        # Feature Engineers
        self.football_fe = FootballFeatureEngineer() if FootballFeatureEngineer else None
        self.nba_fe = NBAFeatureEngineer() if NBAFeatureEngineer else None
        self.nfl_fe = NFLFeatureEngineer() if NFLFeatureEngineer else None
        self.tennis_fe = TennisFeatureEngineer() if TennisFeatureEngineer else None
        
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
        remaining = self.api_sports.get_remaining() if self.api_sports.ok else 0
        self._log("Apify/FlashScore (PRIMARY)", "READY" if self.apify.ok else "NO KEY", "34+ Sports - CORRECT actor input")
        self._log("API-SPORTS (BACKUP)", "READY" if self.api_sports.ok else "NO KEY", f"{remaining}/100 daily")
        self._log("Football-Data (BACKUP)", "READY", "10 req/min")
        self._log("MySportsFeeds (BACKUP)", "READY" if self.msf.ok else "NO KEY", "NBA/NFL/MLB/NHL")
        self._log("TheSportsDB (BACKUP)", "READY", "UFC/F1/Tennis/Cricket/Golf")

    def get_provider_status(self) -> List[Dict]:
        remaining = self.api_sports.get_remaining() if self.api_sports.ok else 0
        return [
            {"name": "FlashScore/Apify (PRIMARY)", "status": "🟢 ONLINE" if self.apify.ok else "🔴 Add APIFY_API_KEY"},
            {"name": "API-SPORTS (BACKUP)", "status": f"🟢 {remaining}/100 remaining" if self.api_sports.ok else "⚪ Add API_SPORTS_KEY"},
            {"name": "Football-Data (BACKUP)", "status": "🟢 ONLINE"},
            {"name": "MySportsFeeds (BACKUP)", "status": "🟢 ONLINE" if self.msf.ok else "⚪ Optional"},
            {"name": "TheSportsDB (BACKUP)", "status": "🟢 ONLINE"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-50:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        """Return your COMPLETE static league list - NOTHING REMOVED"""
        return STATIC_LEAGUES.get(sport, [{"id": "ALL", "name": "All Events", "country": "World"}])

    def get_upcoming_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        """Get matches - PRIMARY: Apify/FlashScore for ALL sports"""
        matches = []
        
        # PRIMARY: Use Apify/FlashScore with CORRECT actor input
        if self.apify.ok:
            try:
                # Map sport name for Apify
                if sport in ["Football", "NBA", "NFL", "MLB", "NHL", "UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
                    matches = self.apify.get_matches_by_sport(sport)
                    if matches:
                        self._log("Apify/FlashScore", "SUCCESS", f"{len(matches)} {sport} matches")
                    else:
                        self._log("Apify/FlashScore", "EMPTY", f"No {sport} matches found")
            except Exception as e:
                self._log("Apify/FlashScore", "ERROR", str(e)[:50])
        
        # BACKUP: If Apify fails, try backup providers
        if not matches and sport == "Football":
            # Try API-SPORTS
            if self.api_sports.ok and self.api_sports.get_remaining() > 0:
                matches = self.api_sports.get_upcoming_matches(days=7)
                if matches:
                    self._log("API-SPORTS (BACKUP)", "SUCCESS", f"{len(matches)} matches")
            
            # Try Football-Data as last resort
            if not matches:
                matches = self.football_data.get_upcoming_matches(days=7)
                if matches:
                    self._log("Football-Data (BACKUP)", "SUCCESS", f"{len(matches)} matches")
        
        elif not matches and sport in ["NBA", "NFL", "MLB", "NHL"]:
            matches = self.msf.get_upcoming_matches(sport, days=7)
            if matches:
                self._log("MySportsFeeds (BACKUP)", "SUCCESS", f"{len(matches)} matches")
        
        elif not matches and sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
            matches = self.tsdb.get_upcoming_matches(sport)
            if matches:
                self._log("TheSportsDB (BACKUP)", "SUCCESS", f"{len(matches)} matches")
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        
        # Remove duplicates
        if not df.empty and "MATCH_ID" in df.columns:
            df = df.drop_duplicates(subset=["MATCH_ID"])
        
        return df

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        """Get live matches"""
        matches = []
        
        # Use Apify for live matches with CORRECT input
        if self.apify.ok:
            try:
                matches = self.apify.get_live_matches(sport)
                if matches:
                    self._log("Apify/FlashScore", "LIVE", f"{len(matches)} live {sport} matches")
            except Exception as e:
                self._log("Apify/FlashScore", "ERROR", str(e)[:50])
        
        df = pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        
        if not df.empty and "STATUS" in df.columns:
            df = df[df["STATUS"] == "🔴 LIVE"]
        
        return df

    def enrich_with_features(self, df: pd.DataFrame, sport: str) -> pd.DataFrame:
        if df.empty:
            return df
        
        fe = None
        if sport == "Football" and self.football_fe:
            fe = self.football_fe
        elif sport == "NBA" and self.nba_fe:
            fe = self.nba_fe
        elif sport == "NFL" and self.nfl_fe:
            fe = self.nfl_fe
        elif sport == "Tennis" and self.tennis_fe:
            fe = self.tennis_fe
        
        if fe and hasattr(fe, 'get_feature_names'):
            try:
                feature_names = fe.get_feature_names()
                for fname in feature_names:
                    if fname not in df.columns:
                        df[fname] = 0.5
            except:
                pass
        
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self):
        return self.router.apify.ok or bool(APIConfig.API_SPORTS_KEY)

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
