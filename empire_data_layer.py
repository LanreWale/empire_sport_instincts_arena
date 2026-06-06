"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer
COST-EFFECTIVE MULTI-PROVIDER STRATEGY (All FREE tiers):
  1. API-SPORTS (100/day free)      — Soccer live/fixtures (PRIMARY)
  2. Football-Data.org (10/min free) — Soccer backup
  3. TheSportsDB (FREE unlimited)    — UFC/F1/Tennis/Cricket/Golf
  4. MySportsFeeds (FREE tier)       — NBA/NFL/MLB/NHL
  5. Apify/FlashScore (PAID)         — DISABLED (monthly limit exceeded)
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

    # PRIMARY FREE APIs - Already configured in Render
    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"
    
    # BACKUP FREE APIs
    FOOTBALL_DATA_KEY = _e("FOOTBALL_DATA_KEY")
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    
    # COMPLETELY FREE APIs (No limits)
    TSDB_KEY          = _e("TheSportDB_API_key", "3")
    TSDB_URL          = "https://www.thesportsdb.com/api/v1/json"
    
    # FREE TIER US Sports
    MSF_KEY           = _e("MYSPORTSFEEDS_KEY")
    MSF_PASS          = _e("MYSPORTSFEEDS_PASSWORD")
    MSF_URL           = "https://api.mysportsfeeds.com/v2.1/pull"
    
    # PAID API - DISABLED (monthly limit exceeded)
    APIFY_API_TOKEN    = _e("APIFY_API_KEY")
    USE_APIFY = False  # Set to True only if you upgrade to paid plan

    TTL_LIVE     = 30      # Cache live matches for 30 seconds
    TTL_UPCOMING = 600     # Cache upcoming matches for 10 minutes
    TTL_LEAGUES  = 86400   # Cache leagues for 24 hours
    TIMEOUT      = 12
    RETRIES      = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LISTS (Zero API calls - instantly available)
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Soccer": [
        {"id": "39",  "name": "Premier League",            "country": "England"},
        {"id": "40",  "name": "Championship",              "country": "England"},
        {"id": "140", "name": "La Liga",                   "country": "Spain"},
        {"id": "135", "name": "Serie A",                   "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                   "country": "France"},
        {"id": "88",  "name": "Eredivisie",                "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",             "country": "Portugal"},
        {"id": "2",   "name": "UEFA Champions League",     "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",        "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League",    "country": "Europe"},
        {"id": "253", "name": "MLS",                       "country": "USA"},
        {"id": "71",  "name": "Brasileirao Serie A",       "country": "Brazil"},
        {"id": "283", "name": "Saudi Pro League",          "country": "Saudi Arabia"},
        {"id": "98",  "name": "J-League",                  "country": "Japan"},
        {"id": "1",   "name": "FIFA World Cup",            "country": "World"},
        {"id": "4",   "name": "Euro Championship",         "country": "Europe"},
    ],
    "NBA": [
        {"id": "NBA",        "name": "NBA",                 "country": "USA/Canada"},
        {"id": "EUROLEAGUE", "name": "EuroLeague",          "country": "Europe"},
        {"id": "WNBA",       "name": "WNBA",                "country": "USA"},
    ],
    "NFL": [
        {"id": "NFL",        "name": "NFL",                 "country": "USA"},
        {"id": "CFL",        "name": "CFL",                 "country": "Canada"},
    ],
    "MLB": [
        {"id": "MLB",        "name": "MLB",                 "country": "USA/Canada"},
        {"id": "NPB",        "name": "NPB Japan",           "country": "Japan"},
    ],
    "NHL": [
        {"id": "NHL",        "name": "NHL",                 "country": "USA/Canada"},
        {"id": "KHL",        "name": "KHL",                 "country": "Russia/Europe"},
    ],
    "UFC": [
        {"id": "UFC_ALL",    "name": "UFC — All Events",    "country": "World"},
        {"id": "BELLATOR",   "name": "Bellator MMA",        "country": "World"},
    ],
    "Formula 1": [
        {"id": "F1_ALL",     "name": "F1 — Full Season",    "country": "World"},
        {"id": "INDYCAR",    "name": "IndyCar",             "country": "USA"},
        {"id": "MOTO_GP",    "name": "MotoGP",              "country": "World"},
    ],
    "Tennis": [
        {"id": "ATP_ALL",    "name": "ATP Tour",            "country": "World"},
        {"id": "WTA_ALL",    "name": "WTA Tour",            "country": "World"},
        {"id": "GRAND_SLAM", "name": "Grand Slams",         "country": "World"},
    ],
    "Cricket": [
        {"id": "ICC_WC",     "name": "ICC World Cup",       "country": "World"},
        {"id": "IPL",        "name": "IPL",                 "country": "India"},
        {"id": "BBL",        "name": "Big Bash",            "country": "Australia"},
    ],
    "Golf": [
        {"id": "PGA_ALL",    "name": "PGA Tour",            "country": "USA"},
        {"id": "MASTERS",    "name": "The Masters",         "country": "USA"},
        {"id": "THE_OPEN",   "name": "The Open",            "country": "UK"},
    ],
    "Volleyball": [{"id": "VB_ALL", "name": "Volleyball", "country": "World"}],
    "Handball": [{"id": "HB_ALL", "name": "Handball", "country": "World"}],
    "Rugby": [{"id": "RU_ALL", "name": "Rugby Union", "country": "World"}],
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
        is_live = any(x in su for x in ["LIVE","1H","2H","HT","IN_PLAY","IN_PROGRESS"])
        is_done = any(x in su for x in ["FINISH","FT","FINAL","COMPLET","ENDED"])
        if is_live:   disp = "🔴 LIVE"
        elif is_done: disp = "✅ FINISHED"
        else:         disp = "⏳ UPCOMING"
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
        self.name  = name
        self._cache: Dict[str, Any] = {}

    def _req(self, url: str, headers: Dict = None,
             params: Dict = None, method: str = "GET",
             json_body: Dict = None) -> Optional[Any]:
        for attempt in range(APIConfig.RETRIES):
            try:
                if method == "POST":
                    r = requests.post(url, headers=headers or {}, params=params or {},
                                      json=json_body, timeout=APIConfig.TIMEOUT)
                else:
                    r = requests.get(url, headers=headers or {}, params=params or {},
                                     timeout=APIConfig.TIMEOUT)
                if r.status_code == 429:
                    time.sleep((attempt + 1) * 2)
                    continue
                if r.status_code == 200:
                    return r.json()
                logger.warning(f"[{self.name}] HTTP {r.status_code} {url[:80]}")
                return None
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.name}] Timeout attempt {attempt+1}")
            except Exception as e:
                logger.error(f"[{self.name}] {e}")
            if attempt < APIConfig.RETRIES - 1:
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
# API-SPORTS PROVIDER — FREE (100 requests/day) - PRIMARY SOCCER
# ═══════════════════════════════════════════════════════════════════════════════
class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.h = {"x-apisports-key": APIConfig.API_SPORTS_KEY} if APIConfig.API_SPORTS_KEY else {}
        self.request_counter = 0
        self.last_reset = datetime.now()

    @property
    def ok(self): 
        return bool(APIConfig.API_SPORTS_KEY)

    def _check_rate_limit(self):
        """Track free tier usage (100 requests/day)"""
        now = datetime.now()
        if now.day != self.last_reset.day:
            self.request_counter = 0
            self.last_reset = now
        
        if self.request_counter >= 95:
            logger.warning("[API-SPORTS] Approaching daily limit (95/100)")
        return self.request_counter < 100

    def get_live(self, league_id: str = None) -> List[Match]:
        if not self.ok or not self._check_rate_limit():
            return []
        ck = self._ck("live", league_id)
        c = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None:
            return c
        
        p = {"live": "all"}
        if league_id and league_id not in ("ALL", ""):
            p["league"] = league_id
        d = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.h, p)
        self.request_counter += 1
        out = self._parse(d) if d else []
        self._set(ck, out)
        return out

    def get_upcoming(self, days: int = 7) -> List[Match]:
        if not self.ok or not self._check_rate_limit():
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        ck = self._ck("upcoming", today)
        c = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None:
            return c
        
        d = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.h,
                      {"from": today, "to": future})
        self.request_counter += 1
        out = self._parse(d) if d else []
        self._set(ck, out)
        return out

    def _parse(self, data: Dict) -> List[Match]:
        out = []
        for fx in data.get("response", []):
            f = fx.get("fixture", {})
            lg = fx.get("league", {})
            tm = fx.get("teams", {})
            gl = fx.get("goals", {})
            st = f.get("status", {})
            start = None
            if f.get("date"):
                try:
                    start = datetime.fromisoformat(f["date"].replace("Z", "+00:00"))
                except:
                    pass
            status_str = st.get("short", "NS")
            if status_str == "LIVE":
                status = "LIVE"
            elif status_str in ["FT", "AET", "PEN"]:
                status = "FINISHED"
            else:
                status = "SCHEDULED"
                
            out.append(Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=lg.get("name", "?"),
                league_id=str(lg.get("id", "")),
                home_team=tm.get("home", {}).get("name", "Home"),
                away_team=tm.get("away", {}).get("name", "Away"),
                home_score=gl.get("home"),
                away_score=gl.get("away"),
                status=status,
                minute=st.get("elapsed"),
                start_time=start,
                country=lg.get("country"),
            ))
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA.ORG PROVIDER — FREE (10 requests/min) - SOCCER BACKUP
# ═══════════════════════════════════════════════════════════════════════════════
class FootballDataProvider(DataProvider):
    def __init__(self):
        super().__init__("Football-Data")
        self.h = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY} if APIConfig.FOOTBALL_DATA_KEY else {}
        self.request_timestamps = []

    @property
    def ok(self):
        return True  # Works without API key (limited data)

    def _check_rate_limit(self):
        """Track 10 requests per minute"""
        now = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        if len(self.request_timestamps) >= 10:
            return False
        self.request_timestamps.append(now)
        return True

    def get_today(self) -> List[Match]:
        if not self._check_rate_limit():
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        ck = self._ck("today", today)
        c = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None:
            return c
        
        d = self._req(f"{APIConfig.FOOTBALL_DATA_URL}/matches", self.h,
                      {"dateFrom": today, "dateTo": today})
        if not d:
            return []
        out = []
        for m in d.get("matches", []):
            comp = m.get("competition", {})
            home = m.get("homeTeam", {})
            away = m.get("awayTeam", {})
            score = m.get("score", {}).get("fullTime", {})
            start = None
            if m.get("utcDate"):
                try:
                    start = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
                except:
                    pass
            raw_st = m.get("status", "SCHEDULED").upper()
            if "IN_PLAY" in raw_st or "PAUSED" in raw_st:
                sts = "LIVE"
            elif "FINISHED" in raw_st:
                sts = "FINISHED"
            else:
                sts = "SCHEDULED"
            out.append(Match(
                match_id=str(m.get("id", "")),
                provider="Football-Data",
                league=comp.get("name", "?"),
                league_id=str(comp.get("id", "")),
                home_team=home.get("name", "Home"),
                away_team=away.get("name", "Away"),
                home_score=_toint(score.get("home")),
                away_score=_toint(score.get("away")),
                status=sts,
                start_time=start,
                country=comp.get("area", {}).get("name", ""),
            ))
        self._set(ck, out)
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER — COMPLETELY FREE (Unlimited)
# ═══════════════════════════════════════════════════════════════════════════════
class TheSportsDBProvider(DataProvider):
    LEAGUE_IDS = {
        "UFC": "4467", "Formula 1": "4370", "Tennis": "4424",
        "Cricket": "4722", "Golf": "4426", "Volleyball": "4480",
        "Rugby": "4499", "Handball": "4520", "Darts": "4540",
        "Snooker": "4560", "Table Tennis": "4580",
    }

    def __init__(self):
        super().__init__("TheSportsDB")
        self.key = APIConfig.TSDB_KEY or "3"

    @property
    def ok(self):
        return True

    def _req_v1(self, ep, p=None):
        return self._req(f"{APIConfig.TSDB_URL}/{self.key}/{ep}", params=p)

    def get_upcoming(self, sport: str) -> List[Match]:
        lid = self.LEAGUE_IDS.get(sport)
        if not lid:
            return []
        ck = self._ck("upcoming", sport)
        c = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None:
            return c
        
        d = self._req_v1("eventsnextleague.php", {"id": lid})
        out = []
        if d and d.get("events"):
            for ev in d["events"]:
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M")
                    except:
                        pass
                out.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    status="SCHEDULED",
                    start_time=start,
                ))
        self._set(ck, out)
        return out

    def get_live(self, sport: str) -> List[Match]:
        sport_map = {
            "UFC": "MMA", "Formula 1": "Motorsport", "Tennis": "Tennis",
            "Cricket": "Cricket", "Golf": "Golf"
        }
        ck = self._ck("live", sport)
        c = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None:
            return c
        
        d = self._req_v1("livescore.php", {"s": sport_map.get(sport, sport)})
        out = []
        if d and d.get("events"):
            for ev in d["events"]:
                out.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    home_score=_toint(ev.get("intHomeScore")),
                    away_score=_toint(ev.get("intAwayScore")),
                    status="LIVE",
                    country=ev.get("strCountry"),
                ))
        self._set(ck, out)
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER — FREE TIER (US Sports)
# ═══════════════════════════════════════════════════════════════════════════════
class MySportsFeedsProvider(DataProvider):
    CODES = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}

    def __init__(self):
        super().__init__("MySportsFeeds")
        if APIConfig.MSF_KEY and APIConfig.MSF_PASS:
            creds = base64.b64encode(f"{APIConfig.MSF_KEY}:{APIConfig.MSF_PASS}".encode()).decode()
            self.h = {"Authorization": f"Basic {creds}"}
        else:
            self.h = {}

    @property
    def ok(self):
        return bool(self.h)

    def _season(self, sport: str) -> str:
        now = datetime.now()
        s = sport.upper()
        if s in ("NBA", "NHL"):
            return f"{now.year}-{now.year + 1}" if now.month >= 10 else f"{now.year - 1}-{now.year}"
        if s == "NFL":
            return str(now.year) if now.month >= 8 else str(now.year - 1)
        return str(now.year)

    def get_upcoming(self, sport: str, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        code = self.CODES.get(sport.upper(), "nba")
        season = self._season(sport)
        today = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        ck = self._ck("upcoming", code, today)
        c = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None:
            return c
        
        d = self._req(f"{APIConfig.MSF_URL}/{code}/{season}/games.json",
                      self.h, {"fordate": today, "todate": future})
        out = self._parse(d, sport) if d else []
        self._set(ck, out)
        return out

    def _parse(self, data: Dict, sport: str) -> List[Match]:
        out = []
        for game in data.get("games", []):
            sc = game.get("schedule", game)
            raw = sc.get("playedStatus", sc.get("status", "UNPLAYED")).upper()
            live = raw in ("IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT")
            done = raw in ("COMPLETED", "FINAL", "COMPLETED_PENDING_REVIEW")
            
            def _name(t):
                if isinstance(t, dict):
                    return f"{t.get('city', '')} {t.get('name', '')}".strip()
                return str(t)
            
            home = _name(sc.get("homeTeam", {})) or "TBD"
            away = _name(sc.get("awayTeam", {})) or "TBD"
            sc2 = game.get("score", {}) or {}
            start = None
            for k in ("startTime", "startDate", "date"):
                if sc.get(k):
                    try:
                        start = datetime.fromisoformat(sc[k].replace("Z", "+00:00"))
                        break
                    except:
                        pass
            
            out.append(Match(
                match_id=str(sc.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home,
                away_team=away,
                home_score=_toint(sc2.get("homeScoreTotal")),
                away_score=_toint(sc2.get("awayScoreTotal")),
                status="LIVE" if live else ("FINISHED" if done else "SCHEDULED"),
                start_time=start,
            ))
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _toint(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER — Prioritizes FREE APIs, Apify DISABLED
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        # FREE API Providers (all configured)
        self.api_sports = APISportsProvider()      # Soccer primary (100/day)
        self.football_data = FootballDataProvider() # Soccer backup (10/min)
        self.tsdb = TheSportsDBProvider()           # Unlimited free
        self.msf = MySportsFeedsProvider()          # US Sports free tier
        
        # PAID API - DISABLED due to monthly limit
        self.apify = None
        if APIConfig.USE_APIFY and APIConfig.APIFY_API_TOKEN:
            logger.warning("Apify is PAID and has monthly limits. Using free APIs instead.")
        
        self.log: List[Dict] = []
        self._log_startup()

    def _log(self, prov, status, detail):
        self.log.append({
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": prov,
            "STATUS": status,
            "DETAIL": str(detail)[:80]
        })

    def _log_startup(self):
        items = [
            ("✅ API-SPORTS (FREE)", bool(APIConfig.API_SPORTS_KEY), "100 req/day - PRIMARY"),
            ("✅ Football-Data (FREE)", True, "10 req/min - BACKUP"),
            ("✅ TheSportsDB (FREE)", True, "Unlimited - UFC/F1/Tennis"),
            ("✅ MySportsFeeds (FREE)", bool(APIConfig.MSF_KEY), "US Sports"),
            ("❌ Apify (PAID)", False, "DISABLED - monthly limit exceeded"),
        ]
        for n, ok, d in items:
            self._log(n, "READY" if ok else "DISABLED", d)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "API-SPORTS (FREE)", "status": "🟢 ONLINE" if APIConfig.API_SPORTS_KEY else "⚠️ NEEDS API KEY"},
            {"name": "Football-Data (FREE)", "status": "🟢 ONLINE"},
            {"name": "TheSportsDB (FREE)", "status": "🟢 ONLINE"},
            {"name": "MySportsFeeds (FREE)", "status": "🟢 ONLINE" if APIConfig.MSF_KEY else "⚪ Optional"},
            {"name": "Apify (PAID/DISABLED)", "status": "🔴 DISABLED - Free APIs active"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-60:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        """Returns static leagues instantly - ZERO API calls"""
        return STATIC_LEAGUES.get(sport, [{"id": "ALL", "name": "All Events", "country": "World"}])

    def get_upcoming_matches(self, sport: str) -> pd.DataFrame:
        matches = []
        try:
            # SOCCER: Use FREE API-SPORTS (primary) with Football-Data backup
            if sport == "Soccer":
                matches = self.api_sports.get_upcoming(days=7)
                if matches:
                    self._log("API-SPORTS (FREE)", "SUCCESS", f"{len(matches)} soccer matches")
                else:
                    # Fallback to Football-Data
                    fd_today = self.football_data.get_today()
                    matches = [m for m in fd_today if m.status == "SCHEDULED"]
                    if matches:
                        self._log("Football-Data (FREE)", "SUCCESS", f"{len(matches)} soccer matches")
                    else:
                        self._log("Soccer", "EMPTY", "No matches found from free APIs")
            
            # UFC, F1, Tennis, Cricket, Golf, etc: Use TheSportsDB (completely free)
            elif sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf", "Volleyball", "Rugby", "Handball", "Darts", "Snooker", "Table Tennis"]:
                matches = self.tsdb.get_upcoming(sport)
                self._log("TheSportsDB (FREE)", "SUCCESS" if matches else "EMPTY", f"{len(matches)} {sport} matches")
            
            # US Sports: Use MySportsFeeds (free tier)
            elif sport in ["NBA", "NFL", "MLB", "NHL"]:
                matches = self.msf.get_upcoming(sport)
                self._log("MySportsFeeds (FREE)", "SUCCESS" if matches else "EMPTY", f"{len(matches)} {sport} matches")
            
            # Default fallback for any other sport
            else:
                matches = self.tsdb.get_upcoming(sport)
                self._log("TheSportsDB (FREE)", "SUCCESS" if matches else "EMPTY", f"{len(matches)} {sport} matches")

        except Exception as e:
            self._log("ROUTER", "ERROR", f"upcoming {sport}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        try:
            # SOCCER: Use FREE API-SPORTS for live matches
            if sport == "Soccer":
                matches = self.api_sports.get_live(league_id)
                if matches:
                    self._log("API-SPORTS (FREE)", "SUCCESS", f"{len(matches)} live soccer matches")
                else:
                    # Fallback to Football-Data
                    fd_today = self.football_data.get_today()
                    matches = [m for m in fd_today if m.status == "LIVE"]
                    if matches:
                        self._log("Football-Data (FREE)", "SUCCESS", f"{len(matches)} live soccer matches")
            
            # Other sports live data
            elif sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf"]:
                matches = self.tsdb.get_live(sport)
                self._log("TheSportsDB (FREE)", "SUCCESS" if matches else "EMPTY", f"{len(matches)} live {sport} matches")
            
            elif sport in ["NBA", "NFL", "MLB", "NHL"]:
                # For US sports, get upcoming games and filter live
                all_today = self.msf.get_upcoming(sport, days=1)
                matches = [m for m in all_today if m.status == "LIVE"]
                self._log("MySportsFeeds (FREE)", "SUCCESS" if matches else "EMPTY", f"{len(matches)} live {sport} matches")

        except Exception as e:
            self._log("ROUTER", "ERROR", f"live {sport}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self) -> bool:
        return True  # Free APIs are active

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, s: str) -> List[Dict]:
        return self.router.get_all_leagues(s)

    def get_live_matches_df(self, s: str, lid: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(s, lid)

    def get_upcoming_matches_df(self, s: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(s)


__all__ = ["APIConfig", "EmpireDashboardData"]
