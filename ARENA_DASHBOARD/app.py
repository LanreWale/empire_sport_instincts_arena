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
[data-testid="stDataFrame"] [role="columnheader"],[data-testid="stDataFrame"] th{background:linear-gradient(135deg,#D4AF37 0%,#B8860B 100%) !important;color:#000 !important;font-family:'Orbitron',sans-serif !important;font-weight:900 !important;font-size:.85rem !important;text-transform:uppercase !important;letter-spacing:1.5px !important;border-bottom:3px solid #FFD700 !important;padding:14px 12px !important;text-align:center !important;}
[data-testid="stDataFrame"] [role="gridcell"],[data-testid="stDataFrame"] td{background-color:#1a1a2e !important;color:#FFD700 !important;font-family:'Rajdhani',sans-serif !important;font-weight:500 !important;font-size:.95rem !important;border-bottom:1px solid #2a2a3e !important;padding:10px 12px !important;text-align:center !important;}
[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"]{background-color:#151525 !important;}
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"]{background:rgba(212,175,55,.2) !important;color:#FFF !important;font-weight:700 !important;}
.section-header{font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:700;color:#FFD700;letter-spacing:2px;text-transform:uppercase;padding:15px 20px;background:linear-gradient(90deg,rgba(212,175,55,.2) 0%,transparent 100%);border-left:4px solid #D4AF37;border-radius:0 8px 8px 0;margin:20px 0 10px;}
.pred-card{background:linear-gradient(135deg,rgba(15,20,35,.95),rgba(8,12,25,.98));border:1px solid rgba(212,175,55,.3);border-radius:14px;padding:20px;margin:10px 0;transition:all .3s ease;}
.pred-card:hover{border-color:#D4AF37;box-shadow:0 0 25px rgba(212,175,55,.25);transform:translateY(-2px);}
.pred-card-high{border-color:#00ff88 !important;box-shadow:0 0 20px rgba(0,255,136,.2);}
.pred-card-medium{border-color:#FFD700 !important;}
.pred-card-low{border-color:#ff6b6b !important;opacity:.7;}
.bet-badge{display:inline-block;background:linear-gradient(135deg,#D4AF37,#FFD700);color:#000;font-family:'Orbitron',sans-serif;font-size:.75rem;font-weight:900;padding:6px 14px;border-radius:20px;letter-spacing:2px;text-transform:uppercase;}
.value-badge{display:inline-block;background:rgba(0,255,136,.15);border:1px solid #00ff88;color:#00ff88;font-family:'Orbitron',sans-serif;font-size:.7rem;padding:4px 10px;border-radius:12px;margin-left:8px;}
.factor-item{color:#ccd6f6;font-family:'Rajdhani',sans-serif;font-size:.9rem;padding:3px 0;border-left:2px solid #D4AF37;padding-left:10px;margin:4px 0;}
.risk-item{color:#ff6b6b;font-family:'Rajdhani',sans-serif;font-size:.85rem;padding:3px 0;border-left:2px solid #ff6b6b;padding-left:10px;margin:4px 0;}
.ai-narrative{background:rgba(212,175,55,.08);border-radius:8px;padding:14px;font-family:'Rajdhani',sans-serif;font-size:1rem;color:#e6f1ff;line-height:1.6;border-left:3px solid #D4AF37;margin:12px 0;}
.scan-pick{background:linear-gradient(135deg,rgba(0,255,136,.08),rgba(0,204,106,.05));border:1px solid rgba(0,255,136,.3);border-radius:10px;padding:14px;margin:8px 0;}
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
    # ── Legacy providers (+ FlashScore overlay when Apify key active)
    "Soccer":       {"icon": "⚽",  "provider": "FlashScore/API-SPORTS"},
    "NBA":          {"icon": "🏀",  "provider": "FlashScore/MySportsFeeds"},
    "NFL":          {"icon": "🏈",  "provider": "FlashScore/MySportsFeeds"},
    "MLB":          {"icon": "⚾",  "provider": "FlashScore/MySportsFeeds"},
    "NHL":          {"icon": "🏒",  "provider": "FlashScore/MySportsFeeds"},
    "UFC":          {"icon": "🥊",  "provider": "FlashScore/TheSportsDB"},
    "Formula 1":    {"icon": "🏎️", "provider": "FlashScore/TheSportsDB"},
    "Tennis":       {"icon": "🎾",  "provider": "FlashScore/TheSportsDB"},
    "Cricket":      {"icon": "🏏",  "provider": "FlashScore/TheSportsDB"},
    "Golf":         {"icon": "⛳",  "provider": "FlashScore/TheSportsDB"},
    # ── FlashScore-native (daily global coverage)
    "Volleyball":   {"icon": "🏐",  "provider": "FlashScore"},
    "Handball":     {"icon": "🤾",  "provider": "FlashScore"},
    "Rugby":        {"icon": "🏉",  "provider": "FlashScore"},
    "Darts":        {"icon": "🎯",  "provider": "FlashScore"},
    "Snooker":      {"icon": "🎱",  "provider": "FlashScore"},
    "Table Tennis": {"icon": "🏓",  "provider": "FlashScore"},
    "Esports":      {"icon": "🎮",  "provider": "FlashScore"},
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
    # Clear Streamlit's function cache
    st.cache_data.clear()
    # Clear provider in-memory caches
    for provider in [data.router.api_sports,
                     data.router.my_sports_feeds,
                     data.router.the_sports_db,
                     data.router.flashscore]:
        provider.cache.clear()


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
            'fill="url(#g)" text-anchor="middle" letter-spacing="6">'
            'EMPIRE SPORT INSTINCTS ARENA</text>'
            '<text x="450" y="100" font-family="Arial,sans-serif" font-size="14" '
            'fill="#888" text-anchor="middle" letter-spacing="10">'
            'ELITE AI PREDICTION DASHBOARD v4.0</text></svg>'
        )
        logo_html = f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" class="logo-img">'

    st.markdown(f'<div class="logo-center">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tagline-sub">Claude AI Prediction Engine | Real-Time Intelligence | Where Instinct Meets Data</div>',
        unsafe_allow_html=True,
    )
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
    live_text  = "LIVE MODE — APIs Connected" if data.is_live else "⚠️ API Keys Not Detected"
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
        sb_logo = Path("BRAND_ASSET/empire_logo_arena.png")
        if sb_logo.exists():
            with open(sb_logo, "rb") as f:
                sb_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<div style="text-align:center;margin-bottom:10px;">'
                f'<img src="data:image/png;base64,{sb_b64}" '
                f'style="width:85%;max-height:100px;object-fit:contain;display:block;margin:0 auto;"></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center;color:#D4AF37;font-family:Orbitron;'
                'font-size:16px;font-weight:900;margin-bottom:10px;letter-spacing:4px;">⚡ EMPIRE</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<h2 style="text-align:center;font-size:1.1rem;margin-top:0;">COMMAND CENTER</h2>',
                    unsafe_allow_html=True)

        # AI engine status pill
        ai_col  = "#00ff88" if ai.available else "#ff6b6b"
        ai_stat = "● CLAUDE ONLINE" if ai.available else "● CLAUDE OFFLINE"
        ai_sub  = f"Calls: {ai.get_stats()['api_calls']} | Cache: {ai.get_stats()['cache_active']}"
        st.markdown(
            f'<div style="background:rgba(0,255,136,.1);border:1px solid {ai_col};'
            f'border-radius:8px;padding:10px;margin:10px 0;text-align:center;">'
            f'<div style="color:{ai_col};font-family:Orbitron;font-size:.75rem;">'
            f'🤖 INSTINCT BOT v4.0<br>'
            f'<span style="color:#888;font-size:.7rem;">CLAUDE AI PREDICTION ENGINE</span><br>'
            f'<span style="color:{ai_col};">{ai_stat}</span><br>'
            f'<span style="color:#555;font-size:.65rem;">{ai_sub}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Provider status
        st.subheader("⚡ SYSTEM STATUS")
        st.markdown('<div style="background:rgba(0,0,0,.3);border-radius:8px;padding:10px;margin:8px 0;">',
                    unsafe_allow_html=True)
        for s in data.router.get_provider_status():
            color = "#00ff88" if "ONLINE" in s["status"] else "#888"
            st.markdown(
                f'<div style="font-family:Orbitron;font-size:.65rem;color:{color};padding:2px 0;">'
                f'{s["name"]}: {s["status"]}</div>',
                unsafe_allow_html=True,
            )
        # Claude AI status
        ai_c = "#00ff88" if ai.available else "#ff6b6b"
        ai_s = "🟢 ONLINE" if ai.available else "🔴 KEY MISSING"
        st.markdown(
            f'<div style="font-family:Orbitron;font-size:.65rem;color:{ai_c};padding:2px 0;">'
            f'Claude AI: {ai_s}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # ── Arena controls ────────────────────────────────────────────────────
        st.markdown(
            '<div style="color:#D4AF37;font-family:Orbitron;font-size:.85rem;'
            'text-align:center;margin-bottom:8px;">🏟️ ARENA CONTROLS</div>',
            unsafe_allow_html=True,
        )

        sport_labels = [f"{SPORT_OPTIONS[s]['icon']} {s}" for s in SPORT_NAMES]
        prev_sport   = st.session_state.selected_sport

        sport_choice = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_labels,
            index=SPORT_NAMES.index(prev_sport),
            key="sport_selectbox",
        )
        chosen_sport = SPORT_NAMES[sport_labels.index(sport_choice)]

        if chosen_sport != prev_sport:
            st.session_state.selected_sport     = chosen_sport
            st.session_state.selected_league_id = "ALL"
            st.session_state.selected_status    = "ALL"
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:6px 0;'>", unsafe_allow_html=True)

        # League selector
        raw_leagues   = data.get_all_leagues(st.session_state.selected_sport)
        league_ids    = ["ALL"]
        league_labels = [f"🏆 All {st.session_state.selected_sport} — All Events"]
        for lg in raw_leagues:
            lid   = str(lg.get("id", "ALL"))
            lname = lg.get("name", "Unknown")
            lctry = lg.get("country", "")
            league_ids.append(lid)
            league_labels.append(f"{lname} ({lctry})" if lctry else lname)

        if st.session_state.selected_league_id not in league_ids:
            st.session_state.selected_league_id = "ALL"

        league_choice = st.selectbox(
            "🏆 SELECT LEAGUE / TEAM",
            options=league_labels,
            index=league_ids.index(st.session_state.selected_league_id),
            key=f"league_selectbox__{st.session_state.selected_sport}",
        )
        st.session_state.selected_league_id = league_ids[league_labels.index(league_choice)]

        # Status filter
        status_choice = st.selectbox(
            "📊 MATCH STATUS",
            options=STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(st.session_state.selected_status)
                  if st.session_state.selected_status in STATUS_OPTIONS else 0,
            key=f"status_selectbox__{st.session_state.selected_sport}",
        )
        st.session_state.selected_status = status_choice

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        if st.button("🔄 REFRESH DATA", use_container_width=True):
            _clear_all_caches()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # Risk controls
        st.subheader("🛡️ RISK CONTROLS")
        st.slider("KELLY %",  0.05, 0.50, 0.25, 0.05, format="%.0f%%")
        st.slider("MAX BET",  0.01, 0.10, 0.03, 0.01, format="%.0f%%")
        st.slider("MIN EV",   0.01, 0.10, 0.02, 0.01, format="%.0f%%")
        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.markdown("<hr style='border-color:#333;margin:15px 0;'>", unsafe_allow_html=True)
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
        '⚽ Soccer &nbsp;·&nbsp; 🏀 NBA &nbsp;·&nbsp; 🏈 NFL &nbsp;·&nbsp; '
        '⚾ MLB &nbsp;·&nbsp; 🏒 NHL &nbsp;·&nbsp; 🥊 UFC &nbsp;·&nbsp; '
        '🏎️ F1 &nbsp;·&nbsp; 🎾 Tennis &nbsp;·&nbsp; 🏏 Cricket &nbsp;·&nbsp; ⛳ Golf'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:   return "#00FF88", "rgba(0,255,136,.15)", "● LIVE"
    if any(x in su for x in ("FINISH","FT","FINAL","COMPLETED")):
        return "#888", "rgba(136,136,136,.15)", "FINISHED"
    return "#FFAA00", "rgba(255,170,0,.15)", "UPCOMING"


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_live(_data_key: str, sport: str, league_id: str) -> pd.DataFrame:
    """Cached live match fetch — refreshes every 30s, never blocks UI."""
    try:
        return st.session_state.empire_data.get_live_matches_df(
            sport, None if league_id == "ALL" else league_id
        )
    except Exception as e:
        logger.error(f"_fetch_live: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_upcoming(_data_key: str, sport: str) -> pd.DataFrame:
    """Cached upcoming match fetch — refreshes every 5 min."""
    try:
        return st.session_state.empire_data.get_upcoming_matches_df(sport)
    except Exception as e:
        logger.error(f"_fetch_upcoming: {e}")
        return pd.DataFrame()


def _fetch_matches(sport: str, league_id: str, status: str) -> pd.DataFrame:
    # Cache key changes every 30s for live, 5min for upcoming
    live_key     = str(int(time.time() // 30))
    upcoming_key = str(int(time.time() // 300))
    try:
        if status == "LIVE":
            df = _fetch_live(live_key, sport, league_id)
        elif status in ("UPCOMING", "SCHEDULED"):
            df = _fetch_upcoming(upcoming_key, sport)
        elif status == "FINISHED":
            df = pd.DataFrame()
        else:  # ALL — combine live + upcoming
            live_df     = _fetch_live(live_key, sport, league_id)
            upcoming_df = _fetch_upcoming(upcoming_key, sport)
            parts = [d for d in [live_df, upcoming_df] if not d.empty]
            df    = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

        # Filter by specific league if selected
        if league_id != "ALL" and not df.empty and "LEAGUE" in df.columns:
            mask     = df["LEAGUE"].astype(str).str.contains(league_id, case=False, na=False)
            filtered = df[mask]
            if not filtered.empty:
                df = filtered
    except Exception as e:
        logger.error(f"_fetch_matches: {e}")
        df = pd.DataFrame()
    return df


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
    bar   = confidence_bar_html(pred.confidence, 180)
    donut = probability_donut_html(
        pred.home_win_pct, pred.draw_pct, pred.away_win_pct,
        pred.home_team,    pred.away_team,
    )
    value_badge = (
        f'<span class="value-badge">💰 VALUE BET</span>'
        if pred.value_rating in ("⭐⭐⭐", "⭐⭐") else ""
    )

    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

    # Header row
    h1, h2 = st.columns([3, 2])
    with h1:
        st.markdown(
            f'<div style="font-family:Rajdhani;font-size:.8rem;color:#8892b0;">{pred.league}</div>'
            f'<div style="font-family:Rajdhani;font-size:1.2rem;font-weight:700;color:#e6f1ff;">'
            f'{pred.home_team} <span style="color:#888;">vs</span> {pred.away_team}</div>'
            f'<div style="margin-top:10px;">'
            f'<span class="bet-badge">{pred.recommended_bet}</span>{value_badge}</div>'
            f'<div style="margin-top:10px;color:#888;font-size:.8rem;font-family:Rajdhani;">'
            f'Rating: {pred.value_rating} &nbsp;|&nbsp; '
            f'Generated: {pred.generated_at[11:16]}</div>',
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(donut, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2a2a3e;margin:12px 0;">', unsafe_allow_html=True)

    # Confidence bar
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
        f'<span style="font-family:Orbitron;font-size:.75rem;color:#888;">CONFIDENCE</span>'
        f'{bar}'
        f'<span style="font-family:Orbitron;font-size:1rem;font-weight:900;color:{color};">'
        f'{pred.confidence}% {pred.confidence_label}</span></div>',
        unsafe_allow_html=True,
    )

    # Expected goals
    if pred.expected_goals and pred.expected_goals != "—":
        st.markdown(
            f'<div style="font-family:Orbitron;font-size:.8rem;color:#888;margin-bottom:8px;">'
            f'⚽ EXPECTED GOALS: <span style="color:#FFD700;">{pred.expected_goals}</span></div>',
            unsafe_allow_html=True,
        )

    # AI narrative
    if pred.ai_summary:
        st.markdown(f'<div class="ai-narrative">💬 {pred.ai_summary}</div>',
                    unsafe_allow_html=True)

    # Factors & risks
    f1, f2 = st.columns(2)
    with f1:
        st.markdown(
            '<div style="font-family:Orbitron;font-size:.7rem;color:#D4AF37;'
            'margin-bottom:6px;">✅ KEY FACTORS</div>',
            unsafe_allow_html=True,
        )
        for factor in pred.key_factors[:4]:
            st.markdown(f'<div class="factor-item">{factor}</div>', unsafe_allow_html=True)
    with f2:
        st.markdown(
            '<div style="font-family:Orbitron;font-size:.7rem;color:#ff6b6b;'
            'margin-bottom:6px;">⚠️ RISK FACTORS</div>',
            unsafe_allow_html=True,
        )
        for risk in pred.risk_factors[:3]:
            st.markdown(f'<div class="risk-item">{risk}</div>', unsafe_allow_html=True)

    # Betting angle
    if pred.betting_angle and pred.betting_angle != "—":
        st.markdown(
            f'<div style="margin-top:12px;background:rgba(212,175,55,.1);'
            f'border-radius:8px;padding:10px;">'
            f'<span style="font-family:Orbitron;font-size:.7rem;color:#D4AF37;">🎯 BETTING ANGLE: </span>'
            f'<span style="font-family:Rajdhani;color:#FFD700;font-size:.95rem;">'
            f'{pred.betting_angle}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MATCH CARDS  (arena view)
# ══════════════════════════════════════════════════════════════════════════════
def render_match_cards(matches_df: pd.DataFrame, sport: str):
    if matches_df is None or matches_df.empty:
        fs_ok = st.session_state.empire_data.router.flashscore.ok
        if fs_ok:
            st.warning(
                f"⏳ **No {sport} matches returned yet.**\n\n"
                "FlashScore via Apify may need a moment to complete its first run. "
                "**Click 🔄 REFRESH DATA** in the sidebar to trigger a fresh fetch. "
                "Subsequent loads will be instant from cache."
            )
        else:
            st.info(
                f"No {sport} matches found. "
                "Check that APIFY_API_KEY and sport API keys are set in Render → "
                "Settings → Environment Variables."
            )
        return

    st.markdown(
        f"<div style='color:#888;font-size:.85rem;margin-bottom:10px;'>"
        f"📊 {len(matches_df)} matches found</div>",
        unsafe_allow_html=True,
    )

    for idx, row in matches_df.iterrows():
        home      = row.get("HOME_TEAM", "TBD")
        away      = row.get("AWAY_TEAM", "TBD")
        score     = row.get("SCORE",     "vs")
        league    = row.get("LEAGUE",    "")
        mtime     = row.get("TIME",      "")
        match_id  = row.get("MATCH_ID",  str(idx))
        status_raw = row.get("STATUS",   "UPCOMING")
        color, bg, label = _status_style(status_raw)

        # Quick AI confidence badge (from cache if available)
        cached_pred = ai.cache.get(match_id, sport)
        ai_badge = ""
        if cached_pred and hasattr(cached_pred, "confidence"):
            c = cached_pred.confidence
            cc = confidence_color(c)
            ai_badge = (
                f'<span style="color:{cc};font-family:Orbitron;font-size:.65rem;'
                f'border:1px solid {cc};border-radius:8px;padding:2px 8px;margin-left:8px;">'
                f'🧠 {c}%</span>'
            )

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(20,25,40,.9),rgba(10,15,30,.95));
             border:1px solid rgba(255,255,255,.08);border-radius:12px;
             padding:16px;margin:8px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#8892b0;font-size:.75rem;font-family:Rajdhani;">{league}</span>
                <div>
                  <span style="color:{color};background:{bg};padding:2px 10px;
                        border-radius:10px;font-size:.7rem;font-weight:700;
                        font-family:Orbitron;">{label}</span>
                  {ai_badge}
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="flex:1;text-align:left;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;font-family:Rajdhani;">{home}</div>
                </div>
                <div style="padding:0 20px;text-align:center;">
                    <div style="color:#00d4ff;font-size:1.4rem;font-weight:700;letter-spacing:2px;font-family:Orbitron;">{score}</div>
                    <div style="color:#8892b0;font-size:.65rem;margin-top:2px;">{mtime}</div>
                </div>
                <div style="flex:1;text-align:right;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;font-family:Rajdhani;">{away}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        b1, b2 = st.columns([7, 1])
        with b1:
            if st.button(f"🧠 AI PREDICT", key=f"predict_{sport}_{match_id}_{idx}",
                         use_container_width=True):
                st.session_state.selected_match_id   = match_id
                st.session_state.selected_match_row  = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.session_state.selected_match_sport = sport
                st.rerun()
        with b2:
            if st.button("🔍", key=f"view_{sport}_{match_id}_{idx}"):
                st.session_state.selected_match_id   = match_id
                st.session_state.selected_match_row  = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.session_state.selected_match_sport = sport
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MATCH DETAIL + AI PREDICTION PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_detail():
    match_id  = st.session_state.get("selected_match_id", "")
    match_row = st.session_state.get("selected_match_row", {})
    home      = st.session_state.get("selected_match_home", "Home")
    away      = st.session_state.get("selected_match_away", "Away")
    sport     = st.session_state.get("selected_match_sport",
                                     st.session_state.selected_sport)

    st.markdown(f'<div class="section-header">🧠 AI ANALYSIS — {home} vs {away}</div>',
                unsafe_allow_html=True)

    if st.button("← Back to Match List"):
        for k in ("selected_match_id", "selected_match_row",
                  "selected_match_home", "selected_match_away",
                  "selected_match_sport"):
            st.session_state.pop(k, None)
        st.rerun()

    # Match info row
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 📋 MATCH INFORMATION")
        for label, key in [("League","LEAGUE"),("Status","STATUS"),
                            ("Time","TIME"),("Score","SCORE"),("Provider","PROVIDER")]:
            val = match_row.get(key, "N/A")
            st.markdown(
                f'<div class="stat-row"><span class="stat-label">{label}</span>'
                f'<span class="stat-value">{val}</span></div>',
                unsafe_allow_html=True,
            )
    with c2:
        score_val = match_row.get("SCORE", "vs")
        st.markdown(
            f'<div style="text-align:center;padding:20px;">'
            f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-bottom:4px;">{sport.upper()}</div>'
            f'<div style="font-family:Orbitron;font-size:2.5rem;color:#FFD700;font-weight:900;">{score_val}</div>'
            f'<div style="font-family:Rajdhani;font-size:1rem;color:#8892b0;margin-top:4px;">'
            f'{home} vs {away}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # AI Prediction section
    st.markdown(
        '<div style="font-family:Orbitron;font-size:1rem;color:#D4AF37;'
        'text-align:center;margin:10px 0;">🧠 CLAUDE AI PREDICTION ENGINE</div>',
        unsafe_allow_html=True,
    )

    if not ai.available:
        st.error(
            "🔴 ANTHROPIC_API_KEY not set in Render environment variables. "
            "Add it under Settings → Environment to activate AI predictions."
        )
        return

    # Check cache first; generate if missing
    cached = ai.cache.get(match_id, sport)
    force  = st.button("🔄 Regenerate Prediction", key=f"regen_{match_id}")

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

    icon     = SPORT_OPTIONS.get(sport, {}).get("icon", "🏆")
    provider = SPORT_OPTIONS.get(sport, {}).get("provider", "")
    st.markdown(
        f'<div class="section-header">{icon} EMPIRE ARENA — {sport.upper()}</div>',
        unsafe_allow_html=True,
    )

    # Provider + status badge
    fs_online   = data.router.flashscore.ok
    badge_color = "#00ff88" if fs_online else "#FFD700"
    badge_text  = "FlashScore LIVE" if fs_online else "Legacy Provider"
    st.markdown(
        f'<div style="color:{badge_color};font-family:Orbitron;font-size:.7rem;'
        f'margin-bottom:10px;">📡 {badge_text} | {provider}</div>',
        unsafe_allow_html=True,
    )

    # Show spinner while Apify run-sync is in progress (can take up to 55s first call)
    spinner_msg = (
        f"⚡ Fetching {sport} matches from FlashScore..."
        if fs_online else
        f"📡 Fetching {sport} matches..."
    )
    with st.spinner(spinner_msg):
        df = _fetch_matches(sport, league_id, status)

    render_match_cards(df, sport)


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS TAB  — AI Batch Scanner + top picks
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions(sport: str, league_id: str, status: str):
    st.markdown('<div class="section-header">🎯 AI PREDICTION CENTER</div>',
                unsafe_allow_html=True)

    if not ai.available:
        st.error(
            "🔴 ANTHROPIC_API_KEY not configured. "
            "Go to Render → Settings → Environment Variables and add ANTHROPIC_API_KEY."
        )
        return

    # Metrics row
    stats = ai.get_stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI CALLS",      stats["api_calls"])
    m2.metric("CACHED PREDS",  stats["cache_active"])
    m3.metric("ERRORS",        stats["errors"])
    m4.metric("MODEL",         "Sonnet 4")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # Fetch current matches
    df = _fetch_matches(sport, league_id, status)

    if df.empty:
        st.info("No matches to analyse. Select a sport and ensure the status filter includes upcoming matches.")
        return

    # Auto-scan toggle
    col_scan, col_info = st.columns([2, 3])
    with col_scan:
        run_scan = st.button("⚡ RUN AI BATCH SCANNER", use_container_width=True)
    with col_info:
        st.markdown(
            '<div style="color:#888;font-family:Rajdhani;font-size:.9rem;padding-top:8px;">'
            f'🔍 Will scan {min(len(df), 20)} matches and surface top picks ≥ 65% confidence</div>',
            unsafe_allow_html=True,
        )

    if run_scan or "batch_result" in st.session_state:
        if run_scan:
            with st.spinner("🧠 Claude AI scanning all matches for value..."):
                result = ai.scan_matches(df, sport)
            st.session_state.batch_result = result
        else:
            result = st.session_state.get("batch_result")

        if result and isinstance(result, BulkScanResult):
            st.markdown(
                f'<div style="background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.3);'
                f'border-radius:10px;padding:12px;margin:10px 0;font-family:Rajdhani;">'
                f'<span style="color:#00ff88;font-family:Orbitron;font-size:.85rem;">⚡ SCAN COMPLETE</span> — '
                f'{result.total_matches} matches analysed | '
                f'{len(result.high_conf_picks)} high-confidence picks | '
                f'{len(result.value_bets)} value bets found | '
                f'Scanned at {result.scan_time}</div>',
                unsafe_allow_html=True,
            )

            # Top picks
            if result.high_conf_picks:
                st.markdown(
                    '<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;'
                    'margin:16px 0 8px;">🏆 TOP CONFIDENCE PICKS</div>',
                    unsafe_allow_html=True,
                )
                for pick in result.high_conf_picks:
                    conf  = pick.get("confidence", 0)
                    color = confidence_color(conf)
                    bar   = confidence_bar_html(conf, 150)
                    st.markdown(
                        f'<div class="scan-pick">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'<div><span style="font-family:Rajdhani;color:#e6f1ff;font-size:1rem;">'
                        f'{pick.get("home_team","?")} vs {pick.get("away_team","?")}</span>'
                        f'<span style="color:#8892b0;font-size:.8rem;margin-left:8px;">'
                        f'— {pick.get("league","")}</span></div>'
                        f'<span style="color:{color};font-family:Orbitron;font-size:.85rem;'
                        f'font-weight:700;">{conf}% {pick.get("value_rating","")}</span></div>'
                        f'<div style="margin-top:8px;">'
                        f'<span class="bet-badge">{pick.get("recommended_bet","")}</span></div>'
                        f'<div style="margin-top:8px;color:#ccd6f6;font-family:Rajdhani;font-size:.9rem;">'
                        f'{pick.get("one_line_reason","")}</div>'
                        f'<div style="margin-top:8px;">{bar}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Value bets
            if result.value_bets:
                st.markdown(
                    '<div style="font-family:Orbitron;font-size:.9rem;color:#00ff88;'
                    'margin:16px 0 8px;">💰 VALUE BETS DETECTED</div>',
                    unsafe_allow_html=True,
                )
                for vb in result.value_bets:
                    st.markdown(
                        f'<div style="background:rgba(0,255,136,.06);border:1px solid rgba(0,255,136,.25);'
                        f'border-radius:10px;padding:12px;margin:6px 0;font-family:Rajdhani;">'
                        f'<span style="color:#e6f1ff;font-size:1rem;">{vb.get("match","")}</span>'
                        f'<div style="margin-top:6px;">'
                        f'<span class="bet-badge">{vb.get("bet","")}</span>'
                        f'<span style="color:#00ff88;margin-left:12px;font-size:.9rem;">'
                        f'Edge: {vb.get("edge","")} {vb.get("rating","")}</span></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.warning("Scanner returned no picks above the confidence threshold. Try a different sport or status filter.")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # Individual match predictions
    st.markdown(
        '<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin-bottom:12px;">'
        '🔍 INDIVIDUAL MATCH ANALYSIS</div>',
        unsafe_allow_html=True,
    )
    st.caption("Select a match below to generate a full Claude AI prediction.")

    for idx, row in df.head(15).iterrows():
        home     = row.get("HOME_TEAM", "TBD")
        away     = row.get("AWAY_TEAM", "TBD")
        league   = row.get("LEAGUE",    "")
        match_id = row.get("MATCH_ID",  str(idx))
        mtime    = row.get("TIME",      "")

        cached_pred = ai.cache.get(match_id, sport)
        has_pred    = cached_pred is not None

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            badge = ""
            if has_pred and hasattr(cached_pred, "confidence"):
                cc = confidence_color(cached_pred.confidence)
                badge = (
                    f' <span style="color:{cc};font-family:Orbitron;font-size:.7rem;'
                    f'border:1px solid {cc};border-radius:8px;padding:2px 8px;">'
                    f'🧠 {cached_pred.confidence}%</span>'
                )
            st.markdown(
                f'<div style="padding:8px 0;border-bottom:1px solid #2a2a3e;">'
                f'<span style="font-family:Rajdhani;color:#e6f1ff;">{home} vs {away}</span>'
                f'<span style="color:#8892b0;font-size:.8rem;margin-left:8px;">— {league} | {mtime}</span>'
                f'{badge}</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            btn_label = "⚡ Cached" if has_pred else "🧠 Predict"
            if st.button(btn_label, key=f"pred_tab_{match_id}_{idx}",
                         use_container_width=True):
                with st.spinner(f"🧠 Analysing {home} vs {away}..."):
                    pred = ai.predict_match(row.to_dict(), sport)
                render_prediction_card(pred)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB  — AI performance tracking + log
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 AI PERFORMANCE ANALYTICS</div>',
                unsafe_allow_html=True)

    stats = ai.get_stats()

    # Top metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("TOTAL AI CALLS",  stats["api_calls"])
    m2.metric("CACHED PREDS",    stats["cache_active"])
    m3.metric("PREDICTION LOG",  stats["predictions"])
    m4.metric("ERRORS",          stats["errors"])
    m5.metric("ENGINE",          "Claude Sonnet")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # AI status card
    ai_col  = "#00ff88" if ai.available else "#ff6b6b"
    ai_stat = "ONLINE" if ai.available else "OFFLINE — Set ANTHROPIC_API_KEY"
    st.markdown(
        f'<div style="background:rgba(0,0,0,.3);border:1px solid {ai_col};'
        f'border-radius:10px;padding:16px;margin:10px 0;">'
        f'<div style="font-family:Orbitron;font-size:.9rem;color:{ai_col};">'
        f'🧠 CLAUDE AI ENGINE STATUS: {ai_stat}</div>'
        f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-top:8px;">'
        f'Model: {stats["model"]}<br>'
        f'Prediction TTL: 30 minutes | Batch scan TTL: 5 minutes<br>'
        f'Max tokens per call: 1,200 | Batch max tokens: 2,000<br>'
        f'Confidence thresholds: HIGH ≥70% | MEDIUM ≥55% | LOW below 55%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Prediction log table
    pred_log = ai.get_prediction_log()
    if pred_log:
        st.markdown(
            '<div style="font-family:Orbitron;font-size:.85rem;color:#D4AF37;margin:16px 0 8px;">'
            '📋 RECENT PREDICTION LOG</div>',
            unsafe_allow_html=True,
        )
        log_df = pd.DataFrame(pred_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No predictions generated yet. Go to the ARENA or PREDICTIONS tab and analyse a match.")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # Provider status
    st.markdown(
        '<div style="font-family:Orbitron;font-size:.85rem;color:#D4AF37;margin-bottom:12px;">'
        '⚡ DATA PROVIDER STATUS</div>',
        unsafe_allow_html=True,
    )
    for s in data.router.get_provider_status():
        color = "#00ff88" if "ONLINE" in s["status"] else "#888"
        st.markdown(
            f'<div class="stat-row">'
            f'<span class="stat-label">{s["name"]}</span>'
            f'<span style="color:{color};font-weight:700;">{s["status"]}</span></div>',
            unsafe_allow_html=True,
        )
    # Claude
    ai_col = "#00ff88" if ai.available else "#ff6b6b"
    ai_s   = "🟢 ONLINE" if ai.available else "🔴 KEY MISSING"
    st.markdown(
        f'<div class="stat-row">'
        f'<span class="stat-label">Claude AI (Anthropic)</span>'
        f'<span style="color:{ai_col};font-weight:700;">{ai_s}</span></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
def render_top_bar():
    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= REFRESH_INTERVAL:
        _clear_all_caches()
        st.rerun()
    color, mode = ("#00ff88", "LIVE") if data.is_live else ("#FFD700", "DEMO")
    cb, cs = st.columns([1, 5])
    with cb:
        if st.button("🔄 FORCE REFRESH", use_container_width=True):
            _clear_all_caches()
            st.rerun()
    with cs:
        st.markdown(
            f'<div style="color:{color};font-family:Orbitron;font-size:.8rem;padding-top:8px;">'
            f'● {mode} | Auto-refresh in {int(max(0, REFRESH_INTERVAL - elapsed))}s'
            f' | AI: {"🧠 READY" if ai.available else "⚠️ OFFLINE"}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
render_header()
selected_sport, selected_league_id, selected_status = render_sidebar()
render_ticker()
render_top_bar()

page = st.radio(
    "", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"],
    horizontal=True, label_visibility="collapsed",
    key="page_radio",
)

if "ARENA" in page:
    render_arena(selected_sport, selected_league_id, selected_status)
elif "PREDICTIONS" in page:
    render_predictions(selected_sport, selected_league_id, selected_status)
else:
    render_analytics()
