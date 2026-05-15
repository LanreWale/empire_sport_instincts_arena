"""
ARENA FORGE — NBA Feature Engineering
Transforms raw NBA data into 30+ predictive features.
EMPIRE SPORT INSTINCTS ARENA | Premium Basketball Intelligence
"""
import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class NBAFeatureEngineer:
    """Engineers premium features for NBA game prediction

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Generates gold-standard predictive features for NBA markets.
    """

    def __init__(self):
        self.feature_version = "v1.0-premium"
        self.module_name = "ARENA FORGE — NBA"

    def calculate_all_features(self, home_team_id: int, away_team_id: int,
                               game_date: datetime, historical_data: pd.DataFrame) -> Dict:
        """Calculate complete premium feature set for an NBA game"""
        logger.info(f"[{self.module_name}] Engineering features for {home_team_id} vs {away_team_id}")
        features = {}

        # Offensive Efficiency
        features.update(self._calculate_offensive_features(home_team_id, away_team_id, historical_data))

        # Defensive Efficiency
        features.update(self._calculate_defensive_features(home_team_id, away_team_id, historical_data))

        # Situational Factors
        features.update(self._calculate_situational_features(home_team_id, away_team_id, game_date, historical_data))

        # Momentum & Trends
        features.update(self._calculate_momentum_features(home_team_id, away_team_id, historical_data))

        features['feature_version'] = self.feature_version
        features['computed_at'] = datetime.now().isoformat()
        features['engineer_module'] = self.module_name

        logger.info(f"[{self.module_name}] Generated {len(features)} NBA features")
        return features

    def _calculate_offensive_features(self, home_id: int, away_id: int, data: pd.DataFrame) -> Dict:
        """Calculate offensive efficiency features"""
        home_games = data[data['TEAM_ID'] == home_id].tail(10)
        away_games = data[data['TEAM_ID'] == away_id].tail(10)

        return {
            'pts_avg_home': home_games['PTS'].mean() if not home_games.empty else 110.0,
            'pts_avg_away': away_games['PTS'].mean() if not away_games.empty else 108.0,
            'fg_pct_home': home_games['FG_PCT'].mean() if not home_games.empty else 0.46,
            'fg_pct_away': away_games['FG_PCT'].mean() if not away_games.empty else 0.45,
            'fg3_pct_home': home_games['FG3_PCT'].mean() if not home_games.empty else 0.36,
            'fg3_pct_away': away_games['FG3_PCT'].mean() if not away_games.empty else 0.35,
            'ft_pct_home': home_games['FT_PCT'].mean() if not home_games.empty else 0.78,
            'ft_pct_away': away_games['FT_PCT'].mean() if not away_games.empty else 0.77,
            'ast_avg_home': home_games['AST'].mean() if not home_games.empty else 24.0,
            'ast_avg_away': away_games['AST'].mean() if not away_games.empty else 23.0,
            'oreb_pct_home': home_games['OREB'].mean() / (home_games['OREB'].mean() + home_games['DREB'].mean()) if not home_games.empty else 0.23,
            'oreb_pct_away': away_games['OREB'].mean() / (away_games['OREB'].mean() + away_games['DREB'].mean()) if not away_games.empty else 0.23,
            'tov_pct_home': home_games['TOV'].mean() / home_games['PTS'].mean() if not home_games.empty else 0.12,
            'tov_pct_away': away_games['TOV'].mean() / away_games['PTS'].mean() if not away_games.empty else 0.12,
            'pace_factor_home': home_games['FGA'].mean() + home_games['FTA'].mean() * 0.44 + home_games['TOV'].mean() if not home_games.empty else 100.0,
            'pace_factor_away': away_games['FGA'].mean() + away_games['FTA'].mean() * 0.44 + away_games['TOV'].mean() if not away_games.empty else 100.0,
        }

    def _calculate_defensive_features(self, home_id: int, away_id: int, data: pd.DataFrame) -> Dict:
        """Calculate defensive efficiency features"""
        home_games = data[data['TEAM_ID'] == home_id].tail(10)
        away_games = data[data['TEAM_ID'] == away_id].tail(10)

        return {
            'pts_allowed_home': home_games['PTS_ALLOWED'].mean() if not home_games.empty else 110.0,
            'pts_allowed_away': away_games['PTS_ALLOWED'].mean() if not away_games.empty else 108.0,
            'def_rating_home': (home_games['PTS_ALLOWED'].mean() / home_games['PACE'].mean() * 100) if not home_games.empty else 110.0,
            'def_rating_away': (away_games['PTS_ALLOWED'].mean() / away_games['PACE'].mean() * 100) if not away_games.empty else 110.0,
            'stl_avg_home': home_games['STL'].mean() if not home_games.empty else 7.5,
            'stl_avg_away': away_games['STL'].mean() if not away_games.empty else 7.5,
            'blk_avg_home': home_games['BLK'].mean() if not home_games.empty else 4.5,
            'blk_avg_away': away_games['BLK'].mean() if not away_games.empty else 4.5,
            'def_reb_pct_home': home_games['DREB'].mean() / (home_games['DREB'].mean() + home_games['OREB_ALLOWED'].mean()) if not home_games.empty else 0.77,
            'def_reb_pct_away': away_games['DREB'].mean() / (away_games['DREB'].mean() + away_games['OREB_ALLOWED'].mean()) if not away_games.empty else 0.77,
        }

    def _calculate_situational_features(self, home_id: int, away_id: int, 
                                         game_date: datetime, data: pd.DataFrame) -> Dict:
        """Calculate situational and rest features"""
        home_games = data[data['TEAM_ID'] == home_id]
        away_games = data[data['TEAM_ID'] == away_id]

        # Calculate rest days
        home_last = home_games.tail(1)
        away_last = away_games.tail(1)

        rest_home = 2
        rest_away = 2

        if not home_last.empty:
            last_date = pd.to_datetime(home_last.iloc[0]['GAME_DATE'])
            rest_home = max((game_date - last_date).days, 1)

        if not away_last.empty:
            last_date = pd.to_datetime(away_last.iloc[0]['GAME_DATE'])
            rest_away = max((game_date - last_date).days, 1)

        return {
            'rest_days_home': rest_home,
            'rest_days_away': rest_away,
            'back_to_back_home': 1 if rest_home == 1 else 0,
            'back_to_back_away': 1 if rest_away == 1 else 0,
            'home_court_advantage': 3.5,  # Historical NBA home court advantage in points
            'travel_distance_away': 0.0,  # Would calculate from team cities
            'altitude_factor': 0.0,  # Denver, Utah elevation effects
            'time_zone_change': 0,
            'schedule_strength_home': 0.5,
            'schedule_strength_away': 0.5,
        }

    def _calculate_momentum_features(self, home_id: int, away_id: int, data: pd.DataFrame) -> Dict:
        """Calculate momentum and trend features"""
        home_games = data[data['TEAM_ID'] == home_id].tail(5)
        away_games = data[data['TEAM_ID'] == away_id].tail(5)

        home_wins = len(home_games[home_games['WL'] == 'W']) if not home_games.empty else 0
        away_wins = len(away_games[away_games['WL'] == 'W']) if not away_games.empty else 0

        return {
            'win_streak_home': home_wins,
            'win_streak_away': away_wins,
            'momentum_score_home': home_wins / 5.0,
            'momentum_score_away': away_wins / 5.0,
            'plus_minus_avg_home': home_games['PLUS_MINUS'].mean() if not home_games.empty else 0.0,
            'plus_minus_avg_away': away_games['PLUS_MINUS'].mean() if not away_games.empty else 0.0,
            'clutch_performance_home': 0.5,
            'clutch_performance_away': 0.5,
            'blowout_factor_home': len(home_games[abs(home_games['PLUS_MINUS']) > 20]) if not home_games.empty else 0,
            'blowout_factor_away': len(away_games[abs(away_games['PLUS_MINUS']) > 20]) if not away_games.empty else 0,
        }

    def get_feature_summary(self, features: Dict) -> Dict:
        """Get premium summary of engineered NBA features"""
        return {
            'total_features': len(features),
            'feature_version': features.get('feature_version', 'unknown'),
            'computed_at': features.get('computed_at'),
            'engineer': features.get('engineer_module'),
            'categories': {
                'offensive': len([k for k in features.keys() if any(x in k for x in ['pts', 'fg', 'ast', 'oreb', 'tov', 'pace'])]),
                'defensive': len([k for k in features.keys() if any(x in k for x in ['allowed', 'def_rating', 'stl', 'blk', 'def_reb'])]),
                'situational': len([k for k in features.keys() if any(x in k for x in ['rest', 'back_to_back', 'travel', 'altitude', 'schedule'])]),
                'momentum': len([k for k in features.keys() if any(x in k for x in ['win_streak', 'momentum', 'plus_minus', 'clutch', 'blowout'])]),
            }
        }

if __name__ == "__main__":
    engineer = NBAFeatureEngineer()
    features = engineer.calculate_all_features(1, 2, datetime.now(), pd.DataFrame())
    print(f"[ARENA FORGE] Generated {len(features)} NBA features")
    print(f"[ARENA FORGE] Summary: {engineer.get_feature_summary(features)}")