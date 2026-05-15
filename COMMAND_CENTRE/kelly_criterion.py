"""
COMMAND CENTRE — Kelly Criterion Calculator
Optimal bet sizing with fractional Kelly for safety.
EMPIRE SPORT INSTINCTS ARENA | Premium Position Sizing Intelligence
"""
import numpy as np
from typing import Dict, Optional
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class KellyCriterion:
    """Implements Kelly Criterion for optimal bet sizing

    Part of the EMPIRE SPORT INSTINCTS ARENA COMMAND CENTRE.
    Provides gold-standard position sizing for maximum growth with controlled risk.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'fraction': 0.25,  # Quarter Kelly
            'min_edge': 0.02,
            'max_kelly_pct': 0.03,  # Cap at 3% of bankroll
            'min_bet': 10.0,
            'max_bet_pct': 0.05
        }
        self.module_name = "COMMAND CENTRE — Kelly"
        logger.info(f"[{self.module_name}] Calculator initialized | Fraction: {self.config['fraction']} | Max: {self.config['max_kelly_pct']:.1%}")

    def calculate_stake(self, bankroll: float, predicted_prob: float, 
                       decimal_odds: float, confidence: float = 1.0) -> Dict:
        """Calculate optimal ARENA stake using Kelly Criterion"""

        # Calculate edge
        implied_prob = 1 / decimal_odds
        edge = predicted_prob - implied_prob

        if edge <= self.config['min_edge']:
            logger.info(f"[{self.module_name}] Edge too small: {edge:.2%} (min: {self.config['min_edge']:.1%})")
            return {
                'stake': 0.0,
                'kelly_fraction': 0.0,
                'reason': 'edge_below_minimum',
                'module': self.module_name
            }

        # Full Kelly formula: f* = (bp - q) / b
        # where b = odds - 1, p = predicted_prob, q = 1 - p
        b = decimal_odds - 1
        p = predicted_prob
        q = 1 - p

        full_kelly = (b * p - q) / b

        if full_kelly <= 0:
            logger.info(f"[{self.module_name}] Negative Kelly: {full_kelly:.4f}")
            return {
                'stake': 0.0,
                'kelly_fraction': 0.0,
                'reason': 'negative_kelly',
                'module': self.module_name
            }

        # Apply fractional Kelly
        fractional_kelly = full_kelly * self.config['fraction']

        # Apply confidence adjustment
        adjusted_kelly = fractional_kelly * confidence

        # Cap at maximum
        capped_kelly = min(adjusted_kelly, self.config['max_kelly_pct'])

        # Calculate stake
        stake = bankroll * capped_kelly

        # Apply min/max constraints
        stake = max(stake, self.config['min_bet'])
        stake = min(stake, bankroll * self.config['max_bet_pct'])

        result = {
            'stake': round(stake, 2),
            'kelly_fraction': round(capped_kelly, 4),
            'full_kelly': round(full_kelly, 4),
            'fractional_kelly': round(fractional_kelly, 4),
            'edge': round(edge, 4),
            'implied_prob': round(implied_prob, 4),
            'predicted_prob': round(predicted_prob, 4),
            'confidence': round(confidence, 4),
            'bankroll_pct': round(stake / bankroll, 4) if bankroll > 0 else 0,
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Stake: {stake:,.2f} ({result['bankroll_pct']:.2%}) | Edge: {edge:.2%} | Kelly: {capped_kelly:.4f}")
        return result

    def simultaneous_kelly(self, opportunities: list, bankroll: float) -> list:
        """Calculate ARENA stakes for multiple simultaneous opportunities"""
        # Simplified: allocate proportionally
        total_edge = sum(opp['edge'] for opp in opportunities)

        results = []
        for opp in opportunities:
            if total_edge > 0:
                allocation = opp['edge'] / total_edge
                stake = self.calculate_stake(
                    bankroll * allocation,
                    opp['predicted_prob'],
                    opp['odds'],
                    opp.get('confidence', 1.0)
                )
                results.append(stake)
            else:
                results.append({'stake': 0, 'reason': 'no_edge', 'module': self.module_name})

        logger.info(f"[{self.module_name}] Simultaneous Kelly: {len(opportunities)} opportunities processed")
        return results

    def get_config(self) -> Dict:
        """Get ARENA Kelly configuration"""
        return {
            'config': self.config,
            'module': self.module_name
        }

if __name__ == "__main__":
    kelly = KellyCriterion()
    result = kelly.calculate_stake(10000, 0.60, 2.0)
    print(f"[{kelly.module_name}] Test result: {result['stake']:,.2f} stake at {result['bankroll_pct']:.2%}")
    print(f"[{kelly.module_name}] ARENA position sizing ready")