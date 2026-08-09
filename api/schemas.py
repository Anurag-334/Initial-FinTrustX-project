"""
=========================================================
Pydantic Schemas

Defines request and response models for the API.

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


# =========================================================
# Prediction Request
# =========================================================

class PredictionRequest(BaseModel):
    """
    Generic prediction request.

    Accepts dynamic feature-value pairs.
    """

    features: dict[str, Any]


# =========================================================
# Prediction Response
# =========================================================

class PredictionResponse(BaseModel):
    """
    Prediction response returned by the API.
    """

    prediction: int
    probability: float
    risk_level: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prediction": 0,
                "probability": 0.9132,
                "risk_level": "Low",
            }
        }
    )


# =========================================================
# Batch Prediction Response
# =========================================================

class BatchPredictionResponse(BaseModel):

    total_records: int

    predictions: list[PredictionResponse]


# =========================================================
# Explainability Request
# =========================================================

class ExplainabilityRequest(BaseModel):

    features: dict[str, Any]

    method: str


# =========================================================
# Health Response
# =========================================================

class HealthResponse(BaseModel):

    status: str

    api: str