"""
=========================================================
Utility Functions for Hyperparameter Optimization

Contains helper functions used across the tuning
framework.

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

from pathlib import Path
import json
import random
import time
import os

import joblib
import numpy as np
import optuna
import tensorflow as tf


class TuningUtils:

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Reproducibility / filesystem
    # ------------------------------------------------------------------
    @staticmethod
    def set_random_seed(seed=42):
        random.seed(seed)
        np.random.seed(seed)
        tf.random.set_seed(seed)
        os.environ["PYTHONHASHSEED"] = str(seed)

    @staticmethod
    def create_directory(path):
        Path(path).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------
    @staticmethod
    def save_json(data, filepath):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_json(filepath):
        with open(filepath) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Joblib (sklearn / XGBoost / CatBoost-style models)
    # ------------------------------------------------------------------
    @staticmethod
    def save_joblib(model, filepath):
        joblib.dump(model, filepath)

    @staticmethod
    def load_joblib(filepath):
        return joblib.load(filepath)

    # ------------------------------------------------------------------
    # Keras models
    # ------------------------------------------------------------------
    @staticmethod
    def save_keras_model(model, filepath):
        model.save(filepath)

    @staticmethod
    def load_keras_model(filepath):
        return tf.keras.models.load_model(filepath)

    # ------------------------------------------------------------------
    # Optuna studies
    # ------------------------------------------------------------------
    @staticmethod
    def save_study(study, filepath):
        """
        Persists an Optuna study (all trials, params, and metadata) to
        disk with joblib, since Study objects are picklable. This lets
        you reload a finished study later to regenerate plots or resume
        `.optimize()` without rerunning trials from scratch.
        """
        joblib.dump(study, filepath)

    @staticmethod
    def load_study(filepath):
        return joblib.load(filepath)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    @staticmethod
    def timer(start):
        return time.time() - start

    @staticmethod
    def print_best_trial(study):
        print("=" * 50)
        print("Best Trial")
        print("=" * 50)
        print(f"Trial Number : {study.best_trial.number}")
        print(f"Best Score   : {study.best_value:.5f}")
        print()
        print("Parameters")

        for key, value in study.best_params.items():
            print(f"{key:<25}: {value}")