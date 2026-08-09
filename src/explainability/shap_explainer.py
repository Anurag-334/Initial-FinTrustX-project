"""
===========================================================
SHAP Explainability Module

Supports

• Decision Tree
• Random Forest
• XGBoost
• CatBoost
• Neural Networks

Author : Anurag Kashyap
===========================================================
"""

from pathlib import Path

import shap
import matplotlib.pyplot as plt
import numpy as np

from src.explainability.base_explainer import BaseExplainer

class BaseSHAPExplainer(BaseExplainer):
    def __init__(self,model,feature_names,output_dir="reports/shap"):
        super().__init__(model,feature_names,output_dir)
        self.explainer = None
        self.shap_values = None

    def compute_shap_values(self, X):
        raise NotImplementedError

    def summary_plot(self,X):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        shap.summary_plot(self.shap_values, X, feature_names=self.feature_names)
        self.save_figure("shap_summary_plot.png")

    def beeswarm_plot(self, X):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        shap.plots.beeswarm(self.shap_values, feature_names=self.feature_names)
        self.save_figure("shap_beeswarm_plot.png")

    def water_plot(self, X):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        shap.plots.waterfall(self.shap_values, feature_names=self.feature_names)
        self.save_figure("shap_water_plot.png")

    def force_plot(self, X):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        shap.plots.force(self.shap_values, feature_names=self.feature_names)
        self.save_figure("shap_force_plot.png")

    def dependence_plot(self, X, feature):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        shap.dependence_plot(feature, self.shap_values, X, feature_names=self.feature_names)
        self.save_figure(f"shap_dependence_plot_{feature}.png")

    def feature_importance_plot(self, X):
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        importance = np.abs(self.shap_values.values).mean(axis=0)
        ranking = sorted(zip(self.feature_names,importance),key=lambda x: x[1], reverse=True)
        return ranking

    
class TreeSHAPExplainer(BaseSHAPExplainer):
    def __init__(self,model,feature_names,output_dir="reports/shap"):
        super().__init__(model,feature_names,output_dir)
        self.explainer = shap.TreeExplainer(model)

    def compute_shap_values(self, X):
        self.shap_values = self.explainer.shap_values(X)
        return self.shap_values

class DeepSHAPExplainer(BaseSHAPExplainer):
    def __init__(self,model,feature_names,background_data,output_dir="reports/shap"):
        super().__init__(model,feature_names,output_dir)
        self.background_data = background_data

    def compute_shap_values(self, X):
        try:
            self.explainer = shap.DeepExplainer(self.model, self.background_data)
        except Exception:
            self.explainer = shap.GradientExplainer(self.model, self.background_data)

        self.shap_values = self.explainer.shap_values(X)
        return self.shap_values

class KernelSHAPExplainer(BaseSHAPExplainer):
    def __init__(self,model,feature_names,background_data,output_dir="reports/shap"):
        super().__init__(model,feature_names,output_dir)
        self.background_data = background_data
    def compute_shap_values( self, X):
        self.explainer = shap.KernelExplainer(self.model.predict,self.background_data)
        values = self.explainer.shap_values(X)
        self.shap_values = values
        self.shap_values = shap.Explanation(values=values,data=X,feature_names=self.feature_names)
        return self.shap_values

class SHAPExplainerFactory:
    @staticmethod
    def create(model, feature_names, background_data=None):
        tree_classes = []
        try:
            from sklearn.tree import DecisionTreeClassifier
            tree_classes.append(DecisionTreeClassifier)
        except ImportError:
            pass
        try:
            from sklearn.ensemble import RandomForestClassifier
            tree_classes.append(RandomForestClassifier)
        except ImportError:
            pass
        try:
            from xgboost import XGBClassifier
            tree_classes.append(XGBClassifier)
        except ImportError:
            pass
        try:
            from catboost import CatBoostClassifier
            tree_classes.append(CatBoostClassifier)
        except ImportError:
            pass

        if tree_classes and isinstance(model, tuple(tree_classes)):
            return TreeSHAPExplainer(model, feature_names)

        is_keras = False
        try:
            import tensorflow as tf
            if isinstance(model, tf.keras.Model):
                is_keras = True
        except ImportError:
            pass

        if is_keras and background_data is not None:
            return DeepSHAPExplainer(model, feature_names, background_data)
        else:
            return KernelSHAPExplainer(model, feature_names, background_data)
        

        