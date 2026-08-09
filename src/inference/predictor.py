"""
=========================================================
Prediction Module

Loads trained models and preprocessing pipeline
to perform inference.

Author: Anurag Kashyap
=========================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
try:
    import tensorflow as tf
except ImportError:
    tf = None

logger = logging.getLogger(__name__)

class Predictor:
    """
    Generic prediction class for all supported models.
    """
    def __init__(self,model_path: str,pipeline_path: str,) -> None:
        self.model_path = Path(model_path)
        self.pipeline_path = Path(pipeline_path)

        self.model: Any = None
        self.pipeline: Any = None

        self.load_model()
        self.load_pipeline()

    def load_model(self) -> None:
        logger.info("Loading trained model...")

        suffix = self.model_path.suffix.lower()

        if suffix in [".keras", ".h5"]:
            global tf
            if tf is None:
                import tensorflow as tf
            self.model = tf.keras.models.load_model(self.model_path)
        else:
            self.model = joblib.load(self.model_path)

        logger.info("Model loaded successfully.")

    def load_pipeline(self) -> None:
        logger.info("Loading preprocessing pipeline...")
        self.pipeline = joblib.load(self.pipeline_path)
        logger.info("Pipeline loaded successfully.")

    def preprocess(self, data: pd.DataFrame) -> np.ndarray:
        logger.info("Preprocessing input data...")
        if self.pipeline is None:
            raise RuntimeError("Preprocessing pipeline is not loaded.")

        return self.pipeline.transform(data)

    def predict(self, data: pd.DataFrame) -> dict:
        """
        Predict the class label for the given input data.

        Parameters
        ----------
        data : pd.DataFrame
        Raw input data.

        Returns
        -------
        dict
        Prediction results.
        """

        logger.info("Running prediction...")

        X = self.preprocess(data)

        is_keras = False
        if tf is not None and isinstance(self.model, getattr(tf.keras, "Model", object)):
            is_keras = True
        elif "keras" in type(self.model).__module__.lower():
            is_keras = True

        # TensorFlow Model
        if is_keras:
            probability = float(self.model.predict(X, verbose=0)[0][0])
            prediction = int(probability >= 0.5)

        # Scikit-Learn Models
        else:
            prediction = int(self.model.predict(X)[0])

            if hasattr(self.model, "predict_proba"):
                probability = float(self.model.predict_proba(X)[0][1])
            else:
                probability = None

        logger.info("Prediction completed.")

        return {
            "prediction": prediction,
            "probability": probability,
            "model_type": type(self.model).__name__,
        }

    def predict_proba(self, data: pd.DataFrame) -> float:
        """
        Return probability of positive class.
        """

        X = self.preprocess(data)

        is_keras = False
        if tf is not None and isinstance(self.model, getattr(tf.keras, "Model", object)):
            is_keras = True
        elif "keras" in type(self.model).__module__.lower():
            is_keras = True

        if is_keras:
            probability = float(self.model.predict(X, verbose=0)[0][0])
        elif hasattr(self.model, "predict_proba"):
            probability = float(self.model.predict_proba(X)[0][1])
        else:
            probability = float(self.model.predict(X)[0])

        return probability
    def _classify_risk(self,probability: float,) -> str:
        """
        Convert probability into a risk category.
        """

        if probability >= 0.80:
            return "Very High"

        elif probability >= 0.60:
            return "High"

        elif probability >= 0.40:
            return "Medium"

        elif probability >= 0.20:
            return "Low"

        return "Very Low"

    def health_check(self) -> bool:
        """
        Check whether model and preprocessing pipeline
        are loaded correctly.
        """

        model_loaded = self.model is not None
        pipeline_loaded = self.pipeline is not None

        return model_loaded and pipeline_loaded

    def explain(self,data: pd.DataFrame,method: str = "shap",):
        """
        Generate explanation for a prediction.

        Parameters
        ----------
        data : pd.DataFrame
        Input sample.

        method : str
        Explainability method.

        Returns
        -------
        Any
        Explanation object.
        """

        if method.lower() == "shap":
            raise NotImplementedError(
            "SHAP integration will be added later."
        )

        elif method.lower() == "lime":
            raise NotImplementedError(
            "LIME integration will be added later.")

        elif method.lower() == "dice":
            raise NotImplementedError(
            "DiCE integration will be added later.")

        elif method.lower() == "integrated_gradients":
            raise NotImplementedError(
            "Integrated Gradients integration will be added later.")

        else:
            raise ValueError(
            f"Unsupported explanation method: {method}")
        

