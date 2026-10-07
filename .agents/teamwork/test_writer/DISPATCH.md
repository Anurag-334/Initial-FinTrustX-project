## 2026-10-05T19:21:29Z
You are the E2E Test Writer for the Credit Risk Feature Store and API integration.
Working directory: d:\Projects\Credit-risk-ai\.agents\teamwork\test_writer
Project Root: d:\Projects\Credit-risk-ai

You MUST read the following files before writing tests:
1. `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Projects\Credit-risk-ai\project.md`
3. `d:\Projects\Credit-risk-ai\GEMINI.md`
4. `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_2\PROJECT.md`
5. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_3\report.md`
6. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_3\handoff.md`

File Ownership:
You have exclusive write ownership over:
- `api/tests/test_prediction.py` (for adding the new integration tests)
- Optionally `api/tests/conftest.py` if needed for shared fixtures
- `TEST_READY.md` at project root (`d:\Projects\Credit-risk-ai\TEST_READY.md`)

Tasks:
1. Review the existing tests in `api/tests/test_prediction.py`.
2. Implement comprehensive integration tests in `api/tests/test_prediction.py` per the specifications in `explorer_survey_3/report.md`:
   - `test_predict_with_valid_sk_id_curr_pulls_db_features`: Sends a request with a valid `SK_ID_CURR` (e.g. 100002 or test fixture), verifies HTTP 200, valid prediction probability, risk score, and that `applicant_id` matches. Provide a self-contained SQLite fixture or handle pre-seeded/test db so the test is robust.
   - `test_predict_without_sk_id_curr_backward_compatible`: Sends a request without `SK_ID_CURR` (or with `None`), verifies HTTP 200, backward compatibility, and `applicant_id: None`.
   - `test_predict_with_unknown_sk_id_curr_fallback`: Sends a non-existent `SK_ID_CURR` (e.g. 999999999), verifies graceful fallback without 500 error.
   - `test_zero_pandas_fragmentation_warning`: Wraps single and batch prediction requests in `with warnings.catch_warnings(record=True) as recorded_warnings: ...` and asserts that NO warning matches `pandas.errors.PerformanceWarning` or contains "DataFrame is highly fragmented".
3. Run `pytest api/tests/test_prediction.py` to document the initial baseline. (Note: database-dependent tests may be RED until Worker M1/M2 complete; verify that existing tests still pass and new tests are syntactically and structurally sound).
4. Create `TEST_READY.md` at project root (`d:\Projects\Credit-risk-ai\TEST_READY.md`) following the template in Project Pattern instructions.
5. Write your handoff report to `d:\Projects\Credit-risk-ai\.agents\teamwork\test_writer\handoff.md`.
When finished, send a brief message with your handoff path.
