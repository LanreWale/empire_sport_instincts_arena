"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
═══════════════════════════════════════════════════════════════════════════════

Supported Providers:
  • API-SPORTS (API-Football) — Primary football feed
  • The Odds API — Odds aggregation from 40+ bookmakers
  • Sportmonks — Advanced football analytics (xG, predictions)
  • TheSportsDB — Media-rich metadata + livescores (v1 + v2)
  • MySportsFeeds — US sports (NBA, NFL, MLB, NHL, MLS)
  • Football-Data.org — Free backup for major European leagues

Architecture:
  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
  │  API-SPORTS     │     │  The Odds API   │     │  Sportmonks     │
  │  (Football)     │     │  (Odds Feed)    │     │  (Analytics)    │
  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                    ┌───────────────▼───────────────┐
                    │   EMPIRE Data Router          │
                    │   • Failover logic            │
                    │   • Rate limiting             │
                    │   • Cache layer               │
                    │   • Normalization             │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   EMPIRE AI Engine            │
                    │   • EV Calculator             │
                    │   • Kelly Criterion           │
                    │   • Risk Assessment           │
                    │   • Prediction Models         │
                    └───────────────────────────────┘
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
import traceback
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMPIRE_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION & API KEYS
# Load from environment variables — with robust cleaning for malformed values
# ════════════════════════════════════════════════════════════════════════════════

