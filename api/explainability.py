"""
=========================================================
FinTrustX API Explainability Engine
=========================================================
Computes localized SHAP feature attributions on XGBoost
predictions to provide transparent reason codes and adverse
action factors.

Author: Anurag Kashyap
=========================================================
"""

import logging
from typing import Any, List, Optional
import numpy as np
import shap

from api.schemas import ExplanationResponse, FeatureFactor
from api.config import TOP_EXPLANATION_FACTORS

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    SHAP TreeExplainer wrapper for fast XGBoost feature attribution.
    """
    def __init__(self, model: Any, feature_names: List[str]) -> None:
        self.model = model
        self.feature_names = feature_names
        self.explainer: Optional[shap.TreeExplainer] = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        """Initialize the TreeExplainer instance."""
        try:
            self.explainer = shap.TreeExplainer(self.model)
            logger.info("SHAP TreeExplainer initialized for XGBoost.")
        except Exception as e:
            logger.warning(f"Could not initialize TreeExplainer: {e}")
            self.explainer = None

    def explain_sample(
        self,
        transformed_features: np.ndarray,
        top_n: int = TOP_EXPLANATION_FACTORS
    ) -> ExplanationResponse:
        """
        Generate feature attributions for a single applicant.
        
        Parameters
        ----------
        transformed_features : np.ndarray
            2D array of shape (1, 245) or 1D array of shape (245,).
        top_n : int
            Number of top factors to return.
            
        Returns
        -------
        ExplanationResponse
            Top positive risk factors and top protective factors.
        """
        if self.explainer is None:
            self._init_explainer()
            if self.explainer is None:
                raise RuntimeError("SHAP TreeExplainer could not be initialized.")

        if transformed_features.ndim == 1:
            transformed_features = transformed_features.reshape(1, -1)

        try:
            shap_values = self.explainer.shap_values(transformed_features)
            vals = shap_values[0]
            base_value = float(self.explainer.expected_value) if hasattr(self.explainer, "expected_value") else None
        except Exception as e:
            logger.error(f"Error computing SHAP values: {e}")
            raise RuntimeError(f"SHAP explanation calculation failed: {e}") from e

        # Identify top risk factors (positive SHAP value increases default probability)
        # Identify top protective factors (negative SHAP value reduces default probability)
        sorted_indices = np.argsort(vals)
        
        # Risk factors (highest positive contributions)
        risk_idx = [i for i in sorted_indices[::-1] if vals[i] > 0][:top_n]
        top_risk_factors = [
            FeatureFactor(
                feature=self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}",
                impact="increases risk",
                contribution=round(float(vals[i]), 4)
            )
            for i in risk_idx
        ]

        # Protective factors (lowest negative contributions)
        protect_idx = [i for i in sorted_indices if vals[i] < 0][:top_n]
        protective_factors = [
            FeatureFactor(
                feature=self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}",
                impact="reduces risk",
                contribution=round(float(vals[i]), 4)
            )
            for i in protect_idx
        ]

        return ExplanationResponse(
            top_risk_factors=top_risk_factors,
            protective_factors=protective_factors,
            base_value=round(base_value, 4) if base_value is not None else None
        )
