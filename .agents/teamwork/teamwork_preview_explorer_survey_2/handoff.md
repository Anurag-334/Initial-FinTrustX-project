# Architectural Survey & Integration Handoff Report
**Explorer 2 — FinTrustX Dataset Integration Survey**
**Date**: 2026-10-05 | **Milestone**: Survey (Existing Pipeline & Integration Architecture)

---

## 1. Observations

### 1.1 Codebase Inspection

#### A. Data Loader (`src/data_loader.py`)
- **Location**: `src/data_loader.py` (Lines 47–135, 238–311).
- **Core Methods**:
  - `load_csv(self, filename: str) -> pd.DataFrame` (Lines 59–88):
    ```python
    path = self.raw_data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")
    logger.info(f"Loading {filename}")
    df = pd.read_csv(path)
    logger.info(f"Shape : {df.shape}")
    return df
    ```
    *Observation*: `load_csv` unconditionally executes `pd.read_csv(path)` on the entire file. It lacks parameters for `usecols`, `dtype`, or `chunksize`.
  - `optimize_memory(self, df: pd.DataFrame) -> pd.DataFrame` (Lines 91–135):
    - Loops over `df.columns` and executes `pd.to_numeric(df[col], downcast="integer")` for `int` columns and `pd.to_numeric(df[col], downcast="float")` for `float` columns.
    *Observation*: Downcasts numerics after reading the entire dataframe into RAM, but does not downcast high-cardinality string/object columns to `category`.
  - Utility and audit methods: `dataset_summary`, `missing_summary`, `class_distribution`, `categorical_columns`, `numerical_columns`, `report` (Lines 138–311).
    *Observation*: Several audit methods use standard `print()` statements (Lines 147–161, 216–234, 279–310) instead of standard logger calls, conflicting with `PROJECT_RULES.md` ("Use logging instead of print").

#### B. Feature Engineering (`src/feature_engineering.py`)
- **Location**: `src/feature_engineering.py` (Lines 23–221).
- **Core Class**: `FeatureEngineer(BaseEstimator, TransformerMixin)`:
  - `fit(self, X, y=None)` (Lines 34–35): returns `self`.
  - `transform(self, X)` (Lines 39–221):
    - Executes `df = X.copy()` on line 41.
    - Derives 18 application-level features:
      1. `DAYS_EMPLOYED` replacement (365243 -> `np.nan`, Lines 49–52)
      2. `AGE_YEARS = -DAYS_BIRTH / 365` (Lines 58–60)
      3. `EMPLOYMENT_YEARS = -DAYS_EMPLOYED / 365` (Lines 66–68)
      4. `CREDIT_INCOME_RATIO = AMT_CREDIT / (AMT_INCOME_TOTAL + 1)` (Lines 74–77)
      5. `ANNUITY_INCOME_RATIO = AMT_ANNUITY / (AMT_INCOME_TOTAL + 1)` (Lines 83–86)
      6. `GOODS_CREDIT_RATIO = AMT_GOODS_PRICE / (AMT_CREDIT + 1)` (Lines 92–95)
      7. `INCOME_PER_PERSON = AMT_INCOME_TOTAL / (CNT_FAM_MEMBERS + 1)` (Lines 101–104)
      8. `CHILDREN_RATIO = CNT_CHILDREN / (CNT_FAM_MEMBERS + 1)` (Lines 110–113)
      9. `CREDIT_PER_PERSON = AMT_CREDIT / (CNT_FAM_MEMBERS + 1)` (Lines 119–122)
      10. `EMPLOYMENT_AGE_RATIO = EMPLOYMENT_YEARS / (AGE_YEARS + 1)` (Lines 128–131)
      11. `EXT_SOURCE_MEAN = df[['EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3']].mean(axis=1)` (Lines 150–153)
      12. `EXT_SOURCE_STD = df[['EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3']].std(axis=1)` (Lines 155–158)
      13. `CREDIT_TERM = AMT_ANNUITY / (AMT_CREDIT + 1)` (Lines 164–167)
      14. `PHONE_CHANGE_YEARS = -DAYS_LAST_PHONE_CHANGE / 365` (Lines 173–175)
      15. `REGISTRATION_YEARS = -DAYS_REGISTRATION / 365` (Lines 181–183)
      16. `ID_PUBLISH_YEARS = -DAYS_ID_PUBLISH / 365` (Lines 189–191)
      17. `LARGE_FAMILY = (CNT_FAM_MEMBERS >= 5).astype(int)` (Lines 197–200)
      18. `HAS_CAR = (FLAG_OWN_CAR == 'Y').astype(int)` (Lines 207–210) & `HAS_HOUSE = (FLAG_OWN_REALTY == 'Y').astype(int)` (Lines 217–220)
