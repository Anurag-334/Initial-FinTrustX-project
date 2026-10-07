# Task Assignment: Explorer 1 (Survey - Datasets & Aggregation Architecture)

## Context
You are Explorer 1 participating in the Survey phase of FinTrustX dataset integration.

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1

## Instructions & Objective
1. Read `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md` and `d:\Projects\Credit-risk-ai\project.md`.
2. Inspect the raw datasets in `d:\Projects\Credit-risk-ai\data\` (and `data/raw/` or wherever CSVs are stored):
   - Check existence, paths, sizes, row counts, and schema of `bureau.csv`, `previous_application.csv`, and `application_train.csv`.
   - Analyze `SK_ID_CURR` linking key and relationship cardinality.
3. Formulate specific feature engineering & aggregation strategies for `bureau.csv` and `previous_application.csv`:
   - Numeric aggregations (mean, max, min, sum, count, std).
   - Categorical aggregations (value counts, modes, proportions).
   - High-value credit domain features (e.g. active credit counts, overdue amounts, previous loan refusal rates, credit debt ratios).
4. Address memory management (R2):
   - Memory profiling of raw CSVs.
   - Downcasting strategies (float64 -> float32, int64 -> int32/int16/int8, category types).
   - Chunked processing or efficient groupby aggregation without OOM.
5. Write your comprehensive analysis and recommendations to `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md`.

## 2026-10-05T14:44:24Z
From: 0f3523ae-4a10-43ee-a538-7863c0c9f470
Message: You are Explorer 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\project.md, and your task in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1\DISPATCH.md.

Focus: Raw datasets and aggregation architecture.
1. Inspect the location, structure, columns, row counts, sizes of bureau.csv, previous_application.csv, and application_train.csv.
2. Analyze SK_ID_CURR linking key and relationship cardinality.
3. Propose specific feature engineering & aggregation strategies for bureau and previous_application (numeric & categorical aggregations, domain-specific debt/refusal ratios).
4. Propose memory management strategy (downcasting, chunking, garbage collection) to satisfy R2.
5. Write your comprehensive report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md and notify me via send_message when done.
