# Task Assignment: Challenger M2-2 (Milestone 2 — Inference Stress Testing & Latency SLA)

## Context
You are Challenger M2-2 for Milestone 2 (Augmented Model Training & Benchmark Evaluation).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_2

## Mandatory Inputs to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md`
- Artifacts: `models/xgboost.joblib`, `models/preprocessing_pipeline.joblib`

## Instructions
1. Perform inference stress testing on `models/xgboost.joblib`:
   - Test extreme synthetic vectors (all-zeros, all-medians, extreme positive/negative values).
   - Test latency SLA: measure batch inference throughput on 10,000 rows (verify latency < 0.1 ms/sample).
   - Test edge-case inputs through the full pipeline: raw payload -> preprocessing transformer -> XGBoost model.
   - Run the existing test suites (`tests/test_adversarial_m1.py`, `tests/test_data_integrity_challenger.py`).
2. Provide your verdict: `APPROVE` or `REQUEST_CHANGES` in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_2\handoff.md`.


## 2026-10-05T18:21:52Z
You are Challenger M2-2 for Milestone 2 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_2
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_2\DISPATCH.md.
Also read Worker M2's handoff: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md.

Task:
Perform inference stress testing on models/xgboost.joblib with extreme vectors, batch inference latency SLA (<0.1 ms/row), and run test suites (tests/test_adversarial_m1.py, tests/test_data_integrity_challenger.py).
Report your verdict (APPROVE or REQUEST_CHANGES) in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m2_2\handoff.md and notify me via send_message when done.
