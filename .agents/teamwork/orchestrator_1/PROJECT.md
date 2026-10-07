# Project: FinTrustX Supplementary Dataset Integration & Model Optimization

## Architecture
- **Data Ingestion & Aggregation (`src/data_aggregation.py`)**:
  - Class `DataAggregator`: ingests `bureau.csv` and `previous_application.csv` using selective column filtering, downcasting, and status-partitioned `groupby("SK_ID_CURR")` aggregations.
  - Generates curated numerical metrics, active/closed partitions, approved/refused partitions, and derived financial leverage ratios.
  - Left-joins onto `application_train.csv` (preserving 307,511 rows).
- **Memory Management (R2)**:
  - Downcasting `float64 -> float32`, `int64 -> int32/int16/int8`, strings to `category`.
  - Sequential processing with explicit `gc.collect()` between table transformations.
  - Peak memory usage strictly capped under 1.8 GB (verified at 1059.59 MB).
- **Preprocessing Pipeline (`src/preprocessing.py`)**:
  - Integrated with `DataPreprocessor`: dynamic detection routes newly added `BUREAU_*` and `PREV_*` columns to `SimpleImputer(median)` and `StandardScaler()`.
  - Excludes applicant identifier `SK_ID_CURR` from features to eliminate data leakage.
  - Saves refitted `models/preprocessing_pipeline.joblib`, `models/preprocessed_feature_names.csv`, and parquet files `data/processed_train.parquet`, `data/processed_test.parquet`.
- **Model Training & Benchmarking (`src/training/train_augmented_xgboost.py`)**:
  - Trains XGBoost with `tree_method="hist"`, subsampling (`colsample_bytree=0.7`, `subsample=0.8`), early stopping (`early_stopping_rounds=50`), and refit on full 246,008 train samples with 970 trees.
  - Evaluates on the exact 80/20 stratified held-out test set (61,503 samples, random seed 42) using `src/evaluate.py`.
  - Achieves test ROC-AUC **0.779383** (beating 0.7610 baseline by +0.018345).
  - Saves `models/xgboost.joblib`, `models/xgboost.json`, and updates `reports/model_comparison.csv` and `reports/business_metrics.csv`.
- **Production Serving Compatibility (`api/`)**:
  - Compatible with `api/model_loader.py` and `api/preprocessing.py` (smoke test passed, `api/tests/test_prediction.py` 5/5 passed).

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Bureau Record Aggregation | Groupby `SK_ID_CURR` on `bureau.csv` (counts, loan amounts, debt sums, overdue days) | M1 | Survey (Explorer 1 & 2) |
| 2 | Bureau Status Partitioning | Separate aggregations for active loans (`CREDIT_ACTIVE == 'Active'`) vs closed loans | M1 | Survey (Explorer 1) |
| 3 | Bureau Financial Leverage Ratios | Debt-to-credit ratio, active debt ratio, overdue debt ratio | M1 | Survey (Explorer 1) |
| 4 | Previous App Aggregation | Groupby `SK_ID_CURR` on `previous_application.csv` (counts, annuity, credit amounts, decision days) | M1 | Survey (Explorer 1 & 2) |
| 5 | Previous App Underwriting Status | Separate aggregations for approved vs refused applications, refusal rate calculation | M1 | Survey (Explorer 1 & 2) |
| 6 | Previous App Leverage Ratios | Application-to-credit ratio, down payment ratio | M1 | Survey (Explorer 1) |
| 7 | Cross-Table Financial Ratios | Bureau debt to current income, previous credit to current credit step-up ratio | M1 | Survey (Explorer 1 & 2) |
| 8 | Memory Optimization Architecture | Downcasting types, selective usecols, sequential execution, explicit gc.collect() | M1 | Survey (Explorer 1 & 2) |
| 9 | Dataset Merging & Integrity | Left merge onto `application_train.csv` (preserving 307,511 rows, 0 duplicate keys) | M1 | Survey (Explorer 1 & 2) |
| 10 | Preprocessing Pipeline Refit | Dynamic feature routing in `DataPreprocessor`, saving pipeline and parquet partitions | M1 | Survey (Explorer 2) |
| 11 | Reproducible Pipeline Script | CLI script `scripts/run_data_pipeline.py` and companion notebook documentation | M1 | Survey (Explorer 2) |
| 12 | XGBoost Model Architecture Enhancement | Support hyperparameters, histogram tree method, early stopping in `src/models/xgboost_model.py` | M2 | Survey (Explorer 3) |
| 13 | Augmented Model Training Pipeline | Training script `src/training/train_augmented_xgboost.py` with validation early stopping | M2 | Survey (Explorer 3) |
| 14 | Metric Benchmark & Champion Evaluation | Calculate 11 classification metrics + 6 business metrics via `src/evaluate.py`, beating ROC-AUC 0.7610 | M2 | Survey (Explorer 3) |
| 15 | Model Artifact Persistence | Save `models/xgboost.joblib`, `models/xgboost.json`, and update `reports/model_comparison.csv` | M2 | Survey (Explorer 3) |
| 16 | Production Serving Smoke Test | Verify `api/model_loader.py` smoke test passes with updated model and pipeline artifacts | M2 | Survey (Explorer 2 & 3) |
| 17 | E2E Acceptance Verification | Test suite validating data shapes, zero OOM, script reproducibility, ROC-AUC > 0.7610 | M3 | Survey (All) |
| 18 | Adversarial Stress & Integrity Audit | Challenger testing and Forensic Auditor verification | M3 | Survey (All) |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Dataset Integration & Memory Management Pipeline | `src/data_aggregation.py`, `src/data_loader.py`, `scripts/run_data_pipeline.py`, preprocessing refit | none | DONE (peak RSS 1059.59 MB, parquet partitions & pipeline saved) |
| M2 | Augmented Model Training & Benchmark Evaluation | `src/models/xgboost_model.py`, `src/training/train_augmented_xgboost.py`, training, evaluation | M1 | DONE (ROC-AUC 0.779383 > 0.7610, model & reports saved) |
| M3 | End-to-End Verification & Audit Hardening | Test suite, challenger empirical testing, forensic audit, acceptance validation | M1, M2 | DONE (Verified across 55 tests, full forensic audit CLEAN) |

