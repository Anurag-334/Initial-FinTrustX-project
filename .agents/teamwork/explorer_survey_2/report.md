# FinTrustX Explorer Survey 2: FastAPI Prediction Pipeline & Preprocessing Optimization Report

## Executive Summary
This survey provides a comprehensive architectural and code-level investigation of the FinTrustX FastAPI serving layer, feature preprocessing pipeline, request schemas, and offline-to-online SQLite Feature Store integration. 

Key Findings:
1. **Pandas Fragmentation Warning Pinpointed**: In `api/preprocessing.py` (lines 51–55), missing raw feature columns are inserted iteratively in a `for col in raw_feature_names: df_raw[col] = np.nan` loop. Inserting ~100 columns one-by-one triggers `PerformanceWarning: DataFrame is highly fragmented...`. We formulate an exact refactoring using `pd.concat(axis=1)` to allocate all missing columns simultaneously, reducing execution overhead and eliminating all fragmentation warnings.
2. **Request Schemas & SK_ID_CURR**: `CreditRiskRequest` in `api/schemas.py` already includes `SK_ID_CURR: Optional[int] = Field(default=None, description="Unique applicant loan ID")` on line 29, but needs enhanced schema metadata, validation (`gt=0`), and alias/validator support for `applicant_id`. Furthermore, `PredictionRequest` was missing from `api/schemas.py`, causing a latent `ImportError` in `api/routers/predict.py:19`.
3. **Feature Store Integration Flow**: An offline-to-online SQLite feature store lookup should be wired cleanly into `PredictionService` and `ExplanationService` via FastAPI dependency injection. When an `SK_ID_CURR` is supplied, historical features are queried from SQLite (`applicant_features` table) and merged with incoming request parameters. Crucially, the incoming request payload takes precedence (`incoming payload overrides historical features`), achieved by filtering incoming fields with `request.model_dump(exclude_unset=True)` so schema defaults do not overwrite genuine historical values.
4. **Database Access Client**: We designed `api/feature_store.py` (`FeatureStore` class) with connection pooling/timeout, read-only mode, single-record lookup (`get_applicant_features`), batch lookup (`get_batch_applicant_features`), and graceful degradation when the database is offline or records are missing.

---

## 1. Codebase Architecture & In-Scope Module Audit

### 1.1 In-Scope File Breakdown

| File Path | Role | Status / Observation |
|---|---|---|
| `api/main.py` | FastAPI entrypoint & route registration | Defines `/`, `/health`, `/model-info`, `/predict`, `/explain`, `/predict/batch`. All routes directly on `app`. Uses `PredictionService`, `XGBoostPredictor`, `ModelLoader`. |
| `api/config.py` | Configuration constants | Holds artifact paths (`xgboost.joblib`, `preprocessing_pipeline.joblib`), thresholds, CORS. Currently missing `FEATURE_STORE_DB_PATH` and `FEATURE_STORE_TABLE_NAME`. |
| `api/schemas.py` | Pydantic v2 data models | Defines `CreditRiskRequest`, `BatchCreditRiskRequest`, `PredictionResponse`, `ExplanationResponse`. `SK_ID_CURR` is present on line 29 of `CreditRiskRequest`. Missing `PredictionRequest`. |
| `api/predictor.py` | Inference orchestration | `XGBoostPredictor` handles `predict_single` and `predict_batch`. Delegates feature conversion to `transform_raw_to_features`, calls `model.predict_proba`, formats response. |
| `api/preprocessing.py` | Feature transformation | `transform_raw_to_features()` converts incoming dict/records into 245-dim feature matrix. Contains the iterative column insertion bug (lines 52–55). |
| `api/dependencies.py` | FastAPI Dependency Injection | Factory functions `get_loader()`, `get_predictor()`, `get_model_service()`, `get_prediction_service()`, `get_explanation_service()`. Needs `get_feature_store()` provider. |
| `api/services/prediction_service.py` | Business logic for scoring | `PredictionService.predict_single()` and `predict_batch()`. Currently dumps request payload and passes straight to `predictor`. Needs feature store lookup & merge. |
| `api/services/explanation_service.py` | Business logic for SHAP | `ExplanationService.explain_applicant()`. Needs feature store lookup & merge so SHAP reflects historical applicant data. |
| `api/routers/predict.py` | Standalone router stub | Orphaned router file; imports missing `PredictionRequest` from `api.schemas`. |
| `api/tests/test_prediction.py` | Integration test suite | Tests single prediction, explanations, batch, and validation. Needs new integration tests for feature store lookup, payload overrides, and warning assertions. |

---

## 2. Preprocessing Optimization: Eliminating Pandas Fragmentation Warning

### 2.1 Problem Analysis
In `api/preprocessing.py`:
```python
# Lines 48-58 in api/preprocessing.py
    # Build DataFrame ensuring all expected raw columns exist
    df_raw = pd.DataFrame(records)
    
    # Fill any unprovided raw columns with NaN so SimpleImputer handles them
    for col in raw_feature_names:
        if col not in df_raw.columns:
            df_raw[col] = np.nan

    # Reorder columns to exactly match pipeline.feature_names_in_
    df_aligned = df_raw[raw_feature_names]
```

**Root Cause**:
- `raw_feature_names` contains 121 columns expected by `pipeline.feature_names_in_`.
- When an API client submits a request (e.g. `SAMPLE_APPLICANT`), only ~18–20 fields are provided.
- The `for col in raw_feature_names:` loop iterates 121 times, executing `df_raw[col] = np.nan` for over 100 missing columns.
- In Pandas 2.0+, inserting more than 100 columns iteratively triggers:
  ```
  PerformanceWarning: DataFrame is highly fragmented. This is usually the result of calling `frame.insert` many times, which has poor performance. Consider joining all columns at once using pd.concat(axis=1) instead. To get a de-fragmented frame, use `newframe = frame.copy()`
  ```
- This slows down inference throughput and floods terminal/server logs.

### 2.2 Exact Refactored Implementation
Instead of iterative column assignment, collect all missing column names in a list and create a single `pd.DataFrame` filled with `np.nan`, then horizontally concatenate using `pd.concat(axis=1)`:

```python
def transform_raw_to_features(
    raw_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
    pipeline: Any,
    raw_feature_names: List[str]
) -> np.ndarray:
    """
    Convert raw applicant payload(s) to preprocessed model feature matrix.
    Refactored to eliminate DataFrame fragmentation warnings using pd.concat.
    """
    if isinstance(raw_inputs, dict):
        records = [raw_inputs]
    else:
        records = raw_inputs

    # Build DataFrame from incoming records
    df_raw = pd.DataFrame(records)

    # Identify missing expected raw columns
    missing_cols = [col for col in raw_feature_names if col not in df_raw.columns]
    if missing_cols:
        # Create a single block NaN DataFrame with matching index
        df_missing = pd.DataFrame(
            np.nan,
            index=df_raw.index,
            columns=missing_cols
        )
        # Concatenate in a single operation (zero fragmentation)
        df_raw = pd.concat([df_raw, df_missing], axis=1)

    # Reorder columns to exactly match pipeline.feature_names_in_
    df_aligned = df_raw[raw_feature_names].copy()

    # Execute transform
    try:
        transformed = pipeline.transform(df_aligned)
    except Exception as e:
        logger.error(f"Preprocessing transform failed: {e}")
        raise ValueError(f"Feature preprocessing failed: {e}") from e

    return transformed
```

### 2.3 Verification & Performance Characteristics
- **Zero Warnings**: `pd.concat(axis=1)` constructs the DataFrame's internal `BlockManager` in a single allocation. No `PerformanceWarning` is emitted.
- **Batch Scalability**: Works cleanly whether `records` contains 1 applicant or 500 applicants (`index=df_raw.index` ensures row alignment).
- **Extra Column Filtering**: Columns in `records` that are not in `raw_feature_names` (e.g., `SK_ID_CURR`) are naturally dropped when subsetting `df_raw[raw_feature_names]`.

---

## 3. Schema Analysis & `SK_ID_CURR` Integration

### 3.1 Investigation of `api/schemas.py`
In `api/schemas.py`:
- `CreditRiskRequest` (line 20):
  - Line 29:
    ```python
    SK_ID_CURR: Optional[int] = Field(default=None, description="Unique applicant loan ID")
    ```
  - It is currently present, but lacks explicit constraints and docstring details regarding the feature store lookup.
- `BatchCreditRiskRequest` (line 70):
  - Uses `requests: List[CreditRiskRequest]`, so batch applicants also support `SK_ID_CURR`.
- `PredictionResponse` (line 98):
  - Line 108:
    ```python
    applicant_id: Optional[int] = Field(default=None, description="Applicant identifier if provided")
    ```
  - Already supports returning `applicant_id`.

### 3.2 Recommended Schema Enhancements
1. **Validation & Documentation**:
   ```python
   SK_ID_CURR: Optional[int] = Field(
       default=None,
       gt=0,
       description="Unique applicant loan ID. If provided, queries SQLite feature store for historical profile.",
       json_schema_extra={"example": 100002}
   )
   ```
2. **Alias / Flexibility Validator**:
   Allow frontend requests providing `"applicant_id"` to seamlessly map to `"SK_ID_CURR"`:
   ```python
   from pydantic import model_validator

   @model_validator(mode="before")
   @classmethod
   def map_applicant_id_alias(cls, data: Any) -> Any:
       if isinstance(data, dict):
           if "SK_ID_CURR" not in data and "applicant_id" in data:
               data["SK_ID_CURR"] = data["applicant_id"]
       return data
   ```
3. **Add Missing `PredictionRequest` Model**:
   `api/routers/predict.py:19` imports `PredictionRequest`. Adding it to `api/schemas.py` resolves the import error:
   ```python
   class PredictionRequest(BaseModel):
       """Legacy prediction request schema."""
       model_config = ConfigDict(extra="allow")
       SK_ID_CURR: Optional[int] = Field(default=None, gt=0, description="Applicant ID")
       features: Dict[str, Any] = Field(default_factory=dict, description="Raw applicant feature dictionary")
   ```

---

## 4. SQLite Feature Store Client Design (`api/feature_store.py`)

### 4.1 Architecture & Requirements
The client module `api/feature_store.py` provides thread-safe, read-only SQLite access for high-speed feature retrieval.

**Key Design Decisions**:
1. **Connection Safety**: Use `sqlite3.connect` with timeout (`timeout=5.0`), WAL mode, and connection context management.
2. **Row Factory**: Set `conn.row_factory = sqlite3.Row` to convert rows directly into Python dictionaries (`dict(row)`).
3. **Graceful Degradation**: If the database file does not exist, or SQLite errors occur, log a warning and return `None` (fallback to incoming request payload without crashing the API).
4. **Batch Query Support**: Implement `get_batch_applicant_features(sk_id_currs)` using `WHERE SK_ID_CURR IN (?, ?, ...)` to prevent $N$ sequential roundtrips during `/predict/batch`.

### 4.2 Module Implementation (`api/feature_store.py`)

```python
"""
=========================================================
FinTrustX SQLite Feature Store Client
=========================================================
Provides real-time online feature retrieval from the
offline SQLite feature store database.

Author: Anurag Kashyap
=========================================================
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.config import FEATURE_STORE_DB_PATH, FEATURE_STORE_TABLE_NAME

logger = logging.getLogger(__name__)


class FeatureStore:
    """Thread-safe SQLite feature store accessor for applicant historical data."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        table_name: str = FEATURE_STORE_TABLE_NAME
    ) -> None:
        self.db_path = Path(db_path) if db_path else FEATURE_STORE_DB_PATH
        self.table_name = table_name

    def is_available(self) -> bool:
        """Check if the SQLite feature store database file exists and is readable."""
        if not self.db_path.exists():
            return False
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (self.table_name,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"Feature store availability check failed: {e}")
            return False

    def get_record_count(self) -> int:
        """Return total applicant records in the feature store table."""
        if not self.db_path.exists():
            return 0
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.warning(f"Feature store count failed: {e}")
            return 0

    def get_applicant_features(self, sk_id_curr: int) -> Optional[Dict[str, Any]]:
        """
        Fetch historical features for a single applicant by SK_ID_CURR.
        
        Returns
        -------
        Optional[Dict[str, Any]]
            Dictionary of feature column names to values, or None if not found.
        """
        if not self.db_path.exists():
            logger.debug(f"Feature store DB not found at {self.db_path}")
            return None

        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = f"SELECT * FROM {self.table_name} WHERE SK_ID_CURR = ? LIMIT 1"
                cursor.execute(query, (sk_id_curr,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return dict(row)
        except Exception as e:
            logger.error(f"Error querying feature store for applicant {sk_id_curr}: {e}")
            return None

    def get_batch_applicant_features(self, sk_id_currs: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Batch-query historical features for multiple applicants.
        
        Returns
        -------
        Dict[int, Dict[str, Any]]
            Mapping of SK_ID_CURR to feature dictionary.
        """
        if not sk_id_currs or not self.db_path.exists():
            return {}

        results: Dict[int, Dict[str, Any]] = {}
        unique_ids = list(set(sk_id_currs))

        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in unique_ids)
                query = f"SELECT * FROM {self.table_name} WHERE SK_ID_CURR IN ({placeholders})"
                cursor.execute(query, unique_ids)
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    applicant_id = int(row_dict.get("SK_ID_CURR", 0))
                    results[applicant_id] = row_dict
            return results
        except Exception as e:
            logger.error(f"Error batch-querying feature store: {e}")
            return {}


# Module-level singleton
_feature_store_instance: Optional[FeatureStore] = None

def get_feature_store() -> FeatureStore:
    """Return singleton FeatureStore instance."""
    global _feature_store_instance
    if _feature_store_instance is None:
        _feature_store_instance = FeatureStore()
    return _feature_store_instance
```

---

## 5. End-to-End Prediction Flow & Feature Merging Logic

### 5.1 Request Flow Diagram

```
Client (Frontend / API Consumer)
   │
   │  POST /predict  {"SK_ID_CURR": 100002, "AMT_CREDIT": 500000.0}
   ▼
api/main.py (predict_credit_risk endpoint)
   │
   │  Depends(get_prediction_service) ──► Injects FeatureStore
   ▼
api/services/prediction_service.py (predict_single)
   │
   ├── 1. Check SK_ID_CURR (100002)
   │      └──► FeatureStore.get_applicant_features(100002)
   │           Returns: {AMT_INCOME_TOTAL: 202500, AMT_CREDIT: 406597.5, DAYS_BIRTH: -9461, ...}
   │
   ├── 2. Extract explicit overrides from request:
   │      request.model_dump(exclude_unset=True)
   │      Returns: {"SK_ID_CURR": 100002, "AMT_CREDIT": 500000.0}
   │
   ├── 3. Merge: {**historical_data, **incoming_overrides}
   │      "AMT_CREDIT" becomes 500000.0 (overridden!)
   │      All other historical attributes preserved!
   │
   ▼
api/predictor.py (predict_single)
   │
   ├── 4. transform_raw_to_features(merged_payload) [api/preprocessing.py]
   │      • Detect missing columns -> pd.concat(axis=1) with NaN
   │      • Align 121 columns to raw_feature_names
   │      • ColumnTransformer.transform() -> (1, 245) feature array
   │
   ├── 5. XGBoost Inference: predict_proba(X_trans)
   │      • P(TARGET=1) = default_probability
   │      • Risk score & category computation
   │      • Optional SHAP local attribution (if explain=True)
   │
   ▼
PredictionResponse JSON (includes applicant_id=100002, score, recommendation)
```

