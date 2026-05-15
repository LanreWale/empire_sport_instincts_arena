"""
EMPIRE TESTING — Walk-Forward Analysis
Rigorous backtesting with temporal cross-validation.
EMPIRE SPORT INSTINCTS ARENA | Premium Backtesting Intelligence
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import logging

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss, roc_auc_score

# Premium gold-themed logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class WalkForwardTester:
    """Performs walk-forward analysis for ARENA model validation

    Part of the EMPIRE SPORT INSTINCTS ARENA ecosystem.
    Provides gold-standard temporal cross-validation for all models.
    """

    def __init__(self, n_splits: int = 5, min_train_size: int = 100):
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.results = []
        self.module_name = "EMPIRE TESTING — Walk-Forward"
        logger.info(f"[{self.module_name}] Tester initialized | Splits: {n_splits} | Min train: {min_train_size}")

    def run_walk_forward(self, X: pd.DataFrame, y: pd.Series, 
                         model_class, model_params: Dict = None) -> Dict:
        """Run premium walk-forward validation"""
        logger.info(f"[{self.module_name}] Starting walk-forward analysis | Samples: {len(X)} | Features: {X.shape[1]}")

        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        fold_results = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            if len(train_idx) < self.min_train_size:
                logger.warning(f"[{self.module_name}] Fold {fold}: Insufficient training data ({len(train_idx)} < {self.min_train_size})")
                continue

            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            # Train model
            model = model_class(**(model_params or {}))
            model.fit(X_train, y_train)

            # Predict
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)

            # Calculate metrics
            metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
            metrics['fold'] = fold
            metrics['train_size'] = len(train_idx)
            metrics['test_size'] = len(test_idx)

            fold_results.append(metrics)
            logger.info(f"[{self.module_name}] Fold {fold}: Accuracy={metrics['accuracy']:.2%} | LogLoss={metrics['log_loss']:.4f} | Train={len(train_idx)} | Test={len(test_idx)}")

        # Aggregate results
        aggregated = self._aggregate_results(fold_results)

        logger.info(f"[{self.module_name}] Walk-forward complete | Mean Acc: {aggregated.get('accuracy_mean', 0):.2%} | Mean LogLoss: {aggregated.get('log_loss_mean', 0):.4f}")

        return {
            'fold_results': fold_results,
            'aggregated': aggregated,
            'n_splits': self.n_splits,
            'total_samples': len(X),
            'module': self.module_name,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_metrics(self, y_true, y_pred, y_pred_proba) -> Dict:
        """Calculate comprehensive ARENA metrics"""
        metrics = {
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'log_loss': float(log_loss(y_true, y_pred_proba)),
        }

        if len(np.unique(y_true)) == 2:
            metrics['roc_auc'] = float(roc_auc_score(y_true, y_pred_proba[:, 1]))
            metrics['brier_score'] = float(brier_score_loss(y_true, y_pred_proba[:, 1]))

        return metrics

    def _aggregate_results(self, fold_results: List[Dict]) -> Dict:
        """Aggregate metrics across folds"""
        if not fold_results:
            return {}

        metrics_keys = ['accuracy', 'log_loss', 'roc_auc', 'brier_score']
        aggregated = {}

        for key in metrics_keys:
            values = [f[key] for f in fold_results if key in f]
            if values:
                aggregated[f'{key}_mean'] = float(np.mean(values))
                aggregated[f'{key}_std'] = float(np.std(values))
                aggregated[f'{key}_min'] = float(np.min(values))
                aggregated[f'{key}_max'] = float(np.max(values))

        return aggregated

    def generate_report(self, results: Dict) -> str:
        """Generate premium ARENA backtest report"""
        agg = results['aggregated']

        report = f"""
╔══════════════════════════════════════════════════════════╗
║  EMPIRE SPORT INSTINCTS ARENA — WALK-FORWARD REPORT      ║
╠══════════════════════════════════════════════════════════╣
║  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                          ║
║  Total Samples: {results['total_samples']:<45}║
║  Number of Folds: {results['n_splits']:<43}║
╠══════════════════════════════════════════════════════════╣
║  AGGREGATED METRICS                                      ║
╠══════════════════════════════════════════════════════════╣
"""

        for key, value in agg.items():
            label = key.replace('_', ' ').title()
            report += f"║  {label:<30} {value:>20.4f}  ║\n"

        report += """╠══════════════════════════════════════════════════════════╣
║  INTERPRETATION                                          ║
╠══════════════════════════════════════════════════════════╣
║  • Log Loss < 0.50  → Good calibration                   ║
║  • Accuracy > 52%   → Beats random (binary)              ║
║  • ROC-AUC > 0.55   → Some discriminative power          ║
║  • Brier Score < 0.25 → Well-calibrated probabilities    ║
╠══════════════════════════════════════════════════════════╣
║  RECOMMENDATION                                          ║
╠══════════════════════════════════════════════════════════╣
"""

        accuracy = agg.get('accuracy_mean', 0)
        logloss = agg.get('log_loss_mean', 1.0)

        if accuracy > 0.55 and logloss < 0.50:
            report += "║  ✅ Model shows promise. Proceed with paper trading.   ║\n"
        elif accuracy > 0.52:
            report += "║  ⚠️  Marginal edge. Consider feature improvements.     ║\n"
        else:
            report += "║  ❌ No significant edge. Do not deploy.                  ║\n"

        report += """╚══════════════════════════════════════════════════════════╝
"""

        logger.info(f"[{self.module_name}] Report generated | Accuracy: {accuracy:.2%} | Recommendation: {'PASS' if accuracy > 0.55 else 'REVIEW' if accuracy > 0.52 else 'FAIL'}")

        return report

    def get_test_summary(self, results: Dict) -> Dict:
        """Get ARENA test summary"""
        agg = results['aggregated']
        accuracy = agg.get('accuracy_mean', 0)

        return {
            'total_samples': results['total_samples'],
            'n_splits': results['n_splits'],
            'accuracy_mean': accuracy,
            'log_loss_mean': agg.get('log_loss_mean', 0),
            'roc_auc_mean': agg.get('roc_auc_mean', 0),
            'status': 'PASS' if accuracy > 0.55 else 'REVIEW' if accuracy > 0.52 else 'FAIL',
            'module': self.module_name,
            'timestamp': results.get('timestamp')
        }

if __name__ == "__main__":
    tester = WalkForwardTester()
    print(f"[{tester.module_name}] Initialized successfully")
    print(f"[{tester.module_name}] ARENA backtesting intelligence ready")