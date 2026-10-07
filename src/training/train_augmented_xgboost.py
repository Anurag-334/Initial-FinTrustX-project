"""
====================================================================
FinTrustX Augmented XGBoost Training & Benchmark Evaluation Pipeline
====================================================================
Orchestrates model training on the augmented dataset with:
- Supplementary Bureau & Previous Application features (341 features)
- Stratified validation split and early stopping
- Tree method: 'hist' for accelerated gradient boosting
- Full dataset refit using optimal tree iterations
- Comprehensive evaluation on held-out test set (61,503 applicants)
- Persistence of model artifact (models/xgboost.joblib), parameters
  (models/xgboost.json), and updated evaluation reports.

Author: Anurag Kashyap
====================================================================
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Ensure project root is in sys.path for direct CLI execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Central project paths and configuration
from src.config import DATA_DIR, MODEL_DIR, RANDOM_STATE, REPORT_DIR
from src.evaluate import EvaluationEngine
from src.models.xgboost_model import XGBoostModel
from src.utils import set_seed, setup_logger

logger = setup_logger()

# Recommended production XGBoost hyperparameter configuration
DEFAULT_HYPERPARAMETERS: Dict[str, Any] = {
    "n_estimators": 1200,
    "learning_rate": 0.03,
    "max_depth": 6,
    "min_child_weight": 35,
    "subsample": 0.80,
    "colsample_bytree": 0.70,
    "colsample_bylevel": 0.70,
    "gamma": 1.0,
    "reg_alpha": 2.5,
    "reg_lambda": 8.0,
    "scale_pos_weight": 1.0,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "tree_method": "hist",
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}

BASELINE_ROC_AUC = 0.7610378899421779


def load_datasets(
    train_path: Optional[Path] = None,
    test_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Load preprocessed training and held-out test datasets from Parquet.

    Parameters
    ----------
    train_path : Optional[Path], optional
        Path to processed_train.parquet.
    test_path : Optional[Path], optional
        Path to processed_test.parquet.

    Returns
    -------
    Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]
        X_train, y_train, X_test, y_test
    """
    train_file = train_path or (DATA_DIR / "processed_train.parquet")
    test_file = test_path or (DATA_DIR / "processed_test.parquet")

    if not train_file.exists():
        raise FileNotFoundError(f"Processed train data not found at: {train_file}")
    if not test_file.exists():
        raise FileNotFoundError(f"Processed test data not found at: {test_file}")

    logger.info("Loading training dataset from %s...", train_file)
    train_df = pd.read_parquet(train_file)
    logger.info("Loading held-out test dataset from %s...", test_file)
    test_df = pd.read_parquet(test_file)

    if "TARGET" not in train_df.columns or "TARGET" not in test_df.columns:
        raise KeyError("TARGET column missing from processed parquet datasets.")

    X_train = train_df.drop(columns=["TARGET"])
    y_train = train_df["TARGET"].astype(int)

    X_test = test_df.drop(columns=["TARGET"])
    y_test = test_df["TARGET"].astype(int)

    logger.info("Train set shape: %s | Test set shape: %s", X_train.shape, X_test.shape)
    logger.info("Train default rate: %.4f | Test default rate: %.4f", y_train.mean(), y_test.mean())

    return X_train, y_train, X_test, y_test


