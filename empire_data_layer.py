"""
EMPIRE SPORT INSTINCTS ARENA — Data Layer
Unified live sports data with multi-provider failover.
Providers (priority order):
  1. FlashScore via Apify     — 30+ sports (requires APIFY_API_KEY)
  2. API-Sports               — Soccer live/fixtures (requires API_SPORTS_KEY)
  3. MySportsFeeds            — NBA/NFL/MLB/NHL (requires MYSPORTSFEEDS_KEY)
  4. TheSportsDB              — UFC/F1/Tennis/Cricket/Golf (free key)
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

    APIFY_API_TOKEN    = _e("APIFY_API_KEY")
    APIFY_BASE        = "https://api.apify.com/v2/acts"

    API_SPORTS_KEY    = _e("API_SPORTS_KEY")
    API_SPORTS_URL    = "https://v3.football.api-sports.io"

    MSF_KEY           = _e("MYSPORTSFEEDS_KEY")
    MSF_PASS          = _e("MYSPORTSFEEDS_PASSWORD")
    MSF_URL           = "https://api.mysportsfeeds.com/v2.1/pull"

    FOOTBALL_DATA_KEY = _e("FOOTBALL_DATA_KEY")
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

    TSDB_KEY          = _e("TheSportDB_API_key", "3")
    TSDB_URL          = "https://www.thesportsdb.com/api/v1/json"

    TTL_LIVE     = 30
    TTL_UPCOMING = 600
    TTL_LEAGUES  = 86400
    TIMEOUT      = 12
    RETRIES      = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC LEAGUE LISTS — always instant, never empty
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_LEAGUES: Dict[str, List[Dict]] = {
    "Soccer": [
        {"id": "39",  "name": "Premier League",            "country": "England"},
        {"id": "40",  "name": "Championship",              "country": "England"},
        {"id": "45",  "name": "FA Cup",                    "country": "England"},
        {"id": "48",  "name": "EFL Cup",                   "country": "England"},
        {"id": "140", "name": "La Liga",                   "country": "Spain"},
        {"id": "141", "name": "La Liga 2",                 "country": "Spain"},
        {"id": "143", "name": "Copa del Rey",              "country": "Spain"},
        {"id": "135", "name": "Serie A",                   "country": "Italy"},
        {"id": "136", "name": "Serie B",                   "country": "Italy"},
        {"id": "78",  "name": "Bundesliga",                "country": "Germany"},
        {"id": "79",  "name": "2. Bundesliga",             "country": "Germany"},
        {"id": "61",  "name": "Ligue 1",                   "country": "France"},
        {"id": "62",  "name": "Ligue 2",                   "country": "France"},
        {"id": "88",  "name": "Eredivisie",                "country": "Netherlands"},
        {"id": "94",  "name": "Primeira Liga",             "country": "Portugal"},
        {"id": "144", "name": "Pro League",                "country": "Belgium"},
        {"id": "197", "name": "Super Lig",                 "country": "Turkey"},
        {"id": "119", "name": "Superliga",                 "country": "Denmark"},
        {"id": "113", "name": "Allsvenskan",               "country": "Sweden"},
        {"id": "103", "name": "Eliteserien",               "country": "Norway"},
        {"id": "116", "name": "Ekstraklasa",               "country": "Poland"},
        {"id": "179", "name": "Premiership",               "country": "Scotland"},
        {"id": "207", "name": "Super League",              "country": "Switzerland"},
        {"id": "172", "name": "Super League",              "country": "Greece"},
        {"id": "235", "name": "Premier League",            "country": "Russia"},
        {"id": "2",   "name": "UEFA Champions League",     "country": "Europe"},
        {"id": "3",   "name": "UEFA Europa League",        "country": "Europe"},
        {"id": "848", "name": "UEFA Conference League",    "country": "Europe"},
        {"id": "960", "name": "UEFA Nations League",       "country": "Europe"},
        {"id": "4",   "name": "Euro Championship",         "country": "Europe"},
        {"id": "253", "name": "MLS",                       "country": "USA"},
        {"id": "262", "name": "Liga MX",                   "country": "Mexico"},
        {"id": "71",  "name": "Brasileirao Serie A",       "country": "Brazil"},
        {"id": "72",  "name": "Brasileirao Serie B",       "country": "Brazil"},
        {"id": "242", "name": "Primera Division",          "country": "Argentina"},
        {"id": "265", "name": "Primera Division",          "country": "Colombia"},
        {"id": "11",  "name": "Copa Libertadores",         "country": "S. America"},
        {"id": "13",  "name": "Copa Sudamericana",         "country": "S. America"},
        {"id": "9",   "name": "Copa America",              "country": "S. America"},
        {"id": "29",  "name": "CAF Champions League",      "country": "Africa"},
        {"id": "6",   "name": "Africa Cup of Nations",     "country": "Africa"},
        {"id": "233", "name": "NPFL",                      "country": "Nigeria"},
        {"id": "128", "name": "Ligue Professionnelle 1",   "country": "Algeria"},
        {"id": "169", "name": "Egyptian Premier League",   "country": "Egypt"},
        {"id": "168", "name": "Botola Pro",                "country": "Morocco"},
        {"id": "360", "name": "Premier League",            "country": "South Africa"},
        {"id": "375", "name": "Premier League",            "country": "Ghana"},
        {"id": "283", "name": "Saudi Pro League",          "country": "Saudi Arabia"},
        {"id": "307", "name": "UAE Pro League",            "country": "UAE"},
        {"id": "98",  "name": "J-League",                  "country": "Japan"},
        {"id": "292", "name": "K League 1",                "country": "South Korea"},
        {"id": "301", "name": "Indian Super League",       "country": "India"},
        {"id": "323", "name": "A-League",                  "country": "Australia"},
        {"id": "17",  "name": "AFC Champions League",      "country": "Asia"},
        {"id": "573", "name": "Women's Super League",      "country": "England"},
        {"id": "582", "name": "NWSL",                      "country": "USA"},
        {"id": "1",   "name": "FIFA World Cup",            "country": "World"},
        {"id": "15",  "name": "FIFA Club World Cup",       "country": "World"},
        {"id": "10",  "name": "Friendlies International",  "country": "World"},
    ],
    "NBA": [
        {"id": "NBA",        "name": "NBA",                           "country": "USA/Canada"},
        {"id": "NBA_PO",     "name": "NBA Playoffs",                  "country": "USA/Canada"},
        {"id": "NBA_F",      "name": "NBA Finals",                    "country": "USA/Canada"},
        {"id": "NBA_AS",     "name": "NBA All-Star Weekend",          "country": "USA"},
        {"id": "NBAGL",      "name": "NBA G League",                  "country": "USA"},
        {"id": "WNBA",       "name": "WNBA",                         "country": "USA"},
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
        {"id": "USFL",       "name": "USFL",                         "country": "USA"},
        {"id": "XFL",        "name": "XFL",                          "country": "USA"},
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
        {"id": "AHL",        "name": "AHL",                          "country": "USA/Canada"},
        {"id": "IIHF_WC",    "name": "IIHF World Championship",      "country": "World"},
        {"id": "IIHF_OLY",   "name": "Olympics Ice Hockey",           "country": "World"},
        {"id": "IIHF_U20",   "name": "World Junior Championship",     "country": "World"},
        {"id": "SHL",        "name": "SHL",                          "country": "Sweden"},
        {"id": "Liiga",      "name": "Liiga",                        "country": "Finland"},
        {"id": "DEL",        "name": "DEL",                          "country": "Germany"},
        {"id": "KHL",        "name": "KHL",                          "country": "Russia/Europe"},
        {"id": "CHAMPIONS_HL","name": "Champions Hockey League",     "country": "Europe"},
        {"id": "OHL",        "name": "OHL",                          "country": "Canada"},
        {"id": "WHL",        "name": "WHL",                          "country": "Canada"},
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
        {"id": "PFL",        "name": "PFL",                          "country": "World"},
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
        {"id": "M_MADRID",   "name": "Madrid Open",              "country": "Spain"},
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
        {"id": "RYDER_CUP",  "name": "Ryder Cup",                "country": "World"},
        {"id": "PRES_CUP",   "name": "Presidents Cup",           "country": "World"},
        {"id": "KORN_FERRY", "name": "Korn Ferry Tour",          "country": "USA"},
        {"id": "LPGA_ALL",   "name": "LPGA Tour",                 "country": "USA"},
        {"id": "ASIAN_TOUR", "name": "Asian Tour",               "country": "Asia"},
        {"id": "SENIOR_PGA", "name": "PGA Tour Champions",       "country": "USA"},
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
        {"id": "WTT_CHAMP",  "name": "WTT Champions",            "country": "World"},
        {"id": "WTT_STAR",   "name": "WTT Star Contender",       "country": "World"},
        {"id": "ITTF_WC",    "name": "ITTF World Championship",  "country": "World"},
        {"id": "TT_OLY",     "name": "Olympics Table Tennis",    "country": "World"},
        {"id": "TT_EURO_CH", "name": "European Championship",    "country": "Europe"},
        {"id": "TT_BL",      "name": "Bundesliga TT",            "country": "Germany"},
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
    ],
    "Esports": [
        {"id": "ES_ALL",     "name": "Esports — All Events",       "country": "World"},
        {"id": "LOL_WC",     "name": "LoL World Championship",     "country": "World"},
        {"id": "LOL_LCK",    "name": "LCK Korea",                  "country": "South Korea"},
        {"id": "LOL_LPL",    "name": "LPL China",                  "country": "China"},
        {"id": "LOL_LEC",    "name": "LEC Europe",                 "country": "Europe"},
        {"id": "DOTA_TI",    "name": "Dota 2 — The International", "country": "World"},
        {"id": "CS_MAJOR",   "name": "CS2 Major Championship",     "country": "World"},
        {"id": "CS_ESL",     "name": "ESL Pro League CS2",         "country": "World"},
        {"id": "VALORANT_WC","name": "Valorant Champions",         "country": "World"},
        {"id": "ROCKET_RLCS","name": "Rocket League Championship", "country": "World"},
        {"id": "COD_CDL",    "name": "Call of Duty League",        "country": "World"},
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
                    time.sleep((attempt + 1) * 2); continue
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
# API-SPORTS PROVIDER — Soccer
# ═══════════════════════════════════════════════════════════════════════════════
class APISportsProvider(DataProvider):
    def __init__(self):
        super().__init__("API-SPORTS")
        self.h = {"x-apisports-key": APIConfig.API_SPORTS_KEY} if APIConfig.API_SPORTS_KEY else {}

    @property
    def ok(self): return bool(APIConfig.API_SPORTS_KEY)

    def get_leagues(self) -> List[Dict]:
        if not self.ok: return []
        ck = self._ck("leagues")
        c  = self._get(ck, APIConfig.TTL_LEAGUES)
        if c: return c
        d = self._req(f"{APIConfig.API_SPORTS_URL}/leagues", self.h)
        if not d: return []
        out = [{"id": str(i.get("league",{}).get("id","")),
                "name": i.get("league",{}).get("name","?"),
                "country": i.get("country",{}).get("name","")}
               for i in d.get("response",[])]
        self._set(ck, out)
        return out

    def get_live(self, league_id: str = None) -> List[Match]:
        if not self.ok: return []
        ck = self._ck("live", league_id)
        c  = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None: return c
        p = {"live": "all"}
        if league_id and league_id not in ("ALL",""):
            p["league"] = league_id
        d = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.h, p)
        out = self._parse(d) if d else []
        self._set(ck, out); return out

    def get_upcoming(self, days: int = 3) -> List[Match]:
        if not self.ok: return []
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now()+timedelta(days=days)).strftime("%Y-%m-%d")
        ck = self._ck("upcoming", today)
        c  = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None: return c
        d = self._req(f"{APIConfig.API_SPORTS_URL}/fixtures", self.h,
                      {"from": today, "to": future})
        out = self._parse(d) if d else []
        self._set(ck, out); return out

    def _parse(self, data: Dict) -> List[Match]:
        out = []
        for fx in data.get("response", []):
            f  = fx.get("fixture", {})
            lg = fx.get("league", {})
            tm = fx.get("teams", {})
            gl = fx.get("goals", {})
            st = f.get("status", {})
            start = None
            if f.get("date"):
                try: start = datetime.fromisoformat(f["date"].replace("Z","+00:00"))
                except: pass
            out.append(Match(
                match_id  = str(f.get("id","")),
                provider  = "API-SPORTS",
                league    = lg.get("name","?"),
                league_id = str(lg.get("id","")),
                home_team = tm.get("home",{}).get("name","Home"),
                away_team = tm.get("away",{}).get("name","Away"),
                home_score= gl.get("home"),
                away_score= gl.get("away"),
                status    = st.get("short","NS"),
                minute    = st.get("elapsed"),
                start_time= start,
                country   = lg.get("country"),
            ))
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTBALL-DATA.ORG PROVIDER — Soccer backup (10 calls/min free)
# ═══════════════════════════════════════════════════════════════════════════════
class FootballDataProvider(DataProvider):
    def __init__(self):
        super().__init__("Football-Data")
        self.h = {"X-Auth-Token": APIConfig.FOOTBALL_DATA_KEY} if APIConfig.FOOTBALL_DATA_KEY else {}

    @property
    def ok(self): return bool(APIConfig.FOOTBALL_DATA_KEY)

    def get_today(self) -> List[Match]:
        if not self.ok: return []
        today = datetime.now().strftime("%Y-%m-%d")
        ck = self._ck("today", today)
        c  = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None: return c
        d = self._req(f"{APIConfig.FOOTBALL_DATA_URL}/matches", self.h,
                      {"dateFrom": today, "dateTo": today})
        if not d: return []
        out = []
        for m in d.get("matches", []):
            comp  = m.get("competition", {})
            home  = m.get("homeTeam", {})
            away  = m.get("awayTeam", {})
            score = m.get("score", {}).get("fullTime", {})
            start = None
            if m.get("utcDate"):
                try: start = datetime.fromisoformat(m["utcDate"].replace("Z","+00:00"))
                except: pass
            raw_st = m.get("status","SCHEDULED").upper()
            if   "IN_PLAY" in raw_st or "PAUSED" in raw_st: st = "LIVE"
            elif "FINISHED" in raw_st:                       st = "FINISHED"
            else:                                            st = "SCHEDULED"
            out.append(Match(
                match_id  = str(m.get("id","")),
                provider  = "Football-Data",
                league    = comp.get("name","?"),
                league_id = str(comp.get("id","")),
                home_team = home.get("name","Home"),
                away_team = away.get("name","Away"),
                home_score= _toint(score.get("home")),
                away_score= _toint(score.get("away")),
                status    = st,
                start_time= start,
                country   = comp.get("area",{}).get("name",""),
            ))
        self._set(ck, out)
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# MYSPORTSFEEDS PROVIDER — NBA/NFL/MLB/NHL
# ═══════════════════════════════════════════════════════════════════════════════
class MySportsFeedsProvider(DataProvider):
    CODES = {"NBA":"nba","NFL":"nfl","MLB":"mlb","NHL":"nhl"}

    def __init__(self):
        super().__init__("MySportsFeeds")
        if APIConfig.MSF_KEY and APIConfig.MSF_PASS:
            creds = base64.b64encode(f"{APIConfig.MSF_KEY}:{APIConfig.MSF_PASS}".encode()).decode()
            self.h = {"Authorization": f"Basic {creds}"}
        else:
            self.h = {}

    @property
    def ok(self): return bool(self.h)

    def _season(self, sport: str) -> str:
        now = datetime.now()
        s   = sport.upper()
        if s in ("NBA","NHL"):
            return f"{now.year}-{now.year+1}" if now.month >= 10 else f"{now.year-1}-{now.year}"
        if s == "NFL":
            return str(now.year) if now.month >= 8 else str(now.year-1)
        return str(now.year)

    def get_today(self, sport: str) -> List[Match]:
        if not self.ok: return []
        code   = self.CODES.get(sport.upper(),"nba")
        season = self._season(sport)
        today  = datetime.now().strftime("%Y%m%d")
        ck = self._ck("today", code, today)
        c  = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None: return c
        d = self._req(f"{APIConfig.MSF_URL}/{code}/{season}/date/{today}/games.json",
                      self.h)
        if not d:
            d = self._req(f"{APIConfig.MSF_URL}/{code}/{season}/games.json",
                          self.h, {"date": today})
        out = self._parse(d, sport) if d else []
        self._set(ck, out); return out

    def get_upcoming(self, sport: str, days: int = 7) -> List[Match]:
        if not self.ok: return []
        code   = self.CODES.get(sport.upper(),"nba")
        season = self._season(sport)
        today  = datetime.now().strftime("%Y%m%d")
        future = (datetime.now()+timedelta(days=days)).strftime("%Y%m%d")
        ck = self._ck("upcoming", code, today)
        c  = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None: return c
        d = self._req(f"{APIConfig.MSF_URL}/{code}/{season}/games.json",
                      self.h, {"fordate": today, "todate": future})
        out = self._parse(d, sport, upcoming=True) if d else []
        self._set(ck, out); return out

    def _parse(self, data: Dict, sport: str, upcoming: bool = False) -> List[Match]:
        out = []
        for game in data.get("games",[]):
            sc   = game.get("schedule", game)
            raw  = sc.get("playedStatus", sc.get("status","UNPLAYED")).upper()
            live = raw in ("IN_PROGRESS","LIVE","1ST","2ND","3RD","4TH","OT")
            done = raw in ("COMPLETED","FINAL","COMPLETED_PENDING_REVIEW")
            if upcoming and (live or done): continue
            def _name(t):
                if isinstance(t, dict): return f"{t.get('city','')} {t.get('name','')}".strip()
                return str(t)
            home = _name(sc.get("homeTeam",{})) or "TBD"
            away = _name(sc.get("awayTeam",{})) or "TBD"
            sc2  = game.get("score",{}) or {}
            start = None
            for k in ("startTime","startDate","date"):
                if sc.get(k):
                    try: start = datetime.fromisoformat(sc[k].replace("Z","+00:00")); break
                    except: pass
            out.append(Match(
                match_id  = str(sc.get("id","")),
                provider  = "MySportsFeeds",
                league    = sport,
                league_id = sport,
                home_team = home,
                away_team = away,
                home_score= _toint(sc2.get("homeScoreTotal")),
                away_score= _toint(sc2.get("awayScoreTotal")),
                status    = "LIVE" if live else ("FINISHED" if done else "SCHEDULED"),
                start_time= start,
            ))
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# THESPORTSDB PROVIDER — UFC/F1/Tennis/Cricket/Golf
# ═══════════════════════════════════════════════════════════════════════════════
class TheSportsDBProvider(DataProvider):
    LEAGUE_IDS = {
        "UFC": "4467", "Formula 1": "4370", "Tennis": "4424",
        "Cricket": "4722", "Golf": "4426",
    }

    def __init__(self):
        super().__init__("TheSportsDB")
        self.key = APIConfig.TSDB_KEY or "3"

    def _req_v1(self, ep, p=None):
        return self._req(f"{APIConfig.TSDB_URL}/{self.key}/{ep}", params=p)

    def get_upcoming(self, sport: str) -> List[Match]:
        lid = self.LEAGUE_IDS.get(sport)
        if not lid: return []
        ck = self._ck("upcoming", sport)
        c  = self._get(ck, APIConfig.TTL_UPCOMING)
        if c is not None: return c
        d = self._req_v1("eventsnextleague.php", {"id": lid})
        out = []
        if d and d.get("events"):
            for ev in d["events"]:
                start = None
                if ev.get("dateEvent"):
                    try:
                        ts    = (ev.get("strTime") or "00:00:00")[:5]
                        start = datetime.strptime(f"{ev['dateEvent']} {ts}", "%Y-%m-%d %H:%M")
                    except: pass
                out.append(Match(
                    match_id  = ev.get("idEvent",""),
                    provider  = "TheSportsDB",
                    league    = ev.get("strLeague", sport),
                    league_id = ev.get("idLeague",""),
                    home_team = ev.get("strHomeTeam","TBD"),
                    away_team = ev.get("strAwayTeam","TBD"),
                    status    = "SCHEDULED",
                    start_time= start,
                ))
        self._set(ck, out); return out

    def get_live(self, sport: str) -> List[Match]:
        sport_map = {"UFC":"MMA","Formula 1":"Motorsport","Tennis":"Tennis",
                     "Cricket":"Cricket","Golf":"Golf"}
        ck = self._ck("live", sport)
        c  = self._get(ck, APIConfig.TTL_LIVE)
        if c is not None: return c
        d = self._req_v1("livescore.php", {"s": sport_map.get(sport, sport)})
        out = []
        if d and d.get("events"):
            for ev in d["events"]:
                out.append(Match(
                    match_id  = ev.get("idEvent",""),
                    provider  = "TheSportsDB",
                    league    = ev.get("strLeague", sport),
                    league_id = ev.get("idLeague",""),
                    home_team = ev.get("strHomeTeam","TBD"),
                    away_team = ev.get("strAwayTeam","TBD"),
                    home_score= _toint(ev.get("intHomeScore")),
                    away_score= _toint(ev.get("intAwayScore")),
                    status    = "LIVE",
                    country   = ev.get("strCountry"),
                ))
        self._set(ck, out); return out


# ═══════════════════════════════════════════════════════════════════════════════
# APIFY / FLASHSCORE PROVIDER - CORRECTED WITH FOOTBALL MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

class ApifyProvider(DataProvider):
    """Calls Apify FlashScore scraper with correct API workflow and sport name mapping"""

    # Use the actor ID from your Apify account
    ACTOR_ID = "crawlerbros~flashscore-scraper"
    
    # Map internal sport names to FlashScore URL paths
    # IMPORTANT: FlashScore uses "football" not "soccer"
    FLASHSCORE_PATH_MAP = {
        "Soccer": "football",
        "NBA": "basketball/nba",
        "NFL": "american-football/nfl",
        "MLB": "baseball/mlb",
        "NHL": "hockey/nhl",
        "Tennis": "tennis",
        "Cricket": "cricket",
        "Rugby": "rugby",
        "Volleyball": "volleyball",
        "Handball": "handball",
        "Table Tennis": "table-tennis",
        "Snooker": "snooker",
        "Darts": "darts",
        "Esports": "esports",
        "Golf": "golf",
        "Formula 1": "motorsport/formula-1",
        "UFC": "mma/ufc",
    }

    def __init__(self):
        super().__init__("Apify/FlashScore")
        self.token = APIConfig.APIFY_API_TOKEN
        self._prefetch_done = False

    @property
    def ok(self):
        return bool(self.token)

    def _get_flashscore_url(self, sport: str) -> Optional[str]:
        """Get correct FlashScore URL for the sport - handles 'Soccer' to 'football' mapping"""
        path = self.FLASHSCORE_PATH_MAP.get(sport)
        if not path:
            logger.warning(f"[Apify] No URL mapping for sport: {sport}")
            return None
        
        # Build the URL
        url = f"https://www.flashscore.com/{path}/"
        
        # For soccer, also log which URL we're using
        if sport == "Soccer":
            logger.info(f"[Apify] Using FlashScore URL for football: {url}")
        
        return url

    def _call_actor(self, start_url: str, timeout: int = 65) -> Optional[List]:
        """Run Apify actor and wait for results"""
        if not self.token:
            logger.warning("[Apify] No API token")
            return None

        # Step 1: Start the actor run
        run_url = f"https://api.apify.com/v2/acts/{self.ACTOR_ID}/runs"
        
        # Build payload with proper parameters for FlashScore
        payload = {
            "startUrls": [{"url": start_url}],
            "maxItems": 300,
            "proxyConfiguration": {"useApifyProxy": True}
        }
        
        logger.info(f"[Apify] Starting actor with URL: {start_url}")

        try:
            # Start the run
            start_response = requests.post(
                run_url,
                params={"token": self.token},
                json=payload,
                timeout=30
            )

            if start_response.status_code != 201:
                logger.error(f"[Apify] Failed to start run: {start_response.status_code} - {start_response.text[:200]}")
                return None

            run_data = start_response.json()
            run_id = run_data.get('data', {}).get('id')

            if not run_id:
                logger.error("[Apify] No run ID returned")
                return None

            # Step 2: Wait for completion with progress indicator
            logger.info(f"[Apify] Run started: {run_id}")
            start_time = time.time()
            last_status = ""
            
            while time.time() - start_time < timeout:
                status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
                status_response = requests.get(status_url, params={"token": self.token})

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    run_status = status_data.get('data', {}).get('status')
                    
                    # Log status change
                    if run_status != last_status:
                        logger.info(f"[Apify] Run status: {run_status}")
                        last_status = run_status

                    if run_status == 'SUCCEEDED':
                        # Step 3: Fetch results
                        dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"
                        items_response = requests.get(dataset_url, params={"token": self.token, "limit": 500})

                        if items_response.status_code == 200:
                            items = items_response.json()
                            logger.info(f"[Apify] Retrieved {len(items)} items from run")
                            return items
                        else:
                            logger.error(f"[Apify] Failed to get dataset: {items_response.status_code}")
                            return None

                    elif run_status in ['FAILED', 'TIMED-OUT', 'ABORTED']:
                        logger.error(f"[Apify] Run {run_status}")
                        return None

                time.sleep(3)  # Wait before checking again

            logger.error(f"[Apify] Timeout after {timeout}s")
            return None

        except Exception as e:
            logger.error(f"[Apify] Error: {e}")
            return None

    def fetch_matches(self, sport: str) -> List[Match]:
        """Fetch matches for a given sport from FlashScore"""
        # Check cache first
        ck = self._ck("flashscore", sport)
        cached = self._get(ck, APIConfig.TTL_LIVE)
        if cached is not None:
            logger.info(f"[Apify] Returning {len(cached)} cached matches for {sport}")
            return cached

        # Get the correct FlashScore URL for this sport
        url = self._get_flashscore_url(sport)
        if not url:
            logger.warning(f"[Apify] No URL for sport: {sport}")
            return []

        logger.info(f"[Apify] Fetching {sport} from {url}")
        
        # For soccer, try multiple URLs if needed
        items = None
        if sport == "Soccer":
            # Try main football URL
            items = self._call_actor(url, 65)
            
            # If no items, try with Premier League URL
            if not items or len(items) == 0:
                logger.info("[Apify] Trying Premier League specific URL")
                items = self._call_actor("https://www.flashscore.com/football/england/premier-league/", 60)
        else:
            items = self._call_actor(url, 60)

        if not items or len(items) == 0:
            logger.warning(f"[Apify] No items returned for {sport}")
            return []

        matches = self._parse_items(items, sport)
        if matches:
            self._set(ck, matches)
            logger.info(f"[Apify] Parsed {len(matches)} matches for {sport}")

        return matches

    def get_live(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        matches = self.fetch_matches(sport)
        return [m for m in matches if m.status == "LIVE"]

    def get_upcoming(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        matches = self.fetch_matches(sport)
        return [m for m in matches if m.status == "SCHEDULED"]

    def get_all(self, sport: str) -> List[Match]:
        if not self.ok:
            return []
        return self.fetch_matches(sport)

    def prefetch(self):
        """Warm up cache in background"""
        if not self.ok or self._prefetch_done:
            return
        self._prefetch_done = True

        # Priority sports - note: "Soccer" maps to "football" in FlashScore
        priority_sports = ["Soccer", "NBA", "Tennis", "NFL", "MLB", "NHL"]
        
        def _run():
            for sport in priority_sports:
                try:
                    logger.info(f"[Apify] Prefetching {sport}")
                    matches = self.fetch_matches(sport)
                    logger.info(f"[Apify] Prefetched {len(matches)} matches for {sport}")
                    time.sleep(5)  # Delay between prefetches
                except Exception as e:
                    logger.warning(f"[Apify] Prefetch error {sport}: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _parse_items(self, items: List, sport: str) -> List[Match]:
        """Parse Apify output into Match objects"""
        out = []
        
        if not items:
            return out

        logger.info(f"[Apify] Parsing {len(items)} items for {sport}")

        for item in items:
            if not isinstance(item, dict):
                continue

            # Extract team names - handle various field names
            home = (item.get('homeTeam') or item.get('home') or
                   item.get('team1') or item.get('homeName') or 
                   item.get('participants', [{}])[0].get('name') if item.get('participants') else '')
            away = (item.get('awayTeam') or item.get('away') or
                   item.get('team2') or item.get('awayName') or
                   item.get('participants', [{}])[1].get('name') if len(item.get('participants', [])) > 1 else '')

            # Handle nested team objects
            if isinstance(home, dict):
                home = home.get('name', home.get('shortName', 'TBD'))
            if isinstance(away, dict):
                away = away.get('name', away.get('shortName', 'TBD'))

            # Clean up team names
            home = str(home).strip() if home else 'TBD'
            away = str(away).strip() if away else 'TBD'

            # Skip if no valid teams
            if home == 'TBD' and away == 'TBD':
                continue

            # Tournament/league information
            tournament = item.get('tournament') or item.get('league') or item.get('competition')
            if isinstance(tournament, dict):
                league = tournament.get('name', tournament.get('longName', sport))
                country = tournament.get('category', {}).get('name', '')
            else:
                league = str(tournament) if tournament else sport
                country = item.get('country', '')

            # Parse status
            status_raw = str(item.get('status') or item.get('matchStatus') or
                            item.get('statusText') or item.get('eventStatus') or 'SCHEDULED').lower()

            # Determine if live or finished
            is_live = any(x in status_raw for x in ['live', 'in progress', '1st', '2nd', '1st half', '2nd half',
                                                      'half', 'period', 'quarter', 'ongoing', 'inplay', 'in_play'])
            is_finished = any(x in status_raw for x in ['finished', 'ft', 'final', 'ended', 'complete'])

            if is_live:
                status = "LIVE"
            elif is_finished:
                status = "FINISHED"
            else:
                status = "SCHEDULED"

            # Extract scores
            home_score = None
            away_score = None

            # Try direct score fields
            if 'score' in item:
                score = item['score']
                if isinstance(score, dict):
                    home_score = score.get('home') or score.get('homeTeam')
                    away_score = score.get('away') or score.get('awayTeam')
                elif isinstance(score, str) and ':' in score:
                    parts = score.split(':')
                    if len(parts) == 2:
                        home_score = _toint(parts[0])
                        away_score = _toint(parts[1])

            # Try other score field names
            if home_score is None:
                home_score = item.get('homeScore') or item.get('goalsHome') or item.get('scoreHome')
            if away_score is None:
                away_score = item.get('awayScore') or item.get('goalsAway') or item.get('scoreAway')

            home_score = _toint(home_score)
            away_score = _toint(away_score)

            # Parse start time
            start_time = None
            time_fields = ['startTime', 'startTimestamp', 'date', 'kickoff', 'time', 'startDate', 'scheduled']
            for field in time_fields:
                raw_time = item.get(field)
                if raw_time:
                    try:
                        if isinstance(raw_time, (int, float)):
                            # Assume timestamp in seconds or milliseconds
                            if raw_time > 1e10:
                                raw_time = raw_time / 1000
                            start_time = datetime.fromtimestamp(raw_time)
                        elif isinstance(raw_time, str):
                            # Try to parse ISO format
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                try:
                                    start_time = datetime.strptime(raw_time[:19], fmt)
                                    break
                                except:
                                    continue
                        break
                    except Exception as e:
                        continue

            # Create match ID
            match_id = str(item.get('id') or item.get('matchId') or
                          item.get('eventId') or item.get('_id') or
                          abs(hash(f"{home}{away}{league}{start_time}")) % 10**9)

            out.append(Match(
                match_id=match_id,
                provider="FlashScore",
                league=league[:100],
                league_id=str(item.get('tournamentId', item.get('leagueId', ''))),
                home_team=home[:50],
                away_team=away[:50],
                home_score=home_score,
                away_score=away_score,
                status=status,
                start_time=start_time,
                country=country[:50] if country else None,
            ))

        logger.info(f"[Apify] Successfully parsed {len(out)} matches for {sport}")
        return out


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _toint(v) -> Optional[int]:
    try: return int(v) if v is not None else None
    except: return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE DATA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
SOCCER_SPORTS = {"Soccer"}
US_SPORTS     = {"NBA","NFL","MLB","NHL"}
MISC_SPORTS   = {"UFC","Formula 1","Tennis","Cricket","Golf"}
FS_SPORTS     = set(ApifyProvider.FLASHSCORE_PATH_MAP.keys())   # all mapped sports


class EmpireDataRouter:
    def __init__(self):
        self.api_sports   = APISportsProvider()
        self.football_data= FootballDataProvider()
        self.msf          = MySportsFeedsProvider()
        self.tsdb         = TheSportsDBProvider()
        self.apify        = ApifyProvider()
        self.log: List[Dict] = []
        self._log_startup()
        self.apify.prefetch()   # warm cache in background

    def _log(self, prov, status, detail):
        self.log.append({"TIME": datetime.now().strftime("%H:%M:%S"),
                         "PROVIDER": prov, "STATUS": status,
                         "DETAIL": str(detail)[:80]})

    def _log_startup(self):
        items = [
            ("Apify/FlashScore", bool(APIConfig.APIFY_API_TOKEN), "30+ sports"),
            ("API-SPORTS",       bool(APIConfig.API_SPORTS_KEY),  "Soccer"),
            ("Football-Data",    bool(APIConfig.FOOTBALL_DATA_KEY),"Soccer backup"),
            ("MySportsFeeds",    bool(APIConfig.MSF_KEY),          "NBA/NFL/MLB/NHL"),
            ("TheSportsDB",      True,                             "UFC/F1/Tennis"),
        ]
        for n, ok, d in items:
            self._log(n, "READY" if ok else "NOT CONFIGURED", d)

    def get_provider_status(self) -> List[Dict]:
        return [
            {"name":"Apify/FlashScore",  "status":"🟢 ONLINE" if APIConfig.APIFY_API_TOKEN else "⚪ NOT CONFIGURED"},
            {"name":"API-SPORTS",        "status":"🟢 ONLINE" if APIConfig.API_SPORTS_KEY   else "⚪ NOT CONFIGURED"},
            {"name":"Football-Data",     "status":"🟢 ONLINE" if APIConfig.FOOTBALL_DATA_KEY else "⚪ NOT CONFIGURED"},
            {"name":"MySportsFeeds",     "status":"🟢 ONLINE" if APIConfig.MSF_KEY           else "⚪ NOT CONFIGURED"},
            {"name":"TheSportsDB",       "status":"🟢 ONLINE"},
        ]

    def get_connection_log_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.log[-60:]) if self.log else pd.DataFrame()

    def get_all_leagues(self, sport: str) -> List[Dict]:
        """Always returns instantly from static list. Soccer enriched from API if key active."""
        static = STATIC_LEAGUES.get(sport, [{"id":"ALL","name":"All Events","country":"World"}])
        if sport == "Soccer" and self.api_sports.ok:
            ck = "apisports_leagues"
            c  = self.api_sports._get(ck, APIConfig.TTL_LEAGUES)
            if c: return c
            def _warm():
                leagues = self.api_sports.get_leagues()
                if leagues: self._log("API-SPORTS","LEAGUES",f"{len(leagues)} leagues cached")
            threading.Thread(target=_warm, daemon=True).start()
        return static

    def get_live_matches(self, sport: str, league_id: str = None) -> pd.DataFrame:
        matches = []
        try:
            # 1. Try Apify (fastest, all sports)
            if self.apify.ok and sport in FS_SPORTS:
                matches = self.apify.get_live(sport)
                self._log("Apify", "SUCCESS" if matches else "EMPTY", f"{len(matches)} live {sport}")

            # 2. Fallback to legacy providers
            if not matches:
                if sport in SOCCER_SPORTS:
                    matches = self.api_sports.get_live(league_id)
                    if not matches:
                        # Football-Data also covers live
                        fd_today = self.football_data.get_today()
                        matches  = [m for m in fd_today if m.status == "LIVE"]
                    self._log("Soccer-Fallback","RESULT", f"{len(matches)} live")
                elif sport in US_SPORTS:
                    matches = self.msf.get_today(sport)
                    matches = [m for m in matches if m.status == "LIVE"]
                    self._log("MySportsFeeds","RESULT", f"{len(matches)} live {sport}")
                elif sport in MISC_SPORTS:
                    matches = self.tsdb.get_live(sport)
                    self._log("TheSportsDB","RESULT", f"{len(matches)} live {sport}")

        except Exception as e:
            self._log("ROUTER","ERROR", f"live {sport}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()

    def get_upcoming_matches(self, sport: str) -> pd.DataFrame:
        matches = []
        try:
            # 1. Try Apify
            if self.apify.ok and sport in FS_SPORTS:
                matches = self.apify.get_upcoming(sport)
                self._log("Apify","SUCCESS" if matches else "EMPTY", f"{len(matches)} upcoming {sport}")

            # 2. Fallback
            if not matches:
                if sport in SOCCER_SPORTS:
                    matches = self.api_sports.get_upcoming()
                    if not matches:
                        fd_today = self.football_data.get_today()
                        matches  = [m for m in fd_today if m.status == "SCHEDULED"]
                    self._log("Soccer-Fallback","RESULT", f"{len(matches)} upcoming")
                elif sport in US_SPORTS:
                    matches = self.msf.get_upcoming(sport)
                    self._log("MySportsFeeds","RESULT", f"{len(matches)} upcoming {sport}")
                elif sport in MISC_SPORTS:
                    matches = self.tsdb.get_upcoming(sport)
                    self._log("TheSportsDB","RESULT", f"{len(matches)} upcoming {sport}")

        except Exception as e:
            self._log("ROUTER","ERROR", f"upcoming {sport}: {e}")

        return pd.DataFrame([m.to_dataframe_row() for m in matches]) if matches else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE
# ═══════════════════════════════════════════════════════════════════════════════
class EmpireDashboardData:
    def __init__(self):
        self.router = EmpireDataRouter()

    @property
    def is_live(self) -> bool:
        return bool(APIConfig.APIFY_API_TOKEN or APIConfig.API_SPORTS_KEY
                    or APIConfig.MSF_KEY or APIConfig.TSDB_KEY)

    def get_connection_log_df(self)   -> pd.DataFrame: return self.router.get_connection_log_df()
    def get_all_leagues(self, s: str) -> List[Dict]:    return self.router.get_all_leagues(s)
    def get_live_matches_df(self, s: str, lid: str = None) -> pd.DataFrame:
        return self.router.get_live_matches(s, lid)
    def get_upcoming_matches_df(self, s: str) -> pd.DataFrame:
        return self.router.get_upcoming_matches(s)

    # Stubs
    def get_match_prediction(self, mid): return None
    def get_match_details(self, mid):    return {"found": False}
    def get_team_form(self, t, mid):     return None
    def get_head_to_head(self, h, a, mid): return []
    def get_key_players(self, mid):      return []
    def get_match_odds(self, mid):       return {}
    def get_ai_reasoning(self, mid):     return []


__all__ = ["APIConfig", "EmpireDashboardData"]
