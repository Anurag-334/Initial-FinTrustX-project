"""
=========================================================
Integrated Gradients Explainer

TensorFlow implementation of Integrated Gradients
for Neural Networks.

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
try:
    import tensorflow as tf
except ImportError:
    tf = None

from src.explainability.base_explainer import BaseExplainer

logger = logging.getLogger(__name__)

class IntegratedGradientsExplainer(BaseExplainer):
    """
    Integrated Gradients for TensorFlow models.
    """
    def __init__(self,model: tf.keras.Model,output_dir: str = "reports/explainability",):
        super().__init__( output_dir=output_dir)
        self.model = model  
        logger.info("Integrated Gradients Explainer initialized.")

    def interpolate_inputs(self,baseline,input_tensor,steps: int = 50,):
        alphas = tf.linspace(0.0, 1.0, steps + 1)

        interpolated = [baseline + alpha * (input_tensor - baseline) for alpha in alphas]
        return tf.stack(interpolated)

    def compute_gradients(self,interpolated_inputs: tf.Tensor,target_class_idx: int | None = None,) -> tf.Tensor:
        """
        Compute gradients of the model output with respect to
        the interpolated inputs.

        Parameters
        ----------
        interpolated_inputs : tf.Tensor
        Interpolated samples.

        target_class_idx : int, optional
        Target class index.

        Returns
        -------
        tf.Tensor
        Computed gradients.
        """
        with tf.GradientTape() as tape:
            tape.watch(interpolated_inputs)
            predictions = self.model(interpolated_inputs,training=False,)

            if target_class_idx is None:
                outputs = predictions[:, 0]

            else:
                outputs = predictions[:, target_class_idx]

        gradients = tape.gradient(outputs,interpolated_inputs,)

        return tf.convert_to_tensor(gradients)
    def explain(self,input_data: pd.DataFrame,baseline: pd.DataFrame | None = None,steps: int = 50,) -> pd.DataFrame:
        """
        Generate Integrated Gradients attribution scores.

        Parameters
        ----------
        input_data : pd.DataFrame
        Input sample.

        baseline : pd.DataFrame, optional
        Baseline sample.

        steps : int
        Number of interpolation steps.

        Returns
        -------
        pd.DataFrame
        Feature attribution scores.
        """
        logger.info("Generating Integrated Gradients...")
        input_tensor = tf.cast(input_data.values,tf.float32,)
        if baseline is None:
            baseline_tensor = tf.zeros_like(input_tensor)
        else:
            baseline_tensor = tf.cast(baseline.values,tf.float32,)
        interpolated_inputs = self.interpolate_inputs(baseline_tensor,input_tensor,steps,)
        gradients = self.compute_gradients(interpolated_inputs,)
        avg_gradients = tf.reduce_mean(gradients,axis=0)
        integrated_gradients = (input_tensor - baseline_tensor) * avg_gradients
        importance = pd.DataFrame({"Feature": input_data.columns,"Importance": integrated_gradients.numpy()[0]})
        importance = importance.sort_values(by="Importance",ascending=False,)
        logger.info("Integrated Gradients completed.")
        return importance
    def visualize(self,importance: pd.DataFrame,top_n: int = 10,) -> None:
        """
        Visualize the top feature importances.

        Parameters
        ----------
        importance : pd.DataFrame
        Output from explain().

        top_n : int
        Number of top features to display.
        """

        logger.info("Visualizing Integrated Gradients...")

        data = importance.head(top_n)

        plt.figure(figsize=(10, 6))

        plt.barh(data["Feature"],data["Importance"],)

        plt.xlabel("Integrated Gradient")

        plt.ylabel("Feature")

        plt.title("Integrated Gradients Feature Importance")

        plt.gca().invert_yaxis()

        plt.tight_layout()

        plt.show()
    def save_csv(self,importance: pd.DataFrame,filename: str = "integrated_gradients.csv",):
        """
        Save feature importance to CSV.

        Parameters
        ----------
        importance : pd.DataFrame
        Output from explain().

        filename : str
        CSV filename.

        Returns
        -------
        Path
        Path to the saved CSV file.

        Notes
        -----
        Save feature importance to CSV.
        """

        path = self.output_dir / filename

        importance.to_csv(path,index=False,)

        logger.info(f"Saved CSV: {path}")

        return path
    def save_json(self,importance: pd.DataFrame,filename: str = "integrated_gradients.json",):
        """
        Save feature importance to JSON.

        Parameters
        ----------
        importance : pd.DataFrame
        Output from explain().

        filename : str
        JSON filename.

        Returns
        -------
        Path
        Path to the saved JSON file.

        Notes
        -----
        """
        path = self.output_dir / filename

        importance.to_json(path,orient="records",indent=4,)

        logger.info(f"Saved JSON: {path}")

        return path
    def summary(self,importance: pd.DataFrame,top_n: int = 10,) -> dict:
        """
        Generate a summary of feature importance.

        Parameters
        ----------
        importance : pd.DataFrame
        Output from explain().

        top_n : int
        Number of top features to include in the summary.

        Returns
        -------
        dict
        Summary of feature importance.
        """

        logger.info("Generating Integrated Gradients summary...")

        top_features = importance.head(top_n)

        return {
            "method": "Integrated Gradients",
            "total_features": len(importance),
            "top_features": top_features.to_dict(
                orient="records"
            ),
        }
