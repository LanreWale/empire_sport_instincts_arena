"""
EMPIRE TESTING — EMPIRE SPORT INSTINCTS ARENA
Premium paper trading and walk-forward analysis module.
The proving ground of the ARENA — where strategies earn their crown.

Modules:
    paper_trading         — Virtual bankroll simulation and strategy validation
    walk_forward          — Temporal cross-validation and backtesting

Color Palette:
    Gold Primary:   #D4AF37
    Gold Bright:    #FFD700
    Gold Dark:      #B8860B
    Silver:         #C0C0C0
    Dark BG:        #0a0a0a
    Dark Secondary: #1a1a1a
"""

__version__ = "1.0.0-premium"
__author__ = "EMPIRE SPORT INSTINCTS ARENA"

from .paper_trading import PaperTradingEngine
from .walk_forward import WalkForwardTester

__all__ = ['PaperTradingEngine', 'WalkForwardTester']

# Brand color constants for programmatic use
GOLD_PRIMARY = "#D4AF37"
GOLD_BRIGHT = "#FFD700"
GOLD_DARK = "#B8860B"
SILVER = "#C0C0C0"
DARK_BG = "#0a0a0a"
DARK_SECONDARY = "#1a1a1a"
