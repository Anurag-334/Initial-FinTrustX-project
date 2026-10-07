"""
=========================================================
FinTrustX API Dependency Injection
=========================================================
FastAPI dependency providers for ModelLoader, Predictor,
FeatureStore, and Service layer singletons.

Author: Anurag Kashyap
=========================================================
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
import os
from api.config import FEATURE_STORE_DB_PATH, FEATURE_STORE_PATH
from api.feature_store import FeatureStore, get_feature_store as _get_default_feature_store

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("FINTRUSTX_API_KEY", "dev_api_key_123")
    if api_key != expected_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

from api.model_loader import ModelLoader, get_model_loader
from api.predictor import XGBoostPredictor
from api.services.model_service import ModelService
from api.services.prediction_service import PredictionService
from api.services.explanation_service import ExplanationService

_predictor_instance = None


def get_loader() -> ModelLoader:
    """Provide singleton ModelLoader, ensuring artifacts are loaded."""
    loader = get_model_loader()
    if not loader.is_loaded:
        loader.load_artifacts()
    return loader


def get_predictor(loader: ModelLoader = Depends(get_loader)) -> XGBoostPredictor:
    """Provide singleton XGBoostPredictor instance."""
    global _predictor_instance
    if _predictor_instance is None or _predictor_instance.model_loader != loader:
        _predictor_instance = XGBoostPredictor(model_loader=loader)
    return _predictor_instance


def get_model_service() -> ModelService:
    """Provide ModelService instance."""
    return ModelService()


def get_feature_store() -> FeatureStore:
    """Provide singleton FeatureStore instance."""
    return _get_default_feature_store()


def get_prediction_service(
    feature_store: FeatureStore = Depends(get_feature_store),
) -> PredictionService:
    """Provide PredictionService instance wired with FeatureStore."""
    return PredictionService(feature_store=feature_store)


def get_explanation_service(
    feature_store: FeatureStore = Depends(get_feature_store),
) -> ExplanationService:
    """Provide ExplanationService instance wired with FeatureStore."""
    return ExplanationService(feature_store=feature_store)