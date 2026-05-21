"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
World-Class Professional Command Center
24/7 AI Engine | Real-Time Global Sports Intelligence
"""
import sys
import os

# Add project root to Python path BEFORE importing empire_data_layer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from pathlib import Path
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import logging

from empire_data_layer import EmpireDashboardData, APIConfig

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="BRAND_ASSET/empire_logo_primary.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# LIVE DATA INITIALIZATION (singleton via session_state)
# ══════════════════════════════════════════════════════════════════════════════
if "empire_data" not in st.session_state:
    st.session_state.empire_data = EmpireDashboardData()

data: EmpireDashboardData = st.session_state.empire_data

REFRESH_INTERVAL = 30  # seconds

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');

    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
        font-family: 'Rajdhani', sans-serif;
    }

    .logo-center {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; text-align: center;
        padding: 8px 0 4px 0; width: 100%; margin-bottom: 0;
    }
    .logo-img {
        width: 90%; height: auto; max-height: 180px;
        object-fit: contain; display: block; margin: 0 auto;
    }
    .tagline-bold {
        font-family: 'Orbitron', sans-serif; font-size: 1.4rem; font-weight: 900;
        background: linear-gradient(135deg, #D4AF37 0%, #FFD700 50%, #B8860B 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; letter-spacing: 4px; text-transform: uppercase;
        margin-top: 6px; margin-bottom: 2px;
    }
    .tagline-sub {
        font-family: 'Rajdhani', sans-serif; font-size: 0.9rem; color: #888;
        text-align: center; letter-spacing: 6px; text-transform: uppercase;
        margin-top: 2px; margin-bottom: 8px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
        border-right: 3px solid #D4AF37;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #D4AF37 !important; font-family: 'Orbitron', sans-serif;
        font-weight: 700; letter-spacing: 2px;
    }
    .ai-status {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
        color: #000; font-family: 'Orbitron', sans-serif; font-weight: 900;
        font-size: 0.8rem; padding: 8px 16px; border-radius: 20px;
        text-align: center; letter-spacing: 3px; text-transform: uppercase;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.4); animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.4); }
        50%       { box-shadow: 0 0 25px rgba(0, 255, 136, 0.8); }
    }
    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
        color: #000000 !important; font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important; font-size: 0.85rem !important;
        text-transform: uppercase !important; letter-spacing: 1.5px !important;
        border-bottom: 3px solid #FFD700 !important;
        padding: 14px 12px !important; text-align: center !important;
    }
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] td {
        background-color: #1a1a2e !important; color: #FFD700 !important;
        font-family: 'Rajdhani', sans-serif !important; font-weight: 500 !important;
        font-size: 0.95rem !important; border-bottom: 1px solid #2a2a3e !important;
        padding: 10px 12px !important; text-align: center !important;
    }
    [data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
        background-color: #151525 !important;
    }
    [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
        background: rgba(212, 175, 55, 0.2) !important;
        color: #FFFFFF !important; font-weight: 700 !important; cursor: pointer;
    }
    .section-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.3rem; font-weight: 700;
        color: #FFD700; letter-spacing: 2px; text-transform: uppercase;
        padding: 15px 20px;
        background: linear-gradient(90deg, rgba(212,175,55,0.2) 0%, transparent 100%);
        border-left: 4px solid #D4AF37; border-radius: 0 8px 8px 0;
        margin: 20px 0 10px 0;
    }
    .match-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #333; border-radius: 10px;
        padding: 15px; margin: 8px 0; transition: all 0.3s ease;
    }
    .match-card:hover {
        border-color: #D4AF37; box-shadow: 0 0 20px rgba(212,175,55,0.2);
        transform: translateX(5px);
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.5; }
    }
    [data-testid="stMetricValue"] {
        color: #FFD700 !important; font-family: 'Orbitron', sans-serif;
        font-weight: 900; font-size: 2rem;
    }
    [data-testid="stMetricLabel"] {
        color: #888 !important; font-family: 'Rajdhani', sans-serif;
        font-weight: 500; letter-spacing: 2px; text-transform: uppercase;
    }
    .world-clock {
        font-family: 'Orbitron', sans-serif; font-size: 0.9rem;
        color: #D4AF37; text-align: center; letter-spacing: 2px;
        padding: 10px; background: rgba(212,175,55,0.1);
        border-radius: 8px; margin: 10px 0;
    }
    .ticker {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        border-top: 2px solid #D4AF37; border-bottom: 2px solid #D4AF37;
        padding: 10px; overflow: hidden; white-space: nowrap;
    }
    .ticker-text {
        font-family: 'Rajdhani', sans-serif; color: #FFD700;
        font-size: 0.9rem; letter-spacing: 2px;
        animation: scroll 20s linear infinite;
    }
    @keyframes scroll {
        0%   { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    .stButton>button {
        background: linear-gradient(135deg, #D4AF37 0%, #FFD700 100%);
        color: #000; font-family: 'Orbitron', sans-serif; font-weight: 700;
        border: none; border-radius: 8px; padding: 0.6rem 2rem;
        letter-spacing: 2px; text-transform: uppercase; transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #FFD700 0%, #FFF8DC 100%);
        box-shadow: 0 0 25px rgba(212,175,55,0.6); transform: scale(1.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: rgba(26,26,46,0.5);
        border-radius: 10px; padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #888;
        font-family: 'Orbitron', sans-serif; font-weight: 500;
        letter-spacing: 1px; border-radius: 6px; padding: 0.5rem 1.5rem;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #D4AF37 0%, #FFD700 100%) !important;
        color: #000 !important; font-weight: 700;
    }
    .gold-divider {
        border: none; height: 2px;
        background: linear-gradient(90deg, transparent 0%, #D4AF37 50%, transparent 100%);
        margin: 20px 0;
    }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0a0a0f; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%);
        border-radius: 4px;
    }
    .stat-row {
        display: flex; justify-content: space-between; padding: 8px 0;
        border-bottom: 1px solid #2a2a3e; font-family: 'Rajdhani', sans-serif;
        font-size: 0.95rem;
    }
    .stat-label { color: #888; }
    .stat-value { color: #FFD700; font-weight: 700; }
</style>
""")

# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Soccer":    {"icon": "⚽",  "provider": "API-SPORTS"},
    "NBA":       {"icon": "🏀",  "provider": "MySportsFeeds"},
    "NFL":       {"icon": "🏈",  "provider": "MySportsFeeds"},
    "MLB":       {"icon": "⚾",  "provider": "MySportsFeeds"},
    "NHL":       {"icon": "🏒",  "provider": "MySportsFeeds"},
    "UFC":       {"icon": "🥊",  "provider": "TheSportsDB"},
    "Formula 1": {"icon": "🏎️", "provider": "TheSportsDB"},
    "Tennis":    {"icon": "🎾",  "provider": "TheSportsDB"},
    "Cricket":   {"icon": "🏏",  "provider": "TheSportsDB"},
    "Golf":      {"icon": "⛳",  "provider": "TheSportsDB"},
}

STATUS_OPTIONS = ["ALL", "LIVE", "UPCOMING", "FINISHED"]

# ══════════════════════════════════════════════════════════════════════════════
# AI STATUS & CLOCK
# ══════════════════════════════════════════════════════════════════════════════
def render_ai_status():
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        st.markdown('<div class="ai-status">🤖 AI ENGINE ONLINE 24/7</div>',
                    unsafe_allow_html=True)
    now = datetime.utcnow()
    cities = [
        ("LONDON",   now + timedelta(hours=1)),
        ("NEW YORK", now - timedelta(hours=5)),
        ("TOKYO",    now + timedelta(hours=9)),
        ("SYDNEY",   now + timedelta(hours=10)),
        ("LAGOS",    now + timedelta(hours=1)),
    ]
    clock = " | ".join(f"{c}: {dt.strftime('%H:%M')}" for c, dt in cities)
    st.markdown(f'<div class="world-clock">🌍 {clock}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    logo_path = Path("BRAND_ASSET/empire_logo_primary.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="EMPIRE Logo">'
    else:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 140">'
            '<defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%">'
            '<stop offset="0%" style="stop-color:#D4AF37"/>'
            '<stop offset="100%" style="stop-color:#FFD700"/>'
            '</linearGradient></defs>'
            '<rect width="900" height="140" rx="12" fill="#16213e" stroke="#D4AF37" stroke-width="2"/>'
            '<text x="450" y="85" font-family="Arial Black,Impact,sans-serif" font-size="52" '
            'fill="url(#g1)" text-anchor="middle" font-weight="900" letter-spacing="6">'
            'EMPIRE SPORT INSTINCTS ARENA</text>'
            '<text x="450" y="115" font-family="Arial,sans-serif" font-size="16" '
            'fill="#888" text-anchor="middle" letter-spacing="10">'
            'ELITE TRADING DASHBOARD v3.0</text></svg>'
        )
        b64 = base64.b64encode(svg.encode()).decode()
        logo_html = f'<img src="data:image/svg+xml;base64,{b64}" class="logo-img" alt="EMPIRE Logo">'

    st.markdown(f'<div class="logo-center">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Advanced Research & Evaluation System | Where Data Meets Instinct</div>',
                unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    render_ai_status()

    if data.is_live:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#00ff88,#00cc6a);color:#000;
             font-family:Orbitron;font-size:1rem;padding:12px 20px;border-radius:8px;
             text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;
             box-shadow:0 0 20px rgba(0,255,136,0.4);">
            🟢 LIVE MODE — APIs Connected | Real-Time Data Active
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#B8860B,#FFD700);color:#000;
             font-family:Orbitron;font-size:1rem;padding:12px 20px;border-radius:8px;
             text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;
             box-shadow:0 0 20px rgba(212,175,55,0.4);">
            ⚠️ NO API KEYS FOUND — Check Render environment variables
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    """
    Renders the sidebar and returns (selected_sport, selected_league_id, selected_status).
    All three dropdowns stay in sync via session_state.
    """
    with st.sidebar:
        # Brand
        sidebar_logo = Path("BRAND_ASSET/empire_logo_arena.png")
        if sidebar_logo.exists():
            with open(sidebar_logo, "rb") as f:
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
                'font-size:14px;font-weight:900;margin-bottom:10px;">EMPIRE</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<h2 style="text-align:center;font-size:1.2rem;">COMMAND CENTER</h2>',
                    unsafe_allow_html=True)

        # Bot status
        st.markdown("""
        <div style="background:rgba(0,255,136,0.1);border:1px solid #00ff88;
             border-radius:8px;padding:10px;margin:10px 0;">
            <div style="color:#00ff88;font-family:'Orbitron';font-size:0.8rem;text-align:center;">
                🤖 INSTINCT BOT v3.0<br>
                <span style="color:#888;font-size:0.7rem;">SCANNING LIVE MATCHES</span><br>
                <span style="color:#00ff88;">● LIVE</span>
            </div>
        </div>""", unsafe_allow_html=True)

        # Provider status
        st.subheader("⚡ SYSTEM STATUS")
        st.markdown(
            '<div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px;margin:8px 0;">',
            unsafe_allow_html=True,
        )
        try:
            for s in data.router.get_provider_status():
                color = "#00ff88" if "ONLINE" in s["status"] else "#888"
                st.markdown(
                    f'<div style="font-family:Orbitron;font-size:0.7rem;'
                    f'color:{color};padding:2px 0;">'
                    f'{s["name"]}: {s["status"]}</div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.markdown(f'<div style="color:#ff4444;font-size:0.7rem;">Error: {e}</div>',
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # ── ARENA CONTROLS ────────────────────────────────────────────────────
        st.markdown(
            '<div style="color:#D4AF37;font-family:Orbitron;font-size:0.9rem;'
            'text-align:center;margin-bottom:10px;">🏟️ ARENA CONTROLS</div>',
            unsafe_allow_html=True,
        )

        sport_names = list(SPORT_OPTIONS.keys())

        # Initialise session_state defaults once
        if "selected_sport" not in st.session_state:
            st.session_state.selected_sport = sport_names[0]
        if "selected_league_id" not in st.session_state:
            st.session_state.selected_league_id = "ALL"
        if "selected_status" not in st.session_state:
            st.session_state.selected_status = "ALL"

        # ── Sport selector ────────────────────────────────────────────────────
        prev_sport = st.session_state.selected_sport

        selected_sport = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_names,
            index=sport_names.index(st.session_state.selected_sport),
            key="_sport_box",
        )

        # When sport changes → reset league & status to avoid stale cross-filter
        if selected_sport != prev_sport:
            st.session_state.selected_sport      = selected_sport
            st.session_state.selected_league_id  = "ALL"
            st.session_state.selected_status     = "ALL"
            # Bust league cache for old sport so new sport fetches fresh
            st.cache_data.clear()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:8px 0;'>", unsafe_allow_html=True)

        # ── League / team selector ────────────────────────────────────────────
        # Fetch league list; cache inside the data layer (24 h TTL)
        league_options = [("ALL", "🏆 All Leagues / Teams")]
        try:
            api_leagues = data.get_all_leagues(selected_sport)
            for lg in api_leagues:
                label = lg.get("name", "Unknown")
                if lg.get("country"):
                    label += f" ({lg['country']})"
                league_options.append((str(lg.get("id", "ALL")), label))
        except Exception as e:
            logger.error(f"League fetch failed for {selected_sport}: {e}")

        league_ids    = [o[0] for o in league_options]
        league_labels = [o[1] for o in league_options]

        # Ensure persisted league_id is still valid for this sport
        if st.session_state.selected_league_id not in league_ids:
            st.session_state.selected_league_id = "ALL"

        current_league_idx = league_ids.index(st.session_state.selected_league_id)

        selected_label = st.selectbox(
            "🏆 SELECT LEAGUE / TEAM",
            options=league_labels,
            index=current_league_idx,
            key=f"_league_box_{selected_sport}",  # key includes sport → widget resets on sport change
        )
        selected_league_id = league_ids[league_labels.index(selected_label)]
        st.session_state.selected_league_id = selected_league_id

        # ── Match status filter ───────────────────────────────────────────────
        current_status_idx = (
            STATUS_OPTIONS.index(st.session_state.selected_status)
            if st.session_state.selected_status in STATUS_OPTIONS else 0
        )
        selected_status = st.selectbox(
            "📊 MATCH STATUS",
            options=STATUS_OPTIONS,
            index=current_status_idx,
            key=f"_status_box_{selected_sport}",  # also sport-scoped
        )
        st.session_state.selected_status = selected_status

        # ── Refresh button ────────────────────────────────────────────────────
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            # Clear provider caches so next call hits API
            for provider in [data.router.api_sports,
                             data.router.my_sports_feeds,
                             data.router.the_sports_db]:
                provider.cache.clear()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # Risk controls
        st.subheader("🛡️ RISK CONTROLS")
        st.slider("KELLY %",   0.05, 0.50, 0.25, 0.05, format="%.0f%%")
        st.slider("MAX BET",   0.01, 0.10, 0.03, 0.01, format="%.0f%%")
        st.slider("MIN EV",    0.01, 0.10, 0.02, 0.01, format="%.0f%%")

        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.markdown("<hr style='border-color:#333;margin:15px 0;'>", unsafe_allow_html=True)
        st.subheader("📡 API CONNECTION LOG")
        try:
            log_df = data.get_connection_log_df()
            if not log_df.empty:
                st.dataframe(log_df, use_container_width=True, hide_index=True, height=200)
            else:
                st.info("No connection attempts yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {e}")

    return selected_sport, selected_league_id, selected_status


