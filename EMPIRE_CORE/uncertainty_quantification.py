"""
EMPIRE CORE — Uncertainty Quantification
Provides confidence intervals and uncertainty estimates for predictions.
EMPIRE SPORT INSTINCTS ARENA | Premium Confidence Intelligence
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from datetime import datetime
import logging

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class UncertaintyQuantifier:
    """Quantifies prediction uncertainty using multiple premium methods

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard confidence intervals for all predictions.
    """

    def __init__(self):
        self.methods = ['ensemble_disagreement', 'monte_carlo_dropout', 'bootstrap']
        self.module_name = "EMPIRE CORE — Uncertainty"
        logger.info(f"[{self.module_name}] Quantifier initialized | Methods: {self.methods}")

    def calculate_uncertainty(self, predictions: Dict, method: str = 'ensemble') -> Dict:
        """Calculate ARENA uncertainty bounds for predictions"""
        logger.info(f"[{self.module_name}] Calculating uncertainty using {method}")

        if method == 'ensemble':
            return self._ensemble_uncertainty(predictions)
        elif method == 'monte_carlo':
            return self._monte_carlo_uncertainty(predictions)
        elif method == 'bootstrap':
            return self._bootstrap_uncertainty(predictions)
        else:
            return self._default_uncertainty(predictions)

    def _ensemble_uncertainty(self, predictions: Dict) -> Dict:
        """Calculate uncertainty from ensemble disagreement"""
        model_probs = predictions.get('model_probabilities', [])

        if not model_probs:
            logger.warning(f"[{self.module_name}] No model probabilities found, using default")
            return {'lower': 0.0, 'upper': 1.0, 'method': 'default', 'module': self.module_name}

        # Calculate mean and std across models
        mean_prob = np.mean(model_probs, axis=0)
        std_prob = np.std(model_probs, axis=0)

        # 95% confidence interval
        lower = np.clip(mean_prob - 1.96 * std_prob, 0, 1)
        upper = np.clip(mean_prob + 1.96 * std_prob, 0, 1)

        uncertainty_score = float(np.mean(std_prob))

        logger.info(f"[{self.module_name}] Ensemble uncertainty: {uncertainty_score:.4f}")

        return {
            'mean_probability': mean_prob.tolist(),
            'std_deviation': std_prob.tolist(),
            'lower_bound': lower.tolist(),
            'upper_bound': upper.tolist(),
            'confidence_level': 0.95,
            'method': 'ensemble_disagreement',
            'uncertainty_score': uncertainty_score,
            'module': self.module_name
        }

    def _monte_carlo_uncertainty(self, predictions: Dict) -> Dict:
        """Monte Carlo dropout for neural network uncertainty"""
        logger.info(f"[{self.module_name}] Monte Carlo uncertainty requested")
        return {
            'method': 'monte_carlo_dropout',
            'note': 'Requires PyTorch implementation',
            'module': self.module_name
        }

    def _bootstrap_uncertainty(self, predictions: Dict) -> Dict:
        """Bootstrap resampling uncertainty"""
        n_bootstrap = 1000
        probs = predictions.get('probabilities', [])

        if not probs:
            return {'lower': 0.0, 'upper': 1.0, 'module': self.module_name}

        bootstrap_samples = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(probs, size=len(probs), replace=True)
            bootstrap_samples.append(np.mean(sample))

        lower = np.percentile(bootstrap_samples, 2.5)
        upper = np.percentile(bootstrap_samples, 97.5)

        logger.info(f"[{self.module_name}] Bootstrap uncertainty: [{lower:.4f}, {upper:.4f}]")

        return {
            'lower_bound': float(lower),
            'upper_bound': float(upper),
            'confidence_level': 0.95,
            'method': 'bootstrap',
            'bootstrap_samples': n_bootstrap,
            'module': self.module_name
        }

    def _default_uncertainty(self, predictions: Dict) -> Dict:
        """Default uncertainty when no method specified"""
        prob = predictions.get('confidence', 0.5)
        margin = (1 - prob) * 0.5

        return {
            'lower_bound': max(0, prob - margin),
            'upper_bound': min(1, prob + margin),
            'confidence_level': 0.68,
            'method': 'default_heuristic',
            'module': self.module_name
        }

    def calibrate_probabilities(self, predicted_probs: np.ndarray, 
                               true_outcomes: np.ndarray) -> np.ndarray:
        """Calibrate predicted probabilities using isotonic regression"""
        from sklearn.isotonic import IsotonicRegression

        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(predicted_probs, true_outcomes)
        calibrated = iso.predict(predicted_probs)

        logger.info(f"[{self.module_name}] Probabilities calibrated using isotonic regression")
        return calibrated

    def brier_decomposition(self, predicted_probs: np.ndarray, 
                           true_outcomes: np.ndarray) -> Dict:
        """Decompose Brier score into uncertainty, resolution, and reliability"""
        n = len(true_outcomes)

        # Uncertainty (inherent in outcomes)
        base_rate = np.mean(true_outcomes)
        uncertainty = base_rate * (1 - base_rate)

        # Resolution (how well predictions discriminate)
        unique_probs = np.unique(predicted_probs)
        resolution = 0
        for p in unique_probs:
            mask = predicted_probs == p
            if np.sum(mask) > 0:
                p_avg = np.mean(true_outcomes[mask])
                resolution += np.sum(mask) / n * (p_avg - base_rate) ** 2

        # Reliability (calibration)
        reliability = 0
        for p in unique_probs:
            mask = predicted_probs == p
            if np.sum(mask) > 0:
                p_avg = np.mean(true_outcomes[mask])
                reliability += np.sum(mask) / n * (p - p_avg) ** 2

        brier_score = uncertainty - resolution + reliability

        result = {
            'brier_score': float(brier_score),
            'uncertainty': float(uncertainty),
            'resolution': float(resolution),
            'reliability': float(reliability),
            'base_rate': float(base_rate),
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Brier decomposition: Score={brier_score:.4f} | Uncertainty={uncertainty:.4f} | Resolution={resolution:.4f}")
        return result

    def get_quantifier_stats(self) -> Dict:
        """Get ARENA uncertainty quantifier statistics"""
        return {
            'methods_available': self.methods,
            'default_method': 'ensemble',
            'module': self.module_name,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    quantifier = UncertaintyQuantifier()
    print(f"[{quantifier.module_name}] Initialized successfully")
    print(f"[{quantifier.module_name}] ARENA confidence intelligence ready")