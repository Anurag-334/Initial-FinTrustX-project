"""Reusable evaluation utilities for binary classification models."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, TypeAlias, runtime_checkable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from src.config import EVALUATION_REPORTS, REPORT_DIR

logger = logging.getLogger(__name__)

ArrayLike: TypeAlias = Any
MetricValue: TypeAlias = float | int
MetricsMapping: TypeAlias = Mapping[str, MetricValue]
EvaluationOutcome: TypeAlias = dict[str, MetricValue]


@runtime_checkable
class BinaryClassifier(Protocol):
    """Protocol for estimators compatible with the evaluation utilities."""

    def predict(self, X: Any, **kwargs: Any) -> Any:
        ...

    def predict_proba(self, X: Any, **kwargs: Any) -> Any:
        ...


class EvaluationEngine:
    """Evaluate, visualize, compare, and persist binary classifier results.

    The engine is estimator-agnostic. It only requires that the supplied model
    implements ``predict`` and ``predict_proba``. The latter may return either
    one-dimensional positive-class probabilities or the conventional two-column
    probability matrix.
    """

    def __init__(
        self,
        model: BinaryClassifier | None = None,
        threshold: float = 0.5,
        report_dir: str | Path = REPORT_DIR,
    ) -> None:
        if not 0 < threshold < 1:
            raise ValueError("threshold must be in the range (0, 1).")

        self.model = model
        self.threshold = threshold
        self.report_dir = Path(report_dir)

        logger.debug(
            "Initialized EvaluationEngine(threshold=%s, report_dir=%s)",
            threshold,
            self.report_dir,
        )

    @staticmethod
    def _get_positive_class_probability(model: Any, features: Any) -> np.ndarray:
        """Extract positive class probabilities from any model (sklearn, XGBoost, CatBoost, Keras, BaseModel)."""
        if hasattr(model, "predict_proba"):
            raw_proba = model.predict_proba(features)
        elif hasattr(model, "predict"):
            # Raw Keras model or estimator with only predict
            is_keras = "keras" in type(model).__module__.lower() or "tensorflow" in type(model).__module__.lower()
            raw_proba = model.predict(features, verbose=0) if is_keras else model.predict(features)
        else:
            raise TypeError("Model must implement predict_proba() or predict().")

        array = np.asarray(raw_proba)
        if array.ndim == 1:
            positive_probability = array
        elif array.ndim == 2 and array.shape[1] == 1:
            positive_probability = array[:, 0]
        elif array.ndim == 2 and array.shape[1] >= 2:
            positive_probability = array[:, 1]
        else:
            raise ValueError("Model predictions must return a 1D or 2D array.")

        positive_probability = positive_probability.astype(float).reshape(-1)
        if np.any(np.isnan(positive_probability)) or np.any(np.isinf(positive_probability)):
            raise ValueError("Predicted probabilities contain NaN or Inf values.")

        return positive_probability

    @staticmethod
    def _as_binary_array(values: Any, name: str) -> np.ndarray:
        array = np.asarray(values).reshape(-1)
        unique_values = set(np.unique(array))
        if not unique_values.issubset({0, 1}):
            raise ValueError(f"{name} must contain binary labels encoded as 0 and 1.")
        return array.astype(int)

    @staticmethod
    def _positive_probabilities(probabilities: Any) -> np.ndarray:
        array = np.asarray(probabilities)

        if array.ndim == 1:
            positive_probability = array
        elif array.ndim == 2 and array.shape[1] == 1:
            positive_probability = array[:, 0]
        elif array.ndim == 2 and array.shape[1] >= 2:
            positive_probability = array[:, 1]
        else:
            raise ValueError("predict_proba must return one or two-dimensional output.")

        if np.any((positive_probability < 0) | (positive_probability > 1)):
            raise ValueError("Predicted probabilities must be in the range [0, 1].")

        return positive_probability.astype(float).reshape(-1)

    @staticmethod
    def _validate_length_equal(*arrays: Any, names: Sequence[str]) -> None:
        lengths = [np.asarray(array).reshape(-1).shape[0] for array in arrays]
        if len(set(lengths)) != 1:
            joined = ", ".join(
                f"{name}={length}" for name, length in zip(names, lengths)
            )
            raise ValueError(f"All inputs must have equal lengths: {joined}")

    def _require_model(self, model: Any | None = None) -> Any:
        estimator = self.model if model is None else model
        if estimator is None:
            raise ValueError("A model is required for this operation.")
        if not hasattr(estimator, "predict") and not hasattr(estimator, "predict_proba"):
            raise TypeError("Model must implement predict() or predict_proba().")
        return estimator

    def _prediction_outputs(
        self,
        features: Any,
        model: Any | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        estimator = self._require_model(model)
        probabilities = self._get_positive_class_probability(estimator, features)
        predictions = (probabilities >= self.threshold).astype(int)
        logger.debug("Generated prediction outputs for %s samples.", probabilities.shape[0])
        return predictions, probabilities

    def classification_metrics(
        self,
        y_true: Any,
        y_pred: Any,
        y_proba: Any,
    ) -> EvaluationOutcome:
        labels = self._as_binary_array(y_true, "y_true")
        predictions = self._as_binary_array(y_pred, "y_pred")
        probabilities = self._positive_probabilities(y_proba)
        self._validate_length_equal(
            labels,
            predictions,
            probabilities,
            names=["y_true", "y_pred", "y_proba"],
        )

        metrics = {
            "Accuracy": float(accuracy_score(labels, predictions)),
            "Precision": float(precision_score(labels, predictions, zero_division=0)),
            "Recall": float(recall_score(labels, predictions, zero_division=0)),
            "F1 Score": float(f1_score(labels, predictions, zero_division=0)),
            "ROC AUC": float(roc_auc_score(labels, probabilities)),
            "Average Precision": float(average_precision_score(labels, probabilities)),
            "Balanced Accuracy": float(
                balanced_accuracy_score(labels, predictions)
            ),
            "Matthews Corrcoef": float(
                matthews_corrcoef(labels, predictions)
            ),
            "Cohen Kappa": float(cohen_kappa_score(labels, predictions)),
            "Log Loss": float(log_loss(labels, probabilities, labels=[0, 1])),
            "Brier Score Loss": float(brier_score_loss(labels, probabilities)),
        }

        logger.debug("Computed classification metrics: %s", metrics)
        return metrics

    def business_metrics(self, y_true: Any, y_pred: Any) -> dict[str, float | int]:
        labels = self._as_binary_array(y_true, "y_true")
        predictions = self._as_binary_array(y_pred, "y_pred")
        self._validate_length_equal(labels, predictions, names=["y_true", "y_pred"])

        tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()

        approval_precision = tp / (tp + fp) if tp + fp else 0.0
        default_capture_rate = tp / (tp + fn) if tp + fn else 0.0

        metrics = {
            "True Defaults Captured": int(tp),
            "False Defaults Flagged": int(fp),
            "Good Customers Cleared": int(tn),
            "Defaults Missed": int(fn),
            "Default Capture Rate": float(default_capture_rate),
            "Approval Precision": float(approval_precision),
            # Backwards compatibility keys
            "True Approvals": int(tp),
            "False Approvals": int(fp),
            "True Rejections": int(tn),
            "False Rejections": int(fn),
            "Default Capture": float(default_capture_rate),
        }

        logger.debug("Computed business metrics: %s", metrics)
        return metrics

    def evaluate(
        self,
        features: Any,
        y_true: Any,
        model: Any | None = None,
    ) -> dict[str, float | int]:
        predictions, probabilities = self._prediction_outputs(features, model)
        metrics = self.classification_metrics(y_true, predictions, probabilities)
        metrics.update(self.business_metrics(y_true, predictions))

        logger.info("Evaluated binary classification model on %s rows.", len(predictions))
        return metrics

    def plot_confusion_matrix(
        self,
        features: Any,
        y_true: Any,
        model: Any | None = None,
        ax: Axes | None = None,
        title: str = "Confusion Matrix",
    ) -> Axes:
        predictions, _ = self._prediction_outputs(features, model)
        labels = self._as_binary_array(y_true, "y_true")
        axis = ax or plt.subplots(figsize=(6, 5))[1]
        ConfusionMatrixDisplay.from_predictions(
            labels,
            predictions,
            display_labels=["Negative", "Positive"],
            cmap="Blues",
            colorbar=False,
            ax=axis,
        )
        axis.set_title(title)
        axis.set_xlabel("Predicted label")
        axis.set_ylabel("Actual label")
        axis.grid(False)
        logger.debug("Rendered confusion matrix.")
        return axis

    def plot_roc_curve(
        self,
        features: Any,
        y_true: Any,
        model: Any | None = None,
        ax: Axes | None = None,
        title: str = "ROC Curve",
    ) -> Axes:
        _, probabilities = self._prediction_outputs(features, model)
        labels = self._as_binary_array(y_true, "y_true")
        fpr, tpr, _ = roc_curve(labels, probabilities)
        score = roc_auc_score(labels, probabilities)
        axis = ax or plt.subplots(figsize=(7, 5))[1]
        axis.plot(fpr, tpr, label=f"Model (AUC = {score:.3f})", linewidth=2)
        axis.plot([0, 1], [0, 1], "--", color="grey", label="No skill")
        axis.set_title(title)
        axis.set_xlabel("False Positive Rate")
        axis.set_ylabel("True Positive Rate")
        axis.grid(True, alpha=0.3)
        axis.legend(loc="lower right")
        logger.debug("Rendered ROC curve with AUC=%s.", score)
        return axis

    def plot_precision_recall_curve(
        self,
        features: Any,
        y_true: Any,
        model: Any | None = None,
        ax: Axes | None = None,
        title: str = "Precision-Recall Curve",
    ) -> Axes:
        _, probabilities = self._prediction_outputs(features, model)
        labels = self._as_binary_array(y_true, "y_true")
        precision, recall, _ = precision_recall_curve(labels, probabilities)
        score = average_precision_score(labels, probabilities)
        axis = ax or plt.subplots(figsize=(7, 5))[1]
        axis.plot(recall, precision, label=f"Model (AP = {score:.3f})", linewidth=2)
        axis.axhline(labels.mean(), linestyle="--", color="grey", label="Baseline")
        axis.set_title(title)
        axis.set_xlabel("Recall")
        axis.set_ylabel("Precision")
        axis.grid(True, alpha=0.3)
        axis.legend(loc="lower left")
        logger.debug("Rendered precision-recall curve with AP=%s.", score)
        return axis

    @staticmethod
    def compare_models(
        results: Sequence[Mapping[str, Any]] | pd.DataFrame,
        metric: str = "ROC AUC",
    ) -> pd.DataFrame:
        comparison = pd.DataFrame(results).copy()
        if metric not in comparison.columns:
            raise ValueError(f"Comparison metric not found: {metric}")
        sorted_df = comparison.sort_values(metric, ascending=False).reset_index(drop=True)
        logger.debug("Compared models by metric=%s.", metric)
        return sorted_df

    def save_metrics(
        self,
        metrics: Mapping[str, Any] | None = None,
        comparison: pd.DataFrame | None = None,
        metrics_path: str | Path | None = None,
        comparison_path: str | Path | None = None,
    ) -> dict[str, Path]:
        if metrics is None and comparison is None:
            raise ValueError("Provide metrics, a comparison table, or both.")

        self.report_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: dict[str, Path] = {}

        if metrics is not None:
            target = (
                Path(metrics_path)
                if metrics_path is not None
                else self.report_dir / EVALUATION_REPORTS["metrics_filename"]
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as metrics_file:
                json.dump(dict(metrics), metrics_file, indent=2)
            saved_paths["metrics"] = target

        if comparison is not None:
            target = (
                Path(comparison_path)
                if comparison_path is not None
                else self.report_dir / EVALUATION_REPORTS["comparison_filename"]
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            comparison.to_csv(target, index=False)
            saved_paths["comparison"] = target

        logger.info("Saved evaluation artifacts: %s", saved_paths)
        return saved_paths

    @staticmethod
    def summary(metrics: Mapping[str, Any]) -> str:
        if not metrics:
            raise ValueError("Metrics cannot be empty.")
        lines = ["Evaluation Summary"]
        for name, value in metrics.items():
            if isinstance(value, (float, np.floating)):
                lines.append(f"{name}: {value:.4f}")
            else:
                lines.append(f"{name}: {value}")
        report = "\n".join(lines)
        logger.info("%s", report)
        return report


def evaluate_model(
    model: Any,
    X_test: Any,
    y_test: Any,
    threshold: float = 0.5,
    plot: bool = True,
) -> dict[str, float | int]:
    engine = EvaluationEngine(model=model, threshold=threshold)
    metrics = engine.evaluate(X_test, y_test)
    if plot:
        engine.plot_confusion_matrix(X_test, y_test)
        engine.plot_roc_curve(X_test, y_test)
        engine.plot_precision_recall_curve(X_test, y_test)
        plt.show()
    return metrics


def plot_roc(model: Any, X_test: Any, y_test: Any) -> Axes:
    return EvaluationEngine(model=model).plot_roc_curve(X_test, y_test)


def plot_precision_recall(model: Any, X_test: Any, y_test: Any) -> Axes:
    return EvaluationEngine(model=model).plot_precision_recall_curve(X_test, y_test)


def plot_confusion_matrix(model: Any, X_test: Any, y_test: Any) -> Axes:
    return EvaluationEngine(model=model).plot_confusion_matrix(X_test, y_test)


def business_metrics(y_true: Any, y_pred: Any) -> dict[str, float | int]:
    return EvaluationEngine().business_metrics(y_true, y_pred)


def compare_models(results: Sequence[Mapping[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    return EvaluationEngine.compare_models(results)


def save_results(df: pd.DataFrame) -> Path:
    path = REPORT_DIR / "model_results.csv"
    EvaluationEngine().save_metrics(comparison=df, comparison_path=path)
    return path
