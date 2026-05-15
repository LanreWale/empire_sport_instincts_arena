"""
COMMAND CENTRE — EMPIRE SPORT INSTINCTS ARENA
Premium risk management and bankroll control module.
The nerve center of the ARENA — where discipline meets strategy.

Modules:
    bankroll_manager      — Capital tracking and performance analytics
    drawdown_protection   — Circuit breakers and risk limits
    kelly_criterion       — Optimal bet sizing algorithms

Color Palette:
    Gold Primary:   #D4AF37
    Gold Bright:    #FFD700
    Gold Dark:      #B8860B
    Silver:         #C0C0C0
    Positive:       #00FF00
    Negative:       #FF4444
"""

__version__ = "1.0.0-premium"
__author__ = "EMPIRE SPORT INSTINCTS ARENA"

from .bankroll_manager import BankrollManager
from .drawdown_protection import DrawdownProtection
from .kelly_criterion import KellyCriterion

__all__ = ['BankrollManager', 'DrawdownProtection', 'KellyCriterion']
