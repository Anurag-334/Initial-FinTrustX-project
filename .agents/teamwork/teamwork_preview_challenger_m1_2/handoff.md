# Challenger M1-2 Handoff Report — Data Leakage & Integrity Verification

**Agent**: Challenger M1-2 (`teamwork_preview_challenger_m1_2`)  
**Role**: Empirical Challenger (critic, specialist)  
**Milestone**: Milestone 1 (Dataset Integration & Memory Management Pipeline)  
**Date**: 2026-10-05  
**Final Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Empirical Verification Test Suite Execution
An independent, standard-library unit test suite was implemented in `tests/test_data_integrity_challenger.py` and executed via Python unittest runner:
Command:
```powershell
& 'd:\Projects\Credit-risk-ai\.venv\Scripts\python.exe' -m unittest tests/test_data_integrity_challenger.py
```
Verbatim stdout/stderr output:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 5.621s

OK

[CHALLENGER M1-2] Loading artifacts for empirical verification...
Loaded Train: (246008, 342), Test: (61503, 342)
Loaded Features: 341 names
```

Additionally, peer test suite `tests/test_adversarial_m1.py` was executed with system Python pytest:
Command:
```powershell
& 'C:\Program Files\Python313\python.exe' -m pytest tests/test_adversarial_m1.py
```
Verbatim stdout/stderr output:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Projects\Credit-risk-ai
plugins: anyio-4.9.0, langsmith-0.7.22
collected 14 items

tests\test_adversarial_m1.py ..............                              [100%]

============================= 14 passed in 5.60s ==============================
```

### 1.2 Applicant Identifier (`SK_ID_CURR`) Exclusion
1. `models/preprocessed_feature_names.csv`:
   - Total rows: 341 feature names.
   - Exact query: `"SK_ID_CURR" in feat_names` -> `False`.
   - Prefix queries: `"num__SK_ID_CURR" in feat_names` -> `False`, `"cat__SK_ID_CURR" in feat_names` -> `False`.
   - Feature inspection for substring `ID`: Only valid count/demographic features were observed:
     - `num__DAYS_ID_PUBLISH` (Kaggle application feature)
     - `num__BUREAU_SK_ID_BUREAU_COUNT` (aggregated count of bureau credit records)
     - `num__PREV_SK_ID_PREV_COUNT` (aggregated count of prior application records)
     - `cat__WEEKDAY_APPR_PROCESS_START_FRIDAY` (day of week category)
2. `data/processed_train.parquet` and `data/processed_test.parquet`:
   - Train columns: 342 (341 features + 1 `TARGET`). `SK_ID_CURR` not present.
   - Test columns: 342 (341 features + 1 `TARGET`). `SK_ID_CURR` not present.
3. `models/preprocessing_pipeline.joblib`:
   - Inspecting `ColumnTransformer.transformers_`:
     - `Transformer 'num'`: Pipeline (Imputer + Scaler), 201 columns.
     - `Transformer 'cat'`: Pipeline (Imputer + OneHot), 16 columns.
     - `Transformer 'remainder'`: `'drop'`, targeting `['SK_ID_CURR']`.
   - Even if raw input containing `SK_ID_CURR` is supplied during inference, the pipeline drops `SK_ID_CURR`.

### 1.3 Disjoint Index Splitting
1. Index overlap check:
   - `train_indices = set(df_train.index)` -> length 246,008.
   - `test_indices = set(df_test.index)` -> length 61,503.
   - `len(train_indices.intersection(test_indices))` -> exactly `0`.
2. Completeness check:
   - `train_indices.union(test_indices) == set(range(307511))` -> evaluates to `True`.
   - Minimum index: `0`, Maximum index: `307510`.
   - Zero duplicated indices within train (`df_train.index.duplicated().sum() == 0`) and zero within test (`df_test.index.duplicated().sum() == 0`).
   - Feature duplicate rows: `df_train.drop(columns=['TARGET']).duplicated().sum() == 0`, `df_test.drop(columns=['TARGET']).duplicated().sum() == 0`.

### 1.4 Target Default Rates
Direct empirical calculation on persisted parquet artifacts:
1. Training partition (`data/processed_train.parquet`):
   - Total applications: 246,008
   - Defaults (`TARGET == 1`): 19,860
   - Non-defaults (`TARGET == 0`): 226,148
   - Empirical default rate: `19860 / 246008 = 0.0807290819...` (8.0729%)
2. Test partition (`data/processed_test.parquet`):
   - Total applications: 61,503
   - Defaults (`TARGET == 1`): 4,965
   - Non-defaults (`TARGET == 0`): 56,538
   - Empirical default rate: `4965 / 61503 = 0.0807277596...` (8.0728%)
3. Combined dataset (`data/raw/application_train.csv` preserved total):
   - Total defaults: `19860 + 4965 = 24825` out of 307,511 (8.07288%)
   - Stratification delta between train and test: `|8.072908% - 8.072776%| = 0.000132%`.

### 1.5 Absence of Missing and Infinite Values
Comprehensive scan across all feature columns (excluding `TARGET`):
- Train feature matrix: 246,008 rows × 341 features = 83,888,728 total values.
  - NaNs: `0`
  - Positive Infinity (`+inf`): `0`
  - Negative Infinity (`-inf`): `0`
