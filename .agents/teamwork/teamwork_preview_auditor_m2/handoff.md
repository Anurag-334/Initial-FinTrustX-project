# Forensic Audit & Handoff Report — Auditor M2: Milestone 2 Model Authenticity & Integrity Audit

**Date:** 2026-10-06  
**Working Directory:** `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_auditor_m2`  
**Auditor:** Forensic Auditor M2  
**Target:** Milestone 2 (`models/xgboost.joblib`, `models/xgboost.json`, `reports/model_comparison.csv`, evaluation metrics)  
**Integrity Mode:** Development Mode (per `ORIGINAL_REQUEST.md`)  
**Verdict:** **`CLEAN`**

---

## Forensic Audit Report

**Work Product**: `models/xgboost.joblib`, `models/xgboost.json`, `reports/model_comparison.csv`, `reports/business_metrics.csv`, `reports/model_metrics.csv`  
**Profile**: General Project (Development Mode)  
**Verdict**: **`CLEAN`**

### Phase Results
- **Check 1: File Existence & Integrity Hashes**: PASS — `models/xgboost.joblib` (2,867,396 bytes, SHA256: `5c1b8484...`) and `models/xgboost.json` (417 bytes, SHA256: `cb6cbf17...`) exist and are valid.
- **Check 2: Booster Architecture & Authenticity**: PASS — Authenticated as genuine `xgboost.sklearn.XGBClassifier` wrapping native C++ `xgboost.core.Booster` with exactly 970 boosted decision trees, 64,642 total nodes, 31,836 splits, and 32,806 leaves (`tree_method="hist"`). Not a mock, stub, or facade.
- **Check 3: Feature Space & Importance Distribution**: PASS — Model binds exactly 341 input features; 256 features exhibit non-zero splits; 99 supplementary features (`BUREAU_*` and `PREV_*`) actively contribute 36.28% of total feature importance mass. Zero customer identifier (`SK_ID_CURR`) leakage.
- **Check 4: Live Empirical Inference & Metric Verification**: PASS — Live inference on 61,503 held-out test rows generates 61,360 distinct continuous probabilities (range [0.001442, 0.839582]). Independently calculated ROC-AUC is `0.7793832838928354`, matching the Worker M2 report with 0.00e+00 discrepancy and strictly exceeding the baseline acceptance threshold (0.761038).
- **Check 5: Adversarial Stress & Permutation Sensitivity**: PASS — Permuting top 3 features drops ROC-AUC by -0.0952. Permuting 102 supplementary features drops ROC-AUC by -0.0378 (down to 0.741595, below baseline). Synthetic random noise inference produces 1,000 distinct predictions. Proves decision surface is dynamic and strictly depends on input data.
- **Check 6: Production Serving Compatibility**: PASS — `api/model_loader.py` smoke test passes with 341 features and 218 raw inputs; `api/tests/test_prediction.py` passes 5/5 tests in 6.46s.
- **Check 7: Forensic Cheating & Facade Prohibitions**: PASS — Zero hardcoded test outputs, zero facade methods, zero pre-populated verification bypasses, and zero memorized lookup tables.

---

## 1. Observation

Verbatim observations obtained empirically through direct Python inspection, booster graph extraction, live dataset scoring, and adversarial stress-testing:

### 1.1 Artifact Deserialization & Tree Graph Inspection
- **File Path**: `models/xgboost.joblib`
  - Size: `2,867,396` bytes (~`2,800.19` KB)
  - SHA256: `5c1b8484b4f7f3ffc9f0cdd7f6f8c214474a79b1bc0c5e09414987937791cb38`
  - Object Class: `<class 'xgboost.sklearn.XGBClassifier'>` (module: `xgboost.sklearn`)
  - Internal Booster: `<class 'xgboost.core.Booster'>`
