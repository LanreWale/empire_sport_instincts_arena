"""
INSTINCT ENGINE — Probability Calibration
Ensures predicted probabilities are well-calibrated and reliable.
EMPIRE SPORT INSTINCTS ARENA | Premium Calibration Intelligence
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import CalibratedClassifierCV
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ProbabilityCalibrator:
    """Calibrates raw model probabilities to true probabilities

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard probability calibration for all sports markets.
    """

    def __init__(self):
        self.calibrators = {}
        self.calibration_data = {}
        self.module_name = "INSTINCT ENGINE — Calibrator"
        logger.info(f"[{self.module_name}] Initialized")

    def fit(self, raw_probs: np.ndarray, true_outcomes: np.ndarray, sport: str):
        """Fit ARENA calibration model for a sport"""
        # Use isotonic regression for calibration
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(raw_probs, true_outcomes)

        self.calibrators[sport] = iso
        self.calibration_data[sport] = {
            'raw_probs': raw_probs,
            'true_outcomes': true_outcomes,
            'n_samples': len(true_outcomes)
        }

        logger.info(f"[{self.module_name}] Fitted probability calibrator for {sport} | Samples: {len(true_outcomes)}")

    def calibrate(self, raw_probs: np.ndarray, sport: str) -> np.ndarray:
        """Calibrate raw probabilities with ARENA precision"""
        if sport in self.calibrators:
            calibrated = self.calibrators[sport].predict(raw_probs)
            logger.info(f"[{self.module_name}] Calibrated {len(raw_probs)} probabilities for {sport}")
            return calibrated

        # If no calibrator, return clipped
        logger.warning(f"[{self.module_name}] No calibrator for {sport}, using clipped raw probabilities")
        return np.clip(raw_probs, 0.01, 0.99)

    def evaluate_calibration(self, probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> Dict:
        """Evaluate ARENA calibration using reliability diagram"""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        bin_centers = []
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []

        for lower, upper in zip(bin_lowers, bin_uppers):
            mask = (probs > lower) & (probs <= upper)
            if np.sum(mask) > 0:
                bin_centers.append((lower + upper) / 2)
                bin_accuracies.append(np.mean(outcomes[mask]))
                bin_confidences.append(np.mean(probs[mask]))
                bin_counts.append(np.sum(mask))

        # Expected Calibration Error
        ece = np.sum(np.abs(np.array(bin_accuracies) - np.array(bin_confidences)) * 
                     np.array(bin_counts)) / np.sum(bin_counts)

        # Maximum Calibration Error
        mce = np.max(np.abs(np.array(bin_accuracies) - np.array(bin_confidences)))

        result = {
            'expected_calibration_error': float(ece),
            'max_calibration_error': float(mce),
            'n_bins': n_bins,
            'bin_centers': bin_centers,
            'bin_accuracies': bin_accuracies,
            'bin_confidences': bin_confidences,
            'bin_counts': bin_counts,
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Calibration evaluation: ECE={ece:.4f} | MCE={mce:.4f} | Bins={n_bins}")
        return result

    def apply_temperature_scaling(self, logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        """Apply ARENA temperature scaling to logits"""
        # Temperature > 1 makes distribution more uniform (less confident)
        # Temperature < 1 makes distribution more peaky (more confident)
        scaled_logits = logits / temperature
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
        calibrated = exp_logits / np.sum(exp_logits)

        logger.info(f"[{self.module_name}] Temperature scaling applied: T={temperature}")
        return calibrated

    def get_calibration_summary(self, sport: str) -> Dict:
        """Get ARENA calibration summary for a sport"""
        data = self.calibration_data.get(sport, {})
        return {
            'sport': sport,
            'calibrator_fitted': sport in self.calibrators,
            'n_samples': data.get('n_samples', 0),
            'module': self.module_name
        }

if __name__ == "__main__":
    calibrator = ProbabilityCalibrator()
    print(f"[{calibrator.module_name}] Initialized successfully")
    print(f"[{calibrator.module_name}] ARENA calibration intelligence ready")