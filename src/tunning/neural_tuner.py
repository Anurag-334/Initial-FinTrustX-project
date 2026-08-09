from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from sklearn.metrics import roc_auc_score
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

from src.config import (
    DEEP_LEARNING_TRAINING,
    EARLY_STOPPING,
    NEURAL_NETWORK_SPACE,
    RANDOM_STATE,
    STUDY_DIR,
)
from src.models.neural_network import NeuralNetworkModel
from src.tunning.base_tuner import BaseTuner

logger = logging.getLogger(__name__)


class NeuralNetworkTuner(BaseTuner):
    """
    Optuna tuner for the reusable NeuralNetworkModel.

    Uses the project search space in NEURAL_NETWORK_SPACE and creates
    a persistent SQLite study under STUDY_DIR.
    """

    def __init__(
        self,
        random_state: int = RANDOM_STATE,
        study_name: str = "neural_network",
    ) -> None:
        super().__init__(random_state=random_state)
        self.study_name = study_name
        self.study_path = Path(STUDY_DIR) / f"{study_name}.db"
        self.study: Optional[optuna.study.Study] = None
        self.best_params: Dict[str, Any] = {}
        self.best_value: Optional[float] = None
        self.best_trial: Optional[optuna.trial.FrozenTrial] = None
        tf.random.set_seed(self.random_state)

    def _storage_url(self) -> str:
        self.study_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.study_path.as_posix()}"

    def _synchronize_best_results(self, study: optuna.study.Study) -> None:
        """Synchronize Optuna's best trial with the base-tuner state."""
        self.best_trial = study.best_trial
        self.best_params = study.best_params
        self.best_score = study.best_value
        self.best_value = study.best_value

    @staticmethod
    def _suggest_trial_value(
        trial: optuna.trial.Trial,
        name: str,
        space: Union[Sequence[Any], Tuple[Any, Any]],
    ) -> Any:
        if (
            isinstance(space, (list, tuple))
            and len(space) == 2
            and not isinstance(space[0], str)
        ):
            low, high = space
            if isinstance(low, int) and isinstance(high, int):
                return trial.suggest_int(name, low, high)
            if isinstance(low, float) and isinstance(high, float):
                return trial.suggest_float(name, low, high, log=(name == "learning_rate"))
        return trial.suggest_categorical(name, list(space))

    @staticmethod
    def _metrics() -> list[str]:
        """Return configured metrics while guaranteeing a metric named ``auc``."""
        metrics = list(DEEP_LEARNING_TRAINING["metrics"])
        if "auc" not in metrics:
            metrics.append("auc")
        return metrics

    def _build_model(
        self,
        trial: optuna.trial.Trial,
        input_dim: int,
    ) -> NeuralNetworkModel:
        layers = self._suggest_trial_value(
            trial, "layers", NEURAL_NETWORK_SPACE["layers"]
        )
        units = self._suggest_trial_value(
            trial, "units", NEURAL_NETWORK_SPACE["units"]
        )
        dropout = self._suggest_trial_value(
            trial, "dropout", NEURAL_NETWORK_SPACE["dropout"]
        )
        learning_rate = self._suggest_trial_value(
            trial,
            "learning_rate",
            NEURAL_NETWORK_SPACE["learning_rate"],
        )
        optimizer = self._suggest_trial_value(
            trial, "optimizer", NEURAL_NETWORK_SPACE["optimizer"]
        )

        model_kwargs: Dict[str, Any] = {
            "input_dim": input_dim,
            "hidden_layers": layers,
            "units": units,
            "dropout": dropout,
            "optimizer": optimizer,
            "learning_rate": learning_rate,
            "hidden_activation": DEEP_LEARNING_TRAINING["hidden_activation"],
            "output_activation": DEEP_LEARNING_TRAINING["output_activation"],
            "loss": DEEP_LEARNING_TRAINING["loss"],
            "metrics": self._metrics(),
            "random_state": self.random_state,
        }

        model = NeuralNetworkModel(**model_kwargs)
        logger.debug(
            "Created new NeuralNetworkModel for trial %s: %s",
            trial.number,
            model_kwargs,
        )
        return model

    def _early_stopping(self) -> EarlyStopping:
        early_stopping_params = dict(EARLY_STOPPING)
        early_stopping_params.setdefault("monitor", "val_auc")
        if "mode" not in early_stopping_params:
            if "loss" in early_stopping_params["monitor"]:
                early_stopping_params["mode"] = "min"
            else:
                early_stopping_params["mode"] = "max"
        early_stopping_params.setdefault("restore_best_weights", True)
        return EarlyStopping(**early_stopping_params)

    def _callbacks(self, trial: optuna.trial.Trial) -> list[tf.keras.callbacks.Callback]:
        class OptunaPruningCallback(tf.keras.callbacks.Callback):
            def __init__(self, trial_to_use: optuna.trial.Trial) -> None:
                super().__init__()
                self._trial = trial_to_use

            def on_epoch_end(self, epoch: int, logs=None) -> None:
                if not logs:
                    return
                if "val_auc" not in logs:
                    return
                value = float(logs["val_auc"])
                self._trial.report(value, step=epoch)
                if self._trial.should_prune():
                    raise optuna.TrialPruned()

        return [
            self._early_stopping(),
            ReduceLROnPlateau(
                monitor=EARLY_STOPPING["monitor"],
                mode=EARLY_STOPPING["mode"],
                factor=DEEP_LEARNING_TRAINING["reduce_lr_factor"],
                patience=DEEP_LEARNING_TRAINING["reduce_lr_patience"],
                min_lr=DEEP_LEARNING_TRAINING["reduce_lr_min_lr"],
                verbose=0,
            ),
            OptunaPruningCallback(trial),
        ]

    def _objective(
        self,
        trial: optuna.trial.Trial,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: np.ndarray,
        y_valid: np.ndarray,
    ) -> float:
        model = self._build_model(trial, X_train.shape[1])

        batch_size = self._suggest_trial_value(
            trial, "batch_size", NEURAL_NETWORK_SPACE["batch_size"]
        )

        model.fit(
            X_train,
            y_train,
            validation_data=(X_valid, y_valid),
            epochs=DEEP_LEARNING_TRAINING["epochs"],
            batch_size=batch_size,
            callbacks=self._callbacks(trial),
            verbose=0,
        )

        probabilities = model.predict_proba(X_valid)
        auc = float(roc_auc_score(y_valid, probabilities[:, 1]))
        logger.debug("Trial %s validation ROC-AUC: %.5f", trial.number, auc)
        return auc

    def create_study(self) -> optuna.study.Study:
        storage = self._storage_url()
        self.study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=self.random_state),
            pruner=MedianPruner(),
            storage=storage,
            study_name=self.study_name,
            load_if_exists=True,
        )
        completed_trials = any(
            trial.state == optuna.trial.TrialState.COMPLETE
            for trial in self.study.trials
        )
        if completed_trials:
            self._synchronize_best_results(self.study)
        logger.debug("Created or loaded study %s at %s", self.study_name, storage)
        return self.study

    def load_study(self) -> optuna.study.Study:
        storage = self._storage_url()
        self.study = optuna.load_study(study_name=self.study_name, storage=storage)
        self._synchronize_best_results(self.study)
        logger.debug("Loaded study %s from %s", self.study_name, storage)
        return self.study

    def save_study(self) -> None:
        if self.study is None:
            raise ValueError("No study available to save.")
        logger.debug("Study %s persisted to %s", self.study_name, self._storage_url())

    def optimize(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: np.ndarray,
        y_valid: np.ndarray,
        n_trials: int = 30,
        timeout: Optional[float] = None,
    ) -> optuna.study.Study:
        study = self.study or self.create_study()
        study.optimize(
            lambda trial: self._objective(trial, X_train, y_train, X_valid, y_valid),
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
        )

        self.study = study
        self._synchronize_best_results(study)
        logger.info(
            "Finished optimization for %s: best_value=%s best_params=%s",
            self.study_name,
            self.best_value,
            self.best_params,
        )
        return study

    def get_best_params(self) -> Any:
        if self.best_params:
            return self.best_params
        if self.study is not None:
            return self.study.best_params
        raise ValueError("No study has been optimized or loaded yet.")
