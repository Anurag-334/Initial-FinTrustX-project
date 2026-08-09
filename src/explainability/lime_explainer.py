"""
=========================================================
LIME Explainability

Provides local explanations for individual predictions.

Author : Anurag Kashyap
=========================================================
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from lime.lime_tabular import LimeTabularExplainer

from src.explainability.base_explainer import BaseExplainer

class LimeExplainer(BaseExplainer):
    def __init__(self, model,X_train, feature_names, class_names=("No Default", "Default"), output_dir="reports/lime"):
        self.X_train = X_train
        self.class_names = class_names 
        super().__init__(model,feature_names,output_dir)
        self.X_train = X_train
        self.class_names = class_names
        self.explainer = LimeTabularExplainer(training_data=X_train,feature_names=feature_names,
                                              class_names=class_names,mode="classification",
                                              discretize_continuous=True,random_state=42)
    def explain_instance(self, instance, num_samples=10):
        if self.model is None:
            raise ValueError("model is None. Cannot generate explanations without a trained model.")

        # bind model to a local variable for static analyzers and validate methods
        model = self.model
        if hasattr(model, "predict_proba"):
            predict_fn = model.predict_proba
        elif hasattr(model, "predict"):
            def predict_fn(x):
                # handle models (e.g., Keras) whose predict returns shape (n,1) or (n,)
                prob = model.predict(x, verbose=0).reshape(-1)
                return pd.DataFrame({0: 1 - prob, 1: prob}).values
        else:
            raise ValueError("Model does not implement predict_proba or predict. Cannot generate probabilities.")

        explanation = self.explainer.explain_instance(
            data_row=instance,
            predict_fn=predict_fn,
            num_samples=num_samples,
        )
        return explanation

    def save_html(self, explanation, filename):
        filepath = self.output_dir / filename
        explanation.save_to_file(filepath)
        return filepath

    def save_png(self, explanation, filename):
        fig = explanation.as_pyplot_figure()
        filepath = self.output_dir / filename
        fig.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return filepath

    def feature_importance(self, explanation):
        return explanation.as_list()
    def explain_multiple(self,X,indices):
        results = {}
        for idx in indices:
         explanation = self.explain_instance(X[idx])


         results[idx] = explanation

        return results 
    
    