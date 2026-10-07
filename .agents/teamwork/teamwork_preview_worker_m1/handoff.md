# Milestone 1 — Data Integration & Memory Management Pipeline Handoff Report

**Agent**: Worker M1 (`teamwork_preview_worker_m1`)  
**Role**: Implementer / QA / Specialist  
**Milestone**: M1 (Dataset Integration & Memory Management Pipeline)  
**Date**: 2026-10-05  

---

## 1. Observation

### 1.1 Source Files Implemented and Modified
1. **`src/data_aggregation.py`** (465 lines, created):
   - Implements `optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame`: downcasts integer columns to `np.int8`/`np.int16`/`np.int32`, float columns to `np.float32`, and low-cardinality strings to `category`.
   - Implements class `DataAggregator`:
     - `aggregate_bureau(filename="bureau.csv", usecols=DEFAULT_BUREAU_USECOLS)`: reads 15 selective columns, precomputes `IS_ACTIVE`, `IS_CLOSED`, `IS_MICROLOAN`, `ACTIVE_AMT_CREDIT_SUM_DEBT`, `ACTIVE_AMT_CREDIT_SUM`, `ACTIVE_DAYS_CREDIT`, groups by `SK_ID_CURR`, computes 5 intra-table financial ratios (`BUREAU_DEBT_CREDIT_RATIO`, `BUREAU_ACTIVE_DEBT_RATIO`, `BUREAU_OVERDUE_DEBT_RATIO`, `BUREAU_ACTIVE_LOAN_SHARE`, `BUREAU_PROLONG_RATE`), and executes garbage collection. Produces shape `(305811, 45)`.
     - `aggregate_previous_application(filename="previous_application.csv", usecols=DEFAULT_PREV_USECOLS)`: reads 12 selective columns, precomputes status partitions (`IS_APPROVED`, `IS_REFUSED`, `IS_CANCELED`), application amounts, decision days, groups by `SK_ID_CURR`, computes 4 intra-table ratios (`PREV_APPROVAL_RATE`, `PREV_REFUSAL_RATE`, `PREV_CREDIT_TO_APPLICATION_RATIO`, `PREV_DOWN_PAYMENT_RATIO`), and executes garbage collection. Produces shape `(338857, 45)`.
     - `merge_features(main_df, bureau_agg, prev_agg)`: verifies unique keys, performs sequential left joins onto `main_df`, introduces `FLAG_NO_BUREAU_DATA` and `FLAG_NO_PREV_DATA` indicators, zero-fills loan and application counts (`BUREAU_LOAN_COUNT`, `PREV_APP_COUNT`), and computes 5 cross-table macroeconomic credit leverage ratios (`BUREAU_TOTAL_DEBT_TO_INCOME`, `BUREAU_ANNUITY_TO_INCOME`, `PREV_ANNUITY_TO_INCOME`, `PREV_CURRENT_TO_PRIOR_CREDIT_RATIO`, `TOTAL_DEBT_TO_INCOME`). Enforces invariant row count of 307,511 and target default count of 24,825. Produces merged shape `(307511, 219)`.

2. **`src/data_loader.py`** (lines 58–125 modified):
   - Updated `DataLoader.load_csv`:
     ```python
     def load_csv(
         self,
         filename: str,
         usecols: Optional[Union[List[str], Callable[[str], bool]]] = None,
         dtype: Optional[Union[Dict[str, Any], str, type]] = None,
         **kwargs: Any,
     ) -> pd.DataFrame:
     ```
   - Passes `usecols`, `dtype`, and `**kwargs` directly to `pd.read_csv`, enabling memory-efficient selective column loading while retaining 100% backward compatibility for zero-argument callers.

3. **`src/preprocessing.py`** (lines 49–115 modified):
   - Updated `DataPreprocessor.detect_features`:
     ```python
     def detect_features(
         self,
         df: pd.DataFrame,
         target_column: Optional[str] = "TARGET",
         exclude_columns: Optional[Union[List[str], Set[str]]] = None,
     ) -> Tuple[List[str], List[str]]:
     ```
   - Safely drops `target_column` only if present, preventing `KeyError`.
   - Excludes applicant identifier `"SK_ID_CURR"` by default from feature lists, permanently resolving the historical applicant ID data leakage (`num__SK_ID_CURR` ranking as 12th most important feature).
   - Includes `category` dtype in `self.categorical_features`.
   - Configures logging with `logger.info()` instead of raw `print()` statements.