- Test feature matrix: 61,503 rows × 341 features = 20,972,523 total values.
  - NaNs: `0`
  - Positive Infinity (`+inf`): `0`
  - Negative Infinity (`-inf`): `0`
- Zero-variance features: `0` columns have zero variance.
- Extreme unbounded values: All numerical features are bounded, median-imputed, and standard-scaled.

---

## 2. Logic Chain

1. **Verification of ID Leakage Elimination (Section 1.2)**:
   - In previous iterations, `SK_ID_CURR` was included in numeric features, resulting in tree models assigning 2.57% feature importance to an arbitrary database key.
   - Observations show that `DataPreprocessor.detect_features()` excludes `"SK_ID_CURR"`, routing it directly into `remainder='drop'` in `ColumnTransformer`.
   - Feature inspection confirms neither `preprocessed_feature_names.csv` nor the Parquet feature columns contain `SK_ID_CURR`.
   - Deduces: Applicant ID data leakage has been completely eliminated from the training and evaluation pipelines.

2. **Verification of Disjoint Partitions (Section 1.3)**:
   - If training and evaluation partitions share any applicant records or indices, evaluation metrics (ROC-AUC) will be inflated due to data leakage.
   - Observation confirms `len(train_indices & test_indices) == 0`, and the union forms the exact continuous integer set `[0, 307510]`.
   - Deduces: Train and test partitions are strictly disjoint and constitute an exact, non-overlapping partition of the 307,511 loan applications.

3. **Verification of Class Stratification (Section 1.4)**:
   - Credit default prediction exhibits severe class imbalance (~11:1). Unstratified sampling risks altering the baseline default probability.
   - Observation confirms default rates on train (8.0729%, 19,860/246,008) and test (8.0728%, 4,965/61,503) match the population default rate (8.0729%, 24,825/307,511) to within 0.00013%.
   - Deduces: Stratified sampling preserved the exact empirical risk distribution without selection bias.

4. **Verification of Data Integrity and Numerical Stability (Section 1.5)**:
   - Machine learning algorithms (specifically gradient boosted decision trees and neural networks) can crash or produce corrupted gradient updates when encountering NaN, null, or infinite values resulting from zero-division in financial ratios.
   - Observation confirms that across all 104,861,251 audited feature values in train and test sets, exactly 0 NaNs and 0 infinite values exist.
   - Deduces: Feature transformations and pipeline imputations are numerically robust and ready for production model training.

---

## 3. Caveats

1. **Scikit-learn Version Inconsistency**:
   - `models/preprocessing_pipeline.joblib` was pickled under scikit-learn `1.7.2` (system Python environment). Loading it inside `.venv` (which contains scikit-learn `1.9.0`) issues an `InconsistentVersionWarning`. While the pipeline deseries and executes without errors in both environments, aligning the virtual environment scikit-learn version with the serializer version is advised for long-term production stability.
2. **Current Served Model Artifact (`models/xgboost.joblib`)**:
   - The serialized `models/xgboost.joblib` artifact currently in `models/` is the legacy 245-feature model from prior runs. Running inference with the new 341-feature `preprocessing_pipeline.joblib` against this legacy model will trigger a feature dimension mismatch. This is expected at Milestone 1 and is slated for Milestone 2 (`M2: Augmented Model Training & Benchmark Evaluation`).
3. **Auxiliary Raw Tables**:
   - Only `bureau.csv` and `previous_application.csv` were aggregated and integrated, adhering strictly to user requirements R1 and R2.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- All Milestone 1 data integrity, non-leakage, and memory management constraints are satisfied:
  - `SK_ID_CURR` is strictly excluded from all feature matrices and output schemas.
  - Train and test partitions have zero index overlap (`len(set(train) & set(test)) == 0`).
  - Target default rates match expected rates: 8.0729% (train) and 8.0728% (test).
  - Preprocessed feature matrices contain zero NaN or infinite values across all 104,861,251 elements.
  - Preprocessing pipeline and feature naming schemas are aligned and reproducible.
- Deliverables are approved to advance to Milestone 2 (Augmented Model Training).

---

## 5. Verification Method

To independently verify all findings in this report:

1. **Run the Challenger Unit Test Suite**:
   ```powershell
   & 'd:\Projects\Credit-risk-ai\.venv\Scripts\python.exe' -m unittest tests/test_data_integrity_challenger.py
   ```
   *Expected outcome*: 8 tests run and pass (`OK`) in ~5 seconds.

2. **Run the Peer Adversarial Test Suite**:
   ```powershell
   & 'C:\Program Files\Python313\python.exe' -m pytest tests/test_adversarial_m1.py
   ```
   *Expected outcome*: 14 passed in ~5 seconds.

3. **Verify Interactive Python Assertions**:
   ```python
   import pandas as pd, numpy as np

   tr = pd.read_parquet("data/processed_train.parquet")
   te = pd.read_parquet("data/processed_test.parquet")
   feats = pd.read_csv("models/preprocessed_feature_names.csv")["feature_name"].tolist()

   assert len(set(tr.index) & set(te.index)) == 0
   assert "SK_ID_CURR" not in feats
   assert "num__SK_ID_CURR" not in feats
   assert tr["TARGET"].sum() == 19860 and len(tr) == 246008
   assert te["TARGET"].sum() == 4965 and len(te) == 61503
   assert not tr[feats].isna().any().any()
   assert np.isfinite(tr[feats].values).all()
   print("Empirical verification complete: all assertions hold.")
   ```
