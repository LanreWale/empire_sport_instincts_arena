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

# ------------------------------------------------------------------------------
# INITIALIZATION
# ------------------------------------------------------------------------------
data = EmpireDashboardData()
REFRESH_INTERVAL = 15

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
elapsed = time.time() - st.session_state.last_refresh

# ------------------------------------------------------------------------------
# CSS (your original CSS – keep exactly as you had)
# ------------------------------------------------------------------------------
st.html("""
<style>
    /* YOUR ORIGINAL CSS HERE – I am not changing it, but you must paste it back */
    /* For brevity, I am using a minimal version; you must replace this block with your full CSS */
    .stApp { background: #0a0a0f; }
    .section-header { color: #FFD700; }
</style>
""")

# ------------------------------------------------------------------------------
# Helper functions (most remain unchanged – I will only modify render_arena)
# ------------------------------------------------------------------------------
def render_ai_status():
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div class="ai-status">🤖 AI ENGINE ONLINE 24/7</div>', unsafe_allow_html=True)
    now = datetime.now()
    cities = [("LONDON", now+timedelta(hours=1)), ("NEW YORK", now-timedelta(hours=5)), ("TOKYO", now+timedelta(hours=9)), ("SYDNEY", now+timedelta(hours=10)), ("LAGOS", now+timedelta(hours=1))]
    clock_text = " | ".join([f"{city}: {dt.strftime('%H:%M')}" for city, dt in cities])
    st.markdown(f'<div class="world-clock">🌍 {clock_text}</div>', unsafe_allow_html=True)

def render_header():
    # unchanged – keep your original header code
    st.markdown('<div class="tagline-bold">EMPIRE SPORT INSTINCTS ARENA</div>', unsafe_allow_html=True)
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    render_ai_status()
    try:
        if data.is_live:
            st.success("🟢 LIVE MODE — Connected")
        else:
            st.warning("⚠️ DEMO MODE — Check API keys")
    except:
        st.error("🔴 SYSTEM ERROR")

def render_sidebar():
    with st.sidebar:
        st.markdown("## COMMAND CENTER")
        st.markdown("---")
        st.subheader("⚡ SYSTEM STATUS")
        # Provider status display (unchanged)
        provider_status = data.router.get_provider_status() if hasattr(data.router, 'get_provider_status') else []
        for s in provider_status:
            st.markdown(f"{s['name']}: {s['status']}")
        st.markdown("---")
        st.subheader("📡 API CONNECTION LOG")
        log_df = data.get_connection_log_df()
        if not log_df.empty:
            st.dataframe(log_df, use_container_width=True, height=200)
        else:
            st.info("No connection attempts yet.")
        # Optional debug button
        if st.button("🐛 DEBUG NBA API"):
            try:
                import requests
                MYSPORTSFEEDS_KEY = os.getenv("MYSPORTSFEEDS_KEY", "")
                MYSPORTSFEEDS_PASSWORD = os.getenv("MYSPORTSFEEDS_PASSWORD", "")
                if MYSPORTSFEEDS_KEY and MYSPORTSFEEDS_PASSWORD:
                    import base64
                    creds = base64.b64encode(f"{MYSPORTSFEEDS_KEY}:{MYSPORTSFEEDS_PASSWORD}".encode()).decode()
                    headers = {"Authorization": f"Basic {creds}"}
                    current_year = datetime.now().year
                    season = f"{current_year-1}-{current_year}"
                    today = datetime.now().strftime("%Y%m%d")
                    url = f"https://api.mysportsfeeds.com/v2.1/pull/nba/{season}/games.json"
                    r = requests.get(url, headers=headers, params={"date": today}, timeout=10)
                    st.write(f"Status: {r.status_code}")
                    if r.status_code == 200:
                        data_raw = r.json()
                        games = data_raw.get("games", [])
                        st.success(f"Found {len(games)} NBA games today")
                        for g in games[:3]:
                            sched = g.get("schedule", {})
                            st.write(f"{sched.get('awayTeam',{}).get('name')} @ {sched.get('homeTeam',{}).get('name')} - {sched.get('status')}")
                    else:
                        st.error(f"API error: {r.text[:200]}")
                else:
                    st.error("MySportsFeeds keys not set")
            except Exception as e:
                st.error(f"Debug error: {e}")

