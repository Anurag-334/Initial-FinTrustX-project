"""
Independent Verification Test Suite authored by Victory Auditor
Zero shared context — independent verification of R1, R2, R3, R4.
"""

import sys
import sqlite3
import warnings
from pathlib import Path
from pandas.errors import PerformanceWarning
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path("d:/Projects/Credit-risk-ai")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from api.main import app
from api.feature_store import FeatureStore

def test_r1_feature_store_db():
    print("\n--- Auditing R1: SQLite Feature Store DB ---")
    db_path = PROJECT_ROOT / "data" / "feature_store.db"
    assert db_path.exists(), f"Feature store DB does not exist at {db_path}"
    print(f"DB file exists: {db_path} (Size: {db_path.stat().st_size / (1024*1024):.2f} MB)")

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("PRAGMA table_info(applicant_features);")
    cols = c.fetchall()
    col_names = [col[1] for col in cols]
    pk_col = next((col[1] for col in cols if col[5] == 1), None)
    print(f"Total columns: {len(col_names)}")
    print(f"Primary key: {pk_col}")
    assert pk_col == "SK_ID_CURR", f"Expected PK SK_ID_CURR, got {pk_col}"
    assert len(col_names) == 98, f"Expected 98 columns, got {len(col_names)}"

    c.execute("SELECT COUNT(*) FROM applicant_features;")
    total_rows = c.fetchone()[0]
    print(f"Total rows: {total_rows}")
    assert total_rows == 356255, f"Expected 356,255 rows, got {total_rows}"

    # Check distinct values of a key feature to ensure non-trivial data
    c.execute("SELECT COUNT(DISTINCT TOTAL_DEBT_TO_INCOME) FROM applicant_features;")
    distinct_ratios = c.fetchone()[0]
    print(f"Distinct TOTAL_DEBT_TO_INCOME values: {distinct_ratios}")
    assert distinct_ratios > 200000, "Too few distinct ratio values!"

    # Query sample ID 100002
    c.execute("SELECT SK_ID_CURR, BUREAU_LOAN_COUNT, PREV_APP_COUNT, TOTAL_DEBT_TO_INCOME FROM applicant_features WHERE SK_ID_CURR = 100002;")
    row = c.fetchone()
    print(f"Row for 100002: {row}")
    assert row is not None, "Applicant 100002 not found in feature store!"
    assert row[1] == 8, f"Expected BUREAU_LOAN_COUNT=8, got {row[1]}"
    assert row[2] == 1, f"Expected PREV_APP_COUNT=1, got {row[2]}"

    conn.close()
    print(">>> R1 Feature Store DB check: PASS")


def test_r2_backend_integration():
    print("\n--- Auditing R2: Backend Integration & Feature Merging ---")
    client = TestClient(app)

    # 1. Prediction with valid SK_ID_CURR
    payload_with_id = {
        "SK_ID_CURR": 100002,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 406597.5,
    }
    res = client.post("/predict", json=payload_with_id)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    print(f"Prediction for 100002: Risk Score = {data['risk_score']}, Prob = {data['default_probability']}")
    assert data["applicant_id"] == 100002
    assert "default_probability" in data
    assert 0.0 <= data["default_probability"] <= 1.0

    # 2. Precedence test: Overriding a historical feature
    # In feature_store.db, 100002 has BUREAU_DAYS_CREDIT_MEAN = -874.0
    # Overriding BUREAU_DAYS_CREDIT_MEAN in payload
    from api.feature_store import get_feature_store
    fs = get_feature_store()
    rec_100002 = fs.get_applicant_features(100002)
    assert rec_100002 is not None
    assert rec_100002["BUREAU_LOAN_COUNT"] == 8

    # Overriding a feature and testing service merge directly
    from api.services.prediction_service import PredictionService
    from api.schemas import CreditRiskRequest
    svc = PredictionService(feature_store=fs)
    req = CreditRiskRequest(SK_ID_CURR=100002, BUREAU_DAYS_CREDIT_MEAN=-50.0)
    merged = svc._merge_applicant_features(req)
    assert merged["BUREAU_DAYS_CREDIT_MEAN"] == -50.0, f"Expected override -50.0, got {merged['BUREAU_DAYS_CREDIT_MEAN']}"
    assert merged["BUREAU_LOAN_COUNT"] == 8, f"Historical attribute lost! Got {merged['BUREAU_LOAN_COUNT']}"
    print("Override precedence directly verified: incoming payload took precedence over historical value.")

    # Test probability sensitivity with external sources
    res_orig = client.post("/predict", json={"SK_ID_CURR": 100002})
    prob_orig = res_orig.json()["default_probability"]

    res_override = client.post("/predict", json={
        "SK_ID_CURR": 100002,
        "EXT_SOURCE_1": 0.95,
        "EXT_SOURCE_2": 0.95,
        "EXT_SOURCE_3": 0.95,
    })
    prob_override = res_override.json()["default_probability"]
    print(f"Probability before override: {prob_orig:.4f}, after high external source override: {prob_override:.4f}")
    assert prob_override < prob_orig, "Payload override of credit scores should lower default probability!"

    # 3. Backward compatibility: request without SK_ID_CURR
    payload_no_id = {
        "AMT_INCOME_TOTAL": 150000.0,
        "AMT_CREDIT": 450000.0,
        "DAYS_BIRTH": -14000.0,
    }
    res_no_id = client.post("/predict", json=payload_no_id)
    assert res_no_id.status_code == 200, f"Expected 200 without ID, got {res_no_id.status_code}: {res_no_id.text}"
    assert res_no_id.json()["applicant_id"] is None
    print("Backward compatibility without SK_ID_CURR: Verified")

    # 4. Unknown SK_ID_CURR: fallback without 500 error
    payload_unknown = {
        "SK_ID_CURR": 999999999,
        "AMT_INCOME_TOTAL": 180000.0,
        "AMT_CREDIT": 500000.0,
    }
    res_unknown = client.post("/predict", json=payload_unknown)
    assert res_unknown.status_code == 200, f"Expected 200 for unknown ID, got {res_unknown.status_code}: {res_unknown.text}"
    assert res_unknown.json()["applicant_id"] == 999999999
    print("Unknown SK_ID_CURR graceful fallback: Verified")

    print(">>> R2 Backend Integration check: PASS")


