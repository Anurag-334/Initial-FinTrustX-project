"""
=========================================================
FinTrustX API Configuration
=========================================================
Central configuration for FastAPI service, model artifact paths,
risk categorization thresholds, and operational lending rules.

Author: Anurag Kashyap
=========================================================
"""

import os
from pathlib import Path
from typing import List
from types import MappingProxyType

# Dynamic Project Root Resolution
def find_project_root(anchor_dirs=("src", "models", "data"), max_upward=4) -> Path:
    """Resolve project root dynamically from cwd or parent directories."""
    current = Path(__file__).resolve().parent
    for _ in range(max_upward):
        if all((current / marker).exists() for marker in anchor_dirs):
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = find_project_root()
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"

# Artifact Paths
XGBOOST_MODEL_PATH = MODELS_DIR / "xgboost.joblib"
PREPROCESSING_PIPELINE_PATH = MODELS_DIR / "preprocessing_pipeline.joblib"
FEATURE_NAMES_PATH = MODELS_DIR / "preprocessed_feature_names.csv"
METRICS_REPORT_PATH = REPORTS_DIR / "model_comparison.csv"

# Feature Store Configuration
FEATURE_STORE_DB_PATH = Path(os.getenv("FEATURE_STORE_DB_PATH", str(DATA_DIR / "feature_store.db")))
FEATURE_STORE_PATH = FEATURE_STORE_DB_PATH
FEATURE_STORE_TABLE_NAME = os.getenv("FEATURE_STORE_TABLE_NAME", "applicant_features")

# API Metadata
API_TITLE = "FinTrustX Credit Risk AI API"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "Production-grade Explainable AI API for Credit Risk Assessment, "
    "Loan Decision Intelligence, and Adverse Action Attribution."
)

# CORS Configuration - Supports Local Dev & Common Frontend Ports
CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://localhost:5501",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# Risk Classification Thresholds (Configurable Application-Level Categorization)
# Note: These are application decision tiers and do not replace official regulatory classifications.
RISK_THRESHOLDS = MappingProxyType({
    "low_max": 0.20,       # P < 0.20 -> Low Risk
    "moderate_max": 0.40,  # 0.20 <= P < 0.40 -> Moderate Risk
    "high_max": 0.60,      # 0.40 <= P < 0.60 -> High Risk
                           # P >= 0.60 -> Very High Risk
})

# Operational Lending Decisions Mapping
LOAN_DECISION_MAPPING = MappingProxyType({
    "Low Risk": "Likely Approved",
    "Moderate Risk": "Manual Review",
    "High Risk": "Higher Risk / Manual Review",
    "Very High Risk": "Likely Rejected",
})

# Inference & Batch Constraints
DEFAULT_CLASSIFICATION_THRESHOLD = 0.50
MAX_BATCH_SIZE = 500
TOP_EXPLANATION_FACTORS = 5

# Host & Server Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
