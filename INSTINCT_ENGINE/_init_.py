"""
INSTINCT ENGINE — EMPIRE SPORT INSTINCTS ARENA
Premium prediction pipeline, probability calibration, and value detection.
The heart of the ARENA — where data transforms into actionable intelligence.

Modules:
    prediction_pipeline      — End-to-end prediction generation
    probability_calibrator   — Ensures reliable, well-calibrated probabilities
    value_detector           — Identifies positive expected value opportunities

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

from .prediction_pipeline import PredictionPipeline
from .probability_calibrator import ProbabilityCalibrator
from .value_detector import ValueDetector

__all__ = ['PredictionPipeline', 'ProbabilityCalibrator', 'ValueDetector']

# Brand color constants for programmatic use
GOLD_PRIMARY = "#D4AF37"
GOLD_BRIGHT = "#FFD700"
GOLD_DARK = "#B8860B"
SILVER = "#C0C0C0"
DARK_BG = "#0a0a0a"
DARK_SECONDARY = "#1a1a1a"
