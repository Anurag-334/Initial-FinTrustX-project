"""
=========================================================
Integration Tests: Prediction & Explainability Endpoints
=========================================================
Comprehensive integration tests covering:
- Single and batch XGBoost inference
- Localized SHAP feature attribution
- SQLite Feature Store lookups by SK_ID_CURR
- Backward compatibility (requests omitting SK_ID_CURR)
- Graceful fallback on unknown applicant IDs
- Zero Pandas DataFrame fragmentation warnings (PerformanceWarning)
- Heterogeneous batch processing with mixed applicant IDs

Author: Anurag Kashyap & FinTrustX Test Suite
=========================================================
"""

import sqlite3
import warnings
from pandas.errors import PerformanceWarning
import pytest
from fastapi.testclient import TestClient
from api.feature_store import FeatureStore
from api.main import app
from api.schemas import CreditRiskRequest
from api.services.prediction_service import PredictionService


@pytest.fixture(scope="module")
def client():
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


SAMPLE_APPLICANT = {
    "SK_ID_CURR": 100002,
    "NAME_CONTRACT_TYPE": "Cash loans",
    "CODE_GENDER": "M",
    "FLAG_OWN_CAR": "N",
    "FLAG_OWN_REALTY": "Y",
    "CNT_CHILDREN": 0,
    "AMT_INCOME_TOTAL": 202500.0,
    "AMT_CREDIT": 406597.5,
    "AMT_ANNUITY": 24700.5,
    "AMT_GOODS_PRICE": 351000.0,
    "NAME_INCOME_TYPE": "Working",
    "NAME_EDUCATION_TYPE": "Secondary / secondary special",
    "NAME_FAMILY_STATUS": "Single / not married",
    "NAME_HOUSING_TYPE": "House / apartment",
    "DAYS_BIRTH": -9461.0,
    "DAYS_EMPLOYED": -637.0,
    "EXT_SOURCE_1": 0.0830,
    "EXT_SOURCE_2": 0.2629,
    "EXT_SOURCE_3": 0.1393,
}


def test_predict_single(client):
    """Test POST /predict with a valid applicant payload."""
    response = client.post("/predict", json=SAMPLE_APPLICANT)
    assert response.status_code == 200
    data = response.json()
    
    assert data["prediction"] in [0, 1]
    assert 0.0 <= data["default_probability"] <= 1.0
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["risk_category"] in ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
    assert data["loan_decision"] in [
        "Likely Approved", "Manual Review", "Higher Risk / Manual Review", "Likely Rejected"
    ]
    assert data["model"] == "XGBoost"
    assert data["explanation"] is None


def test_predict_with_explanation(client):
    """Test POST /predict?explain=true returns SHAP attribution."""
    response = client.post("/predict?explain=true", json=SAMPLE_APPLICANT)
    assert response.status_code == 200
    data = response.json()
    
    assert data["explanation"] is not None
    expl = data["explanation"]
    assert "top_risk_factors" in expl
    assert "protective_factors" in expl
    assert isinstance(expl["top_risk_factors"], list)
    assert isinstance(expl["protective_factors"], list)
    
    if expl["top_risk_factors"]:
        factor = expl["top_risk_factors"][0]
        assert "feature" in factor
        assert factor["impact"] == "increases risk"
        assert "contribution" in factor


def test_explain_endpoint(client):
    """Test dedicated POST /explain endpoint."""
    response = client.post("/explain", json=SAMPLE_APPLICANT)
    assert response.status_code == 200
    data = response.json()
    
    assert "top_risk_factors" in data
    assert "protective_factors" in data
    assert isinstance(data["top_risk_factors"], list)


def test_batch_prediction(client):
    """Test POST /predict/batch with multiple applicants."""
    batch_payload = {
        "requests": [
            SAMPLE_APPLICANT,
            {
                **SAMPLE_APPLICANT,
                "SK_ID_CURR": 100003,
                "AMT_INCOME_TOTAL": 270000.0,
                "AMT_CREDIT": 1293502.5,
                "EXT_SOURCE_1": 0.75,
                "EXT_SOURCE_2": 0.82,
                "EXT_SOURCE_3": 0.89,
            }
        ]
    }
    response = client.post("/predict/batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_processed"] == 2
    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["applicant_id"] == 100002
    assert data["predictions"][1]["applicant_id"] == 100003


def test_invalid_input_validation(client):
    """Test Pydantic 422 error on invalid negative income."""
    invalid_applicant = {
        **SAMPLE_APPLICANT,
        "AMT_INCOME_TOTAL": -50000.0  # Invalid: Income cannot be negative
    }
    response = client.post("/predict", json=invalid_applicant)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data or "detail" in data


