"""
===========================================================
Adversarial Stress Test Suite for Milestone 1
===========================================================

Tests DataAggregator, DataLoader, Preprocessor, and Pipeline
against:
- Unlinked applicants (no bureau, no previous app, or both)
- Boundary values, zeros, and negative values in denominators
- Missingness flags correctness
- Empty inputs and duplicate key detection
- All-NaN records and unexpected categorical statuses
- Preprocessor imputation of merged edge cases (no Infs / NaNs)
===========================================================
"""

import numpy as np
import pandas as pd
import pytest

from src.data_aggregation import DataAggregator, optimize_dtypes
from src.preprocessing import DataPreprocessor


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def sample_main_df():
    """Create a minimal representative application_train dataframe."""
    return pd.DataFrame({
        "SK_ID_CURR": [1001, 1002, 1003, 1004],
        "TARGET": [0, 1, 0, 0],
        "AMT_INCOME_TOTAL": [150000.0, 200000.0, 100000.0, 0.0],
        "AMT_CREDIT": [500000.0, 800000.0, 300000.0, 100000.0],
        "AMT_ANNUITY": [25000.0, 40000.0, 15000.0, 5000.0],
        "NAME_CONTRACT_TYPE": ["Cash loans", "Cash loans", "Revolving loans", "Cash loans"],
        "CODE_GENDER": ["M", "F", "M", "F"],
    })


@pytest.fixture
def sample_bureau_df():
    """
    Bureau records:
    - 1001: 2 records (1 Active, 1 Closed)
    - 1002: 1 record (Active, with overdue debt)
    - 1004: 0 records (unlinked)
    - 1003: 0 records (unlinked)
    - 9999: orphan bureau record (not in main_df)
    """
    return pd.DataFrame({
        "SK_ID_CURR": [1001, 1001, 1002, 9999],
        "SK_ID_BUREAU": [5001, 5002, 5003, 5004],
        "CREDIT_ACTIVE": ["Active", "Closed", "Active", "Closed"],
        "CREDIT_TYPE": ["Consumer credit", "Credit card", "Microloan", "Consumer credit"],
        "DAYS_CREDIT": [-300, -1200, -150, -500],
        "CREDIT_DAY_OVERDUE": [0, 0, 15, 0],
        "DAYS_CREDIT_ENDDATE": [400.0, -200.0, 100.0, 0.0],
        "AMT_CREDIT_MAX_OVERDUE": [0.0, 5000.0, 2000.0, 0.0],
        "CNT_CREDIT_PROLONG": [0, 1, 0, 0],
        "AMT_CREDIT_SUM": [200000.0, 100000.0, 50000.0, 80000.0],
        "AMT_CREDIT_SUM_DEBT": [150000.0, 0.0, 40000.0, 0.0],
        "AMT_CREDIT_SUM_LIMIT": [0.0, 50000.0, 0.0, 0.0],
        "AMT_CREDIT_SUM_OVERDUE": [0.0, 0.0, 10000.0, 0.0],
        "DAYS_CREDIT_UPDATE": [-10, -500, -5, -200],
        "AMT_ANNUITY": [10000.0, np.nan, 3000.0, 5000.0],
    })


@pytest.fixture
def sample_prev_df():
    """
    Previous application records:
    - 1001: 2 records (1 Approved, 1 Refused)
    - 1003: 1 record (Approved)
    - 1002: 0 records (unlinked)
    - 1004: 0 records (unlinked)
    """
    return pd.DataFrame({
        "SK_ID_CURR": [1001, 1001, 1003],
        "SK_ID_PREV": [2001, 2002, 2003],
        "NAME_CONTRACT_STATUS": ["Approved", "Refused", "Approved"],
        "NAME_CONTRACT_TYPE": ["Consumer loans", "Cash loans", "Consumer loans"],
        "AMT_ANNUITY": [12000.0, 25000.0, 8000.0],
        "AMT_APPLICATION": [150000.0, 300000.0, 80000.0],
        "AMT_CREDIT": [140000.0, 300000.0, 80000.0],
        "AMT_DOWN_PAYMENT": [10000.0, 0.0, 0.0],
        "RATE_DOWN_PAYMENT": [0.07, 0.0, 0.0],
        "DAYS_DECISION": [-200, -500, -100],
        "CNT_PAYMENT": [12.0, 24.0, 10.0],
        "DAYS_TERMINATION": [-50.0, np.nan, -10.0],
    })


