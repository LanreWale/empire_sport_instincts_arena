"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA v4.1
World-Class Professional Command Center
24/7 Claude AI Engine | Real-Time Global Sports Intelligence
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from pathlib import Path
import base64
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import logging

import plotly.graph_objects as go
import plotly.express as px

from empire_data_layer import EmpireDashboardData, APIConfig
from empire_ai_engine import (
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

# ── Singleton services ──────────────────────────────────────────────────────
if "empire_data" not in st.session_state:
    st.session_state.empire_data = EmpireDashboardData()
if "empire_ai" not in st.session_state:
    st.session_state.empire_ai = EmpireAIEngine()

data: EmpireDashboardData = st.session_state.empire_data
ai:   EmpireAIEngine      = st.session_state.empire_ai

REFRESH_INTERVAL = 90

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

# ── CSS ─────────────────────────────────────────────────────────────────────
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
.kelly-result-good{background:linear-gradient(135deg,rgba(0,255,136,.15),rgba(0,204,106,.05));border:2px solid #00ff88;border-radius:10px;padding:16px;text-align:center;}
.kelly-result-bad{background:rgba(255,107,107,.1);border:2px solid #ff6b6b;border-radius:10px;padding:16px;text-align:center;}
</style>
""", unsafe_allow_html=True)

# ── Sport config ─────────────────────────────────────────────────────────────
SPORT_OPTIONS = {
    "Football":  {"icon": "⚽",  "provider": "Apify/FlashScore + API-SPORTS + Football-Data"},
    "NBA":       {"icon": "🏀",  "provider": "Apify/FlashScore + MySportsFeeds"},
    "NFL":       {"icon": "🏈",  "provider": "Apify/FlashScore + MySportsFeeds"},
    "MLB":       {"icon": "⚾",  "provider": "Apify/FlashScore + MySportsFeeds"},
    "NHL":       {"icon": "🏒",  "provider": "Apify/FlashScore + MySportsFeeds"},
    "UFC":       {"icon": "🥊",  "provider": "Apify/FlashScore + TheSportsDB"},
    "Formula 1": {"icon": "🏎️", "provider": "Apify/FlashScore + TheSportsDB"},
    "Tennis":    {"icon": "🎾",  "provider": "Apify/FlashScore + TheSportsDB"},
    "Cricket":   {"icon": "🏏",  "provider": "Apify/FlashScore + TheSportsDB"},
    "Golf":      {"icon": "⛳",  "provider": "Apify/FlashScore + TheSportsDB"},
}
STATUS_OPTIONS = ["ALL", "LIVE", "UPCOMING", "FINISHED"]
SPORT_NAMES    = list(SPORT_OPTIONS.keys())

# ── Plotly theme ─────────────────────────────────────────────────────────────
GOLD_PALETTE = ["#D4AF37","#FFD700","#00ff88","#ff6b6b","#00d4ff",
                "#FF8C00","#7B68EE","#20B2AA","#FF69B4","#98FB98"]
DARK_LAYOUT  = dict(
    paper_bgcolor="rgba(10,10,15,0)",
    plot_bgcolor="rgba(26,26,46,0.5)",
    font=dict(family="Rajdhani", color="#e6f1ff"),
    margin=dict(l=20, r=20, t=40, b=20),
)

# ── Session state init ────────────────────────────────────────────────────────
def _init_state():
    for k, v in {
        "selected_sport":     SPORT_NAMES[0],
        "selected_league_id": "ALL",
        "selected_status":    "UPCOMING",
        "kelly_pct":          25,
        "max_bet_pct":        3,
        "min_ev":             2,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Cache clear ───────────────────────────────────────────────────────────────
def _clear_all_caches():
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()
    router = data.router
    for attr in ["api_sports", "football_data", "msf", "tsdb", "apify"]:
        provider = getattr(router, attr, None)
        if provider is not None and hasattr(provider, "clear"):
            try: provider.clear()
            except Exception: pass


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
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
            'ELITE AI PREDICTION DASHBOARD v4.1</text></svg>'
        )
        logo_html = f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" class="logo-img">'

    st.markdown(f'<div class="logo-center">{logo_html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tagline-sub">Claude AI Engine | Real-Time Intelligence | Where Instinct Meets Data</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        ai_label = "🤖 AI ENGINE ONLINE" if ai.available else "⚠️ AI ENGINE OFFLINE"
        st.markdown(f'<div class="ai-status">{ai_label}</div>', unsafe_allow_html=True)

    now = datetime.now(timezone.utc)
    cities = [("LONDON", now + timedelta(hours=1)), ("NEW YORK", now - timedelta(hours=5)),
              ("TOKYO", now + timedelta(hours=9)), ("SYDNEY", now + timedelta(hours=10)),
              ("LAGOS", now + timedelta(hours=1)), ("JOHANNESBURG", now + timedelta(hours=2))]
    clock = " | ".join(f"{c}: {dt.strftime('%H:%M')}" for c, dt in cities)
    st.markdown(f'<div class="world-clock">🌍 {clock}</div>', unsafe_allow_html=True)

    live_color = "#00ff88" if data.is_live else "#FFD700"
    live_text  = "LIVE MODE — Global APIs Connected" if data.is_live else "⚠️ API Keys Not Detected"
    ai_color   = "#00ff88" if ai.available else "#ff6b6b"
    ai_text    = "Claude AI Active" if ai.available else "Set ANTHROPIC_API_KEY in Render"
    st.markdown(
        f'<div style="display:flex;gap:12px;margin:10px 0;">'
        f'<div style="flex:1;background:rgba(0,0,0,.3);border:1px solid {live_color};border-radius:8px;padding:10px;text-align:center;font-family:Orbitron;font-size:.85rem;font-weight:700;color:{live_color};">🟢 {live_text}</div>'
        f'<div style="flex:1;background:rgba(0,0,0,.3);border:1px solid {ai_color};border-radius:8px;padding:10px;text-align:center;font-family:Orbitron;font-size:.85rem;font-weight:700;color:{ai_color};">🧠 {ai_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    with st.sidebar:
        sb_logo = Path("BRAND_ASSET/empire_logo_arena.png")
        if sb_logo.exists():
            with open(sb_logo, "rb") as f:
                sb_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<div style="text-align:center;margin-bottom:10px;">'
                f'<img src="data:image/png;base64,{sb_b64}" style="width:85%;max-height:100px;object-fit:contain;display:block;margin:0 auto;"></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center;color:#D4AF37;font-family:Orbitron;font-size:16px;font-weight:900;margin-bottom:10px;letter-spacing:4px;">⚡ EMPIRE</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<h2 style="text-align:center;font-size:1.1rem;margin-top:0;">COMMAND CENTER</h2>', unsafe_allow_html=True)

        ai_col  = "#00ff88" if ai.available else "#ff6b6b"
        stats   = ai.get_stats()
        ai_stat = "● CLAUDE ONLINE" if ai.available else "● CLAUDE OFFLINE"
        ai_sub  = f"Calls: {stats['api_calls']} | Cache: {stats['cache_active']}"
        st.markdown(
            f'<div style="background:rgba(0,255,136,.1);border:1px solid {ai_col};border-radius:8px;padding:10px;margin:10px 0;text-align:center;">'
            f'<div style="color:{ai_col};font-family:Orbitron;font-size:.75rem;">🤖 INSTINCT BOT v4.1<br>'
            f'<span style="color:#888;font-size:.7rem;">CLAUDE AI PREDICTION ENGINE</span><br>'
            f'<span style="color:{ai_col};">{ai_stat}</span><br>'
            f'<span style="color:#555;font-size:.65rem;">{ai_sub}</span></div></div>',
            unsafe_allow_html=True,
        )

        st.subheader("⚡ SYSTEM STATUS")
        st.markdown('<div style="background:rgba(0,0,0,.3);border-radius:8px;padding:10px;margin:8px 0;">', unsafe_allow_html=True)
        try:
            for s in data.router.get_provider_status():
                color = "#00ff88" if ("ONLINE" in s.get("status","") or "🟢" in s.get("status","")) else "#888"
                st.markdown(
                    f'<div style="font-family:Orbitron;font-size:.65rem;color:{color};padding:2px 0;">'
                    f'{s.get("name","")}: {s.get("status","")}</div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.caption(f"Status unavailable: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        st.markdown(
            '<div style="color:#D4AF37;font-family:Orbitron;font-size:.85rem;text-align:center;margin-bottom:8px;">🏟️ ARENA CONTROLS</div>',
            unsafe_allow_html=True,
        )

        sport_labels = [f"{SPORT_OPTIONS[s]['icon']} {s}" for s in SPORT_NAMES]
        prev_sport   = st.session_state.selected_sport
        sport_choice = st.selectbox("🎯 SELECT SPORT", options=sport_labels,
                                    index=SPORT_NAMES.index(prev_sport), key="sport_selectbox")
        chosen_sport = SPORT_NAMES[sport_labels.index(sport_choice)]
        if chosen_sport != prev_sport:
            st.session_state.selected_sport     = chosen_sport
            st.session_state.selected_league_id = "ALL"
            st.session_state.selected_status    = "ALL"
            _clear_all_caches()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:6px 0;'>", unsafe_allow_html=True)

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
            "🏆 SELECT LEAGUE",
            options=league_labels,
            index=league_ids.index(st.session_state.selected_league_id),
            key=f"league_selectbox__{st.session_state.selected_sport}",
        )
        new_league_id = league_ids[league_labels.index(league_choice)]
        if new_league_id != st.session_state.selected_league_id:
            st.session_state.selected_league_id = new_league_id
            st.cache_data.clear()
            st.rerun()

        status_choice = st.selectbox(
            "📊 MATCH STATUS",
            options=STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(st.session_state.selected_status)
                  if st.session_state.selected_status in STATUS_OPTIONS else 0,
            key=f"status_selectbox__{st.session_state.selected_sport}",
        )
        if status_choice != st.session_state.selected_status:
            st.session_state.selected_status = status_choice
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            _clear_all_caches()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)
        st.subheader("🛡️ RISK CONTROLS")
        st.session_state.kelly_pct   = st.slider("KELLY %",  5,  50, st.session_state.kelly_pct,   5, format="%d%%")
        st.session_state.max_bet_pct = st.slider("MAX BET",  1,  10, st.session_state.max_bet_pct, 1, format="%d%%")
        st.session_state.min_ev      = st.slider("MIN EV",   1,  10, st.session_state.min_ev,      1, format="%d%%")
        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED — No bets placed")
        st.markdown(
            '<div style="font-family:Rajdhani;font-size:.75rem;color:#555;text-align:center;margin-top:4px;">→ Full calculator in Analytics tab</div>',
            unsafe_allow_html=True,
        )

        st.checkbox("🔧 Show Debug Info", key="show_debug")

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


# ═══════════════════════════════════════════════════════════════════════════════
# TICKER
# ═══════════════════════════════════════════════════════════════════════════════
def render_ticker():
    st.markdown(
        '<div class="ticker"><div class="ticker-text">'
        '🧠 CLAUDE AI ACTIVE — GENERATING PREDICTIONS IN REAL TIME &nbsp;·&nbsp; '
        '⚽ Football &nbsp;·&nbsp; 🏀 NBA &nbsp;·&nbsp; 🏈 NFL &nbsp;·&nbsp; '
        '⚾ MLB &nbsp;·&nbsp; 🏒 NHL &nbsp;·&nbsp; 🥊 UFC &nbsp;·&nbsp; '
        '🏎️ F1 &nbsp;·&nbsp; 🎾 Tennis &nbsp;·&nbsp; 🏏 Cricket &nbsp;·&nbsp; ⛳ Golf'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:   return "#00FF88", "rgba(0,255,136,.15)", "● LIVE"
    if any(x in su for x in ("FINISH","FT","FINAL","COMPLETED")): return "#888","rgba(136,136,136,.15)","FINISHED"
    return "#FFAA00", "rgba(255,170,0,.15)", "UPCOMING"


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_live(sport: str, league_id: str) -> pd.DataFrame:
    try:
        return st.session_state.empire_data.get_live_matches_df(
            sport, None if league_id == "ALL" else league_id)
    except Exception as e:
        logger.error(f"_fetch_live: {e}"); return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_upcoming(sport: str) -> pd.DataFrame:
    try:
        return st.session_state.empire_data.get_upcoming_matches_df(sport)
    except Exception as e:
        logger.error(f"_fetch_upcoming: {e}"); return pd.DataFrame()


def _fetch_matches(sport: str, league_id: str, status: str) -> pd.DataFrame:
    try:
        if status == "LIVE":     df = _fetch_live(sport, league_id)
        elif status == "UPCOMING": df = _fetch_upcoming(sport)
        elif status == "FINISHED": df = pd.DataFrame()
        else:
            parts = [d for d in [_fetch_live(sport, league_id), _fetch_upcoming(sport)] if not d.empty]
            df    = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    except Exception as e:
        logger.error(f"_fetch_matches: {e}"); df = pd.DataFrame()
    return df


def _get_league_name(sport: str, league_id: str) -> str:
    if league_id == "ALL": return "All Leagues"
    for lg in data.get_all_leagues(sport):
        if str(lg.get("id","")) == str(league_id): return lg.get("name", league_id)
    return league_id


def _apply_league_filter(df: pd.DataFrame, sport: str, league_id: str):
    league_name = _get_league_name(sport, league_id)
    if league_id == "ALL" or df.empty: return df, league_name, "all"
    if "LEAGUE_ID" in df.columns:
        filtered = df[df["LEAGUE_ID"].astype(str) == str(league_id)]
        if not filtered.empty: return filtered, league_name, "exact"
    if "LEAGUE" in df.columns:
        filtered = df[df["LEAGUE"].astype(str).str.strip().str.lower() == league_name.strip().lower()]
        if not filtered.empty: return filtered, league_name, "exact"
        filtered = df[df["LEAGUE"].astype(str).str.contains(league_name, case=False, na=False, regex=False)]
        if not filtered.empty: return filtered, league_name, "partial"
    return pd.DataFrame(), league_name, "none"


# ═══════════════════════════════════════════════════════════════════════════════
# KELLY CRITERION
# ═══════════════════════════════════════════════════════════════════════════════
def kelly_bet_size(model_prob_pct: float, decimal_odds: float,
                   bankroll: float, kelly_fraction: float = 0.25,
                   max_bet_pct: float = 0.03) -> dict:
    p = max(0.001, min(0.999, model_prob_pct / 100.0))
    q = 1.0 - p
    b = max(0.001, decimal_odds - 1.0)
    full_kelly       = (b * p - q) / b
    fractional_kelly = full_kelly * kelly_fraction
    bet_size         = max(0.0, min(fractional_kelly, max_bet_pct) * bankroll)
    implied_prob_pct = round(100.0 / decimal_odds, 2)
    edge             = round(model_prob_pct - implied_prob_pct, 2)
    ev_pct           = round((p * b - q) * 100, 2)
    return {
        "full_kelly_pct":       round(full_kelly * 100, 2),
        "fractional_kelly_pct": round(fractional_kelly * 100, 2),
        "bet_size":             round(bet_size, 2),
        "implied_prob_pct":     implied_prob_pct,
        "edge_pct":             edge,
        "ev_pct":               ev_pct,
        "roi_pct":              round((p * decimal_odds - 1) * 100, 2),
        "is_value":             edge > 0 and ev_pct > 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION CARD
# ═══════════════════════════════════════════════════════════════════════════════
def render_prediction_card(pred: MatchPrediction):
    card_class = ("pred-card pred-card-high"   if pred.confidence >= HIGH_CONF   else
                  "pred-card pred-card-medium" if pred.confidence >= MEDIUM_CONF else
                  "pred-card pred-card-low")
    color = confidence_color(pred.confidence)
    bar   = confidence_bar_html(pred.confidence, 180)
    donut = probability_donut_html(pred.home_win_pct, pred.draw_pct, pred.away_win_pct,
                                   pred.home_team, pred.away_team)
    value_badge = '<span class="value-badge">💰 VALUE BET</span>' if pred.value_rating in ("⭐⭐⭐","⭐⭐") else ""

    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
    h1, h2 = st.columns([3, 2])
    with h1:
        st.markdown(
            f'<div style="font-family:Rajdhani;font-size:.8rem;color:#8892b0;">{pred.league}</div>'
            f'<div style="font-family:Rajdhani;font-size:1.2rem;font-weight:700;color:#e6f1ff;">'
            f'{pred.home_team} <span style="color:#888;">vs</span> {pred.away_team}</div>'
            f'<div style="margin-top:10px;"><span class="bet-badge">{pred.recommended_bet}</span>{value_badge}</div>'
            f'<div style="margin-top:10px;color:#888;font-size:.8rem;font-family:Rajdhani;">'
            f'Rating: {pred.value_rating} &nbsp;|&nbsp; {pred.generated_at[11:16]}'
            + (f' &nbsp;|&nbsp; Model: {pred.model_version}' if pred.model_version else '')
            + '</div>',
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(donut, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2a2a3e;margin:12px 0;">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
        f'<span style="font-family:Orbitron;font-size:.75rem;color:#888;">CONFIDENCE</span>'
        f'{bar}'
        f'<span style="font-family:Orbitron;font-size:1rem;font-weight:900;color:{color};">'
        f'{pred.confidence}% {pred.confidence_label}</span></div>',
        unsafe_allow_html=True,
    )

    if pred.expected_goals and pred.expected_goals != "—":
        st.markdown(
            f'<div style="font-family:Orbitron;font-size:.8rem;color:#888;margin-bottom:8px;">'
            f'⚽ xG: <span style="color:#FFD700;">{pred.expected_goals}</span></div>',
            unsafe_allow_html=True,
        )

    if pred.ai_summary:
        st.markdown(f'<div class="ai-narrative">💬 {pred.ai_summary}</div>', unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    with f1:
        st.markdown('<div style="font-family:Orbitron;font-size:.7rem;color:#D4AF37;margin-bottom:6px;">✅ KEY FACTORS</div>', unsafe_allow_html=True)
        for factor in pred.key_factors[:4]:
            st.markdown(f'<div class="factor-item">{factor}</div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div style="font-family:Orbitron;font-size:.7rem;color:#ff6b6b;margin-bottom:6px;">⚠️ RISK FACTORS</div>', unsafe_allow_html=True)
        for risk in pred.risk_factors[:3]:
            st.markdown(f'<div class="risk-item">{risk}</div>', unsafe_allow_html=True)

    if pred.betting_angle and pred.betting_angle != "—":
        st.markdown(
            f'<div style="margin-top:12px;background:rgba(212,175,55,.1);border-radius:8px;padding:10px;">'
            f'<span style="font-family:Orbitron;font-size:.7rem;color:#D4AF37;">🎯 BETTING ANGLE: </span>'
            f'<span style="font-family:Rajdhani;color:#FFD700;font-size:.95rem;">{pred.betting_angle}</span></div>',
            unsafe_allow_html=True,
        )

    if pred.error:
        st.error(f"Error: {pred.error}")

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH CARDS
# ═══════════════════════════════════════════════════════════════════════════════
def render_match_cards(matches_df: pd.DataFrame, sport: str):
    if matches_df is None or matches_df.empty:
        st.info(f"📡 No {sport} matches found. Try a different league or status filter.")
        return

    st.markdown(f"<div style='color:#888;font-size:.85rem;margin-bottom:10px;'>📊 {len(matches_df)} matches found</div>", unsafe_allow_html=True)

    for idx, row in matches_df.iterrows():
        home       = str(row.get("HOME_TEAM", "TBD")).replace("<","&lt;")
        away       = str(row.get("AWAY_TEAM", "TBD")).replace("<","&lt;")
        score      = str(row.get("SCORE", "vs"))
        league     = str(row.get("LEAGUE", "")).replace("<","&lt;")
        mtime      = str(row.get("TIME", ""))
        match_id   = str(row.get("MATCH_ID", str(idx)))
        status_raw = str(row.get("STATUS", "UPCOMING"))
        color, bg, label = _status_style(status_raw)

        st.markdown(
            f'<div style="background:linear-gradient(135deg,rgba(20,25,40,.9),rgba(10,15,30,.95));border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px;margin:8px 0;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<span style="color:#8892b0;font-size:.75rem;">{league}</span>'
            f'<span style="color:{color};background:{bg};padding:2px 10px;border-radius:10px;font-size:.7rem;font-weight:700;">{label}</span></div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="flex:1;text-align:left;"><div style="color:#e6f1ff;font-size:1rem;font-weight:600;">{home}</div></div>'
            f'<div style="padding:0 20px;text-align:center;"><div style="color:#00d4ff;font-size:1.4rem;font-weight:700;">{score}</div><div style="color:#8892b0;font-size:.65rem;">{mtime}</div></div>'
            f'<div style="flex:1;text-align:right;"><div style="color:#e6f1ff;font-size:1rem;font-weight:600;">{away}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([7, 1])
        with col1:
            if st.button("🧠 AI PREDICT", key=f"predict_{sport}_{match_id}_{idx}", use_container_width=True):
                for k, v in [("selected_match_id", match_id), ("selected_match_row", row.to_dict()),
                             ("selected_match_home", home), ("selected_match_away", away), ("selected_match_sport", sport)]:
                    st.session_state[k] = v
                st.rerun()
        with col2:
            if st.button("🔍", key=f"view_{sport}_{match_id}_{idx}", use_container_width=True):
                for k, v in [("selected_match_id", match_id), ("selected_match_row", row.to_dict()),
                             ("selected_match_home", home), ("selected_match_away", away), ("selected_match_sport", sport)]:
                    st.session_state[k] = v
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH DETAIL
# ═══════════════════════════════════════════════════════════════════════════════
def render_match_detail():
    match_id  = st.session_state.get("selected_match_id", "")
    match_row = st.session_state.get("selected_match_row", {})
    home      = st.session_state.get("selected_match_home", "Home")
    away      = st.session_state.get("selected_match_away", "Away")
    sport     = st.session_state.get("selected_match_sport", st.session_state.selected_sport)

    st.markdown(f'<div class="section-header">🧠 AI ANALYSIS — {home} vs {away}</div>', unsafe_allow_html=True)

    if st.button("← Back to Match List"):
        for k in ("selected_match_id","selected_match_row","selected_match_home","selected_match_away","selected_match_sport"):
            st.session_state.pop(k, None)
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 📋 MATCH INFORMATION")
        for label, key in [("League","LEAGUE"),("Status","STATUS"),("Time","TIME"),("Score","SCORE"),("Provider","PROVIDER")]:
            val = match_row.get(key, "N/A")
            st.markdown(f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{val}</span></div>', unsafe_allow_html=True)
    with c2:
        score_val = match_row.get("SCORE", "vs")
        st.markdown(
            f'<div style="text-align:center;padding:20px;">'
            f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-bottom:4px;">{sport.upper()}</div>'
            f'<div style="font-family:Orbitron;font-size:2.5rem;color:#FFD700;font-weight:900;">{score_val}</div>'
            f'<div style="font-family:Rajdhani;font-size:1rem;color:#8892b0;margin-top:4px;">{home} vs {away}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    if not ai.available:
        st.error("🔴 ANTHROPIC_API_KEY not set. Add it in Render → Settings → Environment.")
        return

    cached = ai.cache.get(match_id, sport)
    force  = st.button("🔄 Regenerate Prediction", key=f"regen_{match_id}")

    if cached and not force:
        pred = cached
        st.caption(f"⚡ Cached — generated {pred.generated_at[11:16]}")
    else:
        with st.spinner("🧠 Claude AI analysing match..."):
            pred = ai.predict_match(match_row, sport, force=force)

    render_prediction_card(pred)

    # Inline Kelly calculator
    if pred.confidence > 0:
        st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin-bottom:12px;">💰 QUICK BET SIZER</div>', unsafe_allow_html=True)
        ck1, ck2 = st.columns(2)
        with ck1:
            bankroll  = st.number_input("Bankroll ($)", 100, 500000, 1000, 100, key=f"bk_{match_id}")
            dec_odds  = st.number_input("Decimal Odds", 1.01, 30.0, 2.0, 0.05, key=f"odds_{match_id}")
        with ck2:
            result    = kelly_bet_size(
                model_prob_pct=float(pred.confidence),
                decimal_odds=float(dec_odds),
                bankroll=float(bankroll),
                kelly_fraction=st.session_state.kelly_pct / 100.0,
                max_bet_pct=st.session_state.max_bet_pct / 100.0,
            )
            css_class = "kelly-result-good" if result["is_value"] else "kelly-result-bad"
            verdict   = "✅ VALUE BET" if result["is_value"] else "❌ NO VALUE — PASS"
            vc        = "#00ff88" if result["is_value"] else "#ff6b6b"
            st.markdown(
                f'<div class="{css_class}">'
                f'<div style="font-family:Orbitron;font-size:1rem;color:{vc};">{verdict}</div>'
                f'<div style="font-family:Rajdhani;font-size:1.2rem;color:#FFD700;margin-top:8px;">Bet: <strong>${result["bet_size"]:.2f}</strong></div>'
                f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-top:4px;">'
                f'Edge: {result["edge_pct"]:+.1f}% | EV: {result["ev_pct"]:+.1f}% | Kelly: {result["fractional_kelly_pct"]:.1f}%</div>'
                f'<div style="font-family:Rajdhani;font-size:.8rem;color:#555;margin-top:4px;">'
                f'Implied: {result["implied_prob_pct"]}% | Model: {pred.confidence}%</div></div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ARENA TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_arena(sport: str, league_id: str, status: str):
    if "selected_match_id" in st.session_state:
        render_match_detail()
        return

    icon     = SPORT_OPTIONS.get(sport, {}).get("icon", "🏆")
    provider = SPORT_OPTIONS.get(sport, {}).get("provider", "")
    st.markdown(f'<div class="section-header">{icon} EMPIRE ARENA — {sport.upper()}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:#00ff88;font-family:Orbitron;font-size:.7rem;margin-bottom:10px;">📡 {provider} | Real-time data</div>', unsafe_allow_html=True)

    with st.spinner(f"📡 Fetching {sport} matches..."):
        df = _fetch_matches(sport, league_id, status)

    df, league_name, filter_status = _apply_league_filter(df, sport, league_id)

    if filter_status == "exact":   st.success(f"✅ {len(df)} matches — **{league_name}**")
    elif filter_status == "partial": st.info(f"ℹ️ Partial match: {len(df)} results for **{league_name}**")
    elif filter_status == "none":
        st.warning(f"⚠️ No **{league_name}** matches in current window. Try a different status or 'All Events'.")

    if st.session_state.get("show_debug"):
        with st.expander("🔧 DEBUG"):
            st.write(f"League ID: {league_id} | Name: {league_name} | Filter: {filter_status} | Shape: {df.shape}")
            raw = _fetch_matches(sport, "ALL", status)
            if not raw.empty and "LEAGUE" in raw.columns:
                for ul in sorted(raw["LEAGUE"].astype(str).unique())[:30]:
                    st.write(f"• {ul} ({len(raw[raw['LEAGUE']==ul])})")

    render_match_cards(df, sport)


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_predictions(sport: str, league_id: str, status: str):
    st.markdown('<div class="section-header">🎯 AI PREDICTION CENTER</div>', unsafe_allow_html=True)

    if not ai.available:
        st.error("🔴 ANTHROPIC_API_KEY not configured. Add it in Render → Settings → Environment Variables.")
        return

    stats = ai.get_stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI CALLS",     stats["api_calls"])
    m2.metric("CACHED PREDS", stats["cache_active"])
    m3.metric("ERRORS",       stats["errors"])
    m4.metric("MODEL",        stats["model"][:18] if stats["model"] else "—")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    df = _fetch_matches(sport, league_id, status)
    df, league_name, filter_status = _apply_league_filter(df, sport, league_id)

    if df.empty:
        st.info(f"No {league_name} matches to analyse. Adjust filters in the sidebar.")
        return

    col_scan, col_info = st.columns([2, 3])
    with col_scan:
        run_scan = st.button("⚡ RUN AI BATCH SCANNER", use_container_width=True)
    with col_info:
        st.markdown(
            f'<div style="color:#888;font-family:Rajdhani;font-size:.9rem;padding-top:8px;">'
            f'🔍 Scanning {min(len(df),20)} {league_name} matches | picks ≥65% confidence</div>',
            unsafe_allow_html=True,
        )

    if run_scan or "batch_result" in st.session_state:
        if run_scan:
            with st.spinner("🧠 Claude AI scanning for value..."):
                result = ai.scan_matches(df, sport)
            st.session_state.batch_result = result
        else:
            result = st.session_state.get("batch_result")

        if result and isinstance(result, BulkScanResult):
            st.markdown(
                f'<div style="background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.3);border-radius:10px;padding:12px;margin:10px 0;font-family:Rajdhani;">'
                f'<span style="color:#00ff88;font-family:Orbitron;font-size:.85rem;">⚡ SCAN COMPLETE</span> — '
                f'{result.total_matches} analysed | {len(result.high_conf_picks)} high-conf picks | '
                f'{len(result.value_bets)} value bets | {result.scan_time}</div>',
                unsafe_allow_html=True,
            )
            if result.high_conf_picks:
                st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin:16px 0 8px;">🏆 TOP CONFIDENCE PICKS</div>', unsafe_allow_html=True)
                for pick in result.high_conf_picks:
                    conf  = pick.get("confidence", 0)
                    color = confidence_color(conf)
                    bar   = confidence_bar_html(conf, 150)
                    st.markdown(
                        f'<div class="scan-pick">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'<div><span style="font-family:Rajdhani;color:#e6f1ff;font-size:1rem;">{pick.get("home_team","?")} vs {pick.get("away_team","?")}</span>'
                        f'<span style="color:#8892b0;font-size:.8rem;margin-left:8px;">— {pick.get("league","")}</span></div>'
                        f'<span style="color:{color};font-family:Orbitron;font-size:.85rem;font-weight:700;">{conf}% {pick.get("value_rating","")}</span></div>'
                        f'<div style="margin-top:8px;"><span class="bet-badge">{pick.get("recommended_bet","")}</span></div>'
                        f'<div style="margin-top:8px;color:#ccd6f6;font-family:Rajdhani;font-size:.9rem;">{pick.get("one_line_reason","")}</div>'
                        f'<div style="margin-top:8px;">{bar}</div></div>',
                        unsafe_allow_html=True,
                    )
            if result.value_bets:
                st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#00ff88;margin:16px 0 8px;">💰 VALUE BETS</div>', unsafe_allow_html=True)
                for vb in result.value_bets:
                    st.markdown(
                        f'<div style="background:rgba(0,255,136,.06);border:1px solid rgba(0,255,136,.25);border-radius:10px;padding:12px;margin:6px 0;">'
                        f'<span style="color:#e6f1ff;font-size:1rem;">{vb.get("match","")}</span>'
                        f'<div style="margin-top:6px;"><span class="bet-badge">{vb.get("bet","")}</span>'
                        f'<span style="color:#00ff88;margin-left:12px;font-size:.9rem;">Edge: {vb.get("edge","")} {vb.get("rating","")}</span></div></div>',
                        unsafe_allow_html=True,
                    )

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin-bottom:12px;">🔍 INDIVIDUAL MATCH ANALYSIS</div>', unsafe_allow_html=True)

    for idx, row in df.head(15).iterrows():
        home     = row.get("HOME_TEAM", "TBD")
        away     = row.get("AWAY_TEAM", "TBD")
        league   = row.get("LEAGUE", "")
        match_id = row.get("MATCH_ID", str(idx))
        mtime    = row.get("TIME", "")

        cached_pred = ai.cache.get(str(match_id), sport)
        has_pred    = cached_pred is not None

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            badge = ""
            if has_pred and hasattr(cached_pred, "confidence"):
                cc    = confidence_color(cached_pred.confidence)
                badge = f' <span style="color:{cc};font-family:Orbitron;font-size:.7rem;border:1px solid {cc};border-radius:8px;padding:2px 8px;">🧠 {cached_pred.confidence}%</span>'
            st.markdown(
                f'<div style="padding:8px 0;border-bottom:1px solid #2a2a3e;">'
                f'<span style="font-family:Rajdhani;color:#e6f1ff;">{home} vs {away}</span>'
                f'<span style="color:#8892b0;font-size:.8rem;margin-left:8px;">— {league} | {mtime}</span>'
                f'{badge}</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            btn_label = "⚡ Cached" if has_pred else "🧠 Predict"
            if st.button(btn_label, key=f"pred_tab_{match_id}_{idx}", use_container_width=True):
                with st.spinner(f"🧠 Analysing {home} vs {away}..."):
                    pred = ai.predict_match(row.to_dict(), sport)
                render_prediction_card(pred)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB — REAL CHARTS + KELLY CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
def render_analytics():
    st.markdown('<div class="section-header">📊 EMPIRE ANALYTICS & INTELLIGENCE</div>', unsafe_allow_html=True)

    # Row 1: AI Engine Metrics
    stats = ai.get_stats()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("AI CALLS",     stats["api_calls"])
    m2.metric("CACHED PREDS", stats["cache_active"])
    m3.metric("PRED LOG",     stats["predictions"])
    m4.metric("ERRORS",       stats["errors"])
    m5.metric("ENGINE",       "Claude AI")

    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # AI engine status block
    ai_col  = "#00ff88" if ai.available else "#ff6b6b"
    ai_stat = "ONLINE" if ai.available else "OFFLINE — Set ANTHROPIC_API_KEY"
    model_n = stats["model"] or "Not yet resolved"
    st.markdown(
        f'<div style="background:rgba(0,0,0,.3);border:1px solid {ai_col};border-radius:10px;padding:16px;margin:10px 0;">'
        f'<div style="font-family:Orbitron;font-size:.9rem;color:{ai_col};">🧠 CLAUDE AI ENGINE: {ai_stat}</div>'
        f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-top:8px;">'
        f'Active model: {model_n}<br>'
        f'Confidence thresholds — HIGH ≥{HIGH_CONF}% | MEDIUM ≥{MEDIUM_CONF}% | LOW below {MEDIUM_CONF}%<br>'
        f'Cache TTL: 30 min per prediction</div></div>',
        unsafe_allow_html=True,
    )

    # Row 3: Live Match Data Charts
    sport     = st.session_state.selected_sport
    league_id = st.session_state.selected_league_id

    st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin:16px 0 8px;">📡 LIVE MATCH DATA INTELLIGENCE</div>', unsafe_allow_html=True)

    with st.spinner("Loading match intelligence..."):
        df_all = _fetch_matches(sport, "ALL", "ALL")

    if not df_all.empty:
        ch1, ch2 = st.columns(2)

        # Chart 1: Competition Distribution
        with ch1:
            if "LEAGUE" in df_all.columns:
                league_counts = df_all["LEAGUE"].value_counts().head(10)
                fig_pie = go.Figure(data=[go.Pie(
                    labels=league_counts.index.tolist(),
                    values=league_counts.values.tolist(),
                    hole=0.45,
                    marker=dict(colors=GOLD_PALETTE, line=dict(color="#0a0a0f", width=2)),
                    textfont=dict(family="Rajdhani", size=11, color="#fff"),
                    hovertemplate="<b>%{label}</b><br>Matches: %{value}<br>%{percent}<extra></extra>",
                )])
                fig_pie.update_layout(
                    title=dict(text="🏆 MATCHES BY COMPETITION", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                    showlegend=True,
                    legend=dict(font=dict(family="Rajdhani", size=10, color="#888"), bgcolor="rgba(0,0,0,0)"),
                    **DARK_LAYOUT, height=320,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("League data not available.")

        # Chart 2: Match Status Breakdown
        with ch2:
            if "STATUS" in df_all.columns:
                status_counts = df_all["STATUS"].value_counts()
                bar_colors    = ["#00ff88" if "LIVE" in str(s).upper() else "#888" if "FINISH" in str(s).upper() else "#D4AF37" for s in status_counts.index]
                fig_bar = go.Figure(data=[go.Bar(
                    x=status_counts.index.tolist(),
                    y=status_counts.values.tolist(),
                    marker_color=bar_colors,
                    text=status_counts.values.tolist(),
                    textposition="outside",
                    textfont=dict(family="Orbitron", size=13, color="#FFD700"),
                    hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
                )])
                fig_bar.update_layout(
                    title=dict(text="📊 MATCH STATUS BREAKDOWN", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                    xaxis=dict(tickfont=dict(family="Rajdhani", size=11, color="#888")),
                    yaxis=dict(tickfont=dict(family="Rajdhani", size=11, color="#888"), gridcolor="rgba(212,175,55,.1)"),
                    **DARK_LAYOUT, height=320,
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Status data not available.")

        # Chart 3: Match Timeline (scatter)
        if "TIME" in df_all.columns and "HOME_TEAM" in df_all.columns:
            try:
                tdf = df_all[["TIME","LEAGUE","HOME_TEAM","AWAY_TEAM","STATUS"]].copy()
                tdf["MATCH"] = tdf["HOME_TEAM"] + " vs " + tdf["AWAY_TEAM"]
                tdf = tdf[tdf["TIME"].str.len() > 4].head(30)
                if not tdf.empty:
                    fig_tl = px.scatter(tdf, x="TIME", y="LEAGUE", text="MATCH", color="STATUS",
                                        color_discrete_sequence=GOLD_PALETTE)
                    fig_tl.update_traces(textposition="top center", textfont=dict(family="Rajdhani", size=9), marker=dict(size=10))
                    fig_tl.update_layout(
                        title=dict(text="⏱️ MATCH SCHEDULE OVERVIEW", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                        xaxis=dict(tickfont=dict(family="Rajdhani", size=10, color="#888")),
                        yaxis=dict(tickfont=dict(family="Rajdhani", size=10, color="#888")),
                        **DARK_LAYOUT, height=360, showlegend=True,
                        legend=dict(font=dict(family="Rajdhani", size=10, color="#888"), bgcolor="rgba(0,0,0,0)"),
                    )
                    st.plotly_chart(fig_tl, use_container_width=True)
            except Exception:
                pass
    else:
        st.info(f"No {sport} data loaded yet. Fetch matches from the ARENA tab first.")

    # API Provider Status
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin:16px 0 8px;">📡 API PROVIDER STATUS</div>', unsafe_allow_html=True)
    try:
        provider_statuses = data.router.get_provider_status()
        if provider_statuses:
            pcols = st.columns(min(len(provider_statuses), 5))
            for i, ps in enumerate(provider_statuses[:5]):
                name   = ps.get("name","PROVIDER")
                status = ps.get("status","UNKNOWN")
                quota  = ps.get("quota_remaining", None)
                is_on  = "ONLINE" in str(status).upper() or "🟢" in str(status)
                col_c  = "#00ff88" if is_on else "#ff6b6b"
                with pcols[i]:
                    st.markdown(
                        f'<div style="background:rgba(0,0,0,.4);border:1px solid {col_c};border-radius:10px;padding:12px;text-align:center;">'
                        f'<div style="font-family:Orbitron;font-size:.7rem;color:{col_c};">{"🟢" if is_on else "🔴"} {name}</div>'
                        f'<div style="font-family:Rajdhani;font-size:.85rem;color:#888;margin-top:4px;">{status}</div>'
                        + (f'<div style="font-family:Orbitron;font-size:.8rem;color:#FFD700;margin-top:6px;">{quota} req left</div>' if quota is not None else "")
                        + '</div>',
                        unsafe_allow_html=True,
                    )
    except Exception as e:
        st.caption(f"Provider status unavailable: {e}")

    # Prediction Performance Charts
    pred_log = ai.get_prediction_log()
    if pred_log:
        st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Orbitron;font-size:.9rem;color:#D4AF37;margin:16px 0 8px;">🧠 AI PREDICTION PERFORMANCE</div>', unsafe_allow_html=True)

        log_df = pd.DataFrame(pred_log)
        pc1, pc2 = st.columns(2)

        with pc1:
            if "confidence" in log_df.columns:
                fig_hist = go.Figure(data=[go.Histogram(
                    x=log_df["confidence"].tolist(), nbinsx=10,
                    marker=dict(
                        color=["#00ff88" if c >= HIGH_CONF else "#FFD700" if c >= MEDIUM_CONF else "#ff6b6b" for c in log_df["confidence"]],
                        line=dict(color="#0a0a0f", width=1),
                    ),
                    opacity=0.85,
                    hovertemplate="Confidence: %{x}%<br>Count: %{y}<extra></extra>",
                )])
                fig_hist.update_layout(
                    title=dict(text="📈 CONFIDENCE DISTRIBUTION", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                    xaxis=dict(title="Confidence %", tickfont=dict(family="Rajdhani", color="#888")),
                    yaxis=dict(tickfont=dict(family="Rajdhani", color="#888"), gridcolor="rgba(212,175,55,.1)"),
                    **DARK_LAYOUT, height=300,
                )
                st.plotly_chart(fig_hist, use_container_width=True)

        with pc2:
            if "rating" in log_df.columns:
                rating_counts = log_df["rating"].value_counts()
                fig_rating = go.Figure(data=[go.Pie(
                    labels=rating_counts.index.tolist(),
                    values=rating_counts.values.tolist(),
                    hole=0.4,
                    marker=dict(colors=["#00ff88","#FFD700","#D4AF37","#888"], line=dict(color="#0a0a0f", width=2)),
                    textfont=dict(family="Rajdhani", size=12, color="#fff"),
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
                )])
                fig_rating.update_layout(
                    title=dict(text="⭐ VALUE RATING BREAKDOWN", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                    showlegend=True,
                    legend=dict(font=dict(family="Rajdhani", size=10, color="#888"), bgcolor="rgba(0,0,0,0)"),
                    **DARK_LAYOUT, height=300,
                )
                st.plotly_chart(fig_rating, use_container_width=True)

        if "time" in log_df.columns and len(log_df) >= 3:
            fig_line = go.Figure(data=[go.Scatter(
                x=log_df["time"].tolist(),
                y=log_df["confidence"].tolist(),
                mode="lines+markers",
                line=dict(color="#D4AF37", width=2),
                marker=dict(color=["#00ff88" if c >= HIGH_CONF else "#FFD700" if c >= MEDIUM_CONF else "#ff6b6b" for c in log_df["confidence"]], size=8),
                text=[f'{r.get("match","?")} | {r.get("bet","?")}' for r in pred_log],
                hovertemplate="<b>%{text}</b><br>Time: %{x}<br>Confidence: %{y}%<extra></extra>",
                fill="tozeroy", fillcolor="rgba(212,175,55,.06)",
            )])
            fig_line.add_hline(y=HIGH_CONF,   line_dash="dash", line_color="#00ff88", opacity=0.5, annotation_text="HIGH")
            fig_line.add_hline(y=MEDIUM_CONF, line_dash="dash", line_color="#FFD700", opacity=0.5, annotation_text="MEDIUM")
            fig_line.update_layout(
                title=dict(text="📉 CONFIDENCE TREND", font=dict(family="Orbitron", size=13, color="#D4AF37")),
                xaxis=dict(title="Time", tickfont=dict(family="Rajdhani", color="#888")),
                yaxis=dict(title="Confidence %", range=[0, 105], tickfont=dict(family="Rajdhani", color="#888"), gridcolor="rgba(212,175,55,.1)"),
                **DARK_LAYOUT, height=280,
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # Prediction Log Table
        st.markdown('<div style="font-family:Orbitron;font-size:.85rem;color:#D4AF37;margin:16px 0 8px;">📋 RECENT PREDICTION LOG</div>', unsafe_allow_html=True)
        display_cols = [c for c in ["time","match","sport","bet","confidence","rating"] if c in log_df.columns]
        if display_cols:
            disp = log_df[display_cols].head(20).copy()
            disp.columns = [c.upper() for c in disp.columns]
            st.dataframe(disp, use_container_width=True, hide_index=True)
    else:
        st.info("No predictions yet this session. Run predictions in the PREDICTIONS tab to populate analytics.")

    # ── KELLY CRITERION CALCULATOR ─────────────────────────────────────────────
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">💰 KELLY CRITERION BET CALCULATOR</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:Rajdhani;font-size:.95rem;color:#888;margin-bottom:16px;">'
        'Enter your model probability and odds. Kelly fraction & max bet are pulled from sidebar Risk Controls.</div>',
        unsafe_allow_html=True,
    )

    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        bankroll   = st.number_input("💵 BANKROLL ($)",                  min_value=10.0, max_value=1_000_000.0, value=1000.0, step=100.0, format="%.0f")
        model_prob = st.slider("🧠 MODEL WIN PROBABILITY (%)", min_value=1, max_value=99, value=60)
    with kc2:
        dec_odds   = st.number_input("📊 DECIMAL ODDS",                  min_value=1.01, max_value=100.0, value=2.10, step=0.05, format="%.2f")
        st.selectbox("🏟️ SPORT CONTEXT", ["Football","NBA","NFL","MLB","NHL","UFC","Tennis","Cricket","Golf","F1"])
    with kc3:
        st.markdown(
            f'<div style="background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.3);border-radius:8px;padding:12px;margin-top:4px;">'
            f'<div style="font-family:Orbitron;font-size:.7rem;color:#888;">RISK SETTINGS (sidebar)</div>'
            f'<div style="font-family:Rajdhani;color:#FFD700;font-size:.9rem;margin-top:6px;">'
            f'Kelly Fraction: <strong>{st.session_state.kelly_pct}%</strong><br>'
            f'Max Bet: <strong>{st.session_state.max_bet_pct}%</strong> of bankroll<br>'
            f'Min EV: <strong>{st.session_state.min_ev}%</strong></div></div>',
            unsafe_allow_html=True,
        )

    result = kelly_bet_size(
        model_prob_pct=float(model_prob),
        decimal_odds=float(dec_odds),
        bankroll=float(bankroll),
        kelly_fraction=st.session_state.kelly_pct / 100.0,
        max_bet_pct=st.session_state.max_bet_pct / 100.0,
    )

    rr1, rr2, rr3, rr4 = st.columns(4)
    rr1.metric("BET SIZE",     f"${result['bet_size']:.2f}")
    rr2.metric("EDGE",         f"{result['edge_pct']:+.1f}%")
    rr3.metric("EV",           f"{result['ev_pct']:+.1f}%")
    rr4.metric("IMPLIED PROB", f"{result['implied_prob_pct']}%")

    is_value    = result["is_value"] and result["ev_pct"] >= st.session_state.min_ev
    css_class   = "kelly-result-good" if is_value else "kelly-result-bad"
    verdict     = "✅ PLACE BET" if is_value else "❌ PASS — NO VALUE"
    vc          = "#00ff88" if is_value else "#ff6b6b"
    edge_sign   = "+" if result["edge_pct"] >= 0 else ""

    st.markdown(
        f'<div class="{css_class}">'
        f'<div style="font-family:Orbitron;font-size:1.4rem;color:{vc};">{verdict}</div>'
        f'<div style="font-family:Rajdhani;font-size:1rem;color:#e6f1ff;margin-top:8px;">'
        f'Optimal Bet: <strong>${result["bet_size"]:.2f}</strong> of ${bankroll:,.0f} bankroll '
        f'({result["fractional_kelly_pct"]:.1f}% fractional Kelly, capped at {st.session_state.max_bet_pct}%)</div>'
        f'<div style="font-family:Rajdhani;font-size:.9rem;color:#888;margin-top:6px;">'
        f'Model Prob: {model_prob}% | Implied Prob: {result["implied_prob_pct"]}% | '
        f'Edge: {edge_sign}{result["edge_pct"]}% | EV: {result["ev_pct"]:+.1f}% | '
        f'Full Kelly: {result["full_kelly_pct"]:.1f}%</div></div>',
        unsafe_allow_html=True,
    )

    # Sensitivity analysis
    with st.expander("📈 Sensitivity Analysis"):
        probs = list(range(40, 96, 2))
        bets  = [kelly_bet_size(float(p), float(dec_odds), float(bankroll),
                                st.session_state.kelly_pct/100.0, st.session_state.max_bet_pct/100.0)["bet_size"] for p in probs]
        evs   = [kelly_bet_size(float(p), float(dec_odds), float(bankroll),
                                st.session_state.kelly_pct/100.0, st.session_state.max_bet_pct/100.0)["ev_pct"] for p in probs]
        fig_sens = go.Figure()
        fig_sens.add_trace(go.Scatter(x=probs, y=bets, name="Bet Size ($)", line=dict(color="#D4AF37", width=2), fill="tozeroy", fillcolor="rgba(212,175,55,.06)", yaxis="y1"))
        fig_sens.add_trace(go.Scatter(x=probs, y=evs,  name="EV (%)",      line=dict(color="#00ff88", width=2, dash="dash"), yaxis="y2"))
        fig_sens.add_vline(x=model_prob, line_dash="solid", line_color="#FFD700", opacity=0.7, annotation_text=f"Your pick ({model_prob}%)")
        fig_sens.update_layout(
            title=dict(text="BET SIZE & EV vs MODEL PROBABILITY", font=dict(family="Orbitron", size=12, color="#D4AF37")),
            xaxis=dict(title="Model Probability (%)", tickfont=dict(family="Rajdhani", color="#888")),
            yaxis=dict(title="Bet Size ($)", tickfont=dict(family="Rajdhani", color="#D4AF37"), gridcolor="rgba(212,175,55,.1)"),
            yaxis2=dict(title="EV (%)", tickfont=dict(family="Rajdhani", color="#00ff88"), overlaying="y", side="right"),
            legend=dict(font=dict(family="Rajdhani", color="#888"), bgcolor="rgba(0,0,0,0)"),
            **DARK_LAYOUT, height=300,
        )
        st.plotly_chart(fig_sens, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def render_main():
    render_header()
    render_ticker()
    sport, league_id, status = render_sidebar()

    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= REFRESH_INTERVAL:
        _clear_all_caches()

    tab1, tab2, tab3 = st.tabs(["⚡ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"])
    with tab1:
        render_arena(sport, league_id, status)
    with tab2:
        render_predictions(sport, league_id, status)
    with tab3:
        render_analytics()

    st.markdown(
        f'<div style="text-align:center;color:#555;font-family:Rajdhani;font-size:.8rem;margin-top:40px;padding:20px;border-top:1px solid #2a2a3e;">'
        f'EMPIRE SPORT INSTINCTS ARENA v4.1 | {datetime.now().strftime("%H:%M:%S UTC")} | '
        f'Auto-refresh in {max(0, int(REFRESH_INTERVAL - elapsed))}s</div>',
        unsafe_allow_html=True,
    )


render_main()
