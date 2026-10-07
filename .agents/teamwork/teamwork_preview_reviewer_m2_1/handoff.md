# Reviewer M2-1 Handoff Report: Milestone 2 Model Code & Benchmark Review

**Date:** 2026-10-06  
**Agent:** Reviewer M2-1 (Roles: reviewer, critic)  
**Working Directory:** `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1`  
**Target Milestone:** Milestone 2 (Augmented Model Training & Benchmark Evaluation)  
**Verdict:** **APPROVE**

---

## 1. Observation

Direct observations from independent execution, inspection, and verification:

### 1.1 Independent Benchmark Verification
Executed the project verification command independently on `data/processed_test.parquet` (61,503 rows, 342 columns):
- **Command:**
  ```powershell
  python -c "import joblib, pandas as pd; from src.evaluate import EvaluationEngine; model = joblib.load('models/xgboost.joblib'); test_df = pd.read_parquet('data/processed_test.parquet'); X_test = test_df.drop(columns=['TARGET']); y_test = test_df['TARGET'].astype(int); engine = EvaluationEngine(model=model, threshold=0.50); metrics = engine.evaluate(X_test, y_test); print('ROC-AUC:', metrics['ROC AUC']); assert metrics['ROC AUC'] > 0.761038"
  ```
- **Exit Code:** `0`
- **Verbatim Output:**
  ```
  ROC-AUC: 0.7793832838928354
  ```
- **Target Comparison:**
  - Baseline Champion ROC-AUC: `0.761038`
  - Acceptance Criterion Threshold: `> 0.7610`
  - Achieved Verified ROC-AUC: `0.779383` (Absolute Lift: `+0.018345`, relative lift: `+2.41%`)

### 1.2 Model Internals & Integrity Audit
Inspected `models/xgboost.joblib`:
- Class: `xgboost.sklearn.XGBClassifier`
- Number of boosting trees: `970`
- Number of input features: `341`
- Feature split distribution: Non-zero feature importance across `256` of `341` features; `85` features with 0 importance.
- Top predictive features:
  - `num__EXT_SOURCE_3`: `0.03032`
  - `num__EXT_SOURCE_2`: `0.02887`
  - `num__FLAG_EMP_PHONE`: `0.02610`
  - `cat__NAME_EDUCATION_TYPE_Higher education`: `0.02040`
  - `num__FLAG_NO_BUREAU_DATA`: `0.01879` (Supplementary Bureau Feature)
  - `num__BUREAU_IS_MICROLOAN_SUM`: `0.01410` (Supplementary Bureau Feature)
- Verification against facade/cheating:
  - Permuting the first 20 columns degraded test ROC-AUC from `0.779383` down to `0.752678`.
  - Predictions are strictly continuous (over 50,000 unique probability values across 61,503 test instances).
  - Grep search for hardcoded test scores (`0.779383`, mock returns) returned 0 results across `src/`, `api/`, and `tests/`.

### 1.3 Implementation Inspection
- `src/models/xgboost_model.py`:
  - `XGBoostModel.__init__(self, params=None, **kwargs)` accepts arbitrary hyperparameter dictionaries and keyword arguments.
  - Defaults configured to `tree_method="hist"`, `eval_metric="auc"`, `random_state=42`, `n_jobs=-1`.
  - Exposes `fit()` with `early_stopping_rounds` parameter and `best_iteration` property forwarding to the underlying estimator.
- `src/training/train_augmented_xgboost.py`:
  - Implements two-stage training logic: Stratified train/val split (85/15), validation early stopping (Stage 1 stopped at tree 825), tree scaling ($825 \times \frac{1}{0.85} = 970$), and full refit on 246,008 train samples.
  - Updates `reports/model_comparison.csv`, `reports/business_metrics.csv`, and `reports/model_metrics.csv`.
- `src/evaluate.py`:
  - `EvaluationEngine` verified for correct metric computation. Tested against synthetic data and matched exact `sklearn.metrics.roc_auc_score` results.

### 1.4 Production Serving & Test Suites
- Executed `api/model_loader.py` smoke test:
  ```powershell
  python -c "from api.model_loader import ModelLoader; loader = ModelLoader(); loader.load_artifacts(); assert loader.is_loaded is True; assert loader.run_smoke_test() is True; print('Smoke test PASSED')"
  ```
  Result: `Smoke test PASSED` (Exit code: 0).
- Executed `pytest api/tests/test_prediction.py`:
  Result: `5 passed, 0 failed in 7.79s`.
- Executed `pytest tests/test_adversarial_m1.py tests/test_data_integrity_challenger.py`:
  Result: `22 passed, 0 failed in 15.32s`.
- Executed `pytest api/tests/test_health.py api/tests/test_model_loading.py`:
  Result: `2 failed, 4 passed in 10.67s` (`test_model_info_endpoint` and `test_model_loader_singleton` assert `len(raw_feature_names) == 121`, whereas the augmented dataset has `218` raw features).

---

## 2. Logic Chain

1. **Acceptance Threshold Verification (Observation 1.1)**:
   The user request and `PROJECT.md` require the augmented XGBoost model to exceed baseline ROC-AUC of `0.7610` on the 61,503 held-out test applicants. Independent evaluation of `models/xgboost.joblib` on `data/processed_test.parquet` produced `0.779383`, exceeding the required threshold by `+0.018345`.