# =========================================================
# Integration Test A: Valid SK_ID_CURR with Feature Store
# =========================================================
def test_predict_with_valid_sk_id_curr_pulls_db_features(client, sqlite_feature_db):
    """
    Test R2/Acceptance Criterion:
    Passing a valid SK_ID_CURR queries the SQLite Feature Store,
    merges historical applicant features into the profile,
    and produces a successful 200 prediction response.
    """
    valid_id = 100002
    applicant_payload = {
        **SAMPLE_APPLICANT,
        "SK_ID_CURR": valid_id,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 406597.5,
    }

    response = client.post("/predict", json=applicant_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["applicant_id"] == valid_id
    assert data["prediction"] in [0, 1]
    assert 0.0 <= data["default_probability"] <= 1.0
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["risk_category"] in ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
    assert data["loan_decision"] in [
        "Likely Approved", "Manual Review", "Higher Risk / Manual Review", "Likely Rejected"
    ]
    assert data["model"] == "XGBoost"

    # Also verify that a sparse payload with valid SK_ID_CURR succeeds
    sparse_with_id = {
        "SK_ID_CURR": valid_id,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 406597.5,
        "DAYS_BIRTH": -9461.0,
    }
    sparse_res = client.post("/predict", json=sparse_with_id)
    assert sparse_res.status_code == 200
    sparse_data = sparse_res.json()
    assert sparse_data["applicant_id"] == valid_id
    assert sparse_data["prediction"] in [0, 1]


# =========================================================
# Integration Test B: Backward Compatibility (No SK_ID_CURR)
# =========================================================
def test_predict_without_sk_id_curr_backward_compatible(client):
    """
    Test Backward Compatibility:
    Ensure predictions without SK_ID_CURR (omitted or explicitly None)
    succeed without errors and return applicant_id=None.
    """
    # Case 1: SK_ID_CURR completely omitted
    payload_omitted = {k: v for k, v in SAMPLE_APPLICANT.items() if k != "SK_ID_CURR"}
    assert "SK_ID_CURR" not in payload_omitted

    res_omitted = client.post("/predict", json=payload_omitted)
    assert res_omitted.status_code == 200, f"Expected 200, got {res_omitted.status_code}: {res_omitted.text}"
    data_omitted = res_omitted.json()
    assert data_omitted["applicant_id"] is None
    assert data_omitted["prediction"] in [0, 1]
    assert 0.0 <= data_omitted["default_probability"] <= 1.0
    assert 0.0 <= data_omitted["risk_score"] <= 100.0

    # Case 2: SK_ID_CURR explicitly null/None
    payload_null = {**SAMPLE_APPLICANT, "SK_ID_CURR": None}
    res_null = client.post("/predict", json=payload_null)
    assert res_null.status_code == 200, f"Expected 200, got {res_null.status_code}: {res_null.text}"
    data_null = res_null.json()
    assert data_null["applicant_id"] is None
    assert data_null["prediction"] in [0, 1]
    assert 0.0 <= data_null["default_probability"] <= 1.0
    assert 0.0 <= data_null["risk_score"] <= 100.0


# Backward compatibility alias supporting both function name conventions
test_predict_without_sk_id_curr_backward_compatibility = test_predict_without_sk_id_curr_backward_compatible


# =========================================================
# Integration Test C: Fallback on Unknown SK_ID_CURR
# =========================================================
def test_predict_with_unknown_sk_id_curr_fallback(client, sqlite_feature_db):
    """
    Test Missing/Unknown Applicant ID Fallback:
    Sending a non-existent SK_ID_CURR (e.g. 999999999) must gracefully fallback
    to standalone scoring without raising a 500 Internal Server Error.
    """
    unknown_id = 999999999
    payload_unknown = {
        **SAMPLE_APPLICANT,
        "SK_ID_CURR": unknown_id,
    }
    response = client.post("/predict", json=payload_unknown)
    assert response.status_code == 200, (
        f"Expected 200 on unknown applicant ID fallback, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["applicant_id"] == unknown_id
    assert data["prediction"] in [0, 1]
    assert 0.0 <= data["default_probability"] <= 1.0
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["model"] == "XGBoost"


# =========================================================
# Integration Test D: Zero Pandas Fragmentation Warnings
# =========================================================
def test_zero_pandas_fragmentation_warning(client):
    """
    Test R3/Acceptance Criterion:
    Verify that inference execution produces ZERO Pandas DataFrame
    fragmentation warnings (PerformanceWarning).
    """
    sparse_payload = {
        "AMT_INCOME_TOTAL": 150000.0,
        "AMT_CREDIT": 450000.0,
        "AMT_ANNUITY": 25000.0,
        "DAYS_BIRTH": -15000.0,
    }

    with warnings.catch_warnings(record=True) as recorded_warnings:
        # Capture all emitted warnings
        warnings.simplefilter("always")

        # 1. Single prediction request with sparse features
        res_sparse = client.post("/predict", json=sparse_payload)
        assert res_sparse.status_code == 200

        # 2. Prediction with standard payload
        res_std = client.post("/predict", json=SAMPLE_APPLICANT)
        assert res_std.status_code == 200

        # 3. Batch prediction request
        batch_payload = {"requests": [sparse_payload, SAMPLE_APPLICANT]}
        res_batch = client.post("/predict/batch", json=batch_payload)
        assert res_batch.status_code == 200

        # Filter strictly for PerformanceWarning or any warning mentioning fragmentation
        fragmentation_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, PerformanceWarning) 
            or "fragment" in str(w.message).lower()
        ]

        assert len(fragmentation_warnings) == 0, (
            f"Detected {len(fragmentation_warnings)} fragmentation warning(s): "
            f"{[str(w.message) for w in fragmentation_warnings]}"
        )


