"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
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
from empire_ai_engine import EmpireAIEngine, MatchPrediction, BulkScanResult, confidence_color, confidence_bar_html, probability_donut_html, HIGH_CONF, MEDIUM_CONF

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

data = st.session_state.empire_data
ai = st.session_state.empire_ai

REFRESH_INTERVAL = 30
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp{background:linear-gradient(180deg,#0a0a0f 0%,#12121a 50%,#0d0d14 100%);}
.section-header{font-family:Orbitron;font-size:1.3rem;font-weight:700;color:#FFD700;border-left:4px solid #D4AF37;padding:15px 20px;margin:20px 0 10px;}
.gold-divider{border:none;height:2px;background:linear-gradient(90deg,transparent 0%,#D4AF37 50%,transparent 100%);margin:20px 0;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SPORT CONFIG
# ══════════════════════════════════════════════════════════════════════════════
SPORT_OPTIONS = {
    "Football": {"icon": "⚽", "provider": "Football-Data.org"},
    "NBA": {"icon": "🏀", "provider": "MySportsFeeds"},
    "NFL": {"icon": "🏈", "provider": "MySportsFeeds"},
    "MLB": {"icon": "⚾", "provider": "MySportsFeeds"},
    "NHL": {"icon": "🏒", "provider": "MySportsFeeds"},
    "UFC": {"icon": "🥊", "provider": "TheSportsDB"},
    "Formula 1": {"icon": "🏎️", "provider": "TheSportsDB"},
    "Tennis": {"icon": "🎾", "provider": "TheSportsDB"},
    "Cricket": {"icon": "🏏", "provider": "TheSportsDB"},
    "Golf": {"icon": "⛳", "provider": "TheSportsDB"},
}
STATUS_OPTIONS = ["ALL", "LIVE", "UPCOMING", "FINISHED"]
SPORT_NAMES = list(SPORT_OPTIONS.keys())


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "selected_sport": SPORT_NAMES[0],
        "selected_league_id": "ALL",
        "selected_status": "UPCOMING",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def _clear_all_caches():
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    st.markdown("<h1 style='text-align:center;color:#D4AF37;'>⚡ EMPIRE SPORT INSTINCTS ARENA</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#888;'>Claude AI Prediction Engine | Real-Time Intelligence</p>", unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> tuple:
    with st.sidebar:
        st.markdown("## ⚡ COMMAND CENTER")
        
        # Sport Selection
        st.markdown("### 🏟️ SPORT")
        sport_labels = [f"{SPORT_OPTIONS[s]['icon']} {s}" for s in SPORT_NAMES]
        prev_sport = st.session_state.selected_sport
        sport_idx = SPORT_NAMES.index(prev_sport) if prev_sport in SPORT_NAMES else 0
        sport_choice = st.selectbox("Select Sport", options=sport_labels, index=sport_idx)
        chosen_sport = SPORT_NAMES[sport_labels.index(sport_choice)]
        
        if chosen_sport != prev_sport:
            st.session_state.selected_sport = chosen_sport
            st.session_state.selected_league_id = "ALL"
            st.session_state.selected_status = "UPCOMING"
            st.rerun()
        
        # League Selection (CRITICAL - Was Missing!)
        st.markdown("### 🏆 LEAGUE")
        raw_leagues = data.get_all_leagues(st.session_state.selected_sport)
        
        league_ids = ["ALL"]
        league_labels = [f"🌍 All {st.session_state.selected_sport}"]
        
        for lg in raw_leagues:
            lid = str(lg.get("id", "ALL"))
            lname = lg.get("name", "Unknown")
            lctry = lg.get("country", "")
            league_ids.append(lid)
            league_labels.append(f"{lname} ({lctry})" if lctry else lname)
        
        if st.session_state.selected_league_id not in league_ids:
            st.session_state.selected_league_id = "ALL"
        
        league_idx = league_ids.index(st.session_state.selected_league_id)
        league_choice = st.selectbox("Select League", options=league_labels, index=league_idx)
        st.session_state.selected_league_id = league_ids[league_labels.index(league_choice)]
        
        # Status Filter
        st.markdown("### 📊 STATUS")
        status_idx = STATUS_OPTIONS.index(st.session_state.selected_status) if st.session_state.selected_status in STATUS_OPTIONS else 0
        status_choice = st.selectbox("Match Status", options=STATUS_OPTIONS, index=status_idx)
        st.session_state.selected_status = status_choice
        
        # Refresh Button
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            _clear_all_caches()
            st.rerun()
        
        # Provider Status
        st.markdown("---")
        st.markdown("### 📡 API STATUS")
        for s in data.router.get_provider_status():
            st.markdown(f"- {s['name']}: {s['status']}")
    
    return (
        st.session_state.selected_sport,
        st.session_state.selected_league_id,
        st.session_state.selected_status,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════════════════════════
def _status_style(status: str):
    su = str(status).upper()
    if "LIVE" in su:
        return "#00FF88", "rgba(0,255,136,.15)", "● LIVE"
    if any(x in su for x in ("FINISH", "FT", "FINAL", "COMPLETED")):
        return "#888", "rgba(136,136,136,.15)", "FINISHED"
    return "#FFAA00", "rgba(255,170,0,.15)", "UPCOMING"


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_matches_cached(_cache_key: str, sport: str, league_id: str, status: str) -> pd.DataFrame:
    """Cached match fetch - only called when cache expires"""
    try:
        if status == "LIVE":
            df = st.session_state.empire_data.get_live_matches_df(sport, None if league_id == "ALL" else league_id)
        elif status == "UPCOMING":
            df = st.session_state.empire_data.get_upcoming_matches_df(sport)
        elif status == "FINISHED":
            df = pd.DataFrame()
        else:  # ALL
            live_df = st.session_state.empire_data.get_live_matches_df(sport, None if league_id == "ALL" else league_id)
            upcoming_df = st.session_state.empire_data.get_upcoming_matches_df(sport)
            parts = [d for d in [live_df, upcoming_df] if not d.empty]
            df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        
        # Filter by league if needed
        if league_id != "ALL" and not df.empty and "LEAGUE" in df.columns:
            mask = df["LEAGUE"].astype(str).str.contains(league_id, case=False, na=False)
            filtered = df[mask]
            if not filtered.empty:
                df = filtered
        return df
    except Exception as e:
        logger.error(f"_fetch_matches_cached: {e}")
        return pd.DataFrame()


def fetch_matches(sport: str, league_id: str, status: str) -> pd.DataFrame:
    """Fetch matches with caching"""
    cache_key = f"{sport}_{league_id}_{status}_{int(time.time() // 300)}"
    return _fetch_matches_cached(cache_key, sport, league_id, status)


# ══════════════════════════════════════════════════════════════════════════════
# RENDER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def render_match_cards(df: pd.DataFrame, sport: str):
    """Display match cards - NO HARDCODED DATA"""
    if df.empty:
        st.info(f"No {sport} matches found. Try changing the league or status filter.")
        return
    
    st.markdown(f"### 📊 {len(df)} Matches Found")
    
    for idx, row in df.iterrows():
        home = row.get("HOME_TEAM", "TBD")
        away = row.get("AWAY_TEAM", "TBD")
        score = row.get("SCORE", "vs")
        league = row.get("LEAGUE", "")
        match_time = row.get("TIME", "")
        match_id = row.get("MATCH_ID", str(idx))
        status_raw = row.get("STATUS", "UPCOMING")
        
        color, bg, label = _status_style(status_raw)
        
        # Match Card
        card_html = f'''
        <div style="background:linear-gradient(135deg,rgba(20,25,40,.9),rgba(10,15,30,.95)); border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:16px; margin:8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="color:#8892b0; font-size:.75rem;">{league}</span>
                <span style="color:{color}; background:{bg}; padding:2px 10px; border-radius:10px; font-size:.7rem; font-weight:700;">{label}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1; text-align:left;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{home}</div>
                </div>
                <div style="padding:0 20px; text-align:center;">
                    <div style="color:#00d4ff; font-size:1.4rem; font-weight:700;">{score}</div>
                    <div style="color:#8892b0; font-size:.65rem;">{match_time}</div>
                </div>
                <div style="flex:1; text-align:right;">
                    <div style="color:#e6f1ff; font-size:1rem; font-weight:600;">{away}</div>
                </div>
            </div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)
        
        col1, col2 = st.columns([7, 1])
        with col1:
            st.button(f"🧠 AI PREDICT", key=f"predict_{sport}_{match_id}_{idx}", use_container_width=True)
        with col2:
            st.button(f"🔍", key=f"view_{sport}_{match_id}_{idx}", use_container_width=True)


def render_arena(sport: str, league_id: str, status: str):
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {sport.upper()}</div>', unsafe_allow_html=True)
    
    with st.spinner(f"Fetching {sport} matches..."):
        df = fetch_matches(sport, league_id, status)
    
    render_match_cards(df, sport)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    render_header()
    selected_sport, selected_league_id, selected_status = render_sidebar()
    
    tab1, tab2, tab3 = st.tabs(["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"])
    
    with tab1:
        render_arena(selected_sport, selected_league_id, selected_status)
    with tab2:
        st.info("AI Predictions - Select a match from the ARENA tab first")
    with tab3:
        st.info("Analytics Dashboard - Coming soon")


if __name__ == "__main__":
    main()