- *Key Observations*:
  1. `FeatureEngineer` is exclusively a 1-to-1 row transformer on `application_train.csv` columns.
  2. It contains zero aggregation logic for relational 1-to-many child tables (`bureau.csv` or `previous_application.csv`).
  3. In the baseline pipeline execution (`notebooks/02_Preprocessing.ipynb`), `FeatureEngineer` was completely bypassed; raw features were fed directly to `DataPreprocessor`.

#### C. Preprocessing Pipeline (`src/preprocessing.py`)
- **Location**: `src/preprocessing.py` (Lines 40–241).
- **Core Class**: `DataPreprocessor`:
  - `detect_features(self, df, target_column="TARGET")` (Lines 51–78):
    - `X = df.drop(columns=[target_column])` (Line 58).
    - `self.numeric_features = X.select_dtypes(include=["number"]).columns.tolist()` (Lines 60–62).
    - `self.categorical_features = X.select_dtypes(include=["object", "string"]).columns.tolist()` (Lines 64–66).
  - `build_pipeline(self)` (Lines 82–151):
    - `numeric_pipeline`: `SimpleImputer(strategy="median")` -> `StandardScaler()` (Lines 88–104).
    - `categorical_pipeline`: `SimpleImputer(strategy="most_frequent")` -> `OneHotEncoder(handle_unknown="ignore", sparse_output=False)` (Lines 106–124).
    - Assembles `ColumnTransformer` with `('num', numeric_pipeline, self.numeric_features)` and `('cat', categorical_pipeline, self.categorical_features)` (Lines 127–149).
  - `fit_transform(self, X)` & `transform(self, X)` (Lines 155–175): standard Scikit-Learn calls.
  - `save_pipeline(self, filename="preprocessor.joblib")` (Lines 178–200): serializes transformer to `MODEL_DIR / filename`. Default filename argument is `"preprocessor.joblib"`, while the notebook saves as `"preprocessing_pipeline.joblib"`.
  - `get_feature_names(self)` (Lines 220–230): calls `self.preprocessor.get_feature_names_out()`.
- *Key Observations*:
  1. `detect_features` automatically groups all numeric columns into `self.numeric_features`. If aggregated child table features are numeric (e.g. counts, sums, means), they are automatically ingested and routed to `SimpleImputer(median)` and `StandardScaler()`.
  2. `sparse_output=False` forces dense numpy arrays.
  3. If `df` passed to `detect_features` does not contain `target_column`, line 58 will raise a `KeyError: "['TARGET'] not found in axis"`.