- **File Path**: `models/xgboost.json`
  - Size: `417` bytes
  - SHA256: `cb6cbf171781dcbc79bf5894e6bf3eefecb8c85f07c092af5efc1b0451d18fe9`
  - Hyperparameters: `n_estimators=970`, `learning_rate=0.03`, `max_depth=6`, `min_child_weight=35`, `subsample=0.8`, `colsample_bytree=0.7`, `colsample_bylevel=0.7`, `gamma=1.0`, `reg_alpha=2.5`, `reg_lambda=8.0`, `tree_method="hist"`, `best_iteration=970`.
- **Booster Structure Metrics**:
  - Boosted rounds (`len(booster.get_dump())`): exactly **`970`** trees.
  - Total tree nodes: `64,642` nodes (`31,836` decision splits, `32,806` leaf outputs).
  - Tree node distribution: min = `17` nodes, max = `115` nodes, mean = `66.64` nodes, median = `65` nodes.
  - Booster internal configuration: `objective="binary:logistic"`, `tree_method="hist"`.

### 1.2 Feature Specification & Importance Mass
- **Total Expected Features**: `341` features (matching `models/preprocessed_feature_names.csv` and `data/processed_test.parquet`).
- **Feature Presence in Booster**: `booster.feature_names` contains exactly `341` strings.
- **Active Decision Features**: `256` of `341` features have non-zero decision splits across the 970 trees.
- **Top 5 Features by Gain**:
  1. `num__EXT_SOURCE_3`: gain = `86.5513`, weight = `789.0`
  2. `num__EXT_SOURCE_2`: gain = `82.4075`, weight = `859.0`
  3. `num__FLAG_EMP_PHONE`: gain = `74.4823`, weight = `5.0`
  4. `cat__NAME_EDUCATION_TYPE_Higher education`: gain = `58.2154`, weight = `77.0`
  5. `num__FLAG_NO_BUREAU_DATA`: gain = `53.6372`, weight = `31.0`
- **Supplementary Feature Utilization**:
  - `BUREAU_*` features with active splits: **`51`** features.
  - `PREV_*` features with active splits: **`48`** features.
  - Total supplementary features actively utilized: **`99`** features.
  - Total `BUREAU_*` feature importance mass: **`20.3848%`** (`0.2038484`).
  - Total `PREV_*` feature importance mass: **`15.9039%`** (`0.15903905`).
  - Combined supplementary importance mass: **`36.2887%`** (`0.36288745`).
- **Data Leakage Check**:
  - `SK_ID_CURR` present in model features: `False`.
  - Zero applicant ID tokens present in model splits.

### 1.3 Live Inference on Held-Out Test Set (61,503 Rows)
- **Data Path**: `data/processed_test.parquet` (shape: `61,503` rows $\times$ `342` cols, target default rate: `0.080728`).
- **Execution Performance**: 61,503 rows scored in `1.3179` seconds (`0.0214 ms/row`).
- **Predicted Probability Distribution**:
  - Minimum probability: `0.0014417`
  - Maximum probability: `0.8395820`
  - Mean probability: `0.0803008` (closely calibrated to actual default rate `0.080728`)
  - Standard deviation: `0.0890550`
  - Distinct probability values: **`61,360`** unique float values out of `61,503` rows (99.77% uniqueness).
- **Independently Computed Metrics**:
  - **ROC-AUC**: **`0.7793832838928354`** (Exact match to Worker M2 report; delta = `0.00e+00`).
  - Baseline ROC-AUC: `0.7610378899421779`.
  - Absolute ROC-AUC Lift: **`+0.0183453939506575`** (`+1.83%`).
  - Average Precision (PR-AUC): `0.27508940560037387` (Baseline: `0.250731`).
  - Accuracy: `0.9198413085540543`.
  - Precision (threshold 0.50): `0.5487465181058496`.
  - Recall (threshold 0.50): `0.039677744209466265`.
  - F1 Score: `0.07400450788880542`.
  - Balanced Accuracy: `0.5184062073482861`.
  - Log Loss: `0.23912769042232224`.
  - Brier Score Loss: `0.06621659509401012`.
  - Confusion Matrix (threshold 0.50): `TN=56,376`, `FP=162`, `FN=4,768`, `TP=197`.

