"""
COMMAND CENTRE — Bankroll Manager
Complete bankroll tracking and performance management.
EMPIRE SPORT INSTINCTS ARENA | Premium Capital Intelligence
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

class BankrollManager:
    """Manages bankroll, tracks performance, and enforces limits

    Part of the EMPIRE SPORT INSTINCTS ARENA COMMAND CENTRE.
    Provides gold-standard capital management for sports trading.
    """

    def __init__(self, initial_bankroll: float = 10000.0, currency: str = "USD"):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.peak_bankroll = initial_bankroll
        self.currency = currency
        self.bets = []
        self.daily_stats = {}
        self.module_name = "COMMAND CENTRE — Bankroll"
        logger.info(f"[{self.module_name}] Initialized with {currency} {initial_bankroll:,.2f}")

    def place_bet(self, stake: float, odds: float, expected_value: float,
                  sport: str, fixture_id: str) -> Dict:
        """Record a new bet with ARENA tracking"""
        if stake > self.current_bankroll:
            logger.warning(f"[{self.module_name}] Insufficient funds for bet on {fixture_id}")
            return {'error': 'insufficient_funds', 'available': self.current_bankroll}

        bet = {
            'id': f"ARENA_BET_{len(self.bets) + 1:04d}",
            'fixture_id': fixture_id,
            'sport': sport,
            'stake': stake,
            'odds': odds,
            'expected_value': expected_value,
            'potential_return': stake * odds,
            'status': 'open',
            'placed_at': datetime.now().isoformat(),
            'result': None,
            'profit_loss': None
        }

        self.bets.append(bet)
        self.current_bankroll -= stake

        logger.info(f"[{self.module_name}] Bet placed: {sport} {fixture_id} | Stake: {self.currency} {stake:,.2f} | EV: {expected_value:.2%}")
        return bet

    def settle_bet(self, bet_id: str, result: str, actual_return: float = 0):
        """Settle a bet with ARENA result tracking"""
        for bet in self.bets:
            if bet['id'] == bet_id:
                bet['status'] = 'settled'
                bet['result'] = result

                if result == 'win':
                    profit = actual_return - bet['stake']
                    self.current_bankroll += actual_return
                elif result == 'loss':
                    profit = -bet['stake']
                else:  # void/push
                    profit = 0
                    self.current_bankroll += bet['stake']

                bet['profit_loss'] = profit
                bet['settled_at'] = datetime.now().isoformat()

                # Update peak
                if self.current_bankroll > self.peak_bankroll:
                    self.peak_bankroll = self.current_bankroll
                    logger.info(f"[{self.module_name}] New peak bankroll: {self.currency} {self.peak_bankroll:,.2f}")

                logger.info(f"[{self.module_name}] Bet settled: {bet_id} | Result: {result} | P/L: {self.currency} {profit:,.2f}")
                return bet

        logger.error(f"[{self.module_name}] Bet not found: {bet_id}")
        return {'error': 'bet_not_found'}

    def get_statistics(self) -> Dict:
        """Calculate comprehensive ARENA statistics"""
        settled = [b for b in self.bets if b['status'] == 'settled']

        if not settled:
            return {
                'total_bets': 0,
                'win_rate': 0,
                'roi': 0,
                'current_bankroll': self.current_bankroll,
                'peak_bankroll': self.peak_bankroll,
                'drawdown': 0,
                'module': self.module_name
            }

        wins = len([b for b in settled if b['result'] == 'win'])
        losses = len([b for b in settled if b['result'] == 'loss'])
        total_profit = sum(b['profit_loss'] for b in settled)
        total_staked = sum(b['stake'] for b in settled)

        stats = {
            'total_bets': len(settled),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(settled) if settled else 0,
            'roi': total_profit / total_staked if total_staked > 0 else 0,
            'total_profit': total_profit,
            'current_bankroll': self.current_bankroll,
            'peak_bankroll': self.peak_bankroll,
            'drawdown': (self.peak_bankroll - self.current_bankroll) / self.peak_bankroll,
            'yield': total_profit / total_staked if total_staked > 0 else 0,
            'average_stake': total_staked / len(settled) if settled else 0,
            'average_odds': sum(b['odds'] for b in settled) / len(settled) if settled else 0,
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Stats: {stats['wins']}W/{stats['losses']}L | ROI: {stats['roi']:.2%} | Bankroll: {self.currency} {stats['current_bankroll']:,.2f}")
        return stats

    def get_daily_summary(self, date: datetime = None) -> Dict:
        """Get ARENA summary for a specific date"""
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')

        day_bets = [b for b in self.bets if b['placed_at'].startswith(date_str)]

        summary = {
            'date': date_str,
            'bets_placed': len(day_bets),
            'total_staked': sum(b['stake'] for b in day_bets),
            'sport_breakdown': pd.DataFrame(day_bets).groupby('sport').size().to_dict() if day_bets else {},
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Daily summary {date_str}: {summary['bets_placed']} bets, {self.currency} {summary['total_staked']:,.2f} staked")
        return summary

    def get_bankroll_history(self) -> pd.DataFrame:
        """Get bankroll evolution history for ARENA charts"""
        history = []
        running_bankroll = self.initial_bankroll

        for bet in self.bets:
            if bet['status'] == 'settled' and bet['profit_loss'] is not None:
                running_bankroll += bet['profit_loss']
                history.append({
                    'date': bet['settled_at'],
                    'bankroll': running_bankroll,
                    'bet_id': bet['id'],
                    'profit_loss': bet['profit_loss']
                })

        return pd.DataFrame(history)

if __name__ == "__main__":
    manager = BankrollManager()
    print(f"[{manager.module_name}] Initialized successfully")
    print(f"[{manager.module_name}] Ready for ARENA trading operations")