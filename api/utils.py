"""
=========================================================
FinTrustX API Utilities
=========================================================
Helper functions for risk scoring, risk category determination,
and loan underwriting recommendation mappings.

Author: Anurag Kashyap
=========================================================
"""

from typing import Dict
from api.config import RISK_THRESHOLDS, LOAN_DECISION_MAPPING


def calculate_risk_score(probability: float) -> float:
    """
    Convert raw probability [0.0, 1.0] into an intuitive 0-100 risk score.
    Higher score indicates higher risk of default.
    """
    score = probability * 100.0
    return round(float(score), 2)


def classify_risk(probability: float, thresholds: Dict[str, float] = None) -> str:
    """
    Map default probability to application risk category tiers.
    
    Tiers:
    - P < low_max (0.20) -> "Low Risk"
    - low_max <= P < moderate_max (0.40) -> "Moderate Risk"
    - moderate_max <= P < high_max (0.60) -> "High Risk"
    - P >= high_max (0.60) -> "Very High Risk"
    """
    if thresholds is None:
        thresholds = RISK_THRESHOLDS

    if probability < thresholds.get("low_max", 0.20):
        return "Low Risk"
    elif probability < thresholds.get("moderate_max", 0.40):
        return "Moderate Risk"
    elif probability < thresholds.get("high_max", 0.60):
        return "High Risk"
    else:
        return "Very High Risk"


def get_loan_decision(risk_category: str) -> str:
    """
    Map risk tier to a loan underwriting recommendation.
    
    Disclaimer: Application-level decision support only.
    """
    return LOAN_DECISION_MAPPING.get(risk_category, "Manual Review")