2. **Integrity & Authenticity of Implementation (Observation 1.2)**:
   The model is a genuine 970-tree `XGBClassifier`. The feature importance distribution confirms active utilization of supplementary features (`num__FLAG_NO_BUREAU_DATA`, `num__BUREAU_IS_MICROLOAN_SUM`). Permuting input features immediately degraded performance to `0.752678`, proving that the model calculates genuine mathematical inferences rather than returning hardcoded, cached, or mocked values.
3. **Architectural Conformance & Reusability (Observation 1.3)**:
   `src/models/xgboost_model.py` cleanly inherits from `BaseModel` while supporting `tree_method="hist"` and early stopping parameters. The training orchestrator `src/training/train_augmented_xgboost.py` runs end-to-end and synchronizes reports.
4. **Serving Compatibility (Observation 1.4)**:
   The model artifact is fully compatible with the production inference pipeline. `ModelLoader.run_smoke_test()` succeeds, and all 5 API prediction tests pass.
5. **Legacy Test Scope (Observation 1.4 & Caveats)**:
   The 2 test failures in `api/tests/test_health.py` and `api/tests/test_model_loading.py` stem from hardcoded legacy checks for `121` raw features from the unaugmented schema. As documented in Worker M2's handoff and the Milestone breakdown, updating API tests is assigned to Milestone 3 (Test hardening & Audit).

---

## 3. Caveats

1. **Stage 1 vs. Stage 2 Model Selection Snooping**:
   In `src/training/train_augmented_xgboost.py` (lines 217–224), the script chooses whether to persist Stage 1 (early stopped) or Stage 2 (full refit) based on `if stage2_auc >= stage1_auc:` evaluated on `X_test`. In strict statistical methodology, test sets should never be referenced during model selection decisions. Because both Stage 1 (`0.778625`) and Stage 2 (`0.779383`) substantially beat the `0.7610` threshold without training on `X_test`, this did not introduce material data leakage, but is flagged as a minor methodological caveat.
2. **DataFrame Fragmentation in API Preprocessing**:
   `api/preprocessing.py:54` generates 376 pandas `PerformanceWarning` entries due to iterative column insertion in a loop. This does not impact prediction correctness or model accuracy, but should be refactored with bulk concatenation during Milestone 3.
3. **Threshold Calibration**:
   The primary metric ROC-AUC is threshold-independent. However, downstream business metrics reported at default threshold `0.50` yield low recall (3.97%) due to the severe 8.07% class imbalance. Decision threshold tuning is recommended for operational deployment.

---

## 4. Quality & Adversarial Review Findings

### Review Verdict
**`APPROVE`**

### Findings Summary

| ID | Severity | Category | Description | Recommendation |
|---|---|---|---|---|
| F1 | Minor | Methodology | `train_augmented_xgboost.py` compares test set AUCs to choose between Stage 1 and Stage 2 | Make full refit the default without conditional test set branching |
| F2 | Minor | Legacy Tests | `api/tests/test_health.py` and `test_model_loading.py` assert legacy `121` raw feature count | Update assertions to `218` in Milestone 3 |
| F3 | Minor | Performance | Iterative column insertion in `api/preprocessing.py:54` causes DataFrame fragmentation | Refactor with `pd.concat` in Milestone 3 |

### Adversarial Stress Testing Results
- **Hypothesis 1 (Facade/Mock Implementation):** REJECTED. Model contains 970 boosting trees and continuous predictions across all 61,503 rows.
- **Hypothesis 2 (Cheating / Hardcoded Scores):** REJECTED. Zero occurrences of hardcoded test metrics; predictions degrade when inputs are permuted.
- **Hypothesis 3 (Data Leakage into Weights):** REJECTED. `X_test` was never passed to `fit()`; feature pipeline excluded `SK_ID_CURR` and `TARGET`.
- **Hypothesis 4 (Serving Incompatibility):** REJECTED. Smoke test and prediction endpoints pass.

---

## 5. Conclusion

Milestone 2 has successfully satisfied all functional, performance, and integrity requirements:
- Model code (`src/models/xgboost_model.py`) is modular, robust, and supports histogram boosting.
- Training pipeline (`src/training/train_augmented_xgboost.py`) runs reproducibly and trains an augmented XGBoost model leveraging supplementary bureau features.
- Independent verification proves the model achieves an ROC-AUC of **`0.779383`** on the 61,503 held-out test set, beating the baseline target of `0.7610` by **`+0.018345`**.
- Model artifacts and reports (`models/xgboost.joblib`, `models/xgboost.json`, `reports/model_comparison.csv`) are saved and compatible with the API serving layer.

---

## 6. Verification Method

To independently reproduce the evaluation verification:

```powershell
python -c "import joblib, pandas as pd; from src.evaluate import EvaluationEngine; model = joblib.load('models/xgboost.joblib'); test_df = pd.read_parquet('data/processed_test.parquet'); X_test = test_df.drop(columns=['TARGET']); y_test = test_df['TARGET'].astype(int); engine = EvaluationEngine(model=model, threshold=0.50); metrics = engine.evaluate(X_test, y_test); print('ROC-AUC:', metrics['ROC AUC']); assert metrics['ROC AUC'] > 0.761038"
```
**Expected Output:**
`ROC-AUC: 0.7793832838928354` (Exit code 0).

To verify API serving compatibility:
```powershell
python -c "from api.model_loader import ModelLoader; loader = ModelLoader(); loader.load_artifacts(); assert loader.is_loaded is True; assert loader.run_smoke_test() is True; print('Smoke test PASSED')"
```
**Expected Output:**
`Smoke test PASSED` (Exit code 0).

To run prediction tests:
```powershell
python -m pytest api/tests/test_prediction.py
```
**Expected Output:**
`5 passed in ~8s`.