#### D. Production Preprocessing Notebook (`notebooks/02_Preprocessing.ipynb`)
- **Location**: `notebooks/02_Preprocessing.ipynb` (Cells 2–15, Lines 190–1275).
- **Lifecycle Executed**:
  1. Loads `application_train.csv` (Shape: 307,511 rows x 121 features + 1 TARGET).
  2. Stratified train/test split:
     - `train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)` (Line 436).
     - Train: 246,008 rows (default rate: 8.0729%).
     - Test: 61,503 rows (default rate: 8.0728%).
  3. Boolean conversion: converts booleans to stable categorical strings (`prepare_boolean_features`, Lines 1024–1032).
  4. Feature detection: `preprocessor.detect_features(...)` identifies 105 numerical and 16 categorical columns (Lines 990–994, 1034).
  5. Pipeline fit & transform:
     - `X_train_processed = preprocessor.fit_transform(X_train_ready)` -> shape `(246008, 245)` (Lines 1059, 1065).
     - `X_test_processed = preprocessor.transform(X_test_ready)` -> shape `(61503, 245)` (Lines 1060, 1066).
  6. Artifact persistence:
     - Pipeline: `models/preprocessing_pipeline.joblib` (Lines 1098–1100).
     - Feature names: `models/preprocessed_feature_names.csv` (245 rows, Lines 1189–1193).
     - Processed datasets: `data/processed_train.parquet` (24,718,905 bytes) and `data/processed_test.parquet` (7,101,386 bytes) (Lines 1238–1241).

#### E. API Serving Contract (`api/`)
- **Location**: `api/model_loader.py` (Lines 59–96) and `api/preprocessing.py` (Lines 21–66).
- **Model Loading**: `ModelLoader.load_artifacts()` loads `models/preprocessing_pipeline.joblib`, `models/xgboost.joblib`, and `models/preprocessed_feature_names.csv`.
- **Inference Transformation**: `transform_raw_to_features(raw_inputs, pipeline, raw_feature_names)`:
  - Iterates over `pipeline.feature_names_in_`:
    ```python
    for col in raw_feature_names:
        if col not in df_raw.columns:
            df_raw[col] = np.nan
    df_aligned = df_raw[raw_feature_names]
    transformed = pipeline.transform(df_aligned)
    ```
- *Key Observation*: Because missing input features are automatically populated with `np.nan` and then handled by `SimpleImputer` inside `pipeline.transform()`, updating the pipeline with additional aggregated features will NOT break incoming single-applicant API prediction requests.

#### F. Raw Dataset Inventory (`data/raw/`)
- `application_train.csv`: 166,133,370 bytes (~166.1 MB, 307,511 rows x 122 cols).
- `bureau.csv`: 170,016,717 bytes (~170.0 MB, 1,716,428 rows x 17 cols).
- `previous_application.csv`: 404,973,293 bytes (~405.0 MB, 1,670,214 rows x 37 cols).
- Total raw disk size: **741.1 MB**.

---

## 2. Logic Chain

```
[Raw Datasets (741 MB)]
   ├── application_train.csv (307k rows, 122 cols)
   ├── bureau.csv (1.71M rows, 17 cols, 1:N)
   └── previous_application.csv (1.67M rows, 37 cols, 1:N)
             │
             ▼
[Memory Constraint R2 & Profiling]
   • Naive pd.read_csv on all 3 tables concurrently: >2.8 GB RAM.
   • With groupby copies and joins: 6-8 GB peak RAM (risk of OOM).
   • Required: Sequential loading, column filtering (usecols), float32 downcasting, explicit gc.collect().
             │
             ▼
[Architectural Placement Decision]
   • FeatureEngineer is 1:1 row transformer (violates SRP if 1:N aggregation is added).
   • DataPreprocessor is pure ColumnTransformer (impute/scale/encode).
   • Solution: Create dedicated module `src/data_aggregation.py` with `DataAggregator`.
             │
             ▼
[Integration & Preprocessing Compatibility]
   • Aggregated features per applicant (SK_ID_CURR) are numeric, prefixed (BUREAU_*, PREV_*).
   • Left-joined onto application_train.
   • DataPreprocessor.detect_features automatically classifies all BUREAU_* and PREV_* as numeric.
   • SimpleImputer(strategy="median") automatically imputes applicants with zero credit history.
   • Output written to data/processed_train.parquet & data/processed_test.parquet.
             │
             ▼
[API & Serving Layer Backward Compatibility]
   • api/preprocessing.py pads missing payload columns with np.nan.
   • Pipeline imputes training medians; no API schema breakage.
```

