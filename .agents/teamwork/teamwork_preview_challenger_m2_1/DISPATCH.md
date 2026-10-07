# Task Assignment: Challenger M2-1 (Milestone 2 — Metric & Benchmark Adversarial Challenge)

## Context
You are Challenger M2-1 for Milestone 2 (Augmented Model Training & Benchmark Evaluation).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_1

## Mandatory Inputs to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md`
- Artifacts: `models/xgboost.joblib`, `data/processed_test.parquet`

## Instructions
1. Perform adversarial empirical verification of the model evaluation:
   - Independently recalculate ROC-AUC on `data/processed_test.parquet` using `sklearn.metrics.roc_auc_score` directly (avoiding any reliance on internal helper functions).
   - Verify that test applicant count is exactly 61,503.
   - Verify that the test split has zero overlap with the training set.
   - Check calibration and output probabilities: ensure all predicted probabilities lie in `[0.0, 1.0]`.
   - Test threshold stability: evaluate precision, recall, and confusion matrix across thresholds `[0.10, 0.20, 0.30, 0.50, 0.70]`.
2. Provide your verdict: `APPROVE` or `REQUEST_CHANGES` in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_1\handoff.md`.

## 2026-10-05T18:21:51Z
You are Challenger M2-1 for Milestone 2 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_1
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_1\DISPATCH.md.
Also read Worker M2's handoff: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md.

Task:
Adversarially recalculate ROC-AUC on data/processed_test.parquet using raw sklearn.metrics.roc_auc_score. Verify 61,503 held-out test applicants, zero split contamination, well-calibrated output probabilities in [0.0, 1.0], and threshold stability.
Report your verdict (APPROVE or REQUEST_CHANGES) in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_1\handoff.md and notify me via send_message when done.
