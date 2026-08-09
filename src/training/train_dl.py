"""Reusable training orchestration for TensorFlow/Keras models."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import tensorflow as tf

from src.config import (
    DATA_DIR,
    DEEP_LEARNING_TRAINING,
    EARLY_STOPPING,
    MODEL_DIR,
    RANDOM_STATE,
    REPORT_DIR,
)
from src.evaluate import evaluate_model
from src.models.neural_network import NeuralNetworkModel


logger = logging.getLogger(__name__)


class DeepLearningTrainer:
    """Orchestrate reusable neural-network training on processed datasets.

    The trainer owns data loading, callbacks, model lifecycle, evaluation, and
    artifact persistence. Network architecture remains exclusively inside
    :class:`src.models.neural_network.NeuralNetworkModel`.

    Args:
        training_config: Optional values that override the centralized deep
            learning configuration.
        train_path: Optional processed training dataset path.
        test_path: Optional processed test dataset path.
    """

    def __init__(
        self,
        training_config: Mapping[str, Any] | None = None,
        train_path: str | Path | None = None,
        test_path: str | Path | None = None,
    ) -> None:
        """Initialize the trainer and resolve artifact locations."""
        self.config = {**DEEP_LEARNING_TRAINING, **dict(training_config or {})}
        self.train_path = Path(
            train_path or DATA_DIR / self.config["train_filename"]
        )
        self.test_path = Path(test_path or DATA_DIR / self.config["test_filename"])
        self.target_column = self.config["target_column"]

        self.model_path = MODEL_DIR / self.config["model_filename"]
        self.metrics_path = REPORT_DIR / self.config["metrics_filename"]
        self.history_path = REPORT_DIR / self.config["history_filename"]

        self.model: NeuralNetworkModel | None = None
        self.history: tf.keras.callbacks.History | None = None
        self.callbacks: list[tf.keras.callbacks.Callback] = []
        self.metrics: dict[str, Any] = {}
        self.X_train: np.ndarray | None = None
        self.y_train: np.ndarray | None = None
        self.X_test: np.ndarray | None = None
        self.y_test: np.ndarray | None = None

    def load_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Load processed train/test matrices and validate their shared schema."""
        if not self.train_path.exists():
            raise FileNotFoundError(f"Training data not found: {self.train_path}")
        if not self.test_path.exists():
            raise FileNotFoundError(f"Test data not found: {self.test_path}")

        train_frame = pd.read_parquet(self.train_path)
        test_frame = pd.read_parquet(self.test_path)
        if self.target_column not in train_frame.columns:
            raise ValueError(
                f"Missing target column in training data: {self.target_column}"
            )
        if self.target_column not in test_frame.columns:
            raise ValueError(
                f"Missing target column in test data: {self.target_column}"
            )

        train_features = train_frame.drop(columns=self.target_column)
        test_features = test_frame.drop(columns=self.target_column)
        if list(train_features.columns) != list(test_features.columns):
            raise ValueError("Processed train and test feature schemas do not match.")

        X_train = train_features.to_numpy(dtype=np.float32)
        y_train = train_frame[self.target_column].to_numpy(dtype=np.int32)
        X_test = test_features.to_numpy(dtype=np.float32)
        y_test = test_frame[self.target_column].to_numpy(dtype=np.int32)

        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test

        logger.info(
            "Loaded processed data: train=%s, test=%s.",
            X_train.shape,
            X_test.shape,
        )
        return X_train, y_train, X_test, y_test

    def build_model(self) -> NeuralNetworkModel:
        """Build the reusable neural-network wrapper from configured settings."""
        if self.X_train is None:
            raise RuntimeError("Load data before building the model.")

        self.model = NeuralNetworkModel(
            input_dim=self.X_train.shape[1],
            hidden_layers=self.config["hidden_layers"],
            units=self.config["units"],
            dropout=self.config["dropout"],
            optimizer=self.config["optimizer"],
            learning_rate=self.config["learning_rate"],
            hidden_activation=self.config["hidden_activation"],
            output_activation=self.config["output_activation"],
            loss=self.config["loss"],
            metrics=self.config["metrics"],
            random_state=RANDOM_STATE,
        )
        logger.info("Built reusable neural-network model.")
        return self.model

    def create_callbacks(self) -> list[tf.keras.callbacks.Callback]:
        """Create configured early-stop, learning-rate, and checkpoint callbacks."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        monitor = EARLY_STOPPING["monitor"]
        mode = EARLY_STOPPING["mode"]
        self.callbacks = [
            tf.keras.callbacks.EarlyStopping(**EARLY_STOPPING),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor=monitor,
                mode=mode,
                factor=self.config["reduce_lr_factor"],
                patience=self.config["reduce_lr_patience"],
                min_lr=self.config["reduce_lr_min_lr"],
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath=self.model_path,
                monitor=monitor,
                mode=mode,
                save_best_only=True,
                save_weights_only=False,
            ),
        ]
        logger.info("Created %s training callbacks.", len(self.callbacks))
        return self.callbacks

    def train(self) -> tf.keras.callbacks.History:
        """Train the built model and retain the returned Keras history."""
        if self.model is None:
            raise RuntimeError("Build the model before training.")
        if self.X_train is None or self.y_train is None:
            raise RuntimeError("Load data before training.")
        if not self.callbacks:
            self.create_callbacks()

        self.history = self.model.train(
            self.X_train,
            self.y_train,
            validation_split=self.config["validation_split"],
            epochs=self.config["epochs"],
            batch_size=self.config["batch_size"],
            callbacks=self.callbacks,
            verbose=self.config["verbose"],
        )
        if not self.model_path.exists():
            raise RuntimeError(
                "ModelCheckpoint did not produce a Keras model artifact."
            )
        self.model.load(self.model_path)
        logger.info("Completed neural-network training.")
        return self.history

    def evaluate(self) -> dict[str, Any]:
        """Evaluate the trained model with Keras and shared project metrics."""
        if self.model is None:
            raise RuntimeError("Build the model before evaluation.")
        if self.X_test is None or self.y_test is None:
            raise RuntimeError("Load data before evaluation.")

        self.metrics = {
            "keras": self.model.evaluate(self.X_test, self.y_test),
            "classification": evaluate_model(
                self.model,
                self.X_test,
                self.y_test,
                plot=False,
            ),
        }
        logger.info("Evaluated neural network on the processed test set.")
        return self.metrics

    def predict(self, features: np.ndarray | None = None) -> np.ndarray:
        """Return binary predictions for supplied features or the loaded test set."""
        if self.model is None:
            raise RuntimeError("Build the model before predicting.")
        prediction_features = self.X_test if features is None else features
        if prediction_features is None:
            raise RuntimeError("Load data or provide features before predicting.")
        return self.model.predict(prediction_features)

    def save_model(self) -> Path:
        """Persist the trained model in the configured native Keras format."""
        if self.model is None:
            raise RuntimeError("Build the model before saving it.")
        self.model.save(self.model_path)
        logger.info("Saved trained neural network to %s.", self.model_path)
        return self.model_path

    def save_metrics(self) -> tuple[Path, Path]:
        """Persist evaluation metrics as JSON and training history as CSV."""
        if not self.metrics:
            raise RuntimeError("Evaluate the model before saving metrics.")
        if self.history is None:
            raise RuntimeError("Train the model before saving history.")

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        with self.metrics_path.open("w", encoding="utf-8") as metrics_file:
            json.dump(self.metrics, metrics_file, indent=2)
        pd.DataFrame(self.history.history).to_csv(self.history_path, index=False)
        logger.info(
            "Saved training metrics to %s and history to %s.",
            self.metrics_path,
            self.history_path,
        )
        return self.metrics_path, self.history_path

    def run(self) -> dict[str, Any]:
        """Execute the complete load, train, evaluate, and persistence workflow."""
        self.load_data()
        self.build_model()
        self.create_callbacks()
        self.train()
        evaluation_metrics = self.evaluate()
        model_path = self.save_model()
        metrics_path, history_path = self.save_metrics()

        return {
            "model": self.model,
            "metrics": evaluation_metrics,
            "history": self.history.history if self.history is not None else {},
            "artifacts": {
                "model": model_path,
                "metrics": metrics_path,
                "history": history_path,
            },
        }
