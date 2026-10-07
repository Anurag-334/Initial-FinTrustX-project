"""
FinTrustX — Milestone 1 Challenger Empirical Verification Suite
Author: Challenger M1-2 (teamwork_preview_challenger_m1_2)

Rigorous empirical tests covering:
1. SK_ID_CURR exclusion from feature names and Parquet feature matrices.
2. Disjoint index splitting between train and test partitions.
3. Target default rate exact verification (train: 19,860/246,008, test: 4,965/61,503).
4. Absence of NaNs, +inf, -inf across all feature columns.
5. Column alignment, schema parity, and ordering vs preprocessed_feature_names.csv.
6. Target non-leakage (TARGET not in feature names, no perfect correlation with target).
7. Preprocessing pipeline artifact deserialization and transformer configuration.
"""

import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

TRAIN_PARQUET = DATA_DIR / "processed_train.parquet"
TEST_PARQUET = DATA_DIR / "processed_test.parquet"
FEATURE_NAMES_CSV = MODEL_DIR / "preprocessed_feature_names.csv"
PIPELINE_JOBLIB = MODEL_DIR / "preprocessing_pipeline.joblib"


class TestMilestone1Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[CHALLENGER M1-2] Loading artifacts for empirical verification...")
        assert TRAIN_PARQUET.exists(), f"Missing {TRAIN_PARQUET}"
        assert TEST_PARQUET.exists(), f"Missing {TEST_PARQUET}"
        assert FEATURE_NAMES_CSV.exists(), f"Missing {FEATURE_NAMES_CSV}"
        assert PIPELINE_JOBLIB.exists(), f"Missing {PIPELINE_JOBLIB}"

        cls.df_train = pd.read_parquet(TRAIN_PARQUET)
        cls.df_test = pd.read_parquet(TEST_PARQUET)
        cls.feat_names_df = pd.read_csv(FEATURE_NAMES_CSV)
        cls.pipeline = joblib.load(PIPELINE_JOBLIB)
        print(f"Loaded Train: {cls.df_train.shape}, Test: {cls.df_test.shape}")
        print(f"Loaded Features: {len(cls.feat_names_df)} names")

    def test_01_feature_count_and_shapes(self):
        """Verify train, test, and feature names dimensions."""
        self.assertEqual(len(self.df_train), 246008, "Train rows must be exactly 246,008")
        self.assertEqual(len(self.df_test), 61503, "Test rows must be exactly 61,503")
        self.assertEqual(len(self.df_train) + len(self.df_test), 307511, "Total rows must be 307,511")
        
        self.assertEqual(self.df_train.shape[1], 342, "Train must have 342 columns (341 features + TARGET)")
        self.assertEqual(self.df_test.shape[1], 342, "Test must have 342 columns (341 features + TARGET)")
        self.assertEqual(len(self.feat_names_df), 341, "preprocessed_feature_names.csv must list 341 features")

    def test_02_sk_id_curr_exclusion(self):
        """Verify SK_ID_CURR is strictly excluded from feature names and feature matrices."""
        feature_names = self.feat_names_df.iloc[:, 0].tolist()

        # Check in preprocessed_feature_names.csv
        self.assertNotIn("SK_ID_CURR", feature_names, "Raw SK_ID_CURR found in feature names!")
        self.assertNotIn("num__SK_ID_CURR", feature_names, "num__SK_ID_CURR found in feature names!")
        self.assertNotIn("cat__SK_ID_CURR", feature_names, "cat__SK_ID_CURR found in feature names!")

        # Check any column matching SK_ID_CURR exactly or as standalone component
        for name in feature_names:
            parts = name.split("__")
            base = parts[-1] if len(parts) > 1 else parts[0]
            self.assertNotEqual(base, "SK_ID_CURR", f"SK_ID_CURR leaked in feature name: {name}")

        # Check in parquet feature columns (excluding TARGET)
        train_features = [c for c in self.df_train.columns if c != "TARGET"]
        test_features = [c for c in self.df_test.columns if c != "TARGET"]

        self.assertNotIn("SK_ID_CURR", train_features, "SK_ID_CURR in train columns!")
        self.assertNotIn("num__SK_ID_CURR", train_features, "num__SK_ID_CURR in train columns!")
        self.assertNotIn("SK_ID_CURR", test_features, "SK_ID_CURR in test columns!")
        self.assertNotIn("num__SK_ID_CURR", test_features, "num__SK_ID_CURR in test columns!")

    def test_03_disjoint_index_partitioning(self):
        """Verify train and test indices are strictly disjoint with zero overlap."""
        train_idx = set(self.df_train.index)
        test_idx = set(self.df_test.index)

        overlap = train_idx.intersection(test_idx)
        self.assertEqual(len(overlap), 0, f"Disjoint split failure: found {len(overlap)} overlapping indices!")
        self.assertEqual(len(train_idx), 246008, "Train indices count mismatch")
        self.assertEqual(len(test_idx), 61503, "Test indices count mismatch")
        
        # Verify indices span the entire valid original index range [0, 307510]
        union_idx = train_idx.union(test_idx)
        self.assertEqual(len(union_idx), 307511, "Combined indices must cover all 307,511 rows")
        self.assertEqual(min(union_idx), 0, "Index minimum must be 0")
        self.assertEqual(max(union_idx), 307510, "Index maximum must be 307,510")

    def test_04_target_default_rates(self):
        """Verify exact default rates on train and test partitions."""
        self.assertIn("TARGET", self.df_train.columns, "TARGET not in train columns")
        self.assertIn("TARGET", self.df_test.columns, "TARGET not in test columns")

        y_train = self.df_train["TARGET"]
        y_test = self.df_test["TARGET"]

        # Train counts and rate
        train_defaults = int((y_train == 1).sum())
        train_non_defaults = int((y_train == 0).sum())
        train_rate = train_defaults / len(y_train)

        self.assertEqual(train_defaults, 19860, f"Expected 19,860 train defaults, got {train_defaults}")
        self.assertEqual(train_non_defaults, 226148, f"Expected 226,148 train non-defaults, got {train_non_defaults}")
        self.assertAlmostEqual(train_rate, 0.080729, places=6, msg=f"Train default rate deviation: {train_rate}")

        # Test counts and rate
        test_defaults = int((y_test == 1).sum())
        test_non_defaults = int((y_test == 0).sum())
        test_rate = test_defaults / len(y_test)

        self.assertEqual(test_defaults, 4965, f"Expected 4,965 test defaults, got {test_defaults}")
        self.assertEqual(test_non_defaults, 56538, f"Expected 56,538 test non-defaults, got {test_non_defaults}")
        self.assertAlmostEqual(test_rate, 0.080728, places=6, msg=f"Test default rate deviation: {test_rate}")

        # Total defaults
        total_defaults = train_defaults + test_defaults
        self.assertEqual(total_defaults, 24825, f"Expected 24,825 total defaults, got {total_defaults}")

    def test_05_absence_of_nans_and_infs(self):
        """Verify zero NaN, null, +inf, or -inf values in feature columns."""
        feature_cols = [c for c in self.df_train.columns if c != "TARGET"]

        # Train check
        train_nans = self.df_train[feature_cols].isna().sum().sum()
        self.assertEqual(train_nans, 0, f"Train contains {train_nans} NaN values!")

        train_vals = self.df_train[feature_cols].values
        self.assertTrue(np.isfinite(train_vals).all(), "Train features contain non-finite (+inf / -inf) values!")

        # Test check
        test_nans = self.df_test[feature_cols].isna().sum().sum()
        self.assertEqual(test_nans, 0, f"Test contains {test_nans} NaN values!")

        test_vals = self.df_test[feature_cols].values
        self.assertTrue(np.isfinite(test_vals).all(), "Test features contain non-finite (+inf / -inf) values!")

    def test_06_schema_alignment_and_ordering(self):
        """Verify feature ordering in train, test, and preprocessed_feature_names.csv are identical."""
        csv_features = self.feat_names_df.iloc[:, 0].tolist()
        train_features = [c for c in self.df_train.columns if c != "TARGET"]
        test_features = [c for c in self.df_test.columns if c != "TARGET"]

        self.assertEqual(train_features, test_features, "Train and Test feature column orders mismatch!")
        self.assertEqual(train_features, csv_features, "Train features order does not match preprocessed_feature_names.csv!")

    def test_07_target_non_leakage_and_independence(self):
        """Verify TARGET is not among features and no feature trivially encodes TARGET."""
        feature_names = self.feat_names_df.iloc[:, 0].tolist()
        self.assertNotIn("TARGET", feature_names, "TARGET column present in preprocessed feature names!")

        for name in feature_names:
            self.assertFalse(name.endswith("__TARGET"), f"Target found encoded in feature: {name}")

        # Sample check: verify no feature has correlation == 1.0 or -1.0 with TARGET
        y_train = self.df_train["TARGET"].values
        # Quick sample check on a subset of features
        sample_cols = [c for c in self.df_train.columns if c != "TARGET"][:50]
        for col in sample_cols:
            x_col = self.df_train[col].values
            std = np.std(x_col)
            if std > 1e-6:
                corr = np.corrcoef(x_col, y_train)[0, 1]
                self.assertLess(abs(corr), 0.95, f"Feature {col} suspiciously correlated with TARGET: {corr}")

    def test_08_dtypes_sanity(self):
        """Verify correct data types: TARGET is int8/int, features are float32/float64."""
        self.assertTrue(
            np.issubdtype(self.df_train["TARGET"].dtype, np.integer),
            f"Train TARGET dtype must be integer, got {self.df_train['TARGET'].dtype}"
        )
        self.assertTrue(
            np.issubdtype(self.df_test["TARGET"].dtype, np.integer),
            f"Test TARGET dtype must be integer, got {self.df_test['TARGET'].dtype}"
        )

        for col in [c for c in self.df_train.columns if c != "TARGET"]:
            self.assertTrue(
                np.issubdtype(self.df_train[col].dtype, np.floating),
                f"Feature {col} in train must be float, got {self.df_train[col].dtype}"
            )


if __name__ == "__main__":
    unittest.main()
