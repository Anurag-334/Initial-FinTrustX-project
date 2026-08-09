"""
=========================================================
Prediction Router

Handles prediction requests.

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

import pandas as pd

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_predictor
from api.schemas import (
    PredictionRequest,
    PredictionResponse,
)
from src.inference.predictor import Predictor

router = APIRouter()


@router.post(
    "/",
    response_model=PredictionResponse,
)
def predict(
    request: PredictionRequest,
    predictor: Predictor = Depends(get_predictor),
):
    """
    Predict loan default probability.
    """

    try:

        # Convert JSON → DataFrame
        input_df = pd.DataFrame(
            [request.features]
        )

        # Run prediction
        result = predictor.predict(
            input_df
        )

        return PredictionResponse(
            prediction=result["prediction"],
            probability=result["probability"],
            risk_level=result.get(
                "risk_level",
                "Unknown",
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )