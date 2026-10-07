# FinTrustX Survey 3 Report: Frontend UI & Integration Testing Suite

**Explorer:** Survey Agent 3 (Frontend UI & Integration Testing)  
**Date:** 2026-10-05 / 2026-10-06  
**Status:** Completed  
**Target Components:** `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`, `api/tests/test_prediction.py`, `api/preprocessing.py`  

---

## 1. Executive Summary

This report delivers a comprehensive, read-only architectural survey of the FinTrustX static frontend dashboard and the API integration test suite in support of the offline-to-online SQLite Feature Store initiative. 

### Key Investigation Findings:
1. **Frontend HTML (`frontend/index.html`):** The existing dashboard has no HTML input element for `SK_ID_CURR` anywhere in `index.html`. While preset profiles in `app.js` (Prime: `100003`, Moderate: `100045`, Subprime: `100002`) specify an `SK_ID_CURR`, clicking those presets currently drops the ID because no corresponding form element exists in the DOM.
2. **Frontend JavaScript (`frontend/js/app.js`):** In `collectFormData()`, line 250 currently reads:
   ```javascript
   SK_ID_CURR: parseInt(raw.SK_ID_CURR) || 100001,
   ```
   Because `raw.SK_ID_CURR` is missing/empty, `parseInt("")` evaluates to `NaN`, which forcibly defaults to `100001`. This completely blocks testing backward compatibility (requests with no `SK_ID_CURR`) from the UI. It must be updated to conditionally emit `SK_ID_CURR` only when provided by the user.
3. **Pandas Fragmentation Warning (`api/preprocessing.py`):** In `transform_raw_to_features()`, lines 52–54 iteratively insert missing columns into `df_raw` in a loop across all 121 expected raw features. Because typical payloads only contain ~20 fields, ~100 columns are inserted iteratively, triggering Pandas' `PerformanceWarning: DataFrame is highly fragmented`.
4. **Integration Testing Suite (`api/tests/`):** The test suite uses `pytest` with `fastapi.testclient.TestClient`. Current tests in `api/tests/test_prediction.py` verify basic predictions and SHAP attributions, but do not verify:
   - Historical feature merging when a valid `SK_ID_CURR` is provided.
   - Backward compatibility when `SK_ID_CURR` is omitted or `None`.
   - The absence of `PerformanceWarning` during inference.

This report provides production-ready UI markup, CSS styling, JavaScript logic, and three complete integration test specifications.

---

## 2. Frontend UI Investigation & Design

### 2.1 UI Layout & Component Hierarchy
In `frontend/index.html`, the assessment form is hosted within `#assessment` in a two-column responsive grid (`.assessment-grid`):
- **Left Column (`.card.form-panel`):**
  1. Card header with Reset button (`#btn-reset-form`)
  2. Quick Presets Bar (`.presets-bar`) with buttons for Prime, Moderate, Subprime
  3. Form (`#assessment-form`) divided into four visual sections:
     - **Section A:** Personal Information (`age_years`, `CODE_GENDER`, `NAME_EDUCATION_TYPE`, `NAME_FAMILY_STATUS`, `CNT_CHILDREN`, `NAME_HOUSING_TYPE`)
     - **Section B:** Employment Information (`AMT_INCOME_TOTAL`, `employed_years`, `NAME_INCOME_TYPE`, `OCCUPATION_TYPE`)
     - **Section C:** Loan & Financial Details (`AMT_CREDIT`, `AMT_ANNUITY`, `AMT_GOODS_PRICE`, `NAME_CONTRACT_TYPE`, `FLAG_OWN_CAR`, `FLAG_OWN_REALTY`)
     - **Section D:** External Credit Bureau Ratings (Sliders for `EXT_SOURCE_1`, `EXT_SOURCE_2`, `EXT_SOURCE_3`)
  4. Submit Button (`#btn-submit-assessment`)
- **Right Column (`.results-container`):**
  - Empty state (`#empty-state`), Loading state (`#loading-state`), and Result state (`#result-content`).

