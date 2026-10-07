"""
=============================================================================
FinTrustX — Milestone 2 Empirical Adversarial & Inference Stress Test Suite
=============================================================================
Author: Challenger M2-2 (teamwork_preview_challenger_m2_2)

Rigorous empirical tests covering:
1. Direct Model Extreme Vector Resilience (zeros, medians, +/- 1e6..1e12, NaNs)
2. Batch Inference Latency SLA Benchmark (10,000 samples < 0.1 ms/sample)
3. End-to-End Pipeline Edge Cases (empty payloads, missing features, outliers, unseen categories)
4. Inference Determinism & Probability Bounds
5. Test-Set Risk Stratification Sanity
=============================================================================
"""

import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from api.model_loader import ModelLoader
from api.preprocessing import transform_raw_to_features
from api.predictor import XGBoostPredictor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
XGBOOST_PATH = MODEL_DIR / "xgboost.joblib"
PIPELINE_PATH = MODEL_DIR / "preprocessing_pipeline.joblib"
FEATURE_NAMES_PATH = MODEL_DIR / "preprocessed_feature_names.csv"
TEST_PARQUET_PATH = DATA_DIR / "processed_test.parquet"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def model():
    assert XGBOOST_PATH.exists(), f"Missing {XGBOOST_PATH}"
    return joblib.load(XGBOOST_PATH)


@pytest.fixture(scope="module")
def pipeline():
    assert PIPELINE_PATH.exists(), f"Missing {PIPELINE_PATH}"
    return joblib.load(PIPELINE_PATH)


@pytest.fixture(scope="module")
def feature_names():
    assert FEATURE_NAMES_PATH.exists(), f"Missing {FEATURE_NAMES_PATH}"
    df = pd.read_csv(FEATURE_NAMES_PATH)
    return df.iloc[:, 0].tolist()


@pytest.fixture(scope="module")
def test_dataset():
    assert TEST_PARQUET_PATH.exists(), f"Missing {TEST_PARQUET_PATH}"
    df = pd.read_parquet(TEST_PARQUET_PATH)
    X = df.drop(columns=["TARGET"])
    y = df["TARGET"].astype(int)
    return X, y


@pytest.fixture(scope="module")
def api_loader():
    loader = ModelLoader()
    loader.load_artifacts()
    return loader


@pytest.fixture(scope="module")
def api_predictor(api_loader):
    return XGBoostPredictor(api_loader)


# =============================================================================
# 1. Direct Model Stress on Extreme Vectors
# =============================================================================

