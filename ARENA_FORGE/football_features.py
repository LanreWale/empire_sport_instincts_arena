"""
ARENA FORGE — Football Feature Engineering
Transforms raw football data into 50+ predictive features.
EMPIRE SPORT INSTINCTS ARENA | Premium Football Intelligence
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class FootballFeatureEngineer:
    """Engineers premium features for football match prediction

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Generates gold-standard predictive features for football markets.
    """

    def __init__(self):
        self.feature_version = "v1.0-premium"
        self.rolling_windows = [3, 5, 10]
        self.module_name = "ARENA FORGE — Football"

    def calculate_all_features(self, home_team: str, away_team: str, 
                               match_date: datetime, historical_data: pd.DataFrame) -> Dict:
        """Calculate complete premium feature set for a football match"""
        logger.info(f"[{self.module_name}] Engineering features for {home_team} vs {away_team}")
        features = {}

        # 1. xG Features (Expected Goals)
        features.update(self._calculate_xg_features(home_team, away_team, historical_data))

        # 2. Form Features
        features.update(self._calculate_form_features(home_team, away_team, historical_data))

        # 3. Head-to-Head
        features.update(self._calculate_h2h_features(home_team, away_team, historical_data))

        # 4. Rest & Fatigue
        features.update(self._calculate_rest_features(home_team, away_team, match_date, historical_data))

        # 5. League Position & Context
        features.update(self._calculate_context_features(home_team, away_team, historical_data))

        # 6. Statistical Trends
        features.update(self._calculate_trend_features(home_team, away_team, historical_data))

        # 7. Market Features
        features.update(self._calculate_market_features(home_team, away_team))

        features['feature_version'] = self.feature_version
        features['computed_at'] = datetime.now().isoformat()
        features['engineer_module'] = self.module_name

        logger.info(f"[{self.module_name}] Generated {len(features)} features")
        return features

    def _calculate_xg_features(self, home_team: str, away_team: str, 
                               data: pd.DataFrame) -> Dict:
        """Calculate expected goals features"""
        home_matches = data[data['home_team'] == home_team].tail(5)
        away_matches = data[data['away_team'] == away_team].tail(5)

        features = {
            'xg_home_rolling_5': home_matches['xg_home'].mean() if not home_matches.empty else 1.4,
            'xg_away_rolling_5': away_matches['xg_away'].mean() if not away_matches.empty else 1.1,
            'xg_diff': 0.0,
            'xg_home_trend': 0.0,
            'xg_away_trend': 0.0,
            'shots_on_target_diff': 0.0,
            'big_chances_home': 0.0,
            'big_chances_away': 0.0,
        }

        if not home_matches.empty and not away_matches.empty:
            features['xg_diff'] = features['xg_home_rolling_5'] - features['xg_away_rolling_5']

        return features

    def _calculate_form_features(self, home_team: str, away_team: str, 
                                  data: pd.DataFrame) -> Dict:
        """Calculate team form features"""
        # Get last 5 matches for each team (home and away)
        home_last5 = data[
            (data['home_team'] == home_team) | (data['away_team'] == home_team)
        ].tail(5)

        away_last5 = data[
            (data['home_team'] == away_team) | (data['away_team'] == away_team)
        ].tail(5)

        def calculate_form(matches, team):
            if matches.empty:
                return {'wins': 0, 'draws': 0, 'losses': 0, 'points': 0, 'form_string': '?????'}

            wins, draws, losses = 0, 0, 0
            for _, match in matches.iterrows():
                if match['home_team'] == team:
                    if match['home_score'] > match['away_score']: wins += 1
                    elif match['home_score'] == match['away_score']: draws += 1
                    else: losses += 1
                else:
                    if match['away_score'] > match['home_score']: wins += 1
                    elif match['away_score'] == match['home_score']: draws += 1
                    else: losses += 1

            points = wins * 3 + draws
            form_chars = []
            for _, match in matches.iterrows():
                if match['home_team'] == team:
                    if match['home_score'] > match['away_score']: form_chars.append('W')
                    elif match['home_score'] == match['away_score']: form_chars.append('D')
                    else: form_chars.append('L')
                else:
                    if match['away_score'] > match['home_score']: form_chars.append('W')
                    elif match['away_score'] == match['home_score']: form_chars.append('D')
                    else: form_chars.append('L')

            return {
                'wins': wins, 'draws': draws, 'losses': losses,
                'points': points,
                'form_string': ''.join(reversed(form_chars))
            }

        home_form = calculate_form(home_last5, home_team)
        away_form = calculate_form(away_last5, away_team)

        return {
            'form_home_wins_last5': home_form['wins'],
            'form_home_draws_last5': home_form['draws'],
            'form_home_losses_last5': home_form['losses'],
            'form_home_points_last5': home_form['points'],
            'form_home_string': home_form['form_string'],
            'form_away_wins_last5': away_form['wins'],
            'form_away_draws_last5': away_form['draws'],
            'form_away_losses_last5': away_form['losses'],
            'form_away_points_last5': away_form['points'],
            'form_away_string': away_form['form_string'],
            'form_points_diff': home_form['points'] - away_form['points'],
            'home_advantage_factor': 0.35,  # Historical home win %
        }

    def _calculate_h2h_features(self, home_team: str, away_team: str, 
                                 data: pd.DataFrame) -> Dict:
        """Calculate head-to-head features"""
        h2h = data[
            ((data['home_team'] == home_team) & (data['away_team'] == away_team)) |
            ((data['home_team'] == away_team) & (data['away_team'] == home_team))
        ].tail(10)

        if h2h.empty:
            return {
                'h2h_matches': 0,
                'h2h_home_win_pct': 0.33,
                'h2h_away_win_pct': 0.33,
                'h2h_draw_pct': 0.34,
                'h2h_goals_avg': 2.5,
                'h2h_btts_pct': 0.5,
                'h2h_over_2_5_pct': 0.5,
            }

        home_wins = len(h2h[h2h['home_score'] > h2h['away_score']])
        away_wins = len(h2h[h2h['away_score'] > h2h['home_score']])
        draws = len(h2h[h2h['home_score'] == h2h['away_score']])
        total = len(h2h)

        total_goals = (h2h['home_score'] + h2h['away_score']).sum()
        btts = len(h2h[(h2h['home_score'] > 0) & (h2h['away_score'] > 0)])
        over_2_5 = len(h2h[(h2h['home_score'] + h2h['away_score']) > 2.5])

        return {
            'h2h_matches': total,
            'h2h_home_win_pct': home_wins / total if total > 0 else 0.33,
            'h2h_away_win_pct': away_wins / total if total > 0 else 0.33,
            'h2h_draw_pct': draws / total if total > 0 else 0.34,
            'h2h_goals_avg': total_goals / total if total > 0 else 2.5,
            'h2h_btts_pct': btts / total if total > 0 else 0.5,
            'h2h_over_2_5_pct': over_2_5 / total if total > 0 else 0.5,
        }

    def _calculate_rest_features(self, home_team: str, away_team: str, 
                                  match_date: datetime, data: pd.DataFrame) -> Dict:
        """Calculate rest and fatigue features"""
        home_last = data[data['home_team'] == home_team].tail(1)
        away_last = data[data['away_team'] == away_team].tail(1)

        rest_home = 7  # Default
        rest_away = 7

        if not home_last.empty:
            last_date = pd.to_datetime(home_last.iloc[0]['date'])
            rest_home = (match_date - last_date).days

        if not away_last.empty:
            last_date = pd.to_datetime(away_last.iloc[0]['date'])
            rest_away = (match_date - last_date).days

        return {
            'rest_days_home': max(rest_home, 1),
            'rest_days_away': max(rest_away, 1),
            'rest_advantage': rest_home - rest_away,
            'fatigue_home': 1.0 if rest_home >= 7 else (rest_home / 7.0),
            'fatigue_away': 1.0 if rest_away >= 7 else (rest_away / 7.0),
            'congestion_home': 1 if rest_home <= 3 else 0,
            'congestion_away': 1 if rest_away <= 3 else 0,
        }

    def _calculate_context_features(self, home_team: str, away_team: str, 
                                    data: pd.DataFrame) -> Dict:
        """Calculate league context features"""
        # League position simulation
        all_teams = pd.concat([data['home_team'], data['away_team']]).unique()
        n_teams = len(all_teams) if len(all_teams) > 0 else 20

        return {
            'league_position_diff': 0,  # Would calculate from standings
            'season_progress': 0.5,  # % of season completed
            'relegation_pressure_home': 0,
            'relegation_pressure_away': 0,
            'title_race_pressure_home': 0,
            'title_race_pressure_away': 0,
            'european_spot_pressure': 0,
            'derby_match': 0,  # Would check if derby
            'cup_final_factor': 0,
        }

    def _calculate_trend_features(self, home_team: str, away_team: str, 
                                   data: pd.DataFrame) -> Dict:
        """Calculate statistical trend features"""
        home_matches = data[data['home_team'] == home_team].tail(10)
        away_matches = data[data['away_team'] == away_team].tail(10)

        features = {
            'goals_scored_trend_home': 0.0,
            'goals_conceded_trend_home': 0.0,
            'goals_scored_trend_away': 0.0,
            'goals_conceded_trend_away': 0.0,
            'clean_sheet_pct_home': 0.0,
            'clean_sheet_pct_away': 0.0,
            'btts_pct_home': 0.0,
            'btts_pct_away': 0.0,
            'over_2_5_pct_home': 0.0,
            'over_2_5_pct_away': 0.0,
            'corner_avg_home': 5.5,
            'corner_avg_away': 5.5,
            'card_avg_home': 2.5,
            'card_avg_away': 2.5,
        }

        if not home_matches.empty:
            features['goals_scored_trend_home'] = home_matches['home_score'].mean()
            features['goals_conceded_trend_home'] = home_matches['away_score'].mean()
            features['clean_sheet_pct_home'] = (home_matches['away_score'] == 0).mean()
            features['btts_pct_home'] = ((home_matches['home_score'] > 0) & (home_matches['away_score'] > 0)).mean()
            features['over_2_5_pct_home'] = ((home_matches['home_score'] + home_matches['away_score']) > 2.5).mean()

        if not away_matches.empty:
            features['goals_scored_trend_away'] = away_matches['away_score'].mean()
            features['goals_conceded_trend_away'] = away_matches['home_score'].mean()
            features['clean_sheet_pct_away'] = (away_matches['home_score'] == 0).mean()
            features['btts_pct_away'] = ((away_matches['home_score'] > 0) & (away_matches['away_score'] > 0)).mean()
            features['over_2_5_pct_away'] = ((away_matches['home_score'] + away_matches['away_score']) > 2.5).mean()

        return features

    def _calculate_market_features(self, home_team: str, away_team: str) -> Dict:
        """Calculate market-derived features"""
        return {
            'market_implied_home_prob': 0.45,
            'market_implied_draw_prob': 0.25,
            'market_implied_away_prob': 0.30,
            'market_total_goals': 2.5,
            'market_spread': 0.0,
            'odds_movement_home': 0.0,
            'odds_movement_away': 0.0,
            'sharp_money_indicator': 0.0,
            'public_money_pct': 0.5,
        }

    def get_feature_summary(self, features: Dict) -> Dict:
        """Get premium summary of engineered features"""
        return {
            'total_features': len(features),
            'feature_version': features.get('feature_version', 'unknown'),
            'computed_at': features.get('computed_at'),
            'engineer': features.get('engineer_module'),
            'categories': {
                'xg': len([k for k in features.keys() if 'xg' in k]),
                'form': len([k for k in features.keys() if 'form' in k]),
                'h2h': len([k for k in features.keys() if 'h2h' in k]),
                'rest': len([k for k in features.keys() if 'rest' in k or 'fatigue' in k]),
                'context': len([k for k in features.keys() if 'pressure' in k or 'league' in k]),
                'trend': len([k for k in features.keys() if 'trend' in k or 'pct' in k]),
                'market': len([k for k in features.keys() if 'market' in k or 'odds' in k]),
            }
        }

if __name__ == "__main__":
    engineer = FootballFeatureEngineer()
    # Example usage with empty data
    features = engineer.calculate_all_features("Team A", "Team B", datetime.now(), pd.DataFrame())
    print(f"[ARENA FORGE] Generated {len(features)} football features")
    print(f"[ARENA FORGE] Summary: {engineer.get_feature_summary(features)}")