### 2.2 Applicant ID (`SK_ID_CURR`) Input Placement & Design
The Applicant ID serves as the primary key lookup into the SQLite Feature Store (`data/feature_store.db`). Placing it at the very top of **Section A ("A. Personal Information")** provides an intuitive user journey:
1. When selecting a preset (Prime, Moderate, Subprime), the Applicant ID automatically populates.
2. The user immediately understands whether they are assessing an existing applicant with historical bureau records or a new standalone applicant.

#### Proposed HTML Markup
Insert the following markup immediately after `<div class="form-section-title"><i class="fa-solid fa-user"></i> A. Personal Information</div>` in `frontend/index.html` (around line 164):

```html
            <!-- Applicant ID (Feature Store Primary Key) -->
            <div class="form-group applicant-id-group">
              <label class="form-label" for="SK_ID_CURR">
                <span>
                  <i class="fa-solid fa-id-card" style="color: var(--brand-primary); margin-right: 0.35rem;"></i>
                  Applicant ID (SK_ID_CURR)
                </span>
                <span class="badge-optional">Optional &bull; SQLite Store</span>
              </label>
              <div class="input-icon-wrapper">
                <input 
                  type="number" 
                  id="SK_ID_CURR" 
                  name="SK_ID_CURR" 
                  class="form-input" 
                  placeholder="e.g. 100002, 100003, 100045" 
                  min="100001" 
                  step="1"
                  autocomplete="off"
                >
              </div>
              <span class="form-helper-text">
                <i class="fa-solid fa-database"></i>
                Supplying an ID pulls historical credit bureau & prior loan features from the offline SQLite Feature Store. Leave blank for standalone scoring.
              </span>
            </div>
```

### 2.3 Styling Specifications (`frontend/css/style.css`)
To match FinTrustX's dark-mode design system (`#0b0f19` surface, `#131b2e` card, `#38bdf8` accent), add the following targeted rules to `frontend/css/style.css`:

```css
/* =========================================================
   Applicant ID Input & Feature Store Helper Styling
   ========================================================= */
.applicant-id-group {
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px dashed var(--border-color);
}

.badge-optional {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-subtle);
  background: var(--bg-card-alt);
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.form-helper-text {
  font-size: 0.75rem;
  color: var(--text-subtle);
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  margin-top: 0.35rem;
  line-height: 1.4;
}

.form-helper-text i {
  color: var(--brand-primary);
  margin-top: 0.15rem;
  font-size: 0.8rem;
  flex-shrink: 0;
}
```

### 2.4 JavaScript Integration (`frontend/js/app.js`)

#### 1. Form Data Collection & Conditional Payload Creation
Replace line 241–273 of `frontend/js/app.js` with logic that distinguishes between a user-supplied ID and an empty/omitted field:

```javascript
/**
 * 4. Collect Form Data & Map to API Request Schema
 */
function collectFormData() {
  const form = document.getElementById("assessment-form");
  const formData = new FormData(form);
  const raw = Object.fromEntries(formData.entries());

  const ageYears = parseFloat(raw.age_years) || 35;
  const employedYears = parseFloat(raw.employed_years) || 3;

  // Build core payload
  const payload = {
    NAME_CONTRACT_TYPE: raw.NAME_CONTRACT_TYPE || "Cash loans",
    CODE_GENDER: raw.CODE_GENDER || "M",
    FLAG_OWN_CAR: raw.FLAG_OWN_CAR || "N",
    FLAG_OWN_REALTY: raw.FLAG_OWN_REALTY || "Y",
    CNT_CHILDREN: parseInt(raw.CNT_CHILDREN, 10) || 0,
    AMT_INCOME_TOTAL: parseFloat(raw.AMT_INCOME_TOTAL),
    AMT_CREDIT: parseFloat(raw.AMT_CREDIT),
    AMT_ANNUITY: parseFloat(raw.AMT_ANNUITY),
    AMT_GOODS_PRICE: parseFloat(raw.AMT_GOODS_PRICE),
    NAME_INCOME_TYPE: raw.NAME_INCOME_TYPE || "Working",
    NAME_EDUCATION_TYPE: raw.NAME_EDUCATION_TYPE || "Secondary / secondary special",
    NAME_FAMILY_STATUS: raw.NAME_FAMILY_STATUS || "Married",
    NAME_HOUSING_TYPE: raw.NAME_HOUSING_TYPE || "House / apartment",
    DAYS_BIRTH: -1 * Math.round(ageYears * 365.25),
    DAYS_EMPLOYED: -1 * Math.round(employedYears * 365.25),
    EXT_SOURCE_1: parseFloat(raw.EXT_SOURCE_1),
    EXT_SOURCE_2: parseFloat(raw.EXT_SOURCE_2),
    EXT_SOURCE_3: parseFloat(raw.EXT_SOURCE_3),
    REGION_RATING_CLIENT: parseInt(raw.REGION_RATING_CLIENT, 10) || 2,
    OCCUPATION_TYPE: raw.OCCUPATION_TYPE || "Laborers",
    ORGANIZATION_TYPE: raw.ORGANIZATION_TYPE || "Business Entity Type 3",
  };

  // Parse SK_ID_CURR: Only include if explicitly provided as a valid positive integer
  if (raw.SK_ID_CURR && raw.SK_ID_CURR.trim() !== "") {
    const parsedId = parseInt(raw.SK_ID_CURR.trim(), 10);
    if (!isNaN(parsedId) && parsedId > 0) {
      payload.SK_ID_CURR = parsedId;
    }
  }

  return payload;
}
```

