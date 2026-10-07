# Handoff Report — Explorer Survey 2

**Agent**: Explorer Survey 2 (FastAPI Prediction Pipeline & Preprocessing Optimization)  
**Parent**: Orchestrator (Conversation ID: 1cf94437-5dcb-4b7c-bffa-75f9de7165e0)  
**Working Directory**: `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_2`  
**Report**: `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_2\report.md`  
**Type**: Hard Handoff  

---

## 1. Observation

Direct observations and code locations from read-only investigation:

1. **Pandas Fragmentation Warning Source**:
   - File: `d:\Projects\Credit-risk-ai\api\preprocessing.py`
   - Lines 48–58:
     ```python
     # Build DataFrame ensuring all expected raw columns exist
     df_raw = pd.DataFrame(records)
     
     # Fill any unprovided raw columns with NaN so SimpleImputer handles them
     for col in raw_feature_names:
         if col not in df_raw.columns:
             df_raw[col] = np.nan

     # Reorder columns to exactly match pipeline.feature_names_in_
     df_aligned = df_raw[raw_feature_names]
     ```
   - Total raw features: `len(raw_feature_names) == 121` (from Scikit-Learn `ColumnTransformer.feature_names_in_`).
   - Incoming payload (e.g. `SAMPLE_APPLICANT` in `api/tests/test_prediction.py:19–39` or frontend request) provides 18–20 features.
   - The loop iteratively inserts >100 columns via `df_raw[col] = np.nan`, exceeding Pandas' internal fragmentation threshold (100 block insertions) and raising `pandas.errors.PerformanceWarning`.

2. **Schema State in `api/schemas.py`**:
   - File: `d:\Projects\Credit-risk-ai\api\schemas.py`
   - Line 29: `SK_ID_CURR: Optional[int] = Field(default=None, description="Unique applicant loan ID")` is already declared in `CreditRiskRequest`.
   - Line 72: `BatchCreditRiskRequest` wraps `requests: List[CreditRiskRequest]`.
   - Line 108: `applicant_id: Optional[int] = Field(default=None, description="Applicant identifier if provided")` is already declared in `PredictionResponse`.
   - Missing model: `PredictionRequest` is imported in `api/routers/predict.py:19` but does not exist in `api/schemas.py`, causing a latent `ImportError`.

3. **Current Serving & Route Architecture**:
   - File: `d:\Projects\Credit-risk-ai\api\main.py`
   - Routes: Lines 228–256 (`POST /predict`), lines 265–282 (`POST /explain`), lines 290–316 (`POST /predict/batch`).
   - All active routes are defined directly on `FastAPI(app)` in `api/main.py`. The files in `api/routers/` (`predict.py`, `health.py`) are unmounted legacy files.
   - Dependency injection in `api/dependencies.py` wires `get_loader()`, `get_predictor()`, `get_prediction_service()`, and `get_explanation_service()`.

4. **Prediction Service Logic**:
   - File: `d:\Projects\Credit-risk-ai\api\services\prediction_service.py`
   - Lines 30–45:
     ```python
     @staticmethod
     def predict_single(
         request: CreditRiskRequest,
         predictor: XGBoostPredictor,
         threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
         explain: bool = False
     ) -> PredictionResponse:
         payload = request.model_dump(exclude_none=False)
         logger.info(f"Processing prediction request (Applicant ID: {payload.get('SK_ID_CURR')}, Explain: {explain})")
         return predictor.predict_single(raw_data=payload, threshold=threshold, explain=explain)
     ```
   - Currently directly dumps `request.model_dump(exclude_none=False)` without querying any SQLite database.

5. **Missing Database Configuration**:
   - File: `d:\Projects\Credit-risk-ai\api\config.py`
   - Lines 28–38 define `PROJECT_ROOT`, `DATA_DIR`, `MODELS_DIR`, `REPORTS_DIR`, `XGBOOST_MODEL_PATH`, `PREPROCESSING_PIPELINE_PATH`.
   - No path or constant exists for the SQLite feature store database or table name.

---

## 2. Logic Chain

1. **From Observation 1 to Refactoring Proposal**:
   - Iterative column insertion `df_raw[col] = np.nan` inside a 100+ iteration loop is the exact textbook trigger for Pandas `PerformanceWarning`.
   - Creating a single NaN DataFrame `pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)` and appending all missing columns in one step via `pd.concat([df_raw, df_missing], axis=1)` allocates the underlying array blocks in a single memory operation.
   - Therefore, replacing the loop with `pd.concat(axis=1)` guarantees zero fragmentation warnings while preserving exact column names and row indices for both single-item and batch requests.

