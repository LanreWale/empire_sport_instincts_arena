"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
World-Class Professional Command Center
24/7 AI Engine | Real-Time Global Sports Intelligence
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from pathlib import Path
import base64
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

from empire_data_layer import EmpireDashboardData, APIConfig

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="BRAND_ASSET/empire_logo_primary.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LAYER INIT
# ═══════════════════════════════════════════════════════════════════════════════
data = EmpireDashboardData()

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ═══════════════════════════════════════════════════════════════════════════════
# AGGRESSIVE API CACHING — ELIMINATES LAG
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def api_all_leagues(sport_type: str):
    """
    Fetch ALL global leagues for a sport.
    CRITICAL FIX: pass the sport TYPE string (e.g. 'Soccer'), NOT the config dict.
    """
    try:
        # Primary: string-based sport query (returns global catalogue)
        result = data.get_all_leagues(sport_type)
        if result and len(result) > 1:
            return result
    except Exception as e:
        logger.warning(f"String league fetch failed for {sport_type}: {e}")
    try:
        # Defensive fallback: dict-based query
        cfg = SPORT_OPTIONS.get(sport_type, {})
        if cfg:
            result = data.get_all_leagues(cfg)
            if result:
                return result
    except Exception as e:
        logger.warning(f"Dict league fetch failed for {sport_type}: {e}")
    return []

