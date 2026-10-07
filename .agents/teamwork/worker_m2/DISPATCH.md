## 2026-10-05T19:32:54Z
You are Worker M2: Backend & Preprocessing Engineer.
Working directory: d:\Projects\Credit-risk-ai\.agents\teamwork\worker_m2
Project Root: d:\Projects\Credit-risk-ai

You MUST read the following files before writing any code:
1. `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Projects\Credit-risk-ai\project.md`
3. `d:\Projects\Credit-risk-ai\GEMINI.md`
4. `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_2\PROJECT.md`
5. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_2\report.md`
6. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_2\handoff.md`
7. `d:\Projects\Credit-risk-ai\TEST_READY.md`

File Ownership:
You have exclusive write ownership over:
- `api/config.py`
- `api/schemas.py`
- `api/feature_store.py` (new)
- `api/dependencies.py`
- `api/services/prediction_service.py`
- `api/services/explanation_service.py`
- `api/preprocessing.py`
You MUST NOT edit files in `frontend/` or `scripts/`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Implement `api/feature_store.py`:
   - `FeatureStore` class querying `FEATURE_STORE_DB_PATH` (default `data/feature_store.db`, table `applicant_features`).
   - `get_applicant_features(sk_id_curr: int) -> Optional[Dict[str, Any]]`: Returns dict of historical feature name -> value, or None if not found or DB missing.
   - `get_batch_applicant_features(sk_id_currs: List[int]) -> Dict[int, Dict[str, Any]]`: Efficient batch lookup using `WHERE SK_ID_CURR IN (...)`.
   - Thread-safe connection handling using `sqlite3.connect` with `sqlite3.Row` and WAL mode compatibility.
   - Defensive: If DB file doesn't exist, log warning and return None/empty dict gracefully without crashing.
2. Update `api/config.py`:
   - Add `FEATURE_STORE_DB_PATH = Path(os.getenv("FEATURE_STORE_DB_PATH", str(DATA_DIR / "feature_store.db")))` and `FEATURE_STORE_TABLE_NAME = "applicant_features"`.
3. Update `api/schemas.py`:
   - Ensure `CreditRiskRequest` supports `SK_ID_CURR: Optional[int]`.
   - Add `PredictionRequest = CreditRiskRequest` alias (or model) to fix any latent import references.
4. Update `api/dependencies.py`:
   - Add `get_feature_store()` singleton dependency returning `FeatureStore(FEATURE_STORE_DB_PATH)`.
   - Wire `feature_store` into `PredictionService` and `ExplanationService` injection if applicable, or instantiate in service.
5. Update `api/services/prediction_service.py`:
   - In `predict_single`: Check if `request.SK_ID_CURR` is provided. If so, fetch features from `FeatureStore`.
   - Merge user payload with historical features: `incoming payload overrides historical features`. Specifically, use `request.model_dump(exclude_unset=True)` so schema default values do NOT overwrite real historical features!
   - In `predict_batch`: Query `FeatureStore` in batch for provided IDs and merge each accordingly.
   - If `SK_ID_CURR` is omitted or not found in DB, seamlessly use input payload (backward compatibility).
6. Update `api/services/explanation_service.py`:
   - Apply identical feature merge logic when `SK_ID_CURR` is provided so SHAP attributions reflect the merged profile.
7. Refactor `api/preprocessing.py` (lines 51–57):
   - Replace the iterative loop (`for col in raw_feature_names: df_raw[col] = np.nan`) with vectorized `pd.concat(axis=1)`:
     ```python
     missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]
     if missing_cols:
         df_missing = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)
         df_raw = pd.concat([df_raw, df_missing], axis=1)
     df_aligned = df_raw[raw_feature_names]
     ```
   - Verify that this completely eliminates the Pandas `PerformanceWarning: DataFrame is highly fragmented` warning.
8. Run the test suite:
   - Run `python -m pytest api/tests/test_prediction.py -v`
   - Verify that all tests pass, including:
     * `test_predict_with_valid_sk_id_curr_pulls_db_features`
     * `test_predict_without_sk_id_curr_backward_compatible`
     * `test_predict_with_unknown_sk_id_curr_fallback`
     * `test_zero_pandas_fragmentation_warning`
     * `test_batch_prediction_with_mixed_applicant_ids`
     * All original prediction tests.
9. Write a comprehensive handoff report at `d:\Projects\Credit-risk-ai\.agents\teamwork\worker_m2\handoff.md` detailing all changes made and test outputs.
When finished, send a brief message with your handoff path.