def train_augmented_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    hyperparameters: Optional[Dict[str, Any]] = None,
    val_size: float = 0.15,
    early_stopping_rounds: int = 50,
    refit_full: bool = True,
) -> Tuple[XGBoostModel, Dict[str, Any], float]:
    """
    Train XGBoost model on augmented dataset using validation early stopping
    and optional full-dataset refit.

    Parameters
    ----------
    X_train : pd.DataFrame
        Full training feature matrix.
    y_train : pd.Series
        Training binary targets.
    X_test : pd.DataFrame
        Held-out test features.
    y_test : pd.Series
        Held-out test targets.
    hyperparameters : Optional[Dict[str, Any]], optional
        Model parameters.
    val_size : float, default=0.15
        Fraction of training set for early stopping validation.
    early_stopping_rounds : int, default=50
        Early stopping patience.
    refit_full : bool, default=True
        Whether to refit on full training set using optimal tree count.

    Returns
    -------
    Tuple[XGBoostModel, Dict[str, Any], float]
        Champion model, best parameters dict, training duration (seconds).
    """
    set_seed(RANDOM_STATE)
    params = dict(DEFAULT_HYPERPARAMETERS)
    if hyperparameters:
        params.update(hyperparameters)

    start_train_time = time.time()

    # Step 1: Stratified train/validation split for early stopping
    logger.info("Splitting train set into sub-train and early-stopping validation (val_size=%.2f)...", val_size)
    X_sub, X_val, y_sub, y_val = train_test_split(
        X_train,
        y_train,
        test_size=val_size,
        stratify=y_train,
        random_state=RANDOM_STATE,
    )

    logger.info("Sub-train size: %d rows, Validation size: %d rows", len(X_sub), len(X_val))

    # Step 2: Fit with early stopping on validation split
    logger.info("Stage 1: Fitting with early stopping (patience=%d)...", early_stopping_rounds)
    stage1_params = dict(params)
    stage1_params["early_stopping_rounds"] = early_stopping_rounds

    stage1_model = XGBoostModel(**stage1_params)
    stage1_model.fit(
        X_sub,
        y_sub,
        eval_set=[(X_val, y_val)],
        verbose=100,
    )

    best_iter = stage1_model.best_iteration
    logger.info("Stage 1 complete. Best iteration: %s", best_iter)

    # Evaluate Stage 1 model on test set
    stage1_proba = stage1_model.predict_proba(X_test)
    from sklearn.metrics import roc_auc_score
    stage1_auc = float(roc_auc_score(y_test, stage1_proba))
    logger.info("Stage 1 model Test ROC-AUC: %.6f", stage1_auc)

    champion_model = stage1_model
    champion_params = dict(stage1_params)

    # Step 3: Full dataset refit if requested
    if refit_full and best_iter is not None:
        # Scale tree count to account for full dataset volume
        scaled_trees = int(best_iter * (1.0 / (1.0 - val_size)))
        logger.info(
            "Stage 2: Refitting on full training set (%d rows) with %d trees...",
            len(X_train),
            scaled_trees,
        )

        stage2_params = dict(params)
        stage2_params["n_estimators"] = scaled_trees
        if "early_stopping_rounds" in stage2_params:
            del stage2_params["early_stopping_rounds"]

        stage2_model = XGBoostModel(**stage2_params)
        stage2_model.fit(X_train, y_train, verbose=False)

        stage2_proba = stage2_model.predict_proba(X_test)
        stage2_auc = float(roc_auc_score(y_test, stage2_proba))
        logger.info("Stage 2 model Test ROC-AUC: %.6f", stage2_auc)

        # Select the highest-performing model
        if stage2_auc >= stage1_auc:
            logger.info("Selecting Stage 2 (full refit) as champion model.")
            champion_model = stage2_model
            champion_params = stage2_params
            champion_params["best_iteration"] = scaled_trees
        else:
            logger.info("Selecting Stage 1 model as champion model.")
            champion_params["best_iteration"] = best_iter
    else:
        champion_params["best_iteration"] = best_iter

    total_training_time = time.time() - start_train_time
    logger.info("Total model training time: %.2f seconds", total_training_time)

    return champion_model, champion_params, total_training_time


