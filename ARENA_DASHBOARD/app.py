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

st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════
if "empire_data" not in st.session_state:
    st.session_state.empire_data = EmpireDashboardData()

data: EmpireDashboardData = st.session_state.empire_data

REFRESH_INTERVAL = 30  # seconds

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap');

.stApp {
    background: linear-gradient(180deg,#0a0a0f 0%,#12121a 50%,#0d0d14 100%);
    font-family:'Rajdhani',sans-serif;
}
.logo-center {
    display:flex;flex-direction:column;align-items:center;
    justify-content:center;text-align:center;padding:8px 0 4px;width:100%;
}
.logo-img { width:90%;height:auto;max-height:180px;object-fit:contain;display:block;margin:0 auto; }
.tagline-bold {
    font-family:'Orbitron',sans-serif;font-size:1.4rem;font-weight:900;
    background:linear-gradient(135deg,#D4AF37 0%,#FFD700 50%,#B8860B 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    text-align:center;letter-spacing:4px;text-transform:uppercase;
    margin-top:6px;margin-bottom:2px;
}
.tagline-sub {
    font-family:'Rajdhani',sans-serif;font-size:.9rem;color:#888;
    text-align:center;letter-spacing:6px;text-transform:uppercase;
    margin-top:2px;margin-bottom:8px;
}
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0f0f1a 0%,#1a1a2e 100%);
    border-right:3px solid #D4AF37;
}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 {
    color:#D4AF37 !important;font-family:'Orbitron',sans-serif;font-weight:700;letter-spacing:2px;
}
.ai-status {
    background:linear-gradient(135deg,#00ff88 0%,#00cc6a 100%);
    color:#000;font-family:'Orbitron',sans-serif;font-weight:900;
    font-size:.8rem;padding:8px 16px;border-radius:20px;text-align:center;
    letter-spacing:3px;text-transform:uppercase;
    box-shadow:0 0 15px rgba(0,255,136,.4);animation:pulse 2s infinite;
}
@keyframes pulse {
    0%,100%{box-shadow:0 0 15px rgba(0,255,136,.4);}
    50%{box-shadow:0 0 25px rgba(0,255,136,.8);}
}
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataFrame"] th {
    background:linear-gradient(135deg,#D4AF37 0%,#B8860B 100%) !important;
    color:#000 !important;font-family:'Orbitron',sans-serif !important;
    font-weight:900 !important;font-size:.85rem !important;
    text-transform:uppercase !important;letter-spacing:1.5px !important;
    border-bottom:3px solid #FFD700 !important;padding:14px 12px !important;
    text-align:center !important;
}
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] td {
    background-color:#1a1a2e !important;color:#FFD700 !important;
    font-family:'Rajdhani',sans-serif !important;font-weight:500 !important;
    font-size:.95rem !important;border-bottom:1px solid #2a2a3e !important;
    padding:10px 12px !important;text-align:center !important;
}
[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] { background-color:#151525 !important; }
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
    background:rgba(212,175,55,.2) !important;color:#FFF !important;font-weight:700 !important;
}
.section-header {
    font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:700;
    color:#FFD700;letter-spacing:2px;text-transform:uppercase;
    padding:15px 20px;
    background:linear-gradient(90deg,rgba(212,175,55,.2) 0%,transparent 100%);
    border-left:4px solid #D4AF37;border-radius:0 8px 8px 0;margin:20px 0 10px;
}
.match-card {
    background:linear-gradient(135deg,rgba(20,25,40,.9),rgba(10,15,30,.95));
    border:1px solid rgba(255,255,255,.08);border-radius:12px;
    padding:16px;margin:8px 0;transition:all .3s ease;
}
.match-card:hover {
    border-color:#D4AF37;box-shadow:0 0 20px rgba(212,175,55,.2);transform:translateX(5px);
}
[data-testid="stMetricValue"] {
    color:#FFD700 !important;font-family:'Orbitron',sans-serif;font-weight:900;font-size:2rem;
}
[data-testid="stMetricLabel"] {
    color:#888 !important;font-family:'Rajdhani',sans-serif;font-weight:500;
    letter-spacing:2px;text-transform:uppercase;
}
.world-clock {
    font-family:'Orbitron',sans-serif;font-size:.9rem;color:#D4AF37;
    text-align:center;letter-spacing:2px;padding:10px;
    background:rgba(212,175,55,.1);border-radius:8px;margin:10px 0;
}
.ticker {
    background:linear-gradient(90deg,#1a1a2e 0%,#16213e 100%);
    border-top:2px solid #D4AF37;border-bottom:2px solid #D4AF37;
    padding:10px;overflow:hidden;white-space:nowrap;
}
.ticker-text {
    font-family:'Rajdhani',sans-serif;color:#FFD700;font-size:.9rem;
    letter-spacing:2px;animation:scroll 30s linear infinite;display:inline-block;
}
@keyframes scroll { 0%{transform:translateX(100vw);} 100%{transform:translateX(-100%);} }
.stButton>button {
    background:linear-gradient(135deg,#D4AF37 0%,#FFD700 100%);
    color:#000;font-family:'Orbitron',sans-serif;font-weight:700;
    border:none;border-radius:8px;padding:.6rem 2rem;
    letter-spacing:2px;text-transform:uppercase;transition:all .3s ease;
}
.stButton>button:hover {
    background:linear-gradient(135deg,#FFD700 0%,#FFF8DC 100%);
    box-shadow:0 0 25px rgba(212,175,55,.6);transform:scale(1.05);
}
.stTabs [data-baseweb="tab-list"] {
    gap:4px;background:rgba(26,26,46,.5);border-radius:10px;padding:5px;
}
.stTabs [data-baseweb="tab"] {
    background:transparent;color:#888;font-family:'Orbitron',sans-serif;
    font-weight:500;letter-spacing:1px;border-radius:6px;padding:.5rem 1.5rem;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#D4AF37 0%,#FFD700 100%) !important;
    color:#000 !important;font-weight:700;
}
.gold-divider {
    border:none;height:2px;
    background:linear-gradient(90deg,transparent 0%,#D4AF37 50%,transparent 100%);
    margin:20px 0;
}
::-webkit-scrollbar{width:8px;}
::-webkit-scrollbar-track{background:#0a0a0f;}
::-webkit-scrollbar-thumb{background:linear-gradient(180deg,#D4AF37 0%,#B8860B 100%);border-radius:4px;}
.stat-row {
    display:flex;justify-content:space-between;padding:8px 0;
    border-bottom:1px solid #2a2a3e;font-family:'Rajdhani',sans-serif;font-size:.95rem;
}
.stat-label{color:#888;} .stat-value{color:#FFD700;font-weight:700;}
</style>
""")

# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIG
# ══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Football":    {"icon": "⚽",  "provider": "API-SPORTS"},
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
SPORT_NAMES    = list(SPORT_OPTIONS.keys())


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALISATION  (run once per session)
# ══════════════════════════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "selected_sport":     SPORT_NAMES[0],
        "selected_league_id": "ALL",
        "selected_status":    "ALL",
        "page":               "🏟️ ARENA",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


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
            'ELITE TRADING DASHBOARD v3.0</text></svg>'
        )
        b64 = base64.b64encode(svg.encode()).decode()
        logo_html = f'<img src="data:image/svg+xml;base64,{b64}" class="logo-img" alt="EMPIRE">'

    st.markdown(f'<div class="logo-center">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Advanced Research & Evaluation System | Where Data Meets Instinct</div>',
                unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # AI status
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        st.markdown('<div class="ai-status">🤖 AI ENGINE ONLINE 24/7</div>', unsafe_allow_html=True)

    # World clock
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

    # Live / demo banner
    if data.is_live:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#00ff88,#00cc6a);color:#000;
             font-family:Orbitron;font-size:1rem;padding:12px 20px;border-radius:8px;
             text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;">
            🟢 LIVE MODE — APIs Connected | Real-Time Data Active
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#B8860B,#FFD700);color:#000;
             font-family:Orbitron;font-size:1rem;padding:12px 20px;border-radius:8px;
             text-align:center;font-weight:900;letter-spacing:3px;margin:10px 0;">
            ⚠️ API KEYS NOT DETECTED — Showing league/team lists. Add keys in Render env.
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR  — fully synchronised dropdowns
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    with st.sidebar:
        # Brand logo
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

        # Bot status pill
        st.markdown("""
        <div style="background:rgba(0,255,136,.1);border:1px solid #00ff88;
             border-radius:8px;padding:10px;margin:10px 0;text-align:center;">
            <div style="color:#00ff88;font-family:Orbitron;font-size:.75rem;">
                🤖 INSTINCT BOT v3.0<br>
                <span style="color:#888;font-size:.7rem;">SCANNING LIVE MATCHES</span><br>
                <span style="color:#00ff88;">● ACTIVE</span>
            </div>
        </div>""", unsafe_allow_html=True)

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
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # ── ARENA CONTROLS ────────────────────────────────────────────────────
        st.markdown(
            '<div style="color:#D4AF37;font-family:Orbitron;font-size:.85rem;'
            'text-align:center;margin-bottom:8px;">🏟️ ARENA CONTROLS</div>',
            unsafe_allow_html=True,
        )

        # ── 1. SPORT selector ─────────────────────────────────────────────────
        sport_labels = [
            f"{SPORT_OPTIONS[s]['icon']} {s}" for s in SPORT_NAMES
        ]
        current_sport_idx = SPORT_NAMES.index(st.session_state.selected_sport)

        sport_choice_label = st.selectbox(
            "🎯 SELECT SPORT",
            options=sport_labels,
            index=current_sport_idx,
            key="sport_selectbox",
        )
        chosen_sport = SPORT_NAMES[sport_labels.index(sport_choice_label)]

        # When sport changes → reset the other two filters before doing anything else
        if chosen_sport != st.session_state.selected_sport:
            st.session_state.selected_sport     = chosen_sport
            st.session_state.selected_league_id = "ALL"
            st.session_state.selected_status    = "ALL"
            st.rerun()   # force immediate clean re-render with new sport

        st.markdown("<hr style='border-color:#333;margin:6px 0;'>", unsafe_allow_html=True)

        # ── 2. LEAGUE / TEAM selector ─────────────────────────────────────────
        # Pull league list — always instant (static fallback guaranteed)
        raw_leagues = data.get_all_leagues(st.session_state.selected_sport)

        # Build parallel id / label lists; "ALL" is always index 0
        league_ids    = ["ALL"]
        league_labels = [f"🏆 All {st.session_state.selected_sport} — All Events"]
        for lg in raw_leagues:
            lid   = str(lg.get("id", "ALL"))
            lname = lg.get("name", "Unknown")
            lctry = lg.get("country", "")
            label = f"{lname} ({lctry})" if lctry else lname
            league_ids.append(lid)
            league_labels.append(label)

        # Clamp persisted league id to current list (handles sport switch edge case)
        if st.session_state.selected_league_id not in league_ids:
            st.session_state.selected_league_id = "ALL"

        league_idx = league_ids.index(st.session_state.selected_league_id)

        league_label_choice = st.selectbox(
            "🏆 SELECT LEAGUE / TEAM",
            options=league_labels,
            index=league_idx,
            # key is sport-scoped so Streamlit creates a fresh widget on sport change
            key=f"league_selectbox__{st.session_state.selected_sport}",
        )
        chosen_league_id = league_ids[league_labels.index(league_label_choice)]
        st.session_state.selected_league_id = chosen_league_id

        # ── 3. STATUS filter ──────────────────────────────────────────────────
        status_idx = (
            STATUS_OPTIONS.index(st.session_state.selected_status)
            if st.session_state.selected_status in STATUS_OPTIONS else 0
        )
        status_choice = st.selectbox(
            "📊 MATCH STATUS",
            options=STATUS_OPTIONS,
            index=status_idx,
            key=f"status_selectbox__{st.session_state.selected_sport}",
        )
        st.session_state.selected_status = status_choice

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        # ── Refresh button ────────────────────────────────────────────────────
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

        # Connection log
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
# CACHE CLEAR HELPER - FIXED VERSION
# ══════════════════════════════════════════════════════════════════════════════
def _clear_all_caches():
    """Clear all caches safely - handles both Streamlit and provider caches"""
    st.session_state.last_refresh = time.time()
    
    # Clear Streamlit's data cache
    st.cache_data.clear()
    
    # Safely clear provider caches if they exist - using correct attribute names
    router = data.router
    
    # Use the correct attribute names from your EmpireDataRouter
    provider_attrs = ["api_sports", "football_data", "msf", "tsdb", "apify"]
    
    for attr in provider_attrs:
        provider = getattr(router, attr, None)
        if provider is not None and hasattr(provider, "clear"):
            try:
                provider.clear()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# LIVE TICKER
# ══════════════════════════════════════════════════════════════════════════════
def render_ticker():
    st.markdown(
        '<div class="ticker"><div class="ticker-text">'
        '📡 LIVE DATA FEED ACTIVE — '
        '⚽ Football &nbsp;·&nbsp; 🏀 NBA &nbsp;·&nbsp; 🏈 NFL &nbsp;·&nbsp; '
        '⚾ MLB &nbsp;·&nbsp; 🏒 NHL &nbsp;·&nbsp; 🥊 UFC &nbsp;·&nbsp; '
        '🏎️ F1 &nbsp;·&nbsp; 🎾 Tennis &nbsp;·&nbsp; 🏏 Cricket &nbsp;·&nbsp; ⛳ Golf'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MATCH STATUS HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:
        return "#00FF88", "rgba(0,255,136,.15)", "● LIVE"
    if any(x in su for x in ("FINISH", "FT", "FINAL", "COMPLETED")):
        return "#888", "rgba(136,136,136,.15)", "FINISHED"
    return "#FFAA00", "rgba(255,170,0,.15)", "UPCOMING"


# ══════════════════════════════════════════════════════════════════════════════
# MATCH CARDS
# ══════════════════════════════════════════════════════════════════════════════
def render_match_cards(matches_df: pd.DataFrame, sport: str):
    if matches_df is None or matches_df.empty:
        st.info(
            f"No {sport} matches found right now. "
            "This may be off-season, between fixtures, or the API returned no events. "
            "Try changing the Status filter or refreshing."
        )
        return

    st.markdown(
        f"<div style='color:#888;font-size:.85rem;margin-bottom:10px;'>"
        f"📊 {len(matches_df)} matches</div>",
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

        st.markdown(f"""
        <div class="match-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#8892b0;font-size:.75rem;">{league}</span>
                <span style="color:{color};background:{bg};padding:2px 10px;
                      border-radius:10px;font-size:.7rem;font-weight:700;">{label}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="flex:1;text-align:left;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;">{home}</div>
                </div>
                <div style="padding:0 20px;text-align:center;">
                    <div style="color:#00d4ff;font-size:1.4rem;font-weight:700;">{score}</div>
                    <div style="color:#8892b0;font-size:.65rem;">{mtime}</div>
                </div>
                <div style="flex:1;text-align:right;">
                    <div style="color:#e6f1ff;font-size:1rem;font-weight:600;">{away}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        btn_col = st.columns([8, 1])
        with btn_col[1]:
            if st.button("🔍", key=f"view_{sport}_{match_id}_{idx}", help="Match details"):
                st.session_state.selected_match_id   = match_id
                st.session_state.selected_match_row  = row.to_dict()
                st.session_state.selected_match_home = home
                st.session_state.selected_match_away = away
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MATCH DETAIL PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_match_detail():
    match_id  = st.session_state.get("selected_match_id", "")
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
        for label, key in [
            ("Match ID", "MATCH_ID"), ("League", "LEAGUE"),
            ("Status", "STATUS"),     ("Time",   "TIME"),
            ("Provider", "PROVIDER"),
        ]:
            val = match_row.get(key, "N/A")
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-label">{label}</span>'
                f'<span class="stat-value">{val}</span></div>',
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown("##### ⚖️ SCORE")
        st.markdown(
            f'<div style="font-family:Orbitron;font-size:2rem;color:#FFD700;text-align:center;'
            f'padding:20px;">{match_row.get("SCORE","vs")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
    st.info("Full H2H, player stats, and predictive model coming from live APIs.")


# ══════════════════════════════════════════════════════════════════════════════
# ARENA  — main match view
# ══════════════════════════════════════════════════════════════════════════════
def render_arena(sport: str, league_id: str, status: str):
    if "selected_match_id" in st.session_state:
        render_match_detail()
        return

    icon = SPORT_OPTIONS.get(sport, {}).get("icon", "🏆")
    st.markdown(
        f'<div class="section-header">{icon} EMPIRE ARENA — {sport.upper()}</div>',
        unsafe_allow_html=True,
    )

    try:
        if status == "LIVE":
            df = data.get_live_matches_df(sport, None if league_id == "ALL" else league_id)
        elif status in ("UPCOMING", "SCHEDULED"):
            df = data.get_upcoming_matches_df(sport)
        elif status == "FINISHED":
            df = pd.DataFrame()
        else:  # ALL
            live_df     = data.get_live_matches_df(sport, None if league_id == "ALL" else league_id)
            upcoming_df = data.get_upcoming_matches_df(sport)
            parts = [d for d in [live_df, upcoming_df] if not d.empty]
            df    = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

        # Filter by specific league when one is selected and data contains LEAGUE column
        if league_id != "ALL" and not df.empty and "LEAGUE" in df.columns:
            # Match by league name substring (API-Sports returns name, not id, in rows)
            mask     = df["LEAGUE"].astype(str).str.contains(league_id, case=False, na=False)
            filtered = df[mask]
            if not filtered.empty:
                df = filtered
            # else keep full df (league_id is an opaque key with no text match)

    except Exception as e:
        st.error(f"Error loading matches: {e}")
        logger.exception("render_arena error")
        df = pd.DataFrame()

    render_match_cards(df, sport)


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS  (stub)
# ══════════════════════════════════════════════════════════════════════════════
def render_predictions():
    st.markdown('<div class="section-header">🎯 PREDICTION CENTER</div>', unsafe_allow_html=True)
    st.info("🔮 AI predictions will populate here once live match data is flowing.")


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS  (stub)
# ══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 PERFORMANCE ANALYTICS</div>', unsafe_allow_html=True)
    st.info("📊 Performance analytics powered by historical API data.")


# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR  — force-refresh button + auto-refresh countdown
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
            f'● {mode} | Auto-refresh in {int(max(0, REFRESH_INTERVAL - elapsed))}s</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
render_header()
selected_sport, selected_league_id, selected_status = render_sidebar()
render_ticker()

render_top_bar()

# Page tabs
page = st.radio(
    "", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"],
    horizontal=True, label_visibility="collapsed",
    key="page_radio",
)

if "ARENA" in page:
    render_arena(selected_sport, selected_league_id, selected_status)
elif "PREDICTIONS" in page:
    render_predictions()
else:
    render_analytics()