### 1.4 Adversarial Stress & Permutation Testing
1. **Permutation Test A (Top Features)**:
   - Permuting `num__EXT_SOURCE_1`, `num__EXT_SOURCE_2`, and `num__EXT_SOURCE_3` on test data resulted in:
     - Perturbed ROC-AUC: `0.6841759823807510`
     - Absolute Performance Drop: **`-0.09520730151208445`** (-9.52 AUC points).
2. **Permutation Test B (Supplementary Features)**:
   - Permuting all `102` supplementary features (`BUREAU_*` and `PREV_*`) on test data resulted in:
     - Perturbed ROC-AUC: `0.7415952008607280`
     - Absolute Performance Drop: **`-0.037788083032107345`** (-3.78 AUC points).
     - Resulting AUC falls strictly *below* the baseline of `0.761038`.
3. **Perturbation Test C (Single-Feature Gradient Sensitivity)**:
   - Evaluated single applicant row with `num__EXT_SOURCE_3` delta sweeps:
     - $\Delta = -2.0$: predicted prob = `0.074828`
     - $\Delta = -1.0$: predicted prob = `0.051748`
     - $\Delta = 0.0$: predicted prob = `0.036118`
     - $\Delta = +1.0$: predicted prob = `0.026949`
     - $\Delta = +2.0$: predicted prob = `0.023799`
     - Shows smooth, monotonic risk decay as creditworthiness score increases.
4. **Synthetic Noise Test D**:
   - 1,000 synthetic random Gaussian noise vectors produced 1,000 unique probability outputs (min: `0.010524`, max: `0.467712`, mean: `0.100844`).

### 1.5 Serving & Integration Test Execution
- `python -c "from api.model_loader import ModelLoader; ..."`:
  - `loader.is_loaded`: `True`
  - `loader.run_smoke_test()`: `True`
  - Feature counts: `341` preprocessed, `218` raw features.
- `python -m pytest api/tests/test_prediction.py -v`:
  - Result: `5 passed, 0 failed in 6.46s`.
  - Tests verified: `test_predict_single`, `test_predict_with_explanation`, `test_explain_endpoint`, `test_batch_prediction`, `test_invalid_input_validation`.

---

## 2. Logic Chain

1. **Premise 1 (Authentic Architecture)**: If a model was a stub, lookup table, or facade, its internal booster would lack deep decision trees, exhibit trivial node counts, or fail to produce continuous predictions on synthetic inputs.
   - *Observation*: The booster contains exactly 970 trees with 64,642 nodes, an average of 66.64 nodes per tree, and generates 1,000 distinct continuous outputs for 1,000 synthetic inputs.
   - *Inference*: `models/xgboost.joblib` is an authentic, genuinely trained gradient-boosted tree ensemble.

2. **Premise 2 (Feature Utilization & Value Addition)**: If the supplementary features were merged nominally without providing value, they would have zero splits, negligible gain, and permuting them would not degrade performance.
   - *Observation*: 99 supplementary features are actively used in splits, accounting for 36.29% of the model's total importance mass. When permuted on the test set, ROC-AUC plummets from `0.779383` down to `0.741595` (a drop of 0.0378, dropping below the baseline model).
   - *Inference*: The supplementary features from Milestone 1 are genuinely ingested, modeled, and provide the critical +0.0183 AUC lift over baseline.

3. **Premise 3 (Metric Integrity)**: If the reported ROC-AUC of `0.779383` was fabricated or hardcoded in reports, live inference on the 61,503 held-out test records would produce a divergent score.
   - *Observation*: Independent scoring via `sklearn.metrics.roc_auc_score` yielded `0.7793832838928354`, matching Worker M2's claim to machine precision ($0.00\times 10^0$).
   - *Inference*: The reported metric is 100% authentic and reproducible.

