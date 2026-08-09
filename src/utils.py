"""
===========================================================
Utility Module
===========================================================

Author : Anurag Kashyap

Contains helper functions used across the project.

Features
--------
✔ Random Seed
✔ Logging
✔ Directory Creation
✔ Save / Load Models
✔ Save Figures
✔ Timer Decorator
✔ Memory Usage
✔ Dataset Information

===========================================================
"""

import os
import random
import logging
import joblib
import time
from pathlib import Path

import numpy as np
try:
    import tensorflow as tf
except ImportError:
    tf = None
import matplotlib.pyplot as plt


# ==========================================================
# Logger
# ==========================================================

def setup_logger():

    logger = logging.getLogger("CreditRisk")

    logger.setLevel(logging.INFO)

    if not logger.handlers:

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        console = logging.StreamHandler()
        console.setFormatter(formatter)

        logger.addHandler(console)

    return logger


logger = setup_logger()


# ==========================================================
# Random Seed
# ==========================================================

def set_seed(seed=42):

    """
    Set random seed for reproducibility.
    """

    random.seed(seed)

    np.random.seed(seed)

    if tf is not None:
        tf.random.set_seed(seed)

    os.environ["PYTHONHASHSEED"] = str(seed)

    logger.info(f"Random Seed set to {seed}")


# ==========================================================
# Directory Creation
# ==========================================================

def create_directory(path):

    """
    Create directory if it doesn't exist.
    """

    Path(path).mkdir(
        parents=True,
        exist_ok=True
    )


# ==========================================================
# Save Model
# ==========================================================

def save_model(model,
               filepath):

    """
    Save sklearn model.
    """

    create_directory(
        Path(filepath).parent
    )

    joblib.dump(
        model,
        filepath
    )

    logger.info(
        f"Model saved -> {filepath}"
    )


# ==========================================================
# Load Model
# ==========================================================

def load_model(filepath):

    """
    Load saved model.
    """

    logger.info(
        f"Loading model {filepath}"
    )

    return joblib.load(filepath)


# ==========================================================
# Save Keras Model
# ==========================================================

def save_dl_model(model,
                  filepath):

    create_directory(
        Path(filepath).parent
    )

    model.save(filepath)

    logger.info(
        f"Deep Learning model saved -> {filepath}"
    )


# ==========================================================
# Load Keras Model
# ==========================================================

def load_dl_model(filepath):
    global tf
    if tf is None:
        import tensorflow as tf
    return tf.keras.models.load_model(filepath)


# ==========================================================
# Save Figure
# ==========================================================

def save_figure(fig,
                filepath,
                dpi=300):

    create_directory(
        Path(filepath).parent
    )

    fig.savefig(
        filepath,
        dpi=dpi,
        bbox_inches="tight"
    )

    logger.info(
        f"Figure saved -> {filepath}"
    )


# ==========================================================
# Timer Decorator
# ==========================================================

def timer(func):

    """
    Measure execution time.
    """

    def wrapper(*args,
                **kwargs):

        start = time.time()

        result = func(
            *args,
            **kwargs
        )

        end = time.time()

        logger.info(
            f"{func.__name__} executed in {end-start:.2f} sec"
        )

        return result

    return wrapper


# ==========================================================
# Memory Usage
# ==========================================================

def memory_usage(df):

    memory = (
        df.memory_usage(deep=True)
        .sum()
        / 1024**2
    )

    print("="*60)
    print("Memory Usage")
    print("="*60)
    print(f"{memory:.2f} MB")


# ==========================================================
# Dataset Information
# ==========================================================

def dataset_info(df):

    print("="*60)

    print("Dataset Shape")

    print("="*60)

    print(df.shape)

    print()

    print("="*60)

    print("Missing Values")

    print("="*60)

    print(df.isnull().sum().sort_values(
        ascending=False
    ).head(20))

    print()

    print("="*60)

    print("Data Types")

    print("="*60)

    print(df.dtypes.value_counts())


# ==========================================================
# Model Size
# ==========================================================

def model_size(filepath):

    size = os.path.getsize(filepath)

    size = size / (1024*1024)

    print(f"Model Size : {size:.2f} MB")