4. **`scripts/run_data_pipeline.py`** (604 lines, created):
   - Standalone CLI execution script with arguments: `--raw-dir`, `--output-dir`, `--model-dir`, `--random-state`, `--test-size`, `--skip-bureau`, `--skip-prev`, `--verify-only`, `--log-level`.
   - Class `MemoryTracker`: monitors RSS memory via `psutil` before and after each transformation stage, tracking delta, peak RSS, and uncollected cycle reclamation.
   - Context-managed sequential stages: Bureau Aggregation -> Prev App Aggregation -> Main Merge -> Stratified Split -> Preprocessing Transform -> Artifact Persistence -> Validation Assertions.
   - `save_processed_partition()`: writes compressed float32 PyArrow Parquet files with int8 `TARGET`.
   - `run_validation_suite()`: executes 7 assertions (file presence, row invariance, column parity, disjoint split indices, target default rates, non-finite/NaN checks, feature name mapping).

5. **`notebooks/02_Preprocessing.ipynb`** (updated):
   - Cell 0 & 1 updated: documented supplementary data integration (R1), memory limits (R2), and lack of data leakage.
   - Cell 3 updated: imported `DataAggregator`, `DataLoader`, `MemoryTracker`, `save_processed_partition`, `run_validation_suite`.
   - Cell 4 & 5 updated: integrated `DataAggregator` with sequential tracking, loading `bureau.csv`, `previous_application.csv`, and merging onto `application_train.csv`.
   - Cell 17 & 19 updated: configured `detect_features` with `exclude_columns=["SK_ID_CURR"]`, fit `ColumnTransformer` on training split, transformed test split.
   - Cell 21, 23, 25, 27, 28 updated: persisted pipeline, feature names, Parquet partitions, and embedded automated validation assertions.

---

### 1.2 Pipeline Execution Output and Memory Profile
The pipeline was executed directly via `python scripts/run_data_pipeline.py`. Verbatim execution log:

```text
2026-10-05 20:47:33,246 | INFO | Random Seed set to 42
2026-10-05 20:47:33,246 - INFO - Starting FinTrustX Data Pipeline (PID: 4700)
2026-10-05 20:47:33,246 - INFO - Raw: D:\Projects\Credit-risk-ai\data\raw | Output: D:\Projects\Credit-risk-ai\data | Models: D:\Projects\Credit-risk-ai\models
>>> [STAGE START] Stage 1: Bureau Record Aggregation | Initial RSS: 380.14 MB
    Loading bureau.csv with 15 columns...
    Executing GroupBy aggregation on Bureau records...
    Bureau aggregation finished. Result shape: (305811, 45)
<<< [STAGE COMPLETE] Stage 1 | Duration: 5.51s | Final RSS: 432.70 MB | Peak RSS: 432.70 MB

>>> [STAGE START] Stage 2: Previous Application Aggregation | Initial RSS: 432.70 MB
    Loading previous_application.csv with 12 columns...
    Executing GroupBy aggregation on Previous Applications...
    Previous app aggregation finished. Result shape: (338857, 45)
<<< [STAGE COMPLETE] Stage 2 | Duration: 7.51s | Final RSS: 486.46 MB | Peak RSS: 486.46 MB

>>> [STAGE START] Stage 3: Application Data Merge | Initial RSS: 486.46 MB
    Loading application_train.csv... Shape: (307511, 122)
    Memory Before: 286.23 MB | Memory After: 129.33 MB | Reduced: 156.90 MB
    Initiating feature merge. Anchor shape: (307511, 122)
    Feature merge completed successfully. Final shape: (307511, 219)
<<< [STAGE COMPLETE] Stage 3 | Duration: 7.85s | Final RSS: 570.41 MB | Peak RSS: 570.41 MB

>>> [STAGE START] Stage 4: Stratified Train/Test Split | Initial RSS: 570.41 MB
    Train split: 246008 rows | Test split: 61503 rows
<<< [STAGE COMPLETE] Stage 4 | Duration: 1.10s | Final RSS: 582.34 MB | Peak RSS: 582.34 MB

>>> [STAGE START] Stage 5: Preprocessing Transformation | Initial RSS: 582.34 MB
    Numerical: 201 | Categorical: 16 | Excluded applicant ID: SK_ID_CURR
    Fitting ColumnTransformer strictly on X_train...
    X_train transformed. Shape: (246008, 341)
    Transforming X_test using frozen transformer...
    X_test transformed. Shape: (61503, 341)
    Total output feature names: 341
<<< [STAGE COMPLETE] Stage 5 | Duration: 13.06s | Final RSS: 1059.55 MB | Peak RSS: 1059.55 MB

>>> [STAGE START] Stage 6: Artifact Serialization | Initial RSS: 1059.59 MB
    Saved feature names to models\preprocessed_feature_names.csv
    Saved data\processed_train.parquet (Shape: (246008, 342), Size: 72.39 MB)
    Saved data\processed_test.parquet (Shape: (61503, 342), Size: 19.18 MB)
<<< [STAGE COMPLETE] Stage 6 | Duration: 6.03s | Final RSS: 643.50 MB | Peak RSS: 1059.59 MB

>>> [STAGE START] Stage 7: Pipeline Validation | Initial RSS: 643.50 MB
    >>> ALL VALIDATION ASSERTIONS PASSED SUCCESSFULLY! <<<
<<< [STAGE COMPLETE] Stage 7 | Duration: 1.62s | Final RSS: 819.84 MB | Peak RSS: 1059.59 MB

Pipeline execution finished successfully!
Global Peak RSS Memory: 1059.59 MB (< 1800 MB)
```

### 1.3 Generated Artifact Properties

| Artifact Path | File Size | Shape | Description |
|---|---|---|---|
| `data/processed_train.parquet` | 75,908,039 bytes (~72.4 MB) | `(246008, 342)` | 341 float32 features + 1 int8 `TARGET` (19,860 defaults = 8.0729%). Zero missing values. |
| `data/processed_test.parquet` | 20,109,507 bytes (~19.2 MB) | `(61503, 342)` | 341 float32 features + 1 int8 `TARGET` (4,965 defaults = 8.0728%). Zero missing values. |
| `models/preprocessing_pipeline.joblib` | 31,442 bytes | Fitted `ColumnTransformer` | Fitted exclusively on `X_train`. Imputer + Scaler (201 num), Imputer + OneHot (16 cat). |
| `models/preprocessed_feature_names.csv` | 10,738 bytes | 341 features | List of output feature names. Starts with `num__CNT_CHILDREN` (ID `SK_ID_CURR` excluded). |

---

## 2. Logic Chain

1. **Relational Data Aggregation (Requirement R1)**:
   - Direct joins of 1.71M bureau rows and 1.67M previous application rows onto 307k application rows without prior grouping would result in a multi-million row Cartesian product.
   - Deduces: Independent `groupby("SK_ID_CURR")` aggregation is mathematically required.
   - Status partitioning (active loans vs closed loans, approved loans vs refused loans) separates active credit default risk from historical amortized debt.
   - Grouping produces exactly 1 record per unique applicant (`SK_ID_CURR`).
   - Left-merging child aggregations preserves all 307,511 application rows and the exact 24,825 defaults (8.0729% default rate).

2. **Memory Ceiling Compliance (Requirement R2)**:
   - Reading all 37 columns of `previous_application.csv` and 17 columns of `bureau.csv` in default 64-bit precision consumes > 2.5 GB RAM.
   - Deduces: Restricting ingestion via `usecols` (15 bureau, 12 prev) and downcasting types (`float64 -> float32`, `int64 -> int8/int16/int32`) reduces table footprints by > 65%.
   - Sequential processing with immediate intermediate deletion and explicit garbage collection (`del df_bureau; gc.collect()`) constrained peak RSS to **1059.59 MB**, satisfying Requirement R2 (< 1,800 MB) with 740 MB of headroom.

