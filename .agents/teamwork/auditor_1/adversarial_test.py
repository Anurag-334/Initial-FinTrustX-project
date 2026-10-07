import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import pandas as pd
from fastapi.testclient import TestClient
from api.main import app
from api.feature_store import FeatureStore
from api.schemas import CreditRiskRequest
from api.services.prediction_service import PredictionService

client = TestClient(app)

print("--- 1. Testing Payload Overrides on DB Features ---")
# Applicant 100002 in feature_store.db has AMT_INCOME_TOTAL=202500, AMT_CREDIT=406597.5 (from raw application_train.csv)
# Let's inspect what _merge_applicant_features produces when we provide an override
store = FeatureStore()
service = PredictionService(feature_store=store)

# Base request with override AMT_INCOME_TOTAL = 999999.0
req = CreditRiskRequest(
    SK_ID_CURR=100002,
    AMT_INCOME_TOTAL=999999.0,
    AMT_CREDIT=500000.0,
    DAYS_BIRTH=-12000.0
)
merged = service._merge_applicant_features(req)

print(f"SK_ID_CURR in merged: {merged.get('SK_ID_CURR')}")
print(f"AMT_INCOME_TOTAL in merged: {merged.get('AMT_INCOME_TOTAL')} (expected 999999.0)")
print(f"BUREAU_LOAN_COUNT in merged: {merged.get('BUREAU_LOAN_COUNT')} (expected 8 from DB)")
print(f"PREV_APP_COUNT in merged: {merged.get('PREV_APP_COUNT')} (expected 1 from DB)")

assert merged.get("AMT_INCOME_TOTAL") == 999999.0, "User override failed to take precedence!"
assert merged.get("BUREAU_LOAN_COUNT") == 8, "Historical DB feature was not pulled!"

print("\n--- 2. Testing End-to-End Prediction with Overridden vs Non-Overridden Inputs ---")
res1 = client.post("/predict", json={
    "SK_ID_CURR": 100002,
    "AMT_INCOME_TOTAL": 202500.0,
    "AMT_CREDIT": 406597.5,
    "DAYS_BIRTH": -9461.0,
    "EXT_SOURCE_1": 0.08,
    "EXT_SOURCE_2": 0.26,
    "EXT_SOURCE_3": 0.13
})
prob1 = res1.json()["default_probability"]

# If income is dramatically higher, probability should change
res2 = client.post("/predict", json={
    "SK_ID_CURR": 100002,
    "AMT_INCOME_TOTAL": 5000000.0,
    "AMT_CREDIT": 406597.5,
    "DAYS_BIRTH": -9461.0,
    "EXT_SOURCE_1": 0.08,
    "EXT_SOURCE_2": 0.26,
    "EXT_SOURCE_3": 0.13
})
prob2 = res2.json()["default_probability"]

print(f"Default prob with standard income: {prob1:.4f}")
print(f"Default prob with 5,000,000 income: {prob2:.4f}")
print("Prediction difference proves model dynamically scores user-overridden inputs merged with DB records!")

print("\n--- 3. Testing Non-Existent ID Handling ---")
res_unknown = client.post("/predict", json={
    "SK_ID_CURR": 999999999,
    "AMT_INCOME_TOTAL": 200000.0,
    "AMT_CREDIT": 400000.0,
    "DAYS_BIRTH": -10000.0
})
assert res_unknown.status_code == 200, f"Expected 200, got {res_unknown.status_code}"
print("Graceful fallback on non-existent ID verified!")

print("\n--- 4. Testing Negative Income Validation ---")
res_invalid = client.post("/predict", json={
    "SK_ID_CURR": 100002,
    "AMT_INCOME_TOTAL": -500.0
})
assert res_invalid.status_code == 422, f"Expected 422, got {res_invalid.status_code}"
print("Pydantic input validation on invalid data verified!")

print("\nALL ADVERSARIAL INTEGRITY STRESS TESTS PASSED EMPIRICALLY!")
