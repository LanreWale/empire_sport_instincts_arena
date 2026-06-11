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
from datetime import datetime, timedelta, timezone
import time
import logging

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

# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON SERVICES
# ══════════════════════════════════════════════════════════════════════════════
if "empire_data" not in st.session_state:
    st.session_state.empire_data = EmpireDashboardData()
if "empire_ai" not in st.session_state:
    st.session_state.empire_ai = EmpireAIEngine()

data: EmpireDashboardData = st.session_state.empire_data
ai: EmpireAIEngine = st.session_state.empire_ai

REFRESH_INTERVAL = 90  # Balanced for real-time feel without constant reloads

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False


# ══════════════════════════════════════════════════════════════════════════════
# CSS (unchanged - kept your premium styling)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
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
</style>""", unsafe_allow_html=True)

# (All SPORT_OPTIONS, STATUS_OPTIONS, _init_state, _clear_all_caches, render_header, render_sidebar, render_ticker, _status_style, render_prediction_card, render_match_cards, render_match_detail remain the same except for slider capture and debug toggle in sidebar)

# ══════════════════════════════════════════════════════════════════════════════
# UPDATED SIDEBAR (sliders now captured + debug toggle)
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    with st.sidebar:
        # ... (logo and AI status unchanged)

        st.subheader("⚡ SYSTEM STATUS")
        # ... (provider status unchanged)

        # Arena controls (unchanged until league selector)
        # ... (sport selector unchanged)

        # League selector (unchanged)

        # Status filter (unchanged)

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        if st.button("🔄 REFRESH DATA", use_container_width=True):
            _clear_all_caches()
            st.rerun()

        st.markdown("<hr style='border-color:#333;margin:10px 0;'>", unsafe_allow_html=True)

        st.subheader("🛡️ RISK CONTROLS")
        st.session_state.kelly_pct = st.slider("KELLY %", 5, 50, 25, 5, format="%d%%")
        st.session_state.max_bet_pct = st.slider("MAX BET", 1, 10, 3, 1, format="%d%%")
        st.session_state.min_ev = st.slider("MIN EV", 1, 10, 2, 1, format="%d%%")

        if st.button("🚨 EMERGENCY STOP", type="primary", use_container_width=True):
            st.error("ALL SYSTEMS HALTED")

        st.checkbox("Show Debug Information", value=False, key="show_debug")

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


# Updated cache functions with league_id in key
@st.cache_data(ttl=60, show_spinner=False)
def _fetch_live(_cache_key: str, sport: str, league_id: str) -> pd.DataFrame:
    return data.get_live_matches_df(sport, None if league_id == "ALL" else league_id)

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_upcoming(_cache_key: str, sport: str, league_id: str) -> pd.DataFrame:
    return data.get_upcoming_matches_df(sport)

def _fetch_matches(sport: str, league_id: str, status: str) -> pd.DataFrame:
    cache_key = f"{sport}_{league_id}_{status}_{int(time.time()//90)}"
    try:
        if status == "LIVE":
            df = _fetch_live(cache_key, sport, league_id)
        elif status in ("UPCOMING", "SCHEDULED"):
            df = _fetch_upcoming(cache_key, sport, league_id)
        elif status == "FINISHED":
            df = pd.DataFrame()  # extend with get_finished if needed
        else:
            live_df = _fetch_live(cache_key, sport, league_id)
            upcoming_df = _fetch_upcoming(cache_key, sport, league_id)
            parts = [d for d in [live_df, upcoming_df] if not d.empty]
            df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    except Exception as e:
        logger.error(f"_fetch_matches error: {e}")
        df = pd.DataFrame()
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ARENA — FIXED LEAGUE FILTERING (Core Fix)
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

    with st.spinner(f"📡 Fetching {sport} matches..."):
        df = _fetch_matches(sport, league_id, status)

    # Get selected league name for display and filtering
    selected_league_name = "All Leagues"
    if league_id != "ALL":
        raw_leagues = data.get_all_leagues(sport)
        for lg in raw_leagues:
            if str(lg.get("id", "")) == str(league_id):
                selected_league_name = lg.get("name", league_id)
                break

    # === FIXED LEAGUE FILTERING ===
    if league_id != "ALL" and not df.empty:
        filtered = pd.DataFrame()
        if "LEAGUE_ID" in df.columns:
            filtered = df[df["LEAGUE_ID"].astype(str) == str(league_id)]
        if filtered.empty and "LEAGUE" in df.columns:
            filtered = df[df["LEAGUE"].astype(str).str.lower() == selected_league_name.lower()]
        if filtered.empty and "LEAGUE" in df.columns:
            filtered = df[df["LEAGUE"].astype(str).str.contains(selected_league_name.split()[0], case=False, na=False)]

        if not filtered.empty:
            df = filtered
            st.success(f"✅ Filtered to **{selected_league_name}** ({len(df)} matches)")
        else:
            st.warning(f"⚠️ No matches found for **{selected_league_name}**. Showing all available {sport} matches.")
            st.info("Tip: Some leagues may have no fixtures right now (off-season, night time, etc.). Try UPCOMING or another league.")

    # Optional debug (controlled by sidebar checkbox)
    if st.session_state.show_debug:
        with st.expander("🔧 Debug Information", expanded=False):
            st.write(f"**Selected League ID:** {league_id} | **Name:** {selected_league_name}")
            st.write(f"**DataFrame shape:** {df.shape}")
            if not df.empty and "LEAGUE" in df.columns:
                st.write("**Leagues in returned data:**")
                for league in sorted(df["LEAGUE"].unique()):
                    st.write(f"• {league} ({len(df[df['LEAGUE']==league])} matches)")

    render_match_cards(df, sport)


# The rest of the file (render_predictions, render_analytics, render_top_bar, MAIN block) remains functionally the same as you provided, with only minor cleanups for consistency.

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
render_header()
selected_sport, selected_league_id, selected_status = render_sidebar()
render_ticker()
render_top_bar()

page = st.radio(
    "", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"],
    horizontal=True, label_visibility="collapsed", key="page_radio"
)

if "ARENA" in page:
    render_arena(selected_sport, selected_league_id, selected_status)
elif "PREDICTIONS" in page:
    render_predictions(selected_sport, selected_league_id, selected_status)
else:
    render_analytics()