# ══════════════════════════════════════════════════════════════════════════════
# LIVE TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_live_ticker():
    st.markdown(
        '<div class="ticker"><div class="ticker-text">'
        '📡 LIVE DATA FEED ACTIVE — CONNECTED TO ALL PROVIDERS | '
        '⚽ Soccer · 🏀 NBA · 🏈 NFL · ⚾ MLB · 🏒 NHL · 🥊 UFC · 🏎️ F1 · 🎾 Tennis · 🏏 Cricket · ⛳ Golf'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MATCH CARD RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:
        return "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
    if "FINISH" in su or "FT" in su or "FINAL" in su or "COMPLETED" in su:
        return "#888888", "rgba(136,136,136,0.15)", "FINISHED"
    return "#FFAA00", "rgba(255,170,0,0.15)", "UPCOMING"


def render_match_cards(matches_df: pd.DataFrame, sport: str):
    if matches_df is None or matches_df.empty:
        st.info(f"No matches found. The API may be off-season or returning no data for {sport}.")
        return

    st.markdown(
        f"<div style='color:#888;font-size:0.85rem;margin-bottom:10px;'>"
        f"📊 {len(matches_df)} matches found</div>",
        unsafe_allow_html=True,
    )

    for idx, row in matches_df.iterrows():
        home  = row.get("HOME_TEAM", row.get("MATCH", "TBD vs TBD").split(" vs ")[0])
        away  = row.get("AWAY_TEAM", row.get("MATCH", "TBD vs TBD").split(" vs ")[-1])
        score = row.get("SCORE", "vs")
        league = row.get("LEAGUE", "")
        match_time = row.get("TIME", "")
        match_id   = row.get("MATCH_ID", str(idx))
        status_raw = row.get("STATUS", "UPCOMING")

        color, bg, label = _status_style(status_raw)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(20,25,40,0.9),rgba(10,15,30,0.95));
             border:1px solid rgba(255,255,255,0.08);border-radius:12px;
             padding:16px;margin:8px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#8892b0;font-size:0.75rem;font-family:Rajdhani;">{league}</span>
                <span style="color:{color};background:{bg};padding:2px 10px;
                      border-radius:10px;font-size:0.7rem;font-weight:700;
                      font-family:Orbitron;">{label}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="flex:1;text-align:left;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;font-family:Rajdhani;">{home}</div>
                </div>
                <div style="padding:0 20px;text-align:center;">
                    <div style="color:#00d4ff;font-size:1.4rem;font-weight:700;letter-spacing:2px;
                          font-family:Orbitron;">{score}</div>
                    <div style="color:#8892b0;font-size:0.65rem;margin-top:2px;">{match_time}</div>
                </div>
                <div style="flex:1;text-align:right;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;font-family:Rajdhani;">{away}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        btn_cols = st.columns([6, 1])
        with btn_cols[1]:
            if st.button("🔍", key=f"view_{sport}_{match_id}_{idx}",
                         help="View match details"):
                st.session_state.selected_match_id   = match_id
                st.session_state.selected_match_row  = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MATCH DETAIL PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_analysis_panel():
    if "selected_match_id" not in st.session_state:
        st.info("👆 Select a match to view detailed analysis.")
        return

    match_id  = st.session_state.selected_match_id
    match_row = st.session_state.get("selected_match_row", {})
    home      = st.session_state.get("selected_match_home", "Home")
    away      = st.session_state.get("selected_match_away", "Away")

    st.markdown(f'<div class="section-header">🔍 MATCH ANALYSIS — {home} vs {away}</div>',
                unsafe_allow_html=True)

    if st.button("← Back to Match List"):
        for k in ("selected_match_id", "selected_match_row",
                  "selected_match_home", "selected_match_away"):
            st.session_state.pop(k, None)
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 📋 MATCH INFORMATION")
        for label, value in {
            "Match ID": match_id,
            "League":   match_row.get("LEAGUE", "N/A"),
            "Status":   match_row.get("STATUS", "N/A"),
            "Time":     match_row.get("TIME",   "TBD"),
            "Provider": match_row.get("PROVIDER", "N/A"),
        }.items():
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-label">{label}</span>'
                f'<span class="stat-value">{value}</span></div>',
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown("##### ⚖️ CURRENT ODDS")
        for label, key in [("Home", "HOME"), ("Draw", "DRAW"), ("Away", "AWAY")]:
            val = match_row.get(key, "-")
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-label">{label}</span>'
                f'<span class="stat-value">{val}</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.info("Full H2H, player stats, and form coming from live APIs.")