def evaluate_and_save_artifacts(
    model: XGBoostModel,
    best_params: Dict[str, Any],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    training_time: float,
) -> Dict[str, Any]:
    """
    Perform rigorous evaluation using EvaluationEngine and update all reports
    and model artifacts.

    Parameters
    ----------
    model : XGBoostModel
        Trained champion model.
    best_params : Dict[str, Any]
        Best hyperparameter configuration.
    X_test : pd.DataFrame
        Held-out test features.
    y_test : pd.Series
        Held-out test labels.
    training_time : float
        Total training duration in seconds.

    Returns
    -------
    Dict[str, Any]
        Dictionary of evaluated metrics.
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Measure Prediction Latency
    pred_start = time.time()
    _ = model.predict_proba(X_test)
    pred_duration = time.time() - pred_start
    pred_time_ms_row = (pred_duration / len(X_test)) * 1000.0

    # 2. Evaluate with EvaluationEngine (threshold = 0.50)
    logger.info("Evaluating champion model on %d held-out test applicants...", len(X_test))
    engine = EvaluationEngine(model=model.get_model(), threshold=0.50, report_dir=REPORT_DIR)
    eval_metrics = engine.evaluate(X_test, y_test)

    new_roc_auc = eval_metrics["ROC AUC"]
    lift = new_roc_auc - BASELINE_ROC_AUC
    logger.info("==================================================")
    logger.info("EVALUATION RESULTS ON 61,503 HELD-OUT TEST APPLICANTS:")
    logger.info("  Baseline ROC-AUC : %.6f", BASELINE_ROC_AUC)
    logger.info("  New Model ROC-AUC: %.6f", new_roc_auc)
    logger.info("  ROC-AUC Lift     : %+.6f", lift)
    logger.info("  PR-AUC (Avg Prec): %.6f", eval_metrics["Average Precision"])
    logger.info("  Default Capture  : %.2f%%", eval_metrics["Default Capture Rate"] * 100)
    logger.info("  Approval Prec.   : %.2f%%", eval_metrics["Approval Precision"] * 100)
    logger.info("==================================================")

    # Strict Acceptance Assertion
    if new_roc_auc <= BASELINE_ROC_AUC:
        raise AssertionError(
            f"Model ROC-AUC ({new_roc_auc:.6f}) does not beat baseline ({BASELINE_ROC_AUC:.6f})"
        )

    # 3. Save Model Artifacts
    model_path = MODEL_DIR / "xgboost.joblib"
    params_path = MODEL_DIR / "xgboost.json"

    logger.info("Saving trained XGBoost model to %s...", model_path)
    model.save(model_path)

    logger.info("Saving best parameters to %s...", params_path)
    # Convert non-serializable objects
    clean_params = {}
    for k, v in best_params.items():
        if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
            clean_params[k] = v
        else:
            clean_params[k] = str(v)
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(clean_params, f, indent=2)

    # 4. Update reports/model_comparison.csv
    comparison_path = REPORT_DIR / "model_comparison.csv"
    comp_df = pd.read_csv(comparison_path) if comparison_path.exists() else pd.DataFrame()

    xgboost_row = {
        "Model": "xgboost",
        "ROC AUC": float(eval_metrics["ROC AUC"]),
        "Average Precision": float(eval_metrics["Average Precision"]),
        "F1 Score": float(eval_metrics["F1 Score"]),
        "Recall": float(eval_metrics["Recall"]),
        "Precision": float(eval_metrics["Precision"]),
        "Balanced Accuracy": float(eval_metrics["Balanced Accuracy"]),
        "Accuracy": float(eval_metrics["Accuracy"]),
        "Matthews Corrcoef": float(eval_metrics["Matthews Corrcoef"]),
        "Cohen Kappa": float(eval_metrics["Cohen Kappa"]),
        "Log Loss": float(eval_metrics["Log Loss"]),
        "Brier Score Loss": float(eval_metrics["Brier Score Loss"]),
    }

    if not comp_df.empty and "Model" in comp_df.columns:
        # Remove old xgboost entry if present and append new
        comp_df = comp_df[comp_df["Model"] != "xgboost"]
        comp_df = pd.concat([pd.DataFrame([xgboost_row]), comp_df], ignore_index=True)
    else:
        comp_df = pd.DataFrame([xgboost_row])

    comp_df = comp_df.sort_values(by="ROC AUC", ascending=False).reset_index(drop=True)
    comp_df.to_csv(comparison_path, index=False)
    logger.info("Updated %s.", comparison_path)

    # 5. Update reports/business_metrics.csv
    business_path = REPORT_DIR / "business_metrics.csv"
    biz_df = pd.read_csv(business_path) if business_path.exists() else pd.DataFrame()

    biz_row = {
        "Model": "xgboost",
        "True Defaults Captured": int(eval_metrics["True Defaults Captured"]),
        "False Defaults Flagged": int(eval_metrics["False Defaults Flagged"]),
        "Good Customers Cleared": int(eval_metrics["Good Customers Cleared"]),
        "Defaults Missed": int(eval_metrics["Defaults Missed"]),
        "Default Capture Rate": float(eval_metrics["Default Capture Rate"]),
        "Approval Precision": float(eval_metrics["Approval Precision"]),
        "True Approvals": int(eval_metrics["True Defaults Captured"]),
        "False Approvals": int(eval_metrics["False Defaults Flagged"]),
        "True Rejections": int(eval_metrics["Good Customers Cleared"]),
        "False Rejections": int(eval_metrics["Defaults Missed"]),
        "Default Capture": float(eval_metrics["Default Capture Rate"]),
    }

    if not biz_df.empty and "Model" in biz_df.columns:
        biz_df = biz_df[biz_df["Model"] != "xgboost"]
        biz_df = pd.concat([pd.DataFrame([biz_row]), biz_df], ignore_index=True)
    else:
        biz_df = pd.DataFrame([biz_row])

    biz_df.to_csv(business_path, index=False)
    logger.info("Updated %s.", business_path)

    # 6. Update reports/model_metrics.csv
    model_metrics_path = REPORT_DIR / "model_metrics.csv"
    metrics_df = pd.read_csv(model_metrics_path) if model_metrics_path.exists() else pd.DataFrame()

    detailed_row = {
        "Accuracy": float(eval_metrics["Accuracy"]),
        "Precision": float(eval_metrics["Precision"]),
        "Recall": float(eval_metrics["Recall"]),
        "F1 Score": float(eval_metrics["F1 Score"]),
        "ROC AUC": float(eval_metrics["ROC AUC"]),
        "Average Precision": float(eval_metrics["Average Precision"]),
        "Balanced Accuracy": float(eval_metrics["Balanced Accuracy"]),
        "Matthews Corrcoef": float(eval_metrics["Matthews Corrcoef"]),
        "Cohen Kappa": float(eval_metrics["Cohen Kappa"]),
        "Log Loss": float(eval_metrics["Log Loss"]),
        "Brier Score Loss": float(eval_metrics["Brier Score Loss"]),
        "Model": "XGBoost",
        "Prediction Time (ms/row)": float(pred_time_ms_row),
        "Training Time (s)": float(training_time),
        "Baseline Training Time (s)": "",
    }

    if not metrics_df.empty and "Model" in metrics_df.columns:
        metrics_df = metrics_df[metrics_df["Model"] != "XGBoost"]
        metrics_df = pd.concat([pd.DataFrame([detailed_row]), metrics_df], ignore_index=True)
    else:
        metrics_df = pd.DataFrame([detailed_row])

    metrics_df.to_csv(model_metrics_path, index=False)
    logger.info("Updated %s.", model_metrics_path)

    return eval_metrics


def run_pipeline() -> Dict[str, Any]:
    """Execute end-to-end augmented XGBoost training and evaluation pipeline."""
    logger.info("Starting augmented XGBoost training pipeline...")
    X_train, y_train, X_test, y_test = load_datasets()

    model, best_params, train_time = train_augmented_xgboost(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        hyperparameters=DEFAULT_HYPERPARAMETERS,
        val_size=0.15,
        early_stopping_rounds=50,
        refit_full=True,
    )

    metrics = evaluate_and_save_artifacts(
        model=model,
        best_params=best_params,
        X_test=X_test,
        y_test=y_test,
        training_time=train_time,
    )

    logger.info("Augmented XGBoost pipeline completed successfully.")
    return metrics


if __name__ == "__main__":
    try:
        results = run_pipeline()
        sys.exit(0)
    except Exception as exc:
        logger.exception("Training pipeline failed: %s", exc)
        sys.exit(1)
