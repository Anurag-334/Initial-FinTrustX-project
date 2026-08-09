"""
===========================================================
Base Tuner
===========================================================

Common functionality used by every hyperparameter tuner.

Author : Anurag Kashyap
===========================================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna

from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score
)

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s"

)

logger = logging.getLogger(__name__)

class BaseTuner:
    def __init__(

        self,

        random_state: int = 42,

        cv: int = 5,

        metric: str = "roc_auc",

        study_dir="studies",

        model_dir="models"

     ):
        self.random_state = random_state

        self.cv = cv
        self.metric = metric
        self.study = None
        self.best_model = None
        self.best_params = None
        self.best_score = None
        self.study_dir = Path(study_dir)
        self.model_dir = Path(model_dir)

        self.study_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def _create_study(
        self,
        study_name,
        direction="maximize"
    ):
        storage = f"sqlite:///{self.study_dir}/{study_name}.db"
        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            load_if_exists=True,
            direction=direction,
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
            pruner=optuna.pruners.MedianPruner(),
        )
        return self.study

    def _cross_validation(
        self,
        model,
        X,
        y
    ):
        cv = StratifiedKFold(
            n_splits=self.cv,
            shuffle=True,
            random_state=self.random_state
        )
        scores = cross_val_score(
            estimator=model,
            X=X,
            y=y,
            scoring=self.metric,
            cv=cv,
            n_jobs=-1,
        )
        return np.mean(scores)

    def _save_model(
        self,
        model,
        filename
    ):
        path = self.model_dir / filename
        joblib.dump(model, path)

    def _save_parameters(
        self,
        filename
    ):
        """Save best_params to a json file in model_dir."""
        path = self.model_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.best_params or {}, f, indent=2)

    def summary(self):

     print("=" * 60)

     print("Optimization Summary")

     print("=" * 60)

     print()

     print("Best Score")

     print(self.best_score)

     print()

     print("Best Parameters")

     print(self.best_params)

    def get_best_model(self):

       return self.best_model

    def get_best_params(self):

      return self.best_params
    def get_best_score(self):

      return self.best_score    