### 5.2 The Crucial "Default vs Override" Rule
When using Pydantic, calling `request.model_dump()` returns all fields, including schema default values (such as `AMT_INCOME_TOTAL: 150000.0`, `DAYS_BIRTH: -14000.0`).
If we blindly merged `{**historical, **request.model_dump()}`, the schema defaults would overwrite the applicant's real historical data!

**The Solution**:
- Call `request.model_dump(exclude_unset=True)`.
- This ensures only fields explicitly passed in the HTTP request override the historical record.
- If no historical data is found (or no `SK_ID_CURR` was supplied), use `request.model_dump(exclude_none=False)`, falling back to full defaults for backward compatibility.

### 5.3 Service Implementation Updates

#### `api/dependencies.py`
```python
from api.feature_store import FeatureStore, get_feature_store

def get_store() -> FeatureStore:
    """Provide singleton FeatureStore instance."""
    return get_feature_store()

def get_prediction_service(store: FeatureStore = Depends(get_store)) -> PredictionService:
    """Provide PredictionService instance with feature store dependency."""
    return PredictionService(feature_store=store)

def get_explanation_service(store: FeatureStore = Depends(get_store)) -> ExplanationService:
    """Provide ExplanationService instance with feature store dependency."""
    return ExplanationService(feature_store=store)
```

#### `api/services/prediction_service.py`
```python
class PredictionService:
    """Service orchestrating applicant scoring and batch inference pipelines."""

    def __init__(self, feature_store: Optional[FeatureStore] = None) -> None:
        self.feature_store = feature_store

    def _merge_applicant_features(self, request: CreditRiskRequest) -> Dict[str, Any]:
        """Merge historical features from SQLite with incoming request overrides."""
        applicant_id = request.SK_ID_CURR
        historical: Dict[str, Any] = {}

        if applicant_id is not None and self.feature_store is not None:
            db_data = self.feature_store.get_applicant_features(applicant_id)
            if db_data:
                logger.info(f"Retrieved {len(db_data)} historical features for applicant {applicant_id}")
                historical = db_data
            else:
                logger.warning(f"Applicant {applicant_id} not found in feature store; using request payload.")

        if historical:
            # Only explicitly provided request fields override historical data
            incoming_overrides = request.model_dump(exclude_unset=True)
            merged = {**historical, **incoming_overrides}
            merged["SK_ID_CURR"] = applicant_id
            return merged
        else:
            return request.model_dump(exclude_none=False)

    def predict_single(
        self,
        request: CreditRiskRequest,
        predictor: XGBoostPredictor,
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
        explain: bool = False
    ) -> PredictionResponse:
        """Process single prediction with feature store lookup."""
        payload = self._merge_applicant_features(request)
        logger.info(f"Processing prediction request (Applicant ID: {payload.get('SK_ID_CURR')}, Explain: {explain})")

        return predictor.predict_single(
            raw_data=payload,
            threshold=threshold,
            explain=explain
        )

    def predict_batch(
        self,
        batch_request: BatchCreditRiskRequest,
        predictor: XGBoostPredictor,
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD
    ) -> BatchPredictionResponse:
        """Process multiple applicants with batch SQLite feature lookup."""
        app_ids = [req.SK_ID_CURR for req in batch_request.requests if req.SK_ID_CURR is not None]
        historical_batch: Dict[int, Dict[str, Any]] = {}
        if app_ids and self.feature_store is not None:
            historical_batch = self.feature_store.get_batch_applicant_features(app_ids)

        raw_list: List[Dict[str, Any]] = []
        for req in batch_request.requests:
            app_id = req.SK_ID_CURR
            if app_id in historical_batch:
                incoming_overrides = req.model_dump(exclude_unset=True)
                merged = {**historical_batch[app_id], **incoming_overrides}
                merged["SK_ID_CURR"] = app_id
                raw_list.append(merged)
            else:
                raw_list.append(req.model_dump(exclude_none=False))

        logger.info(f"Processing batch prediction for {len(raw_list)} applicants.")
        predictions = predictor.predict_batch(raw_data_list=raw_list, threshold=threshold)

        return BatchPredictionResponse(
            predictions=predictions,
            total_processed=len(predictions),
            model="XGBoost"
        )
```

