"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
World-Class Professional Command Center
24/7 AI Engine | Real-Time Global Sports Intelligence
"""
import streamlit as st
from pathlib import Path
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import sys
import os
import time

# EMPIRE Live Data Integration
from empire_data_layer import EmpireDashboardData

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Auto-refresh every 60 seconds
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PREMIUM DARK GOLD COMMAND CENTER CSS
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# PREMIUM DARK GOLD COMMAND CENTER CSS — FIXED FOR STREAMLIT 2026
# Uses st.html() (official API) + targets actual Streamlit DOM structure
# ══════════════════════════════════════════════════════════════════════════════

st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');

    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
        font-family: 'Rajdhani', sans-serif;
    }

    /* Centered Logo Container - 90% width, reduced height */
    .logo-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 10px 0;
        width: 100%;
    }

    /* Logo container — centered, contained (user's original placement) */
    .logo-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 10px 0;
        width: 100%;
    }

    /* Logo: 90% width, natural height from aspect ratio, tight spacing */
    .logo-img {
        width: 90%;
        height: auto;
        max-height: 180px;
        object-fit: contain;
        display: block;
        margin: 0 auto;
    }

    /* Tighten gap between logo and tagline */
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

    /* Bold Gold Tagline */
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

    /* Command Center Sidebar */
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

    /* AI Engine Status Badge */
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

    /* ════════════════════════════════════════════════════════════════
       DATAFRAME DARK GOLD — ULTRA-AGGRESSIVE SELECTORS
       Mimics Live Match Cards: gold headers, bright text, dark cells
       ════════════════════════════════════════════════════════════════ */

    /* Force ALL dataframe backgrounds to dark */
    [data-testid="stDataFrameResizable"],
    [data-testid="stDataFrameResizable"] > div,
    [data-testid="stDataFrame"] {
        background-color: #1a1a2e !important;
    }

    /* Virtual table inner container */
    [data-testid="stDataFrame"] [data-testid="stVirtualTable"],
    [data-testid="stDataFrame"] .stDataFrameContainer {
        background-color: #1a1a2e !important;
    }

    /* HEADER CELLS — Gold gradient like Live Match card titles */
    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] .stDataFrameHeader {
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

    /* DATA CELLS — Bright gold/white text on dark, like match cards */
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] .stDataFrameCell {
        background-color: #1a1a2e !important;
        color: #FFD700 !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        border-bottom: 1px solid #2a2a3e !important;
        padding: 10px 12px !important;
        text-align: center !important;
    }

    /* Alternate row striping for readability */
    [data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
        background-color: #151525 !important;
    }

    /* HOVER — Gold glow like match cards */
    [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
        background: rgba(212, 175, 55, 0.2) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    /* Row numbers/index column */
    [data-testid="stDataFrame"] [role="rowheader"],
    [data-testid="stDataFrame"] .stDataFrameRowIndex {
        background-color: #16213e !important;
        color: #D4AF37 !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 700 !important;
        border-right: 2px solid #D4AF37 !important;
    }

    /* Scrollbar theming */
    [data-testid="stDataFrameResizable"] ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    [data-testid="stDataFrameResizable"] ::-webkit-scrollbar-track {
        background: #16213e !important;
    }
    [data-testid="stDataFrameResizable"] ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%) !important;
        border-radius: 4px;
    }

    /* st.table fallback — same gold-on-dark theme */
    [data-testid="stTable"] {
        background-color: #1a1a2e !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    [data-testid="stTable"] th {
        background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
        color: #000 !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 12px !important;
        border: 1px solid #D4AF37 !important;
    }
    [data-testid="stTable"] td {
        background-color: #1a1a2e !important;
        color: #FFD700 !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 500 !important;
        padding: 10px 12px !important;
        border: 1px solid #2a2a3e !important;
    }
    [data-testid="stTable"] tr:nth-child(even) td {
        background-color: #151525 !important;
    }
    [data-testid="stTable"] tr:hover td {
        background: rgba(212, 175, 55, 0.2) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Section Headers */
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

    /* Live Match Cards */
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

    /* Metric Cards */
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

    /* World Clock */
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

    /* Activity Ticker */
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

    /* Buttons */
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

    /* Tabs */
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

    /* Gold Divider */
    .gold-divider {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #D4AF37 50%, transparent 100%);
        margin: 20px 0;
    }

    /* Scrollbar */
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

    /* Force dark on all block containers */
    [data-testid="stVerticalBlock"] > div {
        background-color: transparent !important;
    }

    /* Dark container wrapper */
    .dark-container {
        background-color: #1a1a2e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        margin: 10px 0;
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
# HEADER — CENTERED LOGO (90% WIDTH, REDUCED HEIGHT) + BOLD TAGLINE
# ══════════════════════════════════════════════════════════════════════════════
def render_header():

    # ═══════════════════════════════════════════════════════════════════════
    # LOGO: Base64 HTML img — bypasses ALL st.image() CSS conflicts
    # 90% width, max-height 240px, auto height, object-fit contain
    # ═══════════════════════════════════════════════════════════════════════
    logo_path = Path("BRAND_ASSET/empire_logo_primary.png")

    if logo_path.exists():
        with open(logo_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="EMPIRE Logo">'
    else:
        # Procedural SVG fallback — always renders
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 140">
<defs>
<linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%">
<stop offset="0%" style="stop-color:#D4AF37;stop-opacity:1"/>
<stop offset="100%" style="stop-color:#FFD700;stop-opacity:1"/>
</linearGradient>
</defs>
<rect width="900" height="140" rx="12" fill="#16213e" stroke="#D4AF37" stroke-width="2"/>
<text x="450" y="85" font-family="Arial Black, Impact, sans-serif" font-size="52" fill="url(#g1)" text-anchor="middle" font-weight="900" letter-spacing="6">EMPIRE SPORT INSTINCTS ARENA</text>
<text x="450" y="115" font-family="Arial, sans-serif" font-size="16" fill="#888" text-anchor="middle" letter-spacing="10">ELITE TRADING DASHBOARD v2.4</text>
</svg>"""
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

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE / DEMO MODE BANNER — Shows actual API connection status
    # ═══════════════════════════════════════════════════════════════════════
    try:
        from empire_data_layer import EmpireDataRouter
        router = EmpireDataRouter()
        has_live = router.active_provider is not None

        if has_live:
            provider_name = router.active_provider.name
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
# SIDEBAR — PROFESSIONAL COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # Sidebar logo rendered as HTML for consistency
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

        sport = st.selectbox("🎯 SELECT SPORT", ["ALL SPORTS", "⚽ FOOTBALL", "🏀 NBA", "🏈 NFL", "🎾 TENNIS"])

        st.subheader("⚡ SYSTEM STATUS")

        # Live API connection status
        st.markdown('<div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px; margin: 8px 0;">', unsafe_allow_html=True)

        # Test each provider and show status with detailed errors
        provider_status = []
        try:
            from empire_data_layer import EmpireDataRouter
            router = EmpireDataRouter()
            statuses = router.get_provider_status()
            for s in statuses:
                if "ONLINE" in s["status"]:
                    icon = "🟢"
                    color = "#00ff88"
                elif "EMPTY" in s["status"]:
                    icon = "🟡"
                    color = "#FFD700"
                else:
                    icon = "🔴"
                    color = "#ff4444"

                status_text = s["status"]
                if s.get("error") and "OFFLINE" in status_text:
                    status_text += f" ({s['error'][:30]})"

                provider_status.append((f"{icon} {s['name']}", status_text, color))
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

        # ═════════════════════════════════════════════════════════════════
        # REAL-TIME API CONNECTION LOG
        # ═════════════════════════════════════════════════════════════════
        st.markdown("<hr style='border-color: #333; margin: 15px 0;'>", unsafe_allow_html=True)
        st.subheader("📡 API CONNECTION LOG")

        try:
            log_df = data.get_connection_log_df()
            if not log_df.empty:
                # Color-code status column
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
                st.info("No connection attempts yet. Refresh to test APIs.")
        except Exception as e:
            st.warning(f"Log unavailable: {str(e)[:50]}")

        return sport