# =========================================================
# Integration Test E: Batch Prediction with Heterogeneous IDs
# =========================================================
def test_batch_prediction_with_mixed_applicant_ids(client, sqlite_feature_db):
    """
    Test Batch Prediction with Heterogeneous ID Profiles:
    Verifies that batch evaluation correctly handles records with valid IDs,
    missing IDs (None or omitted), and unknown IDs in the same request.
    """
    batch_payload = {
        "requests": [
            {**SAMPLE_APPLICANT, "SK_ID_CURR": 100002},
            {k: v for k, v in SAMPLE_APPLICANT.items() if k != "SK_ID_CURR"},
            {**SAMPLE_APPLICANT, "SK_ID_CURR": None},
            {**SAMPLE_APPLICANT, "SK_ID_CURR": 999999999},
        ]
    }
    response = client.post("/predict/batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 4
    assert len(data["predictions"]) == 4

    assert data["predictions"][0]["applicant_id"] == 100002
    assert data["predictions"][1]["applicant_id"] is None
    assert data["predictions"][2]["applicant_id"] is None
    assert data["predictions"][3]["applicant_id"] == 999999999

    for pred in data["predictions"]:
        assert pred["prediction"] in [0, 1]
        assert 0.0 <= pred["default_probability"] <= 1.0
        assert 0.0 <= pred["risk_score"] <= 100.0


# =========================================================
# Adversarial Challenge Tests: Merge Semantics & Stress Tests
# =========================================================

def test_user_payload_strictly_overrides_historical_attributes(sqlite_feature_db):
    """
    Empirically prove that user-supplied payload attributes strictly override
    historical attributes retrieved from SQLite.
    """
    store = FeatureStore(db_path=sqlite_feature_db)
    svc = PredictionService(feature_store=store)

    # In sqlite_feature_db: 100002 has EXT_SOURCE_1=0.0830, EXT_SOURCE_3=0.1393
    # User provides explicit override for EXT_SOURCE_1=0.9999 and EXT_SOURCE_3=0.8888
    req = CreditRiskRequest(
        SK_ID_CURR=100002,
        EXT_SOURCE_1=0.9999,
        EXT_SOURCE_3=0.8888,
    )
    merged = svc._merge_applicant_features(req)

    # User overrides must strictly take precedence
    assert merged["EXT_SOURCE_1"] == 0.9999, (
        f"Expected user override 0.9999, got {merged['EXT_SOURCE_1']}"
    )
    assert merged["EXT_SOURCE_3"] == 0.8888, (
        f"Expected user override 0.8888, got {merged['EXT_SOURCE_3']}"
    )
    # Non-overridden historical attributes must be preserved from SQLite
    assert merged["EXT_SOURCE_2"] == 0.2629
    assert merged["EXT_SOURCE_3"] == 0.1393
    assert merged["BUREAU_AMT_CREDIT_SUM_MAX"] == 450000.0
    assert merged["PREV_AMT_APPLICATION_MEAN"] == 179055.0


def test_unsupplied_fields_preserve_historical_without_schema_default_clobbering(tmp_path):
    """
    Empirically prove that unsupplied fields take historical values from SQLite
    without being clobbered by Pydantic schema defaults.
    """
    # Create isolated DB where historical table contains fields with schema defaults:
    # Schema defaults: AMT_INCOME_TOTAL=150000.0, AMT_CREDIT=450000.0, DAYS_BIRTH=-14000.0
    db_file = tmp_path / "clobber_test.db"
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE applicant_features (
            SK_ID_CURR INTEGER PRIMARY KEY,
            AMT_INCOME_TOTAL REAL,
            AMT_CREDIT REAL,
            DAYS_BIRTH REAL,
            BUREAU_DAYS_CREDIT_MEAN REAL
        )
    """)
    # Historical record has values differing from schema defaults
    c.execute("""
        INSERT INTO applicant_features 
        (SK_ID_CURR, AMT_INCOME_TOTAL, AMT_CREDIT, DAYS_BIRTH, BUREAU_DAYS_CREDIT_MEAN)
        VALUES (888001, 750000.0, 1200000.0, -19500.0, -999.0)
    """)
    conn.commit()
    conn.close()

    store = FeatureStore(db_path=db_file)
    svc = PredictionService(feature_store=store)

    # User submits only SK_ID_CURR (leaving AMT_INCOME_TOTAL, AMT_CREDIT, DAYS_BIRTH unsupplied)
    req = CreditRiskRequest(SK_ID_CURR=888001)
    merged = svc._merge_applicant_features(req)

    # Prove historical values are NOT clobbered by schema defaults
    assert merged["AMT_INCOME_TOTAL"] == 750000.0, (
        f"Schema default clobbered historical income! Got {merged['AMT_INCOME_TOTAL']}"
    )
    assert merged["AMT_CREDIT"] == 1200000.0, (
        f"Schema default clobbered historical credit! Got {merged['AMT_CREDIT']}"
    )
    assert merged["DAYS_BIRTH"] == -19500.0, (
        f"Schema default clobbered historical age! Got {merged['DAYS_BIRTH']}"
    )
    assert merged["BUREAU_DAYS_CREDIT_MEAN"] == -999.0

    # Fields absent from historical table still take schema defaults gracefully
    assert merged["CODE_GENDER"] == "M"
    assert merged["CNT_CHILDREN"] == 0


def test_omitted_or_nonexistent_sk_id_curr_zero_crashes(client, sqlite_feature_db):
    """
    Empirically prove that omitted, null, unknown, or negative SK_ID_CURR
    works gracefully with zero crashes across single, batch, and explanation endpoints.
    """
    # 1. Negative ID
    res_neg = client.post("/predict", json={**SAMPLE_APPLICANT, "SK_ID_CURR": -999})
    assert res_neg.status_code == 200
    assert res_neg.json()["applicant_id"] == -999

    # 2. String alias applicant_id
    res_alias = client.post("/predict", json={"applicant_id": 100002, "AMT_INCOME_TOTAL": 180000.0})
    assert res_alias.status_code == 200
    assert res_alias.json()["applicant_id"] == 100002

    # 3. Explain endpoint with unknown ID
    res_expl = client.post("/explain", json={**SAMPLE_APPLICANT, "SK_ID_CURR": 999999999})
    assert res_expl.status_code == 200
    assert "top_risk_factors" in res_expl.json()

    # 4. Explain endpoint with omitted ID
    payload_no_id = {k: v for k, v in SAMPLE_APPLICANT.items() if k != "SK_ID_CURR"}
    res_expl_noid = client.post("/explain", json=payload_no_id)
    assert res_expl_noid.status_code == 200
    assert "top_risk_factors" in res_expl_noid.json()


def test_preprocessing_stress_100_plus_simulated_requests_zero_warnings(client):
    """
    Empirically stress test api/preprocessing.py with 100+ diverse simulated requests
    wrapped in warning capture to guarantee ZERO PerformanceWarning or fragmentation warnings.
    """
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")

        # 50 Single diverse requests
        for i in range(50):
            if i % 5 == 0:
                payload = {}  # Empty payload
            elif i % 5 == 1:
                payload = {"AMT_INCOME_TOTAL": 100000.0 + i * 1000.0}  # Sparse payload
            elif i % 5 == 2:
                payload = {**SAMPLE_APPLICANT, f"EXTRA_COL_{i}": 123.45}  # Payload with unexpected extra col
            elif i % 5 == 3:
                payload = {**SAMPLE_APPLICANT, "DAYS_BIRTH": -30000.0, "EXT_SOURCE_1": 0.99}  # Full payload
            else:
                payload = {"SK_ID_CURR": 100002, "AMT_CREDIT": 500000.0 + i * 2000.0}  # DB lookup payload
            res = client.post("/predict", json=payload)
            assert res.status_code == 200

        # 25 Batch requests of 3 items each (75 items)
        for b in range(25):
            batch_payload = {
                "requests": [
                    {},
                    {"SK_ID_CURR": 100002, "AMT_INCOME_TOTAL": 150000.0},
                    {**SAMPLE_APPLICANT, "SK_ID_CURR": None},
                ]
            }
            res = client.post("/predict/batch", json=batch_payload)
            assert res.status_code == 200

        # Strict assertion for ZERO PerformanceWarning or fragmentation warnings
        frag_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, PerformanceWarning)
            or "fragment" in str(w.message).lower()
        ]

        assert len(frag_warnings) == 0, (
            f"Detected {len(frag_warnings)} fragmentation warning(s): "
            f"{[str(w.message) for w in frag_warnings]}"
        )

