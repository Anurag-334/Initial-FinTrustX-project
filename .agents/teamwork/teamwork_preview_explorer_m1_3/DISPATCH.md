# Task Assignment: Explorer M1-3 (Milestone 1 — Pipeline Script & Memory Architecture)

## Context
You are Explorer M1-3 for Milestone 1 (Dataset Integration & Memory Management Pipeline).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_3

## Mandatory Inputs
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\notebooks\02_Preprocessing.ipynb`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md`

## Objectives
1. Provide the exact structure and implementation specification for `scripts/run_data_pipeline.py` (a standalone, reproducible script that executes the complete end-to-end data integration and preprocessing).
2. Specify exact memory tracking mechanism (e.g. tracking memory before/after with `gc.collect()`, logging memory usage at each stage).
3. Specify exact output artifact paths, schemas, and verification assertions:
   - `data/processed_train.parquet` (246,008 rows)
   - `data/processed_test.parquet` (61,503 rows)
   - `models/preprocessing_pipeline.joblib`
   - `models/preprocessed_feature_names.csv`
4. Provide the companion notebook cells / script execution guide to guarantee 100% reproducibility.
5. Write your findings and recommendations to `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_3\handoff.md` and send a completion message.


## 2026-10-05T14:57:30Z
You are Explorer M1-3 for Milestone 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_3
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your task in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_3\DISPATCH.md.

Task:
Design the standalone, reproducible CLI script scripts/run_data_pipeline.py and companion notebook updates. Detail memory tracking, sequential execution steps, garbage collection, output parquet schemas (data/processed_train.parquet, data/processed_test.parquet), fitted pipeline serialization (models/preprocessing_pipeline.joblib, models/preprocessed_feature_names.csv), and validation assertions.
Write your complete report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_3\handoff.md and notify me via send_message when done.
