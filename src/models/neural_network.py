"""Reusable TensorFlow/Keras neural-network model wrapper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import tensorflow as tf

from .base_model import BaseModel


logger = logging.getLogger(__name__)


class NeuralNetworkModel(BaseModel):
    """Configurable feed-forward neural network for binary classification.

    The class deliberately accepts arrays or data frames without making any
    assumptions about feature names, preprocessing, or dataset splits. When
    ``input_dim`` is omitted, the network is built automatically the first
    time ``train`` is called.

    Args:
        input_dim: Number of input features. If omitted, infer it at training.
        hidden_layers: Number of dense hidden layers.
        units: Units per hidden layer, as one integer or one value per layer.
        dropout: Dropout rate, as one float or one value per hidden layer.
        optimizer: Keras optimizer name or optimizer instance.
        learning_rate: Learning rate applied to the selected optimizer.
        hidden_activation: Activation name, or one value per hidden layer.
        output_activation: Activation for the binary output layer.
        loss: Keras loss used during compilation.
        metrics: Metrics tracked during training and evaluation.
        random_state: Optional random seed for reproducible Keras execution.
    """

    def __init__(
        self,
        input_dim: int | None = None,
        hidden_layers: int = 2,
        units: int | Sequence[int] = 64,
        dropout: float | Sequence[float] = 0.2,
        optimizer: str | tf.keras.optimizers.Optimizer = "adam",
        learning_rate: float = 1e-3,
        hidden_activation: str | Sequence[str] = "relu",
        output_activation: str = "sigmoid",
        loss: str | tf.keras.losses.Loss = "binary_crossentropy",
        metrics: Sequence[str | tf.keras.metrics.Metric] = ("accuracy",),
        random_state: int | None = None,
    ) -> None:
        """Initialize the model configuration without dataset-specific state."""
        super().__init__("Neural Network")

        if input_dim is not None and input_dim <= 0:
            raise ValueError("input_dim must be a positive integer.")
        if hidden_layers <= 0:
            raise ValueError("hidden_layers must be at least 1.")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be greater than zero.")

        self.input_dim = input_dim
        self.hidden_layers = hidden_layers
        self.units = self._expand_parameter(units, "units", int)
        self.dropout = self._expand_parameter(dropout, "dropout", float)
        self.hidden_activation = self._expand_parameter(
            hidden_activation,
            "hidden_activation",
            str,
        )
        self.optimizer = optimizer
        self.learning_rate = learning_rate
        self.output_activation = output_activation
        self.loss = loss
        self.metrics = list(metrics)
        self.random_state = random_state
        self._is_compiled = False
        self.model: tf.keras.Model | None = None

        if any(rate < 0 or rate >= 1 for rate in self.dropout):
            raise ValueError("Each dropout rate must be in the range [0, 1).")

        if random_state is not None:
            tf.random.set_seed(random_state)

        if self.input_dim is not None:
            self.build_model()
            self.compile()

    def _expand_parameter(
        self,
        value: int | float | str | Sequence[Any],
        parameter_name: str,
        expected_type: type,
    ) -> list[Any]:
        """Normalize a scalar or per-layer value into a layer-aligned list."""
        if isinstance(value, Sequence) and not isinstance(value, str):
            values = list(value)
            if len(values) != self.hidden_layers:
                raise ValueError(
                    f"{parameter_name} must contain {self.hidden_layers} values."
                )
        else:
            values = [value] * self.hidden_layers

        if not all(isinstance(item, expected_type) for item in values):
            raise TypeError(
                f"{parameter_name} values must be of type {expected_type.__name__}."
            )
        return values

    def _set_input_dim(self, features: Any) -> None:
        """Infer and validate the feature width from an array-like input."""
        shape = getattr(features, "shape", None)
        if shape is None or len(shape) != 2 or shape[1] is None:
            raise ValueError("features must be a two-dimensional array-like object.")

        feature_count = int(shape[1])
        if self.input_dim is None:
            self.input_dim = feature_count
            self.build_model()
            self.compile()
        elif self.input_dim != feature_count:
            raise ValueError(
                f"Expected {self.input_dim} input features, received {feature_count}."
            )

    def build_model(self) -> tf.keras.Model:
        """Build and return the configured Keras model architecture."""
        if self.input_dim is None:
            raise ValueError("input_dim is required before building the model.")

        inputs = tf.keras.Input(shape=(self.input_dim,), name="features")
        outputs = inputs
        for layer_index in range(self.hidden_layers):
            outputs = tf.keras.layers.Dense(
                units=self.units[layer_index],
                activation=self.hidden_activation[layer_index],
                name=f"hidden_{layer_index + 1}",
            )(outputs)
            if self.dropout[layer_index] > 0:
                outputs = tf.keras.layers.Dropout(
                    rate=self.dropout[layer_index],
                    name=f"dropout_{layer_index + 1}",
                )(outputs)

        outputs = tf.keras.layers.Dense(
            units=1,
            activation=self.output_activation,
            name="default_probability",
        )(outputs)
        self.model = tf.keras.Model(
            inputs=inputs,
            outputs=outputs,
            name="neural_network",
        )
        self._is_compiled = False
        logger.info("Built neural network with %s hidden layers.", self.hidden_layers)
        return self.model

    def compile(self) -> None:
        """Compile the Keras model with the configured optimizer and loss."""
        if self.model is None:
            raise ValueError("Build the model before compiling it.")

        optimizer = tf.keras.optimizers.get(self.optimizer)
        optimizer.learning_rate = self.learning_rate
        self.model.compile(optimizer=optimizer, loss=self.loss, metrics=self.metrics)
        self._is_compiled = True
        logger.info("Compiled neural network with optimizer %s.", optimizer.name)

    def train(
        self,
        X_train: Any,
        y_train: Any,
        validation_data: tuple[Any, Any] | None = None,
        validation_split: float = 0.0,
        epochs: int = 100,
        batch_size: int = 32,
        callbacks: Sequence[tf.keras.callbacks.Callback] | None = None,
        verbose: int = 0,
        **fit_kwargs: Any,
    ) -> tf.keras.callbacks.History:
        """Fit the model and return its Keras training history."""
        if epochs <= 0:
            raise ValueError("epochs must be greater than zero.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")
        if not 0 <= validation_split < 1:
            raise ValueError("validation_split must be in the range [0, 1).")

        self._set_input_dim(X_train)
        if validation_data is not None:
            self._set_input_dim(validation_data[0])
        if not self._is_compiled:
            self.compile()

        logger.info("Training neural network for up to %s epochs.", epochs)
        return self.model.fit(
            X_train,
            y_train,
            validation_data=validation_data,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=list(callbacks or []),
            verbose=verbose,
            **fit_kwargs,
        )

    def fit(
        self,
        X_train: Any,
        y_train: Any,
        **kwargs: Any,
    ) -> tf.keras.callbacks.History:
        """Provide a BaseModel-compatible alias for :meth:`train`."""
        return self.train(X_train, y_train, **kwargs)

    def predict_proba(
        self,
        X: Any,
        batch_size: int | None = None,
        verbose: int = 0,
    ) -> np.ndarray:
        """Return two-column probabilities for the negative and positive classes."""
        self._set_input_dim(X)
        probabilities = self.model.predict(X, batch_size=batch_size, verbose=verbose)
        positive_probability = np.asarray(probabilities).reshape(-1)
        return np.column_stack((1.0 - positive_probability, positive_probability))

    def predict(
        self,
        X: Any,
        threshold: float = 0.5,
        batch_size: int | None = None,
        verbose: int = 0,
    ) -> np.ndarray:
        """Return binary class predictions using the supplied probability threshold."""
        if not 0 < threshold < 1:
            raise ValueError("threshold must be in the range (0, 1).")
        probabilities = self.predict_proba(X, batch_size=batch_size, verbose=verbose)
        return (probabilities[:, 1] >= threshold).astype(int)

    def evaluate(
        self,
        X: Any,
        y: Any,
        batch_size: int | None = None,
        verbose: int = 0,
        **kwargs: Any,
    ) -> dict[str, float]:
        """Evaluate the model and return named metric values."""
        self._set_input_dim(X)
        if not self._is_compiled:
            self.compile()
        results = self.model.evaluate(
            X,
            y,
            batch_size=batch_size,
            verbose=verbose,
            return_dict=True,
            **kwargs,
        )
        return {name: float(value) for name, value in results.items()}

    def save(self, path: str | Path) -> None:
        """Save the model in the native Keras ``.keras`` format."""
        if self.model is None:
            raise ValueError("Build or train the model before saving it.")

        model_path = Path(path)
        if model_path.suffix != ".keras":
            raise ValueError(
                "Neural-network models must be saved with a .keras suffix."
            )
        model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(model_path)
        logger.info("Saved neural network to %s.", model_path)

    def load(self, path: str | Path) -> None:
        """Load a previously saved native Keras model."""
        model_path = Path(path)
        if model_path.suffix != ".keras":
            raise ValueError("Neural-network models must use a .keras suffix.")
        if not model_path.exists():
            raise FileNotFoundError(f"Model file does not exist: {model_path}")

        self.model = tf.keras.models.load_model(model_path)
        input_shape = self.model.input_shape
        self.input_dim = int(input_shape[-1])
        self._is_compiled = self.model.optimizer is not None
        logger.info("Loaded neural network from %s.", model_path)

    def summary(self) -> None:
        """Log the Keras architecture summary without writing directly to stdout."""
        if self.model is None:
            raise ValueError("Build or load the model before requesting a summary.")
        self.model.summary(print_fn=logger.info)
