"""
EMPIRE CORE — EMPIRE SPORT INSTINCTS ARENA
Premium ensemble model training and uncertainty quantification.
The brain of the ARENA — where algorithms meet instinct.

Modules:
    ensemble_trainer         — XGBoost, Transformer, Bayesian ensemble training
    uncertainty_quantification — Confidence intervals and calibration

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

from .ensemble_trainer import EmpireEnsembleTrainer
from .uncertainty_quantification import UncertaintyQuantifier

__all__ = ['EmpireEnsembleTrainer', 'UncertaintyQuantifier']

# Brand color constants for programmatic use
GOLD_PRIMARY = "#D4AF37"
GOLD_BRIGHT = "#FFD700"
GOLD_DARK = "#B8860B"
SILVER = "#C0C0C0"
DARK_BG = "#0a0a0a"
DARK_SECONDARY = "#1a1a1a"
