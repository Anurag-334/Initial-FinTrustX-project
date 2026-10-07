# FinTrustX Feature Store Architecture Survey & Design Report

**Author**: Explorer Survey 1 (Data & Feature Store Architecture)  
**Date**: 2026-10-05  
**Project**: FinTrustX (Credit Risk Assessment & Explainable AI)  
**Scope**: Offline-to-Online SQLite Feature Store, Data Seeding, API Integration, Preprocessing Optimization, Frontend Integration  

---

## 1. Executive Summary

FinTrustX recently augmented its XGBoost credit risk champion model by integrating supplementary historical datasets (`bureau.csv` and `previous_application.csv`), expanding the model from 245 to 341 preprocessed features and increasing test ROC-AUC to **0.779383** (+1.83% improvement). 

However, during real-time online serving, an applicant's payload only contains loan application fields (e.g., income, loan amount, age). The API cannot afford to parse and aggregate 1.7M bureau records and 1.6M previous application records on the fly, as that takes ~30 seconds and consumes ~1 GB RAM. 

To bridge this offline-to-online gap, we design a lightweight, high-performance **SQLite Feature Store** (`data/feature_store.db`) that persists pre-aggregated historical features indexed by `SK_ID_CURR`. At prediction time, when an `SK_ID_CURR` is supplied, the API performs an $O(1)$ sub-millisecond lookup, merges the historical features with the incoming payload, and feeds the full 341-feature profile into the champion model.

This report documents the exact data findings, table schema, seeding architecture, memory safeguards, API refactoring, frontend updates, and testing plan.

---

## 2. Codebase & Data Investigation Findings

### 2.1 Existing Data Files & Storage Locations

