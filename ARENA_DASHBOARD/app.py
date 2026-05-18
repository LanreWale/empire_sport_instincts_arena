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
        svg = """<<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 140"><defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#D4AF37;stop-opacity:1"/><stop offset="100%" style="stop-color:#FFD700;stop-opacity:1"/></linearGradient></defs><rect width="900" height="140" rx="12" fill="#16213e" stroke="#D4AF37" stroke-width="2"/><text x="450" y="85" font-family="Arial Black, Impact, sans-serif" font-size="52" fill="url(#g1)" text-anchor="middle" font-weight="900" letter-spacing="6">EMPIRE SPORT INSTINCTS ARENA</text><text x="450" y="115" font-family="Arial, sans-serif" font-size="16" fill="#888" text-anchor="middle" letter-spacing="10">ELITE TRADING DASHBOARD v2.4</text></svg>"""
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

        # ─── LIVE MATCH COUNT (REAL API) ───
        live_count = 0
        try:
            live_df = data.get_live_matches_df()
            if live_df is not None and not live_df.empty:
                live_count = len(live_df)
        except Exception:
            live_count = 0

        st.markdown(f"""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; border-radius: 8px; padding: 10px; margin: 10px 0;">
            <div style="color: #00ff88; font-family: 'Orbitron'; font-size: 0.8rem; text-align: center;">
                🤖 INSTINCT BOT v2.0<br>
                <span style="color: #888; font-size: 0.7rem;">SCANNING {live_count} LIVE MATCHES</span><br>
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
                provider_status.append((f"{icon} {s['name']}", s["status"].split(" — ")[-1], color))
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
                render_api_log_table(log_df)
            else:
                st.info("No connection attempts yet.")
        except Exception as e:
            st.warning(f"Log unavailable: {str(e)[:50]}")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM DARK API LOG TABLE (guaranteed background color)
# ══════════════════════════════════════════════════════════════════════════════
def render_api_log_table(log_df):
    """Render connection log as custom HTML to bypass Streamlit dataframe theming."""
    html = '<div style="background:#1a1a2e; border:1px solid #2a2a3e; border-radius:8px; overflow:hidden;">'
    html += '<table style="width:100%; border-collapse:collapse; font-family: Rajdhani, sans-serif; font-size:0.82rem;">'
    
    # Header row
    html += '<tr style="background:linear-gradient(135deg, #D4AF37 0%, #B8860B 100%); color:#000; font-family:Orbitron; font-weight:900; font-size:0.78rem; text-transform:uppercase; letter-spacing:1px;">'
    for col in log_df.columns:
        html += f'<th style="padding:10px 8px; text-align:center; border-bottom:3px solid #FFD700;">{col}</th>'
    html += '</tr>'
    
    # Data rows
    for _, row in log_df.iterrows():
        status = str(row.get("STATUS", ""))
        if status == "SUCCESS":
            status_color = "#00ff88"
        elif status in ["FAIL", "ERROR", "TIMEOUT"]:
            status_color = "#ff4444"
        elif status == "EMPTY":
            status_color = "#FFD700"
        else:
            status_color = "#888"
        
        html += '<tr style="border-bottom:1px solid #2a2a3e;">'
        for col in log_df.columns:
            val = row.get(col, "")
            if col == "STATUS":
                html += f'<td style="padding:8px; color:{status_color}; text-align:center; font-weight:700;">{val}</td>'
            else:
                html += f'<td style="padding:8px; color:#FFD700; text-align:center; font-weight:500;">{val}</td>'
        html += '</tr>'
    
    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

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
                match_text = f"{status_icon} {row.get('LEAGUE', 'Unknown')}: {row.get('MATCH', 'vs')} ({row.get('STATUS', '')})"
                matches.append(match_text)
            ticker_text = "    ★    ".join(matches)
        else:
            ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."
    except Exception:
        ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."

    st.markdown(f'<div class="ticker"><div class="ticker-text">{ticker_text}</div></div>', unsafe_allow_html=True)

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
# ROBUST DATAFRAME LEAGUE FILTER (auto-detects columns)
# ══════════════════════════════════════════════════════════════════════════════
def filter_dataframe_by_league(df, selected_league_id, league_options):
    """
    Client-side league filter that auto-detects league_id or league_name columns.
    Returns the filtered dataframe. If selected_league_id is ALL, returns untouched.
    """
    if selected_league_id == "ALL" or df is None or df.empty:
        return df
    
    # ─── Strategy 1: Filter by league_id column ─────────────────────────────
    for col in df.columns:
        cu = str(col).upper().replace("_", "").replace(" ", "")
        if any(x in cu for x in ['LEAGUEID', 'IDLEAGUE', 'LEAGUE_ID', 'ID_LEAGUE']):
            try:
                mask = df[col].astype(str) == str(selected_league_id)
                if mask.any():
                    return df[mask]
            except Exception:
                continue
    
    # ─── Strategy 2: Filter by league name column ─────────────────────────────
    league_name = None
    for lid, label in league_options:
        if str(lid) == str(selected_league_id):
            league_name = label.replace("🏆 ", "").split(" (")[0]
            break
    
    if league_name:
        for col in df.columns:
            cu = str(col).upper().replace("_", "").replace(" ", "")
            if any(x in cu for x in ['LEAGUE', 'COMPETITION', 'TOURNAMENT', 'STRLEAGUE', 'COMP']):
                try:
                    mask = df[col].astype(str).str.contains(league_name, case=False, na=False)
                    if mask.any():
                        return df[mask]
                except Exception:
                    continue
    
    # If nothing matched, return unfiltered so user sees data instead of blank
    return df

# ══════════════════════════════════════════════════════════════════════════════
# MATCH TABLE RENDERER — Clickable cards with league-aware filtering
# ══════════════════════════════════════════════════════════════════════════════
def render_match_table(matches_df, selected_view, key_prefix, selected_league_id, selected_status):
    """
    Render clickable match cards. Clicking a card stores match_id in session_state
    for detailed view rendering.
    """
    if matches_df is None or matches_df.empty:
        st.info("No matches available for the selected criteria.")
        return

    df = matches_df.copy()
    
    # ─── Auto-detect columns ─────────────────────────────────────────────────
    home_col = away_col = home_score_col = away_score_col = score_col = None
    status_col = league_col = league_id_col = date_col = time_col = match_id_col = None

    for col in df.columns:
        cu = str(col).upper().replace("_", "").replace(" ", "")
        if not home_col and any(x in cu for x in ['HOME', 'HTEAM', 'TEAM1', 'T1', 'STRHOMETEAM', 'LOCAL', 'HOMETEAM']):
            home_col = col
        elif not away_col and any(x in cu for x in ['AWAY', 'ATEAM', 'TEAM2', 'T2', 'STRAWAYTEAM', 'VISITOR', 'AWAYTEAM']):
            away_col = col
        elif not score_col and any(x in cu for x in ['SCORE', 'RESULT', 'VS', 'FULLTIME', 'FT']):
            score_col = col
        elif not home_score_col and any(x in cu for x in ['HOMESCORE', 'INTHOMESCORE', 'HOME_GOAL', 'HSCORE']):
            home_score_col = col
        elif not away_score_col and any(x in cu for x in ['AWAYSCORE', 'INTAWAYSCORE', 'AWAY_GOAL', 'ASCORE']):
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

    # ─── Fallback debug ────────────────────────────────────────────────────────
    if not home_col or not away_col:
        st.warning(f"⚠️ Could not identify team columns. Available: {list(df.columns)}")
        st.dataframe(df.head(3), use_container_width=True, hide_index=True)
        return

    # ─── Client-side league filter (defensive second pass) ────────────────────
    if selected_league_id != "ALL" and league_id_col:
        df = df[df[league_id_col].astype(str) == str(selected_league_id)]
    elif selected_league_id != "ALL" and league_col:
        # If we have no league_id column but have a name column, we can't filter
        # precisely here because we don't have league_options in scope.
        pass

    # ─── Client-side status filter ───────────────────────────────────────────
    if selected_status != "ALL" and status_col:
        status_mask = df[status_col].astype(str).str.upper().str.contains(
            selected_status, na=False
        )
        df = df[status_mask]

    if df.empty:
        st.info(f"🔍 No {selected_status.lower()} matches found for this league. Try another filter.")
        return

    st.markdown(f"<div style='color:#888; font-size:0.85rem; margin-bottom:10px;'>📊 Showing {len(df)} matches</div>", unsafe_allow_html=True)

    # ─── Render clickable match cards ────────────────────────────────────────
    for idx, row in df.iterrows():
        home = str(row.get(home_col, "TBD"))
        away = str(row.get(away_col, "TBD"))
        
        # Score
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
            if val in ["nan", "None", "null", "NaT"]: val = ""
        
        # Status badge
        su = status.upper()
        if any(x in su for x in ["LIVE", "IN PLAY", "INPLAY", "1H", "2H", "HT"]):
            status_color, status_bg, status_text = "#00FF88", "rgba(0,255,136,0.15)", "● LIVE"
        elif any(x in su for x in ["FINISHED", "FT", "FULL", "COMPLETED", "ENDED", "PEN", "AET"]):
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
# COMPREHENSIVE MATCH ANALYSIS PANEL — ALL DATA FROM LIVE API
# ══════════════════════════════════════════════════════════════════════════════
def render_match_analysis_panel():
    """Render detailed analysis when a match is selected from the sidebar."""
    if 'selected_match_id' not in st.session_state:
        st.info("👆 Select a match from the sidebar to view detailed analysis.")
        return

    match_id = st.session_state.selected_match_id
    match_row = st.session_state.get('selected_match_row', {})
    home = st.session_state.get('selected_match_home', 'Home')
    away = st.session_state.get('selected_match_away', 'Away')

    st.markdown(f'<div class="section-header">🔍 MATCH ANALYSIS — {home} vs {away}</div>', unsafe_allow_html=True)

    # Back button
    if st.button("← Back to Match List", use_container_width=False):
        del st.session_state.selected_match_id
        del st.session_state.selected_match_row
        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # FETCH DETAILED DATA FROM API
    # ══════════════════════════════════════════════════════════════════════════
    details = {"found": False}
    prediction = None
    try:
        details = data.router.get_match_details(match_id) or {"found": False}
        prediction = data.get_match_prediction(match_id)
    except Exception as e:
        st.warning(f"Detailed data unavailable: {str(e)[:80]}")

    # ══════════════════════════════════════════════════════════════════════════
    # TOP ROW: Match Info + Odds + Prediction
    # ══════════════════════════════════════════════════════════════════════════
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown("##### 📋 MATCH INFORMATION")
        info_items = {
            "Match ID": match_id,
            "League": match_row.get('LEAGUE', match_row.get('league', 'N/A')),
            "Status": match_row.get('STATUS', match_row.get('status', 'N/A')),
            "Date": match_row.get('DATE', match_row.get('dateEvent', match_row.get('match_date', '-'))),
            "Time": match_row.get('TIME', match_row.get('strTime', match_row.get('match_time', '-'))),
        }
        for label, value in info_items.items():
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("##### ⚖️ CURRENT ODDS")
        home_odds = match_row.get('HOME', match_row.get('home_odds', '-'))
        draw_odds = match_row.get('DRAW', match_row.get('draw_odds', '-'))
        away_odds = match_row.get('AWAY', match_row.get('away_odds', '-'))
        
        odds_html = '<div class="odds-row">'
        odds_html += f'<div class="odds-box"><div class="odds-label">1 (Home)</div><div class="odds-value">{home_odds}</div></div>'
        odds_html += f'<div class="odds-box"><div class="odds-label">X (Draw)</div><div class="odds-value">{draw_odds}</div></div>'
        odds_html += f'<div class="odds-box"><div class="odds-label">2 (Away)</div><div class="odds-value">{away_odds}</div></div>'
        odds_html += '</div>'
        st.markdown(odds_html, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 🎯 AI PREDICTION")
        if prediction:
            conf_color = "#00FF88" if prediction.confidence > 70 else "#FFD700" if prediction.confidence > 50 else "#FF4444"
            st.markdown(f'<div style="font-size:2rem; color:{conf_color}; font-weight:900; text-align:center;">{prediction.confidence:.0f}%</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; color:#888; font-size:0.8rem;">Confidence</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="margin-top:10px; padding:8px; background:rgba(0,255,136,0.1); border-radius:6px; text-align:center; color:#00FF88; font-family:Orbitron;">Signal: {prediction.signal.upper()}</div>', unsafe_allow_html=True)
        else:
            st.info("Prediction loading...")

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TEAM PROFILES & FORM — LIVE API DATA
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 🏆 TEAM PROFILES & RECENT FORM")

    team_col1, team_col2 = st.columns(2)

    # ─── HOME TEAM ───
    with team_col1:
        home_form = details.get("home_form", []) if isinstance(details, dict) else []
        home_stats = details.get("home_stats", {}) if isinstance(details, dict) else {}
        
        st.markdown(f'<div style="background:rgba(0,255,136,0.05); border:1px solid rgba(0,255,136,0.2); border-radius:10px; padding:15px;">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#00FF88; font-family:Orbitron; font-size:1.1rem; margin-bottom:10px;">{home} (Home)</div>', unsafe_allow_html=True)
        
        if home_form:
            form_html = "".join([
                f'<span style="display:inline-block; width:28px; height:28px; line-height:28px; text-align:center; border-radius:4px; margin-right:4px; font-size:0.75rem; font-weight:700; {"background:#00FF88;color:#000;" if r=="W" else "background:#FFD700;color:#000;" if r=="D" else "background:#FF4444;color:#fff;"}">{r}</span>' 
                for r in home_form[:5]
            ])
            st.markdown(f'<div style="margin-bottom:10px;">{form_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#666; font-size:0.8rem; margin-bottom:10px;">Form data unavailable</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="stat-row"><span class="stat-label">Home Record</span><span class="stat-value">{home_stats.get("record", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Goals Scored</span><span class="stat-value">{home_stats.get("goals_for", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Goals Conceded</span><span class="stat-value">{home_stats.get("goals_against", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Clean Sheets</span><span class="stat-value">{home_stats.get("clean_sheets", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ─── AWAY TEAM ───
    with team_col2:
        away_form = details.get("away_form", []) if isinstance(details, dict) else []
        away_stats = details.get("away_stats", {}) if isinstance(details, dict) else {}
        
        st.markdown(f'<div style="background:rgba(255,68,68,0.05); border:1px solid rgba(255,68,68,0.2); border-radius:10px; padding:15px;">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#FF4444; font-family:Orbitron; font-size:1.1rem; margin-bottom:10px;">{away} (Away)</div>', unsafe_allow_html=True)
        
        if away_form:
            form_html = "".join([
                f'<span style="display:inline-block; width:28px; height:28px; line-height:28px; text-align:center; border-radius:4px; margin-right:4px; font-size:0.75rem; font-weight:700; {"background:#00FF88;color:#000;" if r=="W" else "background:#FFD700;color:#000;" if r=="D" else "background:#FF4444;color:#fff;"}">{r}</span>' 
                for r in away_form[:5]
            ])
            st.markdown(f'<div style="margin-bottom:10px;">{form_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#666; font-size:0.8rem; margin-bottom:10px;">Form data unavailable</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="stat-row"><span class="stat-label">Away Record</span><span class="stat-value">{away_stats.get("record", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Goals Scored</span><span class="stat-value">{away_stats.get("goals_for", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Goals Conceded</span><span class="stat-value">{away_stats.get("goals_against", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-row"><span class="stat-label">Clean Sheets</span><span class="stat-value">{away_stats.get("clean_sheets", "N/A")}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # HEAD TO HEAD & PLAYER PROFILES — LIVE API DATA
    # ══════════════════════════════════════════════════════════════════════════
    h2h_col, player_col = st.columns(2)

    with h2h_col:
        st.markdown("##### ⚔️ HEAD TO HEAD")
        h2h_data = details.get("h2h", []) if isinstance(details, dict) else []
        
        if h2h_data:
            for h in h2h_data[:5]:
                date_val = h.get("date", "N/A")
                score_val = h.get("score", "N/A")
                comp_val = h.get("competition", "N/A")
                st.markdown(f'<div class="stat-row"><span class="stat-label">{date_val}</span><span class="stat-value">{score_val}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#666; font-size:0.7rem; margin-bottom:6px;">{comp_val}</div>', unsafe_allow_html=True)
        else:
            st.info("No head-to-head data available from API.")

    with player_col:
        st.markdown("##### 👤 KEY PLAYERS")
        players = details.get("players", []) if isinstance(details, dict) else []
        
        if players:
            for p in players[:5]:
                team_color = "#00FF88" if p.get("team") == home else "#FF4444"
                st.markdown(f'''
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #2a2a3e;">
                        <div>
                            <div style="color:#e6f1ff; font-weight:600;">{p.get("name", "Unknown")}</div>
                            <div style="color:{team_color}; font-size:0.75rem;">{p.get("team", "N/A")}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#FFD700; font-family:Orbitron; font-size:0.9rem;">⭐ {p.get("rating", "-")}</div>
                            <div style="color:#888; font-size:0.7rem;">⚽ {p.get("goals", 0)} | 🅰️ {p.get("assists", 0)}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No player data available from API.")

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # ALL ODDS CATEGORIES — LIVE API DATA
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 💰 COMPLETE ODDS MARKET")
    odds_data = details.get("odds", {}) if isinstance(details, dict) else {}

    odds_tabs = st.tabs(["1X2", "Over/Under", "BTTS", "Cards", "Corners", "Asian Handicap"])

    with odds_tabs[0]:
        ox = odds_data.get("1x2", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Home Win", ox.get("home", match_row.get('HOME', "-")), ox.get("home_delta", ""))
        c2.metric("Draw", ox.get("draw", match_row.get('DRAW', "-")), ox.get("draw_delta", ""))
        c3.metric("Away Win", ox.get("away", match_row.get('AWAY', "-")), ox.get("away_delta", ""))

    with odds_tabs[1]:
        ou = odds_data.get("over_under", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Over 0.5", ou.get("o0_5", "-"), ou.get("o0_5_delta", ""))
        c2.metric("Over 1.5", ou.get("o1_5", "-"), ou.get("o1_5_delta", ""))
        c3.metric("Over 2.5", ou.get("o2_5", "-"), ou.get("o2_5_delta", ""))
        c4.metric("Over 3.5", ou.get("o3_5", "-"), ou.get("o3_5_delta", ""))

    with odds_tabs[2]:
        btts = odds_data.get("btts", {})
        c1, c2 = st.columns(2)
        c1.metric("BTTS Yes", btts.get("yes", "-"), btts.get("yes_prob", ""))
        c2.metric("BTTS No", btts.get("no", "-"), btts.get("no_prob", ""))

    with odds_tabs[3]:
        cards = odds_data.get("cards", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Over 2.5 Cards", cards.get("o2_5", "-"), cards.get("o2_5_label", ""))
        c2.metric("Over 4.5 Cards", cards.get("o4_5", "-"), cards.get("o4_5_label", ""))
        c3.metric("Home More Cards", cards.get("home_more", "-"), cards.get("home_more_label", ""))

    with odds_tabs[4]:
        corners = odds_data.get("corners", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Over 8.5", corners.get("o8_5", "-"), corners.get("o8_5_label", ""))
        c2.metric("Over 10.5", corners.get("o10_5", "-"), corners.get("o10_5_label", ""))
        c3.metric("Over 12.5", corners.get("o12_5", "-"), corners.get("o12_5_label", ""))

    with odds_tabs[5]:
        ah = odds_data.get("asian_handicap", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Home -1.5", ah.get("home_m1_5", "-"), ah.get("home_m1_5_label", ""))
        c2.metric("Home -0.5", ah.get("home_m0_5", "-"), ah.get("home_m0_5_label", ""))
        c3.metric("Away +1.5", ah.get("away_p1_5", "-"), ah.get("away_p1_5_label", ""))

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # AI REASONING — LIVE API DATA ONLY
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 🧠 AI ANALYSIS REASONING")
    if prediction and hasattr(prediction, 'reasoning') and prediction.reasoning:
        for reason in prediction.reasoning:
            st.markdown(f'<div style="padding:8px; margin:4px 0; background:rgba(212,175,55,0.05); border-left:3px solid #D4AF37; border-radius:0 6px 6px 0; color:#e6f1ff;">• {reason}</div>', unsafe_allow_html=True)
    else:
        st.info("AI reasoning pending. Ensure prediction models are connected to the API.")


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

        # Sport selector moved to sidebar
        sport_names = list(SPORT_OPTIONS.keys())
        if 'selected_sport' not in st.session_state:
            st.session_state.selected_sport = sport_names[0]

        selected_sport = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_names,
            index=sport_names.index(st.session_state.selected_sport),
            key="sidebar_sport_select"
        )
        
        # If sport changed, clear cached league options for this sport to force fresh fetch
        new_key_prefix = selected_sport.replace(" ", "_").replace("⚽", "f").replace("🏀", "b").replace("🏈", "nfl").replace("🎾", "t").replace("🏒", "nhl")
        old_key_prefix = st.session_state.selected_sport.replace(" ", "_").replace("⚽", "f").replace("🏀", "b").replace("🏈", "nfl").replace("🎾", "t").replace("🏒", "nhl") if 'selected_sport' in st.session_state else None
        
        if old_key_prefix and old_key_prefix != new_key_prefix:
            st.session_state.pop(f'league_options_{new_key_prefix}', None)
        
        st.session_state.selected_sport = selected_sport

        sport_key = SPORT_OPTIONS[selected_sport]
        key_prefix = new_key_prefix

        st.markdown("<hr style='border-color:#333; margin:10px 0;'>", unsafe_allow_html=True)

        # League dropdown — ROBUST FETCH WITH FALLBACK
        if f'league_options_{key_prefix}' not in st.session_state:
            st.session_state[f'league_options_{key_prefix}'] = [("ALL", "🏆 All Leagues")]

        league_options = st.session_state.get(f'league_options_{key_prefix}', [("ALL", "🏆 All Leagues")])
        
        # Only hit the API if we still only have the default entry
        if len(league_options) <= 1:
            try:
                # Try 1: pass the sport config dict (legacy behavior)
                api_leagues = data.get_all_leagues(sport_key)
                # Try 2: if we got 0 or 1 leagues, the API may expect a string like "Soccer"
                if not api_leagues or len(api_leagues) <= 1:
                    api_leagues = data.get_all_leagues(sport_key.get("sport_type", selected_sport))
                
                if api_leagues and len(api_leagues) > 1:
                    fresh_options = [("ALL", "🏆 All Leagues")]
                    for league in api_leagues:
                        display = f"{league.get('name', 'Unknown')}"
                        if league.get('country'):
                            display += f" ({league['country']})"
                        fresh_options.append((league.get('id', '0'), display))
                    league_options = fresh_options
                    st.session_state[f'league_options_{key_prefix}'] = league_options
            except Exception as e:
                # Silently fall back to cached/default
                pass

        league_labels = [opt[1] for opt in league_options]
        league_ids = [opt[0] for opt in league_options]

        current_id = st.session_state.get(f'league_id_{key_prefix}', "ALL")
        try:
            current_index = league_ids.index(current_id)
        except ValueError:
            current_index = 0

        selected_label = st.selectbox(
            "🏆 SELECT LEAGUE",
            options=league_labels,
            index=current_index,
            key=f"sidebar_league_{key_prefix}"
        )
        selected_league_id = league_ids[league_labels.index(selected_label)]
        st.session_state[f'league_id_{key_prefix}'] = selected_league_id

        # Status filter
        status_options = ["ALL", "LIVE", "SCHEDULED", "FINISHED"]
        selected_status = st.selectbox(
            "📊 MATCH STATUS",
            options=status_options,
            key=f"sidebar_status_{key_prefix}"
        )

        # Refresh button
        if st.button("🔄 REFRESH DATA", use_container_width=True, key=f"sidebar_refresh_{key_prefix}"):
            st.session_state.last_refresh = time.time()
            st.session_state.pop(f'league_options_{key_prefix}', None)
            st.cache_data.clear()
            st.rerun()

        st.markdown("<hr style='border-color:#333; margin:10px 0;'>", unsafe_allow_html=True)

    # ─── MAIN AREA: Header + Match Cards ─────────────────────────────────────
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {selected_sport.upper()}</div>', unsafe_allow_html=True)

    # Fetch matches based on filters — NO HARDCODED COLUMN NAMES
    try:
        if selected_status == "LIVE":
            raw_df = data.get_live_matches_df(sport_key, selected_league_id)
            matches_df = filter_dataframe_by_league(raw_df, selected_league_id, league_options)
        elif selected_status == "SCHEDULED":
            raw_df = data.get_upcoming_matches_df(sport_key)
            matches_df = filter_dataframe_by_league(raw_df, selected_league_id, league_options)
        elif selected_status == "FINISHED":
            raw_df = data.router.get_matches_by_status("FINISHED", sport_key, selected_league_id)
            matches_df = filter_dataframe_by_league(raw_df, selected_league_id, league_options)
        else:  # ALL
            live_raw = data.get_live_matches_df(sport_key, selected_league_id)
            sched_raw = data.get_upcoming_matches_df(sport_key)
            live_df = filter_dataframe_by_league(live_raw, selected_league_id, league_options)
            sched_df = filter_dataframe_by_league(sched_raw, selected_league_id, league_options)
            if not live_df.empty and not sched_df.empty:
                matches_df = pd.concat([live_df, sched_df], ignore_index=True)
            elif not live_df.empty:
                matches_df = live_df
            else:
                matches_df = sched_df
    except Exception as e:
        st.error(f"Error fetching matches: {str(e)[:100]}")
        matches_df = pd.DataFrame()

    # Render match cards
    render_match_table(matches_df, "CARD VIEW", key_prefix, selected_league_id, selected_status)

# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS CENTER
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔮 UPCOMING", "📜 HISTORY", "⚙️ CALIBRATION"])

    with tab1:
        try:
            upcoming_df = data.get_upcoming_matches_df()
            if not upcoming_df.empty:
                st.dataframe(upcoming_df, use_container_width=True, hide_index=True)
            else:
                st.info("🔮 No upcoming predictions available.")
        except Exception:
            st.info("🔮 No upcoming predictions available.")

    with tab2:
        st.info("📜 Prediction history requires database integration.")
        history = pd.DataFrame({"DATE": [], "MATCH": [], "PREDICTED": [], "RESULT": [], "P/L": []})
        st.dataframe(history, use_container_width=True, hide_index=True)

    with tab3:
        st.info("⚙️ Model calibration analysis.")
        cal_data = pd.DataFrame({"BIN": [], "PREDICTED": [], "ACTUAL": [], "BETS": []})
        st.dataframe(cal_data, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)
    st.info("📊 Performance analytics require database integration.")

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
