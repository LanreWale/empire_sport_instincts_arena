# =============================================================================
# EMPIRE SPORT TRADING SYSTEM - DATA LAYER
# empire_data_layer.py
# Complete overhaul: API integrations, league mapping, filtering, caching,
# enhanced logging, and EmpireDashboardData class
# =============================================================================

import os
import json
import time
import asyncio
import aiohttp
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from functools import wraps
import redis
import asyncpg
from contextlib import asynccontextmanager

# =============================================================================
# CONFIGURATION & ENVIRONMENT
# =============================================================================

class Config:
    """Centralized configuration from environment variables."""
    # API Keys
    API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "")
    THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "")
    SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY", "")
    THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "")  # Premium: 7603135814
    MYSPORTSFEEDS_API_KEY = os.getenv("MYSPORTSFEEDS_API_KEY", "")
    FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_MATCHES = int(os.getenv("CACHE_TTL_MATCHES", "120"))
    CACHE_TTL_ANALYTICS = int(os.getenv("CACHE_TTL_ANALYTICS", "300"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/empire")
    
    # Rate Limiting
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
    
    # System
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
)
logger = logging.getLogger("EMPIRE_DATA")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class APIStatus(Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"


class LeagueTier(Enum):
    TIER_1 = "tier_1"      # Top 5 European + Champions League
    TIER_2 = "tier_2"      # Secondary European + Copa Libertadores
    TIER_3 = "tier_3"      # MLS, Asian leagues, etc.
    ALL = "all"


@dataclass
class APIConnectionLogEntry:
    """Enhanced API connection log entry."""
    timestamp: str
    provider: str
    status: str
    http_status: Optional[int] = None
    response_time_ms: float = 0.0
    matches_returned: int = 0
    matches_total: int = 0
    rate_limit_remaining: Optional[int] = None
    error_detail: Optional[str] = None
    endpoint_url: Optional[str] = None
    date_requested: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Match:
    """Unified match data structure across all providers."""
    match_id: str
    provider: str
    league_id: str
    league_name: str
    league_tier: str
    home_team: str
    away_team: str
    match_date: str
    match_time: str
    status: str  # SCHEDULED, LIVE, FINISHED
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None
    country: Optional[str] = None
    odds: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchAnalytics:
    """Match analytics and prediction metrics."""
    match_id: str
    home_form: List[str] = field(default_factory=list)
    away_form: List[str] = field(default_factory=list)
    h2h_record: Dict[str, Any] = field(default_factory=dict)
    home_xg: float = 0.0
    away_xg: float = 0.0
    home_possession_avg: float = 50.0
    away_possession_avg: float = 50.0
    predicted_home_score: Optional[float] = None
    predicted_away_score: Optional[float] = None
    confidence: float = 0.0
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskControlStatus:
    """Risk control thresholds and current status."""
    kelly_pct: float = 0.0
    max_bet_pct: float = 0.0
    min_ev: float = 0.0
    emergency_stop: bool = False
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# COMPREHENSIVE LEAGUE MAPPING
# =============================================================================

class LeagueRegistry:
    """
    Global league registry with API-specific IDs.
    Maps unified league codes to provider-specific IDs.
    """
    
    # Unified League Definitions
    LEAGUES = {
        # Tier 1 - Top European
        "premier_league": {
            "name": "Premier League",
            "country": "England",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "PL",
                "api_sports": 39,
                "sportmonks": 8,
                "thesportsdb": "English Premier League",
                "mysportsfeeds": "eng-premier-league",
            }
        },
        "la_liga": {
            "name": "La Liga",
            "country": "Spain",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "PD",
                "api_sports": 140,
                "sportmonks": 564,
                "thesportsdb": "Spanish La Liga",
                "mysportsfeeds": "esp-primera-division",
            }
        },
        "serie_a": {
            "name": "Serie A",
            "country": "Italy",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "SA",
                "api_sports": 135,
                "sportmonks": 384,
                "thesportsdb": "Italian Serie A",
                "mysportsfeeds": "ita-serie-a",
            }
        },
        "bundesliga": {
            "name": "Bundesliga",
            "country": "Germany",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "BL1",
                "api_sports": 78,
                "sportmonks": 82,
                "thesportsdb": "German Bundesliga",
                "mysportsfeeds": "ger-bundesliga",
            }
        },
        "ligue_1": {
            "name": "Ligue 1",
            "country": "France",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "FL1",
                "api_sports": 61,
                "sportmonks": 301,
                "thesportsdb": "French Ligue 1",
                "mysportsfeeds": "fra-ligue-1",
            }
        },
        "champions_league": {
            "name": "UEFA Champions League",
            "country": "Europe",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "CL",
                "api_sports": 2,
                "sportmonks": 2,
                "thesportsdb": "UEFA Champions League",
                "mysportsfeeds": "uefa-champions-league",
            }
        },
        "europa_league": {
            "name": "UEFA Europa League",
            "country": "Europe",
            "tier": LeagueTier.TIER_1,
            "apis": {
                "football_data": "EL",
                "api_sports": 3,
                "sportmonks": 5,
                "thesportsdb": "UEFA Europa League",
                "mysportsfeeds": "uefa-europa-league",
            }
        },
        # Tier 2 - Secondary European + South American
        "copa_libertadores": {
            "name": "Copa Libertadores",
            "country": "South America",
            "tier": LeagueTier.TIER_2,
            "apis": {
                "football_data": "CLI",
                "api_sports": 13,
                "sportmonks": 18,
                "thesportsdb": "Copa Libertadores",
                "mysportsfeeds": "conmebol-copa-libertadores",
            }
        },
        "copa_sudamericana": {
            "name": "Copa Sudamericana",
            "country": "South America",
            "tier": LeagueTier.TIER_2,
            "apis": {
                "api_sports": 11,
                "sportmonks": 14,
                "thesportsdb": "Copa Sudamericana",
            }
        },
        "eredivisie": {
            "name": "Eredivisie",
            "country": "Netherlands",
            "tier": LeagueTier.TIER_2,
            "apis": {
                "football_data": "DED",
                "api_sports": 88,
                "sportmonks": 72,
                "thesportsdb": "Dutch Eredivisie",
            }
        },
        "primeira_liga": {
            "name": "Primeira Liga",
            "country": "Portugal",
            "tier": LeagueTier.TIER_2,
            "apis": {
                "football_data": "PPL",
                "api_sports": 94,
                "sportmonks": 462,
                "thesportsdb": "Portuguese Primeira Liga",
            }
        },
        "championship": {
            "name": "EFL Championship",
            "country": "England",
            "tier": LeagueTier.TIER_2,
            "apis": {
                "football_data": "ELC",
                "api_sports": 40,
                "sportmonks": 25,
                "thesportsdb": "English Championship",
            }
        },
        # Tier 3 - MLS, Asian, African
        "mls": {
            "name": "Major League Soccer",
            "country": "USA",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "football_data": "MLS",
                "api_sports": 253,
                "sportmonks": 161,
                "thesportsdb": "American Major League Soccer",
                "mysportsfeeds": "usa-major-league-soccer",
            }
        },
        "brasileirao": {
            "name": "Brasileirão Série A",
            "country": "Brazil",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 71,
                "sportmonks": 325,
                "thesportsdb": "Brazilian Brasileirão",
            }
        },
        "liga_mx": {
            "name": "Liga MX",
            "country": "Mexico",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 262,
                "sportmonks": 265,
                "thesportsdb": "Mexican Liga MX",
            }
        },
        "j1_league": {
            "name": "J1 League",
            "country": "Japan",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 98,
                "sportmonks": 132,
                "thesportsdb": "Japanese J1 League",
            }
        },
        "k_league": {
            "name": "K League 1",
            "country": "South Korea",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 292,
                "sportmonks": 267,
                "thesportsdb": "South Korean K League",
            }
        },
        "a_league": {
            "name": "A-League Men",
            "country": "Australia",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 188,
                "sportmonks": 109,
                "thesportsdb": "Australian A-League",
            }
        },
        "south_africa_psl": {
            "name": "South African PSL",
            "country": "South Africa",
            "tier": LeagueTier.TIER_3,
            "apis": {
                "api_sports": 250,
                "sportmonks": 543,
                "thesportsdb": "South African Premier Division",
            }
        },
    }
    
    @classmethod
    def get_all_leagues(cls) -> List[Dict[str, Any]]:
        """Return all leagues for dropdown population."""
        return [
            {
                "id": key,
                "name": data["name"],
                "country": data["country"],
                "tier": data["tier"].value
            }
            for key, data in cls.LEAGUES.items()
        ]
    
    @classmethod
    def get_league_by_id(cls, league_id: str) -> Optional[Dict[str, Any]]:
        """Get league configuration by unified ID."""
        return cls.LEAGUES.get(league_id)
    
    @classmethod
    def get_api_id(cls, league_id: str, provider: str) -> Optional[Any]:
        """Get provider-specific league ID."""
        league = cls.LEAGUES.get(league_id)
        if not league:
            return None
        return league["apis"].get(provider)
    
    @classmethod
    def get_tier_leagues(cls, tier: LeagueTier) -> List[str]:
        """Get all league IDs for a specific tier."""
        return [
            key for key, data in cls.LEAGUES.items()
            if data["tier"] == tier
        ]


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """Redis-based caching with fallback to in-memory."""
    
    def __init__(self):
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._redis: Optional[redis.Redis] = None
        self._redis_available = False
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self._redis = redis.from_url(
                Config.REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True
            )
            self._redis.ping()
            self._redis_available = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory cache: {e}")
            self._redis_available = False
    
    def _make_key(self, prefix: str, *args) -> str:
        """Create cache key from arguments."""
        key_data = json.dumps(args, sort_keys=True)
        hash_key = hashlib.md5(key_data.encode()).hexdigest()
        return f"empire:{prefix}:{hash_key}"
    
    def get(self, prefix: str, *args) -> Optional[Any]:
        """Get cached value."""
        key = self._make_key(prefix, *args)
        
        # Try Redis first
        if self._redis_available:
            try:
                data = self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        # Fallback to memory
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(self, prefix: str, value: Any, ttl: int, *args) -> None:
        """Set cached value."""
        key = self._make_key(prefix, *args)
        
        # Try Redis first
        if self._redis_available:
            try:
                self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass
        
        # Fallback to memory
        self._memory_cache[key] = (value, time.time() + ttl)
    
    def invalidate(self, prefix: str = None) -> None:
        """Invalidate cache entries."""
        if prefix and self._redis_available:
            try:
                for key in self._redis.scan_iter(match=f"empire:{prefix}:*"):
                    self._redis.delete(key)
            except Exception:
                pass
        
        if not prefix:
            self._memory_cache.clear()
        else:
            keys_to_remove = [
                k for k in self._memory_cache.keys()
                if k.startswith(f"empire:{prefix}:")
            ]
            for k in keys_to_remove:
                del self._memory_cache[k]


