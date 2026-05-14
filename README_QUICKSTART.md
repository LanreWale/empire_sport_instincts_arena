# EMPIRE SPORT INSTINCTS ARENA v2.0
## Quick Deploy Guide

### Files to Replace
1. `empire_data_layer.py` -> `empire_data_layer_v2.py`
2. `app.py` -> `app_v2.py`

### Your .env is Already Configured!
Your existing `.env` file has these keys:
- TheSportDB_API_key=123 (recognized by v2.0)
- FOOTBALL_DATA_KEY=08af6b1da466... 
- API_SPORTS_KEY=32ad809f5bc8...
- ODDS_API_KEY=142174d4b72d...
- SPORTMONKS_KEY=QdJbPnno5P0...
- MYSPORTSFEEDS_KEY=84517b6c...

### Launch
```powershell
cd [Your EMPIRE folder path]
streamlit run app_v2.py
```

### What You Will See
- **Live matches** from OpenLigaDB (always works, no key)
- **Additional matches** from Football-Data.org & TheSportsDB (if keys valid)
- **Demo fallback** only if ALL APIs fail (clearly labeled)
- **Enhanced cards** with league, venue, referee, odds, stats, H2H

### API Key Status (Expected)
| Provider | Your Key | Expected Status |
|----------|----------|-----------------|
| OpenLigaDB | None needed | Always works |
| Football-Data | Set | Should work |
| TheSportsDB | Set | Should work |
| API-SPORTS | Set | Check RapidAPI quota |
| The Odds API | Set | Check subscription |
| Sportmonks | Set | Check plan tier |
