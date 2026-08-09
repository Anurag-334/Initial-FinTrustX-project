"""
=========================================================
Base Explainer

Common functionality shared by all explainability
methods.

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
try:
    import tensorflow as tf
except ImportError:
    tf = None
import matplotlib.pyplot as plt


class BaseExplainer:
    """
    Shared functionality for every explainability method
    (SHAP, LIME, Counterfactual, Integrated Gradients).

    Subclasses own the actual explanation logic; this class only
    owns the plumbing: predicting, saving figures, and managing
    the output directory.
    """

    def __init__(self, model=None, feature_names=None, output_dir="reports/explainability"):
        self.model = model
        self.feature_names = feature_names if feature_names is not None else []
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Prediction (works for both sklearn/boosting models and Keras models)
    # ------------------------------------------------------------------
    def predict(self, X):
        if self.model is None:
            raise ValueError("Model has not been initialized.")
        return self.model.predict(X)

    def predict_probability(self, X):
        if self.model is None:
            raise ValueError("Model has not been initialized.")

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        else:
            pred = self.model.predict(X, verbose=0)
            return pred

    # ------------------------------------------------------------------
    # Filesystem / figure helpers
    # ------------------------------------------------------------------
    def save_figure(self, filename):
        filepath = self.output_dir / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()

        return filepath

    def create_subfolder(self, folder_name):
        folder = self.output_dir / folder_name
        folder.mkdir(exist_ok=True, parents=True)
        return folder

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def model_name(self):
        return self.model.__class__.__name__

    def number_of_features(self):
        return len(self.feature_names)