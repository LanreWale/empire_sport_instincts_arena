"""
# ══════════════════════════════════════════════════════════════════════════════
#  EMPIRE SPORT INSTINCTS ARENA — INSTINCT SCOUT Module
#  Dark Gold Premium Edition v2.0 | Production Ready
# ══════════════════════════════════════════════════════════════════════════════
#
#  Brand Identity:
#    Primary Logo: Crowned Shield Monogram (Gold "E" on Black)
#    Secondary: Stadium Arena Wordmark (Metallic Gold + Silver)
#    Asset Path: BRAND_ASSET/empire_logo_primary.png
#               BRAND_ASSET/empire_logo_arena.png
#
#  Module: odds_collector
#  Purpose: Odds Data Collector
# ══════════════════════════════════════════════════════════════════════════════
"""
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os

# ──────────────────────────────────────────────────────────────────────────────
# ⚜  IMPORTS & DEPENDENCIES
# ──────────────────────────────────────────────────────────────────────────────


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLASS: OddsCollector
# ──────────────────────────────────────────────────────────────────────────────

class OddsCollector:
    """Collects odds from multiple bookmakers via APIs"""

    def __init__(self):
        self.the_odds_api_key = os.getenv('THE_ODDS_API_KEY', '')
        self.sharp_api_key = os.getenv('SHARP_API_KEY', '')
        self.the_odds_base = "https://api.the-odds-api.com/v4"
        self.sharp_base = "https://api.sharpapi.io"

    def get_the_odds_sports(self) -> List[Dict]:
        """Fetch available sports from The Odds API"""
        if not self.the_odds_api_key:
            logger.warning("THE_ODDS_API_KEY not set")
            return []

        url = f"{self.the_odds_base}/sports"
        params = {"apiKey": self.the_odds_api_key}
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching sports: {e}")
            return []

    def get_the_odds_events(self, sport: str, region: str = "us", market: str = "h2h") -> pd.DataFrame:
        """Fetch odds for a specific sport"""
        if not self.the_odds_api_key:
            return pd.DataFrame()

        url = f"{self.the_odds_base}/sports/{sport}/odds"
        params = {
            "apiKey": self.the_odds_api_key,
            "regions": region,
            "markets": market,
            "oddsFormat": "decimal"
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Flatten odds data
            odds_list = []
            for event in data:
                for bookmaker in event.get('bookmakers', []):
                    for market_data in bookmaker.get('markets', []):
                        for outcome in market_data.get('outcomes', []):
                            odds_list.append({
                                'event_id': event['id'],
                                'sport': sport,
                                'home_team': event.get('home_team'),
                                'away_team': event.get('away_team'),
                                'commence_time': event.get('commence_time'),
                                'bookmaker': bookmaker['title'],
                                'market': market_data['key'],
                                'outcome': outcome['name'],
                                'odds': outcome['price'],
                                'point': outcome.get('point'),
                                'last_update': bookmaker.get('last_update')
                            })

            df = pd.DataFrame(odds_list)
            logger.info(f"Loaded {len(df)} odds entries for {sport}")
            return df
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return pd.DataFrame()

    def get_sharp_api_odds(self, sport: str = "soccer") -> pd.DataFrame:
        """Fetch odds from SharpAPI"""
        if not self.sharp_api_key:
            return pd.DataFrame()

        url = f"{self.sharp_base}/odds/{sport}"
        headers = {"Authorization": f"Bearer {self.sharp_api_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data.get('odds', []))
            return df
        except Exception as e:
            logger.error(f"Error fetching SharpAPI odds: {e}")
            return pd.DataFrame()

    def calculate_implied_probabilities(self, odds_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate implied probabilities from decimal odds"""
        df = odds_df.copy()
        df['implied_prob'] = 1 / df['odds']

        # Adjust for vig (overround)
        # Group by event and market to calculate fair probabilities
        def remove_vig(group):
            total_prob = group['implied_prob'].sum()
            if total_prob > 1:
                group['fair_prob'] = group['implied_prob'] / total_prob
            else:
                group['fair_prob'] = group['implied_prob']
            return group

        df = df.groupby(['event_id', 'market']).apply(remove_vig)
        return df

    def find_best_odds(self, odds_df: pd.DataFrame, event_id: str, outcome: str) -> Dict:
        """Find best available odds for a specific outcome"""
        filtered = odds_df[
            (odds_df['event_id'] == event_id) & 
            (odds_df['outcome'] == outcome)
        ]
        if filtered.empty:
            return {}

        best = filtered.loc[filtered['odds'].idxmax()]
        return {
            'bookmaker': best['bookmaker'],
            'odds': best['odds'],
            'implied_prob': best['implied_prob'],
            'fair_prob': best.get('fair_prob', best['implied_prob'])
        }


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    collector = OddsCollector()
    sports = collector.get_the_odds_sports()
    print(f"Available sports: {len(sports)}")


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  END OF MODULE — EMPIRE SPORT INSTINCTS ARENA
# ⚜  Dark Gold Premium Edition v2.0 | Production Ready
# ──────────────────────────────────────────────────────────────────────────────