"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
World-Class Professional Command Center
24/7 AI Engine | Real-Time Global Sports Intelligence | Claude-Powered Predictions
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
import requests

from empire_data_layer import EmpireDashboardData, APIConfig
from empire_ai_engine  import (
    EmpireAIEngine, MatchPrediction, BulkScanResult,
    confidence_color, confidence_bar_html, probability_donut_html,
    HIGH_CONF, MEDIUM_CONF,
)

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON SERVICES
# ══════════════════════════════════════════════════════════════════════════════
if "empire_data" not in st.session_state:
    st.session_state.empire_data = EmpireDashboardData()
if "empire_ai" not in st.session_state:
    st.session_state.empire_ai = EmpireAIEngine()

data: EmpireDashboardData = st.session_state.empire_data
ai:   EmpireAIEngine      = st.session_state.empire_ai

REFRESH_INTERVAL = 30

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def test_api_sports_live():
    """Direct test of API-SPORTS for live matches"""
    st.markdown("### 🔴 LIVE MATCHES DIAGNOSTIC")
    st.markdown("---")
    
    api_key = os.environ.get("API_SPORTS_KEY")
    if not api_key:
        st.error("❌ API_SPORTS_KEY not found in environment variables")
        return
    
    st.success(f"✅ API_SPORTS_KEY found (length: {len(api_key)})")
    
    headers = {"x-apisports-key": api_key}
    
    st.markdown("### 📡 API Connection")
    try:
        response = requests.get("https://v3.football.api-sports.io/status", headers=headers, timeout=10)
        if response.status_code == 200:
            st.success("✅ API connection successful!")
        else:
            st.error(f"❌ API connection failed: HTTP {response.status_code}")
            return
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
        return
    
    st.markdown("### 🏃 Live Fixtures")
    try:
        response = requests.get("https://v3.football.api-sports.io/fixtures", headers=headers, params={"live": "all"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            live_matches = data.get("response", [])
            if live_matches:
                st.success(f"✅ Found {len(live_matches)} LIVE matches!")
                for match in live_matches:
                    league = match.get("league", {}).get("name", "?")
                    home = match.get("teams", {}).get("home", {}).get("name", "?")
                    away = match.get("teams", {}).get("away", {}).get("name", "?")
                    st.write(f"• **{league}**: {home} vs {away}")
            else:
                st.warning("No live matches found at this moment")
        else:
            st.error(f"Failed: HTTP {response.status_code}")
    except Exception as e:
        st.error(f"Error: {str(e)}")


def test_api_sports_upcoming():
    """Test API-SPORTS for upcoming matches"""
    st.markdown("### 📋 UPCOMING MATCHES DIAGNOSTIC")
    st.markdown("---")
    
    api_key = os.environ.get("API_SPORTS_KEY")
    if not api_key:
        st.error("❌ API_SPORTS_KEY not found")
        return
    
    headers = {"x-apisports-key": api_key}
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    try:
        response = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"from": today, "to": next_week},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("response", [])
            if fixtures:
                st.success(f"✅ Found {len(fixtures)} upcoming matches")
            else:
                st.warning("No upcoming matches found")
        else:
            st.error(f"Failed: HTTP {response.status_code}")
    except Exception as e:
        st.error(f"Error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');
.stApp{background:linear-gradient(180deg,#0a0a0f 0%,#12121a 50%,#0d0d14 100%);font-family:'Rajdhani',sans-serif;}
.logo-center{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:8px 0 4px;width:100%;}
.logo-img{width:90%;height:auto;max-height:180px;object-fit:contain;display:block;margin:0 auto;}
.tagline-bold{font-family:'Orbitron',sans-serif;font-size:1.4rem;font-weight:900;background:linear-gradient(135deg,#D4AF37 0%,#FFD700 50%,#B8860B 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;letter-spacing:4px;text-transform:uppercase;margin-top:6px;margin-bottom:2px;}
.tagline-sub{font-family:'Rajdhani',sans-serif;font-size:.9rem;color:#888;text-align:center;letter-spacing:6px;text-transform:uppercase;margin-top:2px;margin-bottom:8px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0f0f1a 0%,#1a1a2e 100%);border-right:3px solid #D4AF37;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#D4AF37 !important;font-family:'Orbitron',sans-serif;font-weight:700;letter-spacing:2px;}
.ai-status{background:linear-gradient(135deg,#00ff88 0%,#00cc6a 100%);color:#000;font-family:'Orbitron',sans-serif;font-weight:900;font-size:.8rem;padding:8px 16px;border-radius:20px;text-align:center;letter-spacing:3px;text-transform:uppercase;box-shadow:0 0 15px rgba(0,255,136,.4);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{box-shadow:0 0 15px rgba(0,255,136,.4);}50%{box-shadow:0 0 25px rgba(0,255,136,.8);}}
.section-header{font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:700;color:#FFD700;letter-spacing:2px;text-transform:uppercase;padding:15px 20px;background:linear-gradient(90deg,rgba(212,175,55,.2) 0%,transparent 100%);border-left:4px solid #D4AF37;border-radius:0 8px 8px 0;margin:20px 0 10px;}
.gold-divider{border:none;height:2px;background:linear-gradient(90deg,transparent 0%,#D4AF37 50%,transparent 100%);margin:20px 0;}
.stat-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2a2a3e;font-family:'Rajdhani',sans-serif;font-size:.95rem;}
.stat-label{color:#888;}.stat-value{color:#FFD700;font-weight:700;}
.world-clock{font-family:'Orbitron',sans-serif;font-size:.9rem;color:#D4AF37;text-align:center;letter-spacing:2px;padding:10px;background:rgba(212,175,55,.1);border-radius:8px;margin:10px 0;}
.ticker{background:linear-gradient(90deg,#1a1a2e 0%,#16213e 100%);border-top:2px solid #D4AF37;border-bottom:2px solid #D4AF37;padding:10px;overflow:hidden;white-space:nowrap;}
.ticker-text{font-family:'Rajdhani',sans-serif;color:#FFD700;font-size:.9rem;letter-spacing:2px;animation:scroll 30s linear infinite;display:inline-block;}
@keyframes scroll{0%{transform:translateX(100vw);}100%{transform:translateX(-100%);}}
.stButton>button{background:linear-gradient(135deg,#D4AF37 0%,#FFD700 100%);color:#000;font-family:'Orbitron',sans-serif;font-weight:700;border:none;border-radius:8px;padding:.6rem 2rem;letter-spacing:2px;text-transform:uppercase;transition:all .3s ease;}
.stButton>button:hover{background:linear-gradient(135deg,#FFD700 0%,#FFF8DC 100%);box-shadow:0 0 25px rgba(212,175,55,.6);transform:scale(1.05);}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:rgba(26,26,46,.5);border-radius:10px;padding:5px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#888;font-family:'Orbitron',sans-serif;font-weight:500;letter-spacing:1px;border-radius:6px;padding:.5rem 1.5rem;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#D4AF37 0%,#FFD700 100%) !important;color:#000 !important;font-weight:700;}
::-webkit-scrollbar{width:8px;}::-webkit-scrollbar-track{background:#0a0a0f;}::-webkit-scrollbar-thumb{background:linear-gradient(180deg,#D4AF37 0%,#B8860B 100%);border-radius:4px;}
[data-testid="stMetricValue"]{color:#FFD700 !important;font-family:'Orbitron',sans-serif;font-weight:900;font-size:2rem;}
[data-testid="stMetricLabel"]{color:#888 !important;font-family:'Rajdhani',sans-serif;font-weight:500;letter-spacing:2px;text-transform:uppercase;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIG
# ══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Football":     {"icon": "⚽",  "provider": "Football-Data.org (Free)"},
    "NBA":          {"icon": "🏀",  "provider": "MySportsFeeds (Free)"},
    "NFL":          {"icon": "🏈",  "provider": "MySportsFeeds (Free)"},
    "MLB":          {"icon": "⚾",  "provider": "MySportsFeeds (Free)"},
    "NHL":          {"icon": "🏒",  "provider": "MySportsFeeds (Free)"},
    "UFC":          {"icon": "🥊",  "provider": "TheSportsDB (Free)"},
    "Formula 1":    {"icon": "🏎️", "provider": "TheSportsDB (Free)"},
    "Tennis":       {"icon": "🎾",  "provider": "TheSportsDB (Free)"},
    "Cricket":      {"icon": "🏏",  "provider": "TheSportsDB (Free)"},
    "Golf":         {"icon": "⛳",  "provider": "TheSportsDB (Free)"},
}
STATUS_OPTIONS = ["ALL", "LIVE", "UPCOMING", "FINISHED"]
SPORT_NAMES    = list(SPORT_OPTIONS.keys())


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
def _init_state():
    for k, v in {
        "selected_sport":     SPORT_NAMES[0],
        "selected_league_id": "ALL",
        "selected_status":    "UPCOMING",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ══════════════════════════════════════════════════════════════════════════════
# CACHE CLEAR
# ══════════════════════════════════════════════════════════════════════════════
def _clear_all_caches():
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    logo_path = Path("BRAND_ASSET/empire_logo_primary.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="EMPIRE">'
    else:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 120">'
            '<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">'
            '<stop offset="0%" style="stop-color:#D4AF37"/>'
            '<stop offset="100%" style="stop-color:#FFD700"/></linearGradient></defs>'
            '<rect width="900" height="120" rx="10" fill="#16213e" stroke="#D4AF37" stroke-width="2"/>'
            '<text x="450" y="72" font-family="Impact,Arial Black,sans-serif" font-size="48" '
            'fill="url(#g)" text-anchor="middle" letter-spacing="6">EMPIRE SPORT INSTINCTS ARENA</text>'
            '<text x="450" y="100" font-family="Arial,sans-serif" font-size="14" '
            'fill="#888" text-anchor="middle" letter-spacing="10">ELITE AI PREDICTION DASHBOARD v4.0</text></svg>'
        )
        logo_html = f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" class="logo-img">'

    st.markdown(f'<div class="logo-center">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Claude AI Prediction Engine | Real-Time Intelligence | Where Instinct Meets Data</div>', unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        ai_label = "🤖 AI ENGINE ONLINE" if ai.available else "⚠️ AI ENGINE OFFLINE"
        st.markdown(f'<div class="ai-status">{ai_label}</div>', unsafe_allow_html=True)

    now = datetime.utcnow()
    cities = [("LONDON", now+timedelta(hours=1)), ("NEW YORK", now-timedelta(hours=5)),
              ("TOKYO",  now+timedelta(hours=9)), ("SYDNEY",   now+timedelta(hours=10)),
              ("LAGOS",  now+timedelta(hours=1))]
    clock = " | ".join(f"{c}: {dt.strftime('%H:%M')}" for c, dt in cities)
    st.markdown(f'<div class="world-clock">🌍 {clock}</div>', unsafe_allow_html=True)

    live_color = "#00ff88" if data.is_live else "#FFD700"
    live_text  = "LIVE MODE — Free APIs Active" if data.is_live else "⚠️ API Configuration Needed"
    ai_color   = "#00ff88" if ai.available else "#ff6b6b"
    ai_text    = "Claude AI Active" if ai.available else "Set ANTHROPIC_API_KEY in Render"
    st.markdown(
        f'<div style="display:flex;gap:12px;margin:10px 0;">'
        f'<div style="flex:1;background:rgba(0,0,0,.3);border:1px solid {live_color};'
        f'border-radius:8px;padding:10px;text-align:center;font-family:Orbitron;'
        f'font-size:.85rem;font-weight:700;color:{live_color};">🟢 {live_text}</div>'
        f'<div style="flex:1;background:rgba(0,0,0,.3);border:1px solid {ai_color};'
        f'border-radius:8px;padding:10px;text-align:center;font-family:Orbitron;'
        f'font-size:.85rem;font-weight:700;color:{ai_color};">🧠 {ai_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    with st.sidebar:
        st.markdown("### ⚡ SYSTEM STATUS")
        for s in data.router.get_provider_status():
            st.markdown(f"- {s['name']}: {s['status']}")
        
        st.markdown("---")
        st.markdown("### 🔬 QUICK DIAGNOSTICS")
        
        if st.button("🔴 TEST LIVE MATCHES", use_container_width=True):
            test_api_sports_live()
        if st.button("📋 TEST UPCOMING MATCHES", use_container_width=True):
            test_api_sports_upcoming()
        if st.button("🔑 CHECK API KEY", use_container_width=True):
            api_key = os.environ.get("API_SPORTS_KEY")
            if api_key:
                st.success(f"✅ API_SPORTS_KEY is set")
            else:
                st.error("❌ API_SPORTS_KEY not found")
        
        st.markdown("---")
        st.markdown("### 🏟️ ARENA CONTROLS")
        
        sport_labels = [f"{SPORT_OPTIONS[s]['icon']} {s}" for s in SPORT_NAMES]
        prev_sport = st.session_state.selected_sport
        sport_choice = st.selectbox("🎯 SELECT SPORT", options=sport_labels, index=SPORT_NAMES.index(prev_sport))
        chosen_sport = SPORT_NAMES[sport_labels.index(sport_choice)]
        if chosen_sport != prev_sport:
            st.session_state.selected_sport = chosen_sport
            st.session_state.selected_league_id = "ALL"
            st.session_state.selected_status = "ALL"
            st.rerun()
        
        status_choice = st.selectbox("📊 MATCH STATUS", options=STATUS_OPTIONS, index=STATUS_OPTIONS.index(st.session_state.selected_status))
        st.session_state.selected_status = status_choice
        
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            _clear_all_caches()
            st.rerun()
        
        st.markdown("---")
        st.subheader("📡 API LOG")
        try:
            log_df = data.get_connection_log_df()
            if not log_df.empty:
                st.dataframe(log_df, use_container_width=True, hide_index=True, height=180)
            else:
                st.caption("No log entries yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {e}")

    return (
        st.session_state.selected_sport,
        st.session_state.selected_league_id,
        st.session_state.selected_status,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_ticker():
    st.markdown(
        '<div class="ticker"><div class="ticker-text">'
        '🧠 CLAUDE AI ACTIVE — GENERATING PREDICTIONS IN REAL TIME &nbsp;·&nbsp; '
        '⚽ Football (Free API) &nbsp;·&nbsp; 🏀 NBA &nbsp;·&nbsp; 🏈 NFL &nbsp;·&nbsp; '
        '⚾ MLB &nbsp;·&nbsp; 🏒 NHL &nbsp;·&nbsp; 🥊 UFC &nbsp;·&nbsp; 🏎️ F1 &nbsp;·&nbsp; 🎾 Tennis &nbsp;·&nbsp; 🏏 Cricket &nbsp;·&nbsp; ⛳ Golf'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:
        return "#00FF88", "rgba(0,255,136,.15)", "● LIVE"
    if any(x in su for x in ("FINISH","FT","FINAL","COMPLETED")):
        return "#888", "rgba(136,136,136,.15)", "FINISHED"
    return "#FFAA00", "rgba(255,170,0,.15)", "UPCOMING"


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_upcoming(_data_key: str, sport: str) -> pd.DataFrame:
    try:
        return st.session_state.empire_data.get_upcoming_matches_df(sport)
    except Exception as e:
        logger.error(f"_fetch_upcoming: {e}")
        return pd.DataFrame()


def _fetch_matches(sport: str, league_id: str, status: str) -> pd.DataFrame:
    upcoming_key = str(int(time.time() // 300))
    try:
        if status in ("UPCOMING", "SCHEDULED", "ALL"):
            df = _fetch_upcoming(upcoming_key, sport)
        else:
            df = pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"_fetch_matches: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTION CARD RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def render_prediction_card(pred: MatchPrediction):
    card_class = (
        "pred-card pred-card-high"   if pred.confidence >= HIGH_CONF   else
        "pred-card pred-card-medium" if pred.confidence >= MEDIUM_CONF else
        "pred-card pred-card-low"
    )
    color = confidence_color(pred.confidence)
    bar = confidence_bar_html(pred.confidence, 180)
    donut = probability_donut_html(
        pred.home_win_pct, pred.draw_pct, pred.away_win_pct,
        pred.home_team, pred.away_team,
    )
    
    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"**{pred.league}**")
        st.markdown(f"### {pred.home_team} vs {pred.away_team}")
        st.markdown(f"**Recommended Bet:** {pred.recommended_bet}")
        st.markdown(f"*Generated: {pred.generated_at[11:16]}*")
    with col2:
        st.markdown(donut, unsafe_allow_html=True)
    
    st.markdown(f"**Confidence:** {bar} {pred.confidence}% {pred.confidence_label}")
    
    if pred.ai_summary:
        st.markdown(f"💬 {pred.ai_summary}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ KEY FACTORS**")
        for factor in pred.key_factors[:4]:
            st.markdown(f"- {factor}")
    with col2:
        st.markdown("**⚠️ RISK FACTORS**")
        for risk in pred.risk_factors[:3]:
            st.markdown(f"- {risk}")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MATCH CARDS - CORRECTED VERSION (NO HARDCODED DATA)
# ══════════════════════════════════════════════════════════════════════════════
def render_match_cards(matches_df: pd.DataFrame, sport: str):
    if matches_df is None or matches_df.empty:
        st.warning(f"⚠️ **No {sport} matches found**\n\nTry changing the status filter or refreshing data.")
        return

    st.markdown(f"📊 **{len(matches_df)} matches found**")
    
    for idx, row in matches_df.iterrows():
        home = row.get("HOME_TEAM", "TBD")
        away = row.get("AWAY_TEAM", "TBD")
        score = row.get("SCORE", "vs")
        league = row.get("LEAGUE", "")
        match_time = row.get("TIME", "")
        match_id = row.get("MATCH_ID", str(idx))
        status_raw = row.get("STATUS", "UPCOMING")
        
        color, bg, label = _status_style(status_raw)
        
        # Build match card HTML as a SINGLE properly formatted string
        card_html = f'''
        <div style="background:linear-gradient(135deg,rgba(20,25,40,.9),rgba(10,15,30,.95)); border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:16px; margin:8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="color:#8892b0; font-size:.75rem; font-family:Rajdhani;">{league}</span>
                <span style="color:{color}; background:{bg}; padding:2px 10px; border-radius:10px; font-size:.7rem; font-weight:700; font-family:Orbitron;">{label}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1; text-align:left;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600; font-family:Rajdhani;">{home}</div>
                </div>
                <div style="padding:0 20px; text-align:center;">
                    <div style="color:#00d4ff; font-size:1.4rem; font-weight:700; letter-spacing:2px; font-family:Orbitron;">{score}</div>
                    <div style="color:#8892b0; font-size:.65rem; margin-top:2px;">{match_time}</div>
                </div>
                <div style="flex:1; text-align:right;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600; font-family:Rajdhani;">{away}</div>
                </div>
            </div>
        </div>
        '''
        
        st.markdown(card_html, unsafe_allow_html=True)
        
        col1, col2 = st.columns([7, 1])
        with col1:
            if st.button(f"🧠 AI PREDICT", key=f"predict_{sport}_{match_id}_{idx}", use_container_width=True):
                st.session_state.selected_match_id = match_id
                st.session_state.selected_match_row = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.session_state.selected_match_sport = sport
                st.rerun()
        with col2:
            if st.button(f"🔍", key=f"view_{sport}_{match_id}_{idx}", use_container_width=True):
                st.session_state.selected_match_id = match_id
                st.session_state.selected_match_row = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.session_state.selected_match_sport = sport
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MATCH DETAIL + AI PREDICTION PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_detail():
    match_id = st.session_state.get("selected_match_id", "")
    match_row = st.session_state.get("selected_match_row", {})
    home = st.session_state.get("selected_match_home", "Home")
    away = st.session_state.get("selected_match_away", "Away")
    sport = st.session_state.get("selected_match_sport", st.session_state.selected_sport)

    st.markdown(f'<div class="section-header">🧠 AI ANALYSIS — {home} vs {away}</div>', unsafe_allow_html=True)

    if st.button("← Back to Match List"):
        for k in ("selected_match_id", "selected_match_row", "selected_match_home", "selected_match_away", "selected_match_sport"):
            st.session_state.pop(k, None)
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📋 MATCH INFORMATION")
        for label, key in [("League", "LEAGUE"), ("Status", "STATUS"), ("Time", "TIME"), ("Score", "SCORE"), ("Provider", "PROVIDER")]:
            val = match_row.get(key, "N/A")
            st.markdown(f"**{label}:** {val}")
    
    with col2:
        score_val = match_row.get("SCORE", "vs")
        st.markdown(f"<div style='text-align:center; padding:20px;'><div style='font-family:Orbitron; font-size:2.5rem; color:#FFD700; font-weight:900;'>{score_val}</div><div>{home} vs {away}</div></div>", unsafe_allow_html=True)

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    if not ai.available:
        st.error("🔴 ANTHROPIC_API_KEY not set. Add it in Render environment variables.")
        return

    cached = ai.cache.get(match_id, sport)
    force = st.button("🔄 Regenerate Prediction", key=f"regen_{match_id}")

    if cached and not force:
        pred = cached
        st.caption(f"⚡ From cache — generated at {pred.generated_at[11:16]}")
    else:
        with st.spinner("🧠 Claude AI analysing match..."):
            pred = ai.predict_match(match_row, sport, force=force)

    render_prediction_card(pred)


# ══════════════════════════════════════════════════════════════════════════════
# ARENA
# ══════════════════════════════════════════════════════════════════════════════
def render_arena(sport: str, league_id: str, status: str):
    if "selected_match_id" in st.session_state:
        render_match_detail()
        return

    icon = SPORT_OPTIONS.get(sport, {}).get("icon", "🏆")
    st.markdown(f'<div class="section-header">{icon} EMPIRE ARENA — {sport.upper()}</div>', unsafe_allow_html=True)

    with st.spinner(f"📡 Fetching {sport} matches..."):
        df = _fetch_matches(sport, league_id, status)

    render_match_cards(df, sport)


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS TAB
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions(sport: str, league_id: str, status: str):
    st.markdown('<div class="section-header">🎯 AI PREDICTION CENTER</div>', unsafe_allow_html=True)

    if not ai.available:
        st.error("🔴 ANTHROPIC_API_KEY not configured.")
        return

    stats = ai.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("AI CALLS", stats["api_calls"])
    col2.metric("CACHED PREDS", stats["cache_active"])
    col3.metric("ERRORS", stats["errors"])
    col4.metric("MODEL", "Sonnet 4")

    df = _fetch_matches(sport, league_id, status)

    if df.empty:
        st.info("No matches to analyse. Select a sport and ensure the status filter includes upcoming matches.")
        return

    if st.button("⚡ RUN AI BATCH SCANNER", use_container_width=True):
        with st.spinner("🧠 Claude AI scanning all matches for value..."):
            result = ai.scan_matches(df, sport)
            if result and result.high_conf_picks:
                for pick in result.high_conf_picks[:5]:
                    st.markdown(f"**{pick.get('home_team')} vs {pick.get('away_team')}** - {pick.get('confidence')}% confidence")
                    st.markdown(f"*{pick.get('one_line_reason')}*")
                    st.markdown("---")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown("### 🔍 INDIVIDUAL MATCH ANALYSIS")

    for idx, row in df.head(10).iterrows():
        home = row.get("HOME_TEAM", "TBD")
        away = row.get("AWAY_TEAM", "TBD")
        league = row.get("LEAGUE", "")
        match_id = row.get("MATCH_ID", str(idx))
        mtime = row.get("TIME", "")

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**{home} vs {away}** - {league} | {mtime}")
        with col2:
            if st.button("🧠 Predict", key=f"pred_tab_{match_id}_{idx}"):
                with st.spinner(f"Analysing {home} vs {away}..."):
                    pred = ai.predict_match(row.to_dict(), sport)
                    render_prediction_card(pred)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 AI PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)

    stats = ai.get_stats()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("TOTAL AI CALLS", stats["api_calls"])
    col2.metric("CACHED PREDS", stats["cache_active"])
    col3.metric("PREDICTION LOG", stats["predictions"])
    col4.metric("ERRORS", stats["errors"])
    col5.metric("ENGINE", "Claude Sonnet")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    pred_log = ai.get_prediction_log()
    if pred_log:
        log_df = pd.DataFrame(pred_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No predictions generated yet.")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown("### ⚡ DATA PROVIDER STATUS")
    for s in data.router.get_provider_status():
        st.markdown(f"- {s['name']}: {s['status']}")


# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
def render_top_bar():
    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= REFRESH_INTERVAL:
        _clear_all_caches()
        st.rerun()
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 FORCE REFRESH", use_container_width=True):
            _clear_all_caches()
            st.rerun()
    with col2:
        st.markdown(f"● Auto-refresh in {int(max(0, REFRESH_INTERVAL - elapsed))}s | AI: {'🧠 READY' if ai.available else '⚠️ OFFLINE'}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
render_header()
selected_sport, selected_league_id, selected_status = render_sidebar()
render_ticker()
render_top_bar()

page = st.radio("", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"], horizontal=True, label_visibility="collapsed")

if "ARENA" in page:
    render_arena(selected_sport, selected_league_id, selected_status)
elif "PREDICTIONS" in page:
    render_predictions(selected_sport, selected_league_id, selected_status)
else:
    render_analytics()
