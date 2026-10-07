# Task Assignment: Explorer M1-1 (Milestone 1 — Data Aggregation Implementation Spec)

## Context
You are Explorer M1-1 for Milestone 1 (Dataset Integration & Memory Management Pipeline).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_1

## Mandatory Inputs
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- Previous survey reports:
  - `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md`
  - `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md`

## Objectives
1. Provide the exact, production-ready class and method specifications for `src/data_aggregation.py` (`DataAggregator`).
2. Specify exact column lists for `usecols`, aggregation dictionaries for `bureau.csv` and `previous_application.csv`, and derived credit ratios.
3. Detail how `merge_features` safely left-joins the aggregated frames with `application_train.csv` (preserving all 307,511 rows and target distributions).
4. Specify downcasting and memory management logic to guarantee peak RAM stays below 1.5 GB.
5. Write your findings and recommendations to `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_1\handoff.md` and send a completion message.


## 2026-10-05T14:57:30Z
Sender: 0f3523ae-4a10-43ee-a538-7863c0c9f470
Content:
You are Explorer M1-1 for Milestone 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_1
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your task in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_1\DISPATCH.md.

Task:
Formulate the exact class, function, and aggregation specifications for src/data_aggregation.py (DataAggregator), including column lists for selective reading (usecols), aggregation dictionaries for bureau.csv and previous_application.csv, derived credit ratios, downcasting logic, and safe left-merge on SK_ID_CURR preserving all 307,511 rows.
Write your complete report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_m1_1\handoff.md and notify me via send_message when done.
