"""
EMPIRE SPORT INSTINCTS ARENA — ARENA DASHBOARD
Streamlit web interface | Live data | Value detection
"""

import streamlit as st
import pandas as pd
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Allow imports from repo root regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from empire_data_layer import EmpireDashboardData, APIConfig

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "EMPIRE Sport Instincts Arena",
    page_icon   = "⚔️",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main .block-container { padding-top: 1rem; }
  .empire-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #d4a843;
  }
  .empire-title {
    color: #d4a843;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin: 0;
  }
  .empire-subtitle {
    color: #a0a8b8;
    font-size: 0.9rem;
    margin: 0.25rem 0 0;
  }
  .demo-banner {
    background: #2d1f00;
    border: 1px solid #d4a843;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    color: #d4a843;
    font-size: 0.9rem;
  }
  .live-banner {
    background: #0a2d0a;
    border: 1px solid #2ea82e;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    color: #2ea82e;
    font-size: 0.9rem;
  }
  .metric-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
  }
  .signal-buy  { color: #2ea82e; font-weight: 600; }
  .signal-hold { color: #888;    font-weight: 400; }
</style>
""", unsafe_allow_html=True)


# ── Initialise data layer (cached across Streamlit re-runs) ──────────────────
@st.cache_resource(show_spinner="Connecting to sports data feeds…")
def get_data_layer() -> EmpireDashboardData:
    return EmpireDashboardData()


def main():
    data = get_data_layer()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="empire-header">
      <p class="empire-title">⚔️ EMPIRE SPORT INSTINCTS ARENA</p>
      <p class="empire-subtitle">AI-Powered Sports Analytics &amp; Prediction Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Live / Demo Mode banner ───────────────────────────────────────────────
    if data.is_live:
        provider_name = data.router.active_provider.name if data.router.active_provider else "Unknown"
        st.markdown(f"""
        <div class="live-banner">
          🟢 <strong>LIVE MODE</strong> — Real data streaming via {provider_name}.
          Dashboard auto-refreshes every 30 seconds.
        </div>
        """, unsafe_allow_html=True)
    else:
        missing = data.missing_keys
        st.markdown(f"""
        <div class="demo-banner">
          🟡 <strong>DEMO MODE</strong> — Displaying sample data.
          To enable live feeds, add your API keys as environment variables on Render.<br>
          <small>Missing: {', '.join(missing) if missing else 'All keys set but no live matches found right now.'}</small>
        </div>
        """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image("BRAND_ASSET/empire_logo_primary.png", use_column_width=True)
        st.markdown("---")

        st.subheader("⚙️ Settings")
        auto_refresh     = st.toggle("Auto-refresh (30s)", value=True)
        min_ev_filter    = st.slider("Min EV % filter", 0, 20, 2)
        show_diagnostics = st.toggle("Show API diagnostics", value=False)

        st.markdown("---")
        st.subheader("🏟️ Sport filter")
        sport = st.selectbox("Sport", ["Football", "NBA", "NFL", "Tennis", "All"])

        st.markdown("---")
        st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh now"):
            st.cache_resource.clear()
            st.rerun()

    # ── API diagnostics (collapsible) ─────────────────────────────────────────
    if show_diagnostics:
        with st.expander("📡 API Connection Log", expanded=True):
            for entry in data.connection_log:
                icon = "🟢" if entry["status"] == "SUCCESS" else ("🟡" if entry["status"] == "EMPTY" else ("⚪" if entry["status"] == "SKIP" else "🔴"))
                st.markdown(f"{icon} **{entry['provider']}** — `{entry['status']}` — {entry['detail']}")

            missing = data.missing_keys
            if missing:
                st.warning(f"⚠️ Missing API keys: {', '.join(missing)}")
                st.info("Add these as Environment Variables in your Render service dashboard.")

    # ── KPI strip ─────────────────────────────────────────────────────────────
    live_df  = data.get_live_matches_df()
    value_df = data.get_value_opportunities_df()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Live Matches",        len(live_df))
    with col2:
        live_count = len(live_df[live_df["STATUS"].str.contains("LIVE", na=False)]) if not live_df.empty else 0
        st.metric("In-Play Now",         live_count)
    with col3:
        buy_count  = len(value_df[value_df["SIGNAL"].str.contains("BUY",  na=False)]) if not value_df.empty else 0
        st.metric("🟢 BUY Signals",      buy_count)
    with col4:
        st.metric("Data Mode", "🟢 LIVE" if data.is_live else "🟡 DEMO")

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📺 Live Matches", "💰 Value Opportunities", "📊 System Status"])

    with tab1:
        st.subheader("Live & Upcoming Matches")
        if not live_df.empty:
            # Highlight live rows
            def highlight_live(row):
                if "LIVE" in str(row.get("STATUS", "")):
                    return ["background-color: #0a1a0a"] * len(row)
                return [""] * len(row)
            st.dataframe(
                live_df.style.apply(highlight_live, axis=1),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No matches available. Check your API keys or try again during a live fixture window.")

    with tab2:
        st.subheader("Value Betting Opportunities")
        st.caption(f"Showing opportunities with EV > {min_ev_filter}%")

        if not value_df.empty:
            # Apply EV filter
            def ev_to_float(ev_str):
                try:
                    return float(str(ev_str).replace("%", "").replace("+", ""))
                except ValueError:
                    return 0.0

            filtered = value_df.copy()
            filtered["_ev_num"] = filtered["EV"].apply(ev_to_float)
            filtered = filtered[filtered["_ev_num"] >= min_ev_filter].drop(columns=["_ev_num"])

            if filtered.empty:
                st.info(f"No opportunities above {min_ev_filter}% EV right now.")
            else:
                def colour_signal(val):
                    if "BUY"  in str(val): return "color: #2ea82e; font-weight: 600"
                    if "HOLD" in str(val): return "color: #888"
                    return ""

                st.dataframe(
                    filtered.style.applymap(colour_signal, subset=["SIGNAL"]),
                    use_container_width=True,
                    hide_index=True,
                )

                # Summary stats
                c1, c2, c3 = st.columns(3)
                with c1:
                    buy_rows = filtered[filtered["SIGNAL"].str.contains("BUY", na=False)]
                    st.metric("BUY signals", len(buy_rows))
                with c2:
                    st.metric("Opportunities shown", len(filtered))
                with c3:
                    high_conf = filtered[filtered["CONF"] == "HIGH"]
                    st.metric("High confidence", len(high_conf))
        else:
            st.info("No value opportunities found at the current EV threshold.")

    with tab3:
        st.subheader("System Status")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Provider health**")
            for entry in data.connection_log:
                icon = {"SUCCESS": "🟢", "EMPTY": "🟡", "SKIP": "⚪", "FAIL": "🔴"}.get(entry["status"], "⚫")
                st.markdown(f"{icon} `{entry['provider']}` — {entry['detail']}")

        with col_b:
            st.markdown("**Configuration**")
            missing = data.missing_keys
            all_keys = [
                "API_SPORTS_KEY", "ODDS_API_KEY", "SPORTMONKS_KEY",
                "RUNDOWN_KEY", "MYSPORTSFEEDS_KEY", "FOOTBALL_DATA_KEY", "TheSportDB_API_key",
            ]
            for k in all_keys:
                icon = "🔴" if k in missing else "🟢"
                st.markdown(f"{icon} `{k}`")
"""
EMPIRE SPORT INSTINCTS ARENA — ARENA DASHBOARD
Streamlit web interface | Live data | Value detection
"""

import streamlit as st
import pandas as pd
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Allow imports from repo root regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from empire_data_layer import EmpireDashboardData, APIConfig

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "EMPIRE Sport Instincts Arena",
    page_icon   = "⚔️",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main .block-container { padding-top: 1rem; }
  .empire-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #d4a843;
  }
  .empire-title {
    color: #d4a843;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin: 0;
  }
  .empire-subtitle {
    color: #a0a8b8;
    font-size: 0.9rem;
    margin: 0.25rem 0 0;
  }
  .demo-banner {
    background: #2d1f00;
    border: 1px solid #d4a843;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    color: #d4a843;
    font-size: 0.9rem;
  }
  .live-banner {
    background: #0a2d0a;
    border: 1px solid #2ea82e;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    color: #2ea82e;
    font-size: 0.9rem;
  }
  .metric-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
  }
  .signal-buy  { color: #2ea82e; font-weight: 600; }
  .signal-hold { color: #888;    font-weight: 400; }
</style>
""", unsafe_allow_html=True)


# ── Initialise data layer (cached across Streamlit re-runs) ──────────────────
@st.cache_resource(show_spinner="Connecting to sports data feeds…")
def get_data_layer() -> EmpireDashboardData:
    return EmpireDashboardData()


def main():
    data = get_data_layer()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="empire-header">
      <p class="empire-title">⚔️ EMPIRE SPORT INSTINCTS ARENA</p>
      <p class="empire-subtitle">AI-Powered Sports Analytics &amp; Prediction Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Live / Demo Mode banner ───────────────────────────────────────────────
    if data.is_live:
        provider_name = data.router.active_provider.name if data.router.active_provider else "Unknown"
        st.markdown(f"""
        <div class="live-banner">
          🟢 <strong>LIVE MODE</strong> — Real data streaming via {provider_name}.
          Dashboard auto-refreshes every 30 seconds.
        </div>
        """, unsafe_allow_html=True)
    else:
        missing = data.missing_keys
        st.markdown(f"""
        <div class="demo-banner">
          🟡 <strong>DEMO MODE</strong> — Displaying sample data.
          To enable live feeds, add your API keys as environment variables on Render.<br>
          <small>Missing: {', '.join(missing) if missing else 'All keys set but no live matches found right now.'}</small>
        </div>
        """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image("BRAND_ASSET/empire_logo_primary.png", use_column_width=True)
        st.markdown("---")

        st.subheader("⚙️ Settings")
        auto_refresh     = st.toggle("Auto-refresh (30s)", value=True)
        min_ev_filter    = st.slider("Min EV % filter", 0, 20, 2)
        show_diagnostics = st.toggle("Show API diagnostics", value=False)

        st.markdown("---")
        st.subheader("🏟️ Sport filter")
        sport = st.selectbox("Sport", ["Football", "NBA", "NFL", "Tennis", "All"])

        st.markdown("---")
        st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh now"):
            st.cache_resource.clear()
            st.rerun()

    # ── API diagnostics (collapsible) ─────────────────────────────────────────
    if show_diagnostics:
        with st.expander("📡 API Connection Log", expanded=True):
            for entry in data.connection_log:
                icon = "🟢" if entry["status"] == "SUCCESS" else ("🟡" if entry["status"] == "EMPTY" else ("⚪" if entry["status"] == "SKIP" else "🔴"))
                st.markdown(f"{icon} **{entry['provider']}** — `{entry['status']}` — {entry['detail']}")

            missing = data.missing_keys
            if missing:
                st.warning(f"⚠️ Missing API keys: {', '.join(missing)}")
                st.info("Add these as Environment Variables in your Render service dashboard.")

    # ── KPI strip ─────────────────────────────────────────────────────────────
    live_df  = data.get_live_matches_df()
    value_df = data.get_value_opportunities_df()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Live Matches",        len(live_df))
    with col2:
        live_count = len(live_df[live_df["STATUS"].str.contains("LIVE", na=False)]) if not live_df.empty else 0
        st.metric("In-Play Now",         live_count)
    with col3:
        buy_count  = len(value_df[value_df["SIGNAL"].str.contains("BUY",  na=False)]) if not value_df.empty else 0
        st.metric("🟢 BUY Signals",      buy_count)
    with col4:
        st.metric("Data Mode", "🟢 LIVE" if data.is_live else "🟡 DEMO")

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📺 Live Matches", "💰 Value Opportunities", "📊 System Status"])

    with tab1:
        st.subheader("Live & Upcoming Matches")
        if not live_df.empty:
            # Highlight live rows
            def highlight_live(row):
                if "LIVE" in str(row.get("STATUS", "")):
                    return ["background-color: #0a1a0a"] * len(row)
                return [""] * len(row)
            st.dataframe(
                live_df.style.apply(highlight_live, axis=1),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No matches available. Check your API keys or try again during a live fixture window.")

    with tab2:
        st.subheader("Value Betting Opportunities")
        st.caption(f"Showing opportunities with EV > {min_ev_filter}%")

        if not value_df.empty:
            # Apply EV filter
            def ev_to_float(ev_str):
                try:
                    return float(str(ev_str).replace("%", "").replace("+", ""))
                except ValueError:
                    return 0.0

            filtered = value_df.copy()
            filtered["_ev_num"] = filtered["EV"].apply(ev_to_float)
            filtered = filtered[filtered["_ev_num"] >= min_ev_filter].drop(columns=["_ev_num"])

            if filtered.empty:
                st.info(f"No opportunities above {min_ev_filter}% EV right now.")
            else:
                def colour_signal(val):
                    if "BUY"  in str(val): return "color: #2ea82e; font-weight: 600"
                    if "HOLD" in str(val): return "color: #888"
                    return ""

                st.dataframe(
                    filtered.style.applymap(colour_signal, subset=["SIGNAL"]),
                    use_container_width=True,
                    hide_index=True,
                )

                # Summary stats
                c1, c2, c3 = st.columns(3)
                with c1:
                    buy_rows = filtered[filtered["SIGNAL"].str.contains("BUY", na=False)]
                    st.metric("BUY signals", len(buy_rows))
                with c2:
                    st.metric("Opportunities shown", len(filtered))
                with c3:
                    high_conf = filtered[filtered["CONF"] == "HIGH"]
                    st.metric("High confidence", len(high_conf))
        else:
            st.info("No value opportunities found at the current EV threshold.")

    with tab3:
        st.subheader("System Status")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Provider health**")
            for entry in data.connection_log:
                icon = {"SUCCESS": "🟢", "EMPTY": "🟡", "SKIP": "⚪", "FAIL": "🔴"}.get(entry["status"], "⚫")
                st.markdown(f"{icon} `{entry['provider']}` — {entry['detail']}")

        with col_b:
            st.markdown("**Configuration**")
            missing = data.missing_keys
            all_keys = [
                "API_SPORTS_KEY", "ODDS_API_KEY", "SPORTMONKS_KEY",
                "RUNDOWN_KEY", "MYSPORTSFEEDS_KEY", "FOOTBALL_DATA_KEY", "TheSportDB_API_key",
            ]
            for k in all_keys:
                icon = "🔴" if k in missing else "🟢"
                st.markdown(f"{icon} `{k}`")

        st.markdown("---")
        st.markdown("**Risk management rules**")
        rules = [
            "Quarter Kelly sizing — never risk more than 25% of full Kelly",
            "Max 3% of bankroll per position, regardless of edge",
            "Max 40% exposure to any single sport",
            "Pause at 20% drawdown — 7-day cooldown",
            "Maximum 10 bets per day",
        ]
        for r in rules:
            st.markdown(f"• {r}")

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    if auto_refresh and data.is_live:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()

        st.markdown("---")
        st.markdown("**Risk management rules**")
        rules = [
            "Quarter Kelly sizing — never risk more than 25% of full Kelly",
            "Max 3% of bankroll per position, regardless of edge",
            "Max 40% exposure to any single sport",
            "Pause at 20% drawdown — 7-day cooldown",
            "Maximum 10 bets per day",
        ]
        for r in rules:
            st.markdown(f"• {r}")

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    if auto_refresh and data.is_live:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
            