---

## Interface Contracts

### `src/data_aggregation.py` ↔ Preprocessing & Modeling
- **Class `DataAggregator`**:
  - `aggregate_bureau(filename: str = "bureau.csv") -> pd.DataFrame`: returns DataFrame with unique `SK_ID_CURR` index/column and prefixed columns `BUREAU_*`. Output shape: `(305811, 45)`.
  - `aggregate_previous_application(filename: str = "previous_application.csv") -> pd.DataFrame`: returns DataFrame with unique `SK_ID_CURR` index/column and prefixed columns `PREV_*`. Output shape: `(338857, 45)`.
  - `merge_features(main_df: pd.DataFrame, bureau_agg: pd.DataFrame, prev_agg: pd.DataFrame) -> pd.DataFrame`: performs sequential left merges, returning shape `(307511, 219)` without duplicate rows or index corruption.
- **Output Data Artifacts**:
  - `data/processed_train.parquet`: 246,008 rows x 342 cols (341 float32 features + 1 int8 TARGET).
  - `data/processed_test.parquet`: 61,503 rows x 342 cols (341 float32 features + 1 int8 TARGET).
  - `models/preprocessing_pipeline.joblib`: fitted `ColumnTransformer` (201 numeric, 16 categorical inputs -> 341 outputs).
  - `models/preprocessed_feature_names.csv`: CSV containing 341 preprocessed feature names.

### Modeling ↔ Evaluation & Serving
- **Class `XGBoostModel` / `train_augmented_xgboost.py`**:
  - Exposes `.fit(X_train, y_train, eval_set=..., early_stopping_rounds=...)` and `.predict_proba(X)`.
  - Output Model Artifact: `models/xgboost.joblib` containing the trained 970-tree estimator (341 features).
  - Evaluation Output: `reports/model_comparison.csv` with ROC-AUC 0.779383.
  - Serving Contract: `api/model_loader.py` successfully loads `models/xgboost.joblib` and passes `loader.run_smoke_test()`. All 5 tests in `api/tests/test_prediction.py` pass.

---

## Code Layout
- `src/data_aggregation.py`: Aggregation logic for supplementary datasets (`DataAggregator`).
- `src/data_loader.py`: Enhanced `load_csv()` with optional `usecols` and `dtype`.
- `src/preprocessing.py`: Enhanced `detect_features()` with safe target drop and `SK_ID_CURR` exclusion.
- `src/models/xgboost_model.py`: Flexible `XGBoostModel` supporting hyperparameters.
- `src/training/train_augmented_xgboost.py`: End-to-end training and evaluation script.
- `scripts/run_data_pipeline.py`: Reproducible CLI pipeline script.
- `tests/test_adversarial_m1.py` & `tests/test_data_integrity_challenger.py`: M1 adversarial test suites (22 tests).
- `tests/test_inference_stress_m2.py` & `tests/test_adversarial_m2_challenger.py`: M2 inference and metric verification test suites (33 tests).