class APIConfig:
    """Centralized API configuration with failover priorities.
    Handles malformed .env values like _KEY=prefix."""

    @staticmethod
    def _clean_key(key: str) -> str:
        """Remove malformed _KEY= prefix from env values."""
        if not key:
            return ""
        if key.startswith("_KEY="):
            key = key[5:]
        if key.startswith("KEY="):
            key = key[4:]
        return key.strip()

    @staticmethod
    def _safe_float(value, default=0.0):
        """Safely convert any value to float, handling strings like '-'."""
        if value is None or value == "" or value == "-":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # API-SPORTS (API-Football) — https://www.api-football.com/
    API_SPORTS_KEY = _clean_key(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL = "https://v3.football.api-sports.io"
    API_SPORTS_PRIORITY = 1  # Primary football data

    # The Odds API — https://the-odds-api.com/
    ODDS_API_KEY = _clean_key(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL = "https://api.the-odds-api.com/v4"
    ODDS_API_PRIORITY = 1  # Primary odds feed

    # Sportmonks — https://www.sportmonks.com/
    SPORTMONKS_KEY = _clean_key(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL = "https://api.sportmonks.com/v3/football"
    SPORTMONKS_PRIORITY = 2  # Secondary analytics

    # MySportsFeeds — https://www.mysportsfeeds.com/
    # Uses TWO-PART auth: API Key (username) + Password
    MYSPORTSFEEDS_KEY = _clean_key(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean_key(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL = "https://api.mysportsfeeds.com/v2.1/pull"
    MYSPORTSFEEDS_PRIORITY = 2  # US sports

    # Football-Data.org (free backup) — https://www.football-data.org/
    FOOTBALL_DATA_KEY = _clean_key(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"
    FOOTBALL_DATA_PRIORITY = 3  # Free fallback

    # TheSportsDB — https://www.thesportsdb.com/
    THESPORTSDB_KEY = _clean_key(os.getenv("TheSportDB_API_key", ""))
    THESPORTSDB_URL = "https://www.thesportsdb.com/api/v2/json"
    THESPORTSDB_URL_V1 = "https://www.thesportsdb.com/api/v1/json"
    THESPORTSDB_PRIORITY = 2  # Media-rich metadata + livescores

    # Cache settings
    CACHE_TTL_SECONDS = 30  # Live data cache
    ODDS_CACHE_TTL = 60     # Odds refresh rate

    # Rate limits
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    REQUEST_TIMEOUT = 10

    @classmethod
    def get_missing_keys(cls) -> List[str]:
        """Return list of API keys that are not configured."""
        required = {
            "API_SPORTS_KEY": cls.API_SPORTS_KEY,
            "ODDS_API_KEY": cls.ODDS_API_KEY,
            "SPORTMONKS_KEY": cls.SPORTMONKS_KEY,
            "MYSPORTSFEEDS_KEY": cls.MYSPORTSFEEDS_KEY,
            "TheSportDB_API_key": cls.THESPORTSDB_KEY,
            "FOOTBALL_DATA_KEY": cls.FOOTBALL_DATA_KEY,
        }
        return [k for k, v in required.items() if not v]

    @classmethod
    def is_configured(cls) -> bool:
        """Check if at least one primary provider is configured."""
        return bool(cls.API_SPORTS_KEY or cls.ODDS_API_KEY or cls.SPORTMONKS_KEY)



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
    """Unified match data model across all providers."""
    match_id: str
    provider: str
    league: str
    league_id: str
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = MatchStatus.SCHEDULED.value
    minute: Optional[int] = None
    start_time: Optional[datetime] = None
    venue: Optional[str] = None
    country: Optional[str] = None
    season: Optional[str] = None
    round: Optional[str] = None
    # Live stats
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
    # Odds
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None
    # Predictions
    home_win_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    over_25_prob: Optional[float] = None
    btts_prob: Optional[float] = None
    # EMPIRE analysis
    ev_home: Optional[float] = None
    ev_draw: Optional[float] = None
    ev_away: Optional[float] = None
    kelly_home: Optional[float] = None
    kelly_draw: Optional[float] = None
    kelly_away: Optional[float] = None
    confidence: Optional[str] = None
    signal: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_dataframe_row(self) -> Dict:
        """Convert to flat dict for DataFrame display."""
        return {
            "MATCH_ID": self.match_id,
            "TIME": self.start_time.strftime("%H:%M") if self.start_time else "TBD",
            "LEAGUE": self.league,
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
    """Bookmaker odds snapshot for value detection."""
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



# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class DataProvider:
    """Abstract base class for all sports data providers."""

    def __init__(self, name: str, priority: int):
        self.name = name
        self.priority = priority
        self.last_call = 0
        self.rate_limit_delay = 1.0
        self.cache = {}

    def _make_request(self, url: str, headers: Dict = None, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request with retry logic and rate limiting."""
        # Rate limiting
        elapsed = time.time() - self.last_call
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        for attempt in range(APIConfig.MAX_RETRIES):
            try:
                self.last_call = time.time()
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=APIConfig.REQUEST_TIMEOUT
                )

                if response.status_code == 429:  # Rate limited
                    wait = (attempt + 1) * 2
                    logger.warning(f"{self.name}: Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.error(f"{self.name}: Request failed (attempt {attempt + 1}): {e}")
                if attempt < APIConfig.MAX_RETRIES - 1:
                    time.sleep(APIConfig.RETRY_DELAY * (attempt + 1))

        return None

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key for request."""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached(self, cache_key: str, ttl: int = None) -> Optional[Dict]:
        """Retrieve cached data if not expired."""
        if cache_key not in self.cache:
            return None

        data, timestamp = self.cache[cache_key]
        ttl = ttl or APIConfig.CACHE_TTL_SECONDS

        if time.time() - timestamp > ttl:
            del self.cache[cache_key]
            return None

        return data

    def _set_cached(self, cache_key: str, data: Dict):
        """Cache response data."""
        self.cache[cache_key] = (data, time.time())

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        """Fetch live matches. Override in subclass."""
        raise NotImplementedError

    def get_upcoming_matches(self, sport: str = "football", days: int = 1) -> List[Match]:
        """Fetch upcoming matches. Override in subclass."""
        raise NotImplementedError

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """Fetch odds for specific match. Override in subclass."""
        raise NotImplementedError

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """Fetch AI predictions. Override in subclass."""
        raise NotImplementedError



# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS (API-FOOTBALL) PROVIDER
# Primary football data: live scores, fixtures, statistics
# ════════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    """
    API-SPORTS / API-Football integration.
    Coverage: 900+ leagues worldwide, live scores, stats, lineups, events.
    Docs: https://www.api-football.com/documentation-v3
    """

    def __init__(self):
        super().__init__("API-SPORTS", APIConfig.API_SPORTS_PRIORITY)
        self.base_url = APIConfig.API_SPORTS_URL
        self.headers = {
            "x-rapidapi-key": APIConfig.API_SPORTS_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        self.rate_limit_delay = 0.5  # 6 calls/second on basic plan

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        """Fetch currently live football matches."""
        if not APIConfig.API_SPORTS_KEY:
            logger.warning("API_SPORTS_KEY not configured")
            return []

        cache_key = self._get_cache_key("fixtures/live", {"league": league_id})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_fixtures(cached)

        params = {"live": "all"}
        if league_id:
            params["league"] = league_id

        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_upcoming_matches(self, sport: str = "football", days: int = 1) -> List[Match]:
        """Fetch upcoming fixtures."""
        if not APIConfig.API_SPORTS_KEY:
            return []

        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        cache_key = self._get_cache_key("fixtures", {"from": today, "to": future})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_fixtures(cached)

        params = {
            "date": today,
            "season": datetime.now().year,
            "timezone": "UTC"
        }

        data = self._make_request(f"{self.base_url}/fixtures", self.headers, params)
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_fixtures(data)

    def get_match_stats(self, fixture_id: str) -> Optional[Dict]:
        """Fetch detailed match statistics."""
        if not APIConfig.API_SPORTS_KEY:
            return None

        cache_key = self._get_cache_key("fixtures/statistics", {"fixture": fixture_id})
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = self._make_request(
            f"{self.base_url}/fixtures/statistics",
            self.headers,
            {"fixture": fixture_id}
        )
        if data:
            self._set_cached(cache_key, data)
            return data
        return None

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """Fetch odds for a fixture."""
        if not APIConfig.API_SPORTS_KEY:
            return []

        cache_key = self._get_cache_key("odds", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=APIConfig.ODDS_CACHE_TTL)
        if cached:
            return self._parse_odds(cached, match_id)

        data = self._make_request(
            f"{self.base_url}/odds",
            self.headers,
            {"fixture": match_id}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_odds(data, match_id)

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """Fetch predictions from API-SPORTS (if available)."""
        if not APIConfig.API_SPORTS_KEY:
            return None

        cache_key = self._get_cache_key("predictions", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=600)
        if cached:
            return self._parse_predictions(cached, match_id)

        data = self._make_request(
            f"{self.base_url}/predictions",
            self.headers,
            {"fixture": match_id}
        )
        if not data:
            return None

        self._set_cached(cache_key, data)
        return self._parse_predictions(data, match_id)

    def _parse_fixtures(self, data: Dict) -> List[Match]:
        """Parse API-SPORTS fixture response into Match objects."""
        matches = []
        response = data.get("response", [])

        for fixture in response:
            f = fixture.get("fixture", {})
            league = fixture.get("league", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            status = fixture.get("fixture", {}).get("status", {})

            match = Match(
                match_id=str(f.get("id", "")),
                provider="API-SPORTS",
                league=league.get("name", "Unknown"),
                league_id=str(league.get("id", "")),
                home_team=teams.get("home", {}).get("name", "Home"),
                away_team=teams.get("away", {}).get("name", "Away"),
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                status=status.get("short", "SCH"),
                minute=status.get("elapsed"),
                start_time=datetime.fromisoformat(f.get("date", "").replace("Z", "+00:00")) if f.get("date") else None,
                venue=f.get("venue", {}).get("name"),
                country=league.get("country"),
                season=str(league.get("season", "")),
                round=league.get("round"),
            )
            matches.append(match)

        return matches

    def _parse_odds(self, data: Dict, match_id: str) -> List[OddsSnapshot]:
        """Parse API-SPORTS odds response."""
        snapshots = []
        response = data.get("response", [])

        for odds_data in response:
            bookmaker = odds_data.get("bookmaker", {}).get("name", "Unknown")
            bets = odds_data.get("bets", [])

            for bet in bets:
                market = bet.get("name", "Unknown")
                values = bet.get("values", [])

                home = draw = away = None
                for v in values:
                    if v.get("value") in ["Home", "1"]:
                        home = float(v.get("odd", 0))
                    elif v.get("value") in ["Draw", "X"]:
                        draw = float(v.get("odd", 0))
                    elif v.get("value") in ["Away", "2"]:
                        away = float(v.get("odd", 0))

                if home and away:
                    snapshots.append(OddsSnapshot(
                        match_id=match_id,
                        bookmaker=bookmaker,
                        market=market,
                        home_odds=home,
                        draw_odds=draw,
                        away_odds=away,
                        timestamp=datetime.now()
                    ))

        return snapshots

    def _parse_predictions(self, data: Dict, match_id: str) -> Optional[Match]:
        """Parse API-SPORTS predictions response."""
        response = data.get("response", [])
        if not response:
            return None

        pred = response[0]
        predictions = pred.get("predictions", {})
        comparison = pred.get("comparison", {})

        return Match(
            match_id=match_id,
            provider="API-SPORTS",
            league=pred.get("league", {}).get("name", ""),
            league_id=str(pred.get("league", {}).get("id", "")),
            home_team=pred.get("teams", {}).get("home", {}).get("name", ""),
            away_team=pred.get("teams", {}).get("away", {}).get("name", ""),
            home_win_prob=predictions.get("percent", {}).get("home"),
            draw_prob=predictions.get("percent", {}).get("draw"),
            away_win_prob=predictions.get("percent", {}).get("away"),
        )



# ═══════════════════════════════════════════════════════════════════════════════
# THE ODDS API PROVIDER
# Odds aggregation from 40+ global bookmakers
# ════════════════════════════════════════════════════════════════════════════════

class TheOddsAPIProvider(DataProvider):
    """
    The Odds API integration.
    Coverage: 70+ sports, 40+ bookmakers, real-time odds.
    Docs: https://the-odds-api.com/liveapi/guides/v4/
    """

    def __init__(self):
        super().__init__("TheOddsAPI", APIConfig.ODDS_API_PRIORITY)
        self.base_url = APIConfig.ODDS_API_URL
        self.rate_limit_delay = 1.0

    def get_live_matches(self, sport: str = "soccer", league_id: str = None) -> List[Match]:
        """Fetch in-play events."""
        if not APIConfig.ODDS_API_KEY:
            logger.warning("ODDS_API_KEY not configured")
            return []

        cache_key = self._get_cache_key("sports/events/inplay", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_events(cached, sport)

        data = self._make_request(
            f"{self.base_url}/sports/{sport}/events",
            params={"apiKey": APIConfig.ODDS_API_KEY, "regions": "eu", "oddsFormat": "decimal"}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_events(data, sport)

    def get_upcoming_matches(self, sport: str = "soccer", days: int = 1) -> List[Match]:
        """Fetch upcoming events with odds."""
        if not APIConfig.ODDS_API_KEY:
            return []

        cache_key = self._get_cache_key("sports/events/upcoming", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_events(cached, sport)

        data = self._make_request(
            f"{self.base_url}/sports/{sport}/odds",
            params={
                "apiKey": APIConfig.ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h,totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso"
            }
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_events(data, sport)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """Fetch odds for specific event from all bookmakers."""
        if not APIConfig.ODDS_API_KEY:
            return []

        cache_key = self._get_cache_key("event_odds", {"event": match_id, "markets": markets or ["h2h"]})
        cached = self._get_cached(cache_key, ttl=APIConfig.ODDS_CACHE_TTL)
        if cached:
            return self._parse_event_odds(cached, match_id)

        data = self._make_request(
            f"{self.base_url}/sports/soccer/events/{match_id}/odds",
            params={
                "apiKey": APIConfig.ODDS_API_KEY,
                "regions": "eu",
                "markets": ",".join(markets) if markets else "h2h",
                "oddsFormat": "decimal"
            }
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_event_odds(data, match_id)

    def _parse_events(self, data: List[Dict], sport: str) -> List[Match]:
        """Parse The Odds API event response."""
        matches = []

        for event in data:
            commence = event.get("commence_time")
            start_time = datetime.fromisoformat(commence.replace("Z", "+00:00")) if commence else None

            # Extract best odds across bookmakers
            home_odds = draw_odds = away_odds = None
            bookmakers = event.get("bookmakers", [])

            if bookmakers:
                best = bookmakers[0]
                markets = best.get("markets", [])
                for market in markets:
                    if market.get("key") == "h2h":
                        outcomes = market.get("outcomes", [])
                        for o in outcomes:
                            name = o.get("name", "").lower()
                            price = o.get("price")
                            if "home" in name or event.get("home_team", "").lower() in name:
                                home_odds = price
                            elif "away" in name or event.get("away_team", "").lower() in name:
                                away_odds = price
                            elif "draw" in name:
                                draw_odds = price

            match = Match(
                match_id=event.get("id", ""),
                provider="TheOddsAPI",
                league=event.get("sport_title", sport),
                league_id="",
                home_team=event.get("home_team", "Home"),
                away_team=event.get("away_team", "Away"),
                start_time=start_time,
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
            )
            matches.append(match)

        return matches

    def _parse_event_odds(self, data: Dict, match_id: str) -> List[OddsSnapshot]:
        """Parse odds for a specific event across all bookmakers."""
        snapshots = []
        bookmakers = data.get("bookmakers", [])

        for bm in bookmakers:
            bookmaker_name = bm.get("title", "Unknown")
            markets = bm.get("markets", [])

            for market in markets:
                market_key = market.get("key", "Unknown")
                outcomes = market.get("outcomes", [])

                home = draw = away = over = under = None
                for o in outcomes:
                    name = o.get("name", "").lower()
                    price = o.get("price")
                    point = o.get("point")

                    if "home" in name:
                        home = price
                    elif "away" in name:
                        away = price
                    elif "draw" in name:
                        draw = price
                    elif market_key == "totals" and "over" in name:
                        over = price
                    elif market_key == "totals" and "under" in name:
                        under = price

                if home and away:
                    snapshots.append(OddsSnapshot(
                        match_id=match_id,
                        bookmaker=bookmaker_name,
                        market=market_key,
                        home_odds=home,
                        draw_odds=draw,
                        away_odds=away,
                        over_odds=over,
                        under_odds=under,
                        timestamp=datetime.now()
                    ))

        return snapshots


# ═══════════════════════════════════════════════════════════════════════════════
# SPORTMONKS PROVIDER
# Advanced football analytics: xG, predictions, deep stats
# ════════════════════════════════════════════════════════════════════════════════

class SportmonksProvider(DataProvider):
    """
    Sportmonks integration.
    Coverage: 2,500+ football leagues, xG, predictions, advanced stats.
    Docs: https://docs.sportmonks.com/football/
    """

    def __init__(self):
        super().__init__("Sportmonks", APIConfig.SPORTMONKS_PRIORITY)
        self.base_url = APIConfig.SPORTMONKS_URL
        self.rate_limit_delay = 1.5

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        """Fetch live matches with predictions."""
        if not APIConfig.SPORTMONKS_KEY:
            logger.warning("SPORTMONKS_KEY not configured")
            return []

        cache_key = self._get_cache_key("livescores/inplay", {})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_livescores(cached)

        data = self._make_request(
            f"{self.base_url}/livescores/inplay",
            params={"api_token": APIConfig.SPORTMONKS_KEY, "include": "predictions"}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_livescores(data)

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """Fetch AI predictions for a match."""
        if not APIConfig.SPORTMONKS_KEY:
            return None

        cache_key = self._get_cache_key("predictions/probabilities", {"fixture": match_id})
        cached = self._get_cached(cache_key, ttl=600)
        if cached:
            return self._parse_predictions(cached, match_id)

        data = self._make_request(
            f"{self.base_url}/predictions/probabilities/fixture/{match_id}",
            params={"api_token": APIConfig.SPORTMONKS_KEY}
        )
        if not data:
            return None

        self._set_cached(cache_key, data)
        return self._parse_predictions(data, match_id)

    def _parse_livescores(self, data: Dict) -> List[Match]:
        """Parse Sportmonks livescore response."""
        matches = []
        for item in data.get("data", []):
            participants = item.get("participants", [{}, {}])
            home_team = participants[0].get("name", "Home") if len(participants) > 0 else "Home"
            away_team = participants[1].get("name", "Away") if len(participants) > 1 else "Away"

            match = Match(
                match_id=str(item.get("id", "")),
                provider="Sportmonks",
                league=item.get("league", {}).get("name", "Unknown"),
                league_id=str(item.get("league_id", "")),
                home_team=home_team,
                away_team=away_team,
                home_score=item.get("scores", {}).get("home"),
                away_score=item.get("scores", {}).get("away"),
                status=item.get("state", {}).get("state", "SCH"),
                minute=item.get("minute"),
            )
            matches.append(match)
        return matches

    def _parse_predictions(self, data: Dict, match_id: str) -> Optional[Match]:
        """Parse prediction probabilities."""
        pred = data.get("data", {})
        return Match(
            match_id=match_id,
            provider="Sportmonks",
            league="",
            league_id="",
            home_team="",
            away_team="",
            home_win_prob=pred.get("home_win_probability"),
            draw_prob=pred.get("draw_probability"),
            away_win_prob=pred.get("away_win_probability"),
            over_25_prob=pred.get("over_2_5_probability"),
            btts_prob=pred.get("both_teams_to_score_probability"),
        )



# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER
# Media-rich sports metadata, livescores, events, team/player data
# Free tier: 30 req/min | Premium: 100 req/min (v2 with X-API-KEY header)
# ════════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    """
    TheSportsDB integration.
    Coverage: 50+ sports, team logos, player photos, livescores (v2 premium),
    events, schedules, historical results.
    Docs: https://www.thesportsdb.com/free_sports_api
    """

    def __init__(self):
        super().__init__("TheSportsDB", APIConfig.THESPORTSDB_PRIORITY)
        self.base_url_v1 = APIConfig.THESPORTSDB_URL_V1
        self.base_url_v2 = APIConfig.THESPORTSDB_URL
        self.headers_v2 = {"X-API-KEY": APIConfig.THESPORTSDB_KEY} if APIConfig.THESPORTSDB_KEY else {}
        self.rate_limit_delay = 2.0  # 30 req/min free tier

    def _make_request_v1(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make v1 API request (key in URL path)."""
        key = APIConfig.THESPORTSDB_KEY or "123"  # free test key
        url = f"{self.base_url_v1}/{key}/{endpoint}"
        return self._make_request(url, params=params)

    def _make_request_v2(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make v2 API request (key in header)."""
        if not APIConfig.THESPORTSDB_KEY:
            return None
        url = f"{self.base_url_v2}/{endpoint}"
        return self._make_request(url, headers=self.headers_v2, params=params)

    def get_live_matches(self, sport: str = "Soccer", league_id: str = None) -> List[Match]:
        """Fetch live scores via v2 livescore endpoint (premium key required)."""
        if not APIConfig.THESPORTSDB_KEY:
            return []

        cache_key = self._get_cache_key("livescore", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_livescores(cached)

        data = self._make_request_v2(f"livescore/{sport}")
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_livescores(data)

    def get_upcoming_matches(self, sport: str = "Soccer", days: int = 1) -> List[Match]:
        """Fetch next events via v1 (no key required for basic calls)."""
        cache_key = self._get_cache_key("eventsnextleague", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_events(cached)

        if APIConfig.THESPORTSDB_KEY:
            data = self._make_request_v2(f"schedule/{sport}")
        else:
            return []

        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_events(data)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """TheSportsDB does not provide odds — return empty."""
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """TheSportsDB does not provide predictions — return None."""
        return None

    def _parse_livescores(self, data: Dict) -> List[Match]:
        """Parse TheSportsDB v2 livescore response."""
        matches = []
        events = data.get("events", []) or data.get("livescore", [])

        for event in events:
            status = event.get("strStatus", "NS")
            is_live = status in ["1H", "2H", "HT", "Q1", "Q2", "Q3", "Q4", "OT", "P1", "P2", "P3", "IN1", "IN2", "IN3", "IN4", "IN5", "S1", "S2", "S3", "S4", "S5"]

            home_score = event.get("intHomeScore")
            away_score = event.get("intAwayScore")
            if home_score == "":
                home_score = None
            if away_score == "":
                away_score = None
            try:
                home_score = int(home_score) if home_score is not None else None
            except (ValueError, TypeError):
                home_score = None
            try:
                away_score = int(away_score) if away_score is not None else None
            except (ValueError, TypeError):
                away_score = None

            match = Match(
                match_id=str(event.get("idEvent", "")),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=str(event.get("idLeague", "")),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                home_score=home_score,
                away_score=away_score,
                status="LIVE" if is_live else status,
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
                venue=event.get("strVenue"),
                country=event.get("strCountry"),
                season=event.get("strSeason"),
                round=event.get("intRound"),
            )
            matches.append(match)
        return matches

    def _parse_events(self, data: Dict) -> List[Match]:
        """Parse TheSportsDB event schedule response."""
        matches = []
        events = data.get("events", [])

        for event in events:
            match = Match(
                match_id=str(event.get("idEvent", "")),
                provider="TheSportsDB",
                league=event.get("strLeague", "Unknown"),
                league_id=str(event.get("idLeague", "")),
                home_team=event.get("strHomeTeam", "Home"),
                away_team=event.get("strAwayTeam", "Away"),
                start_time=datetime.strptime(event.get("dateEvent", ""), "%Y-%m-%d") if event.get("dateEvent") else None,
                venue=event.get("strVenue"),
                country=event.get("strCountry"),
                season=event.get("strSeason"),
                round=event.get("intRound"),
            )
            matches.append(match)
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER
# US sports: NFL, NBA, MLB, NHL, MLS
# Uses TWO-PART Basic Auth: API Key + Password
# ════════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    """
    MySportsFeeds integration.
    Coverage: NFL, NBA, MLB, NHL, MLS. Real-time play-by-play.
    Uses Basic Auth: base64(api_key:password)
    Docs: https://www.mysportsfeeds.com/data-feeds/api-docs/
    """

    def __init__(self):
        super().__init__("MySportsFeeds", APIConfig.MYSPORTSFEEDS_PRIORITY)
        self.base_url = APIConfig.MYSPORTSFEEDS_URL
        # MySportsFeeds requires TWO-PART Basic Auth: API Key + Password
        # Format: base64(api_key:password)
        api_key = APIConfig.MYSPORTSFEEDS_KEY
        password = APIConfig.MYSPORTSFEEDS_PASSWORD
        if api_key and password:
            credentials = base64.b64encode(f"{api_key}:{password}".encode()).decode()
            self.headers = {"Authorization": f"Basic {credentials}"}
        else:
            self.headers = {}
        self.rate_limit_delay = 2.0

    def get_live_matches(self, sport: str = "nba", league_id: str = None) -> List[Match]:
        """Fetch live games."""
        if not APIConfig.MYSPORTSFEEDS_KEY:
            return []

        cache_key = self._get_cache_key("games", {"sport": sport})
        cached = self._get_cached(cache_key)
        if cached:
            return self._parse_games(cached)

        season = datetime.now().year
        data = self._make_request(
            f"{self.base_url}/{sport}/current/games.json",
            self.headers,
            {"date": datetime.now().strftime("%Y%m%d")}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_games(data)

    def get_upcoming_matches(self, sport: str = "nba", days: int = 7) -> List[Match]:
        """Fetch upcoming games."""
        if not APIConfig.MYSPORTSFEEDS_KEY:
            return []

        cache_key = self._get_cache_key("games/upcoming", {"sport": sport, "days": days})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_games(cached)

        data = self._make_request(
            f"{self.base_url}/{sport}/current/games.json",
            self.headers,
            {"date": datetime.now().strftime("%Y%m%d")}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_games(data)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """MySportsFeeds does not provide odds — return empty."""
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """MySportsFeeds does not provide predictions — return None."""
        return None

    def _parse_games(self, data: Dict) -> List[Match]:
        """Parse MySportsFeeds response."""
        matches = []
        for game in data.get("games", []):
            status = game.get("schedule", {}).get("status", "SCHEDULED")
            is_live = status == "IN_PROGRESS"

            home_score = game.get("score", {}).get("homeScoreTotal")
            away_score = game.get("score", {}).get("awayScoreTotal")

            matches.append(Match(
                match_id=str(game.get("schedule", {}).get("id", "")),
                provider="MySportsFeeds",
                league=game.get("schedule", {}).get("league", "Unknown"),
                league_id="",
                home_team=game.get("schedule", {}).get("homeTeam", {}).get("name", "Home"),
                away_team=game.get("schedule", {}).get("awayTeam", {}).get("name", "Away"),
                home_score=home_score,
                away_score=away_score,
                status="LIVE" if is_live else status,
                start_time=datetime.fromisoformat(game.get("schedule", {}).get("startTime", "").replace("Z", "+00:00")) if game.get("schedule", {}).get("startTime") else None,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA.ORG PROVIDER
# Free backup for major European leagues
# ════════════════════════════════════════════════════════════════════════════════

class FootballDataProvider(DataProvider):
    """
    Football-Data.org integration (free tier).
    Coverage: Major European leagues, 10 req/min, 5-min delay on free tier.
    Docs: https://www.football-data.org/documentation/quickstart
    """

    def __init__(self):
        super().__init__("Football-Data", APIConfig.FOOTBALL_DATA_PRIORITY)
        self.base_url = APIConfig.FOOTBALL_DATA_URL
        self.headers = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY}
        self.rate_limit_delay = 6.0  # 10 req/min = 6s between calls

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> List[Match]:
        """Fetch today's matches."""
        if not APIConfig.FOOTBALL_DATA_KEY:
            return []

        cache_key = self._get_cache_key("matches", {"date": datetime.now().strftime("%Y-%m-%d")})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_matches(cached)

        data = self._make_request(
            f"{self.base_url}/matches",
            self.headers
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_matches(data)

    def get_upcoming_matches(self, sport: str = "football", days: int = 7) -> List[Match]:
        """Fetch upcoming matches."""
        if not APIConfig.FOOTBALL_DATA_KEY:
            return []

        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        cache_key = self._get_cache_key("matches/upcoming", {"from": today, "to": future})
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return self._parse_matches(cached)

        data = self._make_request(
            f"{self.base_url}/matches",
            self.headers,
            {"dateFrom": today, "dateTo": future}
        )
        if not data:
            return []

        self._set_cached(cache_key, data)
        return self._parse_matches(data)

    def get_odds(self, match_id: str, markets: List[str] = None) -> List[OddsSnapshot]:
        """Football-Data does not provide odds — return empty."""
        return []

    def get_predictions(self, match_id: str) -> Optional[Match]:
        """Football-Data does not provide predictions — return None."""
        return None

    def _parse_matches(self, data: Dict) -> List[Match]:
        """Parse football-data.org response."""
        matches = []
        for match in data.get("matches", []):
            status = match.get("status", "SCHEDULED")
            minute = None
            if status == "IN_PLAY":
                status = "LIVE"
            elif status == "PAUSED":
                status = "HALFTIME"
            elif status == "FINISHED":
                status = "FINISHED"

            home_score = match.get("score", {}).get("fullTime", {}).get("home")
            away_score = match.get("score", {}).get("fullTime", {}).get("away")

            matches.append(Match(
                match_id=str(match.get("id", "")),
                provider="Football-Data",
                league=match.get("competition", {}).get("name", "Unknown"),
                league_id=str(match.get("competition", {}).get("id", "")),
                home_team=match.get("homeTeam", {}).get("name", "Home"),
                away_team=match.get("awayTeam", {}).get("name", "Away"),
                home_score=home_score,
                away_score=away_score,
                status=status,
                minute=minute,
                start_time=datetime.fromisoformat(match.get("utcDate", "").replace("Z", "+00:00")) if match.get("utcDate") else None,
            ))
        return matches



# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# Multi-provider aggregation with failover
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDataRouter:
    """
    Central data router for EMPIRE system.
    Aggregates multiple providers, handles failover, caches data.
    """

    def __init__(self):
        self.providers: List[DataProvider] = [
            APISportsProvider(),
            TheOddsAPIProvider(),
            SportmonksProvider(),
            TheSportsDBProvider(),
            MySportsFeedsProvider(),
            FootballDataProvider(),
        ]
        self.providers.sort(key=lambda p: p.priority)
        self.active_provider: Optional[DataProvider] = None
        self.connection_log: List[Dict] = []
        self._health_check()

    def _log_connection(self, provider_name: str, status: str, detail: str, 
                        matches_found: int = 0, error_type: str = None, 
                        http_code: int = None, response_time_ms: float = None,
                        endpoint_tested: str = None):
        """Log a structured connection attempt for real-time dashboard display."""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "provider": provider_name,
            "status": status,  # SUCCESS, FAIL, TIMEOUT, RATE_LIMIT, NO_KEY, ERROR, EMPTY
            "detail": detail,
            "matches_found": matches_found,
            "error_type": error_type,
            "http_code": http_code,
            "response_time_ms": response_time_ms,
            "endpoint_tested": endpoint_tested,
        }
        self.connection_log.append(entry)
        # Keep only last 100 entries
        if len(self.connection_log) > 100:
            self.connection_log = self.connection_log[-100:]

        # Also log to Python logger
        level = logging.INFO if status == "SUCCESS" else logging.WARNING
        logger.log(level, f"[{provider_name}] {status}: {detail}")

    def get_connection_log_df(self) -> pd.DataFrame:
        """Return connection log as DataFrame for dashboard display."""
        if not self.connection_log:
            return pd.DataFrame(columns=["TIME", "PROVIDER", "STATUS", "HTTP", "MATCHES", "RESPONSE_MS", "DETAIL", "ENDPOINT"])

        df = pd.DataFrame(self.connection_log)
        df = df.rename(columns={
            "timestamp": "TIME",
            "provider": "PROVIDER",
            "status": "STATUS",
            "http_code": "HTTP",
            "matches_found": "MATCHES",
            "response_time_ms": "RESPONSE_MS",
            "detail": "DETAIL",
            "endpoint_tested": "ENDPOINT",
        })
        # Reorder columns
        df = df[["TIME", "PROVIDER", "STATUS", "HTTP", "MATCHES", "RESPONSE_MS", "DETAIL", "ENDPOINT"]]
        return df.iloc[::-1].reset_index(drop=True)  # Most recent first

    def get_provider_status(self) -> List[Dict]:
        """Return connection status for all providers with detailed error info.
        Also logs each test attempt to connection_log."""
        status = []
        for provider in self.providers:
            start_time = time.time()
            try:
                test = provider.get_live_matches()
                elapsed_ms = (time.time() - start_time) * 1000
                is_online = test is not None and len(test) > 0
                match_count = len(test) if test else 0

                status_text = "ONLINE" if is_online else "EMPTY (key valid but no matches today)"
                status.append({
                    "name": provider.name,
                    "status": status_text,
                    "priority": provider.priority,
                    "matches_found": match_count,
                    "error": None,
                    "response_time_ms": round(elapsed_ms, 2),
                })

                self._log_connection(
                    provider_name=provider.name,
                    status="SUCCESS" if is_online else "EMPTY",
                    detail=f"Status check: {status_text}",
                    matches_found=match_count,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_provider_status()",
                )

            except requests.exceptions.HTTPError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                code = e.response.status_code if e.response else "???"
                msg = "INVALID KEY" if code == 403 else ("RATE LIMITED" if code == 429 else f"HTTP {code}")

                status.append({
                    "name": provider.name,
                    "status": f"OFFLINE — {msg}",
                    "priority": provider.priority,
                    "matches_found": 0,
                    "error": str(e)[:80],
                    "response_time_ms": round(elapsed_ms, 2),
                })

                self._log_connection(
                    provider_name=provider.name,
                    status="FAIL",
                    detail=f"Status check failed: {msg}",
                    error_type="HTTPError",
                    http_code=code,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_provider_status()",
                )

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                status.append({
                    "name": provider.name,
                    "status": f"OFFLINE — {type(e).__name__}",
                    "priority": provider.priority,
                    "matches_found": 0,
                    "error": str(e)[:80],
                    "response_time_ms": round(elapsed_ms, 2),
                })

                self._log_connection(
                    provider_name=provider.name,
                    status="ERROR",
                    detail=f"Status check failed: {type(e).__name__}: {str(e)[:80]}",
                    error_type=type(e).__name__,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_provider_status()",
                )
        return status

    def _health_check(self):
        """Test all providers with detailed logging and select the best available."""
        logger.info("=" * 60)
        logger.info("🔍 EMPIRE HEALTH CHECK — Testing all API providers")
        logger.info("=" * 60)

        for provider in self.providers:
            logger.info(f"Testing {provider.name}...")
            start_time = time.time()

            try:
                matches = provider.get_live_matches()
                elapsed_ms = (time.time() - start_time) * 1000

                if matches is not None:
                    match_count = len(matches) if hasattr(matches, '__len__') else 0
                    self.active_provider = provider

                    self._log_connection(
                        provider_name=provider.name,
                        status="SUCCESS",
                        detail=f"Provider active — {match_count} live matches retrieved",
                        matches_found=match_count,
                        response_time_ms=round(elapsed_ms, 2),
                        endpoint_tested="get_live_matches()",
                    )
                    logger.info(f"✅ {provider.name} is ACTIVE with {match_count} matches ({elapsed_ms:.0f}ms)")
                    break
                else:
                    self._log_connection(
                        provider_name=provider.name,
                        status="FAIL",
                        detail="Provider returned None (no response)",
                        response_time_ms=round(elapsed_ms, 2),
                        endpoint_tested="get_live_matches()",
                    )

            except requests.exceptions.HTTPError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                code = e.response.status_code if e.response else None

                if code == 403:
                    detail = "API KEY INVALID or EXPIRED (403) — regenerate key"
                elif code == 401:
                    detail = "API KEY UNAUTHORIZED (401) — check key format"
                elif code == 429:
                    detail = "RATE LIMITED (429) — too many requests, wait and retry"
                elif code == 404:
                    detail = "ENDPOINT NOT FOUND (404) — API path may have changed"
                elif code == 500:
                    detail = "SERVER ERROR (500) — provider server down"
                elif code == 502:
                    detail = "BAD GATEWAY (502) — provider gateway error"
                elif code == 503:
                    detail = "SERVICE UNAVAILABLE (503) — provider maintenance"
                else:
                    detail = f"HTTP ERROR ({code}) — {str(e)[:80]}"

                self._log_connection(
                    provider_name=provider.name,
                    status="FAIL",
                    detail=detail,
                    error_type="HTTPError",
                    http_code=code,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_live_matches()",
                )
                logger.error(f"❌ {provider.name}: {detail}")

            except requests.exceptions.ConnectionError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                detail = f"CONNECTION FAILED — check internet/VPN/firewall. {str(e)[:60]}"
                self._log_connection(
                    provider_name=provider.name,
                    status="FAIL",
                    detail=detail,
                    error_type="ConnectionError",
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_live_matches()",
                )
                logger.error(f"❌ {provider.name}: {detail}")

            except requests.exceptions.Timeout as e:
                elapsed_ms = (time.time() - start_time) * 1000
                detail = f"TIMEOUT — request took too long (>10s). Provider may be slow."
                self._log_connection(
                    provider_name=provider.name,
                    status="TIMEOUT",
                    detail=detail,
                    error_type="Timeout",
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_live_matches()",
                )
                logger.error(f"❌ {provider.name}: {detail}")

            except requests.exceptions.RequestException as e:
                elapsed_ms = (time.time() - start_time) * 1000
                detail = f"REQUEST FAILED — {type(e).__name__}: {str(e)[:80]}"
                self._log_connection(
                    provider_name=provider.name,
                    status="FAIL",
                    detail=detail,
                    error_type=type(e).__name__,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_live_matches()",
                )
                logger.error(f"❌ {provider.name}: {detail}")

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                detail = f"UNEXPECTED ERROR — {type(e).__name__}: {str(e)[:120]}"
                self._log_connection(
                    provider_name=provider.name,
                    status="ERROR",
                    detail=detail,
                    error_type=type(e).__name__,
                    response_time_ms=round(elapsed_ms, 2),
                    endpoint_tested="get_live_matches()",
                )
                logger.error(f"❌ {provider.name}: {detail}")
                logger.debug(traceback.format_exc())

        if not self.active_provider:
            self._log_connection(
                provider_name="SYSTEM",
                status="FAIL",
                detail="NO PROVIDERS AVAILABLE — All APIs failed. Check .env keys and internet connection.",
                endpoint_tested="_health_check()",
            )
            logger.error("No providers available! All API keys missing or invalid.")

    def get_live_matches(self, sport: str = "football", league_id: str = None) -> pd.DataFrame:
        """Fetch live matches from best available provider."""
        all_matches = []

        for provider in self.providers:
            try:
                matches = provider.get_live_matches(sport, league_id)
                if matches:
                    all_matches.extend(matches)
                    logger.info(f"{provider.name}: {len(matches)} live matches")
            except Exception as e:
                logger.warning(f"{provider.name} live fetch failed: {e}")

        # Deduplicate by match_id, prefer higher priority provider
        seen = set()
        unique = []
        for m in sorted(all_matches, key=lambda x: x.provider != self.active_provider.name if self.active_provider else False):
            if m.match_id not in seen:
                seen.add(m.match_id)
                unique.append(m)

        if not unique:
            logger.warning("No live matches from APIs — returning empty DataFrame")
            return pd.DataFrame(columns=[
                "TIME", "LEAGUE", "MATCH", "STATUS", "SCORE", "MIN",
                "HOME", "DRAW", "AWAY", "PREDICTION", "EV", "CONF", "SIGNAL"
            ])

        return pd.DataFrame([m.to_dataframe_row() for m in unique])

    def get_value_opportunities(self, min_ev: float = 0.02) -> pd.DataFrame:
        """Fetch matches with positive EV opportunities using available odds."""
        matches = self.get_live_matches()

        opportunities = []
        for _, row in matches.iterrows():
            # Extract odds safely
            home_odds = APIConfig._safe_float(row.get("HOME"), 0)
            away_odds = APIConfig._safe_float(row.get("AWAY"), 0)
            draw_odds = APIConfig._safe_float(row.get("DRAW"), 0)

            # Skip if no usable odds
            if home_odds <= 1.0 or away_odds <= 1.0:
                continue

            # Calculate implied probabilities
            total = (1/home_odds) + (1/draw_odds if draw_odds > 1 else 0) + (1/away_odds)
            if total == 0:
                continue

            home_prob = (1/home_odds) / total
            away_prob = (1/away_odds) / total
            draw_prob = (1/draw_odds) / total if draw_odds > 1 else 0

            # Try to get real predictions to override implied probabilities
            empire_home = home_prob
            empire_away = away_prob
            empire_draw = draw_prob

            for provider in self.providers:
                try:
                    pred = provider.get_predictions(str(row.get("MATCH", "")).split(" vs ")[0] if " vs " in str(row.get("MATCH", "")) else "")
                    if pred and pred.home_win_prob:
                        empire_home = pred.home_win_prob
                        empire_away = pred.away_win_prob
                        empire_draw = pred.draw_prob
                        break
                except Exception:
                    continue

            ev_home = (empire_home * home_odds) - 1
            ev_away = (empire_away * away_odds) - 1
            ev_draw = (empire_draw * draw_odds) - 1 if draw_odds > 1 else -1

            best_ev = max(ev_home, ev_away, ev_draw)
            if best_ev > min_ev:
                prediction_str = ""
                if best_ev == ev_home:
                    prediction_str = f"Home ({empire_home*100:.0f}%)"
                elif best_ev == ev_away:
                    prediction_str = f"Away ({empire_away*100:.0f}%)"
                else:
                    prediction_str = f"Draw ({empire_draw*100:.0f}%)"

                opportunities.append({
                    "TIME": row["TIME"],
                    "LEAGUE": row["LEAGUE"],
                    "MATCH": row["MATCH"],
                    "STATUS": row["STATUS"],
                    "HOME": home_odds,
                    "DRAW": draw_odds if draw_odds > 1 else "-",
                    "AWAY": away_odds,
                    "PREDICTION": prediction_str,
                    "EV": f"+{best_ev*100:.1f}%",
                    "KELLY": f"${self._kelly_criterion(best_ev, max(home_odds, away_odds, draw_odds), 0.25):.0f}",
                    "CONF": "HIGH" if best_ev > 0.08 else ("MEDIUM" if best_ev > 0.05 else "LOW"),
                    "SIGNAL": "🟢 BUY" if best_ev > 0.05 else "⚪ HOLD",
                })

        if not opportunities:
            logger.info("No value opportunities found at current EV threshold")
            return pd.DataFrame(columns=[
                "TIME", "LEAGUE", "MATCH", "STATUS", "HOME", "DRAW", "AWAY",
                "PREDICTION", "EV", "KELLY", "CONF", "SIGNAL"
            ])

        return pd.DataFrame(opportunities)

    def _kelly_criterion(self, prob: float, odds: float, bankroll_pct: float = 0.25) -> float:
        """Calculate Kelly Criterion stake."""
        if odds <= 1 or prob <= 0:
            return 0
        kelly = (prob * odds - 1) / (odds - 1)
        return max(0, kelly * 10000 * bankroll_pct)  # $10k base bankroll


    def get_match_details(self, match_id: str, provider_hint: str = None) -> Dict:
        """Fetch comprehensive match details by ID across all providers.

        Returns dict with:
        - match_info: basic match data
        - statistics: live match stats (shots, possession, cards, etc)
        - odds: bookmaker odds comparison
        - predictions: AI predictions
        - h2h: head-to-head history (if available)
        - lineup: team lineups (if available)
        """
        result = {
            "match_info": None,
            "statistics": None,
            "odds": [],
            "predictions": None,
            "h2h": None,
            "lineup": None,
            "players": None,
            "source": None
        }

        # Try each provider to find the match
        for provider in self.providers:
            try:
                # Try to get match info
                if provider.name == "API-SPORTS":
                    # Fetch fixture details
                    stats = provider.get_match_stats(match_id)
                    if stats:
                        result["statistics"] = stats
                        result["source"] = "API-SPORTS"

                    # Fetch odds
                    odds = provider.get_odds(match_id)
                    if odds:
                        result["odds"].extend(odds)

                    # Fetch predictions
                    pred = provider.get_predictions(match_id)
                    if pred:
                        result["predictions"] = pred.to_dict() if hasattr(pred, 'to_dict') else pred

                elif provider.name == "TheOddsAPI":
                    odds = provider.get_odds(match_id)
                    if odds:
                        result["odds"].extend(odds)
                        if not result["source"]:
                            result["source"] = "TheOddsAPI"

                elif provider.name == "Sportmonks":
                    pred = provider.get_predictions(match_id)
                    if pred:
                        result["predictions"] = pred.to_dict() if hasattr(pred, 'to_dict') else pred
                        if not result["source"]:
                            result["source"] = "Sportmonks"

                elif provider.name == "TheSportsDB":
                    # TheSportsDB has event details but we need to search by ID
                    pass

            except Exception as e:
                logger.warning(f"{provider.name} detail fetch failed for {match_id}: {e}")
                continue

        # If we found any data, mark as success
        if result["source"] or result["odds"] or result["statistics"]:
            result["found"] = True
        else:
            result["found"] = False

        return result

    def get_matches_by_status(self, status_filter: str = "all", sport: str = "football") -> pd.DataFrame:
        """Fetch matches filtered by status: LIVE, SCHEDULED, FINISHED, ALL."""
        all_matches = []

        for provider in self.providers:
            try:
                if status_filter.lower() == "live":
                    matches = provider.get_live_matches(sport)
                elif status_filter.lower() == "scheduled":
                    matches = provider.get_upcoming_matches(sport, days=7)
                else:
                    # For ALL or FINISHED, fetch both live and upcoming
                    live = provider.get_live_matches(sport) or []
                    upcoming = provider.get_upcoming_matches(sport, days=7) or []
                    matches = live + upcoming

                if matches:
                    # Filter by status if specified
                    if status_filter.lower() not in ["all", "live", "scheduled"]:
                        matches = [m for m in matches if m.status.upper() == status_filter.upper()]
                    all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"{provider.name} status fetch failed: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for m in all_matches:
            if m.match_id not in seen:
                seen.add(m.match_id)
                unique.append(m)

        if not unique:
            return pd.DataFrame(columns=[
                "MATCH_ID", "TIME", "LEAGUE", "MATCH", "STATUS", "SCORE", "MIN",
                "HOME", "DRAW", "AWAY", "PREDICTION", "EV", "CONF", "SIGNAL"
            ])

        return pd.DataFrame([m.to_dataframe_row() for m in unique])

    def get_leagues(self, sport: str = "football") -> List[str]:
        """Return list of available leagues from active providers."""
        leagues = set()
        for provider in self.providers:
            try:
                matches = provider.get_live_matches(sport) or []
                for m in matches:
                    if m.league and m.league != "Unknown":
                        leagues.add(m.league)
            except Exception:
                continue
        return sorted(list(leagues))


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT INTEGRATION HELPERS
# ════════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    """Streamlit-friendly data interface for EMPIRE dashboard."""

    def __init__(self):
        self.router = EmpireDataRouter()
        self.last_refresh = datetime.now()
        self.refresh_interval = 30  # seconds

    @property
    def is_live(self) -> bool:
        """Property to check if live data is available."""
        return self.router.active_provider is not None

    @property
    def missing_keys(self) -> List[str]:
        """Property to return missing API keys."""
        return APIConfig.get_missing_keys()

    @property
    def connection_log(self) -> List[Dict]:
        """Property to access router connection log."""
        return self.router.connection_log

    def get_connection_log_df(self) -> pd.DataFrame:
        """Get real-time API connection log for dashboard display."""
        return self.router.get_connection_log_df()

    def get_live_matches_df(self) -> pd.DataFrame:
        """Get live matches for dashboard display."""
        return self.router.get_live_matches()

    def get_upcoming_matches_df(self) -> pd.DataFrame:
        """Get upcoming matches for dashboard display."""
        all_matches = []
        for provider in self.router.providers:
            try:
                matches = provider.get_upcoming_matches()
                if matches:
                    all_matches.extend(matches)
            except Exception:
                pass

        if not all_matches:
            return pd.DataFrame(columns=["TIME", "LEAGUE", "MATCH", "STATUS", "HOME", "DRAW", "AWAY", "PREDICTION"])

        return pd.DataFrame([m.to_dataframe_row() for m in all_matches])

    def get_value_opportunities_df(self) -> pd.DataFrame:
        """Get value betting opportunities."""
        return self.router.get_value_opportunities()

    def get_odds_comparison(self, match_id: str) -> pd.DataFrame:
        """Get odds comparison across bookmakers."""
        # Aggregate odds from all providers
        all_odds = []
        for provider in self.router.providers:
            try:
                odds = provider.get_odds(match_id)
                all_odds.extend(odds)
            except Exception:
                pass

        if not all_odds:
            logger.warning(f"No odds found for match {match_id}")
            return pd.DataFrame(columns=["BOOKMAKER", "MARKET", "1", "X", "2", "O", "U", "TIME"])

        return pd.DataFrame([o.to_dataframe_row() for o in all_odds])

    def should_refresh(self) -> bool:
        """Check if data needs refresh."""
        return (datetime.now() - self.last_refresh).seconds > self.refresh_interval

    def mark_refreshed(self):
        """Update last refresh timestamp."""
        self.last_refresh = datetime.now()


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 EMPIRE SPORT DATA LAYER — Self-Test")
    print("=" * 60)

    # Check configuration
    missing = APIConfig.get_missing_keys()
    if missing:
        print("⚠️  Missing API keys: " + ", ".join(missing))
        print("Set these as environment variables to enable live data.")
    else:
        print("✅ All API keys configured")
    router = EmpireDataRouter()

    print("📡 Fetching live matches...")
    live = router.get_live_matches()
    print(f"✅ Retrieved {len(live)} live matches")
    if not live.empty:
        print(live.head())

    print("💰 Fetching value opportunities...")
    value = router.get_value_opportunities()
    print(f"✅ Found {len(value)} value opportunities")
    if not value.empty:
        print(value.head())

    print("" + "=" * 60)
    print("EMPIRE Data Layer ready for dashboard integration.")