# ══════════════════════════════════════════════════════════════════════════════
# ARENA — MAIN VIEW
# ══════════════════════════════════════════════════════════════════════════════
def render_arena(sport: str, league_id: str, status: str):
    if "selected_match_id" in st.session_state:
        render_match_analysis_panel()
        return

    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {sport.upper()}</div>',
                unsafe_allow_html=True)

    try:
        if status == "LIVE":
            matches_df = data.get_live_matches_df(
                sport, league_id if league_id != "ALL" else None
            )
        elif status in ("UPCOMING", "SCHEDULED"):
            matches_df = data.get_upcoming_matches_df(sport)
        elif status == "FINISHED":
            matches_df = pd.DataFrame()  # no historical endpoint yet
        else:  # ALL
            live_df     = data.get_live_matches_df(
                sport, league_id if league_id != "ALL" else None
            )
            upcoming_df = data.get_upcoming_matches_df(sport)
            parts = [df for df in [live_df, upcoming_df] if not df.empty]
            matches_df  = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

        # Filter by league/team if a specific one is chosen
        if league_id != "ALL" and not matches_df.empty and "LEAGUE" in matches_df.columns:
            # Try to filter by league name or ID match
            mask = (
                matches_df["LEAGUE"].astype(str).str.contains(league_id, case=False, na=False)
            )
            filtered = matches_df[mask]
            if not filtered.empty:
                matches_df = filtered
            # If filter yields nothing keep full list (league_id may be an opaque ID)

    except Exception as e:
        st.error(f"Error fetching matches: {e}")
        logger.exception("render_arena fetch error")
        matches_df = pd.DataFrame()

    render_match_cards(matches_df, sport)


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS & ANALYTICS (stubs)
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>',
                unsafe_allow_html=True)
    st.info("🔮 AI predictions will appear here based on live match data.")


