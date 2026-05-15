"""
INSTINCT ENGINE — Value Detection Engine
Identifies positive expected value opportunities from predictions and odds.
EMPIRE SPORT INSTINCTS ARENA | Premium Value Intelligence
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ValueDetector:
    """Detects value betting opportunities using EV analysis

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard value detection for all sports markets.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'min_ev': 0.02,  # 2% minimum expected value
            'min_confidence': 0.55,
            'max_uncertainty': 0.15
        }
        self.module_name = "INSTINCT ENGINE — Value Detector"
        logger.info(f"[{self.module_name}] Initialized | Min EV: {self.config['min_ev']:.1%} | Min Confidence: {self.config['min_confidence']:.1%}")

    def detect_value(self, prediction: Dict, odds: Dict, market: str = 'h2h') -> Optional[Dict]:
        """Detect ARENA value opportunity for a single prediction"""
        probs = prediction.get('probabilities', [])
        if not probs:
            logger.info(f"[{self.module_name}] No probabilities found, skipping")
            return None

        # Map market to probability index
        if market == 'h2h':
            if len(probs) == 3:  # Football (H/D/A)
                outcomes = ['home', 'draw', 'away']
            else:  # Basketball/Tennis (H/A)
                outcomes = ['home', 'away']
        else:
            outcomes = ['over', 'under']

        opportunities = []

        for i, outcome in enumerate(outcomes):
            if i >= len(probs):
                continue

            predicted_prob = probs[i]
            decimal_odds = odds.get(f'{outcome}_odds', 0)

            if decimal_odds <= 1.0:
                continue

            # Calculate implied probability from odds
            implied_prob = 1 / decimal_odds

            # Calculate Expected Value
            ev = (predicted_prob * decimal_odds) - 1

            # Calculate edge
            edge = predicted_prob - implied_prob

            # Check thresholds
            if ev >= self.config['min_ev'] and edge > 0:
                opportunity = {
                    'outcome': outcome,
                    'predicted_probability': float(predicted_prob),
                    'implied_probability': float(implied_prob),
                    'decimal_odds': decimal_odds,
                    'expected_value': float(ev),
                    'edge_percentage': float(edge),
                    'market': market,
                    'confidence': prediction.get('confidence', 0),
                    'uncertainty_lower': prediction.get('uncertainty_lower', 0),
                    'uncertainty_upper': prediction.get('uncertainty_upper', 1),
                    'value_rating': self.get_value_rating(ev),
                    'timestamp': datetime.now().isoformat(),
                    'module': self.module_name
                }
                opportunities.append(opportunity)
                logger.info(f"[{self.module_name}] Value found: {outcome} | EV: {ev:.2%} | Edge: {edge:.2%} | Rating: {self.get_value_rating(ev)}")

        # Return best opportunity
        if opportunities:
            best = max(opportunities, key=lambda x: x['expected_value'])
            logger.info(f"[{self.module_name}] Best opportunity: {best['outcome']} | EV: {best['expected_value']:.2%}")
            return best

        logger.info(f"[{self.module_name}] No value opportunities found")
        return None

    def detect_all_values(self, predictions_df: pd.DataFrame, odds_df: pd.DataFrame) -> pd.DataFrame:
        """Batch ARENA value detection for multiple fixtures"""
        values = []
        logger.info(f"[{self.module_name}] Batch value detection: {len(predictions_df)} predictions")

        for _, pred_row in predictions_df.iterrows():
            fixture_id = pred_row['fixture_id']

            # Find matching odds
            fixture_odds = odds_df[odds_df['fixture_id'] == fixture_id]

            if fixture_odds.empty:
                continue

            # Build prediction dict
            prediction = {
                'probabilities': [
                    pred_row.get('predicted_home_prob', 0.33),
                    pred_row.get('predicted_draw_prob', 0.33),
                    pred_row.get('predicted_away_prob', 0.34)
                ],
                'confidence': pred_row.get('confidence_score', 0.5),
                'uncertainty_lower': pred_row.get('uncertainty_lower', 0),
                'uncertainty_upper': pred_row.get('uncertainty_upper', 1)
            }

            # Build odds dict
            for _, odds_row in fixture_odds.iterrows():
                odds = {
                    'home_odds': odds_row.get('home_odds', 0),
                    'draw_odds': odds_row.get('draw_odds', 0),
                    'away_odds': odds_row.get('away_odds', 0)
                }

                value = self.detect_value(prediction, odds)
                if value:
                    value['fixture_id'] = fixture_id
                    value['bookmaker'] = odds_row.get('bookmaker', 'unknown')
                    values.append(value)

        result_df = pd.DataFrame(values)
        logger.info(f"[{self.module_name}] Batch complete: {len(values)} value opportunities found")
        return result_df

    def calculate_fair_odds(self, predicted_prob: float, margin: float = 0.05) -> Dict:
        """Calculate ARENA fair odds from predicted probability"""
        if predicted_prob <= 0:
            return {'decimal': float('inf'), 'implied': 0}

        fair_decimal = 1 / predicted_prob

        # Add bookmaker margin
        with_margin = fair_decimal * (1 - margin)

        return {
            'fair_decimal': round(fair_decimal, 2),
            'with_margin': round(with_margin, 2),
            'implied_probability': round(predicted_prob, 4),
            'margin_applied': margin
        }

    def get_value_rating(self, ev: float) -> str:
        """Rate ARENA value opportunity quality"""
        if ev >= 0.10:
            return 'exceptional'
        elif ev >= 0.07:
            return 'strong'
        elif ev >= 0.05:
            return 'good'
        elif ev >= 0.02:
            return 'marginal'
        else:
            return 'no_value'

    def get_value_color(self, rating: str) -> str:
        """Get ARENA color for value rating"""
        colors = {
            'exceptional': '#FFD700',  # Gold
            'strong': '#D4AF37',       # Antique Gold
            'good': '#B8860B',         # Dark Goldenrod
            'marginal': '#C0C0C0',     # Silver
            'no_value': '#888888'      # Gray
        }
        return colors.get(rating, '#888888')

    def get_detector_stats(self) -> Dict:
        """Get ARENA value detector statistics"""
        return {
            'min_ev': self.config['min_ev'],
            'min_confidence': self.config['min_confidence'],
            'max_uncertainty': self.config['max_uncertainty'],
            'module': self.module_name,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    detector = ValueDetector()
    print(f"[{detector.module_name}] Initialized successfully")
    print(f"[{detector.module_name}] ARENA value intelligence ready")