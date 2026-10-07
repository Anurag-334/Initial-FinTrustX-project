"""
=========================================================
FinTrustX API Predictor
=========================================================
Core inference execution layer linking preprocessor,
XGBoost model, and risk scoring utilities.

Author: Anurag Kashyap
=========================================================
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from api.model_loader import ModelLoader
from api.preprocessing import transform_raw_to_features
from api.explainability import SHAPExplainer
from api.utils import calculate_risk_score, classify_risk, get_loan_decision
from api.schemas import PredictionResponse, ExplanationResponse
from api.config import DEFAULT_CLASSIFICATION_THRESHOLD

logger = logging.getLogger(__name__)


class XGBoostPredictor:
    """
    Inference orchestrator for XGBoost credit risk predictions.
    """
    def __init__(self, model_loader: ModelLoader) -> None:
        self.model_loader = model_loader
        self.explainer: Optional[SHAPExplainer] = None

    def _get_explainer(self) -> SHAPExplainer:
        """Lazy-initialize or return SHAP explainer instance."""
        if self.explainer is None:
            self.explainer = SHAPExplainer(
                model=self.model_loader.model,
                feature_names=self.model_loader.feature_names
            )
        return self.explainer

    def predict_single(
        self,
        raw_data: Dict[str, Any],
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
        explain: bool = False
    ) -> PredictionResponse:
        """
        Execute prediction on a single applicant payload.
        """
        if not self.model_loader.is_loaded:
            raise RuntimeError("Model and preprocessing artifacts are not loaded.")

        applicant_id = raw_data.get("SK_ID_CURR")

        # 1. Transform raw input to 245-dim feature representation
        X_trans = transform_raw_to_features(
            raw_inputs=raw_data,
            pipeline=self.model_loader.pipeline,
            raw_feature_names=self.model_loader.raw_feature_names
        )

        # 2. Extract positive class default probability P(TARGET=1)
        raw_prob = self.model_loader.model.predict_proba(X_trans)[0][1]
        default_prob = float(raw_prob)
        prediction = 1 if default_prob >= threshold else 0

        # 3. Calculate Risk Category, Score, and Recommendation
        risk_score = calculate_risk_score(default_prob)
        risk_category = classify_risk(default_prob)
        loan_decision = get_loan_decision(risk_category)

        # 4. Compute Explanation if requested
        explanation_res: Optional[ExplanationResponse] = None
        if explain:
            explainer = self._get_explainer()
            explanation_res = explainer.explain_sample(X_trans)

        return PredictionResponse(
            prediction=prediction,
            default_probability=round(default_prob, 4),
            risk_score=risk_score,
            risk_category=risk_category,
            loan_decision=loan_decision,
            model="XGBoost",
            threshold_used=threshold,
            explanation=explanation_res,
            applicant_id=applicant_id
        )

    def predict_batch(
        self,
        raw_data_list: List[Dict[str, Any]],
        threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD
    ) -> List[PredictionResponse]:
        """
        Execute vectorized batch prediction on multiple applicant payloads.
        """
        if not self.model_loader.is_loaded:
            raise RuntimeError("Model and preprocessing artifacts are not loaded.")

        if not raw_data_list:
            return []

        # 1. Batch Transform
        X_trans = transform_raw_to_features(
            raw_inputs=raw_data_list,
            pipeline=self.model_loader.pipeline,
            raw_feature_names=self.model_loader.raw_feature_names
        )

        # 2. Vectorized Probability Extraction
        probs = self.model_loader.model.predict_proba(X_trans)[:, 1]

        responses: List[PredictionResponse] = []
        for idx, p in enumerate(probs):
            prob_val = float(p)
            pred = 1 if prob_val >= threshold else 0
            score = calculate_risk_score(prob_val)
            cat = classify_risk(prob_val)
            dec = get_loan_decision(cat)
            app_id = raw_data_list[idx].get("SK_ID_CURR")

            responses.append(
                PredictionResponse(
                    prediction=pred,
                    default_probability=round(prob_val, 4),
                    risk_score=score,
                    risk_category=cat,
                    loan_decision=dec,
                    model="XGBoost",
                    threshold_used=threshold,
                    applicant_id=app_id
                )
            )

        return responses