def render_live_ticker():
    # unchanged – keep your original
    st.markdown("### Live Ticker Placeholder")

def render_match_table(matches_df, selected_view, key_prefix, selected_league_id, selected_status):
    # unchanged – keep your original
    if matches_df.empty:
        st.info("No matches available")
        return
    st.dataframe(matches_df)

def render_match_analysis_panel():
    # unchanged – keep your original
    st.info("Match analysis panel")

def render_predictions():
    st.markdown("## Predictions Center")
    st.info("Coming soon")

def render_analytics():
    st.markdown("## Performance Analytics")
    st.info("Coming soon")

# ------------------------------------------------------------------------------
# CRITICAL FIX: render_arena (no local variable named 'data')
# ------------------------------------------------------------------------------
def render_arena():
    # If a match is selected, show analysis panel
    if 'selected_match_id' in st.session_state:
        render_match_analysis_panel()
        return

    # SIDEBAR CONTROLS
    with st.sidebar:
        st.markdown("---")
        st.markdown("🏟️ **ARENA CONTROLS**")
        # Sport selector
        sport_names = list(SPORT_OPTIONS.keys())
        if 'selected_sport' not in st.session_state:
            st.session_state.selected_sport = sport_names[0]
        selected_sport = st.selectbox("🎯 SELECT SPORT", options=sport_names, index=sport_names.index(st.session_state.selected_sport), key="arena_sport")
        # Clear league cache on sport change
        if 'prev_arena_sport' not in st.session_state:
            st.session_state.prev_arena_sport = selected_sport
        elif st.session_state.prev_arena_sport != selected_sport:
            old_prefix = st.session_state.prev_arena_sport.replace(" ", "_")
            st.session_state.pop(f'league_opts_{old_prefix}', None)
            st.session_state.prev_arena_sport = selected_sport
        st.session_state.selected_sport = selected_sport

        sport_key = SPORT_OPTIONS[selected_sport]
        key_prefix = selected_sport.replace(" ", "_")

        # League dropdown – ensure at least "All Leagues"
        cache_key = f'league_opts_{key_prefix}'
        if cache_key not in st.session_state:
            st.session_state[cache_key] = [("ALL", "🏆 All Leagues")]
        league_options = st.session_state[cache_key]

        try:
            api_leagues = data.get_all_leagues(selected_sport)  # passes string, e.g., "NBA"
            if api_leagues:
                new_opts = [("ALL", "🏆 All Leagues")]
                for l in api_leagues:
                    lid = l.get('id') if isinstance(l, dict) else getattr(l, 'league_id', '')
                    lname = l.get('name') if isinstance(l, dict) else getattr(l, 'name', 'Unknown')
                    country = l.get('country') if isinstance(l, dict) else getattr(l, 'country', '')
                    display = f"{lname}" + (f" ({country})" if country else "")
                    if lid:
                        new_opts.append((str(lid), display))
                if len(new_opts) > 1:
                    league_options = new_opts
                    st.session_state[cache_key] = league_options
        except Exception as e:
            logger.error(f"League fetch error: {e}")

        league_labels = [opt[1] for opt in league_options]
        league_ids = [opt[0] for opt in league_options]
        current_id = st.session_state.get(f'league_id_{key_prefix}', "ALL")
        try:
            idx = league_ids.index(current_id)
        except ValueError:
            idx = 0
        selected_label = st.selectbox("🏆 SELECT LEAGUE", options=league_labels, index=idx, key=f"arena_league_{key_prefix}")
        selected_league_id = league_ids[league_labels.index(selected_label)]
        st.session_state[f'league_id_{key_prefix}'] = selected_league_id

        status_options = ["ALL", "LIVE", "UPCOMING", "SCHEDULED", "FINISHED"]
        selected_status = st.selectbox("📊 MATCH STATUS", options=status_options, key=f"arena_status_{key_prefix}")

        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()

    # MAIN AREA
    st.markdown(f'<div class="section-header">🏟️ EMPIRE ARENA — {selected_sport.upper()}</div>', unsafe_allow_html=True)

    # FETCH MATCHES – no variable named 'data' here
    try:
        if selected_status == "LIVE":
            matches_df = data.get_live_matches_df(sport_key, selected_league_id)
        elif selected_status in ("UPCOMING", "SCHEDULED"):
            matches_df = data.get_upcoming_matches_df(sport_key)
            # Apply league filter if needed
            if selected_league_id != "ALL" and not matches_df.empty and "LEAGUE" in matches_df.columns:
                league_name = next((label.replace("🏆 ", "").split(" (")[0] for lid, label in league_options if lid == selected_league_id), None)
                if league_name:
                    matches_df = matches_df[matches_df["LEAGUE"].str.contains(league_name, case=False, na=False)]
        elif selected_status == "FINISHED":
            matches_df = data.router.get_matches_by_status("FINISHED", sport_key, selected_league_id) if hasattr(data.router, 'get_matches_by_status') else pd.DataFrame()
        else:  # ALL
            live_df = data.get_live_matches_df(sport_key)
            sched_df = data.get_upcoming_matches_df(sport_key)
            if selected_league_id != "ALL":
                league_name = next((label.replace("🏆 ", "").split(" (")[0] for lid, label in league_options if lid == selected_league_id), None)
                if league_name:
                    if not live_df.empty and "LEAGUE" in live_df.columns:
                        live_df = live_df[live_df["LEAGUE"].str.contains(league_name, case=False, na=False)]
                    if not sched_df.empty and "LEAGUE" in sched_df.columns:
                        sched_df = sched_df[sched_df["LEAGUE"].str.contains(league_name, case=False, na=False)]
            matches_df = pd.concat([live_df, sched_df], ignore_index=True) if not live_df.empty else sched_df
    except Exception as e:
        st.error(f"Error fetching matches: {str(e)}")
        matches_df = pd.DataFrame()

    render_match_table(matches_df, "CARD VIEW", key_prefix, selected_league_id, selected_status)

