# Handoff Report — Challenger 2: API Prediction & Preprocessing Adversarial Verifier

**Agent**: Challenger 2 (`challenger_2`)  
**Parent Orchestrator**: `1cf94437-5dcb-4b7c-bffa-75f9de7165e0`  
**Working Directory**: `d:\Projects\Credit-risk-ai\.agents\teamwork\challenger_2`  
**Date**: 2026-10-05T19:57:00Z  
**Verdict**: **APPROVE**  
**Type**: Hard Handoff  

---

## 1. Observation

### 1.1 Full Test Suite Execution Output
Running the full prediction integration test suite (`python -m pytest api/tests/test_prediction.py -v`) yielded a 100% pass rate:

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0 -- C:\Program Files\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\Projects\Credit-risk-ai
plugins: anyio-4.9.0, langsmith-0.7.22
collecting ... collected 15 items

api/tests/test_prediction.py::test_predict_single PASSED                 [  6%]
api/tests/test_prediction.py::test_predict_with_explanation PASSED       [ 13%]
api/tests/test_prediction.py::test_explain_endpoint PASSED               [ 20%]
api/tests/test_prediction.py::test_batch_prediction PASSED               [ 26%]
api/tests/test_prediction.py::test_invalid_input_validation PASSED       [ 33%]
api/tests/test_prediction.py::test_predict_with_valid_sk_id_curr_pulls_db_features PASSED [ 40%]
api/tests/test_prediction.py::test_predict_without_sk_id_curr_backward_compatible PASSED [ 46%]
api/tests/test_prediction.py::test_predict_without_sk_id_curr_backward_compatibility PASSED [ 53%]
api/tests/test_prediction.py::test_predict_with_unknown_sk_id_curr_fallback PASSED [ 60%]
api/tests/test_prediction.py::test_zero_pandas_fragmentation_warning PASSED [ 66%]
api/tests/test_prediction.py::test_batch_prediction_with_mixed_applicant_ids PASSED [ 73%]
api/tests/test_prediction.py::test_user_payload_strictly_overrides_historical_attributes PASSED [ 80%]
api/tests/test_prediction.py::test_unsupplied_fields_preserve_historical_without_schema_default_clobbering PASSED [ 86%]
api/tests/test_prediction.py::test_omitted_or_nonexistent_sk_id_curr_zero_crashes PASSED [ 93%]
api/tests/test_prediction.py::test_preprocessing_stress_100_plus_simulated_requests_zero_warnings PASSED [100%]

============================== warnings summary ===============================
api/tests/test_prediction.py::test_invalid_input_validation
  C:\Users\Anurag\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:59: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    response = await handler(conn, exc)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 15 passed, 1 warning in 4.65s ========================
```

### 1.2 Feature Merge Code Inspection
Inspected `_merge_applicant_features` in `api/services/prediction_service.py` (lines 59–68) and `api/services/explanation_service.py` (lines 51–60):
```python
base_data = request.model_dump(exclude_none=False)
if historical:
    base_data.update(historical)
    incoming_overrides = request.model_dump(exclude_unset=True)
    base_data.update(incoming_overrides)
    base_data["SK_ID_CURR"] = applicant_id
    return base_data
else:
    base_data["SK_ID_CURR"] = applicant_id
    return base_data
```

### 1.3 Preprocessing Vectorized Concatenation Inspection
Inspected `api/preprocessing.py` (lines 51–58):
```python
# Fill any unprovided raw columns with NaN so SimpleImputer handles them (vectorized to eliminate fragmentation warnings)
missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]
if missing_cols:
    df_missing = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)
    df_raw = pd.concat([df_raw, df_missing], axis=1)

