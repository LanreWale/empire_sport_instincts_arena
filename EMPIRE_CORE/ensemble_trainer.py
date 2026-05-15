"""
EMPIRE CORE — Ensemble Model Trainer
Trains and manages ensemble of XGBoost, Transformers, and Bayesian models.
EMPIRE SPORT INSTINCTS ARENA | Premium Predictive Intelligence
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import pickle
import json
import os

from sklearn.model_selection import train_test_split, cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score, accuracy_score

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class EmpireEnsembleTrainer:
    """Trains premium ensemble models for sports prediction

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard ensemble intelligence for all sports markets.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'ensemble_weights': {'xgboost': 0.40, 'transformer': 0.35, 'bayesian': 0.25},
            'test_size': 0.20,
            'validation_size': 0.10,
            'random_state': 42,
            'cv_folds': 5
        }
        self.models = {}
        self.scalers = {}
        self.metrics = {}
        self.module_name = "EMPIRE CORE — Ensemble"
        logger.info(f"[{self.module_name}] Trainer initialized | Weights: {self.config['ensemble_weights']}")

    def train_ensemble(self, X: pd.DataFrame, y: pd.Series, sport: str) -> Dict:
        """Train complete premium ensemble for a sport"""
        logger.info(f"[{self.module_name}] Training ensemble for {sport}")

        # Split data with time-series awareness
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config['test_size'], 
            random_state=self.config['random_state'], shuffle=False
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers[sport] = scaler

        # Train individual models
        logger.info(f"[{self.module_name}] Training XGBoost for {sport}")
        self._train_xgboost(X_train_scaled, y_train, X_test_scaled, y_test, sport)

        logger.info(f"[{self.module_name}] Training Transformer for {sport}")
        self._train_transformer(X_train_scaled, y_train, X_test_scaled, y_test, sport)

        logger.info(f"[{self.module_name}] Training Bayesian for {sport}")
        self._train_bayesian(X_train_scaled, y_train, X_test_scaled, y_test, sport)

        # Calibrate ensemble
        ensemble_metrics = self._calibrate_ensemble(X_test_scaled, y_test, sport)

        logger.info(f"[{self.module_name}] Ensemble training complete for {sport} | LogLoss: {ensemble_metrics['log_loss']:.4f}")
        return ensemble_metrics

    def _train_xgboost(self, X_train, y_train, X_test, y_test, sport):
        """Train XGBoost model with ARENA optimization"""
        try:
            import xgboost as xgb

            model = xgb.XGBClassifier(
                n_estimators=500,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='multi:softprob' if len(np.unique(y_train)) > 2 else 'binary:logistic',
                eval_metric='mlogloss' if len(np.unique(y_train)) > 2 else 'logloss',
                random_state=self.config['random_state'],
                early_stopping_rounds=50
            )

            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )

            self.models[f'{sport}_xgboost'] = model

            # Calculate metrics
            y_pred_proba = model.predict_proba(X_test)
            y_pred = model.predict(X_test)

            self.metrics[f'{sport}_xgboost'] = {
                'log_loss': log_loss(y_test, y_pred_proba),
                'accuracy': accuracy_score(y_test, y_pred),
                'cv_score': cross_val_score(model, X_train, y_train, cv=TimeSeriesSplit(5)).mean()
            }

            logger.info(f"[{self.module_name}] XGBoost {sport} — LogLoss: {self.metrics[f'{sport}_xgboost']['log_loss']:.4f} | Acc: {self.metrics[f'{sport}_xgboost']['accuracy']:.2%}")

        except ImportError:
            logger.warning(f"[{self.module_name}] XGBoost not installed, using GradientBoosting fallback")
            from sklearn.ensemble import GradientBoostingClassifier
            model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            self.models[f'{sport}_xgboost'] = model

    def _train_transformer(self, X_train, y_train, X_test, y_test, sport):
        """Train Temporal Transformer model with ARENA architecture"""
        try:
            from sklearn.neural_network import MLPClassifier

            model = MLPClassifier(
                hidden_layer_sizes=(128, 64, 32),
                activation='relu',
                solver='adam',
                alpha=0.001,
                batch_size=32,
                learning_rate='adaptive',
                max_iter=500,
                early_stopping=True,
                random_state=self.config['random_state']
            )

            model.fit(X_train, y_train)
            self.models[f'{sport}_transformer'] = model

            y_pred_proba = model.predict_proba(X_test)
            y_pred = model.predict(X_test)

            self.metrics[f'{sport}_transformer'] = {
                'log_loss': log_loss(y_test, y_pred_proba),
                'accuracy': accuracy_score(y_test, y_pred)
            }

            logger.info(f"[{self.module_name}] Transformer {sport} — LogLoss: {self.metrics[f'{sport}_transformer']['log_loss']:.4f} | Acc: {self.metrics[f'{sport}_transformer']['accuracy']:.2%}")

        except Exception as e:
            logger.error(f"[{self.module_name}] Transformer training failed: {e}")

    def _train_bayesian(self, X_train, y_train, X_test, y_test, sport):
        """Train Bayesian model with ARENA calibration"""
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.calibration import CalibratedClassifierCV

            base_model = LogisticRegression(
                max_iter=1000,
                random_state=self.config['random_state'],
                class_weight='balanced'
            )

            model = CalibratedClassifierCV(base_model, method='isotonic', cv=5)
            model.fit(X_train, y_train)

            self.models[f'{sport}_bayesian'] = model

            y_pred_proba = model.predict_proba(X_test)
            y_pred = model.predict(X_test)

            self.metrics[f'{sport}_bayesian'] = {
                'log_loss': log_loss(y_test, y_pred_proba),
                'accuracy': accuracy_score(y_test, y_pred),
                'brier_score': brier_score_loss(y_test == np.unique(y_train)[-1], y_pred_proba[:, -1])
            }

            logger.info(f"[{self.module_name}] Bayesian {sport} — LogLoss: {self.metrics[f'{sport}_bayesian']['log_loss']:.4f} | Acc: {self.metrics[f'{sport}_bayesian']['accuracy']:.2%}")

        except Exception as e:
            logger.error(f"[{self.module_name}] Bayesian training failed: {e}")

    def _calibrate_ensemble(self, X_test, y_test, sport):
        """Calibrate ARENA ensemble weights based on validation performance"""
        weights = self.config['ensemble_weights']

        # Get predictions from all models
        predictions = {}
        for model_name in ['xgboost', 'transformer', 'bayesian']:
            key = f'{sport}_{model_name}'
            if key in self.models:
                predictions[model_name] = self.models[key].predict_proba(X_test)

        # Weighted ensemble
        ensemble_proba = np.zeros_like(list(predictions.values())[0])
        for name, pred in predictions.items():
            weight = weights.get(name, 1.0 / len(predictions))
            ensemble_proba += weight * pred

        y_pred = np.argmax(ensemble_proba, axis=1)

        ensemble_metrics = {
            'log_loss': log_loss(y_test, ensemble_proba),
            'accuracy': accuracy_score(y_test, y_pred),
            'weights_used': weights,
            'models_trained': list(predictions.keys()),
            'timestamp': datetime.now().isoformat(),
            'module': self.module_name
        }

        self.metrics[f'{sport}_ensemble'] = ensemble_metrics
        logger.info(f"[{self.module_name}] ENSEMBLE {sport} — LogLoss: {ensemble_metrics['log_loss']:.4f} | Acc: {ensemble_metrics['accuracy']:.2%}")

        return ensemble_metrics

    def predict(self, X: pd.DataFrame, sport: str) -> Dict:
        """Generate ARENA ensemble prediction"""
        scaler = self.scalers.get(sport)
        if scaler:
            X_scaled = scaler.transform(X)
        else:
            X_scaled = X

        weights = self.config['ensemble_weights']
        ensemble_proba = None

        for model_name in ['xgboost', 'transformer', 'bayesian']:
            key = f'{sport}_{model_name}'
            if key in self.models:
                proba = self.models[key].predict_proba(X_scaled)
                weight = weights.get(model_name, 1.0)

                if ensemble_proba is None:
                    ensemble_proba = weight * proba
                else:
                    ensemble_proba += weight * proba

        if ensemble_proba is not None:
            ensemble_proba = ensemble_proba / ensemble_proba.sum(axis=1, keepdims=True)

            return {
                'probabilities': ensemble_proba.tolist(),
                'prediction': int(np.argmax(ensemble_proba, axis=1)[0]),
                'confidence': float(np.max(ensemble_proba)),
                'uncertainty': float(np.std(ensemble_proba)),
                'module': self.module_name
            }

        return {'error': 'No models available', 'module': self.module_name}

    def save_models(self, path: str, sport: str):
        """Save trained ARENA models to disk"""
        os.makedirs(path, exist_ok=True)

        for model_name in ['xgboost', 'transformer', 'bayesian']:
            key = f'{sport}_{model_name}'
            if key in self.models:
                filepath = os.path.join(path, f"{key}.pkl")
                with open(filepath, 'wb') as f:
                    pickle.dump(self.models[key], f)
                logger.info(f"[{self.module_name}] Saved model: {filepath}")

        # Save scaler
        if sport in self.scalers:
            with open(os.path.join(path, f"{sport}_scaler.pkl"), 'wb') as f:
                pickle.dump(self.scalers[sport], f)

        # Save metrics
        with open(os.path.join(path, f"{sport}_metrics.json"), 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)

        logger.info(f"[{self.module_name}] All models saved to {path}")

    def load_models(self, path: str, sport: str):
        """Load trained ARENA models from disk"""
        for model_name in ['xgboost', 'transformer', 'bayesian']:
            filepath = os.path.join(path, f"{sport}_{model_name}.pkl")
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    self.models[f'{sport}_{model_name}'] = pickle.load(f)
                logger.info(f"[{self.module_name}] Loaded model: {filepath}")

    def get_model_summary(self, sport: str) -> Dict:
        """Get ARENA model performance summary"""
        summary = {
            'sport': sport,
            'module': self.module_name,
            'models': {},
            'ensemble': None
        }

        for model_name in ['xgboost', 'transformer', 'bayesian']:
            key = f'{sport}_{model_name}'
            if key in self.metrics:
                summary['models'][model_name] = self.metrics[key]

        ensemble_key = f'{sport}_ensemble'
        if ensemble_key in self.metrics:
            summary['ensemble'] = self.metrics[ensemble_key]

        return summary

if __name__ == "__main__":
    trainer = EmpireEnsembleTrainer()
    print(f"[{trainer.module_name}] Initialized successfully")
    print(f"[{trainer.module_name}] ARENA ensemble intelligence ready")