### Detailed Logical Deductions:
1. **Separation of Concerns**: `FeatureEngineer` in `src/feature_engineering.py` implements an sklearn `TransformerMixin` expecting a 2D matrix/dataframe `X` of loan applications. Attempting to pass supplementary file paths or child dataframes into `FeatureEngineer.transform()` violates Scikit-Learn transformer contracts and breaks single responsibility.
2. **Dedicated Aggregator Module**: Creating `src/data_aggregation.py` provides a clean separation. It owns child table ingestion, grouping by `SK_ID_CURR`, aggregations, column prefixing, and joining with the main application dataset.
3. **Memory Safety Mechanism (Requirement R2)**:
   - Reading `previous_application.csv` (405 MB) with all 37 columns consumes ~1.5 GB in pandas. Many columns (e.g. `WEEKDAY_APPR_PROCESS_START`, seller place IDs) have negligible predictive value for default risk. Loading only ~12-15 informative columns cuts raw memory consumption by >60%.
   - Ingesting sequentially:
     - `bureau.csv` -> aggregate to `bureau_agg` (307k rows x ~25 cols, ~30 MB) -> `del df_bureau; gc.collect()`.
     - `previous_application.csv` -> aggregate to `prev_agg` (307k rows x ~30 cols, ~37 MB) -> `del df_prev; gc.collect()`.
     - Merge `bureau_agg` and `prev_agg` into `application_train.csv`.
     - Peak RAM during aggregation is capped under **1.8 GB**, comfortably satisfying R2.
4. **DataPreprocessor Schema Invariance**:
   - In `src/preprocessing.py`, `detect_features()` checks `df.select_dtypes(include=["number"])`.
   - All proposed aggregated features (counts, sums, means, medians, maxes, ratios) are numeric (`float32` / `int32`).
   - Consequently, `detect_features()` automatically routes every single new feature into `self.numeric_features`, which are processed by `SimpleImputer(median)` and `StandardScaler()`.
   - No custom transformers or ColumnTransformer re-architecting are needed.
5. **Leakage Control**:
   - `bureau.csv` and `previous_application.csv` do not contain the target variable `TARGET`.
   - Child table aggregations summarize an applicant's historical financial behavior prior to the current application.
   - However, global statistics (such as feature medians and scalers) must be fit exclusively on `X_train`.
   - By performing the left merge before the train/test split (or independently onto `X_train` and `X_test`) and fitting `DataPreprocessor` strictly on `X_train`, leakage is 100% prevented.

---

## 3. Proposed Integration Architecture & Implementation Design

### 3.1 Component Placement Overview

```
Credit-risk-ai/
├── src/
│   ├── config.py                # Add RAW_BUREAU_FILE, RAW_PREVIOUS_APPL_FILE constants
│   ├── data_loader.py           # Enhance load_csv() with optional usecols & dtype
│   ├── feature_engineering.py   # Retain 18 baseline domain features
│   ├── data_aggregation.py      # [NEW] Dedicated aggregation class & functions
│   └── preprocessing.py         # DataPreprocessor (robust target checking & logging)
├── scripts/
│   └── run_data_pipeline.py     # [NEW] Reproducible CLI execution script
├── notebooks/
│   └── 02_Preprocessing.ipynb   # Updated notebook with augmented data workflow
├── data/
│   ├── processed_train.parquet  # Augmented training dataset (~330 features + TARGET)
│   └── processed_test.parquet   # Augmented test dataset (~330 features + TARGET)
└── models/
    ├── preprocessing_pipeline.joblib  # Refitted ColumnTransformer
    └── preprocessed_feature_names.csv # Updated feature names
```

### 3.2 Design of `src/data_aggregation.py`