# Reorder columns to exactly match pipeline.feature_names_in_
df_aligned = df_raw[raw_feature_names]
```

### 1.4 Production Database Inspection
Inspected SQLite database at `data/feature_store.db`:
- Record count: 356,255 applicant records.
- Columns: 98 columns (`SK_ID_CURR INTEGER PRIMARY KEY`, 97 aggregated historical bureau & previous application features).
- Point query sample `SK_ID_CURR=100002`: successfully returns historical record containing `BUREAU_SK_ID_BUREAU_COUNT=8.0`, `BUREAU_DAYS_CREDIT_MEAN=-874.0`, `BUREAU_AMT_CREDIT_SUM_MAX=450000.0`, `PREV_AMT_APPLICATION_MEAN=179055.0`.

---

## 2. Logic Chain

1. **User Overrides vs Historical Attributes (Semantics Proof)**:
   - Observation: When user explicit attributes are provided in the payload, Pydantic's `request.model_dump(exclude_unset=True)` contains strictly those fields.
   - Mechanism: In `PredictionService._merge_applicant_features`, `base_data` first ingests `historical` via `base_data.update(historical)`. Immediately after, `incoming_overrides = request.model_dump(exclude_unset=True)` is applied via `base_data.update(incoming_overrides)`.
   - Verification: In `test_user_payload_strictly_overrides_historical_attributes`, applicant `100002` (historical `EXT_SOURCE_1 = 0.0830`, `BUREAU_DAYS_CREDIT_MEAN = -874.0`) was passed with explicit payload overrides `EXT_SOURCE_1 = 0.9999` and `BUREAU_DAYS_CREDIT_MEAN = -100.0`. The merged feature dictionary evaluated to `merged["EXT_SOURCE_1"] == 0.9999` and `merged["BUREAU_DAYS_CREDIT_MEAN"] == -100.0`, while un-overridden historical attributes (`EXT_SOURCE_2 = 0.2629`, `PREV_AMT_APPLICATION_MEAN = 179055.0`) were strictly preserved.

2. **Unsupplied Fields vs Schema Defaults (Non-Clobbering Proof)**:
   - Observation: Standard Pydantic schemas populate field defaults when dumping models without exclusions.
   - Mechanism: By calling `request.model_dump(exclude_unset=True)`, fields not supplied by the client are omitted from `incoming_overrides`. Consequently, when `historical` values are placed into `base_data`, they are NOT overwritten by schema defaults.
   - Verification: In `test_unsupplied_fields_preserve_historical_without_schema_default_clobbering`, applicant `888001` in SQLite had `AMT_INCOME_TOTAL = 750000.0` (schema default is `150000.0`), `AMT_CREDIT = 1200000.0` (schema default is `450000.0`), and `DAYS_BIRTH = -19500.0` (schema default is `-14000.0`). When submitting `{"SK_ID_CURR": 888001}` with all other fields unsupplied:
     * `merged["AMT_INCOME_TOTAL"]` was `750000.0` (from SQLite, NOT clobbered by `150000.0`).
     * `merged["AMT_CREDIT"]` was `1200000.0` (from SQLite, NOT clobbered by `450000.0`).
     * `merged["DAYS_BIRTH"]` was `-19500.0` (from SQLite, NOT clobbered by `-14000.0`).
     * Missing non-historical fields (`CODE_GENDER="M"`, `CNT_CHILDREN=0`) correctly fell back to schema defaults.

3. **Backward Compatibility & Crash Resilience**:
   - Observation: API clients may send legacy requests without `SK_ID_CURR`, explicit `null` IDs, string aliases (`applicant_id`), negative integers, or IDs missing from SQLite.
   - Mechanism: `PredictionService` checks `if applicant_id is not None and self.feature_store is not None:`. If missing or not found in SQLite, it falls back to standalone payload scoring without raising an unhandled exception.
   - Verification: `test_predict_without_sk_id_curr_backward_compatible`, `test_predict_with_unknown_sk_id_curr_fallback`, and `test_omitted_or_nonexistent_sk_id_curr_zero_crashes` executed requests across `/predict`, `/predict/batch`, and `/explain`. All returned HTTP 200 with zero crashes, returning `applicant_id: None` for legacy requests and the supplied identifier for fallback requests.

4. **Vectorized Concatenation & Warning Immunity Under Stress**:
   - Observation: The baseline implementation iterated over ~100 missing columns with `df_raw[col] = np.nan`, emitting 282 `PerformanceWarning` entries.
   - Mechanism: `api/preprocessing.py` now groups all missing columns into a single `pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)` and concatenates once via `pd.concat([df_raw, df_missing], axis=1)`.
   - Verification: In `test_preprocessing_stress_100_plus_simulated_requests_zero_warnings`, we sent:
     * 50 diverse single requests (empty dicts, sparse inputs, inputs with 30+ unknown extra columns, full inputs, extreme values).
     * 25 batch requests containing 3 items each (75 items).
     * Intercepted all warnings via `warnings.catch_warnings(record=True)`.
     * Zero `PerformanceWarning` and zero fragmentation warnings were emitted. Execution completed in 4.65s total across the full 15-test suite.

---

## 3. Caveats

- **SQLite Concurrency**: SQLite handles single-writer / multi-reader workloads efficiently via WAL mode. Under massive concurrent distributed load across multiple containers, an external feature store (e.g. Feast / Redis / PostgreSQL) would be required. For the current single-instance deployment, SQLite is fully adequate.
- **Pre-existing Deprecation Warning**: One external framework deprecation warning (`starlette\_exception_handler.py:59: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated`) was observed from Starlette during 422 validation tests. This is purely upstream in FastAPI/Starlette and does not impact FinTrustX code.

---

## 4. Conclusion & Verdict

**VERDICT: APPROVE**

All requirements from `ORIGINAL_REQUEST.md` (R1–R4, AC3, AC4) and `orchestrator_2/PROJECT.md` have been empirically validated and verified:
1. Feature merge semantics strictly enforce `User Explicit Overrides > SQLite Historical Records > Schema Defaults`.
2. Unsupplied fields preserve historical values without schema default clobbering.
3. Legacy and edge-case applicant IDs (omitted, null, negative, unknown, alias) execute gracefully with zero 500 errors.
4. Preprocessing vectorized concatenation completely eliminates Pandas `PerformanceWarning` and DataFrame fragmentation across 100+ simulated requests.
5. All 15 integration tests in `api/tests/test_prediction.py` pass cleanly in 4.65 seconds.

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Execute Full Prediction Integration & Stress Suite**:
   ```bash
   python -m pytest api/tests/test_prediction.py -v
   ```
   **Expected**: 15 passed, 0 failures, 0 PerformanceWarning in $< 5$s.

2. **Inspect Specific Feature Merge Override Tests**:
   ```bash
   python -m pytest api/tests/test_prediction.py -k "overrides_historical or default_clobbering" -v
   ```
   **Expected**: 2 passed.

3. **Inspect 100+ Simulated Request Warning Stress Test**:
   ```bash
   python -m pytest api/tests/test_prediction.py -k "test_preprocessing_stress_100_plus_simulated_requests_zero_warnings" -v
   ```
   **Expected**: 1 passed with 0 fragmentation warnings.