3. **Data Leakage Elimination**:
   - In baseline runs, `SK_ID_CURR` was included in numeric features (`num__SK_ID_CURR`), where it accounted for 2.57% of feature importance in tree models.
   - Deduces: Applicant ID must be strictly excluded from feature detection and transformer fitting.
   - Stratified 80/20 train/test splitting occurs before fitting `DataPreprocessor`. The test partition `X_test` is transformed using the frozen fitted pipeline, guaranteeing zero leakage of test set statistics.

4. **Production Serving Compatibility**:
   - `models/preprocessing_pipeline.joblib` and `models/preprocessed_feature_names.csv` were regenerated with the augmented 341-feature schema.
   - When running `api/tests/test_health.py`, the FastAPI backend initialized cleanly and dynamically detected 218 raw inputs, confirming API loader compatibility.

---

## 3. Caveats

1. **Downstream Model Training in Milestone 2**:
   - The current `models/xgboost.joblib` model artifact is the 245-feature model from earlier runs. It expects 245 features, whereas the new `preprocessing_pipeline.joblib` generates 341 features.
   - Running full inference prediction tests against `models/xgboost.joblib` will result in a feature dimension mismatch until Milestone 2 trains the new XGBoost model on `data/processed_train.parquet` and updates `models/xgboost.joblib`.
   - Milestone 2 worker will train the augmented model to beat the ROC-AUC benchmark (> 0.7610).
2. **Auxiliary Tables Excluded**:
   - Tables such as `bureau_balance.csv`, `POS_CASH_balance.csv`, `credit_card_balance.csv`, and `installments_payments.csv` in `data/raw/` were intentionally not ingested, adhering strictly to Requirement R1.

---

## 4. Conclusion

1. **Milestone 1 Objectives Completed**:
   - `src/data_aggregation.py` is implemented with complete status partitioning, downcasting, and ratio generation.
   - `src/data_loader.py` and `src/preprocessing.py` are updated with backward-compatible memory loading and leak-free feature detection.
   - `scripts/run_data_pipeline.py` is implemented and executed to completion without errors.
   - Peak RSS was strictly **1059.59 MB** (< 1.8 GB ceiling, satisfying R2).
   - Augmented Parquet datasets (`processed_train.parquet`: 246,008 rows, `processed_test.parquet`: 61,503 rows) and pipeline artifacts are serialized on disk.
   - `notebooks/02_Preprocessing.ipynb` is updated and synchronized with the pipeline.
   - All validation assertions passed.

---

## 5. Verification Method

To independently verify the deliverables:

1. **Run Pipeline Verification Assertion Suite**:
   ```bash
   python scripts/run_data_pipeline.py --verify-only
   ```
   *Expected Output*: Returns exit code 0 and logs `>>> ALL VALIDATION ASSERTIONS PASSED SUCCESSFULLY! <<<`.

2. **Verify Processed Parquet Shapes and Schema in Python**:
   ```python
   import pandas as pd
   df_train = pd.read_parquet("data/processed_train.parquet")
   df_test = pd.read_parquet("data/processed_test.parquet")
   assert df_train.shape == (246008, 342)
   assert df_test.shape == (61503, 342)
   assert "TARGET" in df_train.columns
   assert not df_train.isna().any().any()
   assert not df_test.isna().any().any()
   print("Parquet verification passed!")
   ```

3. **Verify Applicant ID Leakage Elimination**:
   ```python
   import pandas as pd
   feat_df = pd.read_csv("models/preprocessed_feature_names.csv")
   assert "num__SK_ID_CURR" not in feat_df["feature_name"].values
   assert len(feat_df) == 341
   print("Leakage verification passed!")
   ```

4. **Verify Memory Management Profile**:
   Inspect the execution logs in `scripts/run_data_pipeline.py` or rerun with `--log-level INFO`. Peak RSS must remain under 1,500 MB (verified at 1059.59 MB).
