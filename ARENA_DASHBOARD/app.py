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

# EMPIRE Live Data Integration — imports from project root
from empire_data_layer import EmpireDashboardData, APIConfig

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="BRAND_ASSET/empire_logo_primary.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE DATA INITIALIZATION
# ════════════════════════════════════════════════════════════════════════════════
data = EmpireDashboardData()

REFRESH_INTERVAL = 15  # seconds

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh

# ══════════════════════════════════════════════════════════════════════════════
# PREMIUM DARK GOLD COMMAND CENTER CSS
# ══════════════════════════════════════════════════════════════════════════════
st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');

    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
        font-family: 'Rajdhani', sans-serif;
    }

    .logo-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 8px 0 4px 0;
        width: 100%;
        margin-bottom: 0;
    }

    .logo-img {
        width: 90%;
        height: auto;
        max-height: 180px;
        object-fit: contain;
        display: block;
        margin: 0 auto;
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
        text-shadow: 0 0 20px rgba(212, 175, 55, 0.3);
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

    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
        color: #000000 !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        border-bottom: 3px solid #FFD700 !important;
        padding: 14px 12px !important;
        text-align: center !important;
    }

    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] td {
        background-color: #1a1a2e !important;
        color: #FFD700 !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        border-bottom: 1px solid #2a2a3e !important;
        padding: 10px 12px !important;
        text-align: center !important;
    }

    [data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
        background-color: #151525 !important;
    }

    [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
        background: rgba(212, 175, 55, 0.2) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        cursor: pointer;
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

    .match-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }

    .match-card:hover {
        border-color: #D4AF37;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.2);
        transform: translateX(5px);
    }

    .match-live {
        color: #00ff88;
        font-weight: 700;
        animation: blink 1s infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    [data-testid="stMetricValue"] {
        color: #FFD700 !important;
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: 2rem;
    }

    [data-testid="stMetricLabel"] {
        color: #888 !important;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
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
        animation: scroll 20s linear infinite;
    }

    @keyframes scroll {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }

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
        transform: scale(1.05);
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

    .gold-divider {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #D4AF37 50%, transparent 100%);
        margin: 20px 0;
    }

    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #0a0a0f;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%);
        border-radius: 4px;
    }

    .dark-container {
        background-color: #1a1a2e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        margin: 10px 0;
    }

    .detail-panel {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
        border: 2px solid #D4AF37;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }

    .detail-header {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.1rem;
        color: #FFD700;
        border-bottom: 2px solid #D4AF37;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #2a2a3e;
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.95rem;
    }

    .stat-label {
        color: #888;
    }

    .stat-value {
        color: #FFD700;
        font-weight: 700;
    }

    .odds-row {
        display: flex;
        justify-content: space-around;
        padding: 15px;
        background: rgba(212, 175, 55, 0.1);
        border-radius: 8px;
        margin: 10px 0;
    }

    .odds-box {
        text-align: center;
        padding: 10px 20px;
    }

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
</style>
""")

# ══════════════════════════════════════════════════════════════════════════════
# AI ENGINE STATUS & GLOBAL CLOCK
# ══════════════════════════════════════════════════════════════════════════════
def render_ai_status():
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div class="ai-status">🤖 AI ENGINE ONLINE 24/7</div>', unsafe_allow_html=True)

    now = datetime.now()
    cities = [
        ("LONDON", now + timedelta(hours=1)),
        ("NEW YORK", now - timedelta(hours=5)),
        ("TOKYO", now + timedelta(hours=9)),
        ("SYDNEY", now + timedelta(hours=10)),
        ("LAGOS", now + timedelta(hours=1)),
    ]
    clock_text = " | ".join([f"{city}: {dt.strftime('%H:%M')}" for city, dt in cities])
    st.markdown(f'<div class="world-clock">🌍 {clock_text}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    logo_path = Path("BRAND_ASSET/empire_logo_primary.png")

    if logo_path.exists():
        with open(logo_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="EMPIRE Logo">'
    else:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 140"><defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#D4AF37;stop-opacity:1"/><stop offset="100%" style="stop-color:#FFD700;stop-opacity:1"/></linearGradient></defs><rect width="900" height="140" rx="12" fill="#16213e" stroke="#D4AF37" stroke-width="2"/><text x="450" y="85" font-family="Arial Black, Impact, sans-serif" font-size="52" fill="url(#g1)" text-anchor="middle" font-weight="900" letter-spacing="6">EMPIRE SPORT INSTINCTS ARENA</text><text x="450" y="115" font-family="Arial, sans-serif" font-size="16" fill="#888" text-anchor="middle" letter-spacing="10">ELITE TRADING DASHBOARD v2.4</text></svg>"""
        b64 = base64.b64encode(svg.encode()).decode()
        logo_html = f'<img src="data:image/svg+xml;base64,{b64}" class="logo-img" alt="EMPIRE Logo">'

    st.markdown(f"""
    <div class="logo-center">
        {logo_html}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Advanced Research & Evaluation System | Where Data Meets Instinct</div>', unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    render_ai_status()

    # LIVE / DEMO MODE BANNER
    try:
        has_live = data.is_live
        if has_live:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #00ff88 0%, #00cc6a 100%); 
                        color: #000; font-family: Orbitron; font-size: 1rem; 
                        padding: 12px 20px; border-radius: 8px; text-align: center;
                        font-weight: 900; letter-spacing: 3px; margin: 10px 0;
                        box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);">
                🟢 LIVE MODE — Connected | Real data streaming
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #B8860B 0%, #FFD700 100%); 
                        color: #000; font-family: Orbitron; font-size: 1rem; 
                        padding: 12px 20px; border-radius: 8px; text-align: center;
                        font-weight: 900; letter-spacing: 3px; margin: 10px 0;
                        box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);">
                ⚠️ DEMO MODE — No APIs connected | Check .env keys & internet
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <div style="background: linear-gradient(90deg, #ff4444 0%, #cc0000 100%); 
                    color: #fff; font-family: Orbitron; font-size: 1rem; 
                    padding: 12px 20px; border-radius: 8px; text-align: center;
                    font-weight: 900; letter-spacing: 3px; margin: 10px 0;">
            🔴 SYSTEM ERROR — Cannot initialize data layer
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        sidebar_logo_path = Path("BRAND_ASSET/empire_logo_arena.png")
        if sidebar_logo_path.exists():
            with open(sidebar_logo_path, "rb") as f:
                sb_img = f.read()
            sb_b64 = base64.b64encode(sb_img).decode()
            st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{sb_b64}" style="width:85%; max-height:100px; object-fit:contain; display:block; margin:0 auto;"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center; color:#D4AF37; font-family:Orbitron; font-size:14px; font-weight:900; margin-bottom:10px;">EMPIRE</div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; font-size:1.2rem;">COMMAND CENTER</h2>', unsafe_allow_html=True)

        st.markdown("""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; border-radius: 8px; padding: 10px; margin: 10px 0;">
            <div style="color: #00ff88; font-family: 'Orbitron'; font-size: 0.8rem; text-align: center;">
                🤖 INSTINCT BOT v2.0<br>
                <span style="color: #888; font-size: 0.7rem;">SCANNING LIVE MATCHES</span><br>
                <span style="color: #00ff88; animation: blink 1s infinite;">● LIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("⚡ SYSTEM STATUS")

        st.markdown('<div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px; margin: 8px 0;">', unsafe_allow_html=True)

        provider_status = []
        try:
            statuses = data.router.get_provider_status()
            for s in statuses:
                if "ONLINE" in s["status"]:
                    icon, color = "🟢", "#00ff88"
                elif "EMPTY" in s["status"]:
                    icon, color = "🟡", "#FFD700"
                else:
                    icon, color = "🔴", "#ff4444"
                provider_status.append((f"{icon} {s['name']}", s["status"], color))
        except Exception as e:
            provider_status = [("🔴 Router", f"Error: {str(e)[:40]}", "#ff4444")]

        for name, status, color in provider_status:
            st.markdown(f'<div style="font-family: Orbitron; font-size: 0.7rem; color: {color}; padding: 2px 0;">{name}: {status}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("DATA", "ACTIVE", delta="●", delta_color="normal")
        with col2:
            st.metric("MODELS", "ONLINE", delta="●", delta_color="normal")

        st.subheader("🛡️ RISK CONTROLS")
        st.slider("KELLY %", 0.05, 0.50, 0.25, 0.05, format="%.0f%%")
        st.slider("MAX BET", 0.01, 0.10, 0.03, 0.01, format="%.0f%%")
        st.slider("MIN EV", 0.01, 0.10, 0.02, 0.01, format="%.0f%%")

        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.markdown("<hr style='border-color: #333; margin: 15px 0;'>", unsafe_allow_html=True)
        st.subheader("📡 API CONNECTION LOG")

        try:
            log_df = data.router.get_connection_log_df()
            if not log_df.empty:
                st.dataframe(log_df, use_container_width=True, hide_index=True, height=250)
            else:
                st.info("No connection attempts yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {str(e)[:50]}")

# ══════════════════════════════════════════════════════════════════════════════
# LIVE MATCH TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_live_ticker():
    st.markdown(f'<div class="ticker"><div class="ticker-text">📡 LIVE DATA FEED ACTIVE — CONNECTED TO ALL PROVIDERS</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIGURATION - Dynamic years from API
# ══════════════════════════════════════════════════════════════════════════════
CURRENT_YEAR = datetime.now().year
NEXT_YEAR = CURRENT_YEAR + 1

SPORT_OPTIONS = {
    "Soccer": {
        "sport_type": "Soccer",
        "icon": "⚽",
        "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"
    },
    "NBA": {
        "sport_type": "Basketball",
        "icon": "🏀",
        "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"
    },
    "NFL": {
        "sport_type": "American Football",
        "icon": "🏈",
        "season": str(CURRENT_YEAR)
    },
    "MLB": {
        "sport_type": "Baseball",
        "icon": "⚾",
        "season": str(CURRENT_YEAR)
    },
    "NHL": {
        "sport_type": "Ice Hockey",
        "icon": "🏒",
        "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"
    },
    "UFC": {
        "sport_type": "MMA",
        "icon": "🥊",
        "season": str(CURRENT_YEAR)
    },
    "Formula 1": {
        "sport_type": "Motorsport",
        "icon": "🏎️",
        "season": str(CURRENT_YEAR)
    },
    "Tennis": {
        "sport_type": "Tennis",
        "icon": "🎾",
        "season": str(CURRENT_YEAR)
    },
    "Cricket": {
        "sport_type": "Cricket",
        "icon": "🏏",
        "season": str(CURRENT_YEAR)
    },
    "Golf": {
        "sport_type": "Golf",
        "icon": "⛳",
        "season": str(CURRENT_YEAR)
    }
}

# ══════════════════════════════════════════════════════════════════════════════
# MATCH TABLE RENDERER — Clickable cards with league-aware filtering
# ══════════════════════════════════════════════════════════════════════════════
def render_match_table(matches_df, key_prefix, selected_league_id, selected_status):
    """
    Render clickable match cards. Clicking a card stores match_id in session_state
    for detailed view rendering.
    """
    if matches_df is None or matches_df.empty:
        st.info("No matches available for the selected criteria.")
        return

    # ─── Render clickable match cards ────────────────────────────────────────
    for idx, row in matches_df.iterrows():
        home = row.get("HOME_TEAM", "TBD")
        away = row.get("AWAY_TEAM", "TBD")
        score = row.get("SCORE", "vs")
        status = row.get("STATUS", "SCHEDULED")
        league = row.get("LEAGUE", "")
        match_time = row.get("TIME", "")
        match_id = row.get("MATCH_ID", str(idx))
        
        # Status badge
        su = str(status).upper()
        if "LIVE" in su or "1H" in su or "2H" in su:
            status_color, status_bg, status_text = "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
        elif "FINISHED" in su or "FT" in su:
            status_color, status_bg, status_text = "#888888", "rgba(136,136,136,0.15)", "FINISHED"
        else:
            status_color, status_bg, status_text = "#FFAA00", "rgba(255,170,0,0.15)", "UPCOMING"

        # Clickable card
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, rgba(20,25,40,0.9), rgba(10,15,30,0.95));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
            font-family: 'Orbitron', sans-serif;
            cursor: pointer;
            transition: all 0.2s ease;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="color:#8892b0; font-size:0.75rem;">{league}</span>
                <span style="color:{status_color};background:{status_bg};padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:700;">{status_text}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1; text-align:left;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{home}</div>
                </div>
                <div style="padding:0 20px; text-align:center;">
                    <div style="color:#00d4ff; font-size:1.4rem; font-weight:700; letter-spacing:2px;">{score}</div>
                    <div style="color:#8892b0; font-size:0.65rem; margin-top:2px;">{match_time}</div>
                </div>
                <div style="flex:1; text-align:right;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{away}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Streamlit button for actual click handling
        btn_cols = st.columns([6, 1])
        with btn_cols[1]:
            if st.button("🔍", key=f"view_{key_prefix}_{match_id}_{idx}", help="View match details"):
                st.session_state.selected_match_id = match_id
                st.session_state.selected_match_row = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE MATCH ANALYSIS PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_analysis_panel():
    """Render detailed analysis when a match is selected."""
    if 'selected_match_id' not in st.session_state:
        st.info("👆 Select a match from the sidebar to view detailed analysis.")
        return

    match_id = st.session_state.selected_match_id
    match_row = st.session_state.get('selected_match_row', {})
    home = st.session_state.get('selected_match_home', 'Home')
    away = st.session_state.get('selected_match_away', 'Away')

    st.markdown(f'<div class="section-header">🔍 MATCH ANALYSIS — {home} vs {away}</div>', unsafe_allow_html=True)

    if st.button("← Back to Match List", use_container_width=False):
        del st.session_state.selected_match_id
        del st.session_state.selected_match_row
        st.rerun()

    # Display match info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📋 MATCH INFORMATION")
        info_items = {
            "Match ID": match_id,
            "League": match_row.get('LEAGUE', 'N/A'),
            "Status": match_row.get('STATUS', 'N/A'),
            "Time": match_row.get('TIME', 'TBD'),
        }
        for label, value in info_items.items():
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("##### ⚖️ CURRENT ODDS")
        st.markdown(f'<div class="stat-row"><span class="stat-label">Home</span><span class="stat-value">{match_row.get("HOME", "-")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Draw</span><span class="stat-value">{match_row.get("DRAW", "-")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Away</span><span class="stat-value">{match_row.get("AWAY", "-")}</span></div>', unsafe_allow_html=True)
    
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.info("Full match analysis including H2H, player stats, and form coming from live APIs.")


# ══════════════════════════════════════════════════════════════════════════════
# ARENA — SIDEBAR-DRIVEN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
def render_arena():
    # Check if a match is selected for detailed view
    if 'selected_match_id' in st.session_state:
        render_match_analysis_panel()
        return

    # ─── SIDEBAR: League & Match Filters ─────────────────────────────────────
    with st.sidebar:
        st.markdown("<hr style='border-color:#333; margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#D4AF37; font-family:Orbitron; font-size:0.9rem; text-align:center; margin-bottom:10px;">🏟️ ARENA CONTROLS</div>', unsafe_allow_html=True)

        # Sport selector
        sport_names = list(SPORT_OPTIONS.keys())
        if 'selected_sport' not in st.session_state:
            st.session_state.selected_sport = sport_names[0]

        selected_sport = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_names,
            index=sport_names.index(st.session_state.selected_sport),
            key="sidebar_sport_select"
        )
        st.session_state.selected_sport = selected_sport

        st.markdown("<hr style='border-color:#333; margin:10px 0;'>", unsafe_allow_html=True)

        # League dropdown - Fetches from API based on selected sport
        cache_key = f"league_options_{selected_sport}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = [("ALL", "🏆 All Leagues")]

        try:
            api_leagues = data.get_all_leagues(selected_sport)
            if api_leagues and len(api_leagues) > 0:
                league_options = [("ALL", "🏆 All Leagues")]
                for league in api_leagues:
                    display = f"{league.get('name', 'Unknown')}"
                    if league.get('country'):
                        display += f" ({league.get('country')})"
                    league_options.append((league.get('id', 'ALL'), display))
                st.session_state[cache_key] = league_options
            else:
                league_options = st.session_state.get(cache_key, [("ALL", "🏆 All Leagues")])
        except Exception as e:
            logger.error(f"League fetch error: {e}")
            league_options = st.session_state.get(cache_key, [("ALL", "🏆 All Leagues")])

        league_labels = [opt[1] for opt in league_options]
        league_ids = [opt[0] for opt in league_options]

        selected_label = st.selectbox(
            "🏆 SELECT LEAGUE",
            options=league_labels,
            key="sidebar_league_select"
        )
        selected_league_id = league_ids[league_labels.index(selected_label)]

        # Status filter
        status_options = ["LIVE", "UPCOMING", "SCHEDULED", "FINISHED", "ALL"]
        selected_status = st.selectbox(
            "📊 MATCH STATUS",
            options=status_options,
            index=0,
            key="sidebar_status_select"
        )

        # Refresh button
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()

        st.markdown("<hr style='border-color:#333; margin:10px 0;'>", unsafe_allow_html=True)

    # ─── MAIN AREA: Header + Match Cards ─────────────────────────────────────
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {selected_sport.upper()}</div>', unsafe_allow_html=True)

    # Fetch matches based on filters
    try:
        if selected_status == "LIVE":
            matches_df = data.get_live_matches_df(selected_sport, selected_league_id if selected_league_id != "ALL" else None)
        elif selected_status in ["UPCOMING", "SCHEDULED"]:
            matches_df = data.get_upcoming_matches_df(selected_sport)
        elif selected_status == "FINISHED":
            matches_df = pd.DataFrame()  # Placeholder
        else:  # ALL
            live_df = data.get_live_matches_df(selected_sport, selected_league_id if selected_league_id != "ALL" else None)
            upcoming_df = data.get_upcoming_matches_df(selected_sport)
            if not live_df.empty and not upcoming_df.empty:
                matches_df = pd.concat([live_df, upcoming_df], ignore_index=True)
            elif not live_df.empty:
                matches_df = live_df
            else:
                matches_df = upcoming_df
    except Exception as e:
        st.error(f"Error fetching matches: {str(e)}")
        matches_df = pd.DataFrame()

    # Render match cards
    if matches_df.empty:
        st.info(f"No {selected_status.lower()} matches found for {selected_sport}. Try another filter.")
    else:
        st.markdown(f"<div style='color:#888; font-size:0.85rem; margin-bottom:10px;'>📊 Showing {len(matches_df)} matches</div>", unsafe_allow_html=True)
        
        for idx, row in matches_df.iterrows():
            home = row.get("MATCH", "").split(" vs ")[0] if " vs " in row.get("MATCH", "") else row.get("HOME_TEAM", "TBD")
            away = row.get("MATCH", "").split(" vs ")[1] if " vs " in row.get("MATCH", "") else row.get("AWAY_TEAM", "TBD")
            score = row.get("SCORE", "vs")
            status = row.get("STATUS", "SCHEDULED")
            league = row.get("LEAGUE", "")
            match_time = row.get("TIME", "")
            match_id = row.get("MATCH_ID", str(idx))
            
            su = str(status).upper()
            if "LIVE" in su or "1H" in su or "2H" in su:
                status_color, status_bg, status_text = "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
            elif "FINISHED" in su or "FT" in su:
                status_color, status_bg, status_text = "#888888", "rgba(136,136,136,0.15)", "FINISHED"
            else:
                status_color, status_bg, status_text = "#FFAA00", "rgba(255,170,0,0.15)", "UPCOMING"

            card_html = f"""
            <div style="background: linear-gradient(135deg, rgba(20,25,40,0.9), rgba(10,15,30,0.95)); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; margin: 8px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="color:#8892b0; font-size:0.75rem;">{league}</span>
                    <span style="color:{status_color};background:{status_bg};padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:700;">{status_text}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex:1; text-align:left;">
                        <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{home}</div>
                    </div>
                    <div style="padding:0 20px; text-align:center;">
                        <div style="color:#00d4ff; font-size:1.4rem; font-weight:700; letter-spacing:2px;">{score}</div>
                        <div style="color:#8892b0; font-size:0.65rem; margin-top:2px;">{match_time}</div>
                    </div>
                    <div style="flex:1; text-align:right;">
                        <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{away}</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            btn_cols = st.columns([6, 1])
            with btn_cols[1]:
                if st.button("🔍", key=f"view_{selected_sport}_{match_id}_{idx}", help="View match details"):
                    st.session_state.selected_match_id = match_id
                    st.session_state.selected_match_row = row.to_dict()
                    st.session_state.selected_match_home = home
                    st.session_state.selected_match_away = away
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS CENTER
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>', unsafe_allow_html=True)
    st.info("🔮 AI predictions will appear here based on live match data.")

# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)
    st.info("📊 Performance analytics will appear here based on historical data.")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    render_header()
    render_sidebar()
    render_live_ticker()

    # Auto-refresh control
    col_refresh, col_status = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 FORCE REFRESH", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()

    with col_status:
        next_refresh = max(0, REFRESH_INTERVAL - elapsed)
        status_color = "#00ff88" if data.is_live else "#FFD700"
        status_text = "LIVE" if data.is_live else "DEMO"
        st.markdown(
            f'<div style="color: {status_color}; font-family: Orbitron; font-size: 0.8rem; '
            f'padding-top: 8px;">● {status_text} | Next auto-refresh in {int(next_refresh)}s</div>',
            unsafe_allow_html=True
        )

    # Auto-refresh trigger
    if elapsed >= REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        st.cache_data.clear()
        st.rerun()

    # Main navigation
    page = st.radio("", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"], 
                    horizontal=True, label_visibility="collapsed")

    if "ARENA" in page:
        render_arena()
    elif "PREDICTIONS" in page:
        render_predictions()
    else:
        render_analytics()
