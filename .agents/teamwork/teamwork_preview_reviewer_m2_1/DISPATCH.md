# Task Assignment: Reviewer M2-1 (Milestone 2 — Model Code & Benchmark Review)

## Context
You are Reviewer M2-1 for Milestone 2 (Augmented Model Training & Benchmark Evaluation).

## Working Directory
d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1

## Mandatory Inputs to Read
- `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md`
- `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md`
- Code: `src/models/xgboost_model.py`, `src/training/train_augmented_xgboost.py`, `src/evaluate.py`

## Instructions
1. Independently review the model code for correctness, completeness, robustness, and adherence to `PROJECT_RULES.md`.
2. Verify the two-stage training logic, stratified validation early stopping, tree scaling, and evaluation protocol.
3. Run independent evaluation verification:
   ```bash
   python -c "import joblib, pandas as pd; from src.evaluate import EvaluationEngine; model = joblib.load('models/xgboost.joblib'); test_df = pd.read_parquet('data/processed_test.parquet'); X_test = test_df.drop(columns=['TARGET']); y_test = test_df['TARGET'].astype(int); engine = EvaluationEngine(model=model, threshold=0.50); metrics = engine.evaluate(X_test, y_test); print('ROC-AUC:', metrics['ROC AUC']); assert metrics['ROC AUC'] > 0.761038"
   ```
4. Verify that the ROC-AUC score strictly exceeds 0.7610.
5. Provide your verdict: `APPROVE` or `REQUEST_CHANGES` in `d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1\handoff.md`.


## 2026-10-05T18:21:51Z
You are Reviewer M2-1 for Milestone 2 on the FinTrustX project.
Your working directory is: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1
Read d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md, d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_1\PROJECT.md, and your instructions in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1\DISPATCH.md.
Also read Worker M2's handoff: d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_worker_m2\handoff.md.

Task:
Independently review src/models/xgboost_model.py, src/training/train_augmented_xgboost.py, and src/evaluate.py. Run verification commands to confirm that models/xgboost.joblib achieves ROC-AUC strictly > 0.7610 on data/processed_test.parquet (61,503 rows).
Report your verdict (APPROVE or REQUEST_CHANGES) in d:\Projects\Credit-risk-ai\.agents\teamwork\teamwork_preview_reviewer_m2_1\handoff.md and notify me via send_message when done.
