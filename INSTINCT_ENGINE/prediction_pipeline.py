"""
INSTINCT ENGINE — Prediction Pipeline
End-to-end prediction generation from features to calibrated probabilities.
EMPIRE SPORT INSTINCTS ARENA | Premium Predictive Pipeline
"""
import pandas as pd
import numpy as np
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

class PredictionPipeline:
    """End-to-end prediction pipeline for all sports

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard prediction generation from raw features to calibrated probabilities.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.trainer = None  # EmpireEnsembleTrainer
        self.uncertainty = None  # UncertaintyQuantifier
        self.value_detector = None  # ValueDetector
        self.calibrator = None  # ProbabilityCalibrator
        self.active_models = {}
        self.module_name = "INSTINCT ENGINE — Pipeline"

        # Lazy imports to avoid circular dependencies
        try:
            from EMPIRE_CORE.ensemble_trainer import EmpireEnsembleTrainer
            from EMPIRE_CORE.uncertainty_quantification import UncertaintyQuantifier
            from INSTINCT_ENGINE.value_detector import ValueDetector
            from INSTINCT_ENGINE.probability_calibrator import ProbabilityCalibrator

            self.trainer = EmpireEnsembleTrainer()
            self.uncertainty = UncertaintyQuantifier()
            self.value_detector = ValueDetector()
            self.calibrator = ProbabilityCalibrator()
            logger.info(f"[{self.module_name}] Pipeline initialized with all modules")
        except ImportError as e:
            logger.warning(f"[{self.module_name}] Some modules not available: {e}")

    def load_models(self, sport: str, model_path: str):
        """Load trained ARENA models for a sport"""
        if self.trainer:
            self.trainer.load_models(model_path, sport)
            self.active_models[sport] = True
            logger.info(f"[{self.module_name}] Loaded models for {sport} from {model_path}")
        else:
            logger.error(f"[{self.module_name}] Trainer not initialized")

    def generate_prediction(self, fixture_id: str, features: Dict, sport: str) -> Dict:
        """Generate complete ARENA prediction for a fixture"""
        if sport not in self.active_models:
            logger.error(f"[{self.module_name}] No active models for {sport}")
            return {'error': 'Models not loaded', 'module': self.module_name}

        if not self.trainer or not self.calibrator or not self.uncertainty:
            return {'error': 'modules_not_initialized', 'module': self.module_name}

        # Convert features to DataFrame
        feature_df = pd.DataFrame([features])

        # Remove metadata columns
        feature_cols = [c for c in feature_df.columns if c not in 
                       ['feature_version', 'computed_at', 'sport', 'engineer_module']]
        X = feature_df[feature_cols]

        # Generate ensemble prediction
        logger.info(f"[{self.module_name}] Generating prediction for {sport} fixture {fixture_id}")
        raw_prediction = self.trainer.predict(X, sport)

        if 'error' in raw_prediction:
            return raw_prediction

        # Calibrate probabilities
        probs = np.array(raw_prediction['probabilities'])
        calibrated_probs = self.calibrator.calibrate(probs, sport)

        # Calculate uncertainty
        uncertainty = self.uncertainty.calculate_uncertainty({
            'probabilities': calibrated_probs.tolist(),
            'confidence': raw_prediction['confidence']
        })

        # Build final ARENA prediction
        prediction = {
            'fixture_id': fixture_id,
            'sport': sport,
            'predicted_home_prob': float(calibrated_probs[0]) if len(calibrated_probs) > 0 else 0.33,
            'predicted_draw_prob': float(calibrated_probs[1]) if len(calibrated_probs) > 1 else 0.33,
            'predicted_away_prob': float(calibrated_probs[2]) if len(calibrated_probs) > 2 else 0.34,
            'confidence_score': raw_prediction['confidence'],
            'uncertainty_lower': uncertainty.get('lower_bound', [0])[0] if isinstance(uncertainty.get('lower_bound'), list) else uncertainty.get('lower_bound', 0),
            'uncertainty_upper': uncertainty.get('upper_bound', [1])[0] if isinstance(uncertainty.get('upper_bound'), list) else uncertainty.get('upper_bound', 1),
            'uncertainty_method': uncertainty.get('method', 'default'),
            'uncertainty_score': uncertainty.get('uncertainty_score', 0),
            'model_version': features.get('feature_version', 'unknown'),
            'computed_at': datetime.now().isoformat(),
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Prediction complete for {fixture_id} | Confidence: {prediction['confidence_score']:.2%} | Uncertainty: {prediction.get('uncertainty_score', 0):.4f}")
        return prediction

    def batch_predict(self, fixtures: List[Dict], sport: str) -> List[Dict]:
        """Generate ARENA predictions for multiple fixtures"""
        predictions = []
        logger.info(f"[{self.module_name}] Batch prediction: {len(fixtures)} fixtures for {sport}")

        for fixture in fixtures:
            pred = self.generate_prediction(
                fixture['fixture_id'],
                fixture['features'],
                sport
            )
            predictions.append(pred)

        logger.info(f"[{self.module_name}] Batch complete: {len(predictions)} predictions generated")
        return predictions

    def evaluate_predictions(self, predictions: List[Dict], outcomes: List[int], sport: str) -> Dict:
        """Evaluate ARENA prediction accuracy"""
        from sklearn.metrics import log_loss, accuracy_score, brier_score_loss

        probs = np.array([p['predicted_home_prob'] for p in predictions])
        y_true = np.array(outcomes)

        metrics = {
            'log_loss': float(log_loss(y_true, probs)),
            'accuracy': float(accuracy_score(y_true, (probs > 0.5).astype(int))),
            'brier_score': float(brier_score_loss(y_true, probs)),
            'n_predictions': len(predictions),
            'sport': sport,
            'evaluated_at': datetime.now().isoformat(),
            'module': self.module_name
        }

        logger.info(f"[{self.module_name}] Evaluation: {metrics['n_predictions']} preds | Acc: {metrics['accuracy']:.2%} | LogLoss: {metrics['log_loss']:.4f}")
        return metrics

    def get_pipeline_status(self) -> Dict:
        """Get ARENA pipeline status"""
        return {
            'trainer_loaded': self.trainer is not None,
            'calibrator_loaded': self.calibrator is not None,
            'uncertainty_loaded': self.uncertainty is not None,
            'value_detector_loaded': self.value_detector is not None,
            'active_models': list(self.active_models.keys()),
            'module': self.module_name,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    pipeline = PredictionPipeline()
    print(f"[{pipeline.module_name}] Initialized successfully")
    print(f"[{pipeline.module_name}] ARENA predictive intelligence ready")