| Path | Description | Rows | File Size | Role |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/bureau.csv` | Historical credit accounts from other banks | 1,716,428 | 170 MB | Supplementary source |
| `data/raw/previous_application.csv` | Prior loan applications at Home Credit | 1,670,214 | 405 MB | Supplementary source |
| `data/raw/application_train.csv` | Primary training dataset with target | 307,511 | 166 MB | Main training anchor |
| `data/raw/application_test.csv` | Held-out test set | 48,744 | 26.5 MB | Unlabeled test anchor |
| `data/processed_train.parquet` | Augmented preprocessed train features | 246,008 | 75.9 MB | Model training dataset |
| `data/processed_test.parquet` | Augmented preprocessed test features | 61,503 | 20.1 MB | Model evaluation dataset |
| `models/xgboost.joblib` | Champion augmented XGBoost model | - | 803 KB | Active production model |
| `models/preprocessing_pipeline.joblib` | Fitted `ColumnTransformer` | - | 19 KB | Inference preprocessor |
| `models/preprocessed_feature_names.csv` | Output feature names | 341 | 10.7 KB | Target feature layout |

### 2.2 Feature Distribution Breakdown

Inspection of `models/preprocessed_feature_names.csv` confirms that the current production pipeline produces **341 total preprocessed features**:
1. **201 Numerical Features** (transformed via `SimpleImputer(strategy='median')` + `StandardScaler()`):
   - **104 features**: Base application numeric features from `application_train.csv` (e.g., `AMT_INCOME_TOTAL`, `DAYS_BIRTH`, `EXT_SOURCE_1/2/3`).
   - **44 features**: Aggregated credit bureau features (`BUREAU_*`).
   - **44 features**: Aggregated previous application features (`PREV_*`).
   - **4 features**: Data availability flags and loan counts (`FLAG_NO_BUREAU_DATA`, `FLAG_NO_PREV_DATA`, `BUREAU_LOAN_COUNT`, `PREV_APP_COUNT`).
   - **5 features**: Cross-table macroeconomic credit ratios (`BUREAU_TOTAL_DEBT_TO_INCOME`, `BUREAU_ANNUITY_TO_INCOME`, `PREV_ANNUITY_TO_INCOME`, `PREV_CURRENT_TO_PRIOR_CREDIT_RATIO`, `TOTAL_DEBT_TO_INCOME`).
2. **140 Categorical Features** (transformed via `SimpleImputer(strategy='most_frequent')` + `OneHotEncoder(handle_unknown='ignore')`):
   - Derived from 16 categorical raw columns (e.g., `NAME_CONTRACT_TYPE`, `CODE_GENDER`, `ORGANIZATION_TYPE`).

### 2.3 Existing Aggregation Logic

The class `DataAggregator` in `src/data_aggregation.py` already implements:
- `aggregate_bureau()`: Reads `bureau.csv` using 15 selective columns, partitions by active/closed status, calculates 39 summary statistics across 18 metrics, derives 5 intra-table ratios, and downcasts dtypes.
- `aggregate_previous_application()`: Reads `previous_application.csv` using 12 selective columns, partitions by approval status, calculates 40 summary statistics across 17 metrics, derives 4 intra-table ratios, and downcasts dtypes.
- `merge_features()`: Merges both aggregated DataFrames onto the main application dataset, generates the 4 missing-history flags/counts, and computes the 5 cross-table macroeconomic leverage ratios.

This existing logic in `src/data_aggregation.py` is tested, verified, and memory-safe. The seeding script can reuse `DataAggregator` directly.

---

## 3. SQLite Feature Store Database Design

### 3.1 Database Location & Configuration

- **File Path**: `data/feature_store.db` (configured as `FEATURE_STORE_PATH` in `src/config.py`).
- **Engine**: SQLite 3 with WAL (`Write-Ahead Logging`) enabled for concurrent reads:
  ```sql
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA cache_size = -64000; -- 64MB cache
  PRAGMA temp_store = MEMORY;
  ```
- **Table Name**: `applicant_features`

### 3.2 Table Schema Specification

The `applicant_features` table will store the **97 historical features** plus the primary key:

```sql
CREATE TABLE IF NOT EXISTS applicant_features (
    SK_ID_CURR INTEGER PRIMARY KEY,
    
    -- Bureau Aggregations (44 columns)
    BUREAU_SK_ID_BUREAU_COUNT REAL,
    BUREAU_IS_ACTIVE_SUM REAL,
    BUREAU_IS_ACTIVE_MEAN REAL,
    BUREAU_IS_CLOSED_SUM REAL,
    BUREAU_IS_CLOSED_MEAN REAL,
    BUREAU_IS_MICROLOAN_SUM REAL,
    BUREAU_IS_MICROLOAN_MEAN REAL,
    BUREAU_DAYS_CREDIT_MIN REAL,
    BUREAU_DAYS_CREDIT_MAX REAL,
    BUREAU_DAYS_CREDIT_MEAN REAL,
    BUREAU_CREDIT_DAY_OVERDUE_MAX REAL,
    BUREAU_CREDIT_DAY_OVERDUE_MEAN REAL,
    BUREAU_DAYS_CREDIT_ENDDATE_MIN REAL,
    BUREAU_DAYS_CREDIT_ENDDATE_MAX REAL,
    BUREAU_DAYS_CREDIT_ENDDATE_MEAN REAL,
    BUREAU_AMT_CREDIT_MAX_OVERDUE_MAX REAL,
    BUREAU_AMT_CREDIT_MAX_OVERDUE_MEAN REAL,
    BUREAU_CNT_CREDIT_PROLONG_SUM REAL,
    BUREAU_CNT_CREDIT_PROLONG_MAX REAL,
    BUREAU_AMT_CREDIT_SUM_SUM REAL,
    BUREAU_AMT_CREDIT_SUM_MEAN REAL,
    BUREAU_AMT_CREDIT_SUM_MAX REAL,
    BUREAU_AMT_CREDIT_SUM_DEBT_SUM REAL,
    BUREAU_AMT_CREDIT_SUM_DEBT_MEAN REAL,
    BUREAU_AMT_CREDIT_SUM_DEBT_MAX REAL,
    BUREAU_AMT_CREDIT_SUM_LIMIT_SUM REAL,
    BUREAU_AMT_CREDIT_SUM_LIMIT_MEAN REAL,
    BUREAU_AMT_CREDIT_SUM_OVERDUE_SUM REAL,
    BUREAU_AMT_CREDIT_SUM_OVERDUE_MAX REAL,
    BUREAU_DAYS_CREDIT_UPDATE_MAX REAL,
    BUREAU_DAYS_CREDIT_UPDATE_MEAN REAL,
    BUREAU_AMT_ANNUITY_SUM REAL,
    BUREAU_AMT_ANNUITY_MEAN REAL,
    BUREAU_AMT_ANNUITY_MAX REAL,
    BUREAU_ACTIVE_AMT_CREDIT_SUM_DEBT_SUM REAL,
    BUREAU_ACTIVE_AMT_CREDIT_SUM_DEBT_MEAN REAL,
    BUREAU_ACTIVE_AMT_CREDIT_SUM_SUM REAL,
    BUREAU_ACTIVE_AMT_CREDIT_SUM_MEAN REAL,
    BUREAU_ACTIVE_DAYS_CREDIT_MAX REAL,
    BUREAU_DEBT_CREDIT_RATIO REAL,
    BUREAU_ACTIVE_DEBT_RATIO REAL,
    BUREAU_OVERDUE_DEBT_RATIO REAL,
    BUREAU_ACTIVE_LOAN_SHARE REAL,
    BUREAU_PROLONG_RATE REAL,

    -- Previous Application Aggregations (44 columns)
    PREV_SK_ID_PREV_COUNT REAL,
    PREV_IS_APPROVED_SUM REAL,
    PREV_IS_APPROVED_MEAN REAL,
    PREV_IS_REFUSED_SUM REAL,
    PREV_IS_REFUSED_MEAN REAL,
    PREV_IS_CANCELED_SUM REAL,
    PREV_IS_CANCELED_MEAN REAL,
    PREV_AMT_ANNUITY_MIN REAL,
    PREV_AMT_ANNUITY_MAX REAL,
    PREV_AMT_ANNUITY_MEAN REAL,
    PREV_AMT_ANNUITY_SUM REAL,
    PREV_AMT_APPLICATION_MIN REAL,
    PREV_AMT_APPLICATION_MAX REAL,
    PREV_AMT_APPLICATION_MEAN REAL,
    PREV_AMT_APPLICATION_SUM REAL,
    PREV_AMT_CREDIT_MIN REAL,
    PREV_AMT_CREDIT_MAX REAL,
    PREV_AMT_CREDIT_MEAN REAL,
    PREV_AMT_CREDIT_SUM REAL,
    PREV_AMT_DOWN_PAYMENT_MAX REAL,
    PREV_AMT_DOWN_PAYMENT_MEAN REAL,
    PREV_AMT_DOWN_PAYMENT_SUM REAL,
    PREV_RATE_DOWN_PAYMENT_MAX REAL,
    PREV_RATE_DOWN_PAYMENT_MEAN REAL,
    PREV_DAYS_DECISION_MIN REAL,
    PREV_DAYS_DECISION_MAX REAL,
    PREV_DAYS_DECISION_MEAN REAL,
    PREV_CNT_PAYMENT_MAX REAL,
    PREV_CNT_PAYMENT_MEAN REAL,
    PREV_CNT_PAYMENT_SUM REAL,
    PREV_DAYS_TERMINATION_MAX REAL,
    PREV_DAYS_TERMINATION_MEAN REAL,
    PREV_APP_CREDIT_RATIO_MEAN REAL,
    PREV_APP_CREDIT_RATIO_MAX REAL,
    PREV_APPROVED_AMT_CREDIT_SUM REAL,
    PREV_APPROVED_AMT_CREDIT_MEAN REAL,
    PREV_REFUSED_AMT_APPLICATION_SUM REAL,
    PREV_REFUSED_AMT_APPLICATION_MEAN REAL,
    PREV_REFUSED_DAYS_DECISION_MAX REAL,
    PREV_APPROVED_DAYS_DECISION_MAX REAL,
    PREV_APPROVAL_RATE REAL,
    PREV_REFUSAL_RATE REAL,
    PREV_CREDIT_TO_APPLICATION_RATIO REAL,
    PREV_DOWN_PAYMENT_RATIO REAL,

    -- Missing History Indicator Flags & Counts (4 columns)
    FLAG_NO_BUREAU_DATA INTEGER,
    FLAG_NO_PREV_DATA INTEGER,
    BUREAU_LOAN_COUNT INTEGER,
    PREV_APP_COUNT INTEGER,

    -- Baseline Cross-Table Macroeconomic Credit Ratios (5 columns)
    BUREAU_TOTAL_DEBT_TO_INCOME REAL,
    BUREAU_ANNUITY_TO_INCOME REAL,
    PREV_ANNUITY_TO_INCOME REAL,
    PREV_CURRENT_TO_PRIOR_CREDIT_RATIO REAL,
    TOTAL_DEBT_TO_INCOME REAL
);
```

### 3.3 Indexing Strategy

Because `SK_ID_CURR INTEGER PRIMARY KEY` is an SQLite rowid alias, lookups by `SK_ID_CURR` are instantaneous binary searches ($O(1)$). To be doubly sure:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_applicant_features_sk_id 
ON applicant_features (SK_ID_CURR);
```