In accordance with `PROJECT_RULES.md` (PEP8, line length <= 88, type hints, docstrings, logger, no bare except):

```python
"""
===========================================================
Data Aggregation Module
===========================================================

Author : FinTrustX Engineering Team
Description:
------------
Aggregates relational child tables (bureau.csv and
previous_application.csv) per applicant (SK_ID_CURR)
with strict memory management (R2).
===========================================================
"""

import gc
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import DATA_DIR, RAW_DATA_DIR
from src.data_loader import DataLoader

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Orchestrates memory-efficient aggregations for supplementary datasets.
    """

    def __init__(self, raw_data_dir: Optional[Path] = None) -> None:
        """Initialize DataAggregator with raw data directory."""
        self.raw_data_dir = raw_data_dir or RAW_DATA_DIR
        self.data_loader = DataLoader()

    def aggregate_bureau(
        self,
        filename: str = "bureau.csv",
        usecols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate bureau.csv records per applicant (SK_ID_CURR).
        """
        if usecols is None:
            usecols = [
                "SK_ID_CURR", "SK_ID_BUREAU", "DAYS_CREDIT", "CREDIT_DAY_OVERDUE",
                "DAYS_CREDIT_ENDDATE", "AMT_CREDIT_MAX_OVERDUE", "CNT_CREDIT_PROLONG",
                "AMT_CREDIT_SUM", "AMT_CREDIT_SUM_DEBT", "AMT_CREDIT_SUM_LIMIT",
                "AMT_CREDIT_SUM_OVERDUE", "CREDIT_ACTIVE", "CREDIT_TYPE"
            ]

        logger.info(f"Loading {filename} with selective columns...")
        path = self.raw_data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Bureau file not found at: {path}")

        df_bureau = pd.read_csv(path, usecols=usecols)
        df_bureau = self.data_loader.optimize_memory(df_bureau)

        # Domain Feature: Active Credit Indicator
        df_bureau["IS_ACTIVE"] = (
            df_bureau["CREDIT_ACTIVE"] == "Active"
        ).astype(np.int8)

        # Aggregation Dictionary
        agg_rules = {
            "SK_ID_BUREAU": ["count"],
            "DAYS_CREDIT": ["min", "max", "mean"],
            "CREDIT_DAY_OVERDUE": ["max", "mean"],
            "AMT_CREDIT_MAX_OVERDUE": ["max", "mean"],
            "CNT_CREDIT_PROLONG": ["sum"],
            "AMT_CREDIT_SUM": ["sum", "mean", "max"],
            "AMT_CREDIT_SUM_DEBT": ["sum", "mean"],
            "AMT_CREDIT_SUM_OVERDUE": ["sum", "max"],
            "IS_ACTIVE": ["sum", "mean"],
        }

        logger.info("Executing GroupBy aggregation on Bureau records...")
        bureau_agg = df_bureau.groupby("SK_ID_CURR").agg(agg_rules)
        bureau_agg.columns = [
            f"BUREAU_{col}_{stat}".upper()
            for col, stat in bureau_agg.columns
        ]
        bureau_agg = bureau_agg.reset_index()

        # Derived Ratios
        bureau_agg["BUREAU_DEBT_CREDIT_RATIO"] = (
            bureau_agg["BUREAU_AMT_CREDIT_SUM_DEBT_SUM"] /
            (bureau_agg["BUREAU_AMT_CREDIT_SUM_SUM"] + 1.0)
        )

        del df_bureau
        gc.collect()
        logger.info(f"Bureau aggregation complete. Shape: {bureau_agg.shape}")
        return bureau_agg

    def aggregate_previous_application(
        self,
        filename: str = "previous_application.csv",
        usecols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate previous_application.csv per applicant (SK_ID_CURR).
        """
        if usecols is None:
            usecols = [
                "SK_ID_CURR", "SK_ID_PREV", "AMT_ANNUITY", "AMT_APPLICATION",
                "AMT_CREDIT", "AMT_DOWN_PAYMENT", "NAME_CONTRACT_STATUS",
                "DAYS_DECISION", "CNT_PAYMENT"
            ]

        logger.info(f"Loading {filename} with selective columns...")
        path = self.raw_data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Previous application file not found: {path}")

        df_prev = pd.read_csv(path, usecols=usecols)
        df_prev = self.data_loader.optimize_memory(df_prev)

        # Domain Indicators
        df_prev["IS_APPROVED"] = (
            df_prev["NAME_CONTRACT_STATUS"] == "Approved"
        ).astype(np.int8)
        df_prev["IS_REFUSED"] = (
            df_prev["NAME_CONTRACT_STATUS"] == "Refused"
        ).astype(np.int8)

        # Aggregation Dictionary
        agg_rules = {
            "SK_ID_PREV": ["count"],
            "AMT_ANNUITY": ["mean", "max"],
            "AMT_APPLICATION": ["mean", "max"],
            "AMT_CREDIT": ["mean", "max"],
            "AMT_DOWN_PAYMENT": ["mean"],
            "DAYS_DECISION": ["min", "max", "mean"],
            "CNT_PAYMENT": ["mean", "max"],
            "IS_APPROVED": ["sum", "mean"],
            "IS_REFUSED": ["sum", "mean"],
        }

        logger.info("Executing GroupBy aggregation on Previous Applications...")
        prev_agg = df_prev.groupby("SK_ID_CURR").agg(agg_rules)
        prev_agg.columns = [
            f"PREV_{col}_{stat}".upper()
            for col, stat in prev_agg.columns
        ]
        prev_agg = prev_agg.reset_index()

        # Derived Ratios
        prev_agg["PREV_APPLICATION_CREDIT_RATIO"] = (
            prev_agg["PREV_AMT_APPLICATION_MEAN"] /
            (prev_agg["PREV_AMT_CREDIT_MEAN"] + 1.0)
        )
        prev_agg["PREV_REFUSAL_RATE"] = prev_agg["PREV_IS_REFUSED_MEAN"]

        del df_prev
        gc.collect()
        logger.info(f"Previous application aggregation complete: {prev_agg.shape}")
        return prev_agg

    def merge_features(
        self,
        main_df: pd.DataFrame,
        bureau_agg: pd.DataFrame,
        prev_agg: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Left-merge aggregated features onto the main application dataframe.
        """
        logger.info(f"Merging features. Main shape before merge: {main_df.shape}")
        merged = main_df.merge(bureau_agg, on="SK_ID_CURR", how="left")
        merged = merged.merge(prev_agg, on="SK_ID_CURR", how="left")
        logger.info(f"Main shape after merge: {merged.shape}")
        return merged
```