class TestModelExtremeVectors:
    """Stress tests on models/xgboost.joblib directly with adversarial inputs."""

    def test_extreme_vector_all_zeros(self, model, feature_names):
        """All-zeros feature vector must produce valid probability in [0, 1]."""
        n_features = len(feature_names)
        x_zeros = np.zeros((1, n_features), dtype=np.float32)

        proba = model.predict_proba(x_zeros)
        assert proba.shape == (1, 2)
        assert np.isfinite(proba).all()
        assert 0.0 <= proba[0, 1] <= 1.0
        assert pytest.approx(proba[0, 0] + proba[0, 1], abs=1e-5) == 1.0

    def test_extreme_vector_all_medians(self, model, test_dataset):
        """Vector of dataset medians must yield well-behaved probability."""
        X_test, _ = test_dataset
        medians = X_test.median().values.reshape(1, -1).astype(np.float32)

        proba = model.predict_proba(medians)
        assert proba.shape == (1, 2)
        assert np.isfinite(proba).all()
        assert 0.0 <= proba[0, 1] <= 1.0
        assert pytest.approx(proba[0, 0] + proba[0, 1], abs=1e-5) == 1.0

    @pytest.mark.parametrize("magnitude", [1e3, 1e6, 1e9, 1e12])
    def test_extreme_large_positive_vectors(self, model, feature_names, magnitude):
        """Large positive magnitudes must not cause numerical overflow or NaN."""
        n_features = len(feature_names)
        x_huge = np.full((1, n_features), magnitude, dtype=np.float32)

        proba = model.predict_proba(x_huge)
        assert proba.shape == (1, 2)
        assert not np.isnan(proba).any()
        assert not np.isinf(proba).any()
        assert 0.0 <= proba[0, 1] <= 1.0
        assert pytest.approx(proba[0, 0] + proba[0, 1], abs=1e-5) == 1.0

    @pytest.mark.parametrize("magnitude", [-1e3, -1e6, -1e9, -1e12])
    def test_extreme_large_negative_vectors(self, model, feature_names, magnitude):
        """Large negative magnitudes must not cause numerical underflow or NaN."""
        n_features = len(feature_names)
        x_neg = np.full((1, n_features), magnitude, dtype=np.float32)

        proba = model.predict_proba(x_neg)
        assert proba.shape == (1, 2)
        assert not np.isnan(proba).any()
        assert not np.isinf(proba).any()
        assert 0.0 <= proba[0, 1] <= 1.0
        assert pytest.approx(proba[0, 0] + proba[0, 1], abs=1e-5) == 1.0

    def test_extreme_vector_alternating_polarities(self, model, feature_names):
        """Checkerboard alternating polarities (+1e9, -1e9, ...) stress test."""
        n_features = len(feature_names)
        pattern = np.array([1e9 if i % 2 == 0 else -1e9 for i in range(n_features)], dtype=np.float32)
        x_alt = pattern.reshape(1, -1)

        proba = model.predict_proba(x_alt)
        assert proba.shape == (1, 2)
        assert np.isfinite(proba).all()
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_extreme_heavy_tailed_cauchy_vectors(self, model, feature_names):
        """Stochastic heavy-tailed inputs (Cauchy distributed with infinite variance)."""
        np.random.seed(42)
        n_features = len(feature_names)
        x_cauchy = np.random.standard_cauchy((50, n_features)).astype(np.float32)

        proba = model.predict_proba(x_cauchy)
        assert proba.shape == (50, 2)
        assert np.isfinite(proba).all()
        assert (proba[:, 1] >= 0.0).all() and (proba[:, 1] <= 1.0).all()

    @pytest.mark.parametrize("nan_fraction", [0.25, 0.50, 0.90, 1.0])
    def test_xgboost_native_missingness_tolerance(self, model, feature_names, nan_fraction):
        """
        XGBoost supports native NaN handling.
        Verify that passing vectors with high missingness up to 100% NaN produces valid probabilities.
        """
        np.random.seed(42)
        n_features = len(feature_names)
        x = np.zeros((10, n_features), dtype=np.float32)
        if nan_fraction == 1.0:
            x[:] = np.nan
        else:
            mask = np.random.rand(*x.shape) < nan_fraction
            x[mask] = np.nan

        proba = model.predict_proba(x)
        assert proba.shape == (10, 2)
        assert not np.isnan(proba).any()
        assert not np.isinf(proba).any()
        assert ((proba[:, 1] >= 0.0) & (proba[:, 1] <= 1.0)).all()


# =============================================================================
# 2. Batch Inference Latency SLA Benchmark (<0.1 ms/row on 10,000 samples)
# =============================================================================

