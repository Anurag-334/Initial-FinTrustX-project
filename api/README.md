# FinTrustX Credit Risk API Service

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost%20Champion-FF6600.svg)](https://xgboost.readthedocs.io)
[![Explainability](https://img.shields.io/badge/XAI-SHAP%20TreeExplainer-purple.svg)](https://shap.readthedocs.io)

**FinTrustX API** is a production-grade, CPU-optimized REST API built with **FastAPI** for real-time credit default risk scoring, automated loan decision recommendations, and explainable AI (SHAP) adverse action attribution.

---

## 🏗️ Architecture & Inference Pipeline

```
   Raw Applicant JSON
          │
          ▼
   Pydantic Schema Validation (api/schemas.py)
          │
          ▼
   Preprocessing (ColumnTransformer from models/preprocessing_pipeline.joblib)
   • 121 Raw Features → 245 Imputed & Scaled Features
          │
          ▼
   XGBoost Model Scoring (models/xgboost.joblib)
          │
   ┌──────┴──────────────────────────┐
   ▼                                 ▼
Default Probability P(TARGET=1)    SHAP TreeExplainer (Optional)
   │                                 │
   ├─► Risk Score (0 - 100)          └─► Top Risk Factors (Positive SHAP)
   ├─► Risk Category (Low/Mod/High)  └─► Protective Factors (Negative SHAP)
   └─► Loan Recommendation
          │
          ▼
   JSON Response (api/schemas.py)
```

---

## 📁 Folder Structure

```
api/
├── __init__.py               # API package initialization
├── main.py                   # FastAPI app entrypoint, lifespan, CORS, and routes
├── config.py                 # Central configuration, paths, and risk thresholds
├── schemas.py                # Pydantic v2 request & response schemas
├── dependencies.py           # Dependency injection providers
├── model_loader.py           # Singleton model loader and startup smoke tester
├── predictor.py              # Core XGBoost inference orchestrator
├── preprocessing.py          # ColumnTransformer feature alignment engine
├── explainability.py         # SHAP TreeExplainer attribution generator
├── utils.py                  # Risk categorization and recommendation rules
├── requirements.txt          # API-specific Python dependencies
├── README.md                 # Complete API documentation
├── .env.example              # Environment variables template
│
├── services/
│   ├── __init__.py
│   ├── model_service.py      # Health and model metadata service
│   ├── prediction_service.py # Single and batch prediction business logic
│   └── explanation_service.py# SHAP adverse action explanation service
│
└── tests/
    ├── __init__.py
    ├── test_health.py        # Tests for root, /health, /model-info
    ├── test_model_loading.py # Tests for singleton loader and artifacts
    └── test_prediction.py    # Tests for /predict, /explain, /predict/batch
```

---

## 🚀 Quick Start & Local Execution

### 1. Install Dependencies

From the repository root (`Credit-risk-ai/`):

```bash
pip install -r api/requirements.txt
```

### 2. Start the API Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Interactive Documentation

Once the server starts, open your browser:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📌 API Endpoints Overview

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Service information and route navigation | None |
| `GET` | `/health` | API & ML model readiness health check | None |
| `GET` | `/model-info` | Deployed model parameters and benchmark metrics | None |
| `POST` | `/predict` | Single applicant credit risk scoring | `explain` (bool), `threshold` (float) |
| `POST` | `/explain` | Localized SHAP feature attribution | None |
| `POST` | `/predict/batch` | Batch credit risk scoring (up to 500 applicants) | `threshold` (float) |

---

## 💡 Example Usage

### 1. Single Prediction (`POST /predict`)

**Request**: `POST http://localhost:8000/predict?explain=true`

```json
{
  "SK_ID_CURR": 100002,
  "NAME_CONTRACT_TYPE": "Cash loans",
  "CODE_GENDER": "M",
  "FLAG_OWN_CAR": "N",
  "FLAG_OWN_REALTY": "Y",
  "CNT_CHILDREN": 0,
  "AMT_INCOME_TOTAL": 202500.0,
  "AMT_CREDIT": 406597.5,
  "AMT_ANNUITY": 24700.5,
  "AMT_GOODS_PRICE": 351000.0,
  "NAME_INCOME_TYPE": "Working",
  "NAME_EDUCATION_TYPE": "Secondary / secondary special",
  "NAME_FAMILY_STATUS": "Single / not married",
  "NAME_HOUSING_TYPE": "House / apartment",
  "DAYS_BIRTH": -9461.0,
  "DAYS_EMPLOYED": -637.0,
  "EXT_SOURCE_1": 0.0830,
  "EXT_SOURCE_2": 0.2629,
  "EXT_SOURCE_3": 0.1393
}
```

**Response (`200 OK`)**:
```json
{
  "prediction": 1,
  "default_probability": 0.6784,
  "risk_score": 67.84,
  "risk_category": "Very High Risk",
  "loan_decision": "Likely Rejected",
  "model": "XGBoost",
  "threshold_used": 0.5,
  "applicant_id": 100002,
  "explanation": {
    "top_risk_factors": [
      {
        "feature": "num__DAYS_BIRTH",
        "impact": "increases risk",
        "contribution": 0.1824
      },
      {
        "feature": "num__DAYS_EMPLOYED",
        "impact": "increases risk",
        "contribution": 0.0945
      }
    ],
    "protective_factors": [
      {
        "feature": "num__EXT_SOURCE_2",
        "impact": "reduces risk",
        "contribution": -0.4215
      },
      {
        "feature": "num__AMT_GOODS_PRICE",
        "impact": "reduces risk",
        "contribution": -0.0612
      }
    ],
    "base_value": -2.4831
  }
}
```

---

### 2. Batch Prediction (`POST /predict/batch`)

**Request**: `POST http://localhost:8000/predict/batch`

```json
{
  "requests": [
    {
      "SK_ID_CURR": 100002,
      "AMT_INCOME_TOTAL": 202500.0,
      "AMT_CREDIT": 406597.5,
      "EXT_SOURCE_1": 0.083,
      "EXT_SOURCE_2": 0.262,
      "EXT_SOURCE_3": 0.139
    },
    {
      "SK_ID_CURR": 100003,
      "AMT_INCOME_TOTAL": 270000.0,
      "AMT_CREDIT": 1293502.5,
      "EXT_SOURCE_1": 0.75,
      "EXT_SOURCE_2": 0.82,
      "EXT_SOURCE_3": 0.89
    }
  ]
}
```

**Response (`200 OK`)**:
```json
{
  "predictions": [
    {
      "prediction": 1,
      "default_probability": 0.6784,
      "risk_score": 67.84,
      "risk_category": "Very High Risk",
      "loan_decision": "Likely Rejected",
      "model": "XGBoost",
      "threshold_used": 0.5,
      "applicant_id": 100002,
      "explanation": null
    },
    {
      "prediction": 0,
      "default_probability": 0.1245,
      "risk_score": 12.45,
      "risk_category": "Low Risk",
      "loan_decision": "Likely Approved",
      "model": "XGBoost",
      "threshold_used": 0.5,
      "applicant_id": 100003,
      "explanation": null
    }
  ],
  "total_processed": 2,
  "model": "XGBoost"
}
```

---

## ⚙️ Risk Categories & Decision Rules

Risk categorization is configured in `api/config.py`:

| Default Probability Range | Risk Category | Application Decision Recommendation |
| :--- | :--- | :--- |
| $P < 0.20$ | **Low Risk** | `Likely Approved` |
| $0.20 \le P < 0.40$ | **Moderate Risk** | `Manual Review` |
| $0.40 \le P < 0.60$ | **High Risk** | `Higher Risk / Manual Review` |
| $P \ge 0.60$ | **Very High Risk** | `Likely Rejected` |

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:

```bash
pytest api/tests/ -v
```

---

## 🛡️ Governance & Regulatory Disclaimer

> **IMPORTANT**: The recommendations generated by this API (`Likely Approved`, `Manual Review`, `Likely Rejected`) are **demonstration decision aids** developed for research and educational purposes. In a commercial lending environment, automated credit underwriting must be accompanied by rigorous model risk governance (SR 11-7), fair lending compliance audits (ECOA / Regulation B), adverse action notices (FCRA), population stability monitoring (PSI), and certified human underwriter review.