def test_r3_preprocessing_no_fragmentation_warnings():
    print("\n--- Auditing R3: Preprocessing Vectorization & Zero Fragmentation Warnings ---")
    client = TestClient(app)

    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")

        # Test single requests with diverse subsets of features
        client.post("/predict", json={"AMT_INCOME_TOTAL": 200000.0})
        client.post("/predict", json={"SK_ID_CURR": 100002})
        client.post("/predict", json={"SK_ID_CURR": 100003, "AMT_CREDIT": 300000.0})
        
        # Test batch request
        client.post("/predict/batch", json={"requests": [
            {"SK_ID_CURR": 100002},
            {"AMT_INCOME_TOTAL": 150000.0},
            {"SK_ID_CURR": 999999999, "AMT_CREDIT": 100000.0}
        ]})

        frag_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, PerformanceWarning) or "fragment" in str(w.message).lower()
        ]

    print(f"Emitted fragmentation warnings: {len(frag_warnings)}")
    assert len(frag_warnings) == 0, f"Fragmentation warnings detected: {[str(w.message) for w in frag_warnings]}"
    print(">>> R3 Zero Fragmentation Warnings check: PASS")


def test_r4_frontend_implementation():
    print("\n--- Auditing R4: Frontend UI Elements & Data Binding ---")
    html_path = PROJECT_ROOT / "frontend" / "index.html"
    assert html_path.exists(), "frontend/index.html does not exist"
    html_content = html_path.read_text(encoding="utf-8")
    assert 'id="SK_ID_CURR"' in html_content, "Applicant ID input #SK_ID_CURR missing from index.html"
    assert 'Applicant ID' in html_content, "Applicant ID label missing from index.html"
    print("Frontend HTML contains #SK_ID_CURR input and label: Verified")

    js_path = PROJECT_ROOT / "frontend" / "js" / "app.js"
    assert js_path.exists(), "frontend/js/app.js does not exist"
    js_content = js_path.read_text(encoding="utf-8")
    assert "form.elements['SK_ID_CURR']" in js_content, "Form handling of SK_ID_CURR missing from app.js"
    assert "payload.SK_ID_CURR" in js_content, "Payload assignment of SK_ID_CURR missing from app.js"
    print("Frontend JS correctly binds and submits SK_ID_CURR: Verified")
    print(">>> R4 Frontend Implementation check: PASS")


if __name__ == "__main__":
    print("==================================================")
    print("VICTORY AUDITOR INDEPENDENT TEST EXECUTION")
    print("==================================================")
    test_r1_feature_store_db()
    test_r2_backend_integration()
    test_r3_preprocessing_no_fragmentation_warnings()
    test_r4_frontend_implementation()
    print("\n==================================================")
    print("ALL INDEPENDENT AUDIT CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")
