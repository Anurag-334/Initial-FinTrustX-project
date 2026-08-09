"""
=========================================================
Project Configuration
=========================================================

Central configuration file for the Credit Risk AI Project.

Contains:
- Random Seeds
- Paths
- Model Parameters
- Hyperparameter Search Spaces
- Deep Learning Settings

Author : Anurag Kashyap
=========================================================
"""

from pathlib import Path

###############################################################
# RANDOM STATE
###############################################################

RANDOM_STATE = 42

###############################################################
# PROJECT PATHS
###############################################################

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

TARGET_COLUMN = "TARGET"
TARGET_COL = "TARGET"

MODEL_DIR = PROJECT_ROOT / "models"

REPORT_DIR = PROJECT_ROOT / "reports"

STUDY_DIR = PROJECT_ROOT / "studies"

MLFLOW_DIR = PROJECT_ROOT / "mlruns"

###############################################################
# TRAINING SETTINGS
###############################################################

N_JOBS = -1

CV_FOLDS = 5

SCORING = "roc_auc"

###############################################################
# OPTUNA SETTINGS
###############################################################

OPTUNA_SETTINGS = {

    "direction": "maximize",

    "sampler": "TPESampler",

    "pruner": "MedianPruner",

    "show_progress_bar": True

}

###############################################################
# DECISION TREE
###############################################################

DECISION_TREE_SPACE = {

    "criterion": ["gini", "entropy", "log_loss"],

    "max_depth": (3, 25),

    "min_samples_split": (2, 20),

    "min_samples_leaf": (1, 10),

    "max_features": ["sqrt", "log2", None]

}

###############################################################
# RANDOM FOREST
###############################################################

RANDOM_FOREST_SPACE = {

    "n_estimators": (100, 600),

    "max_depth": (4, 30),

    "min_samples_split": (2, 20),

    "min_samples_leaf": (1, 10),

    "max_features": ["sqrt", "log2", None],

    "bootstrap": [True, False]

}

###############################################################
# XGBOOST
###############################################################

XGBOOST_SPACE = {

    "n_estimators": (200, 1200),

    "learning_rate": (0.005, 0.30),

    "max_depth": (3, 12),

    "min_child_weight": (1, 15),

    "subsample": (0.50, 1.00),

    "colsample_bytree": (0.50, 1.00),

    "gamma": (0, 10),

    "reg_alpha": (0, 10),

    "reg_lambda": (0, 20)

}

###############################################################
# CATBOOST
###############################################################

CATBOOST_SPACE = {

    "iterations": (300, 1500),

    "learning_rate": (0.005, 0.30),

    "depth": (4, 10),

    "l2_leaf_reg": (1, 20),

    "random_strength": (0, 10),

    "bagging_temperature": (0, 5),

    "border_count": (32, 255)

}

###############################################################
# NEURAL NETWORK
###############################################################

NEURAL_NETWORK_SPACE = {

    "layers": (1, 5),

    "units": (32, 512),

    "dropout": (0.10, 0.50),

    "learning_rate": (1e-5, 1e-2),

    "batch_size": [32, 64, 128, 256],

    "optimizer": ["adam", "adamw", "nadam"]

}

###############################################################
# EARLY STOPPING
###############################################################

EARLY_STOPPING = {

    "monitor": "val_auc",

    "mode": "max",

    "patience": 10,

    "restore_best_weights": True

}

###############################################################
# MODEL FILENAMES
###############################################################

MODEL_NAMES = {

    "decision_tree": "decision_tree.joblib",

    "random_forest": "random_forest.joblib",

    "xgboost": "xgboost.joblib",

    "catboost": "catboost.joblib",

    "neural_network": "neural_network.keras"

}

###############################################################
# PARAMETER FILENAMES
###############################################################

PARAMETER_FILES = {

    "decision_tree": "decision_tree.json",

    "random_forest": "random_forest.json",

    "xgboost": "xgboost.json",

    "catboost": "catboost.json",

    "neural_network": "neural_network.json"

}

###############################################################
# STUDY NAMES
###############################################################

STUDY_NAMES = {

    "decision_tree": "decision_tree",

    "random_forest": "random_forest",

    "xgboost": "xgboost",

    "catboost": "catboost",

    "neural_network": "neural_network"

}

###############################################################
# DEEP LEARNING TRAINING
###############################################################

DEEP_LEARNING_TRAINING = {

    "train_filename": "processed_train.parquet",

    "test_filename": "processed_test.parquet",

    "target_column": "TARGET",

    "hidden_layers": 2,

    "units": 64,

    "dropout": 0.20,

    "optimizer": "adam",

    "learning_rate": 1e-3,

    "hidden_activation": "relu",

    "output_activation": "sigmoid",

    "loss": "binary_crossentropy",

    "metrics": ["accuracy", "auc"],

    "epochs": 100,

    "batch_size": 128,

    "validation_split": 0.20,

    "verbose": 0,

    "reduce_lr_factor": 0.5,

    "reduce_lr_patience": 5,

    "reduce_lr_min_lr": 1e-6,

    "model_filename": MODEL_NAMES["neural_network"],

    "metrics_filename": "neural_network_metrics.json",

    "history_filename": "neural_network_history.csv"

}

###############################################################
# EVALUATION REPORTING
###############################################################

EVALUATION_REPORTS = {

    "metrics_filename": "evaluation_metrics.json",

    "comparison_filename": "model_comparison.csv"

}