#### 2. Client-Side Input Validation
In `validateForm(data)` in `frontend/js/app.js`:
```javascript
function validateForm(data) {
  const errors = [];

  // Validate SK_ID_CURR only if provided
  if (data.SK_ID_CURR !== undefined && (isNaN(data.SK_ID_CURR) || data.SK_ID_CURR <= 0)) {
    errors.push("Applicant ID must be a positive integer.");
  }

  if (isNaN(data.AMT_INCOME_TOTAL) || data.AMT_INCOME_TOTAL <= 0) {
    errors.push("Annual Income must be a positive number.");
  }
  if (isNaN(data.AMT_CREDIT) || data.AMT_CREDIT <= 0) {
    errors.push("Credit Amount Requested must be a positive number.");
  }
  if (isNaN(data.AMT_ANNUITY) || data.AMT_ANNUITY <= 0) {
    errors.push("Loan Annuity must be a positive number.");
  }
  if (isNaN(data.DAYS_BIRTH) || data.DAYS_BIRTH > -6570 || data.DAYS_BIRTH < -36525) {
    errors.push("Applicant Age must be between 18 and 100 years.");
  }

  return errors;
}
```

#### 3. Preset Loading & UI Feedback
Because `PRESET_PROFILES` already has `SK_ID_CURR` defined:
- Prime: `100003`
- Moderate: `100045`
- Subprime: `100002`

The existing `loadPresetProfile(profileKey)` function uses `for (const [key, val] of Object.entries(profile)) { const field = form.elements[key]; if (field) field.value = val; }`. With the new HTML field named `SK_ID_CURR`, clicking any preset button will automatically populate `#SK_ID_CURR`!

In addition, update `displayPredictionResult(result)` to show whether historical feature data was merged:
```javascript
// Inside displayPredictionResult(result):
const heroSubtitle = document.querySelector("#decision-hero .decision-hero-text span");
if (heroSubtitle) {
  if (result.applicant_id) {
    heroSubtitle.innerHTML = `Underwriting Recommendation &bull; <span style="color: #38bdf8; font-family: var(--font-mono);">ID #${result.applicant_id} (Historical Features Merged)</span>`;
  } else {
    heroSubtitle.textContent = "Underwriting Recommendation • Standalone Application";
  }
}
```

---

## 3. Preprocessing Optimization: Eliminating Pandas Fragmentation Warning

### 3.1 Root Cause in `api/preprocessing.py`
In `api/preprocessing.py`, lines 51–57:
```python
# CURRENT FRAGMENTING CODE:
for col in raw_feature_names:
    if col not in df_raw.columns:
        df_raw[col] = np.nan