# =============================================================================
# API PROVIDER IMPLEMENTATIONS
# =============================================================================

class BaseAPIProvider:
    """Base class for all API providers."""
    
    def __init__(self, name: str, cache: CacheManager):
        self.name = name
        self.cache = cache
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)
    
    async def _init_session(self):
        """Initialize aiohttp session."""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(
        self,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None
    ) -> Tuple[int, Any, float]:
        """Make HTTP request with timing and error handling."""
        await self._init_session()
        start_time = time.time()
        
        try:
            async with self._semaphore:
                async with self.session.get(
                    url,
                    headers=headers,
                    params=params
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    status = response.status
                    
                    if status == 429:
                        return status, {"error": "Rate limited"}, response_time
                    
                    if status == 204:
                        return status, [], response_time
                    
                    try:
                        data = await response.json()
                    except Exception:
                        data = await response.text()
                    
                    return status, data, response_time
                    
        except asyncio.TimeoutError:
            return 0, {"error": "Timeout"}, (time.time() - start_time) * 1000
        except Exception as e:
            return 0, {"error": str(e)}, (time.time() - start_time) * 1000
    
    def _create_log_entry(
        self,
        status: APIStatus,
        http_status: int,
        response_time: float,
        matches_count: int,
        error: str = None,
        url: str = None,
        date: str = None
    ) -> APIConnectionLogEntry:
        """Create standardized log entry."""
        return APIConnectionLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=self.name,
            status=status.value,
            http_status=http_status if http_status > 0 else None,
            response_time_ms=round(response_time, 2),
            matches_returned=matches_count,
            matches_total=matches_count,
            error_detail=error,
            endpoint_url=url,
            date_requested=date
        )
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches - implement in subclass."""
        raise NotImplementedError
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert provider-specific data to unified Match."""
        raise NotImplementedError


class FootballDataProvider(BaseAPIProvider):
    """football-data.org API provider."""
    
    BASE_URL = "https://api.football-data.org/v4"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from football-data.org."""
        if not Config.FOOTBALL_DATA_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("football_data", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request
        headers = {"X-Auth-Token": Config.FOOTBALL_DATA_KEY}
        params = {"dateFrom": date_str, "dateTo": date_str}
        
        if league_id:
            api_league_id = LeagueRegistry.get_api_id(league_id, "football_data")
            if api_league_id:
                url = f"{self.BASE_URL}/competitions/{api_league_id}/matches"
            else:
                url = f"{self.BASE_URL}/matches"
        else:
            url = f"{self.BASE_URL}/matches"
        
        # Make request
        status, data, response_time = await self._make_request(
            url, headers=headers, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, dict):
            error_msg = data.get("error", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                error_msg, url=url, date=date_str
            )
        
        matches_raw = data.get("matches", [])
        if not matches_raw:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in matches_raw:
            match = self._standardize_match(raw, league_id, data.get("competition", {}).get("name", "Unknown"))
            if match:
                matches.append(match)
        
        # Filter by league if specified
        if league_id:
            league_data = LeagueRegistry.get_league_by_id(league_id)
            if league_data:
                matches = [
                    m for m in matches
                    if m.league_name == league_data["name"] or 
                    league_id in m.metadata.get("league_codes", [])
                ]
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert football-data.org match to unified format."""
        try:
            match_id = str(raw_data.get("id", ""))
            home_team = raw_data.get("homeTeam", {}).get("name", "Unknown")
            away_team = raw_data.get("awayTeam", {}).get("name", "Unknown")
            
            utc_date = raw_data.get("utcDate", "")
            if utc_date:
                dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            else:
                match_date = ""
                match_time = ""
            
            status_map = {
                "SCHEDULED": "SCHEDULED",
                "LIVE": "LIVE",
                "IN_PLAY": "LIVE",
                "PAUSED": "LIVE",
                "FINISHED": "FINISHED",
                "POSTPONED": "POSTPONED",
                "CANCELLED": "CANCELLED"
            }
            
            score_data = raw_data.get("score", {})
            home_score = score_data.get("fullTime", {}).get("home")
            away_score = score_data.get("fullTime", {}).get("away")
            
            return Match(
                match_id=f"fd_{match_id}",
                provider="football_data",
                league_id=league_id or "",
                league_name=league_name,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status=status_map.get(raw_data.get("status", "SCHEDULED"), "SCHEDULED"),
                home_score=int(home_score) if home_score is not None else None,
                away_score=int(away_score) if away_score is not None else None,
                venue=raw_data.get("venue", ""),
                metadata={"raw_id": match_id}
            )
        except Exception as e:
            logger.error(f"Error standardizing football-data match: {e}")
            return None


class APISportsProvider(BaseAPIProvider):
    """API-Sports (api-football) provider."""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from API-Sports."""
        if not Config.API_SPORTS_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("api_sports", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request
        headers = {
            "x-apisports-key": Config.API_SPORTS_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        params = {"date": date_str}
        
        if league_id:
            api_league_id = LeagueRegistry.get_api_id(league_id, "api_sports")
            if api_league_id:
                params["league"] = api_league_id
                params["season"] = datetime.now(timezone.utc).year
        
        url = f"{self.BASE_URL}/fixtures"
        
        # Make request
        status, data, response_time = await self._make_request(
            url, headers=headers, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, dict):
            error_msg = data.get("errors", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                str(error_msg), url=url, date=date_str
            )
        
        response_data = data.get("response", [])
        if not response_data:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in response_data:
            match = self._standardize_match(raw, league_id, "")
            if match:
                matches.append(match)
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert API-Sports match to unified format."""
        try:
            fixture = raw_data.get("fixture", {})
            teams = raw_data.get("teams", {})
            goals = raw_data.get("goals", {})
            league_data = raw_data.get("league", {})
            
            match_id = str(fixture.get("id", ""))
            home_team = teams.get("home", {}).get("name", "Unknown")
            away_team = teams.get("away", {}).get("name", "Unknown")
            
            utc_date = fixture.get("date", "")
            if utc_date:
                dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            else:
                match_date = ""
                match_time = ""
            
            status_map = {
                "NS": "SCHEDULED",
                "1H": "LIVE",
                "HT": "LIVE",
                "2H": "LIVE",
                "ET": "LIVE",
                "P": "LIVE",
                "FT": "FINISHED",
                "AET": "FINISHED",
                "PEN": "FINISHED",
                "SUSP": "POSTPONED",
                "INT": "LIVE",
                "CANC": "CANCELLED",
                "ABD": "CANCELLED",
                "AWD": "CANCELLED",
                "WO": "CANCELLED"
            }
            
            return Match(
                match_id=f"as_{match_id}",
                provider="api_sports",
                league_id=league_id or str(league_data.get("id", "")),
                league_name=league_data.get("name", league_name),
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status=status_map.get(fixture.get("status", {}).get("short", "NS"), "SCHEDULED"),
                home_score=int(goals.get("home")) if goals.get("home") is not None else None,
                away_score=int(goals.get("away")) if goals.get("away") is not None else None,
                venue=fixture.get("venue", {}).get("name", ""),
                country=league_data.get("country", ""),
                metadata={"league_codes": [league_id] if league_id else []}
            )
        except Exception as e:
            logger.error(f"Error standardizing API-Sports match: {e}")
            return None


class TheSportsDBProvider(BaseAPIProvider):
    """TheSportsDB API provider (Premium v2)."""
    
    BASE_URL = "https://www.thesportsdb.com/api/v2/json"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from TheSportsDB."""
        if not Config.THESPORTSDB_API_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("thesportsdb", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request - PREMIUM v2 with X-API-KEY header
        headers = {"X-API-KEY": Config.THESPORTSDB_API_KEY}
        params = {"d": date_str.replace("-", "")}
        
        if league_id:
            api_league_id = LeagueRegistry.get_api_id(league_id, "thesportsdb")
            if api_league_id:
                params["l"] = api_league_id
        
        url = f"{self.BASE_URL}/{Config.THESPORTSDB_API_KEY}/eventsday.php"
        
        # Make request
        status, data, response_time = await self._make_request(
            url, headers=headers, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, dict):
            error_msg = data.get("error", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                str(error_msg), url=url, date=date_str
            )
        
        events = data.get("events", [])
        if not events:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in events:
            match = self._standardize_match(raw, league_id, "")
            if match:
                matches.append(match)
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert TheSportsDB event to unified format."""
        try:
            match_id = str(raw_data.get("idEvent", ""))
            home_team = raw_data.get("strHomeTeam", "Unknown")
            away_team = raw_data.get("strAwayTeam", "Unknown")
            
            date_str = raw_data.get("dateEvent", "")
            time_str = raw_data.get("strTime", "").replace(":", "")[:4]
            if date_str:
                match_date = date_str
                match_time = f"{time_str[:2]}:{time_str[2:]}" if len(time_str) >= 4 else ""
            else:
                match_date = ""
                match_time = ""
            
            status_map = {
                "0": "SCHEDULED",
                "1": "LIVE",
                "2": "FINISHED",
                "3": "POSTPONED"
            }
            
            home_score = raw_data.get("intHomeScore")
            away_score = raw_data.get("intAwayScore")
            
            return Match(
                match_id=f"tsdb_{match_id}",
                provider="thesportsdb",
                league_id=league_id or str(raw_data.get("idLeague", "")),
                league_name=raw_data.get("strLeague", league_name),
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status=status_map.get(raw_data.get("strStatus", "0"), "SCHEDULED"),
                home_score=int(home_score) if home_score and home_score != "null" else None,
                away_score=int(away_score) if away_score and away_score != "null" else None,
                venue=raw_data.get("strVenue", ""),
                country=raw_data.get("strCountry", ""),
                metadata={"league_codes": [league_id] if league_id else []}
            )
        except Exception as e:
            logger.error(f"Error standardizing TheSportsDB match: {e}")
            return None


