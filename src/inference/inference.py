"""
====================================================
Inference Engine

Runs complete inference pipeline.

Author: Anurag Kashyap
====================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from src.inference.predictor import Predictor

logger = logging.getLogger(__name__)

class InferenceEngine:
    """
    Complete inference pipeline.
    """
    def __init__(self,predictor: Predictor,) -> None:
        self.predictor = predictor

    def validate_input(self,data: pd.DataFrame,) -> None:
        """
        Validates input data for inference.
        """
        if data.empty:
            raise ValueError("Input dataframe is empty.")

        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

    def classify_risk(self,probability: float,) -> str:
        if probability >= 0.80:
            return "Very High"

        elif probability >= 0.60:
            return "High"

        elif probability >= 0.40:
            return "Medium"

        elif probability >= 0.20:
            return "Low"

        return "Very Low"

    def run(self,data: pd.DataFrame,) -> dict:
        logger.info("Running inference...")

        self.validate_input(data)

        result = self.predictor.predict(data)

        risk = self.classify_risk(result["probability"])

        return self.format_response(
                prediction=result["prediction"],
                probability=result["probability"],
                risk_level=risk,)
    def format_response(self,prediction: int,probability: float,risk_level: str,) -> dict:
        """
        Formats the inference result into a dictionary.
        """
        risk_level = self.classify_risk(probability)

        return {
            "prediction": int(prediction),
            "probability": float(probability),
            "risk_level": risk_level,
        }
    