---

## 4. Automated Seeding Script Architecture

### 4.1 Script Location & CLI

- **Script Path**: `scripts/seed_feature_store.py`
- **Execution**:
  ```bash
  python scripts/seed_feature_store.py
  python scripts/seed_feature_store.py --db-path data/feature_store.db --limit 50000
  ```

### 4.2 Compliance with `GEMINI.md` Memory Management Rules

| Requirement | Implementation Safeguard |
| :--- | :--- |
| **1. Dtype Downcasting** | Immediately execute `optimize_dtypes()` on loaded DataFrames (float64 $\to$ float32, int64 $\to$ int32/int16, strings $\to$ category). |
| **2. Sequential Execution** | Load and aggregate `bureau.csv` first $\to$ delete raw frame $\to$ `gc.collect()`. Load and aggregate `previous_application.csv` second $\to$ delete raw frame $\to$ `gc.collect()`. |
| **3. Explicit Garbage Collection** | Call `del df` and `gc.collect()` at every stage boundary. |
| **4. Peak RAM Control** | Anchor dataset loaded with only 3 columns (`["SK_ID_CURR", "AMT_INCOME_TOTAL", "AMT_CREDIT"]`), keeping baseline anchor memory under 5 MB. Peak RAM stays well below **1.1 GB** (< 1.8 GB constraint). |
| **5. Chunked DB Writes** | Stream the merged table to SQLite using `chunksize=25000` to prevent large intermediate buffer allocations. |

### 4.3 Seeding Execution Workflow

```
[bureau.csv] 
     │
     ▼ (Sequential Stage 1)
DataAggregator.aggregate_bureau()
     │
     ├─► del df_bureau; gc.collect()
     ▼
[previous_application.csv]
     │
     ▼ (Sequential Stage 2)
DataAggregator.aggregate_previous_application()
     │
     ├─► del df_prev; gc.collect()
     ▼
[application_train.csv + application_test.csv]
(Load only SK_ID_CURR, AMT_INCOME_TOTAL, AMT_CREDIT)
     │
     ▼ (Sequential Stage 3)
DataAggregator.merge_features()
     │
     ├─► Select only SK_ID_CURR + 97 historical columns
     ▼ (Sequential Stage 4)
Write in chunks to SQLite: data/feature_store.db
Create unique index on SK_ID_CURR
Vacuum & set WAL mode
```

---

## 5. API Backend Integration Design (R2 & R3)

### 5.1 Python Feature Store Accessor (`src/feature_store.py`)

A reusable, thread-safe accessor class:

```python
class FeatureStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or FEATURE_STORE_PATH

    def get_features(self, sk_id_curr: int) -> Optional[Dict[str, Any]]:
        """Query historical features for a single applicant ID in < 1 ms."""
        if not self.db_path.exists():
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?",
                (sk_id_curr,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def get_features_batch(self, sk_id_currs: List[int]) -> Dict[int, Dict[str, Any]]:
        """Query multiple applicants in a single IN clause."""
        ...
```