2. **From Observation 2 & 4 to Feature Merge Architecture**:
   - If an applicant provides `SK_ID_CURR`, historical features should be loaded from SQLite.
   - In Pydantic v2, `request.model_dump()` returns all schema fields with their default values (e.g. `AMT_INCOME_TOTAL: 150000.0`, `DAYS_BIRTH: -14000.0`).
   - If a caller supplies only `{"SK_ID_CURR": 100002, "AMT_CREDIT": 500000.0}`, blindly doing `{**historical, **request.model_dump()}` would cause schema defaults to overwrite real historical values.
   - Calling `request.model_dump(exclude_unset=True)` returns strictly the fields explicitly provided by the user in the incoming HTTP request.
   - Merging `{**historical, **incoming_overrides}` ensures historical data populates missing profile attributes, while incoming fields take precedence (`incoming payload overrides historical features`).
   - If `SK_ID_CURR` is not provided or not found in the DB, fallback to `request.model_dump(exclude_none=False)` preserves full backward compatibility.

3. **From Observation 3, 5 to FeatureStore Client Module Design**:
   - Creating `api/feature_store.py` with `FeatureStore` class decouples raw SQLite access from prediction orchestration.
   - Providing `get_store() -> FeatureStore` in `api/dependencies.py` and injecting it into `PredictionService` and `ExplanationService` preserves FastAPI dependency injection architecture.
   - Adding `FEATURE_STORE_DB_PATH = Path(os.getenv("FEATURE_STORE_DB_PATH", str(DATA_DIR / "feature_store.db")))` in `api/config.py` enables central management and straightforward overriding in test fixtures.

---

## 3. Caveats

1. **Database Seeding Dependency**: The runtime lookup depends on `data/feature_store.db` being created and seeded by Survey 1's seeding script (`scripts/seed_feature_store.py`). However, our client and service design is defensive: if the database file does not exist, it logs a warning and gracefully proceeds with payload features only.
2. **Table Schema Alignment**: We assumed table name `applicant_features` and primary key column name `SK_ID_CURR` with standard SQLite column names matching the Home Credit raw and aggregated feature names. This aligns with Survey 1's specification.
3. **Read-Only Inspection**: In accordance with the Explorer role, no source code was modified. Implementation must be performed by the downstream implementer/worker agent.

---

## 4. Conclusion

1. **Preprocessing Fix**: Refactor `api/preprocessing.py` lines 51–55 to use `pd.concat(axis=1)` with a single pre-allocated DataFrame of NaNs. This completely eliminates Pandas fragmentation warnings.
2. **Schema Completeness**: `CreditRiskRequest` in `api/schemas.py` already contains `SK_ID_CURR: Optional[int]`. Enhance it with documentation and a validator mapping `applicant_id` to `SK_ID_CURR`. Add `PredictionRequest` to `api/schemas.py` to fix the latent import error in `api/routers/predict.py`.
3. **Feature Store Integration**:
   - Add `api/config.py`: `FEATURE_STORE_DB_PATH` and `FEATURE_STORE_TABLE_NAME`.
   - Create `api/feature_store.py`: `FeatureStore` class with `get_applicant_features(sk_id_curr)` and `get_batch_applicant_features(sk_id_currs)` using `sqlite3.Row`.
   - Wire `FeatureStore` into `api/dependencies.py` via `get_store()`.
   - Update `api/services/prediction_service.py` to query `FeatureStore`, merge using `request.model_dump(exclude_unset=True)`, and pass merged data to `predictor`.
   - Update `api/services/explanation_service.py` with identical merge logic.
4. **Integration Testing**: Add test cases to `api/tests/test_prediction.py` verifying valid `SK_ID_CURR` DB lookup, payload override priority, backward compatibility, and zero `PerformanceWarning` during execution.

---

## 5. Verification Method

To verify the future implementation:
1. **Fragmentation Warning Check**:
   Run `pytest api/tests/test_prediction.py` with `-W error::pandas.errors.PerformanceWarning` or verify zero warnings captured via `warnings.catch_warnings(record=True)`.
2. **Feature Store Integration Test**:
   Execute integration tests with a temporary SQLite database populated with `SK_ID_CURR = 100002` to confirm historical features are loaded and payload overrides take effect.
3. **Backward Compatibility**:
   Confirm all existing tests in `api/tests/test_health.py`, `api/tests/test_model_loading.py`, and `api/tests/test_prediction.py` pass without regression.
