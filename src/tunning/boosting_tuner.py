"""
=========================================================
Boosting Tuner
=========================================================

Generic hyperparameter optimization engine for boosting
algorithms.

Currently Supported

• XGBoost
• CatBoost

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

import numpy as np
import optuna

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

from src import config
from src.tunning.base_tuner import BaseTuner
from src.tunning.registry import MODEL_REGISTRY
from src.config import RANDOM_STATE

class BoostingTuner(BaseTuner):

    """
    Generic tuner for all boosting algorithms.
    """

    def __init__(

            self,

            random_state=RANDOM_STATE,

            cv=5,

            metric="roc_auc"

    ):

        super().__init__(

            random_state=random_state,

            cv=cv,

            metric=metric

        )
    def _build_model(self, model_name, params):
        config = MODEL_REGISTRY[model_name]
        Model = config["model"]

        if model_name == "xgboost":
            return Model(
                **params,
                objective="binary:logistic",
                eval_metric="auc",
                tree_method="hist",
                random_state=self.random_state,
                n_jobs=-1,
            )
        elif model_name == "catboost":
            return Model(
                **params,
                verbose=0,
                loss_function="Logloss",
                eval_metric="AUC",
                random_seed=self.random_state,
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}")

    def _objective(self,trial,X,y,model_name):
        config = MODEL_REGISTRY[model_name]
        space = config["space"]
        if model_name == "xgboost":
            params = {
                "n_estimators": trial.suggest_int(
                    "n_estimators", *space["n_estimators"]
                ),
                "learning_rate": trial.suggest_float(
                    "learning_rate", *space["learning_rate"], log=True
                ),
                "max_depth": trial.suggest_int(
                    "max_depth", *space["max_depth"]
                ),
                "subsample": trial.suggest_float(
                    "subsample", *space["subsample"]
                ),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree", *space["colsample_bytree"]
                ),
                "reg_alpha": trial.suggest_float(
                    "reg_alpha", *space["reg_alpha"]
                ),
                "reg_lambda": trial.suggest_float(
                    "reg_lambda", *space["reg_lambda"]
                ),
            }
        elif model_name == "catboost":
            params = {
                "iterations": trial.suggest_int(
                    "iterations", *space["iterations"]
                ),
                "learning_rate": trial.suggest_float(
                    "learning_rate", *space["learning_rate"], log=True
                ),
                "depth": trial.suggest_int("depth", *space["depth"]),
                "l2_leaf_reg": trial.suggest_float(
                    "l2_leaf_reg", *space["l2_leaf_reg"]
                ),
                "random_strength": trial.suggest_float(
                    "random_strength", *space["random_strength"]
                ),
                "bagging_temperature": trial.suggest_float(
                    "bagging_temperature", *space["bagging_temperature"]
                ),
                "border_count": trial.suggest_int(
                    "border_count", *space["border_count"]
                ),
            }
        else:
            raise ValueError(f"Unsupported model: {model_name}")

        model = self._build_model(model_name, params)

        cv = StratifiedKFold(n_splits=self.cv,shuffle=True,random_state=self.random_state)

        scores = []
        for train_idx, val_idx in cv.split(X, y):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            model.fit(X_train, y_train)

            prob = model.predict_proba( X_val)[:,1]
            auc = roc_auc_score(y_val, prob)
            scores.append(auc)

        return float(np.mean(scores))
    #####################################################################
    #Generic Optimizers
    def _optimize(self, X, y, model_name, n_trials):
        config = MODEL_REGISTRY[model_name]
        study = self._create_study(config["study"])
        study.optimize(
            lambda trial: self._objective(trial, X, y, model_name),
            n_trials=n_trials,
            show_progress_bar=True,
        )
        self.best_params = study.best_params
        self.best_score = study.best_value
        self.best_model = self._build_model(model_name, self.best_params)
        self.best_model.fit(X, y)
        self._save_model(self.best_model, config["model_file"])
        self._save_parameters(config["params_file"])

        return self.best_model

    def tune_xgboost(self,X,y,n_trials=50):

       return self._optimize(X,y,"xgboost", n_trials)

    def tune_catboost(self,X,y, n_trials=50):

     return self._optimize(X,y,"catboost",n_trials)
    
