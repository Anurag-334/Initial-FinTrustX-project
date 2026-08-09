"""
===========================================================
DiCE Counterfactual Explainer

Generates actionable counterfactual explanations using
DiCE (Diverse Counterfactual Explanations).

Author: Anurag Kashyap
===========================================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    import dice_ml
else:
    try:
        import dice_ml
    except ImportError:
        dice_ml = None

try:
    from tensorflow.keras import Model as KerasModel
except ImportError:
    KerasModel = None

from src.explainability.base_explainer import BaseExplainer

logger = logging.getLogger(__name__)


class DiceExplainer(BaseExplainer):
    """
    Generates counterfactual explanations using DiCE.
    """

    def __init__(
        self,
        model: Any,
        dataframe: pd.DataFrame,
        continuous_features: list[str],
        target_name: str = "TARGET",
        output_dir: str = "reports/explainability",
    ) -> None:
        super().__init__(output_dir=output_dir)

        self.model = model
        self.dataframe = dataframe
        self.continuous_features = continuous_features
        self.target_name = target_name

        self.backend = None
        self.data_interface = None
        self.model_interface = None
        self.dice: Any = None

        if self.target_name not in self.dataframe.columns:
            raise ValueError(
                f"Target column '{self.target_name}' not found in dataframe."
            )

        if len(self.continuous_features) == 0:
            raise ValueError("continuous_features cannot be empty.")

        if self.dataframe.empty:
            raise ValueError("Training dataframe is empty.")

        if dice_ml is None:
            raise ImportError(
                "dice-ml is required for DiCE explainability. Install it with 'pip install dice-ml'."
            )

        self.backend = self._detect_backend()

        self.data_interface = self._create_data_interface()

        self.model_interface = self._create_model_interface()

        self.dice = dice_ml.Dice(
            self.data_interface,
            self.model_interface,
        )

    def _detect_backend(self) -> str:
        if KerasModel is not None and isinstance(self.model, KerasModel):
            logger.info("TensorFlow backend detected.")
            return "TF2"

        logger.info("Scikit-Learn backend detected.")
        return "sklearn"

    def _create_data_interface(self) -> dice_ml.Data:
        logger.info("Creating DiCE data interface...")

        return dice_ml.Data(
            dataframe=self.dataframe,
            continuous_features=self.continuous_features,
            outcome_name=self.target_name,
        )

    def _create_model_interface(self) -> dice_ml.Model:
        logger.info("Creating DiCE model interface...")

        return dice_ml.Model(
            model=self.model,
            backend=self.backend, # pyright: ignore[reportArgumentType]
        )
    def load_constraints(self,immutable_features: list[str] | None = None,permitted_range: dict[str, list] | None = None,) -> None:
        """
        Load feature constraints for counterfactual generation.

        Parameters
        ----------
        immutable_features : list[str], optional
        Features that should never be modified.

        permitted_range : dict, optional
        Allowed range for continuous features.
        """

        self.immutable_features = immutable_features or []
        self.permitted_range = permitted_range or {}

        logger.info("Constraints loaded successfully.")

    def generate_counterfactuals(
        self,
        query_instance: pd.DataFrame,
        total_cfs: int = 5,
        desired_class: str = "opposite",
        features_to_vary: str = "all",
    ):
        """
        Generate counterfactual explanations.

        Parameters
        ----------
        query_instance : pd.DataFrame
        Single input sample.

        total_cfs : int
        Number of counterfactuals.

        desired_class : str
        Desired prediction class.

        features_to_vary : str | list
        Features allowed to change.
        """
        logger.info("Generating counterfactual explanations...")

        if self.dice is None:
            raise RuntimeError("DiCE explainer has not been initialized.")

        counterfactuals = self.dice.generate_counterfactuals(
            query_instances=query_instance,
            total_CFs=total_cfs,
            desired_class=desired_class,
            features_to_vary=features_to_vary,
            permitted_range=getattr(self, "permitted_range", None),
        )

        logger.info("Counterfactual generation completed.")

        return counterfactuals
    def visualize(self,counterfactuals,show_only_changes: bool = True,) -> None:
        """
        Display generated counterfactual explanations.

        Parameters
        ----------
        counterfactuals
        DiCE generated counterfactual object.

        show_only_changes : bool, default=True
        Show only changed features.
         """

        logger.info("Visualizing counterfactual explanations...")

        counterfactuals.visualize_as_dataframe(
        show_only_changes=show_only_changes)

    def save_csv(self,counterfactuals,filename: str = "counterfactuals.csv",) -> Path:
        """
        Save counterfactual explanations as CSV.

        Parameters
        ----------
        counterfactuals
        Generated DiCE object.

        filename : str
        CSV filename.

        Returns
        -------
        Path
        Saved file path.
        """

        logger.info("Saving counterfactuals as CSV...")

        output_path = self.output_dir / filename

        df = counterfactuals.cf_examples_list[0].final_cfs_df

        df.to_csv(output_path, index=False)

        logger.info(f"Saved: {output_path}")

        return output_path
    def save_json(self,counterfactuals,filename: str = "counterfactuals.json",) -> Path:
        """
        Save counterfactual explanations as JSON.
        """

        logger.info("Saving counterfactuals as JSON...")

        output_path = self.output_dir / filename

        df = counterfactuals.cf_examples_list[0].final_cfs_df

        data = df.to_dict(orient="records")

        with open(output_path, "w", encoding="utf-8") as file:
         json.dump(data, file, indent=4)

        logger.info(f"Saved: {output_path}")

        return output_path

    def summary(self,counterfactuals,) -> dict:
        """
        Return a summary of generated counterfactuals.
        """

        df = counterfactuals.cf_examples_list[0].final_cfs_df

        summary = {
        "total_counterfactuals": len(df),
        "features": list(df.columns),
        "prediction_changed": len(df) > 0,
    }

        return summary
    

    
