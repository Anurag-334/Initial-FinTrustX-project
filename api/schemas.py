"""
=========================================================
FinTrustX API Pydantic Schemas
=========================================================
Request and Response models for single & batch predictions,
risk classification, and SHAP feature attribution.

Author: Anurag Kashyap
=========================================================
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


# =========================================================
# Request Models
# =========================================================

class CreditRiskRequest(BaseModel):
    """
    Loan applicant input schema.
    Provides key credit and demographic fields with sensible defaults,
    while permitting any additional Home Credit raw feature via extra='allow'.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Identifier
    SK_ID_CURR: Optional[int] = Field(
        default=None,
        description="Unique applicant loan ID. If provided, queries SQLite feature store for historical profile."
    )

    @model_validator(mode="before")
    @classmethod
    def map_applicant_id_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "SK_ID_CURR" not in data and "applicant_id" in data:
                data["SK_ID_CURR"] = data["applicant_id"]
        return data

    @field_validator("DAYS_EMPLOYED")
    @classmethod
    def validate_days_employed(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v > 0 and v != 365243.0:
                raise ValueError("DAYS_EMPLOYED must be <= 0 or exactly 365243 (for retired).")
        return v

    # Core Application & Loan Info
    NAME_CONTRACT_TYPE: Optional[str] = Field(default="Cash loans", description="Contract type: Cash loans or Revolving loans")
    CODE_GENDER: Optional[str] = Field(default="M", description="Gender of applicant: M, F, or XNA")
    FLAG_OWN_CAR: Optional[str] = Field(default="N", description="Car ownership flag: Y or N")
    FLAG_OWN_REALTY: Optional[str] = Field(default="Y", description="Real estate ownership flag: Y or N")
    CNT_CHILDREN: Optional[int] = Field(default=0, ge=0, description="Number of children")
    
    # Financial Values
    AMT_INCOME_TOTAL: Optional[float] = Field(default=150000.0, gt=0, description="Total annual income in currency")
    AMT_CREDIT: Optional[float] = Field(default=450000.0, gt=0, description="Credit amount requested")
    AMT_ANNUITY: Optional[float] = Field(default=25000.0, ge=0, description="Loan annuity payment")
    AMT_GOODS_PRICE: Optional[float] = Field(default=450000.0, ge=0, description="Price of goods for consumer loan")

    # Demographic & Social Background
    NAME_TYPE_SUITE: Optional[str] = Field(default="Unaccompanied", description="Accompanying person suite")
    NAME_INCOME_TYPE: Optional[str] = Field(default="Working", description="Income source / employment category")
    NAME_EDUCATION_TYPE: Optional[str] = Field(default="Secondary / secondary special", description="Highest education level")
    NAME_FAMILY_STATUS: Optional[str] = Field(default="Married", description="Family marital status")
    NAME_HOUSING_TYPE: Optional[str] = Field(default="House / apartment", description="Living situation")
    
    # Age & Employment Duration (Home Credit format: negative days from application)
    DAYS_BIRTH: Optional[float] = Field(default=-14000.0, le=0, description="Age in negative days from application (e.g. -14000 ~ 38 years)")
    DAYS_EMPLOYED: Optional[float] = Field(default=-2000.0, description="Days employed in negative days (or 365243 for retired)")
    DAYS_REGISTRATION: Optional[float] = Field(default=-4000.0, description="Registration change in negative days")
    DAYS_ID_PUBLISH: Optional[float] = Field(default=-2000.0, description="ID document publish in negative days")

    # External Credit Bureau Risk Scores (Critical Default Predictors)
    EXT_SOURCE_1: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized score from external credit bureau 1")
    EXT_SOURCE_2: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized score from external credit bureau 2")
    EXT_SOURCE_3: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized score from external credit bureau 3")

    # Region and Document Flags
    REGION_POPULATION_RELATIVE: Optional[float] = Field(default=0.02, ge=0.0, le=1.0, description="Normalized population of region")
    REGION_RATING_CLIENT: Optional[int] = Field(default=2, ge=1, le=3, description="Client region rating (1, 2, 3)")
    REGION_RATING_CLIENT_W_CITY: Optional[int] = Field(default=2, ge=1, le=3, description="Client region rating with city (1, 2, 3)")
    OCCUPATION_TYPE: Optional[str] = Field(default="Laborers", description="Client occupation")
    ORGANIZATION_TYPE: Optional[str] = Field(default="Business Entity Type 3", description="Employer organization category")


class BatchCreditRiskRequest(BaseModel):
    """Batch prediction request schema."""
    requests: List[CreditRiskRequest] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="List of applicant credit risk prediction payloads (max 500)"
    )