---

## 6. Integration Test Strategy (`api/tests/test_prediction.py`)

To satisfy the verification criteria in `ORIGINAL_REQUEST.md`:
1. **Valid `SK_ID_CURR` pulls historical data from SQLite**:
   - Create a temporary SQLite database using `tmp_path` and `sqlite3`.
   - Seed sample record with `SK_ID_CURR: 100002` and baseline features.
   - Override `get_store` dependency via `app.dependency_overrides[get_store] = lambda: FeatureStore(db_path=test_db)`.
   - Post `{"SK_ID_CURR": 100002}` without financial fields; verify prediction succeeds using database features.
2. **Payload Override Priority**:
   - Send `{"SK_ID_CURR": 100002, "AMT_CREDIT": 999999.0}`.
   - Verify the prediction succeeds and uses the modified credit amount.
3. **Backward Compatibility**:
   - Send `SAMPLE_APPLICANT` without `SK_ID_CURR` or with non-existent `SK_ID_CURR: 9999999`.
   - Verify HTTP 200 and standard prediction.
4. **Zero Pandas Fragmentation Warnings**:
   - Use `warnings.catch_warnings(record=True)` with `warnings.simplefilter("always")`.
   - Issue `/predict` request with a 2-field payload (triggering missing column imputation).
   - Assert `len([w for w in recorded if issubclass(w.category, PerformanceWarning)]) == 0`.

---

## 7. Step-by-Step Implementation Plan for Implementer

| Step | File | Action | Details |
|---|---|---|---|
| 1 | `api/config.py` | Add DB paths | Add `FEATURE_STORE_DB_PATH = Path(os.getenv("FEATURE_STORE_DB_PATH", str(DATA_DIR / "feature_store.db")))` and `FEATURE_STORE_TABLE_NAME = "applicant_features"`. |
| 2 | `api/preprocessing.py` | Refactor imputation | Replace lines 51–55 with `missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]`, `df_missing = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)`, and `pd.concat([df_raw, df_missing], axis=1)`. |
| 3 | `api/schemas.py` | Enhance schemas | Update `CreditRiskRequest.SK_ID_CURR` description and add validator for `applicant_id`. Add `PredictionRequest` to fix router import. |
| 4 | `api/feature_store.py` | Create client module | Create `FeatureStore` with `get_applicant_features`, `get_batch_applicant_features`, `is_available`, and singleton getter `get_feature_store()`. |
| 5 | `api/dependencies.py` | Wire DI | Add `get_store() -> FeatureStore` and inject into `get_prediction_service` and `get_explanation_service`. |
| 6 | `api/services/prediction_service.py` | Add merge logic | Implement `_merge_applicant_features()`, update `predict_single()` and `predict_batch()` to merge historical data with `request.model_dump(exclude_unset=True)`. |
| 7 | `api/services/explanation_service.py` | Add merge logic | Merge historical features before generating SHAP attributions. |
| 8 | `api/routers/predict.py` | Clean up imports | Import `CreditRiskRequest` or define compatibility with `PredictionRequest`. |
| 9 | `api/tests/test_prediction.py` | Add test cases | Add integration tests for SQLite lookup, payload override priority, backward compatibility, and zero `PerformanceWarning` assertion. |