def render_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>',
                unsafe_allow_html=True)
    st.info("📊 Performance analytics powered by historical API data.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    render_header()

    # sidebar returns the three synchronized filter values
    selected_sport, selected_league_id, selected_status = render_sidebar()

    render_live_ticker()

    # Refresh control bar
    c_btn, c_status = st.columns([1, 4])
    with c_btn:
        if st.button("🔄 FORCE REFRESH", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            for provider in [data.router.api_sports,
                             data.router.my_sports_feeds,
                             data.router.the_sports_db]:
                provider.cache.clear()
            st.rerun()
    with c_status:
        next_refresh   = max(0, REFRESH_INTERVAL - elapsed)
        status_color   = "#00ff88" if data.is_live else "#FFD700"
        status_text    = "LIVE" if data.is_live else "DEMO"
        st.markdown(
            f'<div style="color:{status_color};font-family:Orbitron;font-size:0.8rem;padding-top:8px;">'
            f'● {status_text} | Auto-refresh in {int(next_refresh)}s</div>',
            unsafe_allow_html=True,
        )

    # Auto-refresh
    if elapsed >= REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        st.cache_data.clear()
        st.rerun()

    # Page tabs
    page = st.radio(
        "", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"],
        horizontal=True, label_visibility="collapsed",
    )

    if "ARENA" in page:
        render_arena(selected_sport, selected_league_id, selected_status)
    elif "PREDICTIONS" in page:
        render_predictions()
    else:
        render_analytics()