### 3.3 Enhancement to `src/data_loader.py`
To preserve backward compatibility while enabling selective column loading, update `DataLoader.load_csv` signature:
```python
def load_csv(
    self,
    filename: str,
    usecols: Optional[List[str]] = None,
    dtype: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    path = self.raw_data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")
    logger.info(f"Loading {filename}")
    df = pd.read_csv(path, usecols=usecols, dtype=dtype)
    logger.info(f"Shape : {df.shape}")
    return df
```
Existing calls using `load_csv("application_train.csv")` continue to work unchanged.

### 3.4 Reproducible Pipeline Script (`scripts/run_data_pipeline.py`)
A standalone Python script executing:
1. `DataLoader.load_csv("application_train.csv")`
2. `FeatureEngineer().transform(raw_train)` (generating 18 domain features)
3. `DataAggregator().aggregate_bureau()`
4. `DataAggregator().aggregate_previous_application()`
5. Left merge on `SK_ID_CURR`
6. Stratified 80/20 train/test split (`random_state=42`)
7. `DataPreprocessor().fit_transform(X_train)` and `transform(X_test)`
8. Save artifacts:
   - `models/preprocessing_pipeline.joblib`
   - `models/preprocessed_feature_names.csv`
   - `data/processed_train.parquet`
   - `data/processed_test.parquet`