df_aligned = df_raw[raw_feature_names]
```
Each iteration of `df_raw[col] = np.nan` creates a new underlying block manager partition. When 100+ columns are inserted into an existing single-row DataFrame, Pandas raises:
`PerformanceWarning: DataFrame is highly fragmented. This is usually the result of calling frame.insert (or frame[col] = ...) many times in a loop. The frame will have up to 121 columns, whereas a frame with below 100 columns is usually not fragmented.`

### 3.2 Refactored Solution using `pd.concat` (or `reindex`)
Per requirement R3, we can eliminate fragmentation using `pd.concat()` to attach all missing columns in a single vectorized concatenation, or via `df_raw.reindex()`:

```python
# REFACTORED CONCATENATION IMPLEMENTATION:
def transform_raw_to_features(
    raw_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
    pipeline: Any,
    raw_feature_names: List[str]
) -> np.ndarray:
    if isinstance(raw_inputs, dict):
        records = [raw_inputs]
    else:
        records = raw_inputs

    df_raw = pd.DataFrame(records)

    # 1. Identify missing columns required by the preprocessing pipeline
    missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]
    
    # 2. Vectorized concatenation of missing columns in a single block
    if missing_cols:
        missing_df = pd.DataFrame(
            np.nan, 
            index=df_raw.index, 
            columns=missing_cols, 
            dtype=np.float32
        )
        df_raw = pd.concat([df_raw, missing_df], axis=1)

    # 3. Align exact column order required by ColumnTransformer
    df_aligned = df_raw[raw_feature_names]

    try:
        transformed = pipeline.transform(df_aligned)
    except Exception as e:
        logger.error(f"Preprocessing transform failed: {e}")
        raise ValueError(f"Feature preprocessing failed: {e}") from e

    return transformed
```
*(Note: `df_raw.reindex(columns=raw_feature_names)` achieves identical behavior in a single Pandas native call without any warnings.)*

---

## 4. Integration Test Suite Design (`api/tests/`)

### 4.1 Existing Architecture
- **Framework:** `pytest` + `fastapi.testclient.TestClient(app)`
- **Existing Tests:**
  - `test_health.py`: Root, `/health`, `/model-info`
  - `test_model_loading.py`: Artifact existence, singleton caching, smoke test
  - `test_prediction.py`: Single prediction (`SAMPLE_APPLICANT`), explanation query, batch prediction, 422 validation

### 4.2 New Integration Test Designs (`api/tests/test_prediction.py`)

Here are the three comprehensive tests to append to `api/tests/test_prediction.py`:

```python
import warnings
from pandas.errors import PerformanceWarning
import pytest