@st.cache_data(ttl=120, show_spinner=False)
def api_live_matches(sport_cfg, league_id: str):
    try:
        return data.get_live_matches_df(sport_cfg, league_id)
    except Exception as e:
        logger.error(f"Live fetch error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=120, show_spinner=False)
def api_upcoming_matches(sport_cfg):
    try:
        return data.get_upcoming_matches_df(sport_cfg)
    except Exception as e:
        logger.error(f"Upcoming fetch error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=120, show_spinner=False)
def api_finished_matches(sport_cfg, league_id: str):
    try:
        return data.router.get_matches_by_status("FINISHED", sport_cfg, league_id)
    except Exception as e:
        logger.error(f"Finished fetch error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def api_match_details(match_id: str):
    try:
        return data.router.get_match_details(match_id)
    except Exception as e:
        logger.error(f"Details fetch error: {e}")
        return {}

@st.cache_data(ttl=60, show_spinner=False)
def api_match_prediction(match_id: str):
    try:
        return data.get_match_prediction(match_id)
    except Exception as e:
        logger.error(f"Prediction fetch error: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Soccer":      {"sport_type": "Soccer",      "icon": "⚽", "season": "2024-2025"},
    "NBA":         {"sport_type": "Basketball",  "icon": "🏀", "season": "2024-2025"},
    "NFL":         {"sport_type": "American Football", "icon": "🏈", "season": "2024"},
    "MLB":         {"sport_type": "Baseball",    "icon": "⚾", "season": "2024"},
    "NHL":         {"sport_type": "Ice Hockey",  "icon": "🏒", "season": "2024"},
    "UFC":         {"sport_type": "MMA",         "icon": "🥊", "season": "2024"},
    "Formula 1":   {"sport_type": "Motorsport",  "icon": "🏎️", "season": "2024"},
    "Tennis":      {"sport_type": "Tennis",      "icon": "🎾", "season": "2024"},
    "Cricket":     {"sport_type": "Cricket",     "icon": "🏏", "season": "2024"},
    "Golf":        {"sport_type": "Golf",        "icon": "⛳", "season": "2024"},
}

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — DARK GOLD ARENA THEME
# ═══════════════════════════════════════════════════════════════════════════════
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');

.stApp {
    background: linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
    font-family: 'Rajdhani', sans-serif;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
    border-right: 3px solid #D4AF37;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #D4AF37 !important;
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    letter-spacing: 2px;
}

.tagline-bold {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 900;
    background: linear-gradient(135deg, #D4AF37 0%, #FFD700 50%, #B8860B 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 6px;
    margin-bottom: 2px;
}

.tagline-sub {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
    color: #888;
    text-align: center;
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-top: 2px;
    margin-bottom: 8px;
}

.ai-status {
    background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
    color: #000;
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 0.8rem;
    padding: 8px 16px;
    border-radius: 20px;
    text-align: center;
    letter-spacing: 3px;
    text-transform: uppercase;
    box-shadow: 0 0 15px rgba(0, 255, 136, 0.4);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.4); }
    50% { box-shadow: 0 0 25px rgba(0, 255, 136, 0.8); }
}

.section-header {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #FFD700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 15px 20px;
    background: linear-gradient(90deg, rgba(212, 175, 55, 0.2) 0%, transparent 100%);
    border-left: 4px solid #D4AF37;
    border-radius: 0 8px 8px 0;
    margin: 20px 0 10px 0;
}

.gold-divider {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, #D4AF37 50%, transparent 100%);
    margin: 20px 0;
}

.world-clock {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.9rem;
    color: #D4AF37;
    text-align: center;
    letter-spacing: 2px;
    padding: 10px;
    background: rgba(212, 175, 55, 0.1);
    border-radius: 8px;
    margin: 10px 0;
}

.ticker {
    background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
    border-top: 2px solid #D4AF37;
    border-bottom: 2px solid #D4AF37;
    padding: 10px;
    overflow: hidden;
    white-space: nowrap;
}

.ticker-text {
    font-family: 'Rajdhani', sans-serif;
    color: #FFD700;
    font-size: 0.9rem;
    letter-spacing: 2px;
    animation: scroll 25s linear infinite;
}

@keyframes scroll {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

/* Make arena buttons look like gold command buttons */
.stButton>button {
    background: linear-gradient(135deg, #D4AF37 0%, #FFD700 100%);
    color: #000;
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 2rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #FFD700 0%, #FFF8DC 100%);
    box-shadow: 0 0 25px rgba(212, 175, 55, 0.6);
    transform: scale(1.02);
}

/* Secondary buttons (match cards) */
button[kind="secondary"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
    color: #FFD700 !important;
    border: 1px solid #333 !important;
    font-family: 'Orbitron', sans-serif !important;
    width: 100%;
}
button[kind="secondary"]:hover {
    border-color: #D4AF37 !important;
    box-shadow: 0 0 15px rgba(212, 175, 55, 0.2) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(26, 26, 46, 0.5);
    border-radius: 10px;
    padding: 5px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #888;
    font-family: 'Orbitron', sans-serif;
    font-weight: 500;
    letter-spacing: 1px;
    border-radius: 6px;
    padding: 0.5rem 1.5rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #D4AF37 0%, #FFD700 100%) !important;
    color: #000 !important;
    font-weight: 700;
}

.detail-panel {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
    border: 2px solid #D4AF37;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}

.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #2a2a3e;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.95rem;
}
.stat-label { color: #888; }
.stat-value { color: #FFD700; font-weight: 700; }

.odds-row {
    display: flex;
    justify-content: space-around;
    padding: 15px;
    background: rgba(212, 175, 55, 0.1);
    border-radius: 8px;
    margin: 10px 0;
}
.odds-box { text-align: center; padding: 10px 20px; }
.odds-label {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    color: #888;
    text-transform: uppercase;
}
.odds-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    color: #FFD700;
    font-weight: 900;
}

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%);
    border-radius: 4px;
}
</style>
""")

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE CALLBACKS — RELIABLE MATCH SELECTION
# ═══════════════════════════════════════════════════════════════════════════════
def select_match_callback(match_id, home, away):
    st.session_state.selected_match_id = str(match_id)
    st.session_state.selected_match_home = str(home)
    st.session_state.selected_match_away = str(away)

def clear_match_selection():
    for key in ["selected_match_id", "selected_match_home", "selected_match_away"]:
        st.session_state.pop(key, None)

def on_sport_change():
    # Wipe league cache for the NEW sport so it forces a fresh fetch
    sport = st.session_state.get("sport_widget", "Soccer")
    st.session_state.pop(f"league_list_{sport}", None)
    st.session_state.pop(f"league_id_{sport}", None)
    clear_match_selection()

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
def render_header():
    logo_path = Path("BRAND_ASSET/empire_logo_primary.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" style="width:90%;max-height:160px;object-fit:contain;display:block;margin:0 auto;">'
    else:
        logo_html = '<div style="text-align:center;color:#D4AF37;font-family:Orbitron;font-size:28px;font-weight:900;">EMPIRE</div>'

    st.markdown(f'<div style="text-align:center;padding:10px 0;">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Advanced Research & Evaluation System | Where Data Meets Instinct</div>', unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # World clock
    now = datetime.now()
    cities = [
        ("LONDON", now + timedelta(hours=1)), ("NEW YORK", now - timedelta(hours=5)),
        ("TOKYO", now + timedelta(hours=9)), ("SYDNEY", now + timedelta(hours=10)),
        ("LAGOS", now + timedelta(hours=1)),
    ]
    clock = " | ".join([f"{c}: {dt.strftime('%H:%M')}" for c, dt in cities])
    st.markdown(f'<div class="world-clock">🌍 {clock}</div>', unsafe_allow_html=True)

    # Live / Demo banner
    try:
        if data.is_live:
            provider = data.router.active_provider.name if data.router.active_provider else "API"
            st.markdown(f"""
            <div style="background:linear-gradient(90deg,#00ff88,#00cc6a);color:#000;font-family:Orbitron;font-size:1rem;padding:12px;border-radius:8px;text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;">
                🟢 LIVE MODE — Connected to {provider}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:linear-gradient(90deg,#B8860B,#FFD700);color:#000;font-family:Orbitron;font-size:1rem;padding:12px;border-radius:8px;text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;">
                ⚠️ DEMO MODE — Check API keys in .env
            </div>""", unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#ff4444,#cc0000);color:#fff;font-family:Orbitron;font-size:1rem;padding:12px;border-radius:8px;text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;">
            🔴 SYSTEM ERROR — Data layer not initialized
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown('<h2 style="text-align:center;font-size:1.2rem;">COMMAND CENTER</h2>', unsafe_allow_html=True)

        # Live match count (real API, cached)
        live_count = 0
        try:
            live_df = api_live_matches(SPORT_OPTIONS["Soccer"], "ALL")
            if live_df is not None and not live_df.empty:
                live_count = len(live_df)
        except Exception:
            pass

        st.markdown(f"""
        <div style="background:rgba(0,255,136,0.1);border:1px solid #00ff88;border-radius:8px;padding:10px;margin:10px 0;">
            <div style="color:#00ff88;font-family:Orbitron;font-size:0.8rem;text-align:center;">
                🤖 INSTINCT BOT v2.0<br>
                <span style="color:#888;font-size:0.7rem;">SCANNING {live_count} LIVE MATCHES</span><br>
                <span style="color:#00ff88;">● LIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("⚡ SYSTEM STATUS")
        st.markdown('<div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px;margin:8px 0;">', unsafe_allow_html=True)

        try:
            for s in data.router.get_provider_status():
                if "ONLINE" in s["status"]:
                    icon, color = "🟢", "#00ff88"
                elif "EMPTY" in s["status"]:
                    icon, color = "🟡", "#FFD700"
                else:
                    icon, color = "🔴", "#ff4444"
                st.markdown(f'<div style="font-family:Orbitron;font-size:0.7rem;color:{color};padding:2px 0;">{icon} {s["name"]}: {s["status"].split(" — ")[-1]}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div style="font-family:Orbitron;font-size:0.7rem;color:#ff4444;padding:2px 0;">🔴 Router: {str(e)[:40]}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        c1.metric("DATA", "ACTIVE", delta="●", delta_color="normal")
        c2.metric("MODELS", "ONLINE", delta="●", delta_color="normal")

        st.subheader("🛡️ RISK CONTROLS")
        st.slider("KELLY %", 0.05, 0.50, 0.25, 0.05, format="%.0f%%")
        st.slider("MAX BET", 0.01, 0.10, 0.03, 0.01, format="%.0f%%")
        st.slider("MIN EV", 0.01, 0.10, 0.02, 0.01, format="%.0f%%")

        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.markdown("<hr style='border-color:#333;margin:15px 0;'>", unsafe_allow_html=True)
        st.subheader("📡 API CONNECTION LOG")

        try:
            log_df = data.router.get_connection_log_df()
            if not log_df.empty:
                render_api_log_table(log_df)
            else:
                st.info("No connection attempts yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {str(e)[:50]}")

def render_api_log_table(log_df):
    """Custom HTML table guaranteed to render with dark arena background."""
    html = '<div style="background:#1a1a2e;border:1px solid #2a2a3e;border-radius:8px;overflow:hidden;max-height:280px;overflow-y:auto;">'
    html += '<table style="width:100%;border-collapse:collapse;font-family:Rajdhani,sans-serif;font-size:0.82rem;">'
    html += '<tr style="background:linear-gradient(135deg,#D4AF37,#B8860B);color:#000;font-family:Orbitron;font-weight:900;font-size:0.78rem;text-transform:uppercase;letter-spacing:1px;">'
    for col in log_df.columns:
        html += f'<th style="padding:10px 8px;text-align:center;border-bottom:3px solid #FFD700;">{col}</th>'
    html += '</tr>'

    for _, row in log_df.iterrows():
        status = str(row.get("STATUS", ""))
        if status == "SUCCESS":
            c = "#00ff88"
        elif status in ("FAIL", "ERROR", "TIMEOUT"):
            c = "#ff4444"
        elif status == "EMPTY":
            c = "#FFD700"
        else:
            c = "#888"
        html += '<tr style="border-bottom:1px solid #2a2a3e;">'
        for col in log_df.columns:
            v = row.get(col, "")
            if col == "STATUS":
                html += f'<td style="padding:8px;color:{c};text-align:center;font-weight:700;">{v}</td>'
            else:
                html += f'<td style="padding:8px;color:#FFD700;text-align:center;font-weight:500;">{v}</td>'
        html += '</tr>'
    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TICKER
# ═══════════════════════════════════════════════════════════════════════════════
def render_live_ticker():
    try:
        df = api_live_matches(SPORT_OPTIONS["Soccer"], "ALL")
        if not df.empty:
            matches = []
            for _, row in df.head(6).iterrows():
                status_icon = "🔴" if "LIVE" in str(row.get("STATUS", "")) else "⏳"
                league = str(row.get("LEAGUE", row.get("league", "Unknown")))
                match = str(row.get("MATCH", row.get("match", "vs")))
                status = str(row.get("STATUS", ""))
                matches.append(f"{status_icon} {league}: {match} ({status})")
            ticker = "    ★    ".join(matches)
        else:
            ticker = "📡 Scanning global feeds...    ★    🔄 Stand by for live data..."
    except Exception:
        ticker = "📡 Scanning global feeds...    ★    🔄 Stand by for live data..."

    st.markdown(f'<div class="ticker"><div class="ticker-text">{ticker}</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATAFRAME COLUMN DETECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def detect_columns(df):
    """Auto-detect standard columns in a match dataframe."""
    cols = {
        "home": None, "away": None, "home_score": None, "away_score": None,
        "score": None, "status": None, "league": None, "league_id": None,
        "date": None, "time": None, "match_id": None,
    }
    for col in df.columns:
        u = str(col).upper().replace("_", "").replace(" ", "")
        if not cols["home"] and any(x in u for x in ['HOME', 'HTEAM', 'TEAM1', 'T1', 'STRHOMETEAM', 'LOCAL', 'HOMETEAM']):
            cols["home"] = col
        elif not cols["away"] and any(x in u for x in ['AWAY', 'ATEAM', 'TEAM2', 'T2', 'STRAWAYTEAM', 'VISITOR', 'AWAYTEAM']):
            cols["away"] = col
        elif not cols["score"] and any(x in u for x in ['SCORE', 'RESULT', 'VS', 'FULLTIME', 'FT']):
            cols["score"] = col
        elif not cols["home_score"] and any(x in u for x in ['HOMESCORE', 'INTHOMESCORE', 'HOME_GOAL', 'HSCORE']):
            cols["home_score"] = col
        elif not cols["away_score"] and any(x in u for x in ['AWAYSCORE', 'INTAWAYSCORE', 'AWAY_GOAL', 'ASCORE']):
            cols["away_score"] = col
        elif not cols["status"] and any(x in u for x in ['STATUS', 'STATE', 'LIVE', 'STRSTATUS', 'MATCHSTATUS']):
            cols["status"] = col
        elif not cols["league"] and any(x in u for x in ['LEAGUE', 'COMPETITION', 'TOURNAMENT', 'STRLEAGUE', 'COMP']):
            cols["league"] = col
        elif not cols["league_id"] and any(x in u for x in ['LEAGUEID', 'IDLEAGUE', 'LEAGUE_ID', 'ID_LEAGUE']):
            cols["league_id"] = col
        elif not cols["date"] and any(x in u for x in ['DATE', 'DATEEVENT', 'DATETIME', 'STRDATE', 'MATCHDATE']):
            cols["date"] = col
        elif not cols["time"] and any(x in u for x in ['TIME', 'STRTIME', 'KICKOFF', 'MATCHTIME', 'STARTTIME']):
            cols["time"] = col
        elif not cols["match_id"] and any(x in u for x in ['MATCHID', 'IDMATCH', 'MATCH_ID', 'ID_MATCH', 'EVENTID', 'IDEVENT']):
            cols["match_id"] = col
    return cols

def filter_df_by_league(df, league_id, league_options):
    """Client-side filter that auto-detects the correct league column."""
    if league_id == "ALL" or df is None or df.empty:
        return df
    # Try league_id column first
    for col in df.columns:
        u = str(col).upper().replace("_", "")
        if "LEAGUEID" in u or "IDLEAGUE" in u or "LEAGUE_ID" in u:
            try:
                mask = df[col].astype(str) == str(league_id)
                if mask.any():
                    return df[mask]
            except Exception:
                continue
    # Try league name column
    target_name = None
    for lid, label in league_options:
        if str(lid) == str(league_id):
            target_name = label.replace("🏆 ", "").split(" (")[0]
            break
    if target_name:
        for col in df.columns:
            u = str(col).upper().replace("_", "")
            if "LEAGUE" in u or "COMP" in u or "TOURNAMENT" in u:
                try:
                    mask = df[col].astype(str).str.contains(target_name, case=False, na=False)
                    if mask.any():
                        return df[mask]
                except Exception:
                    continue
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# ARENA MATCH LIST — RELIABLE CLICKABLE CARDS
# ═══════════════════════════════════════════════════════════════════════════════
def render_arena_match_list(matches_df, sport_name, selected_league_id, league_options, selected_status):
    if matches_df is None or matches_df.empty:
        st.info("🔍 No matches found for the selected filters. The API may have no active data for this category right now.")
        return

    df = matches_df.copy()
    c = detect_columns(df)

    if not c["home"] or not c["away"]:
        st.warning(f"⚠️ Could not identify team columns. Available columns: {list(df.columns)}")
        return

    # Apply client-side league filter as safety net
    df = filter_df_by_league(df, selected_league_id, league_options)

    # Apply status filter
    if selected_status != "ALL" and c["status"]:
        mask = df[c["status"]].astype(str).str.upper().str.contains(selected_status, na=False)
        df = df[mask]

    if df.empty:
        st.info(f"🔍 No {selected_status.lower()} matches found for this league. Try 'ALL' leagues or a different status.")
        return

    st.markdown(f"<div style='color:#888;font-size:0.85rem;margin-bottom:10px;'>📊 Showing {len(df)} matches</div>", unsafe_allow_html=True)

    for idx, row in df.iterrows():
        home = str(row.get(c["home"], "TBD"))
        away = str(row.get(c["away"], "TBD"))

        if c["score"]:
            score = str(row.get(c["score"], "vs"))
        elif c["home_score"] and c["away_score"]:
            hs = str(row.get(c["home_score"], "-"))
            aws = str(row.get(c["away_score"], "-"))
            score = f"{hs} - {aws}" if hs != "-" or aws != "-" else "vs"
        else:
            score = "vs"

        status = str(row.get(c["status"], "SCHEDULED")) if c["status"] else "SCHEDULED"
        league = str(row.get(c["league"], "")) if c["league"] else ""
        match_date = str(row.get(c["date"], "")) if c["date"] else ""
        match_time = str(row.get(c["time"], "")) if c["time"] else ""
        match_id = str(row.get(c["match_id"], idx)) if c["match_id"] else str(idx)

        # Status badge colors
        su = status.upper()
        if any(x in su for x in ["LIVE", "IN PLAY", "1H", "2H", "HT"]):
            sc, sb, stxt = "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
        elif any(x in su for x in ["FINISHED", "FT", "COMPLETED", "ENDED", "PEN", "AET"]):
            sc, sb, stxt = "#888888", "rgba(136,136,136,0.15)", "FINISHED"
        else:
            sc, sb, stxt = "#FFAA00", "rgba(255,170,0,0.15)", "UPCOMING"

        # Visual card (HTML only, no click handler)
        card = f"""
        <div style="background:linear-gradient(135deg,rgba(20,25,40,0.95),rgba(10,15,30,0.98));border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;margin:8px 0;font-family:'Orbitron',sans-serif;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#8892b0;font-size:0.75rem;">{league} {f"• {match_date}" if match_date else ""}</span>
                <span style="color:{sc};background:{sb};padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:700;">{stxt}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="flex:1;text-align:left;"><div style="color:#e6f1ff;font-size:1.05rem;font-weight:600;">{home}</div></div>
                <div style="padding:0 20px;text-align:center;">
                    <div style="color:#00d4ff;font-size:1.5rem;font-weight:700;letter-spacing:2px;">{score}</div>
                    <div style="color:#8892b0;font-size:0.65rem;margin-top:2px;">{match_time}</div>
                </div>
                <div style="flex:1;text-align:right;"><div style="color:#e6f1ff;font-size:1.05rem;font-weight:600;">{away}</div></div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)

        # Reliable full-width Streamlit button with callback
        st.button(
            f"🔍 OPEN ANALYSIS: {home} vs {away}",
            key=f"btn_{sport_name}_{match_id}",
            on_click=select_match_callback,
            args=(match_id, home, away),
            use_container_width=True,
            type="secondary"
        )
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MATCH ANALYSIS PANEL — 100% LIVE API DATA
# ═══════════════════════════════════════════════════════════════════════════════
def render_match_analysis_panel():
    if "selected_match_id" not in st.session_state:
        st.info("👆 Select a match from the Arena to view detailed analysis.")
        return

    match_id = st.session_state.selected_match_id
    home = st.session_state.get("selected_match_home", "Home")
    away = st.session_state.get("selected_match_away", "Away")

    st.markdown(f'<div class="section-header">🔍 MATCH ANALYSIS — {home} vs {away}</div>', unsafe_allow_html=True)

    if st.button("← BACK TO ARENA", use_container_width=False):
        clear_match_selection()
        st.rerun()

    # Fetch details & prediction (cached)
    details = api_match_details(match_id)
    prediction = api_match_prediction(match_id)

    if not isinstance(details, dict):
        details = {}

    # ─── TOP ROW: Info + Odds + Prediction ───────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown("##### 📋 MATCH INFORMATION")
        st.markdown(f'<div class="stat-row"><span class="stat-label">Match ID</span><span class="stat-value">{match_id}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Status</span><span class="stat-value">{details.get("status", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Competition</span><span class="stat-value">{details.get("competition", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Date</span><span class="stat-value">{details.get("date", "N/A")}</span></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("##### ⚖️ CURRENT ODDS")
        odds = details.get("odds", {})
        ox = odds.get("1x2", {})
        home_odds = ox.get("home", "-")
        draw_odds = ox.get("draw", "-")
        away_odds = ox.get("away", "-")
        st.markdown(f"""
        <div class="odds-row">
            <div class="odds-box"><div class="odds-label">1 (Home)</div><div class="odds-value">{home_odds}</div></div>
            <div class="odds-box"><div class="odds-label">X (Draw)</div><div class="odds-value">{draw_odds}</div></div>
            <div class="odds-box"><div class="odds-label">2 (Away)</div><div class="odds-value">{away_odds}</div></div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 🎯 AI PREDICTION")
        if prediction and hasattr(prediction, "confidence"):
            conf = prediction.confidence
            conf_color = "#00FF88" if conf > 70 else "#FFD700" if conf > 50 else "#FF4444"
            st.markdown(f'<div style="font-size:2.2rem;color:{conf_color};font-weight:900;text-align:center;">{conf:.0f}%</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center;color:#888;font-size:0.8rem;">Confidence</div>', unsafe_allow_html=True)
            sig = getattr(prediction, "signal", "HOLD")
            st.markdown(f'<div style="margin-top:10px;padding:10px;background:rgba(0,255,136,0.1);border-radius:6px;text-align:center;color:#00FF88;font-family:Orbitron;font-weight:700;">SIGNAL: {str(sig).upper()}</div>', unsafe_allow_html=True)
        else:
            st.info("No prediction available from API.")

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ─── TEAM PROFILES & FORM — LIVE DATA ONLY ───────────────────────────────
    st.markdown("##### 🏆 TEAM PROFILES & RECENT FORM")
    tc1, tc2 = st.columns(2)

    with tc1:
        home_form = details.get("home_form", [])
        home_stats = details.get("home_stats", {})
        st.markdown(f'<div style="background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.2);border-radius:10px;padding:15px;">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#00FF88;font-family:Orbitron;font-size:1.1rem;margin-bottom:10px;">{home} (Home)</div>', unsafe_allow_html=True)
        if home_form:
            fh = "".join([
                f'<span style="display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:4px;margin-right:4px;font-size:0.75rem;font-weight:700;{"background:#00FF88;color:#000;" if r=="W" else "background:#FFD700;color:#000;" if r=="D" else "background:#FF4444;color:#fff;"}">{r}</span>'
                for r in home_form[:5]
            ])
            st.markdown(f'<div style="margin-bottom:10px;">{fh}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#666;font-size:0.8rem;margin-bottom:10px;">Form data unavailable from API</div>', unsafe_allow_html=True)

        for k, label in [("record", "Record"), ("goals_for", "Goals Scored"), ("goals_against", "Goals Conceded"), ("clean_sheets", "Clean Sheets")]:
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{home_stats.get(k, "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tc2:
        away_form = details.get("away_form", [])
        away_stats = details.get("away_stats", {})
        st.markdown(f'<div style="background:rgba(255,68,68,0.05);border:1px solid rgba(255,68,68,0.2);border-radius:10px;padding:15px;">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#FF4444;font-family:Orbitron;font-size:1.1rem;margin-bottom:10px;">{away} (Away)</div>', unsafe_allow_html=True)
        if away_form:
            fa = "".join([
                f'<span style="display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:4px;margin-right:4px;font-size:0.75rem;font-weight:700;{"background:#00FF88;color:#000;" if r=="W" else "background:#FFD700;color:#000;" if r=="D" else "background:#FF4444;color:#fff;"}">{r}</span>'
                for r in away_form[:5]
            ])
            st.markdown(f'<div style="margin-bottom:10px;">{fa}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#666;font-size:0.8rem;margin-bottom:10px;">Form data unavailable from API</div>', unsafe_allow_html=True)

        for k, label in [("record", "Record"), ("goals_for", "Goals Scored"), ("goals_against", "Goals Conceded"), ("clean_sheets", "Clean Sheets")]:
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{away_stats.get(k, "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ─── H2H & PLAYERS — LIVE DATA ONLY ──────────────────────────────────────
    h2h_col, player_col = st.columns(2)

    with h2h_col:
        st.markdown("##### ⚔️ HEAD TO HEAD")
        h2h = details.get("h2h", [])
        if h2h:
            for h in h2h[:5]:
                st.markdown(f'<div class="stat-row"><span class="stat-label">{h.get("date", "N/A")}</span><span class="stat-value">{h.get("score", "N/A")}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#666;font-size:0.7rem;margin-bottom:6px;">{h.get("competition", "")}</div>', unsafe_allow_html=True)
        else:
            st.info("No head-to-head data available from API.")

    with player_col:
        st.markdown("##### 👤 KEY PLAYERS")
        players = details.get("players", [])
        if players:
            for p in players[:5]:
                team_color = "#00FF88" if p.get("team") == home else "#FF4444"
                st.markdown(f'''
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #2a2a3e;">
                    <div>
                        <div style="color:#e6f1ff;font-weight:600;">{p.get("name", "Unknown")}</div>
                        <div style="color:{team_color};font-size:0.75rem;">{p.get("team", "N/A")}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#FFD700;font-family:Orbitron;font-size:0.9rem;">⭐ {p.get("rating", "-")}</div>
                        <div style="color:#888;font-size:0.7rem;">⚽ {p.get("goals", 0)} | 🅰️ {p.get("assists", 0)}</div>
                    </div>
                </div>''', unsafe_allow_html=True)
        else:
            st.info("No player data available from API.")

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ─── ODDS MARKETS — LIVE DATA ONLY ───────────────────────────────────────
    st.markdown("##### 💰 COMPLETE ODDS MARKET")
    odds_tabs = st.tabs(["1X2", "Over/Under", "BTTS", "Cards", "Corners", "Asian Handicap"])

    def safe_metric(label, value, delta=""):
        try:
            st.metric(label, value, delta)
        except Exception:
            st.metric(label, "-", "")

    with odds_tabs[0]:
        o = odds.get("1x2", {})
        c1, c2, c3 = st.columns(3)
        safe_metric("Home Win", o.get("home", "-"), o.get("home_delta", ""))
        safe_metric("Draw", o.get("draw", "-"), o.get("draw_delta", ""))
        safe_metric("Away Win", o.get("away", "-"), o.get("away_delta", ""))

    with odds_tabs[1]:
        o = odds.get("over_under", {})
        c1, c2, c3, c4 = st.columns(4)
        safe_metric("Over 0.5", o.get("o0_5", "-"), o.get("o0_5_delta", ""))
        safe_metric("Over 1.5", o.get("o1_5", "-"), o.get("o1_5_delta", ""))
        safe_metric("Over 2.5", o.get("o2_5", "-"), o.get("o2_5_delta", ""))
        safe_metric("Over 3.5", o.get("o3_5", "-"), o.get("o3_5_delta", ""))

    with odds_tabs[2]:
        o = odds.get("btts", {})
        c1, c2 = st.columns(2)
        safe_metric("BTTS Yes", o.get("yes", "-"), o.get("yes_prob", ""))
        safe_metric("BTTS No", o.get("no", "-"), o.get("no_prob", ""))

    with odds_tabs[3]:
        o = odds.get("cards", {})
        c1, c2, c3 = st.columns(3)
        safe_metric("Over 2.5 Cards", o.get("o2_5", "-"), o.get("o2_5_label", ""))
        safe_metric("Over 4.5 Cards", o.get("o4_5", "-"), o.get("o4_5_label", ""))
        safe_metric("Home More Cards", o.get("home_more", "-"), o.get("home_more_label", ""))

    with odds_tabs[4]:
        o = odds.get("corners", {})
        c1, c2, c3 = st.columns(3)
        safe_metric("Over 8.5", o.get("o8_5", "-"), o.get("o8_5_label", ""))
        safe_metric("Over 10.5", o.get("o10_5", "-"), o.get("o10_5_label", ""))
        safe_metric("Over 12.5", o.get("o12_5", "-"), o.get("o12_5_label", ""))

    with odds_tabs[5]:
        o = odds.get("asian_handicap", {})
        c1, c2, c3 = st.columns(3)
        safe_metric("Home -1.5", o.get("home_m1_5", "-"), o.get("home_m1_5_label", ""))
        safe_metric("Home -0.5", o.get("home_m0_5", "-"), o.get("home_m0_5_label", ""))
        safe_metric("Away +1.5", o.get("away_p1_5", "-"), o.get("away_p1_5_label", ""))

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ─── AI REASONING — LIVE DATA ONLY ───────────────────────────────────────
    st.markdown("##### 🧠 AI ANALYSIS REASONING")
    if prediction and hasattr(prediction, "reasoning") and prediction.reasoning:
        for reason in prediction.reasoning:
            st.markdown(f'<div style="padding:8px;margin:4px 0;background:rgba(212,175,55,0.05);border-left:3px solid #D4AF37;border-radius:0 6px 6px 0;color:#e6f1ff;">• {reason}</div>', unsafe_allow_html=True)
    else:
        st.info("AI reasoning unavailable. The prediction model did not return analysis text for this fixture.")

# ═══════════════════════════════════════════════════════════════════════════════
# ARENA — MAIN SPORT / LEAGUE / MATCH HUB
# ═══════════════════════════════════════════════════════════════════════════════
def render_arena():
    # If user selected a match, show analysis instead of list
    if "selected_match_id" in st.session_state:
        render_match_analysis_panel()
        return

    # ─── SIDEBAR CONTROLS ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#D4AF37;font-family:Orbitron;font-size:0.9rem;text-align:center;margin-bottom:10px;">🏟️ ARENA CONTROLS</div>', unsafe_allow_html=True)

        sport_names = list(SPORT_OPTIONS.keys())
        selected_sport = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_names,
            index=sport_names.index(st.session_state.get("sport_widget", "Soccer")),
            key="sport_widget",
            on_change=on_sport_change
        )

        sport_cfg = SPORT_OPTIONS[selected_sport]

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # ─── LEAGUE DROPDOWN — FETCH ALL GLOBAL LEAGUES FOR SPORT ──────────────
        league_cache_key = f"league_list_{selected_sport}"
        if league_cache_key not in st.session_state:
            with st.spinner("Fetching global leagues..."):
                # CRITICAL: pass sport TYPE string, NOT the dict
                raw_leagues = api_all_leagues(sport_cfg["sport_type"])
                if raw_leagues and len(raw_leagues) > 0:
                    opts = [("ALL", "🏆 All Leagues")]
                    for lg in raw_leagues:
                        name = lg.get("name", lg.get("strLeague", "Unknown"))
                        country = lg.get("country", lg.get("strCountry", ""))
                        lid = lg.get("id", lg.get("idLeague", "0"))
                        display = f"{name}" + (f" ({country})" if country else "")
                        opts.append((lid, display))
                    st.session_state[league_cache_key] = opts
                else:
                    st.session_state[league_cache_key] = [("ALL", "🏆 All Leagues")]

        league_options = st.session_state.get(league_cache_key, [("ALL", "🏆 All Leagues")])
        league_labels = [opt[1] for opt in league_options]
        league_ids = [opt[0] for opt in league_options]

        current_league = st.session_state.get(f"league_id_{selected_sport}", "ALL")
        try:
            li = league_ids.index(current_league)
        except ValueError:
            li = 0

        selected_label = st.selectbox(
            "🏆 SELECT LEAGUE",
            options=league_labels,
            index=li,
            key=f"league_select_{selected_sport}"
        )
        selected_league_id = league_ids[league_labels.index(selected_label)]
        st.session_state[f"league_id_{selected_sport}"] = selected_league_id

        # If we only have "All Leagues", warn user that API returned nothing
        if len(league_options) <= 1:
            st.markdown('<div style="color:#ff4444;font-size:0.75rem;text-align:center;margin:5px 0;">⚠️ API returned no leagues for this sport</div>', unsafe_allow_html=True)

        status_options = ["ALL", "LIVE", "SCHEDULED", "FINISHED"]
        selected_status = st.selectbox(
            "📊 MATCH STATUS",
            options=status_options,
            key=f"status_select_{selected_sport}"
        )

        if st.button("🔄 REFRESH DATA", use_container_width=True, key=f"refresh_{selected_sport}"):
            # Clear caches for this sport
            api_all_leagues.clear()
            api_live_matches.clear()
            api_upcoming_matches.clear()
            api_finished_matches.clear()
            st.session_state.pop(league_cache_key, None)
            st.session_state.last_refresh = time.time()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

    # ─── MAIN AREA: MATCH CARDS ──────────────────────────────────────────────
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {selected_sport.upper()}</div>', unsafe_allow_html=True)

    # Fetch matches based on status
    matches_df = pd.DataFrame()
    try:
        if selected_status == "LIVE":
            raw = api_live_matches(sport_cfg, selected_league_id)
            matches_df = filter_df_by_league(raw, selected_league_id, league_options)
        elif selected_status == "SCHEDULED":
            raw = api_upcoming_matches(sport_cfg)
            matches_df = filter_df_by_league(raw, selected_league_id, league_options)
        elif selected_status == "FINISHED":
            raw = api_finished_matches(sport_cfg, selected_league_id)
            matches_df = filter_df_by_league(raw, selected_league_id, league_options)
        else:  # ALL
            live_raw = api_live_matches(sport_cfg, selected_league_id)
            sched_raw = api_upcoming_matches(sport_cfg)
            live_df = filter_df_by_league(live_raw, selected_league_id, league_options)
            sched_df = filter_df_by_league(sched_raw, selected_league_id, league_options)
            if not live_df.empty and not sched_df.empty:
                matches_df = pd.concat([live_df, sched_df], ignore_index=True)
            elif not live_df.empty:
                matches_df = live_df
            else:
                matches_df = sched_df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)[:120]}")

    render_arena_match_list(matches_df, selected_sport, selected_league_id, league_options, selected_status)

# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS & ANALYTICS (PLACEHOLDER SHELLS)
# ═══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🔮 UPCOMING", "📜 HISTORY", "⚙️ CALIBRATION"])

    with t1:
        try:
            df = api_upcoming_matches(SPORT_OPTIONS[st.session_state.get("sport_widget", "Soccer")])
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("🔮 No upcoming predictions available from API.")
        except Exception:
            st.info("🔮 No upcoming predictions available from API.")

    with t2:
        st.info("📜 Prediction history requires database integration.")
        st.dataframe(pd.DataFrame(columns=["DATE", "MATCH", "PREDICTED", "RESULT", "P/L"]), use_container_width=True, hide_index=True)

    with t3:
        st.info("⚙️ Model calibration analysis.")
        st.dataframe(pd.DataFrame(columns=["BIN", "PREDICTED", "ACTUAL", "BETS"]), use_container_width=True, hide_index=True)

def render_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)
    st.info("📊 Performance analytics require database integration.")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    render_header()
    render_sidebar()
    render_live_ticker()

    # Manual refresh only — no 15s auto-hammer
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🔄 FORCE REFRESH", use_container_width=True):
            api_all_leagues.clear()
            api_live_matches.clear()
            api_upcoming_matches.clear()
            api_finished_matches.clear()
            api_match_details.clear()
            api_match_prediction.clear()
            st.session_state.last_refresh = time.time()
            st.rerun()

    with c2:
        elapsed = time.time() - st.session_state.last_refresh
        status_color = "#00ff88" if data.is_live else "#FFD700"
        status_text = "LIVE" if data.is_live else "DEMO"
        st.markdown(
            f'<div style="color:{status_color};font-family:Orbitron;font-size:0.8rem;padding-top:8px;">'
            f'● {status_text} | Last refresh {int(elapsed)}s ago</div>',
            unsafe_allow_html=True
        )

    page = st.radio("", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"], horizontal=True, label_visibility="collapsed")

    if "ARENA" in page:
        render_arena()
    elif "PREDICTIONS" in page:
        render_predictions()
    else:
        render_analytics()