4. **Premise 4 (Serving Compatibility & Zero Leakage)**: If the artifact expected inconsistent feature dimensions or memorized applicant IDs, the serving smoke tests would fail or applicant IDs would be present in splits.
   - *Observation*: `SK_ID_CURR` is absent from all features. `ModelLoader.run_smoke_test()` returned `True`, and all 5 endpoint prediction tests passed.
   - *Inference*: The artifact conforms strictly to the production API serving contracts without architectural breakage.

---

## 3. Caveats

- **Integrity Mode Context**: Under `ORIGINAL_REQUEST.md`, Integrity Mode is set to `development`. All standard libraries (`xgboost`, `scikit-learn`, `joblib`, `pandas`) are permitted and used appropriately.
- **API Legacy Test Assertion Notice**: While `api/tests/test_prediction.py` passes completely, legacy tests in `test_health.py` and `test_model_loading.py` check for the old baseline raw feature count (`121`) rather than the augmented count (`218`). Updating these assertions is scheduled for Milestone 3 hardening.
- **No Performance or Integrity Caveats**: There are zero caveats regarding the authenticity of the model, data integrity, or reported metrics.

---

## 4. Conclusion

- **Verdict**: **`CLEAN`**.
- `models/xgboost.joblib` is an authentic 970-tree gradient boosted tree classifier trained on 341 features.
- The reported test ROC-AUC score of **`0.779383`** is genuinely computed on 61,503 held-out test rows and surpasses the baseline threshold of `0.761038` by **`+0.018345`** (`+1.83%`).
- Milestone 2 acceptance criteria are fully met with complete integrity.

---

## 5. Verification Method

To independently reproduce the forensic verification:

### 1. Booster Authenticity and Tree Inspection
```powershell
python -c "import joblib; m = joblib.load('models/xgboost.joblib'); b = m.get_booster(); print('Tree count:', len(b.get_dump())); df = b.trees_to_dataframe(); print('Total nodes:', len(df)); print('Total splits:', (df['Feature'] != 'Leaf').sum()); assert len(b.get_dump()) == 970"
```

### 2. Live Independent Scoring & ROC-AUC Recalculation
```powershell
python -c "import joblib, pandas as pd, sklearn.metrics as sm; m = joblib.load('models/xgboost.joblib'); df = pd.read_parquet('data/processed_test.parquet'); X = df.drop(columns=['TARGET']); y = df['TARGET'].astype(int); p = m.predict_proba(X)[:, 1]; auc = sm.roc_auc_score(y, p); print('Calculated ROC-AUC:', auc); assert abs(auc - 0.7793832838928354) < 1e-12"
```

### 3. Supplementary Feature Importance Verification
```powershell
python -c "import joblib; m = joblib.load('models/xgboost.joblib'); fi = m.feature_importances_; supp_mass = sum(fi[i] for i, n in enumerate(m.feature_names_in_) if 'BUREAU' in n or 'PREV' in n); print('Supplementary feature mass:', supp_mass); assert supp_mass > 0.35"
```

### 4. Serving Compatibility Smoke Test
```powershell
python -c "from api.model_loader import ModelLoader; loader = ModelLoader(); loader.load_artifacts(); assert loader.run_smoke_test() is True; print('Smoke test PASSED')"
```

### 5. Prediction Pytest Suite
```powershell
python -m pytest api/tests/test_prediction.py -v
```

### Invalidation Conditions
- Any execution yielding an ROC-AUC $\le 0.761038$ on `data/processed_test.parquet`.
- Any modification resulting in tree count $\ne 970$ or feature count $\ne 341$.
- Any failure of `loader.run_smoke_test()` in `api/model_loader.py`.
