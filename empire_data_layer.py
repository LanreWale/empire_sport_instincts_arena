"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE SPORT DATA INTEGRATION LAYER
Real-Time Sports Data Feeds | Multi-Provider Failover | Value Detection Engine
═══════════════════════════════════════════════════════════════════════════════
Architecture:
  - Instant static fallbacks guarantee dropdowns always populate immediately
  - Live API data enriches / replaces static lists when keys are active
  - All API calls are cached aggressively to avoid blocking the sidebar
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import hashlib
import base64
import requests
import threading
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
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class APIConfig:
    @staticmethod
    def _clean(key: str) -> str:
        return str(key).strip() if key else ""

    API_SPORTS_KEY        = _clean(os.getenv("API_SPORTS_KEY", ""))
    API_SPORTS_URL        = "https://v3.football.api-sports.io"

    ODDS_API_KEY          = _clean(os.getenv("ODDS_API_KEY", ""))
    ODDS_API_URL          = "https://api.the-odds-api.com/v4"

    SPORTMONKS_KEY        = _clean(os.getenv("SPORTMONKS_KEY", ""))
    SPORTMONKS_URL        = "https://api.sportmonks.com/api/v3/football"

    MYSPORTSFEEDS_KEY     = _clean(os.getenv("MYSPORTSFEEDS_KEY", ""))
    MYSPORTSFEEDS_PASSWORD = _clean(os.getenv("MYSPORTSFEEDS_PASSWORD", ""))
    MYSPORTSFEEDS_URL     = "https://api.mysportsfeeds.com/v2.1/pull"

    FOOTBALL_DATA_KEY     = _clean(os.getenv("FOOTBALL_DATA_KEY", ""))
    FOOTBALL_DATA_URL     = "https://api.football-data.org/v4"

    THESPORTSDB_KEY       = _clean(os.getenv("TheSportDB_API_key", "3"))
    THESPORTSDB_URL_V1    = "https://www.thesportsdb.com/api/v1/json"

    APIFY_API_TOKEN       = _clean(os.getenv("APIFY_API_KEY", ""))
    APIFY_BASE_URL        = "https://api.apify.com/v2/acts"
    APIFY_ACTOR_LIVE      = "crawlerbros~flashscore-scraper"
    APIFY_ACTOR_ALL_IN_ONE= "extractify-labs~flashscore-extractor"
    APIFY_ACTOR_TENNIS    = "extractify-labs~flashscore-tennis-matches"

    # TTLs
    TTL_LIVE    = 30
    TTL_UPCOMING = 600
    TTL_LEAGUES  = 86400

    REQUEST_TIMEOUT = 12
    MAX_RETRIES     = 2
    RETRY_DELAY     = 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# INSTANT STATIC FALLBACKS — always populated, never empty
# ═══════════════════════════════════════════════════════════════════════════════

