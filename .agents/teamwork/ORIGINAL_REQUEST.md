# Original User Request

## Initial Request — 2026-10-05T14:40:53Z

Integrate supplementary datasets (`bureau.csv` and `previous_application.csv`) into the Home Credit Default Risk training pipeline to increase the ROC-AUC accuracy of the model.

Working directory: d:\Projects\Credit-risk-ai
Integrity mode: development

## Requirements

### R1. Dataset Integration
Aggregate the `bureau.csv` and `previous_application.csv` datasets per applicant (`SK_ID_CURR`) and merge the aggregated features with the main training dataset (`application_train.csv`).

### R2. Memory Management
Ensure the data aggregation and merging pipeline executes successfully without Out-Of-Memory (OOM) errors.

### R3. Model Training
Train a new XGBoost model on the augmented dataset and evaluate its performance against the current champion model.

## Acceptance Criteria

### Implementation
- [ ] A reproducible script or notebook exists that performs the aggregation and merging of the new datasets.
- [ ] The data integration pipeline runs to completion without crashing or running out of memory.

### Performance
- [ ] The newly trained XGBoost model achieves an ROC-AUC score strictly greater than 0.7610 on the held-out test set.

## Follow-up — 2026-10-05T19:07:57Z

Implement an offline-to-online Feature Store using SQLite to supply historical applicant data to the real-time API. Update the FastAPI prediction endpoint to query the database using the applicant's ID, merge the features with the incoming payload, and update the frontend UI to include an Applicant ID input field.

Working directory: d:\Projects\Credit-risk-ai
Integrity mode: development

## Requirements

### R1. Feature Store Creation
Create an SQLite feature store database populated with the aggregated historical features for each applicant, utilizing `SK_ID_CURR` as the primary key.

### R2. Backend Integration
Update the FastAPI prediction logic so that if an `SK_ID_CURR` is provided in the request, the API queries the SQLite feature store, merges the historical features with the incoming payload, and feeds the complete profile into the model.

### R3. Preprocessing Optimization
Refactor the missing-feature imputation logic in the API (`api/preprocessing.py`) to use `pd.concat()` instead of iterative column insertion to eliminate the Pandas fragmentation warning.

### R4. Frontend Update
Update the frontend HTML/JS to provide an input field for the Applicant ID, ensuring this ID is sent in the prediction payload to trigger the backend database lookup.

## Acceptance Criteria

### Implementation
- [ ] An automated script is provided to seed the SQLite database with the historical features.
- [ ] The frontend UI visually includes the new Applicant ID field and submits it correctly.

### Verification
- [ ] A new integration test in `api/tests/test_prediction.py` passes, proving that providing a valid `SK_ID_CURR` successfully pulls historical data from the database and returns a prediction.
- [ ] The API terminal logs show zero Pandas fragmentation warnings during a prediction request.
