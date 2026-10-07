"""
=========================================================
FinTrustX API Model Service
=========================================================
Business logic for system health monitoring, artifact
readiness, and model metadata inspection.

Author: Anurag Kashyap
=========================================================
"""

import logging
from api.model_loader import ModelLoader
from api.schemas import HealthResponse, ModelInfoResponse
from api.config import API_VERSION

logger = logging.getLogger(__name__)


class ModelService:
    """Service handling model metadata, configuration info, and health checks."""

    @staticmethod
    def get_health(model_loader: ModelLoader) -> HealthResponse:
        """Evaluate readiness status of the backend API and ML models."""
        is_ready = model_loader.is_loaded and (model_loader.model is not None) and (model_loader.pipeline is not None)
        status_str = "healthy" if is_ready else "unhealthy"
        
        return HealthResponse(
            status=status_str,
            model_loaded=model_loader.model is not None,
            pipeline_loaded=model_loader.pipeline is not None,
            model="xgboost",
            version=API_VERSION
        )

    @staticmethod
    def get_model_info(model_loader: ModelLoader) -> ModelInfoResponse:
        """Return deployed XGBoost model characteristics and static performance metrics."""
        if not model_loader.is_loaded:
            raise RuntimeError("Model artifacts are not loaded.")

        model_type_str = type(model_loader.model).__name__
        n_raw = len(model_loader.raw_feature_names)
        n_prep = len(model_loader.feature_names)

        return ModelInfoResponse(
            model_name="XGBoost Champion",
            model_type=model_type_str,
            task="Binary Credit Risk Classification",
            target_column="TARGET",
            n_raw_features=n_raw,
            n_preprocessed_features=n_prep,
            performance_metrics=model_loader.metrics if model_loader.metrics else None
        )