STATIC_LEAGUES: Dict[str, List[Dict]] = {

    # ─────────────────────────────────────────────────────────────────────────
    # SOCCER  — 100+ competitions across every continent, active year-round
    # ─────────────────────────────────────────────────────────────────────────
    "Soccer": [
        # ── UEFA / Europe Top Tiers ──
        {"id": "39",  "name": "Premier League",            "country": "England"},
        {"id": "40",  "name": "Championship",              "country": "England"},
        {"id": "41",  "name": "League One",                "country": "England"},
        {"id": "42",  "name": "League Two",                "country": "England"},
        {"id": "45",  "name": "FA Cup",                    "country": "England"},
        {"id": "48",  "name": "EFL Cup (Carabao Cup)",     "country": "England"},
        {"id": "140", "name": "La Liga",                   "country": "Spain"},
        {"id": "141", "name": "La Liga 2",                 "country": "Spain"},
        {"id": "143", "name": "Copa del Rey",              "country": "Spain"},
        {"id": "135", "name": "Serie A",                   "country": "Italy"},
        {"id": "136", "name": "Serie B",                   "country": "Italy"},
        {"id": "137", "name": "Coppa Italia",              "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                "country": "Germany"},
        {"id": "79",  "name": "2. Bundesliga",             "country": "Germany"},
        {"id": "81",  "name": "DFB Pokal",                 "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                   "country": "France"},
        {"id": "62",  "name": "Ligue 2",                   "country": "France"},
        {"id": "20",  "name": "Coupe de France",           "country": "France"},
        {"id": "88",  "name": "Eredivisie",                "country": "Netherlands"},
        {"id": "89",  "name": "Eerste Divisie",            "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",             "country": "Portugal"},
        {"id": "95",  "name": "Liga Portugal 2",           "country": "Portugal"},
        {"id": "144", "name": "Belgian Pro League",        "country": "Belgium"},
        {"id": "197", "name": "Super Lig",                 "country": "Turkey"},
        {"id": "198", "name": "TFF First League",          "country": "Turkey"},
        {"id": "119", "name": "Superliga",                 "country": "Denmark"},
        {"id": "113", "name": "Allsvenskan",               "country": "Sweden"},
        {"id": "114", "name": "Superettan",                "country": "Sweden"},
        {"id": "103", "name": "Eliteserien",               "country": "Norway"},
        {"id": "106", "name": "Veikkausliiga",             "country": "Finland"},
        {"id": "116", "name": "Ekstraklasa",               "country": "Poland"},
        {"id": "318", "name": "Czech Liga",                "country": "Czech Republic"},
        {"id": "332", "name": "Slovak Super Liga",         "country": "Slovakia"},
        {"id": "271", "name": "Jupiler Pro League",        "country": "Belgium"},
        {"id": "179", "name": "Scottish Premiership",      "country": "Scotland"},
        {"id": "180", "name": "Scottish Championship",     "country": "Scotland"},
        {"id": "357", "name": "League of Ireland Premier", "country": "Ireland"},
        {"id": "130", "name": "Süper Lig",                 "country": "Austria"},
        {"id": "207", "name": "Super League",              "country": "Switzerland"},
        {"id": "218", "name": "Nemzeti Bajnokság",         "country": "Hungary"},
        {"id": "172", "name": "Super League",              "country": "Greece"},
        {"id": "235", "name": "Premier League",            "country": "Russia"},
        {"id": "296", "name": "Premier League",            "country": "Ukraine"},
        {"id": "271", "name": "First League",              "country": "Croatia"},
        {"id": "286", "name": "SuperLiga",                 "country": "Serbia"},
        {"id": "239", "name": "Premijer Liga",             "country": "Bosnia"},
        {"id": "274", "name": "Prva Liga",                 "country": "Slovenia"},
        {"id": "373", "name": "Categoryja Superiore",      "country": "Albania"},
        {"id": "387", "name": "Superliga",                 "country": "Romania"},
        {"id": "392", "name": "First League",              "country": "Bulgaria"},
        # ── UEFA Competitions ──
        {"id": "2",   "name": "UEFA Champions League",     "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",        "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League",    "country": "Europe"},
        {"id": "531", "name": "UEFA Super Cup",            "country": "Europe"},
        {"id": "960", "name": "UEFA Nations League",       "country": "Europe"},
        {"id": "4",   "name": "Euro Championship",         "country": "Europe"},
        {"id": "5",   "name": "UEFA U21 Championship",     "country": "Europe"},
        # ── Americas ──
        {"id": "253", "name": "MLS",                       "country": "USA"},
        {"id": "254", "name": "USL Championship",          "country": "USA"},
        {"id": "257", "name": "US Open Cup",               "country": "USA"},
        {"id": "262", "name": "Liga MX",                   "country": "Mexico"},
        {"id": "263", "name": "Liga MX Clausura",          "country": "Mexico"},
        {"id": "266", "name": "Copa MX",                   "country": "Mexico"},
        {"id": "71",  "name": "Brasileirao Serie A",       "country": "Brazil"},
        {"id": "72",  "name": "Brasileirao Serie B",       "country": "Brazil"},
        {"id": "73",  "name": "Copa do Brasil",            "country": "Brazil"},
        {"id": "242", "name": "Primera Division",          "country": "Argentina"},
        {"id": "281", "name": "Copa Argentina",            "country": "Argentina"},
        {"id": "265", "name": "Primera Division",          "country": "Colombia"},
        {"id": "239", "name": "Primera Division",          "country": "Chile"},
        {"id": "268", "name": "Primera Division",          "country": "Peru"},
        {"id": "270", "name": "Primera Division",          "country": "Uruguay"},
        {"id": "300", "name": "Primera Division",          "country": "Ecuador"},
        {"id": "308", "name": "Primera Division",          "country": "Venezuela"},
        {"id": "258", "name": "Primera Division",          "country": "Paraguay"},
        {"id": "11",  "name": "CONMEBOL Copa Libertadores","country": "S. America"},
        {"id": "13",  "name": "CONMEBOL Sudamericana",     "country": "S. America"},
        {"id": "9",   "name": "Copa America",              "country": "S. America"},
        {"id": "30",  "name": "CONCACAF Champions Cup",    "country": "N. America"},
        {"id": "26",  "name": "CONCACAF Nations League",   "country": "N. America"},
        # ── Africa ──
        {"id": "29",  "name": "CAF Champions League",      "country": "Africa"},
        {"id": "28",  "name": "CAF Confederation Cup",     "country": "Africa"},
        {"id": "6",   "name": "Africa Cup of Nations",     "country": "Africa"},
        {"id": "233", "name": "NPFL",                      "country": "Nigeria"},
        {"id": "128", "name": "Ligue Professionnelle 1",   "country": "Algeria"},
        {"id": "169", "name": "Egyptian Premier League",   "country": "Egypt"},
        {"id": "168", "name": "Botola Pro",                "country": "Morocco"},
        {"id": "360", "name": "Premier League",            "country": "South Africa"},
        {"id": "375", "name": "Premier League",            "country": "Ghana"},
        {"id": "370", "name": "KPL",                       "country": "Kenya"},
        {"id": "371", "name": "FUFA Premier League",       "country": "Uganda"},
        {"id": "363", "name": "Tanzanian Premier League",  "country": "Tanzania"},
        {"id": "376", "name": "Premier League",            "country": "Zambia"},
        {"id": "374", "name": "Super League",              "country": "Zimbabwe"},
        {"id": "377", "name": "Premier League",            "country": "Cameroon"},
        {"id": "378", "name": "Ligue 1",                   "country": "Senegal"},
        {"id": "379", "name": "Ligue 1",                   "country": "Ivory Coast"},
        {"id": "380", "name": "Division 1",                "country": "Tunisia"},
        # ── Asia & Middle East ──
        {"id": "283", "name": "Saudi Pro League",          "country": "Saudi Arabia"},
        {"id": "307", "name": "UAE Pro League",            "country": "UAE"},
        {"id": "17",  "name": "AFC Champions League",      "country": "Asia"},
        {"id": "98",  "name": "J-League",                  "country": "Japan"},
        {"id": "292", "name": "K League 1",                "country": "South Korea"},
        {"id": "169", "name": "Chinese Super League",      "country": "China"},
        {"id": "323", "name": "A-League",                  "country": "Australia"},
        {"id": "301", "name": "Indian Super League",       "country": "India"},
        {"id": "311", "name": "Qatar Stars League",        "country": "Qatar"},
        {"id": "329", "name": "Iraq Premier League",       "country": "Iraq"},
        {"id": "330", "name": "Jordan Premier League",     "country": "Jordan"},
        {"id": "326", "name": "Lebanese Premier League",   "country": "Lebanon"},
        # ── Women's Football ──
        {"id": "573", "name": "Women's Super League",      "country": "England"},
        {"id": "576", "name": "Division 1 Feminine",       "country": "France"},
        {"id": "570", "name": "Women's Bundesliga",        "country": "Germany"},
        {"id": "582", "name": "NWSL",                      "country": "USA"},
        {"id": "8",   "name": "FIFA Women's World Cup",    "country": "World"},
        # ── Global ──
        {"id": "1",   "name": "FIFA World Cup",            "country": "World"},
        {"id": "15",  "name": "FIFA Club World Cup",       "country": "World"},
        {"id": "10",  "name": "Friendlies — International","country": "World"},
        {"id": "667", "name": "Friendlies — Clubs",        "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # NBA / BASKETBALL  — Competitions & leagues worldwide
    # ─────────────────────────────────────────────────────────────────────────
    "NBA": [
        {"id": "NBA",        "name": "NBA",                           "country": "USA/Canada"},
        {"id": "NBA_P",      "name": "NBA Playoffs",                  "country": "USA/Canada"},
        {"id": "NBA_F",      "name": "NBA Finals",                    "country": "USA/Canada"},
        {"id": "NBA_AS",     "name": "NBA All-Star Weekend",          "country": "USA"},
        {"id": "NBAGL",      "name": "NBA G League",                  "country": "USA"},
        {"id": "NBAS",       "name": "NBA Summer League",             "country": "USA"},
        {"id": "WNBA",       "name": "WNBA",                         "country": "USA"},
        {"id": "EUROLEAGUE", "name": "EuroLeague",                    "country": "Europe"},
        {"id": "EUROCUP",    "name": "EuroCup",                       "country": "Europe"},
        {"id": "BCL",        "name": "Basketball Champions League",   "country": "Europe"},
        {"id": "ACB",        "name": "Liga ACB (Spain)",              "country": "Spain"},
        {"id": "LNB",        "name": "LNB Pro A",                     "country": "France"},
        {"id": "BSL",        "name": "BSL Super League",              "country": "Turkey"},
        {"id": "BBL_DE",     "name": "Basketball Bundesliga",         "country": "Germany"},
        {"id": "LBA",        "name": "Lega Basket Serie A",           "country": "Italy"},
        {"id": "VTB",        "name": "VTB United League",             "country": "Russia/Europe"},
        {"id": "BNXT",       "name": "BNXT League",                   "country": "Belgium/Netherlands"},
        {"id": "GBL",        "name": "Greek Basket League",           "country": "Greece"},
        {"id": "PLK",        "name": "Polish Basketball League",      "country": "Poland"},
        {"id": "NLB",        "name": "Adriatic League",               "country": "Balkans"},
        {"id": "NBB",        "name": "NBB (Brazil)",                  "country": "Brazil"},
        {"id": "LNBP",       "name": "LNBP (Mexico)",                 "country": "Mexico"},
        {"id": "LDB",        "name": "Liga de las Americas",          "country": "S. America"},
        {"id": "NBL_AU",     "name": "NBL (Australia)",               "country": "Australia"},
        {"id": "CBA",        "name": "CBA (China)",                   "country": "China"},
        {"id": "KBASKET",    "name": "KBL (Korea)",                   "country": "South Korea"},
        {"id": "JBASKET",    "name": "B.League (Japan)",              "country": "Japan"},
        {"id": "PBA",        "name": "PBA (Philippines)",             "country": "Philippines"},
        {"id": "BAL",        "name": "Basketball Africa League",      "country": "Africa"},
        {"id": "FIBA_WC",    "name": "FIBA World Cup",                "country": "World"},
        {"id": "FIBA_OLY",   "name": "Olympics — Basketball",         "country": "World"},
        {"id": "FIBA_W",     "name": "FIBA Women's World Cup",        "country": "World"},
        {"id": "FIBA_U19",   "name": "FIBA U19 World Cup",            "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # NFL / AMERICAN FOOTBALL  — Competitions & leagues worldwide
    # ─────────────────────────────────────────────────────────────────────────
    "NFL": [
        {"id": "NFL",        "name": "NFL",                           "country": "USA"},
        {"id": "NFL_PRE",    "name": "NFL Preseason",                 "country": "USA"},
        {"id": "NFL_PO",     "name": "NFL Playoffs",                  "country": "USA"},
        {"id": "NFL_SB",     "name": "Super Bowl",                    "country": "USA"},
        {"id": "NFL_PRO",    "name": "Pro Bowl Games",                "country": "USA"},
        {"id": "NFL_DRAFT",  "name": "NFL Draft",                     "country": "USA"},
        {"id": "NFL_INT",    "name": "NFL International Series",      "country": "UK/Germany"},
        {"id": "CFL",        "name": "CFL (Canadian Football League)","country": "Canada"},
        {"id": "USFL",       "name": "USFL",                         "country": "USA"},
        {"id": "XFL",        "name": "XFL",                          "country": "USA"},
        {"id": "UFLG",       "name": "UFL (United Football League)",  "country": "USA"},
        {"id": "NCAA_FBS",   "name": "NCAA FBS — College Football",   "country": "USA"},
        {"id": "NCAA_CFP",   "name": "College Football Playoff",      "country": "USA"},
        {"id": "ROSE_BOWL",  "name": "Rose Bowl",                     "country": "USA"},
        {"id": "SUGAR_BOWL", "name": "Sugar Bowl",                    "country": "USA"},
        {"id": "ORANGE_BOWL","name": "Orange Bowl",                   "country": "USA"},
        {"id": "COTTON_BOWL","name": "Cotton Bowl",                   "country": "USA"},
        {"id": "FIESTA_BOWL","name": "Fiesta Bowl",                   "country": "USA"},
        {"id": "NFL_OLY",    "name": "Olympics — Flag Football",      "country": "World"},
        {"id": "ELF",        "name": "ELF (European League of Football)","country": "Europe"},
        {"id": "AFLS",       "name": "AFL (Arena Football)",          "country": "USA"},
        {"id": "IFL",        "name": "IFL (Indoor Football League)",  "country": "USA"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # MLB / BASEBALL  — Competitions & leagues worldwide
    # ─────────────────────────────────────────────────────────────────────────
    "MLB": [
        {"id": "MLB",        "name": "MLB",                           "country": "USA/Canada"},
        {"id": "MLB_PO",     "name": "MLB Playoffs",                  "country": "USA/Canada"},
        {"id": "MLB_ALCS",   "name": "ALCS (AL Championship Series)", "country": "USA"},
        {"id": "MLB_NLCS",   "name": "NLCS (NL Championship Series)", "country": "USA"},
        {"id": "MLB_WS",     "name": "World Series",                  "country": "USA/Canada"},
        {"id": "MLB_AS",     "name": "MLB All-Star Game",             "country": "USA"},
        {"id": "MLB_AL",     "name": "American League",               "country": "USA/Canada"},
        {"id": "MLB_NL",     "name": "National League",               "country": "USA/Canada"},
        {"id": "AAA",        "name": "Triple-A (AAA)",                "country": "USA"},
        {"id": "AA",         "name": "Double-A (AA)",                 "country": "USA"},
        {"id": "HIGH_A",     "name": "High-A",                       "country": "USA"},
        {"id": "SINGLE_A",   "name": "Single-A",                     "country": "USA"},
        {"id": "NPB",        "name": "NPB (Japan Professional Baseball)","country": "Japan"},
        {"id": "KBO",        "name": "KBO League",                   "country": "South Korea"},
        {"id": "LMB",        "name": "LMB (Mexican League)",         "country": "Mexico"},
        {"id": "CPBL",       "name": "CPBL (Taiwan)",                "country": "Taiwan"},
        {"id": "KBO_PO",     "name": "KBO Playoffs",                 "country": "South Korea"},
        {"id": "WBC",        "name": "World Baseball Classic",       "country": "World"},
        {"id": "OLY_BB",     "name": "Olympics — Baseball",          "country": "World"},
        {"id": "PREMERA12",  "name": "Premier12",                    "country": "World"},
        {"id": "CARIBBEAN",  "name": "Caribbean Series",             "country": "Caribbean"},
        {"id": "LIDOM",      "name": "LIDOM (Dominican Republic)",   "country": "Dominican Republic"},
        {"id": "LVBP",       "name": "LVBP (Venezuela)",             "country": "Venezuela"},
        {"id": "LMP",        "name": "LMP (Mexico Pacific)",         "country": "Mexico"},
        {"id": "MILB_ALL",   "name": "MiLB All-Star Game",           "country": "USA"},
        {"id": "INDY_BB",    "name": "Independent Leagues (USA)",    "country": "USA"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # NHL / ICE HOCKEY  — Competitions & leagues worldwide
    # ─────────────────────────────────────────────────────────────────────────
    "NHL": [
        {"id": "NHL",        "name": "NHL",                           "country": "USA/Canada"},
        {"id": "NHL_PO",     "name": "NHL Playoffs",                  "country": "USA/Canada"},
        {"id": "NHL_CF",     "name": "NHL Conference Finals",         "country": "USA/Canada"},
        {"id": "NHL_SC",     "name": "Stanley Cup Finals",            "country": "USA/Canada"},
        {"id": "NHL_AS",     "name": "NHL All-Star Weekend",          "country": "USA"},
        {"id": "NHL_INT",    "name": "NHL Global Series",             "country": "Europe"},
        {"id": "AHL",        "name": "AHL (American Hockey League)",  "country": "USA/Canada"},
        {"id": "ECHL",       "name": "ECHL",                         "country": "USA/Canada"},
        {"id": "IIHF_WC",    "name": "IIHF World Championship",      "country": "World"},
        {"id": "IIHF_OLY",   "name": "Olympics — Ice Hockey",        "country": "World"},
        {"id": "IIHF_U20",   "name": "IIHF World Junior Championship","country": "World"},
        {"id": "IIHF_U18",   "name": "IIHF U18 Championship",        "country": "World"},
        {"id": "IIHF_W",     "name": "IIHF Women's World Championship","country": "World"},
        {"id": "SHL",        "name": "SHL (Swedish Hockey League)",  "country": "Sweden"},
        {"id": "Liiga",      "name": "Liiga (Finland)",               "country": "Finland"},
        {"id": "DEL",        "name": "DEL (Germany)",                 "country": "Germany"},
        {"id": "NLA",        "name": "National League (Switzerland)", "country": "Switzerland"},
        {"id": "KHL",        "name": "KHL (Kontinental Hockey League)","country": "Russia/Europe"},
        {"id": "HOCKEYALL",  "name": "Hockey Allsvenskan",            "country": "Sweden"},
        {"id": "MESTIS",     "name": "Mestis (Finland)",              "country": "Finland"},
        {"id": "CHAMPIONS_HL","name": "Champions Hockey League",     "country": "Europe"},
        {"id": "OHL",        "name": "OHL (Ontario Hockey League)",   "country": "Canada"},
        {"id": "WHL",        "name": "WHL (Western Hockey League)",   "country": "Canada"},
        {"id": "QMJHL",      "name": "QMJHL",                        "country": "Canada"},
        {"id": "CHL_MCC",    "name": "Memorial Cup",                  "country": "Canada"},
        {"id": "USHL",       "name": "USHL (US Hockey League)",       "country": "USA"},
        {"id": "NCAA_ICE",   "name": "NCAA Ice Hockey",               "country": "USA"},
        {"id": "PWHL",       "name": "PWHL (Women's)",                "country": "USA/Canada"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # UFC / MMA  — All weight classes + rival promotions
    # ─────────────────────────────────────────────────────────────────────────
    "UFC": [
        {"id": "UFC_ALL",     "name": "UFC — All Events",          "country": "World"},
        {"id": "UFC_PPV",     "name": "UFC PPV Events",            "country": "World"},
        {"id": "UFC_FN",      "name": "UFC Fight Night",           "country": "World"},
        {"id": "UFC_FN_SA",   "name": "UFC Fight Night — Saudi Arabia","country": "Saudi Arabia"},
        {"id": "UFC_FN_AU",   "name": "UFC Fight Night — Australia","country": "Australia"},
        {"id": "UFC_FN_EU",   "name": "UFC Fight Night — Europe",  "country": "Europe"},
        # Weight Classes
        {"id": "UFC_SW",      "name": "Strawweight (to 115 lb)",   "country": "World"},
        {"id": "UFC_FLW",     "name": "Flyweight (to 125 lb)",     "country": "World"},
        {"id": "UFC_BW",      "name": "Bantamweight (to 135 lb)",  "country": "World"},
        {"id": "UFC_FW",      "name": "Featherweight (to 145 lb)", "country": "World"},
        {"id": "UFC_LW",      "name": "Lightweight (to 155 lb)",   "country": "World"},
        {"id": "UFC_WW",      "name": "Welterweight (to 170 lb)",  "country": "World"},
        {"id": "UFC_MW",      "name": "Middleweight (to 185 lb)",  "country": "World"},
        {"id": "UFC_LHW",     "name": "Light Heavyweight (to 205 lb)","country": "World"},
        {"id": "UFC_HW",      "name": "Heavyweight (to 265 lb)",   "country": "World"},
        {"id": "UFC_WMSTRAW", "name": "Women's Strawweight",       "country": "World"},
        {"id": "UFC_WMFLY",   "name": "Women's Flyweight",         "country": "World"},
        {"id": "UFC_WMBW",    "name": "Women's Bantamweight",      "country": "World"},
        {"id": "UFC_WMFW",    "name": "Women's Featherweight",     "country": "World"},
        # Other MMA Promotions
        {"id": "BELLATOR",    "name": "Bellator MMA",              "country": "World"},
        {"id": "PFL",         "name": "PFL (Professional Fighters League)","country": "World"},
        {"id": "ONE_FC",      "name": "ONE Championship",          "country": "Asia"},
        {"id": "RIZIN",       "name": "RIZIN FF",                  "country": "Japan"},
        {"id": "KSW",         "name": "KSW",                       "country": "Poland"},
        {"id": "ACA",         "name": "ACA MMA",                   "country": "Russia"},
        {"id": "GLORY",       "name": "GLORY Kickboxing",          "country": "World"},
        {"id": "K1",          "name": "K-1 World GP",              "country": "World"},
        {"id": "ENFUSION",    "name": "Enfusion",                  "country": "World"},
        {"id": "BOXREC_HW",   "name": "Boxing — Heavyweight",      "country": "World"},
        {"id": "BOXREC_LHW",  "name": "Boxing — Light Heavyweight","country": "World"},
        {"id": "BOXREC_MW",   "name": "Boxing — Middleweight",     "country": "World"},
        {"id": "BOXREC_WW",   "name": "Boxing — Welterweight",     "country": "World"},
        {"id": "BOXREC_LW",   "name": "Boxing — Lightweight",      "country": "World"},
        {"id": "BOXREC_FW",   "name": "Boxing — Featherweight",    "country": "World"},
        {"id": "BOXREC_BW",   "name": "Boxing — Bantamweight",     "country": "World"},
        {"id": "WBC",         "name": "WBC Bouts",                 "country": "World"},
        {"id": "IBF",         "name": "IBF Bouts",                 "country": "World"},
        {"id": "WBA",         "name": "WBA Bouts",                 "country": "World"},
        {"id": "WBO",         "name": "WBO Bouts",                 "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # FORMULA 1  — All races + support series
    # ─────────────────────────────────────────────────────────────────────────
    "Formula 1": [
        {"id": "F1_ALL",   "name": "F1 — Full Season",           "country": "World"},
        {"id": "F1_SPRINT","name": "F1 Sprint Weekends",         "country": "World"},
        {"id": "F1_QUAL",  "name": "F1 Qualifying",              "country": "World"},
        {"id": "F1_AUS",   "name": "Australian GP — Melbourne",  "country": "Australia"},
        {"id": "F1_CHN",   "name": "Chinese GP — Shanghai",      "country": "China"},
        {"id": "F1_JPN",   "name": "Japanese GP — Suzuka",       "country": "Japan"},
        {"id": "F1_BHR",   "name": "Bahrain GP — Sakhir",        "country": "Bahrain"},
        {"id": "F1_SAU",   "name": "Saudi Arabian GP — Jeddah",  "country": "Saudi Arabia"},
        {"id": "F1_MIA",   "name": "Miami GP — Miami Gardens",   "country": "USA"},
        {"id": "F1_ITA",   "name": "Emilia Romagna GP — Imola",  "country": "Italy"},
        {"id": "F1_MON",   "name": "Monaco GP — Monte Carlo",    "country": "Monaco"},
        {"id": "F1_CAN",   "name": "Canadian GP — Montreal",     "country": "Canada"},
        {"id": "F1_ESP",   "name": "Spanish GP — Barcelona",     "country": "Spain"},
        {"id": "F1_AUT",   "name": "Austrian GP — Spielberg",    "country": "Austria"},
        {"id": "F1_GBR",   "name": "British GP — Silverstone",   "country": "England"},
        {"id": "F1_HUN",   "name": "Hungarian GP — Budapest",    "country": "Hungary"},
        {"id": "F1_BEL",   "name": "Belgian GP — Spa",           "country": "Belgium"},
        {"id": "F1_NLD",   "name": "Dutch GP — Zandvoort",       "country": "Netherlands"},
        {"id": "F1_ITA2",  "name": "Italian GP — Monza",         "country": "Italy"},
        {"id": "F1_AZE",   "name": "Azerbaijan GP — Baku",       "country": "Azerbaijan"},
        {"id": "F1_SGP",   "name": "Singapore GP — Marina Bay",  "country": "Singapore"},
        {"id": "F1_USA",   "name": "US GP — Austin (COTA)",      "country": "USA"},
        {"id": "F1_MEX",   "name": "Mexico City GP",             "country": "Mexico"},
        {"id": "F1_BRA",   "name": "São Paulo GP — Interlagos",  "country": "Brazil"},
        {"id": "F1_LVG",   "name": "Las Vegas GP",               "country": "USA"},
        {"id": "F1_QAT",   "name": "Qatar GP — Lusail",          "country": "Qatar"},
        {"id": "F1_UAE",   "name": "Abu Dhabi GP — Yas Marina",  "country": "UAE"},
        # Support Series
        {"id": "F2",       "name": "Formula 2",                  "country": "World"},
        {"id": "F3",       "name": "Formula 3",                  "country": "World"},
        {"id": "F1_ACAD",  "name": "F1 Academy",                 "country": "World"},
        {"id": "INDYCAR",  "name": "IndyCar Series",             "country": "USA"},
        {"id": "INDY500",  "name": "Indianapolis 500",           "country": "USA"},
        {"id": "NASCAR_C", "name": "NASCAR Cup Series",          "country": "USA"},
        {"id": "NASCAR_X", "name": "NASCAR Xfinity Series",      "country": "USA"},
        {"id": "WEC",      "name": "WEC (World Endurance Championship)","country": "World"},
        {"id": "LE_MANS",  "name": "24 Hours of Le Mans",        "country": "France"},
        {"id": "DTMS",     "name": "DTM",                        "country": "Germany"},
        {"id": "FERF",     "name": "Formula E",                  "country": "World"},
        {"id": "SUPERCARS","name": "Supercars Championship",      "country": "Australia"},
        {"id": "WTCR",     "name": "WTCR",                       "country": "World"},
        {"id": "MOTO_GP",  "name": "MotoGP",                     "country": "World"},
        {"id": "MOTO_2",   "name": "Moto2",                      "country": "World"},
        {"id": "MOTO_3",   "name": "Moto3",                      "country": "World"},
        {"id": "WSBK",     "name": "World Superbike Championship","country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # TENNIS  — All Grand Slams, Masters, Tours and Davis/Billie Jean King Cup
    # ─────────────────────────────────────────────────────────────────────────
    "Tennis": [
        {"id": "ATP_ALL",    "name": "ATP Tour — All Events",     "country": "World"},
        {"id": "WTA_ALL",    "name": "WTA Tour — All Events",     "country": "World"},
        # Grand Slams
        {"id": "AUS_OPEN",   "name": "Australian Open",           "country": "Australia"},
        {"id": "FRENCH_OPEN","name": "Roland Garros",             "country": "France"},
        {"id": "WIMBLEDON",  "name": "Wimbledon",                 "country": "England"},
        {"id": "US_OPEN",    "name": "US Open",                   "country": "USA"},
        # ATP Masters 1000
        {"id": "M_INDIAN",   "name": "Indian Wells Masters",      "country": "USA"},
        {"id": "M_MIAMI",    "name": "Miami Open",                "country": "USA"},
        {"id": "M_MONTE",    "name": "Monte-Carlo Masters",       "country": "Monaco"},
        {"id": "M_MADRID",   "name": "Madrid Open",               "country": "Spain"},
        {"id": "M_ROME",     "name": "Italian Open (Rome)",       "country": "Italy"},
        {"id": "M_CANADA",   "name": "Canadian Open",             "country": "Canada"},
        {"id": "M_CINCI",    "name": "Cincinnati Masters",        "country": "USA"},
        {"id": "M_SHANG",    "name": "Shanghai Masters",          "country": "China"},
        {"id": "M_PARIS",    "name": "Paris Masters",             "country": "France"},
        # ATP 500
        {"id": "A500_DUBAI", "name": "Dubai Tennis Championships","country": "UAE"},
        {"id": "A500_BCNA",  "name": "Barcelona Open",            "country": "Spain"},
        {"id": "A500_HALLE", "name": "Halle Open",                "country": "Germany"},
        {"id": "A500_QUEENS","name": "Queen's Club Championships","country": "England"},
        {"id": "A500_TOKYO", "name": "Japan Open",                "country": "Japan"},
        {"id": "A500_VIENNA","name": "Vienna Open",               "country": "Austria"},
        {"id": "A500_BASEL", "name": "Swiss Indoors",             "country": "Switzerland"},
        # Season Finals
        {"id": "ATP_FINALS", "name": "ATP Finals",                "country": "Italy"},
        {"id": "WTA_FINALS", "name": "WTA Finals",                "country": "Saudi Arabia"},
        {"id": "NEXTGEN",    "name": "Next Gen ATP Finals",       "country": "Italy"},
        # Team Events
        {"id": "DAVIS_CUP",  "name": "Davis Cup Finals",          "country": "World"},
        {"id": "BJK_CUP",    "name": "Billie Jean King Cup",      "country": "World"},
        {"id": "UNITED_CUP", "name": "United Cup",                "country": "Australia"},
        {"id": "LAVER_CUP",  "name": "Laver Cup",                 "country": "World"},
        # Challenger / ITF
        {"id": "ATP_CHALL",  "name": "ATP Challenger Tour",       "country": "World"},
        {"id": "WTA_125",    "name": "WTA 125K Series",           "country": "World"},
        {"id": "ITF_MEN",    "name": "ITF Men's Circuit",         "country": "World"},
        {"id": "ITF_WOM",    "name": "ITF Women's Circuit",       "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # CRICKET  — All formats, all boards, T20 leagues worldwide
    # ─────────────────────────────────────────────────────────────────────────
    "Cricket": [
        # International formats
        {"id": "TEST",       "name": "Test Matches",              "country": "World"},
        {"id": "ODI",        "name": "ODI Internationals",        "country": "World"},
        {"id": "T20I",       "name": "T20 Internationals",        "country": "World"},
        # ICC Events
        {"id": "ICC_WC",     "name": "ICC Men's World Cup",       "country": "World"},
        {"id": "ICC_T20WC",  "name": "ICC T20 World Cup",         "country": "World"},
        {"id": "ICC_CT",     "name": "ICC Champions Trophy",      "country": "World"},
        {"id": "ICC_WTC",    "name": "World Test Championship",   "country": "World"},
        {"id": "ICC_WWC",    "name": "ICC Women's World Cup",     "country": "World"},
        {"id": "ICC_WT20WC", "name": "ICC Women's T20 World Cup", "country": "World"},
        {"id": "ICC_U19",    "name": "ICC U19 World Cup",         "country": "World"},
        # T20 Franchise Leagues
        {"id": "IPL",        "name": "IPL (Indian Premier League)","country": "India"},
        {"id": "BBL",        "name": "Big Bash League",           "country": "Australia"},
        {"id": "PSL",        "name": "Pakistan Super League",     "country": "Pakistan"},
        {"id": "CPL",        "name": "Caribbean Premier League",  "country": "Caribbean"},
        {"id": "SA20",       "name": "SA20",                      "country": "South Africa"},
        {"id": "ILT20",      "name": "ILT20",                     "country": "UAE"},
        {"id": "LPL",        "name": "Lanka Premier League",      "country": "Sri Lanka"},
        {"id": "BPL",        "name": "Bangladesh Premier League", "country": "Bangladesh"},
        {"id": "MLC",        "name": "Major League Cricket (USA)","country": "USA"},
        {"id": "T20_BLAST",  "name": "Vitality T20 Blast",        "country": "England"},
        {"id": "THE_100",    "name": "The Hundred",               "country": "England"},
        {"id": "CSA_T20",    "name": "CSA T20 Challenge",         "country": "South Africa"},
        {"id": "TNPL",       "name": "TNPL",                      "country": "India"},
        {"id": "CT20",       "name": "Canada T20",                "country": "Canada"},
        # Bilateral Series
        {"id": "ENG_IND",    "name": "England vs India",          "country": "World"},
        {"id": "AUS_ENG",    "name": "The Ashes",                 "country": "World"},
        {"id": "ENG_SA",     "name": "England vs South Africa",   "country": "World"},
        {"id": "AUS_IND",    "name": "Australia vs India",        "country": "World"},
        {"id": "PAK_ENG",    "name": "Pakistan vs England",       "country": "World"},
        # Domestic
        {"id": "RANJI",      "name": "Ranji Trophy",              "country": "India"},
        {"id": "SHEFFIELD",  "name": "Sheffield Shield",          "country": "Australia"},
        {"id": "COUNTY",     "name": "County Championship",       "country": "England"},
        {"id": "CSA4DAY",    "name": "CSA 4-Day Series",          "country": "South Africa"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # GOLF  — All majors, world tours and international events
    # ─────────────────────────────────────────────────────────────────────────
    "Golf": [
        {"id": "PGA_ALL",    "name": "PGA Tour — All Events",     "country": "USA"},
        {"id": "DP_ALL",     "name": "DP World Tour — All Events","country": "Europe"},
        {"id": "LIV_ALL",    "name": "LIV Golf — All Events",     "country": "World"},
        # Majors
        {"id": "MASTERS",    "name": "The Masters — Augusta",     "country": "USA"},
        {"id": "PGA_CHAMP",  "name": "PGA Championship",          "country": "USA"},
        {"id": "US_OPEN_G",  "name": "US Open (Golf)",            "country": "USA"},
        {"id": "THE_OPEN",   "name": "The Open Championship",     "country": "UK"},
        # PGA Tour Flagship
        {"id": "PLAYERS",    "name": "The Players Championship",  "country": "USA"},
        {"id": "TOUR_CHAMP", "name": "Tour Championship",         "country": "USA"},
        {"id": "FED_EX",     "name": "FedEx Cup Playoffs",        "country": "USA"},
        {"id": "GENESIS",    "name": "Genesis Invitational",      "country": "USA"},
        {"id": "ARNOLD",     "name": "Arnold Palmer Invitational","country": "USA"},
        {"id": "MEMORIAL",   "name": "Memorial Tournament",       "country": "USA"},
        {"id": "WELLS_FARGO","name": "Wells Fargo Championship",  "country": "USA"},
        {"id": "TRAVELERS",  "name": "Travelers Championship",    "country": "USA"},
        {"id": "JOHN_DEERE", "name": "John Deere Classic",        "country": "USA"},
        {"id": "ROCKET",     "name": "Rocket Mortgage Classic",   "country": "USA"},
        {"id": "3M_OPEN",    "name": "3M Open",                   "country": "USA"},
        {"id": "WYNDHAM",    "name": "Wyndham Championship",      "country": "USA"},
        # DP World Tour
        {"id": "DP_HERO",    "name": "Hero Dubai Desert Classic", "country": "UAE"},
        {"id": "DP_SCOTTISH","name": "Scottish Open",             "country": "Scotland"},
        {"id": "DP_IRISH",   "name": "Irish Open",                "country": "Ireland"},
        {"id": "DP_BMW",     "name": "BMW PGA Championship",      "country": "England"},
        {"id": "DP_SWISS",   "name": "Swiss Challenge",           "country": "Switzerland"},
        {"id": "DP_ITALY",   "name": "Italian Open",              "country": "Italy"},
        # Team Events
        {"id": "RYDER_CUP",  "name": "Ryder Cup",                "country": "World"},
        {"id": "PRES_CUP",   "name": "Presidents Cup",           "country": "World"},
        {"id": "SOLHEIM",    "name": "Solheim Cup",               "country": "World"},
        # Other Tours
        {"id": "KORN_FERRY", "name": "Korn Ferry Tour",          "country": "USA"},
        {"id": "LPGA_ALL",   "name": "LPGA Tour — All Events",   "country": "USA"},
        {"id": "LPGA_ANA",   "name": "ANA Inspiration (LPGA Major)","country": "USA"},
        {"id": "SENIOR_PGA", "name": "PGA Tour Champions",       "country": "USA"},
        {"id": "JAPAN_GOLF", "name": "JGTO Tour",                "country": "Japan"},
        {"id": "ASIAN_TOUR", "name": "Asian Tour",               "country": "Asia"},
        {"id": "SUNSHINE",   "name": "Sunshine Tour",            "country": "South Africa"},
        {"id": "PGA_AUS",    "name": "PGA Tour of Australasia",  "country": "Australia"},
    ],
    # ─────────────────────────────────────────────────────────────────────────
    # VOLLEYBALL  — International + domestic leagues year-round
    # ─────────────────────────────────────────────────────────────────────────
    "Volleyball": [
        {"id": "VB_ALL",     "name": "Volleyball — All Events",       "country": "World"},
        {"id": "FIVB_WL",    "name": "FIVB Volleyball Nations League","country": "World"},
        {"id": "FIVB_WC",    "name": "FIVB World Championship",       "country": "World"},
        {"id": "FIVB_OLY",   "name": "Olympics — Volleyball",         "country": "World"},
        {"id": "VB_CEV_CL",  "name": "CEV Champions League",          "country": "Europe"},
        {"id": "VB_CEV_CC",  "name": "CEV Cup",                       "country": "Europe"},
        {"id": "SUPERLIGA_IT","name": "SuperLega (Italy)",             "country": "Italy"},
        {"id": "BUNDESLIGA_VB","name": "Bundesliga Volleyball",        "country": "Germany"},
        {"id": "LIGUE_A",    "name": "Ligue A",                       "country": "France"},
        {"id": "PLUSLIGA",   "name": "PlusLiga",                      "country": "Poland"},
        {"id": "SUPERLIG_VB","name": "Efeler Ligi",                   "country": "Turkey"},
        {"id": "SUPERLIGA_RU","name": "Superliga (Russia)",            "country": "Russia"},
        {"id": "NBV_BR",     "name": "Superliga Nacional (Brazil)",   "country": "Brazil"},
        {"id": "AVL_AUS",    "name": "AVL (Australia)",               "country": "Australia"},
        {"id": "KOVO",       "name": "V-League (Korea)",              "country": "South Korea"},
        {"id": "V1_JPN",     "name": "V1 League (Japan)",             "country": "Japan"},
        {"id": "BVL_BR",     "name": "Beach Volleyball — World Tour", "country": "World"},
        {"id": "AVP",        "name": "AVP Beach Volleyball",          "country": "USA"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # DARTS  — PDC, BDO and all major tournaments
    # ─────────────────────────────────────────────────────────────────────────
    "Darts": [
        {"id": "DARTS_ALL",  "name": "Darts — All Events",            "country": "World"},
        {"id": "PDC_WC",     "name": "PDC World Championship",        "country": "UK"},
        {"id": "PDC_PL",     "name": "PDC Premier League Darts",      "country": "UK/Europe"},
        {"id": "PDC_WM",     "name": "World Matchplay",               "country": "UK"},
        {"id": "PDC_WGP",    "name": "World Grand Prix",              "country": "Ireland"},
        {"id": "PDC_GC",     "name": "Grand Slam of Darts",           "country": "UK"},
        {"id": "PDC_EC",     "name": "European Championship",         "country": "Europe"},
        {"id": "PDC_WT",     "name": "PDC World Trophy",              "country": "World"},
        {"id": "PDC_EURO",   "name": "European Tour",                 "country": "Europe"},
        {"id": "PDC_UK_OPEN","name": "UK Open",                       "country": "UK"},
        {"id": "PDC_MASTERS","name": "Masters",                       "country": "UK"},
        {"id": "PDC_OPEN",   "name": "Players Championship",          "country": "UK"},
        {"id": "PDC_WC_QL",  "name": "PDC World Cup of Darts",        "country": "Germany"},
        {"id": "PDC_INT",    "name": "International Darts Open",      "country": "Germany"},
        {"id": "WDF_WC",     "name": "WDF World Championship",        "country": "World"},
        {"id": "PDC_CHALL",  "name": "PDC Challenge Tour",            "country": "UK"},
        {"id": "PDC_SUPER",  "name": "Super Series",                  "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # SNOOKER  — All ranking events + invitational
    # ─────────────────────────────────────────────────────────────────────────
    "Snooker": [
        {"id": "SNK_ALL",    "name": "Snooker — All Events",          "country": "World"},
        {"id": "SNK_WC",     "name": "World Snooker Championship",    "country": "UK"},
        {"id": "SNK_MASTERS","name": "Masters",                       "country": "UK"},
        {"id": "SNK_UK",     "name": "UK Championship",               "country": "UK"},
        {"id": "SNK_TOUR",   "name": "Tour Championship",             "country": "UK"},
        {"id": "SNK_PLAYERS","name": "Players Championship",          "country": "UK"},
        {"id": "SNK_CHINA",  "name": "Shanghai Masters",              "country": "China"},
        {"id": "SNK_INT_CH", "name": "International Championship",    "country": "China"},
        {"id": "SNK_WORLD_O","name": "World Open",                    "country": "China"},
        {"id": "SNK_WELSH",  "name": "Welsh Open",                    "country": "Wales"},
        {"id": "SNK_GERMAN", "name": "German Masters",                "country": "Germany"},
        {"id": "SNK_SCOTTISH","name": "Scottish Open",                "country": "Scotland"},
        {"id": "SNK_ENGLISH","name": "English Open",                  "country": "England"},
        {"id": "SNK_HONG_K", "name": "Hong Kong Masters",             "country": "Hong Kong"},
        {"id": "SNK_CHAMPION","name": "Champion of Champions",        "country": "UK"},
        {"id": "SNK_SHOOT",  "name": "Shoot Out",                     "country": "UK"},
        {"id": "SNK_PAUL_H", "name": "Paul Hunter Classic",           "country": "Germany"},
        {"id": "SNK_RIGA",   "name": "Riga Masters",                  "country": "Latvia"},
        {"id": "SNK_EURO",   "name": "European Masters",              "country": "Europe"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # TABLE TENNIS  — ITTF World Tour + major leagues
    # ─────────────────────────────────────────────────────────────────────────
    "Table Tennis": [
        {"id": "TT_ALL",     "name": "Table Tennis — All Events",     "country": "World"},
        {"id": "WTT_CHAMP",  "name": "WTT Champions",                 "country": "World"},
        {"id": "WTT_STAR",   "name": "WTT Star Contender",            "country": "World"},
        {"id": "WTT_CONT",   "name": "WTT Contender",                 "country": "World"},
        {"id": "ITTF_WC",    "name": "ITTF World Championship",       "country": "World"},
        {"id": "ITTF_WT",    "name": "ITTF World Tour Grand Finals",  "country": "World"},
        {"id": "TT_OLY",     "name": "Olympics — Table Tennis",       "country": "World"},
        {"id": "TT_EURO_CH", "name": "European Championship",         "country": "Europe"},
        {"id": "TT_ASIA_CH", "name": "Asian Championship",            "country": "Asia"},
        {"id": "SUPER_LIGA", "name": "Superliga (Germany)",           "country": "Germany"},
        {"id": "TT_BL",      "name": "Bundesliga TT",                 "country": "Germany"},
        {"id": "TT_PRO_TOUR","name": "Pro Tour (China)",              "country": "China"},
        {"id": "TT_CUP",     "name": "ITTF Team World Cup",           "country": "World"},
        {"id": "TT_YOUTH",   "name": "ITTF World Youth Championship", "country": "World"},
        {"id": "TT_MIXED",   "name": "Mixed Team World Championship", "country": "World"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # HANDBALL  — EHF Champions League + all major leagues
    # ─────────────────────────────────────────────────────────────────────────
    "Handball": [
        {"id": "HB_ALL",     "name": "Handball — All Events",         "country": "World"},
        {"id": "EHF_CL",     "name": "EHF Champions League",          "country": "Europe"},
        {"id": "EHF_EL",     "name": "EHF European League",           "country": "Europe"},
        {"id": "EHF_CC",     "name": "EHF Cup",                       "country": "Europe"},
        {"id": "IHF_WC",     "name": "IHF World Championship",        "country": "World"},
        {"id": "HB_OLY",     "name": "Olympics — Handball",           "country": "World"},
        {"id": "EHF_EURO",   "name": "EHF Euro Championship",         "country": "Europe"},
        {"id": "BUNDES_HB",  "name": "Handball Bundesliga",           "country": "Germany"},
        {"id": "LNH",        "name": "Lidl Starligue (France)",       "country": "France"},
        {"id": "LIGA_ASOBAL","name": "Liga ASOBAL",                   "country": "Spain"},
        {"id": "VELUX_DK",   "name": "Danish Handball League",        "country": "Denmark"},
        {"id": "SHB",        "name": "Swedish Handbollsligan",        "country": "Sweden"},
        {"id": "PICK_SZE",   "name": "Hungarian League",              "country": "Hungary"},
        {"id": "SEHA",       "name": "SEHA League",                   "country": "Balkans"},
        {"id": "HB_PLN",     "name": "PGNiG Superliga",               "country": "Poland"},
        {"id": "IHF_W_WC",   "name": "IHF Women's World Championship","country": "World"},
        {"id": "EHF_W_CL",   "name": "EHF Women's Champions League",  "country": "Europe"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # RUGBY  — All codes: Union, League, Sevens
    # ─────────────────────────────────────────────────────────────────────────
    "Rugby": [
        {"id": "RU_ALL",     "name": "Rugby Union — All Events",      "country": "World"},
        {"id": "RWC",        "name": "Rugby World Cup",               "country": "World"},
        {"id": "SIX_NATIONS","name": "Six Nations Championship",      "country": "Europe"},
        {"id": "THE_RUGBY_CH","name": "The Rugby Championship",       "country": "S. Hemisphere"},
        {"id": "URC",        "name": "United Rugby Championship",     "country": "Europe/Africa"},
        {"id": "PREMIERSHIP","name": "Gallagher Premiership",         "country": "England"},
        {"id": "TOP_14",     "name": "Top 14",                        "country": "France"},
        {"id": "SUPER_RUGBY","name": "Super Rugby Pacific",           "country": "Oceania/Asia"},
        {"id": "PRO_D2",     "name": "Pro D2",                        "country": "France"},
        {"id": "CURRIE_CUP", "name": "Currie Cup",                    "country": "South Africa"},
        {"id": "RUGBYEURO",  "name": "Rugby Europe Championship",     "country": "Europe"},
        {"id": "HSBC_SEVENS","name": "HSBC World Rugby Sevens Series","country": "World"},
        {"id": "RU_OLY",     "name": "Olympics — Rugby Sevens",       "country": "World"},
        {"id": "NRL",        "name": "NRL (Rugby League)",            "country": "Australia"},
        {"id": "SL_RL",      "name": "Super League (Rugby League)",   "country": "UK"},
        {"id": "RL_WC",      "name": "Rugby League World Cup",        "country": "World"},
        {"id": "STATE_ORIGIN","name": "State of Origin",              "country": "Australia"},
        {"id": "CH_CUP",     "name": "Challenge Cup (Rugby League)",  "country": "UK"},
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # ESPORTS  — Fastest growing betting market
    # ─────────────────────────────────────────────────────────────────────────
    "Esports": [
        {"id": "ES_ALL",     "name": "Esports — All Events",          "country": "World"},
        {"id": "LOL_WC",     "name": "League of Legends World Championship","country": "World"},
        {"id": "LOL_LCK",    "name": "LCK (Korea)",                   "country": "South Korea"},
        {"id": "LOL_LPL",    "name": "LPL (China)",                   "country": "China"},
        {"id": "LOL_LEC",    "name": "LEC (Europe)",                  "country": "Europe"},
        {"id": "LOL_LCS",    "name": "LCS (North America)",           "country": "USA"},
        {"id": "DOTA_TI",    "name": "Dota 2 — The International",    "country": "World"},
        {"id": "DOTA_DPC",   "name": "Dota Pro Circuit",              "country": "World"},
        {"id": "CS_MAJOR",   "name": "CS2 Major Championship",        "country": "World"},
        {"id": "CS_ESL",     "name": "ESL Pro League (CS2)",          "country": "World"},
        {"id": "VALORANT_WC","name": "Valorant Champions",            "country": "World"},
        {"id": "VALORANT_VCT","name": "VCT International League",     "country": "World"},
        {"id": "OVERWATCH_L","name": "Overwatch League",              "country": "World"},
        {"id": "ROCKET_RLCS","name": "Rocket League Championship",    "country": "World"},
        {"id": "FIFA_EWWC",  "name": "EA Sports FC World Cup",        "country": "World"},
        {"id": "COD_CDL",    "name": "Call of Duty League",           "country": "World"},
        {"id": "STARCRAFT",  "name": "StarCraft II — GSL",            "country": "South Korea"},
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
    home_team_id: Optional[str]      = None
    away_team_id: Optional[str]      = None
    home_score:   Optional[int]      = None
    away_score:   Optional[int]      = None
    status:       str                = "SCHEDULED"
    minute:       Optional[int]      = None
    start_time:   Optional[datetime] = None
    venue:        Optional[str]      = None
    country:      Optional[str]      = None

    def to_dataframe_row(self) -> Dict:
        su = self.status.upper()
        is_live = any(x in su for x in [
            "LIVE", "1H", "2H", "HT", "IN_PROGRESS",
            "1ST", "2ND", "3RD", "4TH", "OT", "IN_PLAY",
        ])
        is_done = any(x in su for x in [
            "FINISHED", "FT", "AET", "PEN", "COMPLETED", "FINAL",
        ])
        if is_live:
            display = "🔴 LIVE"
        elif is_done:
            display = "✅ FINISHED"
        else:
            display = "⏳ UPCOMING"

        return {
            "MATCH_ID":  self.match_id,
            "TIME":      self.start_time.strftime("%d %b %H:%M") if self.start_time else "TBD",
            "LEAGUE":    self.league,
            "HOME_TEAM": self.home_team,
            "AWAY_TEAM": self.away_team,
            "MATCH":     f"{self.home_team} vs {self.away_team}",
            "STATUS":    display,
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
        self.cache: Dict[str, Any] = {}

    def _make_request(self, url: str, headers: Dict = None,
                      params: Dict = None) -> Optional[Dict]:
        for attempt in range(APIConfig.MAX_RETRIES):
            try:
                r = requests.get(
                    url,
                    headers=headers or {},
                    params=params or {},
                    timeout=APIConfig.REQUEST_TIMEOUT,
                )
                if r.status_code == 429:
                    time.sleep((attempt + 1) * 2)
                    continue
                if r.status_code == 200:
                    return r.json()
                logger.warning(f"[{self.name}] HTTP {r.status_code} {url}")
                return None
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.name}] Timeout attempt {attempt+1}")
            except Exception as e:
                logger.error(f"[{self.name}] {e}")
            if attempt < APIConfig.MAX_RETRIES - 1:
                time.sleep(APIConfig.RETRY_DELAY * (attempt + 1))
        return None

    def _ck(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def _get(self, key: str, ttl: int) -> Optional[Any]:
        e = self.cache.get(key)
        return e["v"] if e and time.time() - e["t"] < ttl else None

    def _set(self, key: str, val: Any):
        self.cache[key] = {"v": val, "t": time.time()}


# ═══════════════════════════════════════════════════════════════════════════════
# API-SPORTS  (Soccer)
# ═══════════════════════════════════════════════════════════════════════════════

class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.base    = APIConfig.API_SPORTS_URL
        self.headers = {"x-apisports-key": APIConfig.API_SPORTS_KEY} \
                       if APIConfig.API_SPORTS_KEY else {}

    @property
    def ok(self) -> bool:
        return bool(APIConfig.API_SPORTS_KEY)

    def get_leagues(self) -> List[Dict]:
        """Return soccer leagues from API, merged over static fallback."""
        if not self.ok:
            return []
        ck = self._ck("apisports_leagues")
        cached = self._get(ck, APIConfig.TTL_LEAGUES)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base}/leagues", self.headers)
        if not data:
            return []
        leagues = []
        for item in data.get("response", []):
            lg = item.get("league", {})
            co = item.get("country", {})
            leagues.append({
                "id":      str(lg.get("id", "")),
                "name":    lg.get("name", "Unknown"),
                "country": co.get("name", ""),
            })
        self._set(ck, leagues)
        return leagues

    def get_live_matches(self, league_id: str = None) -> List[Match]:
        if not self.ok:
            return []
        ck = self._ck("apisports_live", league_id)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        params = {"live": "all"}
        if league_id and league_id not in ("ALL", ""):
            params["league"] = league_id
        data = self._make_request(f"{self.base}/fixtures", self.headers, params)
        matches = self._parse_fixtures(data) if data else []
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        ck = self._ck("apisports_upcoming", today)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._make_request(f"{self.base}/fixtures", self.headers,
                                  {"from": today, "to": future})
        matches = self._parse_fixtures(data) if data else []
        self._set(ck, matches)
        return matches

    def _parse_fixtures(self, data: Dict) -> List[Match]:
        matches = []
        for fx in data.get("response", []):
            f      = fx.get("fixture", {})
            league = fx.get("league", {})
            teams  = fx.get("teams", {})
            goals  = fx.get("goals", {})
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
# MYSPORTSFEEDS  (NBA · NFL · MLB · NHL)
# ═══════════════════════════════════════════════════════════════════════════════

class MySportsFeedsProvider(DataProvider):
    CODES = {"NBA": "nba", "NFL": "nfl", "MLB": "mlb", "NHL": "nhl"}

    def __init__(self):
        super().__init__("MySportsFeeds")
        self.base = APIConfig.MYSPORTSFEEDS_URL
        if APIConfig.MYSPORTSFEEDS_KEY and APIConfig.MYSPORTSFEEDS_PASSWORD:
            creds = base64.b64encode(
                f"{APIConfig.MYSPORTSFEEDS_KEY}:{APIConfig.MYSPORTSFEEDS_PASSWORD}".encode()
            ).decode()
            self.headers = {"Authorization": f"Basic {creds}"}
        else:
            self.headers = {}

    @property
    def ok(self) -> bool:
        return bool(self.headers)

    def _season(self, sport: str) -> str:
        now = datetime.now()
        s   = sport.upper()
        if s in ("NBA", "NHL"):
            return f"{now.year}-{now.year+1}" if now.month >= 10 else f"{now.year-1}-{now.year}"
        if s == "NFL":
            return str(now.year) if now.month >= 8 else str(now.year - 1)
        return str(now.year)  # MLB

    def _code(self, sport: str) -> str:
        return self.CODES.get(sport.upper(), "nba")

    def get_live_matches(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        code  = self._code(sport)
        season = self._season(sport)
        today = datetime.now().strftime("%Y%m%d")
        ck = self._ck("msf_live", code, today)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        url  = f"{self.base}/{code}/{season}/date/{today}/games.json"
        data = self._make_request(url, self.headers)
        if not data:
            data = self._make_request(
                f"{self.base}/{code}/{season}/games.json", self.headers, {"date": today}
            )
        matches = self._parse(data, sport) if data else []
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str, days: int = 7) -> List[Match]:
        if not self.ok:
            return []
        code  = self._code(sport)
        season = self._season(sport)
        today  = datetime.now().strftime("%Y%m%d")
        future = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        ck = self._ck("msf_upcoming", code, today)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._make_request(
            f"{self.base}/{code}/{season}/games.json", self.headers,
            {"fordate": today, "todate": future},
        )
        matches = self._parse(data, sport, upcoming_only=True) if data else []
        self._set(ck, matches)
        return matches

    def _parse(self, data: Dict, sport: str, upcoming_only: bool = False) -> List[Match]:
        matches = []
        for game in data.get("games", []):
            sched      = game.get("schedule", game)
            raw_status = sched.get("playedStatus", sched.get("status", "UNPLAYED")).upper()
            is_live    = raw_status in ("IN_PROGRESS", "LIVE", "1ST", "2ND", "3RD", "4TH", "OT")
            is_done    = raw_status in ("COMPLETED", "FINAL", "COMPLETED_PENDING_REVIEW")
            if upcoming_only and (is_live or is_done):
                continue
            ht = sched.get("homeTeam", {})
            at = sched.get("awayTeam", {})
            home = (f"{ht.get('city','')} {ht.get('name','')}".strip()
                    if isinstance(ht, dict) else str(ht)) or "TBD"
            away = (f"{at.get('city','')} {at.get('name','')}".strip()
                    if isinstance(at, dict) else str(at)) or "TBD"
            sc = game.get("score", {}) or {}
            start = None
            for key in ("startTime", "startDate", "date"):
                raw = sched.get(key, "")
                if raw:
                    try:
                        start = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass
            matches.append(Match(
                match_id=str(sched.get("id", "")),
                provider="MySportsFeeds",
                league=sport,
                league_id=sport,
                home_team=home,
                away_team=away,
                home_score=sc.get("homeScoreTotal"),
                away_score=sc.get("awayScoreTotal"),
                status="LIVE" if is_live else ("FINISHED" if is_done else "SCHEDULED"),
                start_time=start,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB  (UFC · F1 · Tennis · Cricket · Golf)
# ═══════════════════════════════════════════════════════════════════════════════

class TheSportsDBProvider(DataProvider):
    LEAGUE_IDS = {
        "UFC":       "4467",
        "Formula 1": "4370",
        "Tennis":    "4424",
        "Cricket":   "4722",
        "Golf":      "4426",
    }

    def __init__(self):
        super().__init__("TheSportsDB")
        self.key  = APIConfig.THESPORTSDB_KEY or "3"
        self.base = APIConfig.THESPORTSDB_URL_V1

    def _req(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        url = f"{self.base}/{self.key}/{endpoint}"
        return self._make_request(url, params=params)

    def get_live_matches(self, sport: str) -> List[Match]:
        ck = self._ck("tsdb_live", sport)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached
        sport_map = {
            "UFC": "MMA", "Formula 1": "Motorsport",
            "Tennis": "Tennis", "Cricket": "Cricket", "Golf": "Golf",
        }
        data = self._req("livescore.php", {"s": sport_map.get(sport, sport)})
        matches = []
        if data and data.get("events"):
            for ev in data["events"]:
                is_live = ev.get("strStatus") in [
                    "1H", "2H", "HT", "IN_PLAY", "ET", "PEN_LIVE", "LIVE"
                ]
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(
                            f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M"
                        )
                    except Exception:
                        pass
                matches.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    home_score=_toint(ev.get("intHomeScore")),
                    away_score=_toint(ev.get("intAwayScore")),
                    status="LIVE" if is_live else (ev.get("strStatus") or "SCHEDULED"),
                    start_time=start,
                ))
        self._set(ck, matches)
        return matches

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        league_id = self.LEAGUE_IDS.get(sport)
        if not league_id:
            return []
        ck = self._ck("tsdb_upcoming", sport)
        cached = self._get(ck, APIConfig.TTL_UPCOMING)
        if cached is not None:
            return cached
        data = self._req("eventsnextleague.php", {"id": league_id})
        matches = []
        if data and data.get("events"):
            for ev in data["events"]:
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(
                            f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M"
                        )
                    except Exception:
                        pass
                matches.append(Match(
                    match_id=ev.get("idEvent", ""),
                    provider="TheSportsDB",
                    league=ev.get("strLeague", sport),
                    league_id=ev.get("idLeague", ""),
                    home_team=ev.get("strHomeTeam", "TBD"),
                    away_team=ev.get("strAwayTeam", "TBD"),
                    status="SCHEDULED",
                    start_time=start,
                ))
        self._set(ck, matches)
        return matches



# ═══════════════════════════════════════════════════════════════════════════════
# FLASHSCORE PROVIDER via Apify  — 30+ sports, instant cached responses
# ═══════════════════════════════════════════════════════════════════════════════

FS_SPORT_MAP = {
    "Soccer":       "football",
    "NBA":          "basketball",
    "NFL":          "american-football",
    "MLB":          "baseball",
    "NHL":          "hockey",
    "Tennis":       "tennis",
    "Cricket":      "cricket",
    "Rugby":        "rugby",
    "Volleyball":   "volleyball",
    "Handball":     "handball",
    "Table Tennis": "table-tennis",
    "Snooker":      "snooker",
    "Darts":        "darts",
    "Esports":      "esports",
    "Golf":         "golf",
    "Formula 1":    "motorsport",
    "UFC":          "mma",
}

# FlashScore actual status strings → normalised
FS_STATUS_LIVE = {
    "1st half", "2nd half", "halftime", "half time", "extra time",
    "extra time halftime", "penalties", "live", "in progress",
    "1h", "2h", "ht", "et", "pen", "ongoing", "1st period",
    "2nd period", "3rd period", "4th quarter", "overtime",
    "1st set", "2nd set", "3rd set", "4th set", "5th set",
    "in play", "inprogress", "progress", "interrupted",
}
FS_STATUS_DONE = {
    "finished", "ft", "final", "ended", "complete", "completed",
    "aet", "ap", "after penalties", "after extra time",
    "walkover", "retired", "abandoned", "awarded",
}
FS_STATUS_SKIP = {"cancelled", "canceled", "postponed", "suspended", "deleted"}

# Best available Apify actor — run-sync with sport input
APIFY_ACTOR_ID = "mgml2y26whpqzinhi"  # crawlerbros/flashscore-scraper canonical ID


class FlashScoreProvider(DataProvider):
    """
    FlashScore data via Apify — run-sync per sport with in-memory cache.

    Strategy:
    - run-sync-get-dataset-items: starts actor, waits max 55s, returns data
    - Results cached 30s (live) so repeat renders are instant
    - Background thread pre-warms priority sports on startup
    - Fully parses FlashScore's actual output schema (nested tournament obj,
      Unix timestamps, verbose status strings like "1st Half", "Finished")
    """

    # Priority sports to pre-warm on startup
    PRIORITY_SPORTS = ["Soccer", "Tennis", "Basketball", "Cricket"]

    def __init__(self):
        super().__init__("FlashScore/Apify")
        self.token    = APIConfig.APIFY_API_TOKEN
        self._prefetch_started = False

    @property
    def ok(self) -> bool:
        return bool(self.token)

    # ── Run actor synchronously (correct approach — passes sport as input) ────
    def _run_sync(self, sport: str, live_only: bool = False,
                  max_items: int = 300) -> Optional[List]:
        """Run actor with sport input and return items. Timeout 55s."""
        if not self.ok:
            return None
        fs_sport = FS_SPORT_MAP.get(sport, "football")
        url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"
        try:
            r = requests.post(
                url,
                params={"token": self.token, "timeout": 55, "memory": 256},
                json={
                    "sport":    fs_sport,
                    "liveOnly": live_only,
                    "maxItems": max_items,
                    "days":     0,   # today only
                },
                timeout=60,
            )
            if r.status_code == 200:
                items = r.json()
                return items if isinstance(items, list) else []
            logger.warning(f"[Apify run-sync] HTTP {r.status_code}: {r.text[:120]}")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"[Apify run-sync] Timeout for {sport}")
            return None
        except Exception as e:
            logger.error(f"[Apify run-sync] {sport}: {e}")
            return None

    # ── Background trigger (fire-and-forget refresh) ──────────────────────────
    def _trigger_refresh(self, sport: str):
        """Trigger a new run in background so next cache miss gets fresh data."""
        if not self.ok:
            return
        def _run():
            try:
                fs_sport = FS_SPORT_MAP.get(sport, "football")
                requests.post(
                    f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs",
                    params={"token": self.token},
                    json={"sport": fs_sport, "maxItems": 300, "days": 0},
                    timeout=5,
                )
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    # ── Pre-warm priority sports on startup ───────────────────────────────────
    def prefetch_all(self):
        if not self.ok or self._prefetch_started:
            return
        self._prefetch_started = True
        def _warm():
            for sport in self.PRIORITY_SPORTS:
                try:
                    self._fetch_sport(sport)
                    logger.info(f"[Apify prefetch] {sport} warmed")
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"[Apify prefetch] {sport}: {e}")
        threading.Thread(target=_warm, daemon=True).start()

    # ── Core fetch: cache → run-sync → trigger refresh ────────────────────────
    def _fetch_sport(self, sport: str) -> List[Match]:
        ck = self._ck("fs_all", sport)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            return cached

        items = self._run_sync(sport, live_only=False, max_items=300)
        if items is None:
            # No result — trigger background run for next time
            self._trigger_refresh(sport)
            return []

        matches = self._parse_items(items, sport)
        self._set(ck, matches)
        return matches

    def get_live_matches(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        return [m for m in self._fetch_sport(sport) if m.status == "LIVE"]

    def get_upcoming_matches(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        return [m for m in self._fetch_sport(sport) if m.status == "SCHEDULED"]

    def get_all_today(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        return self._fetch_sport(sport)

    # ── Parser: handles FlashScore's actual output schema ────────────────────
    def _parse_items(self, items: List[Dict], sport: str) -> List[Match]:
        matches = []
        for item in items:
            if not isinstance(item, dict):
                continue

            # ── Teams ──────────────────────────────────────────────────────
            home_raw = (item.get("homeTeam") or item.get("homeName") or
                        item.get("home")     or "")
            away_raw = (item.get("awayTeam") or item.get("awayName") or
                        item.get("away")     or "")
            # homeTeam can be a string or {"name": "Arsenal", "id": "1"}
            home = (home_raw.get("name") if isinstance(home_raw, dict)
                    else str(home_raw)) or "TBD"
            away = (away_raw.get("name") if isinstance(away_raw, dict)
                    else str(away_raw)) or "TBD"

            # ── League / tournament ────────────────────────────────────────
            # tournament can be {"name": "Premier League", "category": {...}}
            tourn_raw = (item.get("tournament") or item.get("league") or
                         item.get("competition") or {})
            if isinstance(tourn_raw, dict):
                league  = tourn_raw.get("name", sport)
                country = (tourn_raw.get("category", {}) or {}).get("name", "")
                l_id    = str(tourn_raw.get("id", ""))
            else:
                league  = str(tourn_raw) or sport
                country = str(item.get("country") or item.get("countryName") or "")
                l_id    = str(item.get("tournamentId") or item.get("leagueId") or "")

            # ── Match ID ───────────────────────────────────────────────────
            mid = str(item.get("id") or item.get("matchId") or
                      abs(hash(f"{home}{away}{league}"))%10**9)

            # ── Status ─────────────────────────────────────────────────────
            raw_st  = str(item.get("status") or item.get("matchStatus") or
                          item.get("state")  or "Not started").strip().lower()
            if raw_st in FS_STATUS_SKIP:
                continue
            is_live = raw_st in FS_STATUS_LIVE or any(
                x in raw_st for x in ["half","period","quarter","set","play",
                                       "progress","ongoing","extra","penalt"]
            )
            is_done = raw_st in FS_STATUS_DONE or any(
                x in raw_st for x in ["finish","final","ended","complet","retired"]
            )
            status = "LIVE" if is_live else ("FINISHED" if is_done else "SCHEDULED")

            # ── Score ──────────────────────────────────────────────────────
            score_raw = item.get("score") or {}
            home_score = _toint(
                item.get("homeScore") or item.get("home_score") or
                (score_raw.get("current","").split(":")[0].strip()
                 if isinstance(score_raw, dict) and "current" in score_raw else None) or
                (score_raw.get("home") if isinstance(score_raw, dict) else None)
            )
            away_score = _toint(
                item.get("awayScore") or item.get("away_score") or
                (score_raw.get("current","").split(":")[-1].strip()
                 if isinstance(score_raw, dict) and "current" in score_raw else None) or
                (score_raw.get("away") if isinstance(score_raw, dict) else None)
            )

            # ── Start time ─────────────────────────────────────────────────
            start = None
            for key in ("startTimestamp","startTime","start_time","kickoff",
                        "date","scheduledTime","matchTime","datetime"):
                raw = item.get(key)
                if raw:
                    try:
                        if isinstance(raw, (int, float)):
                            ts = raw/1000 if raw > 1e10 else raw
                            start = datetime.utcfromtimestamp(ts)
                        else:
                            start = datetime.fromisoformat(
                                str(raw).replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass

            matches.append(Match(
                match_id   = mid,
                provider   = "FlashScore",
                league     = league,
                league_id  = l_id,
                home_team  = home,
                away_team  = away,
                home_score = home_score,
                away_score = away_score,
                status     = status,
                start_time = start,
                country    = country,
            ))
        return matches


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _toint(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# All sports supported by FlashScore provider
FLASHSCORE_SPORTS = set(FS_SPORT_MAP.keys())

# Sports with dedicated legacy providers (used as primary when FS unavailable)
LEGACY_SOCCER  = {"Soccer"}
LEGACY_US      = {"NBA", "NFL", "MLB", "NHL"}
LEGACY_MISC    = {"UFC", "Formula 1", "Tennis", "Cricket", "Golf"}


class EmpireDataRouter:
    def __init__(self):
        self.api_sports      = APISportsProvider()
        self.my_sports_feeds = MySportsFeedsProvider()
        self.the_sports_db   = TheSportsDBProvider()
        self.flashscore      = FlashScoreProvider()
        self.connection_log: List[Dict] = []
        self._log_initial_status()
        # Pre-warm all sports in background on startup — zero UI blocking
        self.flashscore.prefetch_all()

    def _log(self, provider: str, status: str, detail: str):
        self.connection_log.append({
            "TIME":     datetime.now().strftime("%H:%M:%S"),
            "PROVIDER": provider,
            "STATUS":   status,
            "DETAIL":   str(detail)[:80],
        })

    def _log_initial_status(self):
        checks = [
            ("FlashScore/Apify", bool(APIConfig.APIFY_API_TOKEN),   "30+ sports daily live"),
            ("API-SPORTS",       bool(APIConfig.API_SPORTS_KEY),     "Soccer live data"),
            ("MySportsFeeds",    bool(APIConfig.MYSPORTSFEEDS_KEY),  "NBA/NFL/MLB/NHL data"),
            ("TheSportsDB",      True,                                "UFC/F1/Tennis/Cricket/Golf"),
            ("TheOddsAPI",       bool(APIConfig.ODDS_API_KEY),        "Odds data"),
            ("Football-Data",    bool(APIConfig.FOOTBALL_DATA_KEY),   "Soccer backup"),
        ]
        for name, active, detail in checks:
            self._log(name, "READY" if active else "NOT CONFIGURED", detail)

    def get_connection_log_df(self) -> pd.DataFrame:
        if not self.connection_log:
            return pd.DataFrame()
        return pd.DataFrame(self.connection_log).tail(60)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "FlashScore (Apify)",
             "status": "🟢 ONLINE" if APIConfig.APIFY_API_TOKEN else "⚪ NOT CONFIGURED"},
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
        ]

    # ── Leagues  ──────────────────────────────────────────────────────────────
    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        """
        ALWAYS returns instantly from static fallback.
        If API-SPORTS key is live and sport is Soccer, enriches asynchronously
        and returns full API list on subsequent calls (already cached).
        """
        static = STATIC_LEAGUES.get(sport_type, [{"id": "ALL", "name": "All Events", "country": "World"}])

        # For Soccer with an active API key: try cache first, then return static
        if sport_type == "Soccer" and self.api_sports.ok:
            ck = self.api_sports._ck("apisports_leagues")
            cached = self.api_sports._get(ck, APIConfig.TTL_LEAGUES)
            if cached:
                self._log("API-SPORTS", "CACHE HIT", f"{len(cached)} soccer leagues")
                return cached
            # Return static immediately; warm cache in background thread
            def _warm():
                try:
                    leagues = self.api_sports.get_leagues()
                    if leagues:
                        self._log("API-SPORTS", "ENRICHED",
                                  f"{len(leagues)} soccer leagues cached")
                except Exception as e:
                    self._log("API-SPORTS", "ERROR", str(e))
            threading.Thread(target=_warm, daemon=True).start()

        return static

    # ── Live matches — FlashScore primary, legacy fallback ───────────────────
    def get_live_matches(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        try:
            # PRIMARY: FlashScore via Apify (covers all 30+ sports)
            if self.flashscore.ok and sport_type in FLASHSCORE_SPORTS:
                matches = self.flashscore.get_live_matches(sport_type)
                self._log("FlashScore", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} live {sport_type}")

            # FALLBACK / SUPPLEMENT: Legacy providers
            if not matches:
                if sport_type in LEGACY_SOCCER:
                    matches = self.api_sports.get_live_matches(league_id)
                    self._log("API-SPORTS", "FALLBACK",
                              f"{len(matches)} live soccer")
                elif sport_type in LEGACY_US:
                    matches = self.my_sports_feeds.get_live_matches(sport_type)
                    self._log("MySportsFeeds", "FALLBACK",
                              f"{len(matches)} live {sport_type}")
                elif sport_type in LEGACY_MISC:
                    matches = self.the_sports_db.get_live_matches(sport_type)
                    self._log("TheSportsDB", "FALLBACK",
                              f"{len(matches)} live {sport_type}")

        except Exception as e:
            self._log("ROUTER", "ERROR", f"live {sport_type}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()

    # ── Upcoming matches — FlashScore primary, legacy fallback ───────────────
    def get_upcoming_matches(self, sport_type: str) -> pd.DataFrame:
        matches = []
        try:
            # PRIMARY: FlashScore via Apify
            if self.flashscore.ok and sport_type in FLASHSCORE_SPORTS:
                matches = self.flashscore.get_upcoming_matches(sport_type)
                self._log("FlashScore", "SUCCESS" if matches else "EMPTY",
                          f"{len(matches)} upcoming {sport_type}")

            # FALLBACK
            if not matches:
                if sport_type in LEGACY_SOCCER:
                    matches = self.api_sports.get_upcoming_matches()
                    self._log("API-SPORTS", "FALLBACK",
                              f"{len(matches)} upcoming soccer")
                elif sport_type in LEGACY_US:
                    matches = self.my_sports_feeds.get_upcoming_matches(sport_type)
                    self._log("MySportsFeeds", "FALLBACK",
                              f"{len(matches)} upcoming {sport_type}")
                elif sport_type in LEGACY_MISC:
                    matches = self.the_sports_db.get_upcoming_matches(sport_type)
                    self._log("TheSportsDB", "FALLBACK",
                              f"{len(matches)} upcoming {sport_type}")

        except Exception as e:
            self._log("ROUTER", "ERROR", f"upcoming {sport_type}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD FACADE
# ═══════════════════════════════════════════════════════════════════════════════

class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self) -> bool:
        return bool(
            APIConfig.APIFY_API_TOKEN
            or APIConfig.API_SPORTS_KEY
            or APIConfig.MYSPORTSFEEDS_KEY
            or APIConfig.THESPORTSDB_KEY
        )

    def get_connection_log_df(self) -> pd.DataFrame:
        return self.router.get_connection_log_df()

    def get_all_leagues(self, sport_type: str) -> List[Dict]:
        return self.router.get_all_leagues(sport_type)

    def get_live_matches_df(self, sport_type: str, league_id: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(sport_type, league_id)

    def get_upcoming_matches_df(self, sport_type: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(sport_type)

    # Stubs
    def get_match_prediction(self, match_id: str): return None
    def get_match_details(self, match_id: str):    return {"found": False}
    def get_team_form(self, team_name: str, match_id: str): return None
    def get_head_to_head(self, home: str, away: str, match_id: str): return []
    def get_key_players(self, match_id: str):      return []
    def get_match_odds(self, match_id: str):       return {}
    def get_ai_reasoning(self, match_id: str):     return []


__all__ = ["APIConfig", "EmpireDashboardData"]