class TestInferenceLatencySLA:
    """Rigorous empirical validation of inference throughput and SLA."""

    def test_batch_inference_latency_sla_10k_rows(self, model, test_dataset):
        """
        SLA Target: < 0.1 ms per sample for batch inference.
        For 10,000 rows, total latency must be < 1,000 ms (1.0 second).
        """
        X_test, _ = test_dataset
        X_10k = X_test.iloc[:10000].values.astype(np.float32)
        assert X_10k.shape[0] == 10000
        assert X_10k.shape[1] == 341

        # Warmup run (JIT/cache/OpenMP thread pool warmup)
        _ = model.predict_proba(X_10k[:500])

        # Benchmark 10 repeated passes
        n_iterations = 10
        durations_sec = []

        for _ in range(n_iterations):
            start = time.perf_counter()
            _ = model.predict_proba(X_10k)
            durations_sec.append(time.perf_counter() - start)

        durations_sec = np.array(durations_sec)
        durations_ms = durations_sec * 1000.0
        latency_per_sample_ms = durations_ms / 10000.0

        mean_per_sample_ms = float(np.mean(latency_per_sample_ms))
        median_per_sample_ms = float(np.median(latency_per_sample_ms))
        p95_per_sample_ms = float(np.percentile(latency_per_sample_ms, 95))
        max_per_sample_ms = float(np.max(latency_per_sample_ms))
        throughput_rows_per_sec = 10000.0 / float(np.mean(durations_sec))

        print(f"\n--- LATENCY SLA BENCHMARK REPORT (10,000 ROWS) ---")
        print(f"Mean batch duration: {np.mean(durations_ms):.2f} ms")
        print(f"Mean latency per sample: {mean_per_sample_ms:.5f} ms/row")
        print(f"Median latency per sample: {median_per_sample_ms:.5f} ms/row")
        print(f"P95 latency per sample: {p95_per_sample_ms:.5f} ms/row")
        print(f"Max latency per sample: {max_per_sample_ms:.5f} ms/row")
        print(f"Throughput: {throughput_rows_per_sec:,.0f} samples/second")

        # SLA Assertions
        SLA_THRESHOLD_MS_PER_ROW = 0.10  # 0.1 ms/row
        assert mean_per_sample_ms < SLA_THRESHOLD_MS_PER_ROW, (
            f"Mean latency {mean_per_sample_ms:.5f} ms/row violates SLA (< 0.1 ms/row)"
        )
        assert p95_per_sample_ms < SLA_THRESHOLD_MS_PER_ROW, (
            f"P95 latency {p95_per_sample_ms:.5f} ms/row violates SLA (< 0.1 ms/row)"
        )
        assert max_per_sample_ms < SLA_THRESHOLD_MS_PER_ROW, (
            f"Worst-case latency {max_per_sample_ms:.5f} ms/row violates SLA (< 0.1 ms/row)"
        )

    def test_single_sample_inference_latency(self, model, test_dataset):
        """Verify single-sample inference latency is under 5.0 ms."""
        X_test, _ = test_dataset
        sample = X_test.iloc[[0]].values.astype(np.float32)

        # Warmup
        _ = model.predict_proba(sample)

        runs = 100
        timings = []
        for _ in range(runs):
            t0 = time.perf_counter()
            _ = model.predict_proba(sample)
            timings.append((time.perf_counter() - t0) * 1000.0)

        mean_ms = np.mean(timings)
        p95_ms = np.percentile(timings, 95)
        print(f"\nSingle-sample latency: mean={mean_ms:.3f} ms, p95={p95_ms:.3f} ms")
        assert mean_ms < 5.0, f"Single-sample latency too high: {mean_ms:.3f} ms"


# =============================================================================
# 3. End-to-End Pipeline Edge Case Testing
# =============================================================================