# ------------------------------------------------------------------------------
# SPORT CONFIGURATION (unchanged – but ensure years are dynamic)
# ------------------------------------------------------------------------------
CURRENT_YEAR = datetime.now().year
NEXT_YEAR = CURRENT_YEAR + 1

SPORT_OPTIONS = {
    "Soccer": {"sport_type": "Soccer", "icon": "⚽", "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"},
    "NBA": {"sport_type": "Basketball", "icon": "🏀", "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"},
    "NFL": {"sport_type": "American Football", "icon": "🏈", "season": str(CURRENT_YEAR)},
    "MLB": {"sport_type": "Baseball", "icon": "⚾", "season": str(CURRENT_YEAR)},
    "NHL": {"sport_type": "Ice Hockey", "icon": "🏒", "season": f"{CURRENT_YEAR}-{NEXT_YEAR}"},
    "UFC": {"sport_type": "MMA", "icon": "🥊", "season": str(CURRENT_YEAR)},
    "Formula 1": {"sport_type": "Motorsport", "icon": "🏎️", "season": str(CURRENT_YEAR)},
    "Tennis": {"sport_type": "Tennis", "icon": "🎾", "season": str(CURRENT_YEAR)},
    "Cricket": {"sport_type": "Cricket", "icon": "🏏", "season": str(CURRENT_YEAR)},
    "Golf": {"sport_type": "Golf", "icon": "⛳", "season": str(CURRENT_YEAR)},
}

# ------------------------------------------------------------------------------
# MAIN ROUTER
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    render_header()
    render_sidebar()
    render_live_ticker()

    col_ref, col_st = st.columns([1,4])
    with col_ref:
        if st.button("🔄 FORCE REFRESH"):
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()
    with col_st:
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
