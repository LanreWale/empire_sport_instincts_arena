def render_predictions():
    st.markdown('<div class="section-header">🎯 EMPIRE AI PREDICTION CENTER</div>', unsafe_allow_html=True)

    if not data.router.ai.available:
        st.warning("⚠️ ANTHROPIC_API_KEY not set — AI predictions disabled. Add key in Render environment.")
        return

    sport = st.session_state.selected_sport
    df = data.get_upcoming_matches_df(sport)   # or live

    if df.empty:
        st.info("No upcoming matches to predict.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🚀 RUN AI BATCH SCAN", use_container_width=True):
            result = data.router.ai.scan_matches(df, sport)
            if result:
                st.success(f"Scanned {result.total_matches} matches")
                # Display top_picks and value_bets

    # Single match prediction example
    for idx, row in df.head(5).iterrows():
        pred = data.router.ai.predict_match(row.to_dict(), sport)
        # Render confidence bar + probability donut + key_factors + betting_angle
