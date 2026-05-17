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

# EMPIRE Live Data Integration — imports from project root
from empire_data_layer import EmpireDashboardData, APIConfig

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

    /* Detail panel styling */
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

        st.markdown("""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; border-radius: 8px; padding: 10px; margin: 10px 0;">
            <div style="color: #00ff88; font-family: 'Orbitron'; font-size: 0.8rem; text-align: center;">
                🤖 INSTINCT BOT v2.0<br>
                <span style="color: #888; font-size: 0.7rem;">SCANNING 847 MATCHES</span><br>
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
                def color_status(val):
                    if val == "SUCCESS":
                        return "color: #00ff88; font-weight: 700;"
                    elif val in ["FAIL", "ERROR", "TIMEOUT"]:
                        return "color: #ff4444; font-weight: 700;"
                    elif val == "EMPTY":
                        return "color: #FFD700; font-weight: 700;"
                    return "color: #888;"

                styled_log = log_df.style.map(color_status, subset=["STATUS"])
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
                match_text = f"{status_icon} {row.get('LEAGUE', 'Unknown')}: {row.get('MATCH', 'vs')} ({row.get('STATUS', '')})"
                matches.append(match_text)
            ticker_text = "    ★    ".join(matches)
        else:
            ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."
    except Exception:
        ticker_text = "📡 Connecting to live data feeds...    ★    🔄 Refreshing match data..."

    st.markdown(f'<div class="ticker"><div class="ticker-text">{ticker_text}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE MATCH DETAIL PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_detail(match_id: str, match_row: pd.Series):
    """Render comprehensive match analysis panel when a match is selected."""

    st.markdown(f"""
    <div class="detail-panel">
        <div class="detail-header">🔍 COMPREHENSIVE MATCH ANALYSIS — {match_row.get('MATCH', 'Unknown Match')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch detailed data
    try:
        details = data.router.get_match_details(match_id)
    except Exception:
        details = {"found": False}

    # Top row: Match info + Odds
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown("##### 📋 MATCH INFORMATION")
        info_data = {
            "League": match_row.get('LEAGUE', 'N/A'),
            "Status": match_row.get('STATUS', 'N/A'),
            "Score": match_row.get('SCORE', 'vs'),
            "Minute": match_row.get('MIN', '-'),
            "Prediction": match_row.get('PREDICTION', 'Analyzing...'),
            "Confidence": match_row.get('CONF', '-'),
            "Signal": match_row.get('SIGNAL', '-'),
        }
        for label, value in info_data.items():
            st.markdown(f"""
            <div class="stat-row">
                <span class="stat-label">{label}</span>
                <span class="stat-value">{value}</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("##### ⚖️ CURRENT ODDS")
        home_odds = match_row.get('HOME', '-')
        draw_odds = match_row.get('DRAW', '-')
        away_odds = match_row.get('AWAY', '-')

        st.markdown(f"""
        <div class="odds-row">
            <div class="odds-box">
                <div class="odds-label">1 (Home)</div>
                <div class="odds-value">{home_odds}</div>
            </div>
            <div class="odds-box">
                <div class="odds-label">X (Draw)</div>
                <div class="odds-value">{draw_odds}</div>
            </div>
            <div class="odds-box">
                <div class="odds-label">2 (Away)</div>
                <div class="odds-value">{away_odds}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        ev_val = match_row.get('EV', '-')
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: rgba(0,255,136,0.1); border-radius: 8px; margin-top: 10px;">
            <span style="font-family: Orbitron; color: #00ff88; font-size: 1.2rem;">EV: {ev_val}</span>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("##### 📊 LIVE STATISTICS")
        if details.get("statistics"):
            stats = details["statistics"]
            # Parse API-SPORTS stats format
            try:
                response = stats.get("response", [])
                if response:
                    team_stats = response[0].get("statistics", [])
                    for stat in team_stats:
                        stat_type = stat.get("type", "Unknown")
                        home_val = stat.get("value", "-")
                        away_val = stat.get("value", "-")  # Need to parse both teams
                        st.markdown(f"""
                        <div class="stat-row">
                            <span class="stat-label">{stat_type}</span>
                            <span class="stat-value">{home_val} - {away_val}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Statistics format not recognized")
            except Exception:
                st.info("Statistics parsing error")
        else:
            st.info("📡 Live statistics not yet available for this match")

    # Bottom row: Odds comparison + Predictions
    st.markdown("<hr style='border-color: #333; margin: 15px 0;'>", unsafe_allow_html=True)

    col4, col5 = st.columns(2)

    with col4:
        st.markdown("##### 📈 ODDS COMPARISON")
        try:
            odds_df = data.get_odds_comparison(match_id)
            if not odds_df.empty:
                st.dataframe(odds_df, use_container_width=True, hide_index=True)
            else:
                st.info("No odds comparison data available")
        except Exception:
            st.info("Odds comparison unavailable")

    with col5:
        st.markdown("##### 🔮 AI PREDICTIONS")
        if details.get("predictions"):
            pred = details["predictions"]
            if isinstance(pred, dict):
                home_prob = pred.get("home_win_prob", "N/A")
                draw_prob = pred.get("draw_prob", "N/A")
                away_prob = pred.get("away_win_prob", "N/A")

                pred_data = {
                    "Home Win": f"{home_prob}%" if home_prob != "N/A" else "Analyzing...",
                    "Draw": f"{draw_prob}%" if draw_prob != "N/A" else "Analyzing...",
                    "Away Win": f"{away_prob}%" if away_prob != "N/A" else "Analyzing...",
                }
                for label, value in pred_data.items():
                    st.markdown(f"""
                    <div class="stat-row">
                        <span class="stat-label">{label}</span>
                        <span class="stat-value">{value}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Prediction data format not recognized")
        else:
            st.info("🔮 AI predictions not yet available for this match")

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ARENA VIEW — SPORT TABS + LEAGUE FILTER + MATCH STATUS + MATCH TABLE
# ══════════════════════════════════════════════════════════════════════════════

def render_sport_tab(tab_name: str, sport_key: str):
    """Render content for a single sport tab. Called only when tab is active."""

    # Use tab_name for unique keys (includes emoji, always unique)
    key_prefix = tab_name.replace(" ", "_").replace("⚽", "f").replace("🏀", "b").replace("🏈", "nfl").replace("🎾", "t").replace("🏒", "nhl")

    # Filters row
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])

    with filter_col1:
        try:
            leagues = data.router.get_leagues(sport_key)
            if not leagues:
                leagues = ["All Leagues"]
        except Exception:
            leagues = ["All Leagues"]

        selected_league = st.selectbox(
            "🏆 SELECT LEAGUE",
            options=leagues,
            key=f"league_{key_prefix}"
        )

    with filter_col2:
        status_options = ["ALL", "LIVE", "SCHEDULED", "FINISHED", "HALFTIME"]
        selected_status = st.selectbox(
            "📊 MATCH STATUS",
            options=status_options,
            key=f"status_{key_prefix}"
        )

    with filter_col3:
        view_options = ["📋 TABLE VIEW", "🃏 CARD VIEW"]
        selected_view = st.selectbox(
            "👁️ DISPLAY MODE",
            options=view_options,
            key=f"view_{key_prefix}"
        )

    with filter_col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 REFRESH", key=f"refresh_{key_prefix}", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()

    # Fetch matches
    try:
        if selected_status == "LIVE":
            matches_df = data.router.get_live_matches(sport_key)
        elif selected_status == "SCHEDULED":
            matches_df = data.get_upcoming_matches_df()
        else:
            matches_df = data.router.get_matches_by_status(selected_status, sport_key)

        if selected_league != "All Leagues" and not matches_df.empty:
            matches_df = matches_df[matches_df["LEAGUE"] == selected_league]
    except Exception as e:
        st.error(f"Error fetching matches: {str(e)[:100]}")
        matches_df = pd.DataFrame()

    # Display
    if matches_df.empty:
        st.info(f"🔍 No {selected_status.lower()} matches found for {tab_name}. Try another status or refresh.")
        return

    st.markdown(f"<div style='color: #888; font-size: 0.85rem; margin-bottom: 10px;'>📊 Showing {len(matches_df)} matches</div>", unsafe_allow_html=True)

    if selected_view == "📋 TABLE VIEW":
        display_df = matches_df.drop(columns=["MATCH_ID"]) if "MATCH_ID" in matches_df.columns else matches_df

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"match_table_{key_prefix}"
        )

        selection = st.session_state.get(f"match_table_{key_prefix}")
        if selection and "rows" in selection and selection["rows"]:
            selected_idx = selection["rows"][0]
            if selected_idx < len(matches_df):
                selected_match = matches_df.iloc[selected_idx]
                match_id = selected_match.get("MATCH_ID", "")
                if match_id:
                    render_match_detail(match_id, selected_match)

    else:  # CARD VIEW
        cols = st.columns(2)
        for idx, (_, match) in enumerate(matches_df.iterrows()):
            with cols[idx % 2]:
                with st.expander(f"{match.get('MATCH', 'vs')} — {match.get('STATUS', '')}", expanded=False):
                    match_id = match.get("MATCH_ID", "")
                    if match_id:
                        render_match_detail(match_id, match)
                    else:
                        st.info("Match details unavailable")


def render_arena():
    st.markdown('<div class="section-header">🏟️ EMPIRE ARENA</div>', unsafe_allow_html=True)

    # Sport tabs — each maps to a unique key prefix
    sport_tabs = {
        "⚽ FOOTBALL": "football",
        "🏀 BASKETBALL": "basketball", 
        "🏈 NFL": "americanfootball",
        "🎾 TENNIS": "tennis",
        "🏒 NHL": "icehockey",
        "🏀 NBA": "basketball_nba"  # Unique key even though same sport
    }

    tab_names = list(sport_tabs.keys())
    tabs = st.tabs(tab_names)

    for tab, tab_name in zip(tabs, tab_names):
        with tab:
            sport_key = sport_tabs[tab_name]
            render_sport_tab(tab_name, sport_key)

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
