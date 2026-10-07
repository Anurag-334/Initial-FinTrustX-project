# FinTrustX: Explainable AI Platform for Secure Credit Risk Assessment and Loan Decision Intelligence

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Framework: Scikit-Learn | TensorFlow | XGBoost | CatBoost](https://img.shields.io/badge/Frameworks-Scikit--Learn%20%7C%20TensorFlow%20%7C%20XGBoost%20%7C%20CatBoost-orange.svg)](#technology-stack)
[![Explainability: SHAP | LIME | DiCE](https://img.shields.io/badge/Explainability-SHAP%20%7C%20LIME%20%7C%20DiCE-purple.svg)](#explainable-ai-framework)

---

## 📌 Executive Overview

**FinTrustX** is an enterprise-grade, end-to-end Explainable AI (XAI) platform designed for credit risk assessment, loan default probability modeling, and automated underwriting intelligence. Leveraging the **Home Credit Default Risk** benchmark dataset, FinTrustX unifies traditional tree ensembles, gradient boosting algorithms, and deep neural architectures into a standardized evaluation and decision-support pipeline.

Credit underwriting in production demands both **high predictive discrimination** on imbalanced data and **strict regulatory compliance** (FCRA, ECOA, GDPR). FinTrustX bridges the gap between black-box accuracy and auditable lending decisions through localized and global explainability engines.

---

## 🎯 Problem Statement & Lending Realities

In consumer credit lending:
1. **Severe Class Imbalance**: Non-defaulting loan applicants outnumber defaults by over **11:1** (~8.1% default rate). Standard metrics like raw Accuracy provide false security and hide catastrophic default losses.
2. **Asymmetric Risk Costs**: The cost of a False Negative (approving a borrower who defaults on principal) is significantly higher than a False Positive (denying a creditworthy applicant).
3. **Regulatory Auditability**: Lending algorithms cannot operate as opaque black boxes; every adverse credit decision mandates transparent reason codes and counterfactual guidance.

---

## 🚀 Key Features

- **Robust Preprocessing & Feature Engineering**: Handles missing values, target encoding, outlier management, aggregation features, and debt-to-income indicators across 245 engineered features.
- **Full 5-Model Benchmark Suite**: Compares Decision Tree, Random Forest, XGBoost, CatBoost, and Deep Neural Network under identical held-out test conditions.
- **Imbalance-Aware Evaluation**: Evaluates models primarily on **ROC-AUC** and **Average Precision (PR-AUC)** alongside customized lending business metrics.
- **Multi-Faceted Explainable AI (XAI)**:
  - **SHAP (SHapley Additive exPlanations)**: Global feature importance, summary beeswarm plots, and local waterfall explanations.
  - **LIME (Local Interpretable Model-agnostic Explanations)**: Local perturbation-based linear approximations.
  - **DiCE (Diverse Counterfactual Explanations)**: Actionable "what-if" guidance for applicants to turn a rejection into an approval.
  - **Integrated Gradients**: Axiomatic attribution for deep learning models.
- **Dynamic Decision Threshold Sweep**: Simulates operational cut-offs from `0.10` to `0.90` to optimize default capture versus loan rejection volume.
- **Production-Ready Architecture**: Modular `src/` hierarchy, model persistence (`.joblib`, `.keras`), and FastAPI serving interface.

---

## 🧠 Model Architecture & Methodology

```
                                 ┌─────────────────────────────┐
                                 │  Home Credit Raw Data       │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │ 02_Preprocessing Pipeline   │
                                 │ (Imputation, Scaling, OHE)  │
                                 └──────────────┬──────────────┘
                                                │
                                 ┌──────────────┴──────────────┐
                                 ▼                             ▼
                    ┌─────────────────────────┐   ┌─────────────────────────┐
                    │ Tree & Boosting Models  │   │ Deep Neural Network     │
                    │ • Decision Tree         │   │ • Multi-Layer Perceptron│
                    │ • Random Forest         │   │ • Dropout & BatchNorm   │
                    │ • XGBoost & CatBoost    │   │ • Early Stopping        │
                    │ • Optuna Hyperparam CV  │   │ • Sigmoid Output        │
                    └────────────┬────────────┘   └────────────┬────────────┘
                                 │                             │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │ 06_Model_Comparison.ipynb   │
                                 │ Held-Out Test Evaluation    │
                                 │ (ROC-AUC, PR-AUC, Cost)     │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │ 05_Explainable_AI.ipynb     │
                                 │ (SHAP, LIME, Counterfactual)│
                                 └─────────────────────────────┘
```

---

## 📊 Benchmark Evaluation Results

Evaluated on the **61,503 held-out test applicants** (245 features, 4,965 actual defaults):

### Standard Performance Comparison (Sorted by ROC AUC)
| Model | ROC AUC | Average Precision (PR-AUC) | F1 Score | Recall (Default Capture) | Precision | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CatBoost (Champion)** | **0.7716** | 0.2784 | 0.3705 | 0.6410 | 0.2604 | 0.7189 |
| **XGBoost** | 0.7712 | **0.2796** | **0.3744** | 0.6466 | **0.2636** | **0.7209** |
| **Deep Neural Network** | 0.7610 | 0.2603 | 0.3552 | 0.6418 | 0.2458 | 0.7077 |
| **Random Forest** | 0.7382 | 0.2139 | 0.2786 | 0.3186 | 0.2475 | 0.6168 |
| **Decision Tree** | 0.6282 | 0.1211 | 0.1901 | **0.6828** | 0.1104 | 0.5999 |

*Note: Baseline empirical default prevalence is **8.07%**. Gradient boosting models achieve >3.4x improvement over random guessing.*

### Credit Risk Business Metrics (Threshold = 0.50)
| Model | True Defaults Captured | False Defaults Flagged | Good Customers Cleared | Defaults Missed | Default Capture Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CatBoost (Champion)** | 3,183 | 9,047 | 47,491 | 1,783 | **64.10%** |
| **XGBoost** | 3,211 | 8,972 | 47,566 | 1,755 | **64.66%** |
| **Deep Neural Network** | 3,187 | 9,789 | 46,749 | 1,779 | **64.18%** |
| **Random Forest** | 1,582 | 4,809 | 51,729 | 3,383 | 31.86% |
| **Decision Tree** | 3,390 | 27,309 | 29,229 | 1,575 | 68.28% |

### Operational Threshold Sensitivity (CatBoost Champion)
| Threshold | Precision | Recall (Default Capture) | F1 Score | True Defaults Captured | False Defaults Flagged |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `0.10` | 0.0810 | 1.0000 | 0.1498 | 4,966 | 0 |
| `0.20` | 0.0886 | 0.9859 | 0.1626 | 4,896 | 50,369 |
| `0.30` | 0.1337 | 0.8844 | 0.2323 | 4,392 | 28,450 |
| `0.40` | 0.1966 | 0.7712 | 0.3134 | 3,830 | 15,647 |
| `0.50` | 0.2604 | 0.6410 | 0.3705 | 3,183 | 9,047 |
| `0.60` | 0.3344 | 0.4905 | 0.3976 | 2,436 | 4,849 |
| `0.70` | 0.4080 | 0.3236 | 0.3610 | 1,607 | 2,332 |
| `0.80` | 0.5057 | 0.1607 | 0.2440 | 798 | 780 |

---

## 🛠️ Technology Stack

- **Core & Manipulation**: Python 3.10+, NumPy, Pandas, SciPy, PyArrow
- **Machine Learning**: Scikit-Learn, Imbalanced-Learn, XGBoost, CatBoost
- **Deep Learning**: TensorFlow 2.x / Keras
- **Hyperparameter Optimization**: Optuna (TPE Sampler & Median Pruning)
- **Explainable AI (XAI)**: SHAP, LIME, DiCE-ML
- **Visualization**: Matplotlib, Seaborn, Plotly, Missingno
- **API & Serving**: FastAPI, Uvicorn, Pydantic
- **Model Serialization**: Joblib

---

## 📁 Repository Structure

```
Credit-risk-ai/
├── data/
│   ├── raw/                      # Raw Kaggle CSVs (application_train.csv - gitignored)
│   ├── processed/                # Processed parquet partitions
│   ├── processed_train.parquet   # Processed training features (245 cols)
│   └── processed_test.parquet    # Processed held-out test features (61,503 rows)
├── models/
│   ├── best_model.joblib         # Persisted champion model (CatBoost)
│   ├── decision_tree.joblib      # Decision tree model artifact
│   ├── random_forest.joblib      # Random forest model artifact
│   ├── xgboost.joblib            # XGBoost model artifact
│   ├── catboost.joblib           # CatBoost model artifact
│   ├── neural_network.keras      # Deep neural network artifact
│   └── preprocessing_pipeline.joblib # Fitted preprocessor transformer
├── notebooks/
│   ├── 01_EDA.ipynb              # Exploratory Data Analysis & missingness audit
│   ├── 02_Preprocessing.ipynb    # Feature engineering & transformation pipeline
│   ├── 03_ML_Models.ipynb        # ML model training, Optuna tuning & baselines
│   ├── 04_DL_Model.ipynb         # Deep learning neural network training
│   ├── 05_Explainable_AI.ipynb   # SHAP, LIME & Counterfactual explanations
│   └── 06_Model_Comparison.ipynb # Final model comparison, ROC/PR & champion selection
├── reports/
│   ├── model_comparison.csv      # Standardized metric benchmark
│   ├── business_metrics.csv      # Credit-risk default capture metrics
│   ├── threshold_analysis.csv    # Multi-threshold sweep data
│   └── model_ranking.csv         # Multi-dimensional ranking table
├── src/
│   ├── __init__.py
│   ├── config.py                 # Central settings, paths, seeds, & parameters
│   ├── evaluate.py               # EvaluationEngine & business metric calculators
│   ├── preprocessing.py          # Data cleaning & transformer pipelines
│   ├── feature_engineering.py    # Custom domain feature transformers
│   ├── utils.py                  # Seeding, I/O, & logging utilities
│   ├── explainability/           # SHAP, LIME, DiCE & Integrated Gradients
│   ├── models/                   # BaseModel wrappers (DT, RF, XGB, CatBoost, NN)
│   ├── training/                 # ML and DL training orchestrators
│   └── tunning/                  # Optuna tuning engines & visualizers
├── .env.example                  # Environment configuration template
├── .gitignore                    # Comprehensive Git ignore rules
├── requirements.txt              # Production dependency specifications
└── README.md                     # Project documentation
```

---

## 💻 Installation & Local Execution

### 1. Clone the Repository
```bash
git clone https://github.com/AnuragKashyap-dev/Credit-risk-ai.git
cd Credit-risk-ai
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Raw Dataset Setup
Download the `application_train.csv` dataset from [Kaggle Home Credit Default Risk](https://www.kaggle.com/c/home-credit-default-risk/data) and place it in `data/raw/application_train.csv`.

### 5. Run the End-to-End Notebooks
Launch Jupyter Lab or VS Code and execute the notebooks in sequence:
1. `notebooks/01_EDA.ipynb`
2. `notebooks/02_Preprocessing.ipynb`
3. `notebooks/03_ML_Models.ipynb`
4. `notebooks/04_DL_Model.ipynb`
5. `notebooks/05_Explainable_AI.ipynb`
6. `notebooks/06_Model_Comparison.ipynb`

---

## ☁️ Google Colab Quick Start

FinTrustX is designed for seamless execution on **Google Colab**.

### Colab Setup Cell
Copy and run the following block in the first cell of any notebook in Google Colab:

```python
# 1. Clone repository (if running in fresh Colab session)
import os, sys
from pathlib import Path

if not os.path.exists("Credit-risk-ai"):
    !git clone https://github.com/AnuragKashyap-dev/Credit-risk-ai.git
    %cd Credit-risk-ai
    !pip install -r requirements.txt
else:
    %cd Credit-risk-ai

# 2. Add repository to Python Path
repo_root = Path.cwd().resolve()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

print(f"✅ Environment initialized. Project Root: {repo_root}")
```

---

## 🛡️ Governance & Production Limitations

1. **Benchmark vs. Production Readiness**: Test set metric superiority is a necessary but insufficient condition for automated lending. Deployment mandates:
   - **Probability Calibration**: Validating Brier score and Platt scaling for accurate Loss Given Default (LGD) calculations.
   - **Fairness & Demographic Parity**: Verifying disparate impact across protected demographic categories.
   - **Model Monitoring & PSI**: Tracking Population Stability Index (PSI) and feature drift in real-time.
2. **Adverse Action Reason Codes**: Model explanations (SHAP / LIME) describe correlational associations within the training distribution; they must be paired with human credit officer review before final loan denial.

---

## 👤 Author & Contact

**Anurag Kashyap**  
FinTrustX Platform Architect & Machine Learning Engineer  
- **GitHub**: [@AnuragKashyap-dev](https://github.com/AnuragKashyap-dev)