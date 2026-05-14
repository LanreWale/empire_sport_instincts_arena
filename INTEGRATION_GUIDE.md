
# EMPIRE SPORT DATA INTEGRATION GUIDE
# Real-Time Sports Feeds | Multi-Provider Architecture

## Step 1: Get API Keys (Free Tiers Available)

| Provider | Data Type | Free Tier | Paid Start | Register |
|---|---|---|---|---|
| **API-SPORTS** | Football scores, stats, fixtures | 100 req/day | $10/mo | api-football.com/pricing |
| **The Odds API** | Bookmaker odds (40+ books) | 500 req/mo | $30/mo | the-odds-api.com |
| **Sportmonks** | xG, predictions, deep stats | 180 req/hr | $29/mo | sportmonks.com/pricing |
| **The Rundown** | US sports odds (NBA/NFL/MLB) | Limited | $49/mo | therundown.io |

## Step 2: Configure Environment

Copy .env.example to .env and add your API keys.

## Step 3: Install Dependencies

pip install requests pandas python-dotenv

## Step 4: Integrate into Dashboard

In app.py, add:

from empire_data_layer import EmpireDashboardData
data = EmpireDashboardData()

Replace mock calls:
  opportunities = data.get_value_opportunities_df()
  live_matches = data.get_live_matches_df()

## Architecture

API-SPORTS + The Odds API + Sportmonks -> EMPIRE Data Router -> AI Engine

## Coverage

Football: API-SPORTS (900+ leagues), Sportmonks (2500+ leagues)
NBA/NFL/MLB/NHL: The Odds API, The Rundown
Tennis: API-SPORTS, The Odds API

## Cost

Starter (Free): $0/month — 15-min refresh
Pro: $69/month — full real-time
Enterprise: $500+/month — official data
