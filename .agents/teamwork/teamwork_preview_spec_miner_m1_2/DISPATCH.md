# Task Assignment: Spec Miner M1-2 (Milestone 1 — Specification Mining & Interface Integrity)

## Context
You are Spec Miner M1-2 for Milestone 1 (Dataset Integration & Memory Management Pipeline).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_spec_miner_m1_2

## Mandatory Inputs
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\PROJECT_RULES.md`
- `d:\Projects\Credit-risk-ai\project.md`
- `d:\Projects\Credit-risk-ai\src\data_loader.py`
- `d:\Projects\Credit-risk-ai\src\preprocessing.py`

## Objectives
1. Mine exact requirements, coding standards, and architectural conventions from `PROJECT_RULES.md` and `project.md` that the worker implementing Milestone 1 must strictly follow (type hints, PEP8 88-char limit, logging, docstrings, no bare except, error handling).
2. Inspect `src/data_loader.py`: specify the exact modification needed for `load_csv()` so it accepts optional `usecols` and `dtype` without breaking existing callers.
3. Inspect `src/preprocessing.py`: verify `DataPreprocessor.detect_features()` behavior with `TARGET` and ensure `SK_ID_CURR` exclusion so that applicant ID is never leaked as a model feature.
4. Document all interface contracts and validation rules in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_spec_miner_m1_2\handoff.md` and send a completion message.

## 2026-10-05T14:57:30Z
You are Spec Miner M1-2 for Milestone 1 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_spec_miner_m1_2
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your task in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_spec_miner_m1_2\DISPATCH.md.

Task:
Mine exact interface constraints and coding standards from PROJECT_RULES.md, project.md, src/data_loader.py, and src/preprocessing.py that the worker implementing Milestone 1 must follow. Specifically specify how load_csv() in src/data_loader.py must be modified to support usecols/dtype while maintaining backward compatibility, and how DataPreprocessor.detect_features() must handle TARGET and exclude SK_ID_CURR.
Write your complete report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_spec_miner_m1_2\handoff.md and notify me via send_message when done.
