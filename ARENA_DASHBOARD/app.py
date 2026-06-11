"""
ARENA DASHBOARD — EMPIRE SPORT INSTINCTS ARENA
Minimal Working Version - Debug Mode
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Configure logging to see errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="EMPIRE COMMAND CENTER",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY ANY ERRORS AT THE TOP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🔧 Empire Arena - Debug Mode")
st.markdown("---")

try:
    from empire_data_layer import EmpireDashboardData, APIConfig
    st.success("✅ empire_data_layer imported successfully")
    
    # Initialize data
    if "empire_data" not in st.session_state:
        st.session_state.empire_data = EmpireDashboardData()
    data = st.session_state.empire_data
    st.success("✅ EmpireDashboardData initialized")
    
except Exception as e:
    st.error(f"❌ Failed to import empire_data_layer: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

try:
    from empire_ai_engine import EmpireAIEngine
    if "empire_ai" not in st.session_state:
        st.session_state.empire_ai = EmpireAIEngine()
    ai = st.session_state.empire_ai
    st.success("✅ empire_ai_engine imported successfully")
except Exception as e:
    st.warning(f"⚠️ AI Engine not available: {str(e)}")
    ai = None

# ══════════════════════════════════════════════════════════════════════════════
# SIMPLE SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚡ EMPIRE COMMAND CENTER")
    st.markdown("---")
    
    # Show API key status
    api_key = os.environ.get("APIFY_API_KEY")
    if api_key:
        st.success(f"✅ APIFY_API_KEY is set (length: {len(api_key)})")
    else:
        st.error("❌ APIFY_API_KEY NOT set in environment")
    
    api_sports_key = os.environ.get("API_SPORTS_KEY")
    if api_sports_key:
        st.success(f"✅ API_SPORTS_KEY is set (length: {len(api_sports_key)})")
    else:
        st.warning("⚠️ API_SPORTS_KEY not set")
    
    st.markdown("---")
    
    # Simple sport selector
    sport_options = ["Football", "NBA", "NFL", "MLB", "NHL", "UFC", "Formula 1", "Tennis", "Cricket", "Golf"]
    selected_sport = st.selectbox("SELECT SPORT", sport_options, index=0)
    
    status_options = ["UPCOMING", "LIVE", "FINISHED", "ALL"]
    selected_status = st.selectbox("MATCH STATUS", status_options, index=0)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"## 🏟️ EMPIRE ARENA — {selected_sport.upper()}")
st.markdown("---")

try:
    # Try to fetch matches
    if selected_status == "UPCOMING":
        df = data.get_upcoming_matches_df(selected_sport)
    elif selected_status == "LIVE":
        df = data.get_live_matches_df(selected_sport)
    else:
        df = data.get_upcoming_matches_df(selected_sport)
    
    if df is not None and not df.empty:
        st.success(f"✅ Found {len(df)} matches for {selected_sport}")
        st.dataframe(df[["HOME_TEAM", "AWAY_TEAM", "LEAGUE", "TIME", "STATUS"]].head(10))
    else:
        st.warning(f"No matches found for {selected_sport}")
        
        # Show available leagues for debugging
        st.markdown("### 🔍 Available Leagues in System")
        leagues = data.get_all_leagues(selected_sport)
        if leagues:
            league_names = [lg.get("name", "Unknown") for lg in leagues[:20]]
            st.write(", ".join(league_names))
        
except Exception as e:
    st.error(f"Error fetching matches: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

# Show connection log
st.markdown("---")
st.markdown("### 📡 Connection Log")
try:
    log_df = data.get_connection_log_df()
    if log_df is not None and not log_df.empty:
        st.dataframe(log_df.tail(10))
    else:
        st.caption("No log entries yet.")
except Exception as e:
    st.warning(f"Could not load log: {e}")