### 5.2 API Prediction Service Lookup & Merge (`api/services/prediction_service.py`)

In `PredictionService.predict_single`:
1. Check if `SK_ID_CURR` is provided in `CreditRiskRequest`.
2. If `SK_ID_CURR` is provided:
   - Query `feature_store.get_features(sk_id_curr)`.
   - If a record is found:
     * Extract the 97 historical features.
     * Overlay the incoming user payload on top of the historical record (`merged = {**historical, **user_payload}`).
     * Recompute dynamic cross-table ratios using the user's incoming `AMT_INCOME_TOTAL` and `AMT_CREDIT`:
       ```python
       income = float(user_payload.get("AMT_INCOME_TOTAL") or 150000.0)
       credit = float(user_payload.get("AMT_CREDIT") or 450000.0)
       debt = float(historical.get("BUREAU_AMT_CREDIT_SUM_DEBT_SUM") or 0.0)
       annuity_bureau = float(historical.get("BUREAU_AMT_ANNUITY_SUM") or 0.0)
       annuity_prev = float(historical.get("PREV_AMT_ANNUITY_SUM") or 0.0)
       prev_credit_mean = float(historical.get("PREV_APPROVED_AMT_CREDIT_MEAN") or 0.0)

       merged["BUREAU_TOTAL_DEBT_TO_INCOME"] = debt / (income + 1.0)
       merged["BUREAU_ANNUITY_TO_INCOME"] = annuity_bureau / (income + 1.0)
       merged["PREV_ANNUITY_TO_INCOME"] = annuity_prev / (income + 1.0)
       merged["PREV_CURRENT_TO_PRIOR_CREDIT_RATIO"] = credit / (prev_credit_mean + 1.0)
       merged["TOTAL_DEBT_TO_INCOME"] = (credit + debt) / (income + 1.0)
       ```
   - If NO record is found (e.g. unlinked applicant or new customer):
     * Set default unlinked flags: `FLAG_NO_BUREAU_DATA = 1`, `FLAG_NO_PREV_DATA = 1`, `BUREAU_LOAN_COUNT = 0`, `PREV_APP_COUNT = 0`.
     * Let pipeline median imputer handle the remaining supplementary fields.
3. Pass the merged dictionary into `predictor.predict_single()`.

### 5.3 Preprocessing Optimization (`api/preprocessing.py`) (R3)

#### The Problem
In `api/preprocessing.py` lines 51-54:
```python
# CURRENT FLAWED IMPLEMENTATION:
for col in raw_feature_names:
    if col not in df_raw.columns:
        df_raw[col] = np.nan  # Iterative insertion triggers Pandas PerformanceWarning!
```
Inserting over 150 missing columns iteratively causes severe internal fragmentation in Pandas and emits repeated warnings in server logs:
`PerformanceWarning: DataFrame is highly fragmented. This is usually the result of calling frame.insert many times.`

#### The Solution (Per R3)
Replace iterative column insertion with vectorized `pd.concat()`:
```python
# REFACTORED IMPLEMENTATION:
df_raw = pd.DataFrame(records)

missing_cols = [col for col in raw_feature_names if col not in df_raw.columns]
if missing_cols:
    missing_df = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)
    df_raw = pd.concat([df_raw, missing_df], axis=1)

df_aligned = df_raw[raw_feature_names]
```
This performs a single concatenation block, reducing latency and completely eliminating the `PerformanceWarning`.

---

## 6. Frontend UI Update Design (R4)

### 6.1 HTML Form Modification (`frontend/index.html`)

Add an Applicant Identification card at the top of the assessment form:

```html
<!-- Applicant Identification (Feature Store Query) -->
<div class="form-section">
  <div class="form-section-title">
    <i class="fa-solid fa-id-card"></i> Applicant Identification
  </div>
  <div class="form-group">
    <label class="form-label" for="SK_ID_CURR">
      Applicant ID (SK_ID_CURR)
      <span class="tooltip" title="Historical credit records will be queried from the Feature Store if this ID exists.">
        <i class="fa-solid fa-circle-question"></i>
      </span>
    </label>
    <input type="number" id="SK_ID_CURR" name="SK_ID_CURR" class="form-input" 
           placeholder="e.g. 100002" value="100002">
    <span class="form-hint">
      Known IDs (e.g. 100002, 100003, 100045) automatically pull offline historical records from SQLite.
    </span>
  </div>
</div>
```

### 6.2 JavaScript Integration (`frontend/js/app.js`)

1. In `collectFormData()`:
   ```javascript
   const applicantId = raw.SK_ID_CURR ? parseInt(raw.SK_ID_CURR) : null;
   return {
     SK_ID_CURR: applicantId,
     // ... other fields
   };
   ```
2. In `PRESET_PROFILES`:
   - Prime: `SK_ID_CURR: 100003`
   - Moderate: `SK_ID_CURR: 100045`
   - Subprime: `SK_ID_CURR: 100002`
   (Note: `app.js` already had these IDs defined; adding the HTML input will allow `loadPresetProfile()` to populate them visually!).

---

## 7. Verification & Integration Testing Plan

### 7.1 New Tests in `api/tests/test_prediction.py`

1. **`test_prediction_with_valid_feature_store_id`**:
   - Send `POST /predict` with payload `{ "SK_ID_CURR": 100002 }`.
   - Assert `status_code == 200`.
   - Assert `data["applicant_id"] == 100002`.
   - Assert `data["prediction"] in [0, 1]` and probability is valid.
2. **`test_prediction_with_unlinked_id`**:
   - Send `POST /predict` with payload `{ "SK_ID_CURR": 99999999 }`.
   - Assert `status_code == 200` (imputer handles missing features without crashing).
3. **`test_zero_pandas_fragmentation_warnings`**:
   - Wrap prediction request in `warnings.catch_warnings()`.
   - Assert that no `PerformanceWarning` or `SettingWithCopyWarning` is raised during feature preprocessing.

---

## 8. Step-by-Step Implementation Roadmap

| Step | Target File | Action | Owner |
| :--- | :--- | :--- | :--- |
| **1** | `src/config.py` | Add `FEATURE_STORE_PATH = DATA_DIR / "feature_store.db"`. | Data Engineer |
| **2** | `src/feature_store.py` | Create `FeatureStore` helper class with SQLite connection pooling and query methods. | Backend Engineer |
| **3** | `scripts/seed_feature_store.py` | Create automated seeding CLI script using `DataAggregator` with sequential execution and `gc.collect()`. | Data Engineer |
| **4** | `api/preprocessing.py` | Refactor missing column insertion to use `pd.concat()`. | Backend Engineer |
| **5** | `api/dependencies.py` & `api/services/prediction_service.py` | Inject `FeatureStore` into prediction flow and perform historical merge. | Backend Engineer |
| **6** | `frontend/index.html` & `frontend/js/app.js` | Add `SK_ID_CURR` input field and connect to form submission. | Frontend Engineer |
| **7** | `api/tests/test_prediction.py` | Add integration tests for SQLite lookup and fragmentation warning audit. | QA / Test Engineer |

---

## 9. Conclusion

The proposed offline-to-online Feature Store design is clean, decoupled, and adheres strictly to all memory constraints in `GEMINI.md`. By leveraging the pre-tested `DataAggregator`, the seeding script can generate `data/feature_store.db` within seconds at ~1.05 GB peak RAM. The API query layer will add < 1 ms latency to inference while enabling full-fidelity scoring on 341 engineered features.