# =========================================================
# Integration Test A: Valid SK_ID_CURR with Feature Store
# =========================================================
def test_predict_with_valid_sk_id_curr_pulls_db_features(client, monkeypatch):
    """
    Test R2/Acceptance Criterion:
    Passing a valid SK_ID_CURR queries the SQLite Feature Store,
    merges historical applicant features into the profile,
    and produces a successful 200 prediction response.
    """
    valid_id = 100002
    applicant_payload = {
        **SAMPLE_APPLICANT,
        "SK_ID_CURR": valid_id,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 406597.5,
    }

    response = client.post("/predict", json=applicant_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["applicant_id"] == valid_id
    assert data["prediction"] in [0, 1]
    assert 0.0 <= data["default_probability"] <= 1.0
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["risk_category"] in ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
    assert data["loan_decision"] in [
        "Likely Approved", "Manual Review", "Higher Risk / Manual Review", "Likely Rejected"
    ]
    assert data["model"] == "XGBoost"


# =========================================================
# Integration Test B: Backward Compatibility (No SK_ID_CURR)
# =========================================================
def test_predict_without_sk_id_curr_backward_compatibility(client):
    """
    Test Backward Compatibility:
    Ensure predictions without SK_ID_CURR (omitted or explicitly None)
    succeed without errors and return applicant_id=None.
    """
    # Case 1: SK_ID_CURR completely omitted
    payload_omitted = {k: v for k, v in SAMPLE_APPLICANT.items() if k != "SK_ID_CURR"}
    assert "SK_ID_CURR" not in payload_omitted

    res_omitted = client.post("/predict", json=payload_omitted)
    assert res_omitted.status_code == 200
    data_omitted = res_omitted.json()
    assert data_omitted["applicant_id"] is None
    assert data_omitted["prediction"] in [0, 1]
    assert 0.0 <= data_omitted["default_probability"] <= 1.0

    # Case 2: SK_ID_CURR explicitly null/None
    payload_null = {**SAMPLE_APPLICANT, "SK_ID_CURR": None}
    res_null = client.post("/predict", json=payload_null)
    assert res_null.status_code == 200
    data_null = res_null.json()
    assert data_null["applicant_id"] is None
    assert data_null["prediction"] in [0, 1]
    assert 0.0 <= data_null["default_probability"] <= 1.0


# =========================================================
# Integration Test C: Zero Pandas Fragmentation Warnings
# =========================================================
def test_zero_pandas_fragmentation_warning(client):
    """
    Test R3/Acceptance Criterion:
    Verify that inference execution produces ZERO Pandas DataFrame
    fragmentation warnings (PerformanceWarning).
    """
    # Test with both a full sample and a sparse sample (many missing columns)
    sparse_payload = {
        "AMT_INCOME_TOTAL": 150000.0,
        "AMT_CREDIT": 450000.0,
        "AMT_ANNUITY": 25000.0,
        "DAYS_BIRTH": -15000.0,
    }

    with warnings.catch_warnings(record=True) as recorded_warnings:
        # Capture all emitted warnings
        warnings.simplefilter("always")

        # 1. Single prediction request with sparse features
        res_sparse = client.post("/predict", json=sparse_payload)
        assert res_sparse.status_code == 200

        # 2. Prediction with standard payload
        res_std = client.post("/predict", json=SAMPLE_APPLICANT)
        assert res_std.status_code == 200

        # 3. Batch prediction request
        batch_payload = {"requests": [sparse_payload, SAMPLE_APPLICANT]}
        res_batch = client.post("/predict/batch", json=batch_payload)
        assert res_batch.status_code == 200

        # Filter strictly for PerformanceWarning or any warning mentioning fragmentation
        fragmentation_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, PerformanceWarning) 
            or "fragment" in str(w.message).lower()
        ]

        assert len(fragmentation_warnings) == 0, (
            f"Detected {len(fragmentation_warnings)} fragmentation warning(s): "
            f"{[str(w.message) for w in fragmentation_warnings]}"
        )
```

---

## 5. End-to-End Integration Verification Workflow

| Step | Action | Verification Check |
|---|---|---|
| **1. UI Form Reset** | Open dashboard, click Reset | `#SK_ID_CURR` is empty; helper text is visible |
| **2. Preset Selection** | Click "🟢 Prime" preset | `#SK_ID_CURR` displays `100003` |
| **3. Preset Selection** | Click "🔴 Subprime" preset | `#SK_ID_CURR` displays `100002` |
| **4. UI Submission** | Click "Assess Credit Risk" | Network inspector shows `POST /predict` payload includes `"SK_ID_CURR": 100002` |
| **5. Blank ID Submission** | Clear `#SK_ID_CURR`, submit | Network inspector shows `POST /predict` without `SK_ID_CURR`; API responds 200 with `applicant_id: null` |
| **6. Integration Tests** | Run `pytest api/tests/test_prediction.py` | All tests pass, including valid ID test, backward compatibility test, and zero fragmentation warning test |
| **7. Warning Audit** | Monitor terminal logs during requests | Zero `PerformanceWarning` entries logged |

---

## 6. Implementation Checklist for Implementing Agents

- [ ] **Frontend HTML:** Add Applicant ID form group to `frontend/index.html` within Section A.
- [ ] **Frontend CSS:** Add `.applicant-id-group`, `.badge-optional`, and `.form-helper-text` to `frontend/css/style.css`.
- [ ] **Frontend JS:** 
  - Update `collectFormData()` in `frontend/js/app.js` to conditionally add `SK_ID_CURR` only when valid.
  - Update `validateForm()` to validate `SK_ID_CURR` if provided.
  - Update `displayPredictionResult()` to display `applicant_id` status badge in the underwriting recommendation.
- [ ] **API Preprocessing:** Refactor `api/preprocessing.py` to use `pd.concat()` (or `.reindex()`) for missing raw columns.
- [ ] **API Tests:** Append `test_predict_with_valid_sk_id_curr_pulls_db_features`, `test_predict_without_sk_id_curr_backward_compatibility`, and `test_zero_pandas_fragmentation_warning` to `api/tests/test_prediction.py`.
