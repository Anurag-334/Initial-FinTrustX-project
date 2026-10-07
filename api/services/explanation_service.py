"""
=========================================================
FinTrustX API Explanation Service
=========================================================
Business logic for generating standalone SHAP feature
attributions and adverse action factor rankings with
SQLite Feature Store integration.

Author: Anurag Kashyap
=========================================================
"""

import logging
from typing import Any, Dict, Optional
from api.feature_store import FeatureStore, get_feature_store
from api.predictor import XGBoostPredictor
from api.preprocessing import transform_raw_to_features
from api.schemas import CreditRiskRequest, ExplanationResponse

logger = logging.getLogger(__name__)


class ExplanationService:
    """Service dedicated to computing SHAP explanations for individual credit applicants."""

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

    def explain_applicant(
        self,
        request: CreditRiskRequest,
        predictor: XGBoostPredictor,
    ) -> ExplanationResponse:
        """
        Compute localized SHAP explanations for the supplied applicant.
        """
        if request is None:
            raise ValueError("CreditRiskRequest is required.")
        if predictor is None:
            raise ValueError("XGBoostPredictor is required.")

        payload = self._merge_applicant_features(request)
        logger.info(
            f"Computing standalone SHAP explanation for Applicant ID: {payload.get('SK_ID_CURR')}"
        )

        # 1. Transform raw input to feature space
        X_trans = transform_raw_to_features(
            raw_inputs=payload,
            pipeline=predictor.model_loader.pipeline,
            raw_feature_names=predictor.model_loader.raw_feature_names,
        )

        # 2. Extract SHAP attribution
        explainer = predictor._get_explainer()
        return explainer.explain_sample(X_trans)