# ==========================================================
# Test Suite: Aggregation and Merging
# ==========================================================

class TestDataAggregatorAdversarial:
    """Stress tests for DataAggregator logic."""

    def test_unlinked_applicants_flags_and_counts(
        self, tmp_path, sample_main_df, sample_bureau_df, sample_prev_df
    ):
        """
        Verify that applicants with no bureau or previous application records
        are properly flagged and have count features safely zero-filled.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        sample_bureau_df.to_csv(raw_dir / "bureau.csv", index=False)
        sample_prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        bureau_agg = aggregator.aggregate_bureau()
        prev_agg = aggregator.aggregate_previous_application()
        merged = aggregator.merge_features(sample_main_df, bureau_agg, prev_agg)

        # Total rows preserved
        assert len(merged) == len(sample_main_df)
        assert merged["SK_ID_CURR"].tolist() == [1001, 1002, 1003, 1004]

        # 1001: Has both Bureau and Prev
        row_1001 = merged[merged["SK_ID_CURR"] == 1001].iloc[0]
        assert row_1001["FLAG_NO_BUREAU_DATA"] == 0
        assert row_1001["FLAG_NO_PREV_DATA"] == 0
        assert row_1001["BUREAU_LOAN_COUNT"] == 2
        assert row_1001["PREV_APP_COUNT"] == 2

        # 1002: Has Bureau only
        row_1002 = merged[merged["SK_ID_CURR"] == 1002].iloc[0]
        assert row_1002["FLAG_NO_BUREAU_DATA"] == 0
        assert row_1002["FLAG_NO_PREV_DATA"] == 1
        assert row_1002["BUREAU_LOAN_COUNT"] == 1
        assert row_1002["PREV_APP_COUNT"] == 0

        # 1003: Has Prev only
        row_1003 = merged[merged["SK_ID_CURR"] == 1003].iloc[0]
        assert row_1003["FLAG_NO_BUREAU_DATA"] == 1
        assert row_1003["FLAG_NO_PREV_DATA"] == 0
        assert row_1003["BUREAU_LOAN_COUNT"] == 0
        assert row_1003["PREV_APP_COUNT"] == 1

        # 1004: Completely unlinked (neither bureau nor prev)
        row_1004 = merged[merged["SK_ID_CURR"] == 1004].iloc[0]
        assert row_1004["FLAG_NO_BUREAU_DATA"] == 1
        assert row_1004["FLAG_NO_PREV_DATA"] == 1
        assert row_1004["BUREAU_LOAN_COUNT"] == 0
        assert row_1004["PREV_APP_COUNT"] == 0

        # Unlinked cross-table fallback
        # TOTAL_DEBT_TO_INCOME should safely compute: (AMT_CREDIT + 0) / (AMT_INCOME_TOTAL + 1.0)
        expected_total_dti_1004 = 100000.0 / (0.0 + 1.0)
        assert pytest.approx(row_1004["TOTAL_DEBT_TO_INCOME"]) == expected_total_dti_1004

    def test_zero_income_and_zero_credit_denominators(
        self, tmp_path, sample_main_df, sample_bureau_df, sample_prev_df
    ):
        """
        Ensure zero income (AMT_INCOME_TOTAL=0) and zero credit values
        do not trigger ZeroDivisionError or produce Infs.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        sample_bureau_df.to_csv(raw_dir / "bureau.csv", index=False)
        sample_prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        bureau_agg = aggregator.aggregate_bureau()
        prev_agg = aggregator.aggregate_previous_application()
        merged = aggregator.merge_features(sample_main_df, bureau_agg, prev_agg)

        # Check all numeric columns for +/- inf
        num_cols = merged.select_dtypes(include=["number"]).columns
        has_inf = np.isinf(merged[num_cols].values).any()
        assert not has_inf, "Found infinite values in merged features!"

    def test_all_refused_or_all_approved_prev_apps(self, tmp_path):
        """
        Boundary condition: applicant has ONLY refused or ONLY approved applications.
        Ensures ratios like PREV_APPROVAL_RATE, PREV_REFUSAL_RATE are valid [0, 1].
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        prev_df = pd.DataFrame({
            "SK_ID_CURR": [2001, 2002],
            "SK_ID_PREV": [3001, 3002],
            "NAME_CONTRACT_STATUS": ["Approved", "Refused"],
            "NAME_CONTRACT_TYPE": ["Cash loans", "Cash loans"],
            "AMT_ANNUITY": [1000.0, 2000.0],
            "AMT_APPLICATION": [10000.0, 20000.0],
            "AMT_CREDIT": [10000.0, 0.0],
            "AMT_DOWN_PAYMENT": [0.0, 0.0],
            "RATE_DOWN_PAYMENT": [0.0, 0.0],
            "DAYS_DECISION": [-10, -20],
            "CNT_PAYMENT": [12.0, 24.0],
            "DAYS_TERMINATION": [0.0, 0.0],
        })
        prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        prev_agg = aggregator.aggregate_previous_application()

        row_approved = prev_agg[prev_agg["SK_ID_CURR"] == 2001].iloc[0]
        row_refused = prev_agg[prev_agg["SK_ID_CURR"] == 2002].iloc[0]

        assert pytest.approx(row_approved["PREV_APPROVAL_RATE"], abs=1e-3) == 1.0
        assert pytest.approx(row_approved["PREV_REFUSAL_RATE"], abs=1e-3) == 0.0

        assert pytest.approx(row_refused["PREV_APPROVAL_RATE"], abs=1e-3) == 0.0
        assert pytest.approx(row_refused["PREV_REFUSAL_RATE"], abs=1e-3) == 1.0

    def test_duplicate_keys_detection(self, sample_main_df):
        """
        DataAggregator.merge_features must raise an exception if bureau_agg
        or prev_agg contains duplicate SK_ID_CURR keys.
        """
        aggregator = DataAggregator()
        dup_bureau = pd.DataFrame({
            "SK_ID_CURR": [1001, 1001],
            "BUREAU_SK_ID_BUREAU_COUNT": [1, 2],
        })
        valid_prev = pd.DataFrame({
            "SK_ID_CURR": [1001],
            "PREV_SK_ID_PREV_COUNT": [1],
        })

        with pytest.raises(ValueError, match="Duplicate SK_ID_CURR"):
            aggregator.merge_features(sample_main_df, dup_bureau, valid_prev)

    def test_empty_main_df_error(self):
        """merge_features must raise ValueError if main_df is empty."""
        aggregator = DataAggregator()
        empty_main = pd.DataFrame(columns=["SK_ID_CURR", "AMT_INCOME_TOTAL"])
        bureau = pd.DataFrame({"SK_ID_CURR": [1], "BUREAU_SK_ID_BUREAU_COUNT": [1]})
        prev = pd.DataFrame({"SK_ID_CURR": [1], "PREV_SK_ID_PREV_COUNT": [1]})

        with pytest.raises(ValueError, match="main_df is empty"):
            aggregator.merge_features(empty_main, bureau, prev)

    def test_all_nan_child_columns(self, tmp_path):
        """
        Adversarial case: Child table has valid SK_ID_CURR, but all feature
        columns are NaN. Aggregation must not crash.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        bureau_nan = pd.DataFrame({
            "SK_ID_CURR": [1001],
            "SK_ID_BUREAU": [5001],
            "CREDIT_ACTIVE": [np.nan],
            "CREDIT_TYPE": [np.nan],
            "DAYS_CREDIT": [np.nan],
            "CREDIT_DAY_OVERDUE": [np.nan],
            "DAYS_CREDIT_ENDDATE": [np.nan],
            "AMT_CREDIT_MAX_OVERDUE": [np.nan],
            "CNT_CREDIT_PROLONG": [np.nan],
            "AMT_CREDIT_SUM": [np.nan],
            "AMT_CREDIT_SUM_DEBT": [np.nan],
            "AMT_CREDIT_SUM_LIMIT": [np.nan],
            "AMT_CREDIT_SUM_OVERDUE": [np.nan],
            "DAYS_CREDIT_UPDATE": [np.nan],
            "AMT_ANNUITY": [np.nan],
        })
        bureau_nan.to_csv(raw_dir / "bureau.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        bureau_agg = aggregator.aggregate_bureau()

        assert len(bureau_agg) == 1
        assert bureau_agg["SK_ID_CURR"].iloc[0] == 1001
        assert not np.isinf(bureau_agg.select_dtypes(include="number").values).any()

    def test_unexpected_categorical_statuses(self, tmp_path):
        """
        Adversarial case: status columns contain unexpected or unknown categories.
        Status masks must evaluate safely to 0 without breaking.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        prev_df = pd.DataFrame({
            "SK_ID_CURR": [3001, 3002],
            "SK_ID_PREV": [4001, 4002],
            "NAME_CONTRACT_STATUS": ["Unused offer", "Alien_Status_XYZ"],
            "NAME_CONTRACT_TYPE": ["Unknown_Loan", "Cash loans"],
            "AMT_ANNUITY": [1000.0, 2000.0],
            "AMT_APPLICATION": [10000.0, 20000.0],
            "AMT_CREDIT": [10000.0, 20000.0],
            "AMT_DOWN_PAYMENT": [0.0, 0.0],
            "RATE_DOWN_PAYMENT": [0.0, 0.0],
            "DAYS_DECISION": [-10, -20],
            "CNT_PAYMENT": [12.0, 24.0],
            "DAYS_TERMINATION": [0.0, 0.0],
        })
        prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        prev_agg = aggregator.aggregate_previous_application()

        assert prev_agg["PREV_IS_APPROVED_SUM"].sum() == 0
        assert prev_agg["PREV_IS_REFUSED_SUM"].sum() == 0
        assert prev_agg["PREV_IS_CANCELED_SUM"].sum() == 0


# ==========================================================
# Test Suite: Preprocessor Handling of Adversarial Merges
# ==========================================================

class TestDataPreprocessorAdversarial:
    """Verify that DataPreprocessor transforms adversarially merged frames cleanly."""

    def test_preprocessor_handles_unlinked_applicants_without_nans_or_infs(
        self, tmp_path, sample_main_df, sample_bureau_df, sample_prev_df
    ):
        """
        When merged dataset contains unlinked applicants (lots of NaNs in bureau
        and prev columns), DataPreprocessor must:
        1. Impute all missing values (median for numeric, most_frequent for cat).
        2. Scale features with zero NaNs and zero Infs remaining.
        3. Exclude SK_ID_CURR from the feature matrix.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        sample_bureau_df.to_csv(raw_dir / "bureau.csv", index=False)
        sample_prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        bureau_agg = aggregator.aggregate_bureau()
        prev_agg = aggregator.aggregate_previous_application()
        merged = aggregator.merge_features(sample_main_df, bureau_agg, prev_agg)

        preprocessor = DataPreprocessor()
        num_cols, cat_cols = preprocessor.detect_features(
            merged,
            target_column="TARGET",
            exclude_columns=["SK_ID_CURR"],
        )

        assert "SK_ID_CURR" not in num_cols
        assert "SK_ID_CURR" not in cat_cols
        assert "TARGET" not in num_cols

        preprocessor.build_pipeline()
        x_processed = preprocessor.fit_transform(merged.drop(columns=["TARGET"]))

        # Check dimensions
        assert x_processed.shape[0] == len(merged)
        # Check no NaNs
        assert not np.isnan(x_processed).any(), "NaN found after fit_transform!"
        # Check no Infs
        assert np.isfinite(x_processed).all(), "Non-finite value found after fit_transform!"

    def test_preprocessor_frozen_transform_on_extreme_unseen_values(
        self, tmp_path, sample_main_df, sample_bureau_df, sample_prev_df
    ):
        """
        Test that a frozen fitted pipeline handles unseen test-set applicants
        with extreme outliers, all-zeros, or new categories without crashing.
        """
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        sample_bureau_df.to_csv(raw_dir / "bureau.csv", index=False)
        sample_prev_df.to_csv(raw_dir / "previous_application.csv", index=False)

        aggregator = DataAggregator(raw_data_dir=raw_dir)
        bureau_agg = aggregator.aggregate_bureau()
        prev_agg = aggregator.aggregate_previous_application()
        merged = aggregator.merge_features(sample_main_df, bureau_agg, prev_agg)

        preprocessor = DataPreprocessor()
        preprocessor.detect_features(
            merged, target_column="TARGET", exclude_columns=["SK_ID_CURR"]
        )
        preprocessor.build_pipeline()
        preprocessor.fit_transform(merged.drop(columns=["TARGET"]))

        # Construct extreme adversarial unseen test applicant
        extreme_applicant = merged.iloc[[0]].copy()
        extreme_applicant["SK_ID_CURR"] = 9999
        extreme_applicant["AMT_INCOME_TOTAL"] = 1e12  # trillionaire
        extreme_applicant["AMT_CREDIT"] = 1e14
        extreme_applicant["CODE_GENDER"] = "X_NON_BINARY"  # unseen category
        extreme_applicant["FLAG_NO_BUREAU_DATA"] = 1

        test_processed = preprocessor.transform(
            extreme_applicant.drop(columns=["TARGET"])
        )

        assert test_processed.shape[0] == 1
        assert not np.isnan(test_processed).any()
        assert np.isfinite(test_processed).all()


# ==========================================================
# Test Suite: Memory Optimization Function
# ==========================================================

class TestOptimizeDtypesAdversarial:
    """Test optimize_dtypes helper edge cases."""

    def test_optimize_dtypes_empty_dataframe(self):
        """optimize_dtypes must not raise error on empty dataframe."""
        empty_df = pd.DataFrame({
            "a": pd.Series(dtype="int64"),
            "b": pd.Series(dtype="float64"),
            "c": pd.Series(dtype="object"),
        })
        optimized = optimize_dtypes(empty_df)
        assert len(optimized) == 0

    def test_optimize_dtypes_all_nan_integer_like(self):
        """Float column with all NaNs remains float32 and doesn't crash."""
        df = pd.DataFrame({"col": [np.nan, np.nan, np.nan]})
        optimized = optimize_dtypes(df)
        assert optimized["col"].dtype == np.float32


# ==========================================================
# Test Suite: Real Pipeline Artifact Verification
# ==========================================================

class TestRealPipelineArtifactIntegrity:
    """Empirical verification on the generated pipeline artifacts."""

    def test_real_artifacts_exist_and_non_empty(self):
        """Verify that all M1 deliverable artifacts exist and are non-empty."""
        from src.config import DATA_DIR, MODEL_DIR

        train_path = DATA_DIR / "processed_train.parquet"
        test_path = DATA_DIR / "processed_test.parquet"
        pipeline_path = MODEL_DIR / "preprocessing_pipeline.joblib"
        feat_path = MODEL_DIR / "preprocessed_feature_names.csv"

        for p in [train_path, test_path, pipeline_path, feat_path]:
            assert p.exists(), f"Missing deliverable: {p}"
            assert p.stat().st_size > 0, f"Empty deliverable: {p}"

    def test_real_parquet_shape_and_no_leakage(self):
        """Verify row counts, column counts, and applicant ID exclusion."""
        from src.config import DATA_DIR, MODEL_DIR, TARGET_COLUMN

        train = pd.read_parquet(DATA_DIR / "processed_train.parquet")
        test = pd.read_parquet(DATA_DIR / "processed_test.parquet")
        feat_df = pd.read_csv(MODEL_DIR / "preprocessed_feature_names.csv")

        assert len(train) == 246008
        assert len(test) == 61503
        assert len(train.columns) == 342
        assert len(test.columns) == 342
        assert len(feat_df) == 341

        # ID Leakage elimination check
        assert "SK_ID_CURR" not in feat_df["feature_name"].values
        assert "num__SK_ID_CURR" not in feat_df["feature_name"].values
        assert "cat__SK_ID_CURR" not in feat_df["feature_name"].values

        # Disjoint index assertion
        assert len(set(train.index).intersection(set(test.index))) == 0

        # Zero NaN and Zero Inf assertion
        train_features = train.drop(columns=[TARGET_COLUMN])
        test_features = test.drop(columns=[TARGET_COLUMN])
        assert not train_features.isna().any().any()
        assert not test_features.isna().any().any()
        assert np.isfinite(train_features.values).all()
        assert np.isfinite(test_features.values).all()

    def test_real_data_unlinked_applicants_handling(self):
        """
        Verify that real unlinked applicants are correctly represented and imputed
        in the generated training partition.
        """
        from src.config import DATA_DIR

        train = pd.read_parquet(DATA_DIR / "processed_train.parquet")

        # Unlinked bureau applicants
        bureau_flag = train["num__FLAG_NO_BUREAU_DATA"]
        unlinked_bureau_mask = bureau_flag > 0
        assert unlinked_bureau_mask.sum() > 30000, "Expected >30,000 unlinked bureau records"

        # Unlinked prev app applicants
        prev_flag = train["num__FLAG_NO_PREV_DATA"]
        unlinked_prev_mask = prev_flag > 0
        assert unlinked_prev_mask.sum() > 10000, "Expected >10,000 unlinked prev app records"

        # Check that unlinked applicants have 100% finite features across all 341 features
        unlinked_bureau_features = train.loc[unlinked_bureau_mask].drop(columns=["TARGET"])
        assert np.isfinite(unlinked_bureau_features.values).all()
