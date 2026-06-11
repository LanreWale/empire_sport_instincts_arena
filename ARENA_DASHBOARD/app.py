"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer
PRIMARY SOURCE: Apify/FlashScore (Covers ALL Sports)
BACKUP: API-SPORTS (Football only, 100/day)
"""

import os
import time
import hashlib
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
class APIConfig:
    @staticmethod
    def _e(k, d=""): return str(os.getenv(k, d)).strip()

    # Primary: Apify/FlashScore
    APIFY_API_KEY     = _e("APIFY_API_KEY")
    
    # Backup: API-SPORTS (Football only)
    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"
    
    TTL_LIVE     = 30
    TTL_UPCOMING = 600
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
    sport:        str                = "Football"
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
            "MATCH_ID":   self.match_id,
            "TIME":       t or "TBD",
            "LEAGUE":     self.league,
            "LEAGUE_ID":  self.league_id,
            "HOME_TEAM":  self.home_team,
            "AWAY_TEAM":  self.away_team,
            "MATCH":      f"{self.home_team} vs {self.away_team}",
            "STATUS":     disp,
            "SCORE":      f"{self.home_score}-{self.away_score}"
                          if self.home_score is not None else "vs",
            "PROVIDER":   self.provider,
            "SPORT":      self.sport,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# APIFY / FLASHSCORE PROVIDER (PRIMARY FOR ALL SPORTS)
# ═══════════════════════════════════════════════════════════════════════════════
class ApifyProvider:
    """Primary data provider - FlashScore covers ALL sports"""
    
    # FlashScore URL mapping for ALL sports (based on actual FlashScore URLs)
    SPORT_URLS = {
        "Football":     "https://www.flashscore.com/football/",
        "NBA":          "https://www.flashscore.com/basketball/nba/",
        "NFL":          "https://www.flashscore.com/american-football/nfl/",
        "MLB":          "https://www.flashscore.com/baseball/mlb/",
        "NHL":          "https://www.flashscore.com/hockey/nhl/",
        "UFC":          "https://www.flashscore.com/mma/ufc/",
        "Formula 1":    "https://www.flashscore.com/motorsport/formula-1/",
        "Tennis":       "https://www.flashscore.com/tennis/",
        "Cricket":      "https://www.flashscore.com/cricket/",
        "Golf":         "https://www.flashscore.com/golf/",
        "Volleyball":   "https://www.flashscore.com/volleyball/",
        "Handball":     "https://www.flashscore.com/handball/",
        "Rugby":        "https://www.flashscore.com/rugby-union/",
        "Darts":        "https://www.flashscore.com/darts/",
        "Snooker":      "https://www.flashscore.com/snooker/",
        "Table Tennis": "https://www.flashscore.com/table-tennis/",
        "Esports":      "https://www.flashscore.com/esports/",
        "Badminton":    "https://www.flashscore.com/badminton/",
        "Bandy":        "https://www.flashscore.com/bandy/",
        "Baseball":     "https://www.flashscore.com/baseball/",
        "Beach Soccer": "https://www.flashscore.com/beach-soccer/",
        "Basketball":   "https://www.flashscore.com/basketball/",
        "Bowls":        "https://www.flashscore.com/bowls/",
        "Boxing":       "https://www.flashscore.com/boxing/",
        "Cycling":      "https://www.flashscore.com/cycling/",
        "Floorball":    "https://www.flashscore.com/floorball/",
        "Futsal":       "https://www.flashscore.com/futsal/",
        "Hockey":       "https://www.flashscore.com/hockey/",
        "Horse Racing": "https://www.flashscore.com/horse-racing/",
        "Ice Hockey":   "https://www.flashscore.com/ice-hockey/",
        "MMA":          "https://www.flashscore.com/mma/",
        "Motorsport":   "https://www.flashscore.com/motorsport/",
        "Netball":      "https://www.flashscore.com/netball/",
        "Pesapallo":    "https://www.flashscore.com/pesapallo/",
        "Pool":         "https://www.flashscore.com/pool/",
        "Rugby League": "https://www.flashscore.com/rugby-league/",
        "Soccer":       "https://www.flashscore.com/soccer/",
        "Speedway":     "https://www.flashscore.com/speedway/",
        "Trotting":     "https://www.flashscore.com/trotting/",
        "Volleyball":   "https://www.flashscore.com/volleyball/",
        "Water Polo":   "https://www.flashscore.com/water-polo/",
        "Winter Sports":"https://www.flashscore.com/winter-sports/",
    }
    
    # Specific competition URLs for friendlies and special competitions
    COMPETITION_URLS = {
        "Friendly International": "https://www.flashscore.com/football/world/friendly-international/",
        "Club Friendly":          "https://www.flashscore.com/football/world/club-friendly/",
        "World Cup":              "https://www.flashscore.com/football/world/world-cup/",
        "Champions League":       "https://www.flashscore.com/football/europe/champions-league/",
        "Europa League":          "https://www.flashscore.com/football/europe/europa-league/",
        "Premier League":         "https://www.flashscore.com/football/england/premier-league/",
        "La Liga":                "https://www.flashscore.com/football/spain/laliga/",
        "Serie A":                "https://www.flashscore.com/football/italy/serie-a/",
        "Bundesliga":             "https://www.flashscore.com/football/germany/bundesliga/",
        "Ligue 1":                "https://www.flashscore.com/football/france/ligue-1/",
    }

    def __init__(self):
        self.api_key = APIConfig.APIFY_API_KEY
        self.actor_id = "crawlerbros~flashscore-scraper"
        self._cache: Dict[str, Any] = {}
        self.request_count = 0

    @property
    def ok(self):
        return bool(self.api_key)

    def _call_actor(self, url: str, timeout: int = 60) -> Optional[List]:
        """Run Apify actor and return results"""
        if not self.api_key:
            logger.warning("Apify: No API key")
            return None
        
        run_url = f"https://api.apify.com/v2/acts/{self.actor_id}/runs"
        payload = {
            "startUrls": [{"url": url}],
            "maxItems": 300,
            "proxyConfiguration": {"useApifyProxy": True}
        }
        
        try:
            # Start the run
            start_response = requests.post(
                run_url,
                params={"token": self.api_key},
                json=payload,
                timeout=30
            )
            
            if start_response.status_code != 201:
                logger.error(f"Apify start failed: {start_response.status_code}")
                return None
            
            run_data = start_response.json()
            run_id = run_data.get('data', {}).get('id')
            
            if not run_id:
                logger.error("Apify: No run ID returned")
                return None
            
            # Wait for completion
            start_time = time.time()
            while time.time() - start_time < timeout:
                status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
                status_response = requests.get(status_url, params={"token": self.api_key})
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    run_status = status_data.get('data', {}).get('status')
                    
                    if run_status == 'SUCCEEDED':
                        dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"
                        items_response = requests.get(dataset_url, params={"token": self.api_key, "limit": 500})
                        
                        if items_response.status_code == 200:
                            items = items_response.json()
                            logger.info(f"Apify: Retrieved {len(items)} items from {url}")
                            return items
                        return None
                    
                    elif run_status in ['FAILED', 'TIMED-OUT', 'ABORTED']:
                        logger.error(f"Apify run {run_status}")
                        return None
                
                time.sleep(3)
            
            logger.error(f"Apify timeout after {timeout}s")
            return None
            
        except Exception as e:
            logger.error(f"Apify error: {e}")
            return None

    def _ck(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get(self, key: str, ttl: int) -> Optional[Any]:
        e = self._cache.get(key)
        return e["v"] if e and time.time() - e["t"] < ttl else None

    def _set(self, key: str, val: Any):
        self._cache[key] = {"v": val, "t": time.time()}

    def get_matches_by_url(self, url: str, sport: str = "Football", cache_ttl: int = None) -> List[Match]:
        """Fetch matches from a specific FlashScore URL"""
        if cache_ttl is None:
            cache_ttl = APIConfig.TTL_UPCOMING
        
        cache_key = self._ck("url", url)
        cached = self._get(cache_key, cache_ttl)
        if cached is not None:
            return cached
        
        items = self._call_actor(url, 60)
        if not items:
            return []
        
        matches = self._parse_items(items, sport)
        self._set(cache_key, matches)
        return matches

    def get_matches_by_sport(self, sport: str, days: int = 7) -> List[Match]:
        """Fetch matches for a sport using the main sport URL"""
        url = self.SPORT_URLS.get(sport)
        if not url:
            logger.warning(f"No URL mapping for sport: {sport}")
            return []
        
        return self.get_matches_by_url(url, sport)

    def get_matches_by_competition(self, competition_name: str, sport: str = "Football") -> List[Match]:
        """Fetch matches for a specific competition (e.g., Friendlies)"""
        url = self.COMPETITION_URLS.get(competition_name)
        if not url:
            return []
        
        return self.get_matches_by_url(url, sport)

    def _parse_items(self, items: List, sport: str) -> List[Match]:
        """Parse Apify output into Match objects"""
        matches = []
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Extract team names
            home = (item.get('homeTeam') or item.get('home') or 
                   item.get('team1') or item.get('homeName') or '')
            away = (item.get('awayTeam') or item.get('away') or 
                   item.get('team2') or item.get('awayName') or '')
            
            # Handle nested objects
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
            else:
                league = str(tournament) if tournament else sport
            
            # Parse status
            status_raw = str(item.get('status') or item.get('matchStatus') or 
                            item.get('statusText') or 'SCHEDULED').lower()
            
            is_live = any(x in status_raw for x in ['live', 'in progress', '1st', '2nd', 'half', 'period', 'quarter'])
            is_finished = any(x in status_raw for x in ['finished', 'ft', 'final', 'ended', 'complete'])
            
            if is_live:
                status = "LIVE"
            elif is_finished:
                status = "FINISHED"
            else:
                status = "SCHEDULED"
            
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
                home_score = item.get('homeScore') or item.get('goalsHome') or item.get('scoreHome')
            if away_score is None:
                away_score = item.get('awayScore') or item.get('goalsAway') or item.get('scoreAway')
            
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
                            # Handle various date formats
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
                league_id=str(item.get('tournamentId', item.get('leagueId', ''))),
                home_team=home[:50],
                away_team=away[:50],
                home_score=home_score,
                away_score=away_score,
                status=status,
                minute=item.get('minute'),
                start_time=start_time,
                sport=sport,
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
# API-SPORTS PROVIDER (BACKUP - Football only)
# ═══════════════════════════════════════════════════════════════════════════════
class APISportsProvider:
    def __init__(self):
        self.api_key = APIConfig.API_SPORTS_KEY
        self.headers = {"x-apisports-key": self.api_key} if self.api_key else {}
        self._cache: Dict[str, Any] = {}
        self.request_count = 0
        self.last_reset = datetime.now()

    @property
    def ok(self):
        return bool(self.api_key)

    def _req(self, url: str, params: Dict = None) -> Optional[Any]:
        if not self._check_limit():
            return None
        for attempt in range(APIConfig.RETRIES):
            try:
                r = requests.get(url, headers=self.headers, params=params or {}, timeout=APIConfig.TIMEOUT)
                if r.status_code == 200:
                    self.request_count += 1
                    return r.json()
                return None
            except Exception as e:
                logger.error(f"API-SPORTS error: {e}")
            time.sleep(0.5 * (attempt + 1))
        return None

    def _check_limit(self):
        now = datetime.now()
        if now.day != self.last_reset.day:
            self.request_count = 0
            self.last_reset = now
        return self.request_count < 100


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LIST - ALL COMPETITIONS WITH FLASHSCORE URLs
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Football": [
        {"id": "ALL",                 "name": "All Competitions",                      "url": None},
        {"id": "FRIENDLY_INTL",       "name": "Friendly International",                "url": "https://www.flashscore.com/football/world/friendly-international/"},
        {"id": "CLUB_FRIENDLY",       "name": "Club Friendly",                         "url": "https://www.flashscore.com/football/world/club-friendly/"},
        {"id": "WC",                  "name": "World Cup",                             "url": "https://www.flashscore.com/football/world/world-cup/"},
        {"id": "UCL",                 "name": "UEFA Champions League",                 "url": "https://www.flashscore.com/football/europe/champions-league/"},
        {"id": "UEL",                 "name": "UEFA Europa League",                    "url": "https://www.flashscore.com/football/europe/europa-league/"},
        {"id": "PL",                  "name": "Premier League",                        "url": "https://www.flashscore.com/football/england/premier-league/"},
        {"id": "LALIGA",              "name": "La Liga",                               "url": "https://www.flashscore.com/football/spain/laliga/"},
        {"id": "SERIEA",              "name": "Serie A",                               "url": "https://www.flashscore.com/football/italy/serie-a/"},
        {"id": "BUNDESLIGA",          "name": "Bundesliga",                            "url": "https://www.flashscore.com/football/germany/bundesliga/"},
        {"id": "LIGUE1",              "name": "Ligue 1",                               "url": "https://www.flashscore.com/football/france/ligue-1/"},
        {"id": "EREDIVISIE",          "name": "Eredivisie",                            "url": "https://www.flashscore.com/football/netherlands/eredivisie/"},
        {"id": "PRIMEIRA",            "name": "Primeira Liga",                         "url": "https://www.flashscore.com/football/portugal/primeira-liga/"},
        {"id": "MLS",                 "name": "MLS",                                   "url": "https://www.flashscore.com/football/usa/mls/"},
        {"id": "LIGAMX",              "name": "Liga MX",                               "url": "https://www.flashscore.com/football/mexico/liga-mx/"},
        {"id": "AFCON",               "name": "Africa Cup of Nations",                 "url": "https://www.flashscore.com/football/africa/africa-cup-of-nations/"},
        {"id": "COPA",                "name": "Copa America",                          "url": "https://www.flashscore.com/football/south-america/copa-america/"},
        {"id": "EURO",                "name": "Euro Championship",                     "url": "https://www.flashscore.com/football/europe/european-championship/"},
        {"id": "AFC",                 "name": "AFC Champions League",                  "url": "https://www.flashscore.com/football/asia/afc-champions-league/"},
        {"id": "CAF",                 "name": "CAF Champions League",                  "url": "https://www.flashscore.com/football/africa/caf-champions-league/"},
        {"id": "CONCACAF",            "name": "CONCACAF Champions League",             "url": "https://www.flashscore.com/football/nc-america/concacaf-champions-league/"},
    ],
    "NBA": [
        {"id": "ALL",  "name": "All Competitions",  "url": None},
        {"id": "NBA",  "name": "NBA",               "url": "https://www.flashscore.com/basketball/nba/"},
        {"id": "WNBA", "name": "WNBA",              "url": "https://www.flashscore.com/basketball/wnba/"},
    ],
    "NFL": [
        {"id": "ALL", "name": "All Competitions", "url": None},
        {"id": "NFL", "name": "NFL",              "url": "https://www.flashscore.com/american-football/nfl/"},
    ],
    "MLB": [
        {"id": "ALL", "name": "All Competitions", "url": None},
        {"id": "MLB", "name": "MLB",              "url": "https://www.flashscore.com/baseball/mlb/"},
    ],
    "NHL": [
        {"id": "ALL", "name": "All Competitions", "url": None},
        {"id": "NHL", "name": "NHL",              "url": "https://www.flashscore.com/hockey/nhl/"},
    ],
    "UFC": [
        {"id": "ALL",  "name": "All Events",      "url": None},
        {"id": "UFC",  "name": "UFC",             "url": "https://www.flashscore.com/mma/ufc/"},
    ],
    "Formula 1": [
        {"id": "ALL", "name": "All Events",       "url": None},
        {"id": "F1",  "name": "Formula 1",        "url": "https://www.flashscore.com/motorsport/formula-1/"},
    ],
    "Tennis": [
        {"id": "ALL",      "name": "All Tournaments", "url": None},
        {"id": "ATP",      "name": "ATP Tour",        "url": "https://www.flashscore.com/tennis/atp-tour/"},
        {"id": "WTA",      "name": "WTA Tour",        "url": "https://www.flashscore.com/tennis/wta-tour/"},
        {"id": "GRAND_SLAM","name": "Grand Slams",    "url": "https://www.flashscore.com/tennis/grand-slam/"},
    ],
    "Cricket": [
        {"id": "ALL", "name": "All Events", "url": None},
        {"id": "ICC", "name": "ICC Events", "url": "https://www.flashscore.com/cricket/"},
    ],
    "Golf": [
        {"id": "ALL", "name": "All Events", "url": None},
        {"id": "PGA", "name": "PGA Tour",   "url": "https://www.flashscore.com/golf/pga-tour/"},
    ],
    "Volleyball": [
        {"id": "ALL", "name": "All Events", "url": None},
        {"id": "VB",  "name": "Volleyball", "url": "https://www.flashscore.com/volleyball/"},
    ],
    "Handball": [
        {"id": "ALL", "name": "All Events", "url": None},
        {"id": "HB",  "name": "Handball",   "url": "https://www.flashscore.com/handball/"},
    ],
    "Rugby": [
        {"id": "ALL", "name": "All Events", "url": None},
        {"id": "RU",  "name": "Rugby Union","url": "https://www.flashscore.com/rugby-union/"},
    ],
    "Darts": [
        {"id": "ALL",   "name": "All Events", "url": None},
        {"id": "PDC",   "name": "PDC",        "url": "https://www.flashscore.com/darts/"},
    ],
    "Snooker": [
        {"id": "ALL",     "name": "All Events", "url": None},
        {"id": "SNOOKER", "name": "Snooker",    "url": "https://www.flashscore.com/snooker/"},
    ],
    "Table Tennis": [
        {"id": "ALL", "name": "All Events",    "url": None},
        {"id": "TT",  "name": "Table Tennis", "url": "https://www.flashscore.com/table-tennis/"},
    ],
    "Esports": [
        {"id": "ALL",    "name": "All Events", "url": None},
        {"id": "ESPORTS","name": "Esports",    "url": "https://www.flashscore.com/esports/"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        self.apify = ApifyProvider()
        self.api_sports = APISportsProvider()  # Backup only
        self.log: List[Dict] = []

    def _log(self, provider, status, detail):
        self.log.append({
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": provider,
            "STATUS": status,
            "DETAIL": str(detail)[:80]
        })

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "FlashScore/Apify (PRIMARY - All Sports)", "status": "🟢 ONLINE" if self.apify.ok else "🔴 Add APIFY_API_KEY"},
            {"name": "API-SPORTS (BACKUP - Football)", "status": "🟢 ONLINE" if self.api_sports.ok else "⚪ Optional"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-50:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        """Return static league list for UI dropdown"""
        return STATIC_LEAGUES.get(sport, [{"id": "ALL", "name": "All Events", "url": None}])

    def get_upcoming_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        """Get matches - PRIMARY: Apify/FlashScore for ALL sports"""
        matches = []
        
        if sport == "Football":
            # For football, use competition-specific URLs if selected
            if league_id and league_id != "ALL":
                # Find the selected competition
                selected_comp = None
                for comp in STATIC_LEAGUES.get("Football", []):
                    if comp.get("id") == league_id:
                        selected_comp = comp
                        break
                
                if selected_comp and selected_comp.get("url"):
                    # Fetch from specific competition URL
                    url = selected_comp.get("url")
                    self._log("Apify/FlashScore", "FETCHING", f"Competition: {selected_comp.get('name')}")
                    matches = self.apify.get_matches_by_url(url, sport)
                else:
                    # Fallback to main sport URL
                    matches = self.apify.get_matches_by_sport(sport, days=14)
            else:
                # Fetch all football matches
                matches = self.apify.get_matches_by_sport(sport, days=14)
        
        else:
            # For all other sports, use the main sport URL
            matches = self.apify.get_matches_by_sport(sport, days=14)
        
        if matches:
            self._log("Apify/FlashScore", "SUCCESS", f"{len(matches)} {sport} matches")
        else:
            self._log("Apify/FlashScore", "EMPTY", f"No {sport} matches found")
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()
        
        # Remove duplicates
        if not df.empty and "MATCH_ID" in df.columns:
            df = df.drop_duplicates(subset=["MATCH_ID"])
        
        return df

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        """Get live matches - filtered from upcoming"""
        df = self.get_upcoming_matches(sport, league_id)
        if not df.empty:
            df = df[df["STATUS"] == "🔴 LIVE"]
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self):
        return self.router.apify.ok

    def get_connection_log_df(self):
        return self.router.get_connection_log_df()

    def get_all_leagues(self, s: str):
        return self.router.get_all_leagues(s)

    def get_live_matches_df(self, s: str, lid: str = None):
        return self.router.get_live_matches(s, lid)

    def get_upcoming_matches_df(self, s: str, lid: str = None):
        return self.router.get_upcoming_matches(s, lid)


__all__ = ["APIConfig", "EmpireDashboardData"]
