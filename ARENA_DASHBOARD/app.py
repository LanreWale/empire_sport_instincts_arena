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
    page_icon="BRAND_ASSET/empire_logo_primary.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize data layer
data = EmpireDashboardData()

REFRESH_INTERVAL = 15

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
elapsed = time.time() - st.session_state.last_refresh

# CSS (keep your existing CSS here - not changing)
st.html("""
<style>
    /* YOUR EXISTING CSS HERE - keep as is */
    .stApp { background: #0a0a0f; }
    .section-header { color: #FFD700; }
</style>
""")


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


def render_header():
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline-sub">Advanced Research & Evaluation System | Where Data Meets Instinct</div>', unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    render_ai_status()
    if data.is_live:
        st.success("🟢 LIVE MODE — Connected")
    else:
        st.warning("⚠️ DEMO MODE — Check API keys")


def render_sidebar():
    with st.sidebar:
        st.markdown("## COMMAND CENTER")
        st.markdown("---")
        st.subheader("⚡ SYSTEM STATUS")
        
        provider_status = data.router.get_provider_status() if data.router else []
        for s in provider_status:
            st.markdown(f"{s['name']}: {s['status']}")
        
        st.markdown("---")
        st.subheader("📡 API CONNECTION LOG")
        log_df = data.get_connection_log_df()
        if not log_df.empty:
            st.dataframe(log_df, use_container_width=True, height=200)
        else:
            st.info("No connection attempts yet.")


def render_live_ticker():
    st.markdown("### Live Ticker")


def render_match_table(matches_df, key_prefix, selected_league_id, selected_status):
    if matches_df.empty:
        st.info("No matches available for the selected criteria.")
        return
    st.dataframe(matches_df, use_container_width=True)


def render_match_analysis_panel():
    st.info("Select a match to view analysis")


def render_predictions():
    st.markdown("## Predictions Center")
    st.info("Coming soon")


def render_analytics():
    st.markdown("## Performance Analytics")
    st.info("Coming soon")


def render_arena():
    if 'selected_match_id' in st.session_state:
        render_match_analysis_panel()
        return

    with st.sidebar:
        st.markdown("---")
        st.markdown("🏟️ **ARENA CONTROLS**")
        
        sport_names = ["Soccer", "NBA", "NFL", "MLB", "NHL", "UFC", "Formula 1", "Tennis", "Cricket", "Golf"]
        if 'selected_sport' not in st.session_state:
            st.session_state.selected_sport = sport_names[0]
        
        selected_sport = st.selectbox("🎯 SELECT SPORT", options=sport_names, index=sport_names.index(st.session_state.selected_sport))
        st.session_state.selected_sport = selected_sport
        
        st.markdown("---")
        
        # League dropdown - loads from API
        cache_key = f"leagues_{selected_sport}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = [("ALL", "🏆 All Leagues")]
        
        try:
            api_leagues = data.get_all_leagues(selected_sport)
            if api_leagues:
                league_options = [("ALL", "🏆 All Leagues")]
                for league in api_leagues:
                    display = f"{league.get('name', 'Unknown')}"
                    if league.get('country'):
                        display += f" ({league.get('country')})"
                    league_options.append((league.get('id', ''), display))
                st.session_state[cache_key] = league_options
        except Exception as e:
            logger.error(f"League fetch error: {e}")
        
        league_options = st.session_state[cache_key]
        league_labels = [opt[1] for opt in league_options]
        league_ids = [opt[0] for opt in league_options]
        
        selected_label = st.selectbox("🏆 SELECT LEAGUE", options=league_labels)
        selected_league_id = league_ids[league_labels.index(selected_label)]
        
        # Status filter
        status_options = ["LIVE", "UPCOMING", "SCHEDULED", "FINISHED", "ALL"]
        selected_status = st.selectbox("📊 MATCH STATUS", options=status_options, index=0)
        
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()
    
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {selected_sport.upper()}</div>', unsafe_allow_html=True)
    
    # Fetch matches based on filters
    try:
        if selected_status == "LIVE":
            matches_df = data.get_live_matches_df(selected_sport, selected_league_id if selected_league_id != "ALL" else None)
        elif selected_status in ["UPCOMING", "SCHEDULED"]:
            matches_df = data.get_upcoming_matches_df(selected_sport)
        else:
            live_df = data.get_live_matches_df(selected_sport, selected_league_id if selected_league_id != "ALL" else None)
            upcoming_df = data.get_upcoming_matches_df(selected_sport)
            matches_df = pd.concat([live_df, upcoming_df], ignore_index=True) if not live_df.empty else upcoming_df
    except Exception as e:
        st.error(f"Error fetching matches: {str(e)}")
        matches_df = pd.DataFrame()
    
    render_match_table(matches_df, selected_sport, selected_league_id, selected_status)


# Main navigation
if __name__ == "__main__":
    render_header()
    render_sidebar()
    render_live_ticker()
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 FORCE REFRESH"):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()
    with col2:
        nxt = max(0, REFRESH_INTERVAL - elapsed)
        st.markdown(f'<div style="color:#00ff88;">● {"LIVE" if data.is_live else "DEMO"} | Next refresh in {int(nxt)}s</div>', unsafe_allow_html=True)
    
    if elapsed >= REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        st.cache_data.clear()
        st.rerun()
    
    page = st.radio("", ["🏟️ ARENA", "🎯 PREDICTIONS", "📊 ANALYTICS"], horizontal=True, label_visibility="collapsed")
    
    if "ARENA" in page:
        render_arena()
    elif "PREDICTIONS" in page:
        render_predictions()
    else:
        render_analytics()
