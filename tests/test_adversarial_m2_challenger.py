"""
FinTrustX — Milestone 2 Challenger Adversarial Empirical Verification Suite
Author: Challenger M2-1 (teamwork_preview_challenger_m2_1)

Adversarial tests covering:
1. Held-out test set dimension and applicant count (exactly 61,503).
2. Zero split contamination (disjoint indices, target stratification invariance, SK_ID_CURR exclusion).
3. Raw sklearn ROC-AUC recalculation (strictly > 0.7610 baseline, hitting ~0.7794).
4. Probability calibration and numerical validity (strictly bounded in [0.0, 1.0], no NaNs/Infs, low ECE and Brier score).
5. Threshold stability and monotonic properties across [0.10, 0.20, 0.30, 0.50, 0.70].
"""

import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from scipy.stats import mannwhitneyu

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"

TRAIN_PARQUET = DATA_DIR / "processed_train.parquet"
TEST_PARQUET = DATA_DIR / "processed_test.parquet"
XGBOOST_JOBLIB = MODEL_DIR / "xgboost.joblib"
FEATURE_NAMES_CSV = MODEL_DIR / "preprocessed_feature_names.csv"

BASELINE_ROC_AUC = 0.7610378899421779


class TestMilestone2AdversarialChallenger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[CHALLENGER M2-1] Loading test artifacts for adversarial verification...")
        assert TEST_PARQUET.exists(), f"Missing {TEST_PARQUET}"
        assert TRAIN_PARQUET.exists(), f"Missing {TRAIN_PARQUET}"
        assert XGBOOST_JOBLIB.exists(), f"Missing {XGBOOST_JOBLIB}"
        assert FEATURE_NAMES_CSV.exists(), f"Missing {FEATURE_NAMES_CSV}"

        cls.df_test = pd.read_parquet(TEST_PARQUET)
        cls.df_train = pd.read_parquet(TRAIN_PARQUET)
        cls.model = joblib.load(XGBOOST_JOBLIB)
        cls.feat_names = pd.read_csv(FEATURE_NAMES_CSV).iloc[:, 0].tolist()

        cls.X_test = cls.df_test.drop(columns=["TARGET"])
        cls.y_test = cls.df_test["TARGET"].astype(int).values
        cls.X_train = cls.df_train.drop(columns=["TARGET"])
        cls.y_train = cls.df_train["TARGET"].astype(int).values

        # Generate predictions once
        cls.probs_all = cls.model.predict_proba(cls.X_test)
        cls.probs_pos = cls.probs_all[:, 1]

    def test_01_applicant_counts_and_dimensions(self):
        """Verify exact held-out test applicant count is 61,503 and train is 246,008."""
        self.assertEqual(len(self.df_test), 61503, "Test set row count must be exactly 61,503")
        self.assertEqual(len(self.df_train), 246008, "Train set row count must be exactly 246,008")
        self.assertEqual(
            len(self.df_test) + len(self.df_train),
            307511,
            "Total dataset row count must be exactly 307,511",
        )
        self.assertEqual(self.df_test.shape[1], 342, "Test dataset must have 342 columns (341 features + TARGET)")
        self.assertEqual(self.df_train.shape[1], 342, "Train dataset must have 342 columns (341 features + TARGET)")
        self.assertEqual(len(self.feat_names), 341, "Feature names count must be 341")

    def test_02_zero_split_contamination(self):
        """Verify zero index intersection, target stratification, and absence of ID leakage."""
        train_idx = set(self.df_train.index)
        test_idx = set(self.df_test.index)
        intersection = train_idx.intersection(test_idx)
        self.assertEqual(len(intersection), 0, f"Split contamination! Found {len(intersection)} overlapping indices")

        # Stratification invariance
        train_default_rate = self.y_train.mean()
        test_default_rate = self.y_test.mean()
        self.assertAlmostEqual(train_default_rate, test_default_rate, places=4)
        self.assertEqual(int(self.y_test.sum()), 4965, "Test set must contain exactly 4,965 defaults")
        self.assertEqual(int(self.y_train.sum()), 19860, "Train set must contain exactly 19,860 defaults")

        # Identifier exclusion
        self.assertNotIn("SK_ID_CURR", self.X_test.columns)
        self.assertNotIn("SK_ID_CURR", self.feat_names)

    def test_03_recalculate_roc_auc_raw_sklearn(self):
        """Independently recalculate ROC-AUC using sklearn.metrics.roc_auc_score directly."""
        raw_auc = roc_auc_score(self.y_test, self.probs_pos)

        # Confirm strictly greater than baseline
        self.assertGreater(
            raw_auc,
            BASELINE_ROC_AUC,
            f"Adversarial verification failed: ROC-AUC ({raw_auc:.6f}) <= baseline ({BASELINE_ROC_AUC:.6f})",
        )
        self.assertGreater(
            raw_auc,
            0.7750,
            f"Model did not reach expected target threshold of 0.7750: got {raw_auc:.6f}",
        )
        self.assertAlmostEqual(raw_auc, 0.779383, places=5)

        # Cross-validate with trapezoidal integration of ROC curve
        fpr, tpr, _ = roc_curve(self.y_test, self.probs_pos)
        auc_trapz = np.trapezoid(tpr, fpr)
        self.assertAlmostEqual(raw_auc, auc_trapz, places=7)

        # Cross-validate with Mann-Whitney U statistic
        pos_scores = self.probs_pos[self.y_test == 1]
        neg_scores = self.probs_pos[self.y_test == 0]
        u_stat, _ = mannwhitneyu(pos_scores, neg_scores, alternative="greater")
        auc_mwu = u_stat / (len(pos_scores) * len(neg_scores))
        self.assertAlmostEqual(raw_auc, auc_mwu, places=7)

    def test_04_probability_calibration_and_bounds(self):
        """Verify output probabilities are strictly in [0.0, 1.0], no NaN/Inf, and well-calibrated."""
        self.assertFalse(np.isnan(self.probs_pos).any(), "NaN found in predicted probabilities")
        self.assertFalse(np.isinf(self.probs_pos).any(), "Inf found in predicted probabilities")
        self.assertTrue(
            (self.probs_pos >= 0.0).all() and (self.probs_pos <= 1.0).all(),
            "Probabilities outside [0.0, 1.0] domain",
        )

        min_p = float(self.probs_pos.min())
        max_p = float(self.probs_pos.max())
        self.assertGreaterEqual(min_p, 0.0)
        self.assertLessEqual(max_p, 1.0)
        self.assertGreater(min_p, 0.0, "Extreme zero probability detected")
        self.assertLess(max_p, 0.99, "Overconfident 1.0 prediction detected")

        # Brier score check
        brier = brier_score_loss(self.y_test, self.probs_pos)
        self.assertLess(brier, 0.07, f"Brier score {brier:.6f} exceeds acceptable limit 0.07")

        # Expected Calibration Error (ECE - 10 uniform bins)
        bins = np.linspace(0, 1, 11)
        bin_indices = np.digitize(self.probs_pos, bins) - 1
        ece = 0.0
        for b in range(10):
            mask = bin_indices == b
            if np.sum(mask) > 0:
                bin_acc = np.mean(self.y_test[mask])
                bin_conf = np.mean(self.probs_pos[mask])
                bin_weight = np.sum(mask) / len(self.probs_pos)
                ece += bin_weight * np.abs(bin_acc - bin_conf)

        self.assertLess(ece, 0.02, f"ECE {ece:.6f} exceeds 2%")

    def test_05_threshold_stability_and_monotonicity(self):
        """Test threshold stability and monotonic characteristics across [0.10, 0.20, 0.30, 0.50, 0.70]."""
        thresholds = [0.10, 0.20, 0.30, 0.50, 0.70]
        recalls = []
        specificities = []
        precisions = []

        for t in thresholds:
            preds = (self.probs_pos >= t).astype(int)
            tn, fp, fn, tp = confusion_matrix(self.y_test, preds).ravel()
            prec = precision_score(self.y_test, preds, zero_division=0)
            rec = recall_score(self.y_test, preds, zero_division=0)
            spec = tn / (tn + fp)

            recalls.append(rec)
            specificities.append(spec)
            precisions.append(prec)

            # Sanity checks
            self.assertEqual(tp + fp + tn + fn, 61503)
            self.assertGreater(tp + fp, 0, f"No positive predictions at threshold {t}")

        # Check monotonic trends
        for i in range(len(thresholds) - 1):
            self.assertGreaterEqual(
                recalls[i],
                recalls[i + 1],
                f"Recall failed monotonicity: {recalls[i]} < {recalls[i + 1]} at {thresholds[i]} -> {thresholds[i + 1]}",
            )
            self.assertLessEqual(
                specificities[i],
                specificities[i + 1],
                f"Specificity failed monotonicity: {specificities[i]} > {specificities[i + 1]} at {thresholds[i]} -> {thresholds[i + 1]}",
            )
            self.assertLessEqual(
                precisions[i],
                precisions[i + 1],
                f"Precision failed monotonicity: {precisions[i]} > {precisions[i + 1]} at {thresholds[i]} -> {thresholds[i + 1]}",
            )


if __name__ == "__main__":
    unittest.main()