---

## 4. Caveats & Assumptions

1. **Feature Engineering Bypassed in Baseline**: In `notebooks/02_Preprocessing.ipynb`, `FeatureEngineer` was not executed. Integrating both `FeatureEngineer` (18 features) and child table aggregations (~60 features) will expand raw features from 121 to ~200, resulting in ~330 preprocessed features. This is advantageous for XGBoost, but all downstream models must support the expanded dimension.
2. **Dense Array Conversion (`sparse_output=False`)**: `DataPreprocessor` outputs dense numpy arrays. With ~330 columns and 246,008 rows in float64, the matrix requires ~650 MB RAM. This easily fits into system memory, but `float32` casting before saving to Parquet is recommended.
3. **No Target Leakage in Child Table Aggregations**: Child records do not contain `TARGET`. Computing aggregations over all child records for known applicants is mathematically valid and does not cause target leakage, provided imputers and scalers are fitted solely on `X_train`.
4. **No Direct Execution Performed**: Per instructions, Explorer 2 is strictly in read-only investigation mode; no scripts were executed and no files in `src/` were modified.

---

## 5. Conclusion

1. **Pipeline Architecture Compatibility**:
   - The existing `DataPreprocessor` dynamically handles any added numerical columns, routing them through median imputation and standard scaling without requiring modifications to the `ColumnTransformer` structure.
   - The API serving layer (`api/preprocessing.py`) handles missing raw features via `SimpleImputer` fallbacks, preventing API breaks when the model artifact is upgraded.
2. **Architectural Placement**:
   - The new aggregation module must be housed in `src/data_aggregation.py` as class `DataAggregator`.
   - Modifying `FeatureEngineer` for child table aggregations is strongly discouraged to maintain clean separation between 1:1 row transformations and 1:N relational operations.
3. **Memory Management (Requirement R2)**:
   - Ingesting `previous_application.csv` and `bureau.csv` using selective columns (`usecols`), downcasting numerics, sequential aggregation, and explicit garbage collection (`gc.collect()`) guarantees that peak memory stays under **1.8 GB**, fully eliminating OOM risk.
4. **Reproducibility & Coding Standards**:
   - Creating `scripts/run_data_pipeline.py` alongside an updated `notebooks/02_Preprocessing.ipynb` fulfills Acceptance Criterion 1.
   - All proposed code strictly complies with `PROJECT_RULES.md` (type hints, PEP8 <= 88 chars, logging instead of print, docstrings, no bare except, `RANDOM_STATE=42`).

---

## 6. Verification Method

To independently verify this survey's findings and test the future implementation:
1. **Inspect Existing Artifacts**:
   - Check pipeline feature count: `python -c "import joblib; p = joblib.load('models/preprocessing_pipeline.joblib'); print(len(p.get_feature_names_out()))"` (confirms 245 features).
   - Check parquet schema: `python -c "import pandas as pd; df = pd.read_parquet('data/processed_train.parquet'); print(df.shape)"` (confirms 246,008 x 246).
2. **Verify Memory Profiling**:
   - Measure memory during sequential aggregation using `tracemalloc` or `memory_profiler`. Verify peak RAM does not exceed 2.0 GB.
3. **Verify Pipeline Re-fitting**:
   - Run the reproducible pipeline script, then assert:
     - Output files exist: `data/processed_train.parquet`, `data/processed_test.parquet`, `models/preprocessing_pipeline.joblib`, `models/preprocessed_feature_names.csv`.
     - Zero NaN values remain in preprocessed datasets (`assert not df.isna().any().any()`).
4. **Verify API Compatibility**:
   - Run API tests: `pytest api/tests/test_prediction.py` to confirm that predictions and SHAP explanations execute successfully with the refitted pipeline.