class TestPipelineEndToEndEdgeCases:
    """
    Stress test raw JSON payloads -> transform_raw_to_features -> model.predict_proba
    """

    def test_completely_empty_payload(self, pipeline, model, api_loader):
        """Completely empty dict payload must be handled safely via imputation."""
        raw_payload = {}
        transformed = transform_raw_to_features(
            raw_inputs=raw_payload,
            pipeline=pipeline,
            raw_feature_names=api_loader.raw_feature_names
        )

        assert transformed.shape == (1, 341)
        assert np.isfinite(transformed).all()

        proba = model.predict_proba(transformed)
        assert proba.shape == (1, 2)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_payload_with_only_id(self, pipeline, model, api_loader):
        """Payload with only SK_ID_CURR."""
        raw_payload = {"SK_ID_CURR": 100002}
        transformed = transform_raw_to_features(
            raw_inputs=raw_payload,
            pipeline=pipeline,
            raw_feature_names=api_loader.raw_feature_names
        )

        assert transformed.shape == (1, 341)
        assert np.isfinite(transformed).all()
        proba = model.predict_proba(transformed)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_payload_with_extreme_unrealistic_finances(self, pipeline, model, api_loader):
        """Payload with trillionaire assets and extreme credit amounts."""
        raw_payload = {
            "SK_ID_CURR": 999999,
            "AMT_INCOME_TOTAL": 1e14,
            "AMT_CREDIT": 1e15,
            "AMT_ANNUITY": 5e13,
            "DAYS_BIRTH": -36500,  # 100 years old
            "DAYS_EMPLOYED": -18000,
            "EXT_SOURCE_1": 0.99999,
            "EXT_SOURCE_2": 0.99999,
            "EXT_SOURCE_3": 0.99999,
            "BUREAU_AMT_CREDIT_SUM": 1e16,
            "PREV_AMT_CREDIT_SUM": 1e15,
        }
        transformed = transform_raw_to_features(
            raw_inputs=raw_payload,
            pipeline=pipeline,
            raw_feature_names=api_loader.raw_feature_names
        )

        assert transformed.shape == (1, 341)
        assert np.isfinite(transformed).all()
        proba = model.predict_proba(transformed)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_payload_with_negative_finances(self, pipeline, model, api_loader):
        """Payload with zero/negative finances."""
        raw_payload = {
            "SK_ID_CURR": 888888,
            "AMT_INCOME_TOTAL": -50000.0,
            "AMT_CREDIT": 0.0,
            "AMT_ANNUITY": 0.0,
            "DAYS_BIRTH": 0,
            "DAYS_EMPLOYED": 365243,  # Home credit sentinel for unemployed
            "EXT_SOURCE_1": -1.0,
            "EXT_SOURCE_2": -1.0,
            "EXT_SOURCE_3": -1.0,
        }
        transformed = transform_raw_to_features(
            raw_inputs=raw_payload,
            pipeline=pipeline,
            raw_feature_names=api_loader.raw_feature_names
        )

        assert transformed.shape == (1, 341)
        assert np.isfinite(transformed).all()
        proba = model.predict_proba(transformed)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_payload_with_completely_unseen_categories(self, pipeline, model, api_loader):
        """Payload containing unknown categorical values in every categorical column."""
        raw_payload = {
            "NAME_CONTRACT_TYPE": "Galactic Credit Line",
            "CODE_GENDER": "Alien_Entity",
            "FLAG_OWN_CAR": "FlyingSaucer",
            "FLAG_OWN_REALTY": "SpaceStation",
            "NAME_TYPE_SUITE": "Cyborg Companion",
            "NAME_INCOME_TYPE": "Cosmic Mining",
            "NAME_EDUCATION_TYPE": "Hyper-Dimensional PhD",
            "NAME_FAMILY_STATUS": "Quantum Entangled",
            "NAME_HOUSING_TYPE": "Orbital Habitat",
            "OCCUPATION_TYPE": "Time Traveler",
            "WEEKDAY_APPR_PROCESS_START": "Funday",
            "ORGANIZATION_TYPE": "United Federation of Planets",
            "FONDKAPREMONT_MODE": "Antimatter Vault",
            "HOUSETYPE_MODE": "Biosphere",
            "WALLSMATERIAL_MODE": "Neutronium",
            "EMERGENCYSTATE_MODE": "Red Alert",
        }
        transformed = transform_raw_to_features(
            raw_inputs=raw_payload,
            pipeline=pipeline,
            raw_feature_names=api_loader.raw_feature_names
        )

        assert transformed.shape == (1, 341)
        assert np.isfinite(transformed).all()
        proba = model.predict_proba(transformed)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_predictor_predict_single_contract(self, api_predictor):
        """Verify API XGBoostPredictor.predict_single returns valid response structure."""
        payload = {
            "SK_ID_CURR": 100001,
            "AMT_INCOME_TOTAL": 200000.0,
            "AMT_CREDIT": 500000.0,
            "AMT_ANNUITY": 25000.0,
        }
        res = api_predictor.predict_single(payload, threshold=0.50)

        assert res.prediction in [0, 1]
        assert 0.0 <= res.default_probability <= 1.0
        assert 0.0 <= res.risk_score <= 100.0
        assert res.risk_category in ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
        assert res.loan_decision in [
            "Likely Approved", "Manual Review", "Higher Risk / Manual Review", "Likely Rejected"
        ]
        assert res.model == "XGBoost"
        assert res.applicant_id == 100001

    def test_predictor_predict_batch_contract(self, api_predictor):
        """Verify API XGBoostPredictor.predict_batch on 50 diverse payloads."""
        batch_payloads = [
            {"SK_ID_CURR": 200000 + i, "AMT_INCOME_TOTAL": 50000.0 * (i + 1)}
            for i in range(50)
        ]
        # Inject adversarial cases
        batch_payloads[10] = {}
        batch_payloads[20] = {"AMT_INCOME_TOTAL": 1e12, "CODE_GENDER": "Alien"}
        batch_payloads[30] = {"AMT_CREDIT": -100.0}

        results = api_predictor.predict_batch(batch_payloads, threshold=0.50)

        assert len(results) == 50
        for idx, res in enumerate(results):
            assert res.prediction in [0, 1]
            assert 0.0 <= res.default_probability <= 1.0
            assert 0.0 <= res.risk_score <= 100.0
            assert res.risk_category in ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]