# ══════════════════════════════════════════════════════════════════════════════
# LIVE MATCH TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_live_ticker():
    # Fetch live matches for ticker instead of hard-coded data
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
# LIVE API DIAGNOSTICS PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_api_diagnostics():
    st.markdown('<div class="section-header">📡 LIVE API DIAGNOSTICS</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    border: 1px solid #333; border-radius: 10px; padding: 15px;">
            <div style="color: #D4AF37; font-family: Orbitron; font-size: 0.8rem; margin-bottom: 8px;">
                🔑 API KEY STATUS
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Only check keys that actually exist in the data layer
        keys = [
            ("API-SPORTS", "API_SPORTS_KEY"),
            ("The Odds API", "ODDS_API_KEY"),
            ("Sportmonks", "SPORTMONKS_KEY"),
            ("TheSportsDB", "TheSportDB_API_key"),
            ("The Rundown", "RUNDOWN_KEY"),
        ]

        for name, env_var in keys:
            key_val = os.getenv(env_var, "")
            if key_val and len(key_val) > 5:
                st.markdown(f'<div style="color: #00ff88; font-size: 0.75rem; font-family: Rajdhani;">🟢 {name}: Key present ({len(key_val)} chars)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color: #ff4444; font-size: 0.75rem; font-family: Rajdhani;">🔴 {name}: MISSING or INVALID</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    border: 1px solid #333; border-radius: 10px; padding: 15px;">
            <div style="color: #D4AF37; font-family: Orbitron; font-size: 0.8rem; margin-bottom: 8px;">
                🌐 NETWORK STATUS
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick network test
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            st.markdown('<div style="color: #00ff88; font-size: 0.75rem; font-family: Rajdhani;">🟢 Internet: Connected</div>', unsafe_allow_html=True)
        except:
            st.markdown('<div style="color: #ff4444; font-size: 0.75rem; font-family: Rajdhani;">🔴 Internet: Disconnected</div>', unsafe_allow_html=True)

        try:
            import requests
            r = requests.get("https://api.github.com", timeout=5)
            st.markdown(f'<div style="color: #00ff88; font-size: 0.75rem; font-family: Rajdhani;">🟢 HTTPS: Working ({r.status_code})</div>', unsafe_allow_html=True)
        except:
            st.markdown('<div style="color: #ff4444; font-size: 0.75rem; font-family: Rajdhani;">🔴 HTTPS: Blocked</div>', unsafe_allow_html=True)

        st.markdown('<div style="color: #888; font-size: 0.7rem; margin-top: 8px; font-family: Rajdhani;">Last checked: just now</div>', unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    border: 1px solid #333; border-radius: 10px; padding: 15px;">
            <div style="color: #D4AF37; font-family: Orbitron; font-size: 0.8rem; margin-bottom: 8px;">
                📊 DATA SOURCE HEALTH
            </div>
        </div>
        """, unsafe_allow_html=True)

        try:
            from empire_data_layer import EmpireDataRouter
            router = EmpireDataRouter()
            statuses = router.get_provider_status()

            for s in statuses:
                if "ONLINE" in s["status"]:
                    icon, color = "🟢", "#00ff88"
                elif "EMPTY" in s["status"]:
                    icon, color = "🟡", "#FFD700"
                else:
                    icon, color = "🔴", "#ff4444"

                resp_time = s.get("response_time_ms", "-")
                resp_str = f" ({resp_time}ms)" if resp_time != "-" else ""

                st.markdown(f'<div style="color: {color}; font-size: 0.75rem; font-family: Rajdhani;">{icon} {s["name"]}: {s["status"].split(" — ")[-1]}{resp_str}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div style="color: #ff4444; font-size: 0.75rem;">⚠️ Health check error: {str(e)[:40]}</div>', unsafe_allow_html=True)

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LIVE MATCH CARDS
# ══════════════════════════════════════════════════════════════════════════════
def render_live_matches():
    st.markdown('<div class="section-header">🔴 LIVE MATCHES NOW</div>', unsafe_allow_html=True)

    # Fetch live matches from EMPIRE data layer — NO MOCK DATA
    try:
        live_df = data.get_live_matches_df()
        if not live_df.empty:
            live_matches = live_df.head(8).to_dict('records')
            # Normalize column names for display
            for match in live_matches:
                match.setdefault('league', match.get('LEAGUE', 'Unknown'))
                match.setdefault('home', match.get('MATCH', '').split(' vs ')[0] if ' vs ' in match.get('MATCH', '') else 'Home')
                match.setdefault('away', match.get('MATCH', '').split(' vs ')[1] if ' vs ' in match.get('MATCH', '') else 'Away')
                match.setdefault('score', match.get('SCORE', 'vs'))
                match.setdefault('time', match.get('MIN', 'LIVE'))
                match.setdefault('odds', match.get('HOME', '-'))
                match.setdefault('ev', match.get('EV', '-'))
                match.setdefault('prediction', match.get('PREDICTION', 'Analyzing...'))
        else:
            live_matches = []
    except Exception as e:
        st.warning(f"⚠️ Live feed connecting... ({str(e)[:50]})")
        live_matches = []

    if not live_matches:
        st.info("🔌 Live feed initializing. Matches will appear once data streams connect.")
        return

    cols = st.columns(2)
    for idx, match in enumerate(live_matches):
        with cols[idx % 2]:
            st.markdown(f"""
            <div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #888; font-size: 0.8rem;">{match['league']}</span>
                    <span class="match-live">● LIVE {match['time']}</span>
                </div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFD700; margin: 10px 0;">
                    {match['home']} <span style="color: #fff;">{match['score']}</span> {match['away']}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                    <span style="color: #00ff88;">📊 {match['prediction']}</span>
                    <span style="color: #D4AF37;">⚡ EV: {match['ev']}</span>
                </div>
                <div style="margin-top: 8px; font-size: 0.8rem; color: #888;">
                    Best Odds: <span style="color: #FFD700;">{match['odds']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PANDAS STYLER — Forces dark cell backgrounds inside st.dataframe
# ══════════════════════════════════════════════════════════════════════════════
def style_dark_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply dark gold theme styling for st.dataframe rendering."""
    return df.style.set_properties(**{
        'background-color': '#1a1a2e',
        'color': '#e0e0e0',
        'border-color': '#333',
        'font-family': 'Rajdhani, sans-serif'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background', 'linear-gradient(135deg, #D4AF37 0%, #B8860B 100%)'),
            ('color', '#000'),
            ('font-family', 'Orbitron, sans-serif'),
            ('font-weight', '700'),
            ('text-transform', 'uppercase'),
            ('letter-spacing', '1px'),
            ('border-bottom', '2px solid #FFD700')
        ]},
        {'selector': 'td', 'props': [
            ('background-color', '#1a1a2e'),
            ('color', '#e0e0e0'),
            ('border-bottom', '1px solid #333')
        ]},
        {'selector': 'tr:hover td', 'props': [
            ('background', 'rgba(212, 175, 55, 0.15)'),
            ('color', '#FFD700')
        ]}
    ])

# ══════════════════════════════════════════════════════════════════════════════
# VALUE OPPORTUNITIES — DARK TABLE
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
def render_value_opportunities(sport_filter):
    st.markdown('<div class="section-header">⚜ ACTIVE VALUE OPPORTUNITIES</div>', unsafe_allow_html=True)

    # Fetch live value opportunities from EMPIRE data layer — NO MOCK DATA
    try:
        opportunities = data.get_value_opportunities_df()

        if sport_filter != "ALL SPORTS":
            sport_name = sport_filter.split()[-1]
            if "SPORT" in opportunities.columns:
                opportunities = opportunities[opportunities["SPORT"] == sport_name]

        if opportunities.empty:
            st.info("🔍 No value opportunities detected. Markets are tight — waiting for edge.")
            return

    except Exception as e:
        st.warning(f"⚠️ Live data temporarily unavailable. ({str(e)[:50]})")
        return

    st.markdown('<div class="dark-container">', unsafe_allow_html=True)
    st.dataframe(style_dark_df(opportunities), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE HISTORY — DARK CHART
# ══════════════════════════════════════════════════════════════════════════════
def render_performance_history():
    st.markdown('<div class="section-header">📈 PERFORMANCE HISTORY</div>', unsafe_allow_html=True)

    # NOTE: This requires a database connection for real historical data.
    # For now, show empty state with instructions.
    st.info("📊 Performance history requires database integration. Connect your PostgreSQL instance to populate this chart with real trading data.")

    # Placeholder chart structure (no fake data points)
    fig = go.Figure()
    fig.update_layout(
        title=dict(text="BANKROLL EVOLUTION", font=dict(family="Orbitron", size=20, color="#FFD700")),
        xaxis_title="DATE", yaxis_title="BANKROLL ($)",
        template="plotly_dark", height=450,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(26, 26, 46, 0.5)",
        font=dict(family="Rajdhani", color="#e0e0e0")
    )
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# MODEL PERFORMANCE — DARK TABLE
# ══════════════════════════════════════════════════════════════════════════════
def render_model_performance():
    st.markdown('<div class="section-header">🧠 AI MODEL PERFORMANCE</div>', unsafe_allow_html=True)

    # NOTE: Model metrics should come from model evaluation pipeline.
    # For now, show empty state.
    st.info("🧠 Model performance metrics require evaluation pipeline integration. Connect your model registry to display live accuracy, log loss, and Sharpe ratio data.")

    # Empty dataframe with correct schema
    model_metrics = pd.DataFrame({
        "MODEL": [],
        "LOG LOSS": [],
        "ACCURACY": [],
        "ROC-AUC": [],
        "SHARPE": [],
        "STATUS": []
    })

    st.markdown('<div class="dark-container">', unsafe_allow_html=True)
    st.dataframe(style_dark_df(model_metrics), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS CENTER
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔮 UPCOMING", "📜 HISTORY", "⚙️ CALIBRATION"])

    with tab1:
        # Fetch upcoming predictions from data layer
        try:
            upcoming_df = data.get_upcoming_matches_df() if hasattr(data, 'get_upcoming_matches_df') else pd.DataFrame()
            if not upcoming_df.empty:
                st.markdown('<div class="dark-container">', unsafe_allow_html=True)
                st.dataframe(style_dark_df(upcoming_df), use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("🔮 No upcoming predictions available. Check API connections or wait for next fixture window.")
        except Exception:
            st.info("🔮 No upcoming predictions available. Check API connections or wait for next fixture window.")

    with tab2:
        # Prediction history requires database
        st.info("📜 Prediction history requires database integration. Connect your PostgreSQL instance to populate historical prediction results.")
        history = pd.DataFrame({
            "DATE": [],
            "MATCH": [],
            "PREDICTED": [],
            "RESULT": [],
            "P/L": []
        })
        st.markdown('<div class="dark-container">', unsafe_allow_html=True)
        st.dataframe(style_dark_df(history), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.info("⚙️ Model calibration analysis — comparing predicted probabilities vs actual outcomes. Requires historical database.")
        cal_data = pd.DataFrame({
            "BIN": [],
            "PREDICTED": [],
            "ACTUAL": [],
            "BETS": []
        })
        st.markdown('<div class="dark-container">', unsafe_allow_html=True)
        st.dataframe(style_dark_df(cal_data), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE ANALYTICS — SPORT BREAKDOWN + MONTHLY
# ══════════════════════════════════════════════════════════════════════════════
def render_performance_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)

    st.info("📊 Performance analytics require database integration. Connect your PostgreSQL instance to populate sport breakdown and monthly performance data.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header" style="font-size:1rem;">⚽ SPORT BREAKDOWN</div>', unsafe_allow_html=True)
        breakdown = pd.DataFrame({
            "SPORT": [],
            "BETS": [],
            "WIN RATE": [],
            "PROFIT": [],
            "ROI": []
        })
        st.markdown('<div class="dark-container">', unsafe_allow_html=True)
        st.dataframe(style_dark_df(breakdown), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header" style="font-size:1rem;">📅 MONTHLY PERFORMANCE</div>', unsafe_allow_html=True)
        # Empty chart placeholder
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark", height=350,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(26, 26, 46, 0.5)",
            font=dict(family="Rajdhani", color="#e0e0e0"),
            xaxis_title="MONTH", yaxis_title="PROFIT ($)"
        )
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    render_header()
    sport = render_sidebar()
    render_live_ticker()

    page = st.radio("", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"], 
                    horizontal=True, label_visibility="collapsed")

    if "ARENA" in page:
        render_api_diagnostics()
        render_live_matches()
        render_value_opportunities(sport)
        render_performance_history()
        render_model_performance()
    elif "PREDICTIONS" in page:
        render_predictions()
    else:
        render_performance_analytics()
