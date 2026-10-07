# Task Assignment: Challenger M1-1 (Milestone 1 — Adversarial Stress Testing)

## Context
You are Challenger M1-1 for Milestone 1 (Dataset Integration & Memory Management Pipeline).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_1

## Mandatory Inputs to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m1\handoff.md`
- Code: `src/data_aggregation.py`, `scripts/run_data_pipeline.py`

## Instructions
1. Stress-test `DataAggregator` with edge cases and adversarial scenarios:
   - Behavior with empty inputs or subsets.
   - Missing values in child records.
   - Unlinked applicants (no bureau or previous app data) to ensure NaN handling and flags work correctly.
   - Out-of-bounds or zero-division cases in derived ratios (debt-to-credit, refusal rate, DTI).
2. Empirically verify that `scripts/run_data_pipeline.py` runs cleanly without memory errors.
3. State your verdict clearly: `APPROVE` or `REQUEST_CHANGES` in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_1\handoff.md`.


## 2026-10-05T15:25:28Z
You are Challenger M1-1 for Milestone 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_1
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_1\DISPATCH.md.
Also read Worker M1's handoff: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m1\handoff.md.

Task:
Adversarially stress-test DataAggregator and scripts/run_data_pipeline.py with boundary cases, unlinked applicants, zero-divisions, and missingness flags. Verify zero crashes and robust handling.
Report your verdict (APPROVE or REQUEST_CHANGES) in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_challenger_m1_1\handoff.md and notify me via send_message when done.
