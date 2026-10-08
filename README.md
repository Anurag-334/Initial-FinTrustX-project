# FinTrustX: Explainable AI Platform for Secure Credit Risk Assessment and Loan Decision Intelligence

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Framework: Scikit-Learn | TensorFlow | XGBoost | FastAPI](https://img.shields.io/badge/Frameworks-Scikit--Learn%20%7C%20TensorFlow%20%7C%20XGBoost%20%7C%20FastAPI-orange.svg)](#technology-stack)
[![Explainability: SHAP | LIME | DiCE](https://img.shields.io/badge/Explainability-SHAP%20%7C%20LIME%20%7C%20DiCE-purple.svg)](#explainable-ai-framework)

---

## 📌 Executive Overview

**FinTrustX** is an enterprise-grade, end-to-end Explainable AI (XAI) platform designed for credit risk assessment, loan default probability modeling, and automated underwriting intelligence. Leveraging the **Home Credit Default Risk** benchmark datasets, FinTrustX unifies traditional tree ensembles, gradient boosting algorithms, and deep neural architectures into a standardized evaluation and decision-support pipeline.

Credit underwriting in production demands both **high predictive discrimination** on imbalanced data and **strict regulatory compliance** (FCRA, ECOA, GDPR). FinTrustX bridges the gap between black-box accuracy and auditable lending decisions through localized and global explainability engines, culminating in a fully deployable REST API and interactive dashboard.

---

## 🎯 Problem Statement & Lending Realities

In consumer credit lending:
1. **Severe Class Imbalance**: Non-defaulting loan applicants outnumber defaults by over **11:1** (~8.1% default rate). Standard metrics like raw Accuracy provide false security and hide catastrophic default losses.
2. **Asymmetric Risk Costs**: The cost of a False Negative (approving a borrower who defaults on principal) is significantly higher than a False Positive (denying a creditworthy applicant).
3. **Regulatory Auditability**: Lending algorithms cannot operate as opaque black boxes; every adverse credit decision mandates transparent reason codes and counterfactual guidance.

---

## 🚀 Key Features

- **Robust Preprocessing & Feature Engineering**: Handles missing values, target encoding, outlier management, and memory-safe aggregation across **341 engineered features** sourced from multiple datasets (`application_train`, `bureau`, `previous_application`).
- **Comprehensive 6-Model Benchmark Suite**: Evaluates Decision Tree, Random Forest, XGBoost, CatBoost, Logistic Regression, and Deep Neural Networks under identical held-out test conditions.
- **Champion Model Deployment**: Deploys an **Augmented XGBoost** model (ROC-AUC: 0.7794) optimized for both precision-recall tradeoffs and latency.
- **Production-Ready Architecture**: Includes a **FastAPI** serving interface, a real-time **SQLite Feature Store** for offline-to-online historical lookups, and a Vanilla HTML/JS **Frontend Dashboard**.
- **Multi-Faceted Explainable AI (XAI)**:
  - **SHAP**: Global feature importance, summary beeswarm plots, and local waterfall explanations for API endpoints.
  - **LIME**: Local perturbation-based linear approximations.
  - **DiCE**: Diverse counterfactual explanations for actionable "what-if" applicant guidance.
- **Dynamic Decision Threshold Sweep**: Simulates operational cut-offs to optimize default capture versus loan rejection volume.

---

## 🧠 Architecture Overview

```text
 ┌────────────────────────────────────────────────────────────────────┐
 │  Raw Data: application_train.csv, bureau.csv, prev_application.csv │
 └────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  Data Pipeline & Preprocessing (scripts/ & src/)                   │
 │  • Aggregations, Left Joins, Memory Optimization                   │
 │  • Imputation, Scaling, One-Hot Encoding (341 features)            │
 └─────────┬──────────────────────────────────────────────┬───────────┘
           │                                              │
           ▼                                              ▼
 ┌────────────────────────────────────┐  ┌────────────────────────────┐
 │  Model Training & Tuning           │  │  Feature Store (SQLite)    │
 │  • Optuna Hyperparameter Search    │  │  Offline-to-Online Storage │
 │  • ML Models & Deep Learning (MLP) │  │  for real-time API lookups │
 └─────────┬──────────────────────────┘  └────────────┬───────────────┘
           │                                          │
           ▼                                          │
 ┌────────────────────────────────────┐               │
 │  Evaluation & XAI                  │               │
 │  • ROC-AUC, PR-AUC, Business KPIs  │               │
 │  • SHAP, LIME, Integrated Grads    │               │
 └─────────┬──────────────────────────┘               │
           │                                          │
           ▼                                          ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  FastAPI Serving Layer (api/main.py)                               │
 │  • Singleton Artifact Loader (XGBoost + Pipeline)                  │
 │  • /predict, /predict/batch, /explain endpoints                    │
 └────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  Frontend Dashboard (frontend/)                                    │
 │  • Interactive Credit Risk Assessment & Approvals                  │
 └────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Benchmark Evaluation Results

Evaluated on **61,503 held-out test applicants** (341 features, ~4,965 actual defaults):

### Classification Metrics (Sorted by ROC AUC)
| Model | ROC AUC | PR-AUC | F1 | Recall | Precision | Balanced Acc | MCC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Augmented XGBoost (API Champion)** | **0.7794** | **0.2751** | — | — | — | — | — |
| **CatBoost** | 0.7716 | 0.2784 | 0.3705 | 0.6410 | 0.2604 | 0.7189 | — |
| **XGBoost (Baseline)** | 0.7712 | 0.2796 | 0.3744 | 0.6466 | 0.2636 | 0.7209 | — |
| **Neural Network** | 0.7610 | 0.2603 | 0.3552 | 0.6418 | 0.2458 | 0.7077 | — |
| **Random Forest** | 0.7382 | 0.2139 | 0.2786 | 0.3186 | 0.2475 | 0.6168 | 0.2085 |
| **Decision Tree** | 0.6282 | 0.1211 | 0.1901 | 0.6828 | 0.1104 | 0.5999 | 0.1088 |

### Credit Risk Business Metrics (Threshold = 0.50)
| Model | Defaults Captured | False Flagged | Cleared Good | Missed | Capture Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Decision Tree** | 3,390 | 27,309 | 29,229 | 1,575 | 68.28% |
| **XGBoost** | 3,325 | 16,124 | 40,414 | 1,640 | 66.97% |
| **CatBoost** | 3,183 | 9,047 | 47,491 | 1,783 | 64.10% |
| **Neural Network** | 3,187 | 9,789 | 46,749 | 1,779 | 64.18% |
| **Random Forest** | 1,582 | 4,809 | 51,729 | 3,383 | 31.86% |

*(Note: XGBoost was chosen as the API Champion over CatBoost due to operational deployment simplicity and favorable Precision-Recall tradeoffs in API evaluation.)*

---

## 🛠️ Technology Stack

- **Core**: Python 3.11+, NumPy, Pandas, SciPy, PyArrow
- **Machine Learning**: Scikit-Learn, Imbalanced-Learn, XGBoost, CatBoost
- **Deep Learning**: TensorFlow 2.x / Keras
- **Hyperparameter Optimization**: Optuna (SQLite backed)
- **Explainable AI (XAI)**: SHAP, LIME, DiCE-ML
- **API & Serving**: FastAPI, Uvicorn, Pydantic, SQLite (Feature Store)
- **Frontend**: Vanilla HTML/CSS/JS

---

## 📁 Repository Structure

```
Credit-risk-ai/
├── api/                          # FastAPI REST API layer
├── data/                         # Raw data, processed parquets, & SQLite Feature Store
├── frontend/                     # Vanilla HTML/CSS/JS dashboard UI
├── models/                       # Serialized models (.joblib, .keras) & preprocessors
├── notebooks/                    # Sequential EDA, Training, and XAI pipelines
├── reports/                      # Evaluation benchmarks & metrics CSVs
├── scripts/                      # Data aggregation and DB seeding scripts
├── src/                          # Core ML Python package (config, loaders, engineering)
├── studies/                      # SQLite-backed Optuna hyperparameter studies
├── requirements.txt              # Production dependency specifications
└── project.md                    # Detailed architecture and source of truth
```

---

## 💻 Installation & Local Execution

### 1. Clone & Environment Setup
```bash
git clone https://github.com/AnuragKashyap-dev/Credit-risk-ai.git
cd Credit-risk-ai

# Create virtual environment (Python 3.11+)
python -m venv venv
# Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install -r api/requirements.txt
```

### 2. Dataset Setup
Download `application_train.csv`, `bureau.csv`, and `previous_application.csv` from [Kaggle Home Credit Default Risk](https://www.kaggle.com/c/home-credit-default-risk/data) and place them in `data/raw/`.

### 3. Pipeline Execution
Run the end-to-end pipeline via notebooks sequentially (`01_EDA.ipynb` -> `06_Model_Comparison.ipynb`), or use the data scripts:
```bash
python scripts/run_data_pipeline.py
python scripts/seed_feature_store.py
```

### 4. Running the API & Frontend
**Start the FastAPI Server:**
```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`

**Serve the Frontend:**
You can open `frontend/index.html` directly in your browser, or run a simple server:
```bash
cd frontend
python -m http.server 3000
```
- Dashboard: `http://127.0.0.1:3000`

---

## 🛡️ Governance & Production Limitations

1. **Probability Calibration**: Validating Brier score and Platt scaling for accurate Loss Given Default (LGD) calculations is required before full production.
2. **Fairness & Demographic Parity**: Verification of disparate impact across protected demographic categories.
3. **Model Monitoring**: Tracking Population Stability Index (PSI) and feature drift in real-time.
4. **Human-in-the-Loop**: Model explanations (SHAP / LIME) describe correlational associations; they must be paired with human credit officer review before final loan denial to ensure FCRA compliance.

---

## 👤 Author & Contact

**Anurag Kashyap**  
FinTrustX Platform Architect & Machine Learning Engineer  
- **GitHub**: [@Anurag334](https://github.com/Anurag334)