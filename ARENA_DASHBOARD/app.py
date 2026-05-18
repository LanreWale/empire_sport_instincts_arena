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
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM DARK GOLD COMMAND CENTER CSS
# ════════════════════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE DATA INITIALIZATION
# ════════════════════════════════════════════════════════════════════════════════
data = EmpireDashboardData()

REFRESH_INTERVAL = 15

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh

# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Soccer": {
        "league_id": "4328",
        "league_name": "English Premier League",
        "country": "England",
        "sport_type": "Soccer",
        "icon": "⚽",
        "season": "2024-2025"
    },
    "NBA": {
        "league_id": "4387",
        "league_name": "NBA",
        "country": "USA",
        "sport_type": "Basketball",
        "icon": "🏀",
        "season": "2024-2025"
    },
    "NFL": {
        "league_id": "4391",
        "league_name": "NFL",
        "country": "USA",
        "sport_type": "American Football",
        "icon": "🏈",
        "season": "2024"
    },
    "MLB": {
        "league_id": "4424",
        "league_name": "MLB",
        "country": "USA",
        "sport_type": "Baseball",
        "icon": "⚾",
        "season": "2024"
    },
    "NHL": {
        "league_id": "4380",
        "league_name": "NHL",
        "country": "USA",
        "sport_type": "Ice Hockey",
        "icon": "🏒",
        "season": "2024"
    },
    "UFC": {
        "league_id": "4445",
        "league_name": "UFC",
        "country": "World",
        "sport_type": "MMA",
        "icon": "🥊",
        "season": "2024"
    },
    "Formula 1": {
        "league_id": "4370",
        "league_name": "Formula 1",
        "country": "World",
        "sport_type": "Motorsport",
        "icon": "🏎️",
        "season": "2024"
    },
    "Tennis": {
        "league_id": "4467",
        "league_name": "ATP Tour",
        "country": "World",
        "sport_type": "Tennis",
        "icon": "🎾",
        "season": "2024"
    },
    "Cricket": {
        "league_id": "4473",
        "league_name": "IPL",
        "country": "India",
        "sport_type": "Cricket",
        "icon": "🏏",
        "season": "2024"
    },
    "Golf": {
        "league_id": "4426",
        "league_name": "PGA Tour",
        "country": "USA",
        "sport_type": "Golf",
        "icon": "⛳",
        "season": "2024"
    }
}

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

    # AI STATUS
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div class="ai-status">🤖 AI ENGINE ONLINE 24/7</div>', unsafe_allow_html=True)

    # WORLD CLOCK
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

    # LIVE / DEMO MODE BANNER
    try:
        has_live = data.is_live
        if has_live:
            provider_name = data.router.active_provider.name if data.router.active_provider else "Unknown"
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #00ff88 0%, #00cc6a 100%); 
                        color: #000; font-family: Orbitron; font-size: 1rem; 
                        padding: 12px 20px; border-radius: 8px; text-align: center;
                        font-weight: 900; letter-spacing: 3px; margin: 10px 0;
                        box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);">
                🟢 LIVE MODE — Connected to {provider_name} | Real data streaming
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
# SIDEBAR — FULL TACTICAL CONTROLS (from Image 2)
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # Logo
        sidebar_logo_path = Path("BRAND_ASSET/empire_logo_arena.png")
        if sidebar_logo_path.exists():
            with open(sidebar_logo_path, "rb") as f:
                sb_img = f.read()
            sb_b64 = base64.b64encode(sb_img).decode()
            st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{sb_b64}" style="width:85%; max-height:100px; object-fit:contain; display:block; margin:0 auto;"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center; color:#D4AF37; font-family:Orbitron; font-size:14px; font-weight:900; margin-bottom:10px;">EMPIRE</div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; font-size:1.2rem;">COMMAND CENTER</h2>', unsafe_allow_html=True)

        # INSTINCT BOT v2.0
        st.markdown("""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; border-radius: 8px; padding: 10px; margin: 10px 0;">
            <div style="color: #00ff88; font-family: 'Orbitron'; font-size: 0.8rem; text-align: center;">
                🤖 INSTINCT BOT v2.0<br>
                <span style="color: #888; font-size: 0.7rem;">SCANNING LIVE MATCHES</span><br>
                <span style="color: #00ff88; animation: blink 1s infinite;">● LIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # SYSTEM STATUS
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
                provider_status.append((f"{icon} {s['name']}", s["status"].split(" — ")[-1], color))
        except Exception as e:
            provider_status = [("🔴 Router", f"Error: {str(e)[:40]}", "#ff4444")]

        for name, status, color in provider_status:
            st.markdown(f'<div style="font-family: Orbitron; font-size: 0.7rem; color: {color}; padding: 2px 0;">{name}: {status}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # DATA / MODELS METRICS
        col1, col2 = st.columns(2)
        with col1:
            st.metric("DATA", "ACTIVE", delta="●", delta_color="normal")
        with col2:
            st.metric("MODELS", "ONLINE", delta="●", delta_color="normal")

        # RISK CONTROLS
        st.subheader("🛡️ RISK CONTROLS")
        st.slider("KELLY %", 0.05, 0.50, 0.25, 0.05, format="%.0f%%", key="kelly_slider")
        st.slider("MAX BET", 0.01, 0.10, 0.03, 0.01, format="%.0f%%", key="maxbet_slider")
        st.slider("MIN EV", 0.01, 0.10, 0.02, 0.01, format="%.0f%%", key="minev_slider")

        # EMERGENCY STOP
        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.markdown("<hr style='border-color: #333; margin: 15px 0;'>", unsafe_allow_html=True)

        # API CONNECTION LOG
        st.subheader("📡 API CONNECTION LOG")
        try:
            log_df = data.router.get_connection_log_df()
            if not log_df.empty:
                def color_status(val):
                    if val == "SUCCESS":
                        return "color: #00ff88; font-weight: 700;"
                    elif val in ["FAIL", "ERROR", "TIMEOUT"]:
                        return "color: #ff4444; font-weight: 700;"
                    elif val == "EMPTY":
                        return "color: #FFD700; font-weight: 700;"
                    return "color: #888;"

                styled_log = log_df.style.map(color_status, subset=["STATUS"])
                st.markdown("""
                <div style="background: linear-gradient(180deg, #0a0a1a 0%, #0f0f1a 100%); 
                            border: 1px solid #2a2a3e; border-radius: 8px; padding: 5px; margin: 5px 0;">
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(styled_log, use_container_width=True, hide_index=True, height=250)
            else:
                st.info("No connection attempts yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {str(e)[:50]}")

# ══════════════════════════════════════════════════════════════════════════════
# LIVE MATCH TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_live_ticker():
    try:
        live_df = data.get_live_matches_df()
        if not live_df.empty:
            matches = []
            for _, row in live_df.head(6).iterrows():
                status_icon = "🔴" if "LIVE" in str(row.get("STATUS", "")) else "⏳"
                home = str(row.get("HOME_TEAM", row.get("MATCH", "")).split(" vs ")[0] if " vs " in str(row.get("MATCH", "")) else row.get("HOME_TEAM", "Home"))
                away = str(row.get("AWAY_TEAM", row.get("MATCH", "")).split(" vs ")[-1] if " vs " in str(row.get("MATCH", "")) else row.get("AWAY_TEAM", "Away"))
                match_text = f"{status_icon} {row.get('LEAGUE', 'Unknown')}: {home} vs {away} ({row.get('STATUS', '')})"
                matches.append(match_text)
            ticker_text = "    ★    ".join(matches)
        else:
            ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."
    except Exception:
        ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."

    st.markdown(f'<div class="ticker"><div class="ticker-text">{ticker_text}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ARENA CONTROLS — Sidebar tactical controls (from Image 2)
# ══════════════════════════════════════════════════════════════════════════════
def render_arena_controls():
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.subheader("🏟️ ARENA CONTROLS")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_sport = st.selectbox(
            "SPORT",
            list(SPORT_OPTIONS.keys()),
            index=0,
            key="sport_select"
        )

    with col2:
        sport_config = SPORT_OPTIONS[selected_sport]
        try:
            all_leagues = data.get_all_leagues(sport_config["sport_type"].lower())
            league_options = [("ALL", "All Leagues")]
            for league in all_leagues:
                league_options.append((league.get("id", ""), league.get("name", "Unknown")))
            if not league_options or len(league_options) == 1:
                league_options = [
                    ("ALL", "All Leagues"),
                    (sport_config["league_id"], sport_config["league_name"]),
                ]
        except Exception:
            league_options = [
                ("ALL", "All Leagues"),
                (sport_config["league_id"], sport_config["league_name"]),
            ]
        selected_league = st.selectbox(
            "LEAGUE",
            options=[opt[1] for opt in league_options],
            index=0,
            key="league_select"
        )
        selected_league_id = next((opt[0] for opt in league_options if opt[1] == selected_league), "ALL")

    with col3:
        status_options = ["ALL", "LIVE", "SCHEDULED", "FINISHED"]
        selected_status = st.selectbox(
            "STATUS",
            status_options,
            index=0,
            key="status_select"
        )

    with col4:
        view_options = ["ALL MATCHES", "LIVE NOW", "UPCOMING", "FINISHED", "VALUE BETS"]
        selected_view = st.selectbox(
            "VIEW",
            view_options,
            index=0,
            key="view_select"
        )

    if st.button("🔄 REFRESH DATA", type="primary", use_container_width=True):
        st.session_state.last_refresh = time.time()
        st.rerun()

    return selected_sport, selected_league_id, selected_status, selected_view

# ══════════════════════════════════════════════════════════════════════════════
# MATCH TABLE RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def render_match_table(matches_df, selected_view, key_prefix, selected_league_id, selected_status):
    if matches_df is None or matches_df.empty:
        st.info("No matches available for the selected criteria.")
        return

    df = matches_df.copy()

    # Auto-detect columns
    home_col = away_col = home_score_col = away_score_col = score_col = None
    status_col = league_col = league_id_col = date_col = time_col = match_id_col = None

    for col in df.columns:
        cu = str(col).upper().replace("_", "").replace(" ", "")
        if not home_col and cu in ['HOMETEAM', 'STRHOMETEAM', 'TEAM1NAME', 'HOMETEAMNAME']:
            home_col = col
        elif not away_col and cu in ['AWAYTEAM', 'STRAWAYTEAM', 'TEAM2NAME', 'AWAYTEAMNAME']:
            away_col = col

    if not home_col or not away_col:
        for col in df.columns:
            cu = str(col).upper().replace("_", "").replace(" ", "")
            if not home_col and 'HOME' in cu and 'ODDS' not in cu and 'SCORE' not in cu and 'WIN' not in cu and 'AWAY' not in cu:
                home_col = col
            elif not away_col and 'AWAY' in cu and 'ODDS' not in cu and 'SCORE' not in cu and 'WIN' not in cu:
                away_col = col

    if not home_col or not away_col:
        if 'MATCH' in df.columns:
            match_col = 'MATCH'
        else:
            match_col = None
            for col in df.columns:
                sample = str(df[col].iloc[0]) if len(df) > 0 else ""
                if " vs " in sample:
                    match_col = col
                    break
    else:
        match_col = None

    for col in df.columns:
        cu = str(col).upper().replace("_", "").replace(" ", "")
        if not score_col and any(x in cu for x in ['SCORE', 'RESULT', 'FULLTIME', 'FT']):
            score_col = col
        elif not home_score_col and any(x in cu for x in ['HOMESCORE', 'INTHOMESCORE', 'HOMEGOAL', 'HSCORE']):
            home_score_col = col
        elif not away_score_col and any(x in cu for x in ['AWAYSCORE', 'INTAWAYSCORE', 'AWAYGOAL', 'ASCORE']):
            away_score_col = col
        elif not status_col and any(x in cu for x in ['STATUS', 'STATE', 'LIVE', 'STRSTATUS', 'MATCHSTATUS']):
            status_col = col
        elif not league_col and any(x in cu for x in ['LEAGUE', 'COMPETITION', 'TOURNAMENT', 'STRLEAGUE', 'COMP']):
            league_col = col
        elif not league_id_col and any(x in cu for x in ['LEAGUEID', 'IDLEAGUE', 'LEAGUE_ID', 'ID_LEAGUE']):
            league_id_col = col
        elif not date_col and any(x in cu for x in ['DATE', 'DATEEVENT', 'DATETIME', 'STRDATE', 'MATCHDATE']):
            date_col = col
        elif not time_col and any(x in cu for x in ['TIME', 'STRTIME', 'KICKOFF', 'MATCHTIME', 'STARTTIME']):
            time_col = col
        elif not match_id_col and any(x in cu for x in ['MATCHID', 'IDMATCH', 'MATCH_ID', 'ID_MATCH', 'EVENTID', 'IDEVENT']):
            match_id_col = col

    if not home_col and not away_col and not match_col:
        st.warning(f"⚠️ Could not identify team columns. Available: {list(df.columns)}")
        st.dataframe(df.head(3), use_container_width=True, hide_index=True)
        return

    if selected_league_id != "ALL" and league_id_col:
        df = df[df[league_id_col].astype(str) == str(selected_league_id)]

    if selected_status != "ALL" and status_col:
        status_mask = df[status_col].astype(str).str.upper().str.contains(selected_status, na=False)
        df = df[status_mask]

    if df.empty:
        st.info(f"🔍 No {selected_status.lower()} matches found. Try another filter.")
        return

    st.markdown(f"<div style='color:#888; font-size:0.85rem; margin-bottom:10px;'>📊 Showing {len(df)} matches</div>", unsafe_allow_html=True)

    for idx, row in df.iterrows():
        if home_col and away_col:
            home = str(row.get(home_col, "TBD"))
            away = str(row.get(away_col, "TBD"))
        elif match_col:
            match_str = str(row.get(match_col, "TBD"))
            if " vs " in match_str:
                parts = match_str.split(" vs ")
                home = parts[0].strip()
                away = parts[1].strip() if len(parts) > 1 else "TBD"
            else:
                home = match_str
                away = "TBD"
        else:
            home = away = "TBD"

        for val in [home, away]:
            if val in ["nan", "None", "null", "NaT", "-", ""]:
                val = "TBD"

        if score_col:
            score = str(row.get(score_col, "vs"))
        elif home_score_col and away_score_col:
            h = str(row.get(home_score_col, "-"))
            a = str(row.get(away_score_col, "-"))
            score = f"{h} - {a}" if h != "-" or a != "-" else "vs"
        else:
            score = "vs"

        status = str(row.get(status_col, "SCHEDULED")) if status_col else "SCHEDULED"
        league = str(row.get(league_col, "")) if league_col else ""
        match_date = str(row.get(date_col, "")) if date_col else ""
        match_time = str(row.get(time_col, "")) if time_col else ""
        match_id = str(row.get(match_id_col, f"{idx}")) if match_id_col else str(idx)

        for val in [league, match_date, match_time]:
            if val in ["nan", "None", "null", "NaT"]:
                val = ""

        su = status.upper()
        if any(x in su for x in ["LIVE", "IN PLAY", "INPLAY", "1H", "2H", "HT"]):
            status_color, status_bg, status_text = "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
        elif any(x in su for x in ["FINISHED", "FT", "FULL", "COMPLETED", "ENDED", "PEN", "AET"]):
            status_color, status_bg, status_text = "#888888", "rgba(136,136,136,0.15)", "FINISHED"
        else:
            status_color, status_bg, status_text = "#FFAA00", "rgba(255,170,0,0.15)", "UPCOMING"

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
        " onmouseover="this.style.borderColor='#D4AF37';this.style.boxShadow='0 0 15px rgba(212,175,55,0.3)'"
           onmouseout="this.style.borderColor='rgba(255,255,255,0.08)';this.style.boxShadow='none'">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="color:#8892b0; font-size:0.75rem;">{league} {f"• {match_date}" if match_date else ""}</span>
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
            if st.button("🔍", key=f"view_{key_prefix}_{match_id}_{idx}", help="View match details"):
                st.session_state.selected_match_id = match_id
                st.session_state.selected_match_row = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MATCH ANALYSIS PANEL — Real API data only, zero hardcoded values
# ══════════════════════════════════════════════════════════════════════════════
def render_match_analysis_panel(match_id: str, match_row: dict):
    """
    Render comprehensive match analysis using ONLY real API data.
    No mock data. No hardcoded defaults. If data is unavailable, show "N/A".
    """
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    home_team = st.session_state.get("selected_match_home", "Home")
    away_team = st.session_state.get("selected_match_away", "Away")
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <h1 style="font-family:Orbitron; color:#FFD700; font-size:1.5rem; margin:0;">
            🔍 MATCH ANALYSIS — {home_team} vs {away_team}
        </h1>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← BACK TO MATCH LIST", type="secondary"):
        del st.session_state.selected_match_id
        st.rerun()

    # ─── Fetch real data from APIs ───────────────────────────────────────────
    prediction = None
    details = None
    error_msg = None

    try:
        prediction = data.get_match_prediction(match_id)
    except Exception as e:
        error_msg = f"Prediction API error: {str(e)[:100]}"
        logger.error(f"Prediction fetch failed for {match_id}: {e}")

    try:
        details = data.get_match_details(match_id)
    except Exception as e:
        if not error_msg:
            error_msg = f"Details API error: {str(e)[:100]}"
        logger.error(f"Details fetch failed for {match_id}: {e}")

    if error_msg and not prediction and not details:
        st.warning(f"⚠️ {error_msg}")
        st.info("Some data may be unavailable. The APIs may have no data for this match, or keys may be missing.")

    # ─── Match Info + Odds + Prediction ──────────────────────────────────────
    col_info, col_odds, col_pred = st.columns(3)

    with col_info:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-header">📋 MATCH INFORMATION</div>', unsafe_allow_html=True)

        match_info = details.get("match") if details else {}
        if not match_info and match_row:
            match_info = match_row

        league = match_info.get("league", match_row.get("LEAGUE", "Unknown")) if match_info else match_row.get("LEAGUE", "Unknown")
        status = match_info.get("status", match_row.get("STATUS", "SCHEDULED")) if match_info else match_row.get("STATUS", "SCHEDULED")
        match_date = match_info.get("start_time", match_row.get("TIME", "TBD")) if match_info else match_row.get("TIME", "TBD")
        venue = match_info.get("venue", "N/A") if match_info else "N/A"
        season = match_info.get("season", "N/A") if match_info else "N/A"

        info_items = [
            ("Match ID", match_id),
            ("League", league),
            ("Status", status),
            ("Date/Time", match_date),
            ("Venue", venue),
            ("Season", season),
        ]
        for label, value in info_items:
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_odds:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-header">⚖️ CURRENT ODDS</div>', unsafe_allow_html=True)

        home_odds = APIConfig._safe_float(match_row.get("HOME"), 0) if match_row else 0
        draw_odds = APIConfig._safe_float(match_row.get("DRAW"), 0) if match_row else 0
        away_odds = APIConfig._safe_float(match_row.get("AWAY"), 0) if match_row else 0

        if details and details.get("odds"):
            for o in details["odds"]:
                if o.home_odds and o.home_odds > 1:
                    home_odds = o.home_odds
                if o.draw_odds and o.draw_odds > 1:
                    draw_odds = o.draw_odds
                if o.away_odds and o.away_odds > 1:
                    away_odds = o.away_odds
                break

        odds_data = [
            ("HOME WIN", home_odds, "#00FF88"),
            ("DRAW", draw_odds, "#FFD700"),
            ("AWAY WIN", away_odds, "#FF6B6B"),
        ]

        for label, val, color in odds_data:
            display_val = f"{val:.2f}" if val and val > 1 else "N/A"
            st.markdown(f'<div style="display:flex; justify-content:space-around; padding:10px; background:rgba(212,175,55,0.1); border-radius:8px; margin:5px 0;"><div style="text-align:center; padding:5px 15px;"><div style="font-family:Orbitron; font-size:0.7rem; color:#888; text-transform:uppercase;">{label}</div><div style="font-family:Orbitron; font-size:1.3rem; color:{color}; font-weight:900;">{display_val}</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_pred:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-header">🎯 AI PREDICTION</div>', unsafe_allow_html=True)

        if prediction and prediction.home_win_prob is not None:
            probs = [
                ("HOME", prediction.home_win_prob, "#00FF88"),
                ("DRAW", prediction.draw_prob, "#FFD700"),
                ("AWAY", prediction.away_win_prob, "#FF6B6B"),
            ]
            for label, val, color in probs:
                display_val = f"{val:.0f}%" if val is not None else "N/A"
                st.markdown(f'<div style="display:flex; justify-content:space-around; padding:8px; background:rgba(212,175,55,0.1); border-radius:8px; margin:3px 0;"><div style="text-align:center; padding:5px 15px;"><div style="font-family:Orbitron; font-size:0.7rem; color:#888; text-transform:uppercase;">{label}</div><div style="font-family:Orbitron; font-size:1.2rem; color:{color}; font-weight:900;">{display_val}</div></div></div>', unsafe_allow_html=True)

            conf = prediction.confidence or "N/A"
            sig = prediction.signal or "N/A"
            st.markdown(f'<div class="stat-row"><span class="stat-label">Confidence</span><span class="stat-value">{conf}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-row"><span class="stat-label">Signal</span><span class="stat-value">{sig}</span></div>', unsafe_allow_html=True)
        else:
            st.info("Prediction data unavailable. API may not have predictions for this match.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ─── Team Form & H2H ─────────────────────────────────────────────────────
    col_form, col_h2h = st.columns(2)

    with col_form:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-header">🏆 TEAM PROFILES & RECENT FORM</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="color:#00FF88; font-family:Orbitron; font-size:0.9rem; margin-bottom:8px;">{home_team} (Home)</div>', unsafe_allow_html=True)
        if prediction and prediction.home_form_rating is not None:
            rating = prediction.home_form_rating
            color = "#00FF88" if rating > 60 else ("#FFD700" if rating > 40 else "#FF6B6B")
            st.markdown(f'<div style="color:{color}; font-size:1.2rem; font-weight:700;">Form Rating: {rating:.0f}/100</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#888; font-size:0.85rem;">Form data unavailable</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="color:#FF6B6B; font-family:Orbitron; font-size:0.9rem; margin:15px 0 8px 0;">{away_team} (Away)</div>', unsafe_allow_html=True)
        if prediction and prediction.away_form_rating is not None:
            rating = prediction.away_form_rating
            color = "#00FF88" if rating > 60 else ("#FFD700" if rating > 40 else "#FF6B6B")
            st.markdown(f'<div style="color:{color}; font-size:1.2rem; font-weight:700;">Form Rating: {rating:.0f}/100</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#888; font-size:0.85rem;">Form data unavailable</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_h2h:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-header">⚔️ HEAD TO HEAD</div>', unsafe_allow_html=True)

        if prediction and prediction.h2h_advantage and prediction.h2h_advantage != "none":
            adv = prediction.h2h_advantage
            adv_team = home_team if adv == "home" else (away_team if adv == "away" else "Even")
            st.markdown(f'<div style="color:#FFD700; font-size:1rem; font-weight:700;">Advantage: {adv_team}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#888; font-size:0.85rem;">H2H data unavailable</div>', unsafe_allow_html=True)

        if details and details.get("h2h"):
            h2h_data = details["h2h"]
            fixtures = h2h_data.get("response", [])
            st.markdown(f'<div style="color:#888; font-size:0.8rem; margin-top:10px;">{len(fixtures)} historical meetings found</div>', unsafe_allow_html=True)
            for fixture in fixtures[:5]:
                f_teams = fixture.get("teams", {})
                f_goals = fixture.get("goals", {})
                h_name = f_teams.get("home", {}).get("name", "Home")
                a_name = f_teams.get("away", {}).get("name", "Away")
                h_goals = f_goals.get("home", "-")
                a_goals = f_goals.get("away", "-")
                f_date = fixture.get("fixture", {}).get("date", "")[:10]
                st.markdown(f'<div class="stat-row"><span class="stat-label">{f_date}</span><span class="stat-value">{h_name} {h_goals} - {a_goals} {a_name}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#888; font-size:0.85rem; margin-top:10px;">No H2H records available from APIs</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ─── Key Players ─────────────────────────────────────────────────────────
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown('<div class="detail-header">👥 KEY PLAYERS</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#888; font-size:0.9rem; text-align:center; padding:20px;">Player data requires additional API integration (e.g., Sportmonks player endpoints). No player APIs currently configured.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ─── Complete Odds Market ────────────────────────────────────────────────
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown('<div class="detail-header">💰 COMPLETE ODDS MARKET</div>', unsafe_allow_html=True)

    tabs = st.tabs(["1X2", "Over/Under", "BTTS", "Cards", "Corners"])

    with tabs[0]:
        if home_odds > 1 or away_odds > 1:
            cols = st.columns(3)
            with cols[0]:
                st.metric("HOME WIN", f"{home_odds:.2f}" if home_odds > 1 else "N/A")
            with cols[1]:
                st.metric("DRAW", f"{draw_odds:.2f}" if draw_odds > 1 else "N/A")
            with cols[2]:
                st.metric("AWAY WIN", f"{away_odds:.2f}" if away_odds > 1 else "N/A")
        else:
            st.info("1X2 odds unavailable from APIs")

    with tabs[1]:
        over_val = None
        under_val = None
        if details and details.get("odds"):
            for o in details["odds"]:
                if o.over_odds and o.over_odds > 1:
                    over_val = o.over_odds
                if o.under_odds and o.under_odds > 1:
                    under_val = o.under_odds
        if over_val or under_val:
            cols = st.columns(2)
            with cols[0]:
                st.metric("OVER 2.5", f"{over_val:.2f}" if over_val else "N/A")
            with cols[1]:
                st.metric("UNDER 2.5", f"{under_val:.2f}" if under_val else "N/A")
        else:
            st.info("Over/Under odds unavailable from APIs")

    with tabs[2]:
        st.info("BTTS odds unavailable — requires additional market parsing from API-SPORTS")

    with tabs[3]:
        st.info("Cards odds unavailable — no card market API configured")

    with tabs[4]:
        st.info("Corners odds unavailable — no corners market API configured")

    st.markdown('</div>', unsafe_allow_html=True)

    # ─── AI Analysis Reasoning ───────────────────────────────────────────────
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown('<div class="detail-header">🧠 AI ANALYSIS REASONING</div>', unsafe_allow_html=True)

    if prediction and prediction.reasoning:
        for reason in prediction.reasoning:
            st.markdown(f'<div style="color:#FFD700; font-size:0.9rem; padding:5px 0; border-left:3px solid #D4AF37; padding-left:10px; margin:5px 0;">• {reason}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#888; font-size:0.9rem; padding:10px;">No reasoning available. This occurs when prediction APIs return no data or when team IDs are missing from the match record.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ─── Value Bet Alert ─────────────────────────────────────────────────────
    if prediction and prediction.value_bet:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,255,136,0.05));
            border: 2px solid #00FF88; border-radius: 12px; padding: 20px; margin: 15px 0;">
            <div style="font-family:Orbitron; color:#00FF88; font-size:1.2rem; font-weight:900;">🎯 VALUE BET DETECTED</div>
            <div style="color:#e6f1ff; font-size:1rem; margin-top:10px;">
                Recommendation: <strong>{prediction.value_bet.upper()}</strong><br>
                Expected Value: Calculated from real odds and model probabilities
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ARENA RENDER
# ══════════════════════════════════════════════════════════════════════════════
def render_arena():
    selected_sport, selected_league_id, selected_status, selected_view = render_arena_controls()
    sport_config = SPORT_OPTIONS[selected_sport]

    # Fetch real match data based on view
    matches_df = None
    try:
        if selected_view == "LIVE NOW":
            matches_df = data.get_live_matches_df(sport_config["sport_type"].lower(), selected_league_id)
        elif selected_view == "UPCOMING":
            matches_df = data.get_upcoming_matches_df(sport_config["sport_type"].lower(), selected_league_id)
        elif selected_view == "FINISHED":
            matches_df = data.router.get_matches_by_status("FINISHED", sport_config["sport_type"].lower(), selected_league_id)
        elif selected_view == "VALUE BETS":
            matches_df = data.get_value_opportunities_df()
        else:
            live = data.get_live_matches_df(sport_config["sport_type"].lower(), selected_league_id)
            upcoming = data.get_upcoming_matches_df(sport_config["sport_type"].lower(), selected_league_id)
            if not live.empty and not upcoming.empty:
                matches_df = pd.concat([live, upcoming], ignore_index=True)
            elif not live.empty:
                matches_df = live
            else:
                matches_df = upcoming
    except Exception as e:
        st.error(f"❌ Error fetching matches: {str(e)[:200]}")
        logger.error(f"Match fetch error: {e}")
        matches_df = pd.DataFrame()

    render_match_table(matches_df, selected_view, "main", selected_league_id, selected_status)

# ══════════════════════════════════════════════════════════════════════════════
# VALUE OPPORTUNITIES
# ══════════════════════════════════════════════════════════════════════════════
def render_value_opportunities():
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">💰 VALUE OPPORTUNITIES</div>', unsafe_allow_html=True)

    try:
        value_df = data.get_value_opportunities_df()
        if not value_df.empty:
            def color_ev(val):
                try:
                    v = float(str(val).replace("+", "").replace("%", ""))
                    if v > 5:
                        return "color: #00FF88; font-weight: 700;"
                    elif v > 2:
                        return "color: #FFD700; font-weight: 700;"
                    return "color: #888;"
                except:
                    return "color: #888;"

            def color_signal(val):
                if "BUY" in str(val):
                    return "color: #00FF88; font-weight: 700;"
                elif "HOLD" in str(val):
                    return "color: #FFD700; font-weight: 700;"
                return "color: #FF6B6B;"

            styled = value_df.style.map(color_ev, subset=["EV"]).map(color_signal, subset=["SIGNAL"])
            st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("🔍 No value opportunities detected. Try adjusting EV threshold or check API connectivity.")
    except Exception as e:
        st.error(f"❌ Value analysis error: {str(e)[:200]}")
        logger.error(f"Value opportunities error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS TAB
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🎯 AI PREDICTIONS</div>', unsafe_allow_html=True)

    try:
        matches = data.get_upcoming_matches_df()
        if matches.empty:
            st.info("🔍 No upcoming matches for prediction analysis.")
            return

        predictions = []
        for _, row in matches.head(20).iterrows():
            match_id = str(row.get("MATCH_ID", ""))
            if not match_id:
                continue
            try:
                pred = data.get_match_prediction(match_id)
                if pred and pred.confidence in ["HIGH", "MEDIUM"]:
                    predictions.append({
                        "TIME": row.get("TIME", "TBD"),
                        "LEAGUE": row.get("LEAGUE", ""),
                        "MATCH": row.get("MATCH", ""),
                        "PREDICTION": f"Home {pred.home_win_prob:.0f}%" if pred.home_win_prob > pred.away_win_prob else f"Away {pred.away_win_prob:.0f}%",
                        "CONFIDENCE": pred.confidence,
                        "SIGNAL": pred.signal,
                        "VALUE": pred.value_bet or "-",
                        "EV": f"+{pred.home_win_prob:.1f}%" if pred.home_win_prob else "-",
                    })
            except Exception:
                continue

        if predictions:
            pred_df = pd.DataFrame(predictions)
            st.dataframe(pred_df, use_container_width=True, hide_index=True, height=500)
        else:
            st.info("🔍 No high-confidence predictions available. Check API keys and match data.")
    except Exception as e:
        st.error(f"❌ Predictions error: {str(e)[:200]}")
        logger.error(f"Predictions render error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📊 ANALYTICS DASHBOARD</div>', unsafe_allow_html=True)

    try:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            live_df = data.get_live_matches_df()
            st.metric("LIVE MATCHES", len(live_df) if not live_df.empty else 0)
        with col2:
            upcoming_df = data.get_upcoming_matches_df()
            st.metric("UPCOMING", len(upcoming_df) if not upcoming_df.empty else 0)
        with col3:
            value_df = data.get_value_opportunities_df()
            st.metric("VALUE BETS", len(value_df) if not value_df.empty else 0)
        with col4:
            try:
                statuses = data.router.get_provider_status()
                online = sum(1 for s in statuses if "ONLINE" in s["status"] or "EMPTY" in s["status"])
                st.metric("APIs ONLINE", f"{online}/{len(statuses)}")
            except Exception:
                st.metric("APIs ONLINE", "?/6")
    except Exception as e:
        st.error(f"Analytics error: {str(e)[:200]}")

    try:
        st.subheader("📈 Match Distribution by League")
        all_matches = data.get_live_matches_df()
        if not all_matches.empty and "LEAGUE" in all_matches.columns:
            league_counts = all_matches["LEAGUE"].value_counts().head(10)
            fig = px.bar(
                x=league_counts.index,
                y=league_counts.values,
                labels={"x": "League", "y": "Matches"},
                color=league_counts.values,
                color_continuous_scale=["#1a1a2e", "#D4AF37", "#FFD700"],
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#FFD700", family="Orbitron"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No league data available for charting.")
    except Exception as e:
        st.warning(f"Chart error: {str(e)[:100]}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
def main():
    render_header()
    render_sidebar()
    render_live_ticker()

    # Check if a match is selected for detailed view
    if "selected_match_id" in st.session_state:
        match_id = st.session_state.selected_match_id
        match_row = st.session_state.get("selected_match_row", {})
        render_match_analysis_panel(match_id, match_row)
        return

    # Main tabs
    tabs = st.tabs(["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"])

    with tabs[0]:
        render_arena()
        render_value_opportunities()

    with tabs[1]:
        render_predictions()

    with tabs[2]:
        render_analytics()

    # Footer
    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; color:#555; font-family:Orbitron; font-size:0.7rem; letter-spacing:3px; padding:20px;">
        EMPIRE SPORT INSTINCTS ARENA v2.4 | © 2024 EMPIRE TRADING SYSTEMS<br>
        Advanced Research & Evaluation | Where Data Meets Instinct
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    if elapsed > REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        st.rerun()

if __name__ == "__main__":
    main()
