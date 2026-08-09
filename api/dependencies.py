"""
=========================================================
API Dependencies

Loads reusable resources.

Author : Anurag Kashyap
=========================================================
"""

from functools import lru_cache

from src.inference.predictor import Predictor

from src.config import (
    MODEL_DIR,
)


@lru_cache
def get_predictor() -> Predictor:
    """
    Load Predictor only once.
    """

    predictor = Predictor(
        model_path=str(MODEL_DIR / "best_model.joblib"),
        pipeline_path=str(MODEL_DIR / "preprocessing_pipeline.joblib"),
    )

    return predictor