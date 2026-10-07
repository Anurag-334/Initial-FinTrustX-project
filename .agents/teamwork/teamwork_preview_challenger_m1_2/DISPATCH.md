# Task Assignment: Challenger M1-2 (Milestone 1 — Data Leakage & Integrity Verification)

## Context
You are Challenger M1-2 for Milestone 1 (Dataset Integration & Memory Management Pipeline).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_2

## Mandatory Inputs to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m1\handoff.md`
- Artifacts: `data/processed_train.parquet`, `data/processed_test.parquet`, `models/preprocessed_feature_names.csv`, `models/preprocessing_pipeline.joblib`

## Instructions
1. Perform empirical verification of dataset integrity and leakage elimination:
   - Verify that `SK_ID_CURR` is strictly NOT in `models/preprocessed_feature_names.csv` or feature matrices.
   - Verify that train and test partitions have zero disjoint index overlap (`len(set(train.index) & set(test.index)) == 0`).
   - Verify that target default rate on train is 8.0729% (19,860/246,008) and on test is 8.0728% (4,965/61,503).
   - Verify that zero NaN or infinite values exist in preprocessed feature columns.

## 2026-10-05T15:25:29Z
You are Challenger M1-2 for Milestone 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_2
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_2\DISPATCH.md.
Also read Worker M1's handoff: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m1\handoff.md.

Task:
Empirically verify data integrity, non-leakage, and disjoint index splitting between train and test partitions. Verify applicant ID SK_ID_CURR exclusion from feature matrices, absence of NaNs in processed parquets, and exact default rates.
Report your verdict (APPROVE or REQUEST_CHANGES) in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_2\handoff.md and notify me via send_message when done.
