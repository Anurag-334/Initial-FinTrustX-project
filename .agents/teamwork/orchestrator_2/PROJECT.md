# Project: Offline-to-Online SQLite Feature Store & API Integration

## Architecture
- **Offline Data Layer**: `src/data_aggregation.py` / `data/raw/` providing applicant-level aggregated bureau and previous application features.
- **Online Feature Store**: SQLite database (`data/feature_store.db`), table `applicant_features` with primary key `SK_ID_CURR` for low-latency indexed queries (0.044 ms mean latency, 16,600 QPS).
- **Seeding Automation**: `scripts/seed_feature_store.py` memory-managed pipeline conforming to `GEMINI.md` (downcasting, sequential execution, explicit `gc.collect()`, peak RAM 211 MB).
- **Feature Store Client**: `api/feature_store.py` (`FeatureStore` class) with connection pooling, WAL mode, error handling.
- **API Serving Layer**: FastAPI (`api/main.py`, `api/services/prediction_service.py`, `api/services/explanation_service.py`, `api/schemas.py`).
  - Feature retrieval by `SK_ID_CURR`.
  - Selective override merging (`incoming payload overrides historical features`).
  - Imputation refactoring using `pd.concat()` in `api/preprocessing.py` to eliminate `PerformanceWarning`.
- **Frontend Dashboard**: `frontend/index.html` + `frontend/js/app.js` with visual `SK_ID_CURR` input field and preset profile synchronization.
- **Verification Layer**: Pytest integration tests in `api/tests/test_prediction.py` verifying DB retrieval, backward compatibility, and zero fragmentation warnings.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | SQLite Feature Store Schema & DB | SQLite database `data/feature_store.db` with table `applicant_features` indexed on `SK_ID_CURR` | M1 | R1 | DONE |
| 2 | Automated DB Seeding Script | `scripts/seed_feature_store.py` with memory optimization (`GEMINI.md`) and batch insertion | M1 | R1 | DONE |
| 3 | Feature Store Client Module | `api/feature_store.py` client providing clean single and batch query interface | M2 | R2 | DONE |
| 4 | FastAPI Dependency & Configuration | `api/config.py` paths and `api/dependencies.py` wiring for FeatureStore | M2 | R2 | DONE |
| 5 | Request Schema Alignment | `api/schemas.py` validating `SK_ID_CURR` and fixing any schema imports | M2 | R2 | DONE |
| 6 | Prediction Service Feature Merging | `api/services/prediction_service.py` fetching DB features and merging with user overrides | M2 | R2 | DONE |
| 7 | Explanation Service Feature Merging | `api/services/explanation_service.py` feature retrieval and merging consistency | M2 | R2 | DONE |
| 8 | Preprocessing Optimization (`pd.concat`) | `api/preprocessing.py` refactored to eliminate Pandas `PerformanceWarning` | M2 | R3 | DONE |
| 9 | Frontend HTML Applicant ID Input | `frontend/index.html` form element with label, input, and styling | M3 | R4 | DONE |
| 10 | Frontend JS Data Binding | `frontend/js/app.js` capturing input, updating presets, and sending payload | M3 | R4 | DONE |
| 11 | Integration Test: DB Feature Retrieval | `api/tests/test_prediction.py` test asserting prediction with DB lookup | M4 | AC3 | DONE |
| 12 | Integration Test: Backward Compatibility | `api/tests/test_prediction.py` test asserting prediction without `SK_ID_CURR` | M4 | AC3 | DONE |
| 13 | Integration Test: Zero Fragmentation | `api/tests/test_prediction.py` test asserting zero Pandas warnings | M4 | AC4 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status | Outputs |
|---|------|-------|-------------|--------|---------|
| M1 | Feature Store SQLite DB & Seeding Script | `scripts/seed_feature_store.py`, `data/feature_store.db`, `tests/test_feature_store.py` | none | DONE | 356,255 rows seeded in 23.5s, 98 cols, peak RAM 211 MB, 4/4 tests pass |
| M2 | Backend Integration & Preprocessing Optimization | `api/config.py`, `api/schemas.py`, `api/feature_store.py`, `api/dependencies.py`, `api/services/prediction_service.py`, `api/services/explanation_service.py`, `api/preprocessing.py` | M1 | DONE | FeatureStore client, override precedence, vectorized pd.concat, 0 warnings |
| M3 | Frontend UI Update | `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js` | M2 | DONE | Applicant ID input in Section A, preset binding, clean empty submission |
| M4 | Integration Testing & Acceptance Verification | `api/tests/test_prediction.py`, `tests/test_feature_store_challenger.py` | M1, M2, M3 | DONE | Gate Result: PASS (Reviewers: APPROVE, Challengers: APPROVE, Auditor: CLEAN) |

## Interface Contracts
### `api/feature_store.py` ↔ `api/services/prediction_service.py`
```python
class FeatureStore:
    def __init__(self, db_path: str | Path, table_name: str = "applicant_features"):
        ...
    def get_applicant_features(self, sk_id_curr: int) -> dict[str, Any] | None:
        """Returns dict of feature name -> value, or None if not found or DB missing."""
        ...
    def get_batch_applicant_features(self, sk_id_currs: list[int]) -> dict[int, dict[str, Any]]:
        """Returns map of sk_id_curr -> feature dict."""
        ...
```

### Incoming Payload vs Feature Store Merge Semantics
```python
# User inputs take precedence over historical features
user_inputs = request.model_dump(exclude_unset=True)
historical_features = feature_store.get_applicant_features(sk_id_curr) or {}
merged_data = {**historical_features, **user_inputs}
```

### Preprocessing Vectorized Imputation Contract
```python
# In api/preprocessing.py:
missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]
if missing_cols:
    df_missing = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)
    df_raw = pd.concat([df_raw, df_missing], axis=1)
df_aligned = df_raw[raw_feature_names]
```

## Code Layout
- `data/feature_store.db`: SQLite database file (162.83 MB, 356,255 rows $\times$ 98 columns).
- `scripts/seed_feature_store.py`: Standalone CLI script with chunked WAL insertion and GEMINI.md memory rules.
- `api/feature_store.py`: Thread-safe SQLite feature store client.
- `api/config.py`: Configuration constants (`FEATURE_STORE_DB_PATH`, `FEATURE_STORE_TABLE_NAME`).
- `api/dependencies.py`: Dependency injection provider `get_feature_store()`.
- `api/schemas.py`: Pydantic models supporting `SK_ID_CURR` and `applicant_id` alias.
- `api/services/prediction_service.py`: Single and batch prediction with selective override merging.
- `api/services/explanation_service.py`: SHAP explanation with merged profile.
- `api/preprocessing.py`: Vectorized `pd.concat(axis=1)` missing column imputation.
- `frontend/index.html`: Applicant ID form element in Section A.
- `frontend/css/style.css`: Theme styling for `.form-group label` and `.field-hint`.
- `frontend/js/app.js`: Dynamic preset binding and payload construction.
- `api/tests/test_prediction.py`: Comprehensive integration test suite (15 passed).
- `tests/test_feature_store.py`: Feature store unit and latency tests (4 passed).
- `tests/test_feature_store_challenger.py`: Adversarial stress test suite (26 passed).