# =============================================================================
# 4. Determinism, Probability Bounds & Monotonicity
# =============================================================================

class TestModelInferenceDeterminism:
    """Verify bitwise/float reproducibility and consistency."""

    def test_inference_reproducibility(self, model, test_dataset):
        """Repeated inference runs on identical inputs must yield identical probabilities."""
        X_test, _ = test_dataset
        X_sample = X_test.iloc[:100].values.astype(np.float32)

        proba_run1 = model.predict_proba(X_sample)
        proba_run2 = model.predict_proba(X_sample)
        proba_run3 = model.predict_proba(X_sample)

        np.testing.assert_allclose(proba_run1, proba_run2, rtol=1e-7, atol=1e-7)
        np.testing.assert_allclose(proba_run1, proba_run3, rtol=1e-7, atol=1e-7)

    def test_batch_vs_single_inference_equivalence(self, model, test_dataset):
        """Predicting a row individually must equal its row in batch inference."""
        X_test, _ = test_dataset
        X_sub = X_test.iloc[:50].values.astype(np.float32)

        batch_probs = model.predict_proba(X_sub)

        for i in range(10):
            single_prob = model.predict_proba(X_sub[[i]])
            np.testing.assert_allclose(
                single_prob[0], batch_probs[i], rtol=1e-6, atol=1e-6,
                err_msg=f"Batch vs single mismatch at row {i}"
            )


# =============================================================================
# 5. Held-Out Test Set Risk Stratification Sanity
# =============================================================================

class TestTestSetRiskStratification:
    """Verify statistical soundness of predictions across held-out test data."""

    def test_test_set_score_distribution_and_separation(self, model, test_dataset):
        """
        Verify on 61,503 held-out test applicants:
        1. All probabilities strictly in [0, 1].
        2. Mean predicted probability is aligned with default base rate (~8%).
        3. Mean predicted probability for actual defaults (TARGET=1) is significantly
           higher than for non-defaults (TARGET=0).
        """
        X_test, y_test = test_dataset
        probs = model.predict_proba(X_test)[:, 1]

        assert len(probs) == 61503
        assert np.isfinite(probs).all()
        assert (probs >= 0.0).all()
        assert (probs <= 1.0).all()

        mean_overall = float(np.mean(probs))
        median_overall = float(np.median(probs))
        p05 = float(np.percentile(probs, 5))
        p95 = float(np.percentile(probs, 95))

        probs_target_0 = probs[y_test == 0]
        probs_target_1 = probs[y_test == 1]

        mean_target_0 = float(np.mean(probs_target_0))
        mean_target_1 = float(np.mean(probs_target_1))

        print(f"\n--- TEST SET RISK SCORE DISTRIBUTION ---")
        print(f"Overall Mean Prob: {mean_overall:.4f} (Base Rate: {np.mean(y_test):.4f})")
        print(f"Overall Median: {median_overall:.4f}, P5: {p05:.4f}, P95: {p95:.4f}")
        print(f"Mean Prob for TARGET=0: {mean_target_0:.4f}")
        print(f"Mean Prob for TARGET=1: {mean_target_1:.4f}")
        print(f"Risk Separation Ratio (P(1|Y=1) / P(1|Y=0)): {mean_target_1 / mean_target_0:.2f}x")

        # Statistical sanity checks:
        # Base rate is ~0.0807. Overall mean predicted probability should be within [0.04, 0.20]
        assert 0.04 <= mean_overall <= 0.20, f"Mean probability uncalibrated: {mean_overall}"

        # Significant risk separation: Mean default risk for actual defaulters must be at least 2x non-defaulters
        assert mean_target_1 > mean_target_0 * 2.0, (
            f"Poor risk discrimination: mean TARGET=1 ({mean_target_1:.4f}) vs TARGET=0 ({mean_target_0:.4f})"
        )
