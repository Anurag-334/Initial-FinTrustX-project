"""
=========================================================
FinTrustX API Prediction Service
=========================================================
Business logic for managing single applicant evaluations
and batch underwriting predictions with SQLite Feature Store integration.

Author: Anurag Kashyap
=========================================================
"""

import logging
from typing import Any, Dict, List, Optional
from api.config import (
    DEFAULT_CLASSIFICATION_THRESHOLD,
    FEATURE_STORE_DB_PATH,
    FEATURE_STORE_PATH,
)
from api.feature_store import FeatureStore, get_feature_store
from api.predictor import XGBoostPredictor
from api.schemas import (
    CreditRiskRequest,
    BatchCreditRiskRequest,
    PredictionResponse,
    BatchPredictionResponse,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Service orchestrating applicant scoring and batch inference pipelines."""

    def __init__(self, feature_store: Optional[FeatureStore] = None) -> None:
        self.feature_store = feature_store if feature_store is not None else get_feature_store()

    def _merge_applicant_features(self, request: CreditRiskRequest) -> Dict[str, Any]:
        """
        Merge historical features from SQLite Feature Store with incoming request payload.
        Incoming payload fields explicitly set by user override historical features.
        Schema defaults provide fallback for missing baseline attributes.
        """
        applicant_id = request.SK_ID_CURR
        historical: Optional[Dict[str, Any]] = None

        if applicant_id is not None and self.feature_store is not None:
            historical = self.feature_store.get_applicant_features(applicant_id)
            if historical:
                logger.info(
                    f"Retrieved {len(historical)} historical features from Feature Store "
                    f"for applicant {applicant_id}"
                )
            else:
                logger.warning(
                    f"Applicant {applicant_id} not found in feature store; "
                    "using request payload fallback."
                )

        base_data = request.model_dump(exclude_none=False)
        if historical:
            base_data.update(historical)
            incoming_overrides = request.model_dump(exclude_unset=True)
            base_data.update(incoming_overrides)
            base_data["SK_ID_CURR"] = applicant_id
            return base_data
        else:
            base_data["SK_ID_CURR"] = applicant_id
            return base_data

    def predict_single(
        self,
        request: CreditRiskRequest,
        predictor: XGBoostPredictor,
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
        explain: bool = False,
    ) -> PredictionResponse:
        """
        Process a single credit risk evaluation.
        """
        if request is None:
            raise ValueError("CreditRiskRequest is required.")
        if predictor is None:
            raise ValueError("XGBoostPredictor is required.")

        payload = self._merge_applicant_features(request)
        logger.info(
            f"Processing prediction request (Applicant ID: {payload.get('SK_ID_CURR')}, "
            f"Explain: {explain})"
        )

        return predictor.predict_single(
            raw_data=payload,
            threshold=threshold,
            explain=explain,
        )

    def predict_batch(
        self,
        batch_request: BatchCreditRiskRequest,
        predictor: XGBoostPredictor,
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
    ) -> BatchPredictionResponse:
        """
        Process multiple credit risk applicants in a vectorized batch.
        """
        if batch_request is None:
            raise ValueError("BatchCreditRiskRequest is required.")
        if predictor is None:
            raise ValueError("XGBoostPredictor is required.")

        app_ids = [
            req.SK_ID_CURR
            for req in batch_request.requests
            if req.SK_ID_CURR is not None
        ]

        historical_batch: Dict[int, Dict[str, Any]] = {}
        if app_ids and self.feature_store is not None:
            historical_batch = self.feature_store.get_batch_applicant_features(app_ids)

        raw_list: List[Dict[str, Any]] = []
        for req in batch_request.requests:
            app_id = req.SK_ID_CURR
            base_data = req.model_dump(exclude_none=False)

            if app_id is not None and app_id in historical_batch:
                historical = historical_batch[app_id]
                base_data.update(historical)
                incoming_overrides = req.model_dump(exclude_unset=True)
                base_data.update(incoming_overrides)
                base_data["SK_ID_CURR"] = app_id
            else:
                base_data["SK_ID_CURR"] = app_id

            raw_list.append(base_data)

        logger.info(f"Processing batch prediction for {len(raw_list)} applicants.")

        predictions: List[PredictionResponse] = predictor.predict_batch(
            raw_data_list=raw_list,
            threshold=threshold,
        )

        return BatchPredictionResponse(
            predictions=predictions,
            total_processed=len(predictions),
            model="XGBoost",
        )
