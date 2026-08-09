"""
=========================================================
Counterfactual Explanations

Suggests minimal changes required to alter a prediction.

Author : Anurag Kashyap
=========================================================
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.explainability.base_explainer import BaseExplainer

class CounterfactualExplainer(BaseExplainer):
    def __init__(self,model: Any,feature_names,threshold=0.5,output_dir="reports/counterfactual"):
        super().__init__(model,feature_names,output_dir)
        self.model: Any = model
        self.threshold = threshold

    def predict_probability(self, X):
        if self.model is None:
            raise ValueError("Model must be provided for prediction")
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)[:, 1]
        else:
            return self.model.predict(X, verbose=0)[0][0]

    def generate_counterfactual(self,instance,feature_ranges,step=0.05,max_iterations=100):
        candidate = instance.copy()
        original_probability = self.predict_probability(candidate.reshape(1, -1))
        best_candidate = candidate.copy()
        best_probability = original_probability
        for iteration in range(max_iterations):
            for idx in range(len(candidate)):
                minimum, maximum = feature_ranges[idx]
                candidate[idx] = min(candidate[idx] + step,maximum)
                probability = self.predict_probability(candidate.reshape(1, -1))
                if probability < best_probability:
                    best_probability = probability
                    best_candidate = candidate.copy()
                if best_probability < self.threshold:
                    break
        return best_candidate
    def compare(self,original,counterfactual):
        changes = []
        for feature, old, new in zip(self.feature_names,original,counterfactual):
            if old != new:
                changes.append({"Feature": feature, "Original": old, "Counterfactual": new, "Difference": new - old})
        return pd.DataFrame(changes)

    def visualize_changes(self,comparison_df):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        plt.barh(comparison_df["Feature"],comparison_df["Difference"])
        plt.xlabel("Change in Feature Value")
        plt.title("Counterfactual Feature Changes")
        self.save_figure("counterfactual_changes.png")

    def save_report(self,comparison_df,filename="counterfactual.csv"):
        filepath = self.output_dir / filename
        comparison_df.to_csv(filepath,index=False)

        return filepath
    
    
    