# Alias for latent or legacy prediction request references
PredictionRequest = CreditRiskRequest


# =========================================================
# Response Models
# =========================================================

class FeatureFactor(BaseModel):
    """Attribution item representing feature contribution to prediction."""
    feature: str = Field(..., description="Feature name")
    impact: str = Field(..., description="'increases risk' or 'reduces risk'")
    contribution: float = Field(..., description="SHAP attribution value")


class ExplanationResponse(BaseModel):
    """Explainable AI attribution breakdown."""
    top_risk_factors: List[FeatureFactor] = Field(..., description="Top features increasing default probability")
    protective_factors: List[FeatureFactor] = Field(..., description="Top features reducing default probability")
    base_value: Optional[float] = Field(default=None, description="Model baseline log-odds / expected value")


class PredictionResponse(BaseModel):
    """Single credit risk prediction response."""
    prediction: int = Field(..., description="Binary prediction: 0 (Non-Default) or 1 (Default)")
    default_probability: float = Field(..., description="Predicted probability of loan default P(TARGET=1) in [0.0, 1.0]")
    risk_score: float = Field(..., description="Standardized credit risk score from 0.0 to 100.0")
    risk_category: str = Field(..., description="Risk tier: Low Risk, Moderate Risk, High Risk, Very High Risk")
    loan_decision: str = Field(..., description="Application recommendation: Likely Approved, Manual Review, Likely Rejected")
    model: str = Field(default="XGBoost", description="Model architecture used for inference")
    threshold_used: float = Field(default=0.50, description="Decision cut-off threshold applied")
    explanation: Optional[ExplanationResponse] = Field(default=None, description="Optional SHAP feature attribution")
    applicant_id: Optional[int] = Field(default=None, description="Applicant identifier if provided")


class BatchPredictionResponse(BaseModel):
    """Batch prediction response containing multiple results."""
    predictions: List[PredictionResponse] = Field(..., description="List of individual prediction responses")
    total_processed: int = Field(..., description="Total applicants evaluated in batch")
    model: str = Field(default="XGBoost", description="Model architecture used for inference")


class ModelInfoResponse(BaseModel):
    """Metadata and performance parameters of the deployed model."""
    model_name: str = Field(..., description="Name of deployed model")
    model_type: str = Field(..., description="Underlying algorithm / library class")
    task: str = Field(default="Binary Credit Risk Classification", description="Supervised task definition")
    target_column: str = Field(default="TARGET", description="Target variable name (1 = Default, 0 = Non-Default)")
    n_raw_features: int = Field(..., description="Expected raw input feature count")
    n_preprocessed_features: int = Field(..., description="Transformed feature count fed to XGBoost")
    performance_metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="Held-out test benchmark metrics (ROC AUC, Average Precision, F1, Recall, Precision)"
    )


class HealthResponse(BaseModel):
    """API and model readiness health check."""
    status: str = Field(..., description="Service health: healthy or unhealthy")
    model_loaded: bool = Field(..., description="Whether XGBoost model is loaded into memory")
    pipeline_loaded: bool = Field(..., description="Whether ColumnTransformer preprocessing pipeline is loaded")
    model: str = Field(default="xgboost", description="Deployed champion model name")
    version: str = Field(default="1.0.0", description="API version")