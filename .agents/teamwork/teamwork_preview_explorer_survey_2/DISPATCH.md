# Task Assignment: Explorer 2 (Survey - Existing Pipeline & Integration Architecture)

## Context
You are Explorer 2 participating in the Survey phase of FinTrustX dataset integration.

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2

## Instructions & Objective
1. Read `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md` and `d:\Projects\Credit-risk-ai\project.md`.
2. Inspect the existing codebase architecture:
   - `src/data_loader.py`: inspect `DataLoader.load_csv()`, `optimize_memory()`.
   - `src/feature_engineering.py`: inspect `FeatureEngineer` class and 18 baseline domain features.
   - `src/preprocessing.py`: inspect `DataPreprocessor` class, handling of numeric/categorical columns, imputer/scaler/OHE pipeline.
   - `notebooks/02_Preprocessing.ipynb`: inspect how processed parquet is generated and stored.
3. Propose the integration pattern:
   - How and where to aggregate `bureau.csv` and `previous_application.csv` (e.g. modular function/class in `src/` or dedicated integration script, callable by both scripts and notebooks).
   - How the merged dataset feeds into the preprocessing pipeline without breaking existing schemas or exceeding memory limits.
   - How the script or pipeline should be reproducible and adhere to `PROJECT_RULES.md` (PEP8, type hints, docstrings, error handling, logging).
4. Write your comprehensive analysis and recommendations to `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md`.

## 2026-10-05T14:44:24Z
From: 0f3523ae-4a10-43ee-a538-7863c0c9f470
You are Explorer 2 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\project.md, and your task in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2\DISPATCH.md.

Focus: Existing pipeline & integration architecture.
1. Inspect existing codebase: src/data_loader.py, src/feature_engineering.py, src/preprocessing.py, notebooks/02_Preprocessing.ipynb.
2. Determine how features are engineered, preprocessed, saved, and loaded.
3. Propose the architectural placement of the new aggregation module and reproducible script/pipeline, ensuring compatibility with DataLoader, FeatureEngineer, and DataPreprocessor.
4. Ensure compliance with PROJECT_RULES.md (PEP8, logging, typing, docstrings).
5. Write your comprehensive report to d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md and notify me via send_message when done.