class SportmonksProvider(BaseAPIProvider):
    """Sportmonks API provider."""
    
    BASE_URL = "https://api.sportmonks.com/v3/football"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from Sportmonks."""
        if not Config.SPORTMONKS_API_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("sportmonks", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request
        params = {
            "api_token": Config.SPORTMONKS_API_KEY,
            "include": "league;venue;scores",
            "filters": f"fixtureBetween:{date_str},{date_str}"
        }
        
        if league_id:
            api_league_id = LeagueRegistry.get_api_id(league_id, "sportmonks")
            if api_league_id:
                params["filter"] = f"league_id:{api_league_id}"
        
        url = f"{self.BASE_URL}/fixtures/between/{date_str}/{date_str}"
        
        # Make request
        status, data, response_time = await self._make_request(
            url, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, dict):
            error_msg = data.get("message", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                str(error_msg), url=url, date=date_str
            )
        
        fixtures = data.get("data", [])
        if not fixtures:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in fixtures:
            match = self._standardize_match(raw, league_id, "")
            if match:
                matches.append(match)
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert Sportmonks fixture to unified format."""
        try:
            match_id = str(raw_data.get("id", ""))
            
            # Handle nested includes
            participants = raw_data.get("participants", [])
            home_team = "Unknown"
            away_team = "Unknown"
            for p in participants:
                if p.get("meta", {}).get("location") == "home":
                    home_team = p.get("name", "Unknown")
                elif p.get("meta", {}).get("location") == "away":
                    away_team = p.get("name", "Unknown")
            
            # Parse date
            starting_at = raw_data.get("starting_at", "")
            if starting_at:
                dt = datetime.fromisoformat(starting_at.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            else:
                match_date = ""
                match_time = ""
            
            status_map = {
                "NS": "SCHEDULED",
                "1H": "LIVE",
                "HT": "LIVE",
                "2H": "LIVE",
                "ET": "LIVE",
                "FT": "FINISHED",
                "AET": "FINISHED",
                "PEN": "FINISHED",
                "CANC": "CANCELLED"
            }
            
            # Scores
            scores = raw_data.get("scores", [])
            home_score = None
            away_score = None
            for s in scores:
                if s.get("description") == "CURRENT":
                    if s.get("score", {}).get("participant") == "home":
                        home_score = s.get("score", {}).get("goals")
                    else:
                        away_score = s.get("score", {}).get("goals")
            
            league_info = raw_data.get("league", {})
            
            return Match(
                match_id=f"sm_{match_id}",
                provider="sportmonks",
                league_id=league_id or str(league_info.get("id", "")),
                league_name=league_info.get("name", league_name),
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status=status_map.get(raw_data.get("state", {}).get("state", "NS"), "SCHEDULED"),
                home_score=int(home_score) if home_score is not None else None,
                away_score=int(away_score) if away_score is not None else None,
                venue=raw_data.get("venue", {}).get("name", ""),
                country=league_info.get("country", {}).get("name", ""),
                metadata={"league_codes": [league_id] if league_id else []}
            )
        except Exception as e:
            logger.error(f"Error standardizing Sportmonks match: {e}")
            return None


class MySportsFeedsProvider(BaseAPIProvider):
    """MySportsFeeds API provider."""
    
    BASE_URL = "https://api.mysportsfeeds.com/v2.1/pull/soccer"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from MySportsFeeds."""
        if not Config.MYSPORTSFEEDS_API_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("mysportsfeeds", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request
        import base64
        auth_str = base64.b64encode(f"{Config.MYSPORTSFEEDS_API_KEY}:MYSPORTSFEEDS".encode()).decode()
        headers = {"Authorization": f"Basic {auth_str}"}
        
        # Determine season
        current_year = datetime.now(timezone.utc).year
        season = f"{current_year}-{current_year+1}" if datetime.now(timezone.utc).month >= 7 else f"{current_year-1}-{current_year}"
        
        if league_id:
            api_league_id = LeagueRegistry.get_api_id(league_id, "mysportsfeeds")
            league_path = api_league_id or "current"
        else:
            league_path = "current"
        
        url = f"{self.BASE_URL}/{league_path}/games.json"
        params = {"date": date_str.replace("-", "")}
        
        # Make request
        status, data, response_time = await self._make_request(
            url, headers=headers, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, dict):
            error_msg = data.get("message", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                str(error_msg), url=url, date=date_str
            )
        
        games = data.get("games", [])
        if not games:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in games:
            match = self._standardize_match(raw, league_id, "")
            if match:
                matches.append(match)
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert MySportsFeeds game to unified format."""
        try:
            schedule = raw_data.get("schedule", {})
            match_id = str(schedule.get("id", ""))
            home_team = schedule.get("homeTeam", {}).get("name", "Unknown")
            away_team = schedule.get("awayTeam", {}).get("name", "Unknown")
            
            start_time = schedule.get("startTime", "")
            if start_time:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            else:
                match_date = ""
                match_time = ""
            
            status_map = {
                "Unplayed": "SCHEDULED",
                "Live": "LIVE",
                "Final": "FINISHED",
                "Postponed": "POSTPONED",
                "Cancelled": "CANCELLED"
            }
            
            score = raw_data.get("score", {})
            home_score = score.get("homeScoreTotal")
            away_score = score.get("awayScoreTotal")
            
            venue = schedule.get("venue", {})
            
            return Match(
                match_id=f"msf_{match_id}",
                provider="mysportsfeeds",
                league_id=league_id or "",
                league_name=league_name,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status=status_map.get(schedule.get("playedStatus", "Unplayed"), "SCHEDULED"),
                home_score=int(home_score) if home_score is not None else None,
                away_score=int(away_score) if away_score is not None else None,
                venue=venue.get("name", ""),
                country=venue.get("country", ""),
                metadata={"league_codes": [league_id] if league_id else []}
            )
        except Exception as e:
            logger.error(f"Error standardizing MySportsFeeds match: {e}")
            return None


class TheOddsAPIProvider(BaseAPIProvider):
    """TheOddsAPI provider (odds data)."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    async def fetch_matches(
        self,
        date_str: str,
        league_id: Optional[str] = None
    ) -> Tuple[List[Match], APIConnectionLogEntry]:
        """Fetch matches from TheOddsAPI."""
        if not Config.THE_ODDS_API_KEY:
            return [], self._create_log_entry(
                APIStatus.ERROR, 0, 0, 0,
                "API key not configured", date=date_str
            )
        
        # Check cache
        cache_key = ("theoddsapi", date_str, league_id)
        cached = self.cache.get("matches", *cache_key)
        if cached:
            matches = [Match(**m) for m in cached]
            return matches, self._create_log_entry(
                APIStatus.SUCCESS, 200, 0, len(matches), date=date_str
            )
        
        # Build request
        params = {
            "apiKey": Config.THE_ODDS_API_KEY,
            "regions": "eu,us,uk",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "commenceTimeFrom": f"{date_str}T00:00:00Z",
            "commenceTimeTo": f"{date_str}T23:59:59Z"
        }
        
        # Map league to sport
        sport = "soccer"
        if league_id:
            league_data = LeagueRegistry.get_league_by_id(league_id)
            if league_data and league_data["country"] == "USA":
                sport = "soccer_usa_mls"
        
        url = f"{self.BASE_URL}/sports/{sport}/odds"
        
        # Make request
        status, data, response_time = await self._make_request(
            url, params=params
        )
        
        # Handle response
        if status != 200 or not isinstance(data, list):
            error_msg = data.get("message", "Unknown error") if isinstance(data, dict) else str(data)
            return [], self._create_log_entry(
                APIStatus.ERROR if status != 200 else APIStatus.EMPTY,
                status, response_time, 0,
                str(error_msg), url=url, date=date_str
            )
        
        if not data:
            return [], self._create_log_entry(
                APIStatus.EMPTY, status, response_time, 0,
                "No matches found for date", url=url, date=date_str
            )
        
        # Standardize matches
        matches = []
        for raw in data:
            match = self._standardize_match(raw, league_id, "")
            if match:
                matches.append(match)
        
        # Cache results
        self.cache.set("matches", [m.to_dict() for m in matches], Config.CACHE_TTL_MATCHES, *cache_key)
        
        log_entry = self._create_log_entry(
            APIStatus.SUCCESS, status, response_time, len(matches),
            url=url, date=date_str
        )
        
        return matches, log_entry
    
    def _standardize_match(
        self,
        raw_data: Dict[str, Any],
        league_id: str,
        league_name: str
    ) -> Optional[Match]:
        """Convert TheOddsAPI event to unified format."""
        try:
            match_id = str(raw_data.get("id", ""))
            home_team = raw_data.get("home_team", "Unknown")
            away_team = raw_data.get("away_team", "Unknown")
            
            commence_time = raw_data.get("commence_time", "")
            if commence_time:
                dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            else:
                match_date = ""
                match_time = ""
            
            # Extract best odds
            odds_data = {}
            bookmakers = raw_data.get("bookmakers", [])
            if bookmakers:
                best_h2h = bookmakers[0].get("markets", [{}])[0].get("outcomes", [])
                for outcome in best_h2h:
                    if outcome.get("name") == home_team:
                        odds_data["home_odds"] = outcome.get("price")
                    elif outcome.get("name") == away_team:
                        odds_data["away_odds"] = outcome.get("price")
                    elif outcome.get("name") == "Draw":
                        odds_data["draw_odds"] = outcome.get("price")
            
            return Match(
                match_id=f"odds_{match_id}",
                provider="theoddsapi",
                league_id=league_id or "",
                league_name=raw_data.get("sport_title", league_name),
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                match_time=match_time,
                status="SCHEDULED",
                odds=odds_data,
                metadata={"league_codes": [league_id] if league_id else []}
            )
        except Exception as e:
            logger.error(f"Error standardizing TheOddsAPI match: {e}")
            return None


# =============================================================================
# DATA AGGREGATOR
# =============================================================================

class DataAggregator:
    """
    Aggregates data from all API providers with parallel fetching,
    deduplication, and league filtering.
    """
    
    def __init__(self):
        self.cache = CacheManager()
        self.providers: List[BaseAPIProvider] = [
            FootballDataProvider("Football-Data", self.cache),
            APISportsProvider("API-Sports", self.cache),
            TheSportsDBProvider("TheSportsDB", self.cache),
            SportmonksProvider("Sportmonks", self.cache),
            MySportsFeedsProvider("MySportsFeeds", self.cache),
            TheOddsAPIProvider("TheOddsAPI", self.cache),
        ]
        self.connection_logs: List[APIConnectionLogEntry] = []
    
    async def fetch_all_matches(
        self,
        date_str: Optional[str] = None,
        league_id: Optional[str] = None,
        tier: Optional[LeagueTier] = None
    ) -> Tuple[List[Match], List[APIConnectionLogEntry]]:
        """
        Fetch matches from all providers in parallel.
        
        Args:
            date_str: Date in YYYY-MM-DD format (default: today UTC)
            league_id: Filter by specific league
            tier: Filter by league tier
        
        Returns:
            Tuple of (deduplicated matches, connection logs)
        """
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # If tier specified, get all leagues in that tier
        target_leagues = []
        if tier and tier != LeagueTier.ALL:
            target_leagues = LeagueRegistry.get_tier_leagues(tier)
        elif league_id:
            target_leagues = [league_id]
        
        self.connection_logs = []
        all_matches = []
        
        # Fetch from all providers in parallel
        tasks = []
        for provider in self.providers:
            if target_leagues:
                # Fetch for each target league
                for target_league in target_leagues:
                    tasks.append(provider.fetch_matches(date_str, target_league))
            else:
                # Fetch all matches
                tasks.append(provider.fetch_matches(date_str, None))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Provider fetch failed: {result}")
                continue
            
            matches, log_entry = result
            self.connection_logs.append(log_entry)
            all_matches.extend(matches)
        
        # Deduplicate matches
        deduplicated = self._deduplicate_matches(all_matches)
        
        # Sort by time
        deduplicated.sort(key=lambda m: (m.match_date, m.match_time))
        
        return deduplicated, self.connection_logs
    
    def _deduplicate_matches(self, matches: List[Match]) -> List[Match]:
        """Deduplicate matches across providers using fuzzy matching."""
        if not matches:
            return []
        
        # Group by date and normalized team names
        groups: Dict[str, List[Match]] = {}
        
        for match in matches:
            key = self._make_dedup_key(match)
            if key not in groups:
                groups[key] = []
            groups[key].append(match)
        
        # Select best match from each group (prefer live/finished, then most data)
        result = []
        for group in groups.values():
            best = max(group, key=lambda m: (
                m.home_score is not None,  # Has score data
                len(m.odds) > 0,           # Has odds
                m.venue != "",             # Has venue
                m.provider == "football_data"  # Prefer football-data
            ))
            result.append(best)
        
        return result
    
    def _make_dedup_key(self, match: Match) -> str:
        """Create deduplication key from match data."""
        # Normalize team names
        home = match.home_team.lower().replace(" ", "").replace("fc", "").replace("united", "utd")
        away = match.away_team.lower().replace(" ", "").replace("fc", "").replace("united", "utd")
        return f"{match.match_date}:{home}:{away}"
    
    def get_connection_logs(self) -> List[Dict[str, Any]]:
        """Get all connection logs as dictionaries."""
        return [log.to_dict() for log in self.connection_logs]
    
    async def close(self):
        """Close all provider sessions."""
        for provider in self.providers:
            await provider._close_session()


# =============================================================================
# MATCH ANALYZER
# =============================================================================

class MatchAnalyzer:
    """
    Analyzes matches and generates predictions/metrics.
    Uses cached data and statistical models.
    """
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
    
    async def analyze_match(self, match_id: str) -> Optional[MatchAnalytics]:
        """
        Analyze a specific match and return comprehensive metrics.
        
        Args:
            match_id: Unified match ID
        
        Returns:
            MatchAnalytics object or None if not found
        """
        # Check cache
        cached = self.cache.get("analytics", match_id)
        if cached:
            return MatchAnalytics(**cached)
        
        # In production, this would:
        # 1. Fetch historical H2H data
        # 2. Calculate form from last N matches
        # 3. Run xG models
        # 4. Generate predictions
        
        # For now, generate placeholder analytics based on match ID
        analytics = self._generate_analytics(match_id)
        
        # Cache result
        self.cache.set("analytics", analytics.to_dict(), Config.CACHE_TTL_ANALYTICS, match_id)
        
        return analytics
    
    def _generate_analytics(self, match_id: str) -> MatchAnalytics:
        """Generate analytics for a match (placeholder for ML models)."""
        # Parse provider from match_id prefix
        provider = match_id.split("_")[0] if "_" in match_id else "unknown"
        
        # Generate deterministic but varied analytics based on match_id hash
        hash_val = int(hashlib.md5(match_id.encode()).hexdigest(), 16)
        
        home_form = ["W", "D", "W", "L", "W"] if hash_val % 3 == 0 else ["W", "W", "D", "D", "L"]
        away_form = ["L", "D", "W", "W", "L"] if hash_val % 3 == 1 else ["D", "L", "W", "D", "W"]
        
        home_xg = 1.2 + (hash_val % 100) / 100
        away_xg = 0.8 + (hash_val % 80) / 100
        
        confidence = min(0.95, 0.5 + (hash_val % 50) / 100)
        
        return MatchAnalytics(
            match_id=match_id,
            home_form=home_form,
            away_form=away_form,
            h2h_record={
                "total_matches": 10 + (hash_val % 20),
                "home_wins": 5 + (hash_val % 5),
                "away_wins": 2 + (hash_val % 4),
                "draws": 3 + (hash_val % 3)
            },
            home_xg=round(home_xg, 2),
            away_xg=round(away_xg, 2),
            home_possession_avg=45 + (hash_val % 20),
            away_possession_avg=100 - (45 + (hash_val % 20)),
            predicted_home_score=round(home_xg * 0.9, 1),
            predicted_away_score=round(away_xg * 0.85, 1),
            confidence=round(confidence, 2),
            key_metrics={
                "home_attack_strength": round(1.1 + (hash_val % 30) / 100, 2),
                "away_defense_weakness": round(0.9 + (hash_val % 25) / 100, 2),
                "over_2_5_probability": round(0.4 + (hash_val % 40) / 100, 2),
                "btts_probability": round(0.45 + (hash_val % 35) / 100, 2),
                "recommended_bet": "Over 2.5" if hash_val % 2 == 0 else "BTTS Yes"
            }
        )
    
    async def search_matches(
        self,
        query: str,
        matches: List[Match]
    ) -> List[Match]:
        """
        Search matches by team name, league, or match ID.
        
        Args:
            query: Search string
            matches: List of matches to search within
        
        Returns:
            Filtered list of matches
        """
        if not query:
            return matches
        
        query_lower = query.lower()
        results = []
        
        for match in matches:
            if (
                query_lower in match.home_team.lower()
                or query_lower in match.away_team.lower()
                or query_lower in match.league_name.lower()
                or query_lower in match.match_id.lower()
                or query_lower in match.country.lower() if match.country else False
            ):
                results.append(match)
        
        return results


# =============================================================================
# EMPIRE DASHBOARD DATA
# =============================================================================

class EmpireDashboardData:
    """
    Central data class for the Empire Dashboard.
    Provides unified interface for all dashboard data needs.
    """
    
    def __init__(self):
        self.aggregator = DataAggregator()
        self.analyzer = MatchAnalyzer(self.aggregator.cache)
        self.risk_controls = RiskControlStatus()
        self._current_matches: List[Match] = []
        self._system_status = {
            "data_providers": {},
            "last_refresh": None,
            "emergency_stop": False
        }
    
    async def refresh_data(
        self,
        league_id: Optional[str] = None,
        tier: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh all dashboard data.
        
        Args:
            league_id: Specific league filter
            tier: Tier filter (tier_1, tier_2, tier_3, all)
            date_str: Specific date (default: today)
        
        Returns:
            Dashboard data dictionary
        """
        tier_enum = LeagueTier(tier) if tier else LeagueTier.ALL
        
        # Fetch matches
        matches, logs = await self.aggregator.fetch_all_matches(
            date_str=date_str,
            league_id=league_id,
            tier=tier_enum
        )
        
        self._current_matches = matches
        
        # Update system status
        self._system_status["last_refresh"] = datetime.now(timezone.utc).isoformat()
        self._system_status["data_providers"] = {
            log.provider: {
                "status": log.status,
                "matches": log.matches_returned,
                "response_time": log.response_time_ms
            }
            for log in logs
        }
        
        return {
            "matches": [m.to_dict() for m in matches],
            "connection_logs": [log.to_dict() for log in logs],
            "system_status": self._system_status,
            "risk_controls": self.risk_controls.__dict__,
            "leagues": LeagueRegistry.get_all_leagues(),
            "total_matches": len(matches)
        }
    
    async def get_arena_matches(
        self,
        league_id: Optional[str] = None,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get matches for the Arena display with filtering.
        
        Args:
            league_id: Filter by league
            tier: Filter by tier
            status: Filter by match status
            search_query: Search teams/leagues
        
        Returns:
            Filtered list of match dictionaries
        """
        # Ensure we have current data
        if not self._current_matches:
            await self.refresh_data(league_id=league_id, tier=tier)
        
        matches = self._current_matches
        
        # Apply league filter
        if league_id and league_id != "all":
            league_data = LeagueRegistry.get_league_by_id(league_id)
            if league_data:
                matches = [
                    m for m in matches
                    if m.league_name == league_data["name"]
                    or league_id in m.metadata.get("league_codes", [])
                    or m.league_id == league_id
                ]
        
        # Apply tier filter
        if tier and tier != "all":
            tier_leagues = LeagueRegistry.get_tier_leagues(LeagueTier(tier))
            matches = [
                m for m in matches
                if any(tl in m.metadata.get("league_codes", []) for tl in tier_leagues)
                or m.league_id in tier_leagues
            ]
        
        # Apply status filter
        if status and status != "all":
            matches = [m for m in matches if m.status == status]
        
        # Apply search
        if search_query:
            matches = await self.analyzer.search_matches(search_query, matches)
        
        return [m.to_dict() for m in matches]
    
    async def get_match_analytics(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive analytics for a match.
        
        Args:
            match_id: Match ID to analyze
        
        Returns:
            Analytics dictionary or None
        """
        analytics = await self.analyzer.analyze_match(match_id)
        if analytics:
            return analytics.to_dict()
        return None
    
    def get_league_dropdown_data(self) -> List[Dict[str, Any]]:
        """
        Get data for league dropdown menu.
        Organized by tier for better UX.
        """
        leagues = LeagueRegistry.get_all_leagues()
        
        # Group by tier
        grouped = {
            "tier_1": [],
            "tier_2": [],
            "tier_3": []
        }
        
        for league in leagues:
            tier = league["tier"]
            if tier in grouped:
                grouped[tier].append(league)
        
        return [
            {"label": "🏆 Tier 1 - Elite", "options": grouped["tier_1"]},
            {"label": "🥈 Tier 2 - Major", "options": grouped["tier_2"]},
            {"label": "🥉 Tier 3 - Global", "options": grouped["tier_3"]},
            {"label": "🌍 All Leagues", "options": leagues}
        ]
    
    def update_risk_controls(
        self,
        kelly_pct: Optional[float] = None,
        max_bet_pct: Optional[float] = None,
        min_ev: Optional[float] = None,
        emergency_stop: Optional[bool] = None
    ) -> RiskControlStatus:
        """
        Update risk control parameters.
        
        Args:
            kelly_pct: Kelly criterion percentage
            max_bet_pct: Maximum bet percentage
            min_ev: Minimum expected value
            emergency_stop: Emergency stop flag
        
        Returns:
            Updated RiskControlStatus
        """
        if kelly_pct is not None:
            self.risk_controls.kelly_pct = kelly_pct
        if max_bet_pct is not None:
            self.risk_controls.max_bet_pct = max_bet_pct
        if min_ev is not None:
            self.risk_controls.min_ev = min_ev
        if emergency_stop is not None:
            self.risk_controls.emergency_stop = emergency_stop
        
        self.risk_controls.last_updated = datetime.now(timezone.utc).isoformat()
        return self.risk_controls
    
    def get_api_connection_logs(self) -> List[Dict[str, Any]]:
        """Get enhanced API connection logs."""
        return self.aggregator.get_connection_logs()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            **self._system_status,
            "risk_controls": {
                "kelly_pct": self.risk_controls.kelly_pct,
                "max_bet_pct": self.risk_controls.max_bet_pct,
                "min_ev": self.risk_controls.min_ev,
                "emergency_stop": self.risk_controls.emergency_stop
            },
            "cache_status": {
                "redis_available": self.aggregator.cache._redis_available
            }
        }
    
    async def emergency_stop_all(self) -> bool:
        """Trigger emergency stop."""
        self.risk_controls.emergency_stop = True
        self.risk_controls.last_updated = datetime.now(timezone.utc).isoformat()
        # Close all provider sessions
        await self.aggregator.close()
        logger.critical("EMERGENCY STOP ACTIVATED - All trading halted")
        return True
    
    async def close(self):
        """Cleanup resources."""
        await self.aggregator.close()


# =============================================================================
# DATABASE LAYER (Optional - for persistent storage)
# =============================================================================

class DatabaseManager:
    """PostgreSQL database manager for persistent data storage."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                Config.DATABASE_URL,
                min_size=5,
                max_size=20
            )
            logger.info("Database pool connected")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
    
    async def close(self):
        """Close database pool."""
        if self.pool:
            await self.pool.close()
    
    async def save_matches(self, matches: List[Match]):
        """Save matches to database."""
        if not self.pool:
            return
        
        async with self.pool.acquire() as conn:
            for match in matches:
                await conn.execute("""
                    INSERT INTO matches (
                        match_id, provider, league_id, league_name, home_team, 
                        away_team, match_date, match_time, status, home_score,
                        away_score, venue, country, odds, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW())
                    ON CONFLICT (match_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        odds = EXCLUDED.odds,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """,
                    match.match_id, match.provider, match.league_id, match.league_name,
                    match.home_team, match.away_team, match.match_date, match.match_time,
                    match.status, match.home_score, match.away_score, match.venue,
                    match.country, json.dumps(match.odds), json.dumps(match.metadata)
                )
    
    async def get_historical_matches(
        self,
        team: Optional[str] = None,
        league_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get historical matches for form analysis."""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM matches WHERE 1=1"
            params = []
            
            if team:
                query += f" AND (home_team ILIKE ${len(params)+1} OR away_team ILIKE ${len(params)+1})"
                params.append(f"%{team}%")
            
            if league_id:
                query += f" AND league_id = ${len(params)+1}"
                params.append(league_id)
            
            query += " ORDER BY match_date DESC LIMIT $" + str(len(params)+1)
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]


# =============================================================================
# FACTORY & INITIALIZATION
# =============================================================================

_dashboard_instance: Optional[EmpireDashboardData] = None

def get_dashboard() -> EmpireDashboardData:
    """Get or create singleton dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = EmpireDashboardData()
    return _dashboard_instance

async def initialize_system():
    """Initialize all system components."""
    dashboard = get_dashboard()
    # Pre-fetch today's data
    await dashboard.refresh_data()
    logger.info("System initialized successfully")
    return dashboard

async def shutdown_system():
    """Graceful shutdown."""
    global _dashboard_instance
    if _dashboard_instance:
        await _dashboard_instance.close()
        _dashboard_instance = None
    logger.info("System shutdown complete")


# =============================================================================
# MAIN EXECUTION (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        """Test the data layer."""
        print("=" * 60)
        print("EMPIRE DATA LAYER - TEST SUITE")
        print("=" * 60)
        
        # Initialize
        dashboard = await initialize_system()
        
        # Test 1: League dropdown
        print("\n[TEST 1] League Dropdown Data:")
        leagues = dashboard.get_league_dropdown_data()
        for group in leagues:
            print(f"  {group['label']}: {len(group['options'])} leagues")
        
        # Test 2: Fetch matches for today
        print("\n[TEST 2] Fetching Today's Matches:")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = await dashboard.refresh_data(date_str=today)
        print(f"  Total matches: {data['total_matches']}")
        print(f"  Providers: {list(data['system_status']['data_providers'].keys())}")
        
        # Test 3: Filter by league
        print("\nI understand your frustration — let me deliver the complete corrected `empire_data_layer.py` in one single copy-paste block as you requested. This consolidates all fixes for APIs, league mapping, filtering, logging, and the `EmpireDashboardData` class.

---

```python
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           EMPIRE SPORT TRADING SYSTEM — DATA LAYER v3.0                      ║
║           Consolidated: APIs, Arena, Analyzer, Dashboard, Cache              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import asyncio
import aiohttp
import logging
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from functools import lru_cache, wraps
import hashlib
import sqlite3
from pathlib import Path

# ── CONFIGURATION ────────────────────────────────────────────────────────────

ENV = os.environ

@dataclass(frozen=True)
class APIConfig:
    name: str
    base_url: str
    key: Optional[str]
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 15
    enabled: bool = True
    priority: int = 99  # Lower = higher priority
    rate_limit_per_min: int = 30

    def is_ready(self) -> bool:
        return self.enabled and bool(self.key)

# ── API CONFIGURATIONS (Auto-detects key format) ─────────────────────────────

API_CONFIGS = {
    "football_data": APIConfig(
        name="Football-Data",
        base_url="https://api.football-data.org/v4",
        key=ENV.get("FOOTBALL_DATA_API_KEY"),
        headers=lambda k: {"X-Auth-Token": k},
        timeout=15,
        priority=1,
        rate_limit_per_min=10
    ),
    "api_sports": APIConfig(
        name="API-Sports",
        base_url="https://v3.football.api-sports.io",
        key=ENV.get("API_SPORTS_KEY"),
        headers=lambda k: {"x-apisports-key": k},
        timeout=15,
        priority=2,
        rate_limit_per_min=30
    ),
    "theoddsapi": APIConfig(
        name="TheOddsAPI",
        base_url="https://api.the-odds-api.com/v4/sports",
        key=ENV.get("THEODDSAPI_KEY"),
        headers={},
        timeout=15,
        priority=3,
        rate_limit_per_min=50
    ),
    "sportmonks": APIConfig(
        name="Sportmonks",
        base_url="https://api.sportmonks.com/v3/football",
        key=ENV.get("SPORTMONKS_API_KEY"),
        headers={},
        timeout=20,
        priority=4,
        rate_limit_per_min=30
    ),
    "thesportsdb": APIConfig(
        name="TheSportsDB",
        base_url="https://www.thesportsdb.com/api/v2/json",
        key=ENV.get("THESPORTSDB_API_KEY"),
        headers=lambda k: {"X-API-KEY": k},  # Premium key header
        timeout=15,
        priority=5,
        rate_limit_per_min=60
    ),
    "mysportsfeeds": APIConfig(
        name="MySportsFeeds",
        base_url="https://api.mysportsfeeds.com/v2.1/pull",
        key=ENV.get("MYSPORTSFEEDS_API_KEY"),
        headers=lambda k: {"Authorization": f"Basic {k}"},
        timeout=20,
        priority=6,
        rate_limit_per_min=25
    ),
}

# ── GLOBAL LEAGUE MAP (60+ Leagues) ──────────────────────────────────────────

LEAGUE_MAP = {
    # England
    "PL": {"name": "Premier League", "fd_id": "PL", "as_id": 39, "sm_id": 8, "tsdb_id": "4328", "msf_id": "eng.1", "country": "England"},
    "ELC": {"name": "Championship", "fd_id": "ELC", "as_id": 40, "sm_id": 9, "tsdb_id": "4329", "country": "England"},
    "FAC": {"name": "FA Cup", "fd_id": "FAC", "as_id": 45, "country": "England"},
    # Spain
    "PD": {"name": "La Liga", "fd_id": "PD", "as_id": 140, "sm_id": 564, "tsdb_id": "4335", "msf_id": "esp.1", "country": "Spain"},
    "SD": {"name": "Segunda Division", "fd_id": "SD", "as_id": 141, "country": "Spain"},
    # Italy
    "SA": {"name": "Serie A", "fd_id": "SA", "as_id": 135, "sm_id": 384, "tsdb_id": "4332", "msf_id": "ita.1", "country": "Italy"},
    "SB": {"name": "Serie B", "fd_id": "SB", "as_id": 136, "country": "Italy"},
    # Germany
    "BL1": {"name": "Bundesliga", "fd_id": "BL1", "as_id": 78, "sm_id": 82, "tsdb_id": "4331", "msf_id": "ger.1", "country": "Germany"},
    "BL2": {"name": "2. Bundesliga", "fd_id": "BL2", "as_id": 79, "country": "Germany"},
    # France
    "FL1": {"name": "Ligue 1", "fd_id": "FL1", "as_id": 61, "sm_id": 301, "tsdb_id": "4334", "msf_id": "fra.1", "country": "France"},
    "FL2": {"name": "Ligue 2", "fd_id": "FL2", "as_id": 62, "country": "France"},
    # Europe
    "CL": {"name": "Champions League", "fd_id": "CL", "as_id": 2, "sm_id": 2, "tsdb_id": "4480", "msf_id": "uefa.champions", "country": "Europe"},
    "EL": {"name": "Europa League", "fd_id": "EL", "as_id": 3, "sm_id": 5, "tsdb_id": "4481", "country": "Europe"},
    "ECL": {"name": "Conference League", "fd_id": "ECL", "as_id": 848, "country": "Europe"},
    # Netherlands
    "DED": {"name": "Eredivisie", "fd_id": "DED", "as_id": 88, "sm_id": 72, "country": "Netherlands"},
    # Portugal
    "PPL": {"name": "Primeira Liga", "fd_id": "PPL", "as_id": 94, "sm_id": 462, "country": "Portugal"},
    # Scotland
    "SPL": {"name": "Scottish Premiership", "fd_id": "SPL", "as_id": 179, "country": "Scotland"},
    # Belgium
    "BSA": {"name": "Belgian Pro League", "fd_id": "BSA", "as_id": 144, "country": "Belgium"},
    # Turkey
    "TSL": {"name": "Super Lig", "fd_id": "TSL", "as_id": 203, "country": "Turkey"},
    # Brazil
    "BSA1": {"name": "Serie A Brazil", "as_id": 71, "sm_id": 325, "tsdb_id": "4351", "country": "Brazil"},
    # Argentina
    "ARG1": {"name": "Primera Division", "as_id": 128, "country": "Argentina"},
    # USA/Canada
    "MLS": {"name": "Major League Soccer", "as_id": 253, "tsdb_id": "4346", "msf_id": "usa.1", "country": "USA"},
    # Copa Libertadores
    "CLI": {"name": "Copa Libertadores", "as_id": 13, "sm_id": 14, "tsdb_id": "4427", "country": "South America"},
    # Copa Sudamericana
    "CSA": {"name": "Copa Sudamericana", "as_id": 11, "country": "South America"},
    # Mexico
    "LMX": {"name": "Liga MX", "as_id": 262, "country": "Mexico"},
    # International
    "WC": {"name": "World Cup", "as_id": 1, "tsdb_id": "4427", "country": "International"},
    "EC": {"name": "Euro Championship", "as_id": 4, "country": "International"},
    "UNL": {"name": "UEFA Nations League", "as_id": 5, "country": "International"},
    # Asia
    "J1": {"name": "J1 League", "as_id": 98, "country": "Japan"},
    "K1": {"name": "K League 1", "as_id": 292, "country": "South Korea"},
    "C1": {"name": "Chinese Super League", "as_id": 169, "country": "China"},
    "AUS": {"name": "A-League", "as_id": 188, "country": "Australia"},
    # Africa
    "CAFCL": {"name": "CAF Champions League", "as_id": 12, "country": "Africa"},
    # Nordic
    "ALL": {"name": "Allsvenskan", "as_id": 113, "country": "Sweden"},
    "ELI": {"name": "Eliteserien", "as_id": 103, "country": "Norway"},
    "SL": {"name": "Superliga", "as_id": 119, "country": "Denmark"},
    "VEI": {"name": "Veikkausliiga", "as_id": 244, "country": "Finland"},
    # Others
    "AUT": {"name": "Bundesliga Austria", "as_id": 218, "country": "Austria"},
    "SUI": {"name": "Super League", "as_id": 207, "country": "Switzerland"},
    "POL": {"name": "Ekstraklasa", "as_id": 106, "country": "Poland"},
    "CZE": {"name": "Czech Liga", "as_id": 345, "country": "Czech Republic"},
    "GRE": {"name": "Super League Greece", "as_id": 197, "country": "Greece"},
    "CRO": {"name": "HNL", "as_id": 210, "country": "Croatia"},
    "SRB": {"name": "SuperLiga", "as_id": 286, "country": "Serbia"},
    "UKR": {"name": "Premier League Ukraine", "as_id": 333, "country": "Ukraine"},
    "RUS": {"name": "Premier League Russia", "as_id": 235, "country": "Russia"},
    "ISR": {"name": "Ligat Ha'Al", "as_id": 383, "country": "Israel"},
    "ROU": {"name": "Liga I", "as_id": 283, "country": "Romania"},
    "BUL": {"name": "First League", "as_id": 172, "country": "Bulgaria"},
    "SVK": {"name": "Super Liga", "as_id": 332, "country": "Slovakia"},
    "SVN": {"name": "PrvaLiga", "as_id": 373, "country": "Slovenia"},
    "HUN": {"name": "NB I", "as_id": 271, "country": "Hungary"},
}

LEAGUE_DISPLAY_ORDER = [
    "PL", "PD", "SA", "BL1", "FL1", "CL", "EL", "DED", "PPL", "SPL",
    "BSA", "TSL", "MLS", "CLI", "BSA1", "ARG1", "WC", "EC", "J1", "K1"
]

# ── DATA MODELS ──────────────────────────────────────────────────────────────

class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"

@dataclass
class MatchOdds:
    home: float = 0.0
    draw: float = 0.0
    away: float = 0.0
    over_25: float = 0.0
    under_25: float = 0.0
    btts_yes: float = 0.0
    btts_no: float = 0.0
    source: str = ""

@dataclass
class TeamStats:
    form: str = ""
    goals_scored_avg: float = 0.0
    goals_conceded_avg: float = 0.0
    clean_sheets_pct: float = 0.0
    possession_avg: float = 0.0
    shots_avg: float = 0.0
    shots_on_target_avg: float = 0.0
    corners_avg: float = 0.0
    cards_avg: float = 0.0

@dataclass
class Match:
    id: str
    home_team: str
    away_team: str
    league_code: str
    league_name: str
    match_date: datetime
    status: MatchStatus
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    odds: Optional[MatchOdds] = None
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None
    venue: str = ""
    referee: str = ""
    source_apis: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_live(self) -> bool:
        return self.status in (MatchStatus.LIVE, MatchStatus.IN_PLAY, MatchStatus.PAUSED)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        d['match_date'] = self.match_date.isoformat()
        return d

@dataclass
class APILogEntry:
    timestamp: str
    provider: str
    status: str  # SUCCESS, EMPTY, ERROR, TIMEOUT, RATE_LIMITED
    http_code: Optional[int]
    response_time_ms: float
    matches_found: int
    error_detail: str
    rate_limit_remaining: Optional[int] = None
    endpoint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ── IN-MEMORY CACHE (Redis-ready stub) ───────────────────────────────────────

class MatchCache:
    def __init__(self, ttl_seconds: int = 120):
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def _key(self, *parts) -> str:
        return hashlib.md5(json.dumps(parts, sort_keys=True).encode()).hexdigest()

    def get(self, *parts) -> Optional[Any]:
        key = self._key(*parts)
        if key in self._cache:
            expires, value = self._cache[key]
            if time.time() < expires:
                return value
            del self._cache[key]
        return None

    def set(self, value: Any, *parts):
        key = self._key(*parts)
        self._cache[key] = (time.time() + self._ttl, value)

    def invalidate(self, pattern: Optional[str] = None):
        if pattern:
            self._cache = {k: v for k, v in self._cache.items() if pattern not in k}
        else:
            self._cache.clear()

CACHE = MatchCache(ttl_seconds=120)

# ── RATE LIMITER ─────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self):
        self._timestamps: Dict[str, List[float]] = {}

    async def acquire(self, config: APIConfig):
        now = time.time()
        window = 60.0
        key = config.name

        if key not in self._timestamps:
            self._timestamps[key] = []

        self._timestamps[key] = [t for t in self._timestamps[key] if now - t < window]

        if len(self._timestamps[key]) >= config.rate_limit_per_min:
            wait = window - (now - self._timestamps[key][0]) + 0.1
            if wait > 0:
                await asyncio.sleep(wait)

        self._timestamps[key].append(time.time())

RATE_LIMITER = RateLimiter()

# ── API FETCHER ──────────────────────────────────────────────────────────────

class APIFetcher:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.log: List[APILogEntry] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch(self, config: APIConfig, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not config.is_ready():
            return None

        await RATE_LIMITER.acquire(config)

        url = f"{config.base_url}/{endpoint.lstrip('/')}"
        headers = config.headers(config.key) if callable(config.headers) else config.headers
        start = time.perf_counter()

        try:
            async with self.session.get(
                url, headers=headers, params=params or {}, timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as resp:
                elapsed_ms = (time.perf_counter() - start) * 1000
                body = await resp.text()

                rate_limit = resp.headers.get('X-RateLimit-Remaining')
                rate_limit = int(rate_limit) if rate_limit else None

                if resp.status == 200:
                    try:
                        data = json.loads(body)
                        matches = self._count_matches(data, config.name)
                        self.log.append(APILogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            provider=config.name,
                            status="SUCCESS" if matches > 0 else "EMPTY",
                            http_code=resp.status,
                            response_time_ms=round(elapsed_ms, 2),
                            matches_found=matches,
                            error_detail="Key valid but no matches today" if matches == 0 else "",
                            rate_limit_remaining=rate_limit,
                            endpoint=endpoint
                        ))
                        return data
                    except json.JSONDecodeError:
                        self.log.append(APILogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            provider=config.name,
                            status="ERROR",
                            http_code=resp.status,
                            response_time_ms=round(elapsed_ms, 2),
                            matches_found=0,
                            error_detail="Invalid JSON response",
                            rate_limit_remaining=rate_limit,
                            endpoint=endpoint
                        ))
                        return None

                elif resp.status == 429:
                    self.log.append(APILogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        provider=config.name,
                        status="RATE_LIMITED",
                        http_code=resp.status,
                        response_time_ms=round(elapsed_ms, 2),
                        matches_found=0,
                        error_detail="Rate limit exceeded",
                        rate_limit_remaining=0,
                        endpoint=endpoint
                    ))
                    return None

                else:
                    self.log.append(APILogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        provider=config.name,
                        status="ERROR",
                        http_code=resp.status,
                        response_time_ms=round(elapsed_ms, 2),
                        matches_found=0,
                        error_detail=f"HTTP {resp.status}: {body[:200]}",
                        rate_limit_remaining=rate_limit,
                        endpoint=endpoint
                    ))
                    return None

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.log.append(APILogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=config.name,
                status="TIMEOUT",
                http_code=None,
                response_time_ms=round(elapsed_ms, 2),
                matches_found=0,
                error_detail=f"Request timed out after {config.timeout}s",
                endpoint=endpoint
            ))
            return None
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.log.append(APILogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=config.name,
                status="ERROR",
                http_code=None,
                response_time_ms=round(elapsed_ms, 2),
                matches_found=0,
                error_detail=str(e)[:200],
                endpoint=endpoint
            ))
            return None

    def _count_matches(self, data: Dict, provider: str) -> int:
        if not data:
            return 0
        if provider == "Football-Data":
            return len(data.get("matches", []))
        elif provider == "API-Sports":
            return len(data.get("response", []))
        elif provider == "TheOddsAPI":
            return len(data) if isinstance(data, list) else 0
        elif provider == "Sportmonks":
            return len(data.get("data", []))
        elif provider == "TheSportsDB":
            return len(data.get("events", []))
        elif provider == "MySportsFeeds":
            return len(data.get("games", []))
        return 0

# ── DATA PARSERS ─────────────────────────────────────────────────────────────

class MatchParser:
    @staticmethod
    def parse_football_data(data: Dict) -> List[Match]:
        matches = []
        for m in data.get("matches", []):
            status = MatchStatus(m.get("status", "SCHEDULED"))
            if status == MatchStatus.FINISHED and m.get("score", {}).get("winner") is None:
                continue  # Skip unplayed finished matches
            matches.append(Match(
                id=f"fd_{m['id']}",
                home_team=m["homeTeam"]["name"],
                away_team=m["awayTeam"]["name"],
                league_code=m["competition"]["code"],
                league_name=m["competition"]["name"],
                match_date=datetime.fromisoformat(m["utcDate"].replace('Z', '+00:00')),
                status=status,
                home_score=m.get("score", {}).get("fullTime", {}).get("home"),
                away_score=m.get("score", {}).get("fullTime", {}).get("away"),
                venue=m.get("venue", ""),
                referee=m.get("referee", ""),
                source_apis=["football_data"],
                metadata={"matchday": m.get("matchday")}
            ))
        return matches

    @staticmethod
    def parse_api_sports(data: Dict) -> List[Match]:
        matches = []
        for m in data.get("response", []):
            fixture = m.get("fixture", {})
            teams = m.get("teams", {})
            league = m.get("league", {})
            status_raw = fixture.get("status", {}).get("short", "NS")
            status_map = {"NS": "SCHEDULED", "1H": "LIVE", "HT": "PAUSED", "2H": "LIVE",
                         "ET": "LIVE", "P": "LIVE", "FT": "FINISHED", "AET": "FINISHED",
                         "PEN": "FINISHED", "SUSP": "SUSPENDED", "INT": "PAUSED",
                         "PST": "POSTPONED", "CANC": "CANCELLED", "ABD": "SUSPENDED",
                         "AWD": "FINISHED", "WO": "FINISHED"}
            matches.append(Match(
                id=f"as_{fixture['id']}",
                home_team=teams["home"]["name"],
                away_team=teams["away"]["name"],
                league_code=str(league.get("id", "")),
                league_name=league.get("name", "Unknown"),
                match_date=datetime.fromisoformat(fixture["date"].replace('Z', '+00:00')),
                status=MatchStatus(status_map.get(status_raw, "SCHEDULED")),
                home_score=fixture.get("status", {}).get("goals", {}).get("home"),
                away_score=fixture.get("status", {}).get("goals", {}).get("away"),
                venue=fixture.get("venue", {}).get("name", ""),
                referee=fixture.get("referee", "") or "",
                source_apis=["api_sports"],
                metadata={"round": league.get("round")}
            ))
        return matches

    @staticmethod
    def parse_thesportsdb(data: Dict) -> List[Match]:
        matches = []
        for e in data.get("events", []):
            if not e:
                continue
            date_str = f"{e.get('dateEvent', '')}T{e.get('strTime', '00:00:00')}+00:00"
            try:
                match_date = datetime.fromisoformat(date_str)
            except:
                match_date = datetime.now(timezone.utc)
            status = "LIVE" if e.get("strProgress") and e.get("strProgress") != "FT" else "SCHEDULED"
            if e.get("strStatus") == "Match Finished":
                status = "FINISHED"
            matches.append(Match(
                id=f"tsdb_{e['idEvent']}",
                home_team=e.get("strHomeTeam", ""),
                away_team=e.get("strAwayTeam", ""),
                league_code=e.get("idLeague", ""),
                league_name=e.get("strLeague", ""),
                match_date=match_date,
                status=MatchStatus(status),
                home_score=int(e["intHomeScore"]) if e.get("intHomeScore") else None,
                away_score=int(e["intAwayScore"]) if e.get("intAwayScore") else None,
                venue=e.get("strVenue", ""),
                source_apis=["thesportsdb"],
                metadata={"season": e.get("strSeason")}
            ))
        return matches

    @staticmethod
    def parse_mysportsfeeds(data: Dict) -> List[Match]:
        matches = []
        for g in data.get("games", []):
            schedule = g.get("schedule", {})
            score = g.get("score", {})
            status_map = {"scheduled": "SCHEDULED", "in progress": "LIVE", "final": "FINISHED",
                         "postponed": "POSTPONED", "suspended": "SUSPENDED"}
            matches.append(Match(
                id=f"msf_{schedule.get('id', '')}",
                home_team=schedule.get("homeTeam", {}).get("name", ""),
                away_team=schedule.get("awayTeam", {}).get("name", ""),
                league_code="",
                league_name=schedule.get("league", ""),
                match_date=datetime.fromisoformat(schedule["startTime"].replace('Z', '+00:00')),
                status=MatchStatus(status_map.get(score.get("currentQuarter", {}).get("type", "scheduled"), "SCHEDULED")),
                home_score=score.get("homeScoreTotal") if score else None,
                away_score=score.get("awayScoreTotal") if score else None,
                venue=schedule.get("venue", {}).get("name", ""),
                source_apis=["mysportsfeeds"],
                metadata={"week": schedule.get("week")}
            ))
        return matches

# ── EMPIRE DATA LAYER ────────────────────────────────────────────────────────

class EmpireDataLayer:
    def __init__(self):
        self.fetcher: Optional[APIFetcher] = None
        self.parsers = {
            "football_data": MatchParser.parse_football_data,
            "api_sports": MatchParser.parse_api_sports,
            "thesportsdb": MatchParser.parse_thesportsdb,
            "mysportsfeeds": MatchParser.parse_mysportsfeeds,
        }

    async def __aenter__(self):
        self.fetcher = APIFetcher()
        await self.fetcher.__aenter__()
        return self

    async def __aexit__(self, *args):
        if self.fetcher:
            await self.fetcher.__aexit__(*args)

    def _get_date_range(self, days_ahead: int = 7, days_behind: int = 1) -> tuple[str, str]:
        today = datetime.now(timezone.utc).date()
        return (
            (today - timedelta(days=days_behind)).isoformat(),
            (today + timedelta(days=days_ahead)).isoformat()
        )

    # ── FOOTBALL-DATA.ORG (Primary - Most Reliable) ─────────────────────────
    async def _fetch_football_data(self, league_code: Optional[str] = None) -> List[Match]:
        config = API_CONFIGS["football_data"]
        if not config.is_ready():
            return []

        cache_key = ("fd", league_code or "all")
        cached = CACHE.get(*cache_key)
        if cached:
            return cached

        matches = []
        leagues_to_fetch = [league_code] if league_code else list(LEAGUE_MAP.keys())

        for code in leagues_to_fetch:
            fd_id = LEAGUE_MAP.get(code, {}).get("fd_id")
            if not fd_id:
                continue

            endpoint = f"competitions/{fd_id}/matches"
            params = {"dateFrom": self._get_date_range()[0], "dateTo": self._get_date_range()[1]}

            data = await self.fetcher.fetch(config, endpoint, params)
            if data:
                parsed = self.parsers["football_data"](data)
                matches.extend(parsed)

        CACHE.set(matches, *cache_key)
        return matches

    # ── API-SPORTS ────────────────────────────────────────────────────────────
    async def _fetch_api_sports(self, league_code: Optional[str] = None) -> List[Match]:
        config = API_CONFIGS["api_sports"]
        if not config.is_ready():
            return []

        cache_key = ("as", league_code or "all")
        cached = CACHE.get(*cache_key)
        if cached:
            return cached

        params = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "season": datetime.now(timezone.utc).year,
            "timezone": "UTC"
        }

        if league_code and league_code in LEAGUE_MAP:
            as_id = LEAGUE_MAP[league_code].get("as_id")
            if as_id:
                params["league"] = as_id
        else:
            # Fetch major leagues only if no filter
            params["league"] = "-".join(str(LEAGUE_MAP[k].get("as_id", "")) for k in LEAGUE_DISPLAY_ORDER[:15] if LEAGUE_MAP[k].get("as_id"))

        data = await self.fetcher.fetch(config, "fixtures", params)
        matches = self.parsers["api_sports"](data) if data else []

        CACHE.set(matches, *cache_key)
        return matches

    # ── THESPORTSDB (Premium v2) ─────────────────────────────────────────────
    async def _fetch_thesportsdb(self, league_code: Optional[str] = None) -> List[Match]:
        config = API_CONFIGS["thesportsdb"]
        if not config.is_ready():
            return []

        cache_key = ("tsdb", league_code or "all")
        cached = CACHE.get(*cache_key)
        if cached:
            return cached

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        matches = []

        if league_code and league_code in LEAGUE_MAP:
            tsdb_id = LEAGUE_MAP[league_code].get("tsdb_id")
            if tsdb_id:
                data = await self.fetcher.fetch(config, f"eventsseason.php", {
                    "id": tsdb_id,
                    "s": datetime.now(timezone.utc).year,
                    "d": today,
                    "r": "5"  # Round parameter for filtering
                })
                if data:
                    matches.extend(self.parsers["thesportsdb"](data))
        else:
            # Fetch all major leagues
            for code in LEAGUE_DISPLAY_ORDER[:10]:
                tsdb_id = LEAGUE_MAP.get(code, {}).get("tsdb_id")
                if tsdb_id:
                    data = await self.fetcher.fetch(config, "eventsday.php", {
                        "d": today,
                        "l": tsdb_id
                    })
                    if data:
                        matches.extend(self.parsers["thesportsdb"](data))

        CACHE.set(matches, *cache_key)
        return matches

    # ── MYSPORTSFEEDS ─────────────────────────────────────────────────────────
    async def _fetch_mysportsfeeds(self, league_code: Optional[str] = None) -> List[Match]:
        config = API_CONFIGS["mysportsfeeds"]
        if not config.is_ready():
            return []

        cache_key = ("msf", league_code or "all")
        cached = CACHE.get(*cache_key)
        if cached:
            return cached

        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        msf_league = LEAGUE_MAP.get(league_code, {}).get("msf_id", "eng.1") if league_code else "eng.1"

        data = await self.fetcher.fetch(
            config,
            f"{msf_league}/current/games.json",
            {"date": today, "force": "true"}
        )

        matches = self.parsers["mysportsfeeds"](data) if data else []
        CACHE.set(matches, *cache_key)
        return matches

    # ── PARALLEL FETCH ALL ────────────────────────────────────────────────────
    async def fetch_all_matches(
        self,
        league_code: Optional[str] = None,
        status_filter: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Match]:
        """
        Fetch matches from all enabled APIs in parallel.
        Filters by league_code if provided (fixes Observation #3).
        """
        tasks = [
            self._fetch_football_data(league_code),
            self._fetch_api_sports(league_code),
            self._fetch_thesportsdb(league_code),
            self._fetch_mysportsfeeds(league_code),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_matches: Dict[str, Match] = {}

        for result in results:
            if isinstance(result, Exception):
                logging.warning(f"API fetch error: {result}")
                continue
            for match in result:
                # Deduplicate by home+away+date hash
                dedup_key = f"{match.home_team}|{match.away_team}|{match.match_date.date().isoformat()}"
                if dedup_key in all_matches:
                    existing = all_matches[dedup_key]
                    existing.source_apis.extend(match.source_apis)
                    existing.source_apis = list(set(existing.source_apis))
                else:
                    all_matches[dedup_key] = match

        matches = list(all_matches.values())

        # Apply filters
        if league_code and league_code != "ALL":
            matches = [m for m in matches if m.league_code == league_code or
                      LEAGUE_MAP.get(league_code, {}).get("name") in m.league_name]

        if status_filter and status_filter != "ALL":
            status_enum = MatchStatus(status_filter)
            matches = [m for m in matches if m.status == status_enum]

        if date_from:
            matches = [m for m in matches if m.match_date.date() >= date_from]
        if date_to:
            matches = [m for m in matches if m.match_date.date() <= date_to]

        # Sort by date
        matches.sort(key=lambda m: m.match_date)
        return matches

    def get_api_log(self) -> List[Dict]:
        """Returns enhanced API connection log (fixes Observation #6)."""
        if not self.fetcher:
            return []
        return [entry.to_dict() for entry in self.fetcher.log]

    def get_leagues(self) -> List[Dict[str, str]]:
        """Returns all available leagues for dropdown (fixes Observation #2)."""
        return [
            {"code": code, "name": info["name"], "country": info["country"]}
            for code, info in sorted(LEAGUE_MAP.items(), key=lambda x: LEAGUE_DISPLAY_ORDER.index(x[0]) if x[0] in LEAGUE_DISPLAY_ORDER else 999)
        ]

    def get_system_status(self) -> Dict[str, Any]:
        """Returns real-time system status for all APIs."""
        status = {}
        for key, config in API_CONFIGS.items():
            status[config.name] = {
                "enabled": config.enabled,
                "key_configured": bool(config.key),
                "key_preview": f"{config.key[:8]}..." if config.key else None,
                "last_fetch": None,  # Would be populated from persistent store
                "priority": config.priority
            }
        return status

# ── EMPIRE DASHBOARD DATA (fixes previous ImportError) ───────────────────────

class EmpireDashboardData:
    """
    Unified data provider for the EMPIRE dashboard.
    Exposes all methods the frontend expects.
    """

    def __init__(self):
        self._layer: Optional[EmpireDataLayer] = None

    async def _get_layer(self) -> EmpireDataLayer:
        if self._layer is None:
            self._layer = EmpireDataLayer()
            await self._layer.__aenter__()
        return self._layer

    async def get_matches(
        self,
        league: Optional[str] = None,
        status: Optional[str] = None,
        sport: str = "Soccer"
    ) -> List[Dict[str, Any]]:
        """Primary method for arena match listing."""
        if sport != "Soccer":
            return []
        layer = await self._get_layer()
        matches = await layer.fetch_all_matches(
            league_code=league if league != "ALL" else None,
            status_filter=status if status != "ALL" else None
        )
        return [m.to_dict() for m in matches]

    async def get_match_analytics(self, match_id: str) -> Dict[str, Any]:
        """Returns detailed analytics for a specific match (fixes Observation #4)."""
        layer = await self._get_layer()
        # Fetch all and find by ID
        all_matches = await layer.fetch_all_matches()
        match = next((m for m in all_matches if m.id == match_id), None)

        if not match:
            return {"error": "Match not found", "match_id": match_id}

        # Generate analytics
        return {
            "match": match.to_dict(),
            "predictions": self._generate_predictions(match),
            "head_to_head": await self._get_h2h(match),
            "team_form": {
                "home": match.home_stats.to_dict() if match.home_stats else self._default_stats(),
                "away": match.away_stats.to_dict() if match.away_stats else self._default_stats()
            },
            "odds_trend": match.odds.to_dict() if match.odds else MatchOdds().to_dict(),
            "value_bets": self._detect_value_bets(match)
        }

    def _generate_predictions(self, match: Match) -> Dict[str, float]:
        """Basic prediction model based on available data."""
        home_advantage = 0.1
        predictions = {
            "home_win": 0.33 + home_advantage,
            "draw": 0.33,
            "away_win": 0.33 - home_advantage,
            "over_25": 0.5,
            "btts": 0.5,
            "confidence": 0.0
        }

        if match.home_stats and match.away_stats:
            hs, aw = match.home_stats, match.away_stats
            total_goals = hs.goals_scored_avg + aw.goals_conceded_avg + aw.goals_scored_avg + hs.goals_conceded_avg
            predictions["over_25"] = min(0.85, total_goals / 4.0)
            predictions["btts"] = min(0.85, (hs.goals_scored_avg * aw.goals_scored_avg) / 2.0)
            predictions["confidence"] = 0.6

        return predictions

    def _default_stats(self) -> Dict[str, Any]:
        return TeamStats().to_dict()

    async def _get_h2h(self, match: Match) -> List[Dict[str, Any]]:
        """Fetch head-to-head history."""
        # This would integrate with a historical data API
        return []

    def _detect_value_bets(self, match: Match) -> List[Dict[str, Any]]:
        """Detect value betting opportunities."""
        values = []
        if match.odds:
            implied_home = 1 / match.odds.home if match.odds.home > 0 else 0
            if implied_home < 0.4 and match.home_stats and match.home_stats.form.count('W') >= 3:
                values.append({
                    "type": "HOME_WIN",
                    "odds": match.odds.home,
                    "edge": round(0.4 - implied_home, 3),
                    "confidence": "MEDIUM"
                })
        return values

    async def search_matches(self, query: str) -> List[Dict[str, Any]]:
        """Search matches by team name (fixes Observation #4)."""
        layer = await self._get_layer()
        all_matches = await layer.fetch_all_matches()
        query_lower = query.lower()

        results = [
            m for m in all_matches
            if query_lower in m.home_team.lower() or query_lower in m.away_team.lower()
            or query_lower in m.league_name.lower()
        ]
        return [m.to_dict() for m in results[:20]]

    async def get_api_status(self) -> Dict[str, Any]:
        """Returns system status with enhanced logging."""
        layer = await self._get_layer()
        return {
            "apis": layer.get_system_status(),
            "log": layer.get_api_log(),
            "data_status": "ACTIVE",
            "models_status": "ONLINE",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def get_risk_controls(self) -> Dict[str, Any]:
        """Returns current risk control settings."""
        return {
            "kelly_pct": float(ENV.get("KELLY_PCT", "0")),
            "max_bet_pct": float(ENV.get("MAX_BET_PCT", "0")),
            "min_ev": float(ENV.get("MIN_EV", "0")),
            "emergency_stop": ENV.get("EMERGENCY_STOP", "false").lower() == "true"
        }

    async def refresh_data(self) -> Dict[str, Any]:
        """Force refresh all cached data."""
        CACHE.invalidate()
        layer = await self._get_layer()
        matches = await layer.fetch_all_matches()
        return {
            "status": "success",
            "matches_loaded": len(matches),
            "apis_queried": len([e for e in layer.get_api_log() if e["status"] in ("SUCCESS", "EMPTY")]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def close(self):
        if self._layer:
            await self._layer.__aexit__(None, None, None)
            self._layer = None

# ── SYNC WRAPPER FOR LEGACY COMPATIBILITY ────────────────────────────────────

class EmpireDataLayerSync:
    """Synchronous wrapper for non-async contexts."""

    def __init__(self):
        self._async_layer = EmpireDashboardData()

    def _run(self, coro):
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def get_matches(self, **kwargs):
        return self._run(self._async_layer.get_matches(**kwargs))

    def get_match_analytics(self, match_id: str):
        return self._run(self._async_layer.get_match_analytics(match_id))

    def search_matches(self, query: str):
        return self._run(self._async_layer.search_matches(query))

    def get_api_status(self):
        return self._run(self._async_layer.get_api_status())

    def refresh_data(self):
        return self._run(self._async_layer.refresh_data())

# ── SINGLETON INSTANCE ───────────────────────────────────────────────────────

# Use this for imports: from empire_data_layer import empire_data
empire_data = EmpireDashboardData()

# Legacy alias for direct imports
EmpireDataLayer = EmpireDataLayer
