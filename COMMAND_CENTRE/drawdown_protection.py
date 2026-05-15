"""
COMMAND CENTRE — Drawdown Protection
Circuit breakers and risk limits to protect bankroll.
EMPIRE SPORT INSTINCTS ARENA | Premium Risk Shield
"""
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DrawdownProtection:
    """Protects bankroll from excessive drawdowns

    Part of the EMPIRE SPORT INSTINCTS ARENA COMMAND CENTRE.
    Implements gold-standard circuit breakers for capital preservation.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_drawdown_pct': 0.20,  # 20% max drawdown
            'cooldown_period_days': 7,
            'warning_threshold': 0.15,
            'daily_loss_limit': 0.05,  # 5% daily loss limit
            'weekly_loss_limit': 0.10  # 10% weekly loss limit
        }
        self.peak_bankroll = 0
        self.current_drawdown = 0
        self.cooldown_until = None
        self.daily_losses = {}
        self.weekly_losses = {}
        self.module_name = "COMMAND CENTRE — Drawdown"
        logger.info(f"[{self.module_name}] Protection armed | Max DD: {self.config['max_drawdown_pct']:.1%} | Daily Limit: {self.config['daily_loss_limit']:.1%}")

    def check_status(self, current_bankroll: float, date: datetime = None) -> Dict:
        """Check if ARENA trading should be allowed"""
        date = date or datetime.now()

        # Update peak
        if current_bankroll > self.peak_bankroll:
            self.peak_bankroll = current_bankroll
            self.current_drawdown = 0
            logger.info(f"[{self.module_name}] New peak: {self.peak_bankroll:,.2f}")
        else:
            self.current_drawdown = (self.peak_bankroll - current_bankroll) / self.peak_bankroll

        # Check cooldown
        if self.cooldown_until and date < self.cooldown_until:
            logger.warning(f"[{self.module_name}] COOLDOWN ACTIVE until {self.cooldown_until.isoformat()}")
            return {
                'trading_allowed': False,
                'reason': 'cooldown_active',
                'cooldown_until': self.cooldown_until.isoformat(),
                'drawdown': self.current_drawdown,
                'status': 'PROTECTED'
            }

        # Check max drawdown
        if self.current_drawdown >= self.config['max_drawdown_pct']:
            self.cooldown_until = date + timedelta(days=self.config['cooldown_period_days'])
            logger.error(f"[{self.module_name}] MAX DRAWDOWN REACHED: {self.current_drawdown:.2%} | Cooldown until {self.cooldown_until.isoformat()}")
            return {
                'trading_allowed': False,
                'reason': 'max_drawdown_reached',
                'cooldown_until': self.cooldown_until.isoformat(),
                'drawdown': self.current_drawdown,
                'status': 'LOCKED'
            }

        # Check warning threshold
        warning = self.current_drawdown >= self.config['warning_threshold']
        if warning:
            logger.warning(f"[{self.module_name}] WARNING: Drawdown at {self.current_drawdown:.2%} (threshold: {self.config['warning_threshold']:.1%})")

        # Check daily limit
        date_str = date.strftime('%Y-%m-%d')
        daily_loss = self.daily_losses.get(date_str, 0)
        if daily_loss >= self.config['daily_loss_limit']:
            logger.error(f"[{self.module_name}] DAILY LOSS LIMIT: {daily_loss:.2%} (limit: {self.config['daily_loss_limit']:.1%})")
            return {
                'trading_allowed': False,
                'reason': 'daily_loss_limit',
                'daily_loss': daily_loss,
                'drawdown': self.current_drawdown,
                'status': 'LIMITED'
            }

        status = 'CAUTION' if warning else 'NORMAL'
        logger.info(f"[{self.module_name}] Status: {status} | DD: {self.current_drawdown:.2%} | Daily: {daily_loss:.2%}")

        return {
            'trading_allowed': True,
            'warning': warning,
            'drawdown': self.current_drawdown,
            'peak_bankroll': self.peak_bankroll,
            'daily_loss': daily_loss,
            'status': status
        }

    def record_bet(self, stake: float, result: str, profit_loss: float, date: datetime = None):
        """Record bet result for ARENA tracking"""
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')

        if result == 'loss':
            loss_pct = abs(profit_loss) / self.peak_bankroll if self.peak_bankroll > 0 else 0
            self.daily_losses[date_str] = self.daily_losses.get(date_str, 0) + loss_pct
            logger.info(f"[{self.module_name}] Loss recorded: {loss_pct:.2%} | Daily total: {self.daily_losses[date_str]:.2%}")

    def reset(self):
        """Reset ARENA drawdown tracking"""
        self.peak_bankroll = 0
        self.current_drawdown = 0
        self.cooldown_until = None
        self.daily_losses = {}
        self.weekly_losses = {}
        logger.info(f"[{self.module_name}] Protection reset | System re-armed")

    def get_protection_summary(self) -> Dict:
        """Get ARENA protection status summary"""
        return {
            'peak_bankroll': self.peak_bankroll,
            'current_drawdown': self.current_drawdown,
            'max_allowed_drawdown': self.config['max_drawdown_pct'],
            'cooldown_active': self.cooldown_until is not None,
            'cooldown_until': self.cooldown_until.isoformat() if self.cooldown_until else None,
            'daily_losses': self.daily_losses,
            'config': self.config,
            'module': self.module_name
        }

if __name__ == "__main__":
    protection = DrawdownProtection()
    print(f"[{protection.module_name}] Initialized successfully")
    print(f"[{protection.module_name}] ARENA risk shield active")