# Task Assignment: Worker M2 (Milestone 2 — Augmented Model Training & Benchmark Evaluation)

## Context
You are Worker M2 for Milestone 2 (Augmented Model Training & Benchmark Evaluation).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2

## Mandatory Inputs & Specifications to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- Survey Modeling Specification:
  - `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_3\handoff.md`
- Existing Model and Evaluation Code:
  - `src/models/xgboost_model.py`
  - `src/models/base_model.py`
  - `src/evaluate.py`
  - `api/model_loader.py`
- Generated Datasets:
  - `data/processed_train.parquet` (246,008 rows x 342 columns)
  - `data/processed_test.parquet` (61,503 rows x 342 columns)

## Exclusive File Ownership
You have exclusive write ownership of:
- `src/models/xgboost_model.py` (Enhance with flexible kwargs, tree_method="hist", early stopping)
- `src/training/train_augmented_xgboost.py` (New dedicated training orchestrator script)
- `models/xgboost.joblib` (Augmented trained XGBoost model artifact)
- `models/xgboost.json` (Best hyperparameters)
- `reports/model_comparison.csv` (Leaderboard update with augmented model)
- `reports/business_metrics.csv` (Credit risk KPIs update)
- `reports/model_metrics.csv` (Detailed metric breakdown)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Acceptance Criteria
- Train a genuine XGBoost model on `data/processed_train.parquet` and evaluate on `data/processed_test.parquet`.
- The newly trained model MUST achieve an ROC-AUC score strictly greater than 0.7610 (baseline was 0.761038, expected 0.7750–0.7920) on the 61,503 held-out test applicants.
- Save the trained model to `models/xgboost.joblib`.
- Update `reports/model_comparison.csv` using `src/evaluate.py` / `EvaluationEngine`.
- Verify production serving compatibility: ensure `api/model_loader.py` can load the new model and pipeline artifacts and pass `loader.run_smoke_test()`.
- Document all execution outputs, ROC-AUC score, classification metrics, business metrics, and verification commands in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md`.

## 2026-10-05T15:42:05Z
You are Worker M2 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\DISPATCH.md.

Read the modeling specification:
- d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_3\handoff.md

Your exclusive write ownership:
- src/models/xgboost_model.py
- src/training/train_augmented_xgboost.py
- models/xgboost.joblib
- models/xgboost.json
- reports/model_comparison.csv
- reports/business_metrics.csv
- reports/model_metrics.csv

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Update src/models/xgboost_model.py to support flexible hyperparameters and tree_method="hist".
2. Implement src/training/train_augmented_xgboost.py to load data/processed_train.parquet and data/processed_test.parquet, train XGBoost with early stopping on validation split, evaluate on the 61,503 held-out test set using src/evaluate.py, and save models/xgboost.joblib and updated reports.
3. Verify that the new model achieves ROC-AUC strictly > 0.7610 (target 0.7750+).
4. Verify that api/model_loader.py loads the new model and pipeline and passes smoke test.
5. Write your complete handoff report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md and notify me via send_message when done.
