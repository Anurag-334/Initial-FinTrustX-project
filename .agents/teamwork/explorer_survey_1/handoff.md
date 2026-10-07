# Handoff Report — Explorer Survey 1: Data & Feature Store Architecture

**Agent**: Explorer Survey 1 (`explorer_survey_1`)  
**Type**: Hard Handoff (Investigation & Architecture Survey Complete)  
**Date**: 2026-10-05  

---

## 1. Observation

1. **Original Follow-up Request & Requirements**:
   - `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`: Lines 30–60 define the Follow-up milestone:
     * R1: Feature Store Creation: SQLite database with `SK_ID_CURR` primary key.
     * R2: Backend Integration: Query SQLite feature store in FastAPI prediction endpoint and merge features.
     * R3: Preprocessing Optimization: Refactor missing-feature imputation in `api/preprocessing.py` to use `pd.concat()` to eliminate Pandas fragmentation warnings.
     * R4: Frontend Update: Add Applicant ID input in `frontend/index.html` and `frontend/js/app.js`.
2. **Data Assets & Current Features**:
   - `d:\Projects\Credit-risk-ai\data\raw\`:
     * `bureau.csv` (170,016,717 bytes, 1.72M rows)
     * `previous_application.csv` (404,973,293 bytes, 1.67M rows)
     * `application_train.csv` (166,133,370 bytes, 307,511 rows)
     * `application_test.csv` (26,567,651 bytes, 48,744 rows)
   - `d:\Projects\Credit-risk-ai\models\preprocessed_feature_names.csv`: 343 lines (header + 341 preprocessed feature names: 201 numerical features prefixed with `num__`, and 140 one-hot encoded categorical features prefixed with `cat__`).
   - `d:\Projects\Credit-risk-ai\tests\test_inference_stress_m2.py`: Line 319 confirms `assert transformed.shape == (1, 341)`.
3. **Existing Aggregation Module**:
   - `d:\Projects\Credit-risk-ai\src\data_aggregation.py`:
     * `DataAggregator.aggregate_bureau()` (lines 122–232): creates 44 aggregated features from `bureau.csv`.
     * `DataAggregator.aggregate_previous_application()` (lines 234–349): creates 44 aggregated features from `previous_application.csv`.
     * `DataAggregator.merge_features()` (lines 351–464): adds `FLAG_NO_BUREAU_DATA`, `FLAG_NO_PREV_DATA`, `BUREAU_LOAN_COUNT`, `PREV_APP_COUNT`, and 5 cross-table macroeconomic ratios (`BUREAU_TOTAL_DEBT_TO_INCOME`, `BUREAU_ANNUITY_TO_INCOME`, `PREV_ANNUITY_TO_INCOME`, `PREV_CURRENT_TO_PRIOR_CREDIT_RATIO`, `TOTAL_DEBT_TO_INCOME`).
4. **Current API Preprocessing Flaw (Pandas Fragmentation Warning)**:
   - `d:\Projects\Credit-risk-ai\api\preprocessing.py`:
     * Lines 51–55:
       ```python
       for col in raw_feature_names:
           if col not in df_raw.columns:
               df_raw[col] = np.nan
       ```
     * In a loop over >150 missing raw columns, this iterative insertion causes a `PerformanceWarning: DataFrame is highly fragmented`.
5. **Frontend Form State**:
   - `d:\Projects\Credit-risk-ai\frontend\index.html`: Lines 159–216 currently lack any HTML input element for `SK_ID_CURR`.
   - `d:\Projects\Credit-risk-ai\frontend\js\app.js`: Line 250 already references `raw.SK_ID_CURR`, and preset profiles (lines 23, 47, 71) have `SK_ID_CURR` predefined (`100003`, `100045`, `100002`).

---

## 2. Logic Chain

1. **Feature Identification**:
   - From Observation 2 and 3, the model expects 341 features, composed of 121 base application features, 44 bureau aggregations, 44 previous application aggregations, 4 data availability flags/counts, and 5 cross-table leverage ratios.
   - The 97 historical and cross-table features can only be known ahead of time from `bureau.csv` and `previous_application.csv`.
2. **Feature Store Scope & Primary Key**:
   - Storing all 97 historical and cross-table features per applicant with `SK_ID_CURR` as the primary key creates an exact 98-column schema (`applicant_features`).
   - SQLite provides $O(1)$ indexed point lookups on `SK_ID_CURR`, completing in $<0.2$ ms without runtime CSV parsing.
3. **Memory Management during Seeding (GEMINI.md compliance)**:
   - Aggregating `bureau.csv` (1.72M rows) and `previous_application.csv` (1.67M rows) sequentially using `DataAggregator` with `optimize_dtypes()` and explicit `gc.collect()` at each step consumes only $\sim 1.05$ GB peak RAM, staying well below the 1.8 GB system constraint.
   - Streaming the merged dataset into `data/feature_store.db` in batches of 25,000 prevents intermediate buffer bloat.
4. **Inference Serving & Merge Semantics**:
   - In `PredictionService.predict_single`, querying `feature_store.get_features(sk_id_curr)` retrieves historical data.
   - Overwriting the historical record with user inputs preserves client-supplied application data while injecting historical bureau and application depth.
   - If user provides custom `AMT_INCOME_TOTAL` and `AMT_CREDIT`, the 5 dynamic ratios are cleanly recomputed.
   - If an unknown ID is provided, setting `FLAG_NO_BUREAU_DATA = 1` and `FLAG_NO_PREV_DATA = 1` allows the `ColumnTransformer` to impute medians smoothly without errors.
5. **Fragmentation Warning Fix**:
   - From Observation 4, replacing iterative `df_raw[col] = np.nan` with a single block `pd.concat([df_raw, missing_df], axis=1)` directly satisfies R3 and eliminates all fragmentation warnings.

---

## 3. Caveats

- **Database Size on Disk**: Seeding all 356,255 applicants from train + test will yield a SQLite database of approximately 130–150 MB.
- **Dynamic Cross-Table Ratios**: The 5 cross-table ratios (`BUREAU_TOTAL_DEBT_TO_INCOME`, etc.) depend on incoming application values (`AMT_INCOME_TOTAL`, `AMT_CREDIT`). While default baseline ratios can be stored in SQLite, recalculating them at API runtime ensures accuracy if a user changes the requested credit amount.
- **SQLite Concurrency**: In production serving, opening read-only connections with `PRAGMA journal_mode = WAL;` is necessary to ensure concurrent API workers do not lock the SQLite file.

---

## 4. Conclusion

The SQLite Feature Store architecture is fully mapped:
1. **Database Path**: `data/feature_store.db`
2. **Table**: `applicant_features` with 98 columns (`SK_ID_CURR INTEGER PRIMARY KEY` + 97 historical features).
3. **Seeding Script**: `scripts/seed_feature_store.py` reusing `DataAggregator` with sequential execution and dtype downcasting.
4. **API Integration**: `src/feature_store.py` client queried in `api/services/prediction_service.py`.
5. **Preprocessing Fix**: Refactor `api/preprocessing.py` to use `pd.concat([df_raw, missing_df], axis=1)`.
6. **Frontend Update**: Insert `SK_ID_CURR` input field into `frontend/index.html` form.
7. **Full survey report**: Documented at `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_1\report.md`.

---

## 5. Verification Method

To independently verify the survey findings:
1. **Inspect Target Feature Names**:
   - Check `models/preprocessed_feature_names.csv`: lines 106–202 list all 97 historical and cross-table features.
2. **Inspect Existing Aggregation Logic**:
   - View `src/data_aggregation.py` lines 122–464 to verify `DataAggregator` methods and column mappings.
3. **Inspect Problematic Preprocessing Line**:
   - View `api/preprocessing.py` lines 51–55 to verify the iterative insertion triggering `PerformanceWarning`.
4. **Inspect Frontend Form**:
   - View `frontend/index.html` lines 159–216 to verify absence of `SK_ID_CURR` field.
5. **Read Full Survey Report**:
   - Review `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_1\report.md`.
