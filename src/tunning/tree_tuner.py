"""
===========================================================
Tree Tuner
===========================================================

Hyperparameter optimization for tree-based models.

Models
------
1. Decision Tree
2. Random Forest

Author : Anurag Kashyap
===========================================================
"""

from __future__ import annotations

import optuna

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from src.tunning.base_tuner import BaseTuner


class TreeTuner(BaseTuner):

    def __init__(
        self,
        random_state: int = 42,
        cv: int = 5,
        metric: str = "roc_auc",
        study_dir: str = "studies",
        model_dir: str = "models"
    ):

        super().__init__(
            random_state=random_state,
            cv=cv,
            metric=metric,
            study_dir=study_dir,
            model_dir=model_dir
        )

    ####################################################################
    # Decision Tree
    ####################################################################

    def tune_decision_tree(
        self,
        X,
        y,
        n_trials: int = 20
    ):

        study = self._create_study("decision_tree")

        def objective(trial):

            params = {

                "criterion":
                    trial.suggest_categorical(
                        "criterion",
                        ["gini", "entropy", "log_loss"]
                    ),

                "max_depth":
                    trial.suggest_int(
                        "max_depth",
                        3,
                        25
                    ),

                "min_samples_split":
                    trial.suggest_int(
                        "min_samples_split",
                        2,
                        20
                    ),

                "min_samples_leaf":
                    trial.suggest_int(
                        "min_samples_leaf",
                        1,
                        10
                    ),

                "max_features":
                    trial.suggest_categorical(
                        "max_features",
                        ["sqrt", "log2", None]
                    ),

                "class_weight":
                    "balanced",

                "random_state":
                    self.random_state

            }

            model = DecisionTreeClassifier(**params)

            return float(self._cross_validation(
                model,
                X,
                y
            ))

        study.optimize(
             objective,
            n_trials=n_trials,
            show_progress_bar=True
        )

        self.best_params = study.best_params
        self.best_score = study.best_value

        self.best_model = DecisionTreeClassifier(

            **self.best_params,

            class_weight="balanced",

            random_state=self.random_state

        )

        self.best_model.fit(X, y)

        self._save_model(
            self.best_model,
            "decision_tree.joblib"
        )

        self._save_parameters(
            "decision_tree.json"
        )

        return self.best_model

    ####################################################################
    # Random Forest
    ####################################################################

    def tune_random_forest(
        self,
        X,
        y,
        n_trials: int = 40
    ):

        study = self._create_study("random_forest")

        def objective(trial):

            params = {

                "n_estimators":
                    trial.suggest_int(
                        "n_estimators",
                        100,
                        600
                    ),

                "max_depth":
                    trial.suggest_int(
                        "max_depth",
                        4,
                        30
                    ),

                "min_samples_split":
                    trial.suggest_int(
                        "min_samples_split",
                        2,
                        20
                    ),

                "min_samples_leaf":
                    trial.suggest_int(
                        "min_samples_leaf",
                        1,
                        10
                    ),

                "max_features":
                    trial.suggest_categorical(
                        "max_features",
                        ["sqrt", "log2", None]
                    ),

                "bootstrap":
                    trial.suggest_categorical(
                        "bootstrap",
                        [True, False]
                    ),

                "class_weight":
                    "balanced",

                "random_state":
                    self.random_state,

                "n_jobs":
                    -1

            }

            model = RandomForestClassifier(**params)

            return float(self._cross_validation(
                model,
                X,
                y
            ))

        study.optimize(
            objective,
            n_trials=n_trials,
            show_progress_bar=True
        )

        self.best_params = study.best_params
        self.best_score = study.best_value

        self.best_model = RandomForestClassifier(

            **self.best_params,

            class_weight="balanced",

            random_state=self.random_state,

            n_jobs=-1

        )

        self.best_model.fit(X, y)

        self._save_model(
            self.best_model,
            "random_forest.joblib"
        )

        self._save_parameters(
            "random_forest.json"
        )

        return self.best_model