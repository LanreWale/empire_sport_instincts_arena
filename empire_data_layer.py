"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer
COST-EFFECTIVE MULTI-PROVIDER STRATEGY (All FREE tiers):
  1. API-SPORTS (100/day free)      — Soccer live/fixtures (PRIMARY)
  2. Football-Data.org (10/min free) — Soccer backup
  3. TheSportsDB (FREE unlimited)    — UFC/F1/Tennis/Cricket/Golf
  4. MySportsFeeds (FREE tier)       — NBA/NFL/MLB/NHL
  5. Apify/FlashScore (PAID)         - DISABLED
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

    # PRIMARY FREE APIs
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
    
    # PAID API - DISABLED
    APIFY_API_TOKEN    = _e("APIFY_API_KEY")

    TTL_LIVE     = 30      # Cache live matches for 30 seconds
    TTL_UPCOMING = 600     # Cache upcoming matches for 10 minutes
    TTL_LEAGUES  = 86400   # Cache leagues for 24 hours
    TIMEOUT      = 12
    RETRIES      = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LISTS - COMPLETE WITH ALL COMPETITIONS
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Soccer": [
        # Major European Leagues
        {"id": "39",  "name": "Premier League",                "country": "England"},
        {"id": "40",  "name": "Championship",                  "country": "England"},
        {"id": "45",  "name": "FA Cup",                        "country": "England"},
        {"id": "48",  "name": "EFL Cup",                       "country": "England"},
        {"id": "140", "name": "La Liga",                       "country": "Spain"},
        {"id": "141", "name": "La Liga 2",                     "country": "Spain"},
        {"id": "143", "name": "Copa del Rey",                  "country": "Spain"},
        {"id": "135", "name": "Serie A",                       "country": "Italy"},
        {"id": "136", "name": "Serie B",                       "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                    "country": "Germany"},
        {"id": "79",  "name": "2. Bundesliga",                 "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                       "country": "France"},
        {"id": "62",  "name": "Ligue 2",                       "country": "France"},
        {"id": "88",  "name": "Eredivisie",                    "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",                 "country": "Portugal"},
        {"id": "144", "name": "Pro League",                    "country": "Belgium"},
        {"id": "197", "name": "Super Lig",                     "country": "Turkey"},
        {"id": "119", "name": "Superliga",                     "country": "Denmark"},
        {"id": "113", "name": "Allsvenskan",                   "country": "Sweden"},
        {"id": "103", "name": "Eliteserien",                   "country": "Norway"},
        {"id": "116", "name": "Ekstraklasa",                   "country": "Poland"},
        {"id": "179", "name": "Premiership",                   "country": "Scotland"},
        {"id": "207", "name": "Super League",                  "country": "Switzerland"},
        {"id": "172", "name": "Super League",                  "country": "Greece"},
        {"id": "235", "name": "Premier League",                "country": "Russia"},
        
        # UEFA Competitions
        {"id": "2",   "name": "UEFA Champions League",         "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",            "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League",        "country": "Europe"},
        {"id": "960", "name": "UEFA Nations League",           "country": "Europe"},
        {"id": "4",   "name": "Euro Championship",             "country": "Europe"},
        
        # International Competitions
        {"id": "1",   "name": "FIFA World Cup",                "country": "World"},
        {"id": "15",  "name": "FIFA Club World Cup",           "country": "World"},
        {"id": "5",   "name": "World Cup - Qualification",     "country": "World"},
        {"id": "10",  "name": "Friendlies International",      "country": "World"},
        {"id": "12",  "name": "Friendly International Women",  "country": "World"},
        {"id": "14",  "name": "World Club Friendlies",         "country": "World"},
        
        # African Competitions
        {"id": "29",  "name": "CAF Champions League",          "country": "Africa"},
        {"id": "30",  "name": "CAF Confederation Cup",         "country": "Africa"},
        {"id": "6",   "name": "Africa Cup of Nations",         "country": "Africa"},
        {"id": "233", "name": "NPFL",                          "country": "Nigeria"},
        {"id": "128", "name": "Ligue Professionnelle 1",       "country": "Algeria"},
        {"id": "169", "name": "Egyptian Premier League",       "country": "Egypt"},
        {"id": "168", "name": "Botola Pro",                    "country": "Morocco"},
        {"id": "360", "name": "Premier League",                "country": "South Africa"},
        {"id": "375", "name": "Premier League",                "country": "Ghana"},
        
        # Asian Competitions
        {"id": "17",  "name": "AFC Champions League",          "country": "Asia"},
        {"id": "283", "name": "Saudi Pro League",              "country": "Saudi Arabia"},
        {"id": "307", "name": "UAE Pro League",                "country": "UAE"},
        {"id": "98",  "name": "J-League",                      "country": "Japan"},
        {"id": "292", "name": "K League 1",                    "country": "South Korea"},
        {"id": "301", "name": "Indian Super League",           "country": "India"},
        {"id": "323", "name": "A-League",                      "country": "Australia"},
        {"id": "489", "name": "AFC Asian Cup",                 "country": "Asia"},
        
        # American Competitions
        {"id": "253", "name": "MLS",                           "country": "USA"},
        {"id": "262", "name": "Liga MX",                       "country": "Mexico"},
        {"id": "71",  "name": "Brasileirao Serie A",           "country": "Brazil"},
        {"id": "72",  "name": "Brasileirao Serie B",           "country": "Brazil"},
        {"id": "242", "name": "Primera Division",              "country": "Argentina"},
        {"id": "265", "name": "Primera Division",              "country": "Colombia"},
        {"id": "11",  "name": "Copa Libertadores",             "country": "S. America"},
        {"id": "13",  "name": "Copa Sudamericana",             "country": "S. America"},
        {"id": "9",   "name": "Copa America",                  "country": "S. America"},
        {"id": "558", "name": "CONCACAF Champions League",     "country": "N. America"},
        {"id": "559", "name": "CONCACAF Gold Cup",             "country": "N. America"},
        
        # Women's Competitions
        {"id": "573", "name": "Women's Super League",          "country": "England"},
        {"id": "582", "name": "NWSL",                          "country": "USA"},
        {"id": "583", "name": "Frauen-Bundesliga",             "country": "Germany"},
        {"id": "584", "name": "Division 1 Feminine",           "country": "France"},
        {"id": "585", "name": "Serie A Femminile",             "country": "Italy"},
        {"id": "586", "name": "Liga F",                        "country": "Spain"},
        {"id": "7",   "name": "FIFA Women's World Cup",        "country": "World"},
        {"id": "8",   "name": "Women's Euro Championship",     "country": "Europe"},
        {"id": "16",  "name": "Women's Olympic Tournament",    "country": "World"},
        {"id": "18",  "name": "Women's Friendly International","country": "World"},
    ],
    "NBA": [
        {"id": "NBA",        "name": "NBA",                           "country": "USA/Canada"},
        {"id": "NBA_PO",     "name": "NBA Playoffs",                  "country": "USA/Canada"},
        {"id": "NBA_F",      "name": "NBA Finals",                    "country": "USA/Canada"},
        {"id": "NBA_AS",     "name": "NBA All-Star Weekend",          "country": "USA"},
        {"id": "NBAGL",      "name": "NBA G League",                  "country": "USA"},
        {"id": "WNBA",       "name": "WNBA",                          "country": "USA"},
        {"id": "EUROLEAGUE", "name": "EuroLeague",                    "country": "Europe"},
        {"id": "EUROCUP",    "name": "EuroCup",                       "country": "Europe"},
        {"id": "BCL",        "name": "Basketball Champions League",   "country": "Europe"},
        {"id": "ACB",        "name": "Liga ACB",                      "country": "Spain"},
        {"id": "LNB",        "name": "LNB Pro A",                     "country": "France"},
        {"id": "BSL",        "name": "BSL Super League",              "country": "Turkey"},
        {"id": "BBL_DE",     "name": "Basketball Bundesliga",         "country": "Germany"},
        {"id": "LBA",        "name": "Lega Basket Serie A",           "country": "Italy"},
        {"id": "VTB",        "name": "VTB United League",             "country": "Russia/Europe"},
        {"id": "NBL_AU",     "name": "NBL",                           "country": "Australia"},
        {"id": "CBA",        "name": "CBA",                           "country": "China"},
        {"id": "KBASKET",    "name": "KBL",                           "country": "South Korea"},
        {"id": "BAL",        "name": "Basketball Africa League",      "country": "Africa"},
        {"id": "FIBA_WC",    "name": "FIBA World Cup",                "country": "World"},
        {"id": "FIBA_OLY",   "name": "Olympics — Basketball",         "country": "World"},
    ],
    "NFL": [
        {"id": "NFL",        "name": "NFL",                           "country": "USA"},
        {"id": "NFL_PRE",    "name": "NFL Preseason",                 "country": "USA"},
        {"id": "NFL_PO",     "name": "NFL Playoffs",                  "country": "USA"},
        {"id": "NFL_SB",     "name": "Super Bowl",                    "country": "USA"},
        {"id": "CFL",        "name": "CFL",                           "country": "Canada"},
        {"id": "USFL",       "name": "USFL",                          "country": "USA"},
        {"id": "XFL",        "name": "XFL",                           "country": "USA"},
        {"id": "NCAA_FBS",   "name": "NCAA FBS",                      "country": "USA"},
        {"id": "NCAA_CFP",   "name": "College Football Playoff",      "country": "USA"},
        {"id": "ELF",        "name": "European League of Football",   "country": "Europe"},
    ],
    "MLB": [
        {"id": "MLB",        "name": "MLB",                           "country": "USA/Canada"},
        {"id": "MLB_PO",     "name": "MLB Playoffs",                  "country": "USA/Canada"},
        {"id": "MLB_WS",     "name": "World Series",                  "country": "USA/Canada"},
        {"id": "AAA",        "name": "Triple-A (AAA)",                "country": "USA"},
        {"id": "NPB",        "name": "NPB Japan Baseball",            "country": "Japan"},
        {"id": "KBO",        "name": "KBO League",                    "country": "South Korea"},
        {"id": "LMB",        "name": "Mexican Baseball League",       "country": "Mexico"},
        {"id": "WBC",        "name": "World Baseball Classic",        "country": "World"},
        {"id": "CARIBBEAN",  "name": "Caribbean Series",              "country": "Caribbean"},
    ],
    "NHL": [
        {"id": "NHL",        "name": "NHL",                           "country": "USA/Canada"},
        {"id": "NHL_PO",     "name": "NHL Playoffs",                  "country": "USA/Canada"},
        {"id": "NHL_SC",     "name": "Stanley Cup Finals",            "country": "USA/Canada"},
        {"id": "AHL",        "name": "AHL",                           "country": "USA/Canada"},
        {"id": "IIHF_WC",    "name": "IIHF World Championship",       "country": "World"},
        {"id": "IIHF_OLY",   "name": "Olympics Ice Hockey",           "country": "World"},
        {"id": "IIHF_U20",   "name": "World Junior Championship",     "country": "World"},
        {"id": "SHL",        "name": "SHL",                           "country": "Sweden"},
        {"id": "Liiga",      "name": "Liiga",                         "country": "Finland"},
        {"id": "DEL",        "name": "DEL",                           "country": "Germany"},
        {"id": "KHL",        "name": "KHL",                           "country": "Russia/Europe"},
        {"id": "CHAMPIONS_HL","name": "Champions Hockey League",      "country": "Europe"},
        {"id": "OHL",        "name": "OHL",                           "country": "Canada"},
        {"id": "WHL",        "name": "WHL",                           "country": "Canada"},
        {"id": "PWHL",       "name": "PWHL Women's Hockey",           "country": "USA/Canada"},
    ],
    "UFC": [
        {"id": "UFC_ALL",    "name": "UFC — All Events",              "country": "World"},
        {"id": "UFC_PPV",    "name": "UFC PPV Events",                "country": "World"},
        {"id": "UFC_FN",     "name": "UFC Fight Night",               "country": "World"},
        {"id": "UFC_SW",     "name": "Strawweight",                   "country": "World"},
        {"id": "UFC_FLW",    "name": "Flyweight",                     "country": "World"},
        {"id": "UFC_BW",     "name": "Bantamweight",                  "country": "World"},
        {"id": "UFC_FW",     "name": "Featherweight",                 "country": "World"},
        {"id": "UFC_LW",     "name": "Lightweight",                   "country": "World"},
        {"id": "UFC_WW",     "name": "Welterweight",                  "country": "World"},
        {"id": "UFC_MW",     "name": "Middleweight",                  "country": "World"},
        {"id": "UFC_LHW",    "name": "Light Heavyweight",             "country": "World"},
        {"id": "UFC_HW",     "name": "Heavyweight",                   "country": "World"},
        {"id": "BELLATOR",   "name": "Bellator MMA",                  "country": "World"},
        {"id": "PFL",        "name": "PFL",                           "country": "World"},
        {"id": "ONE_FC",     "name": "ONE Championship",              "country": "Asia"},
        {"id": "BOXING_HW",  "name": "Boxing — Heavyweight",          "country": "World"},
        {"id": "BOXING_MW",  "name": "Boxing — Middleweight",         "country": "World"},
        {"id": "BOXING_WW",  "name": "Boxing — Welterweight",         "country": "World"},
        {"id": "BOXING_LW",  "name": "Boxing — Lightweight",          "country": "World"},
        {"id": "GLORY",      "name": "GLORY Kickboxing",              "country": "World"},
        {"id": "K1",         "name": "K-1 World GP",                  "country": "World"},
    ],
    "Formula 1": [
        {"id": "F1_ALL",   "name": "F1 — Full Season",           "country": "World"},
        {"id": "F1_AUS",   "name": "Australian GP",              "country": "Australia"},
        {"id": "F1_CHN",   "name": "Chinese GP",                 "country": "China"},
        {"id": "F1_JPN",   "name": "Japanese GP",                "country": "Japan"},
        {"id": "F1_BHR",   "name": "Bahrain GP",                 "country": "Bahrain"},
        {"id": "F1_SAU",   "name": "Saudi Arabian GP",           "country": "Saudi Arabia"},
        {"id": "F1_MIA",   "name": "Miami GP",                   "country": "USA"},
        {"id": "F1_MON",   "name": "Monaco GP",                  "country": "Monaco"},
        {"id": "F1_CAN",   "name": "Canadian GP",                "country": "Canada"},
        {"id": "F1_ESP",   "name": "Spanish GP",                 "country": "Spain"},
        {"id": "F1_AUT",   "name": "Austrian GP",                "country": "Austria"},
        {"id": "F1_GBR",   "name": "British GP",                 "country": "England"},
        {"id": "F1_HUN",   "name": "Hungarian GP",               "country": "Hungary"},
        {"id": "F1_BEL",   "name": "Belgian GP",                 "country": "Belgium"},
        {"id": "F1_NLD",   "name": "Dutch GP",                   "country": "Netherlands"},
        {"id": "F1_ITA",   "name": "Italian GP — Monza",         "country": "Italy"},
        {"id": "F1_AZE",   "name": "Azerbaijan GP",              "country": "Azerbaijan"},
        {"id": "F1_SGP",   "name": "Singapore GP",               "country": "Singapore"},
        {"id": "F1_USA",   "name": "US GP — Austin",             "country": "USA"},
        {"id": "F1_MEX",   "name": "Mexico City GP",             "country": "Mexico"},
        {"id": "F1_BRA",   "name": "São Paulo GP",               "country": "Brazil"},
        {"id": "F1_LVG",   "name": "Las Vegas GP",               "country": "USA"},
        {"id": "F1_QAT",   "name": "Qatar GP",                   "country": "Qatar"},
        {"id": "F1_UAE",   "name": "Abu Dhabi GP",               "country": "UAE"},
        {"id": "F2",       "name": "Formula 2",                  "country": "World"},
        {"id": "F3",       "name": "Formula 3",                  "country": "World"},
        {"id": "INDYCAR",  "name": "IndyCar Series",             "country": "USA"},
        {"id": "NASCAR_C", "name": "NASCAR Cup Series",          "country": "USA"},
        {"id": "WEC",      "name": "WEC World Endurance",        "country": "World"},
        {"id": "MOTO_GP",  "name": "MotoGP",                     "country": "World"},
        {"id": "FERF",     "name": "Formula E",                  "country": "World"},
    ],
    "Tennis": [
        {"id": "ATP_ALL",    "name": "ATP Tour — All Events",     "country": "World"},
        {"id": "WTA_ALL",    "name": "WTA Tour — All Events",     "country": "World"},
        {"id": "AUS_OPEN",   "name": "Australian Open",           "country": "Australia"},
        {"id": "FRENCH_OPEN","name": "Roland Garros",             "country": "France"},
        {"id": "WIMBLEDON",  "name": "Wimbledon",                 "country": "England"},
        {"id": "US_OPEN",    "name": "US Open",                   "country": "USA"},
        {"id": "M_INDIAN",   "name": "Indian Wells Masters",      "country": "USA"},
        {"id": "M_MIAMI",    "name": "Miami Open",                "country": "USA"},
        {"id": "M_MADRID",   "name": "Madrid Open",               "country": "Spain"},
        {"id": "M_ROME",     "name": "Italian Open",              "country": "Italy"},
        {"id": "M_CANADA",   "name": "Canadian Open",             "country": "Canada"},
        {"id": "M_CINCI",    "name": "Cincinnati Masters",        "country": "USA"},
        {"id": "M_SHANG",    "name": "Shanghai Masters",          "country": "China"},
        {"id": "M_PARIS",    "name": "Paris Masters",             "country": "France"},
        {"id": "ATP_FINALS", "name": "ATP Finals",                "country": "Italy"},
        {"id": "WTA_FINALS", "name": "WTA Finals",                "country": "Saudi Arabia"},
        {"id": "DAVIS_CUP",  "name": "Davis Cup Finals",          "country": "World"},
        {"id": "BJK_CUP",    "name": "Billie Jean King Cup",      "country": "World"},
        {"id": "LAVER_CUP",  "name": "Laver Cup",                 "country": "World"},
        {"id": "ATP_CHALL",  "name": "ATP Challenger Tour",       "country": "World"},
        {"id": "ITF_MEN",    "name": "ITF Men's Circuit",         "country": "World"},
        {"id": "ITF_WOM",    "name": "ITF Women's Circuit",       "country": "World"},
        {"id": "OLYMPICS_T", "name": "Olympics Tennis",           "country": "World"},
        {"id": "UNITED_CUP", "name": "United Cup",                "country": "World"},
    ],
    "Cricket": [
        {"id": "TEST",       "name": "Test Matches",              "country": "World"},
        {"id": "ODI",        "name": "ODI Internationals",        "country": "World"},
        {"id": "T20I",       "name": "T20 Internationals",        "country": "World"},
        {"id": "ICC_WC",     "name": "ICC Men's World Cup",       "country": "World"},
        {"id": "ICC_T20WC",  "name": "ICC T20 World Cup",         "country": "World"},
        {"id": "ICC_CT",     "name": "ICC Champions Trophy",      "country": "World"},
        {"id": "ICC_WTC",    "name": "World Test Championship",   "country": "World"},
        {"id": "IPL",        "name": "IPL",                       "country": "India"},
        {"id": "BBL",        "name": "Big Bash League",           "country": "Australia"},
        {"id": "PSL",        "name": "Pakistan Super League",     "country": "Pakistan"},
        {"id": "CPL",        "name": "Caribbean Premier League",  "country": "Caribbean"},
        {"id": "SA20",       "name": "SA20",                      "country": "South Africa"},
        {"id": "ILT20",      "name": "ILT20",                     "country": "UAE"},
        {"id": "MLC",        "name": "Major League Cricket",      "country": "USA"},
        {"id": "T20_BLAST",  "name": "Vitality T20 Blast",        "country": "England"},
        {"id": "THE_100",    "name": "The Hundred",               "country": "England"},
        {"id": "ASHES",      "name": "The Ashes",                 "country": "World"},
        {"id": "COUNTY",     "name": "County Championship",       "country": "England"},
        {"id": "RANJI",      "name": "Ranji Trophy",              "country": "India"},
        {"id": "SHEFFIELD",  "name": "Sheffield Shield",          "country": "Australia"},
        {"id": "WBBL",       "name": "Women's Big Bash League",   "country": "Australia"},
        {"id": "THE_HUNDRED_W", "name": "The Hundred Women",      "country": "England"},
    ],
    "Golf": [
        {"id": "PGA_ALL",    "name": "PGA Tour — All Events",     "country": "USA"},
        {"id": "DP_ALL",     "name": "DP World Tour — All Events","country": "Europe"},
        {"id": "LIV_ALL",    "name": "LIV Golf",                  "country": "World"},
        {"id": "MASTERS",    "name": "The Masters",               "country": "USA"},
        {"id": "PGA_CHAMP",  "name": "PGA Championship",          "country": "USA"},
        {"id": "US_OPEN_G",  "name": "US Open",                   "country": "USA"},
        {"id": "THE_OPEN",   "name": "The Open Championship",     "country": "UK"},
        {"id": "PLAYERS",    "name": "The Players Championship",  "country": "USA"},
        {"id": "RYDER_CUP",  "name": "Ryder Cup",                 "country": "World"},
        {"id": "PRES_CUP",   "name": "Presidents Cup",            "country": "World"},
        {"id": "KORN_FERRY", "name": "Korn Ferry Tour",           "country": "USA"},
        {"id": "LPGA_ALL",   "name": "LPGA Tour",                 "country": "USA"},
        {"id": "ASIAN_TOUR", "name": "Asian Tour",                "country": "Asia"},
        {"id": "SENIOR_PGA", "name": "PGA Tour Champions",        "country": "USA"},
        {"id": "SOLHEIM_CUP","name": "Solheim Cup",               "country": "World"},
        {"id": "OLYMPICS_G", "name": "Olympics Golf",             "country": "World"},
    ],
    "Volleyball": [
        {"id": "VB_ALL",     "name": "Volleyball — All Events",   "country": "World"},
        {"id": "FIVB_WL",    "name": "FIVB Nations League",       "country": "World"},
        {"id": "FIVB_WC",    "name": "FIVB World Championship",   "country": "World"},
        {"id": "FIVB_OLY",   "name": "Olympics Volleyball",       "country": "World"},
        {"id": "CEV_CL",     "name": "CEV Champions League",      "country": "Europe"},
        {"id": "SUPERLIGA_IT","name": "SuperLega Italy",          "country": "Italy"},
        {"id": "PLUS_PL",    "name": "PlusLiga Poland",           "country": "Poland"},
        {"id": "SUPERLIG_VB","name": "Efeler Ligi Turkey",        "country": "Turkey"},
        {"id": "NBV_BR",     "name": "Superliga Brazil",          "country": "Brazil"},
        {"id": "KOVO",       "name": "V-League Korea",            "country": "South Korea"},
        {"id": "AVP",        "name": "AVP Beach Volleyball",      "country": "USA"},
        {"id": "BVL_BR",     "name": "Beach Volleyball World Tour","country": "World"},
    ],
    "Handball": [
        {"id": "HB_ALL",     "name": "Handball — All Events",     "country": "World"},
        {"id": "EHF_CL",     "name": "EHF Champions League",      "country": "Europe"},
        {"id": "EHF_EL",     "name": "EHF European League",       "country": "Europe"},
        {"id": "IHF_WC",     "name": "IHF World Championship",    "country": "World"},
        {"id": "EHF_EURO",   "name": "EHF Euro Championship",     "country": "Europe"},
        {"id": "BUNDES_HB",  "name": "Handball Bundesliga",       "country": "Germany"},
        {"id": "LNH",        "name": "Starligue France",          "country": "France"},
        {"id": "LIGA_ASOBAL","name": "Liga ASOBAL Spain",         "country": "Spain"},
        {"id": "EHF_W_CL",   "name": "EHF Women's Champions League","country": "Europe"},
        {"id": "IHF_W_WC",   "name": "IHF Women's World Championship","country": "World"},
        {"id": "HB_OLY",     "name": "Olympics Handball",         "country": "World"},
    ],
    "Rugby": [
        {"id": "RU_ALL",     "name": "Rugby Union — All Events",  "country": "World"},
        {"id": "RWC",        "name": "Rugby World Cup",           "country": "World"},
        {"id": "SIX_NATIONS","name": "Six Nations Championship",  "country": "Europe"},
        {"id": "THE_RUC",    "name": "The Rugby Championship",    "country": "S. Hemisphere"},
        {"id": "URC",        "name": "United Rugby Championship", "country": "Europe/Africa"},
        {"id": "PREMIERSHIP","name": "Gallagher Premiership",     "country": "England"},
        {"id": "TOP_14",     "name": "Top 14",                    "country": "France"},
        {"id": "SUPER_RUGBY","name": "Super Rugby Pacific",       "country": "Oceania"},
        {"id": "HSBC_SEVENS","name": "World Rugby Sevens Series", "country": "World"},
        {"id": "NRL",        "name": "NRL Rugby League",          "country": "Australia"},
        {"id": "SL_RL",      "name": "Super League Rugby League", "country": "UK"},
        {"id": "RUGBY_OLY",  "name": "Olympics Rugby Sevens",     "country": "World"},
    ],
    "Darts": [
        {"id": "DARTS_ALL",  "name": "Darts — All Events",        "country": "World"},
        {"id": "PDC_WC",     "name": "PDC World Championship",    "country": "UK"},
        {"id": "PDC_PL",     "name": "PDC Premier League",        "country": "UK/Europe"},
        {"id": "PDC_WM",     "name": "World Matchplay",           "country": "UK"},
        {"id": "PDC_WGP",    "name": "World Grand Prix",          "country": "Ireland"},
        {"id": "PDC_GC",     "name": "Grand Slam of Darts",       "country": "UK"},
        {"id": "PDC_EC",     "name": "European Championship",     "country": "Europe"},
        {"id": "PDC_UK_OPEN","name": "UK Open",                   "country": "UK"},
        {"id": "PDC_MASTERS","name": "Masters",                   "country": "UK"},
        {"id": "PDC_WC_QL",  "name": "World Cup of Darts",        "country": "Germany"},
        {"id": "WDF_WC",     "name": "WDF World Championship",    "country": "World"},
        {"id": "PDC_EURO",   "name": "European Tour",             "country": "Europe"},
    ],
    "Snooker": [
        {"id": "SNK_ALL",    "name": "Snooker — All Events",      "country": "World"},
        {"id": "SNK_WC",     "name": "World Championship",        "country": "UK"},
        {"id": "SNK_MASTERS","name": "Masters",                   "country": "UK"},
        {"id": "SNK_UK",     "name": "UK Championship",           "country": "UK"},
        {"id": "SNK_TOUR",   "name": "Tour Championship",         "country": "UK"},
        {"id": "SNK_PLAYERS","name": "Players Championship",      "country": "UK"},
        {"id": "SNK_CHINA",  "name": "Shanghai Masters",          "country": "China"},
        {"id": "SNK_WELSH",  "name": "Welsh Open",                "country": "Wales"},
        {"id": "SNK_GERMAN", "name": "German Masters",            "country": "Germany"},
        {"id": "SNK_SCOTTISH","name": "Scottish Open",            "country": "Scotland"},
        {"id": "SNK_ENGLISH","name": "English Open",              "country": "England"},
        {"id": "SNK_CHAMPION","name": "Champion of Champions",    "country": "UK"},
    ],
    "Table Tennis": [
        {"id": "TT_ALL",     "name": "Table Tennis — All Events", "country": "World"},
        {"id": "WTT_CHAMP",  "name": "WTT Champions",             "country": "World"},
        {"id": "WTT_STAR",   "name": "WTT Star Contender",        "country": "World"},
        {"id": "ITTF_WC",    "name": "ITTF World Championship",   "country": "World"},
        {"id": "TT_OLY",     "name": "Olympics Table Tennis",     "country": "World"},
        {"id": "TT_EURO_CH", "name": "European Championship",     "country": "Europe"},
        {"id": "TT_BL",      "name": "Bundesliga TT",             "country": "Germany"},
        {"id": "TT_CTTS",    "name": "China Table Tennis Super",  "country": "China"},
        {"id": "TT_JAPAN",   "name": "Japan T-League",            "country": "Japan"},
    ],
    "Esports": [
        {"id": "ES_ALL",     "name": "Esports — All Events",      "country": "World"},
        {"id": "LOL_WC",     "name": "LoL World Championship",    "country": "World"},
        {"id": "LOL_LCK",    "name": "LCK Korea",                 "country": "South Korea"},
        {"id": "LOL_LPL",    "name": "LPL China",                 "country": "China"},
        {"id": "LOL_LEC",    "name": "LEC Europe",                "country": "Europe"},
        {"id": "LOL_LCS",    "name": "LCS North America",         "country": "USA"},
        {"id": "DOTA_TI",    "name": "Dota 2 — The International","country": "World"},
        {"id": "DOTA_DPC",   "name": "Dota Pro Circuit",          "country": "World"},
        {"id": "CS_MAJOR",   "name": "CS2 Major Championship",    "country": "World"},
        {"id": "CS_ESL",     "name": "ESL Pro League CS2",        "country": "World"},
        {"id": "VALORANT_WC","name": "Valorant Champions",        "country": "World"},
        {"id": "VALORANT_VCT","name": "VCT International League", "country": "World"},
        {"id": "ROCKET_RLCS","name": "Rocket League Championship","country": "World"},
        {"id": "COD_CDL",    "name": "Call of Duty League",       "country": "World"},
        {"id": "OWL",        "name": "Overwatch League",          "country": "World"},
        {"id": "FORTNITE_WC","name": "Fortnite World Cup",        "country": "World"},
        {"id": "APEX_ALGS",  "name": "Apex Legends Global Series","country": "World"},
        {"id": "FIFA_FC",    "name": "FIFAe World Cup",           "country": "World"},
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
        return True

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
# EMPIRE DATA ROUTER — Prioritizes FREE APIs
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDataRouter:
    def __init__(self):
        # FREE API Providers
        self.api_sports = APISportsProvider()      # Soccer primary (100/day)
        self.football_data = FootballDataProvider() # Soccer backup (10/min)
        self.tsdb = TheSportsDBProvider()           # Unlimited free
        self.msf = MySportsFeedsProvider()          # US Sports free tier
        self.apify = None  # Disabled
        
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
            ("✅ API-SPORTS (FREE)", bool(APIConfig.API_SPORTS_KEY), "100 req/day - Soccer Primary"),
            ("✅ Football-Data (FREE)", True, "10 req/min - Soccer Backup"),
            ("✅ TheSportsDB (FREE)", True, "Unlimited - UFC/F1/Tennis/Cricket/Golf"),
            ("✅ MySportsFeeds (FREE)", bool(APIConfig.MSF_KEY), "US Sports"),
            ("❌ Apify (PAID/DISABLED)", False, "Monthly limit exceeded - Using free APIs"),
        ]
        for n, ok, d in items:
            self._log(n, "READY" if ok else "ACTIVE" if "FREE" in n else "DISABLED", d)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name": "API-SPORTS (FREE - 100/day)", "status": "🟢 ONLINE" if APIConfig.API_SPORTS_KEY else "⚠️ Add API_SPORTS_KEY"},
            {"name": "Football-Data (FREE - 10/min)", "status": "🟢 ONLINE"},
            {"name": "TheSportsDB (FREE - Unlimited)", "status": "🟢 ONLINE"},
            {"name": "MySportsFeeds (FREE)", "status": "🟢 ONLINE" if APIConfig.MSF_KEY else "⚪ Optional"},
            {"name": "Apify (PAID)", "status": "🔴 DISABLED - Using FREE APIs"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-60:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        """Returns complete static leagues instantly - ZERO API calls"""
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
            elif sport in ["UFC", "Formula 1", "Tennis", "Cricket", "Golf", "Volleyball", "Rugby", "Handball", "Darts", "Snooker", "Table Tennis", "Esports"]:
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
