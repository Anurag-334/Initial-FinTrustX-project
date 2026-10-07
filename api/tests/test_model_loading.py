"""
=========================================================
Unit Tests: Model Loader & Artifact Validation
=========================================================
"""

import pytest
from pathlib import Path
from api.model_loader import ModelLoader, get_model_loader
from api.config import XGBOOST_MODEL_PATH, PREPROCESSING_PIPELINE_PATH


def test_model_files_exist():
    """Verify that required model artifacts exist on disk."""
    assert XGBOOST_MODEL_PATH.exists(), f"Missing {XGBOOST_MODEL_PATH}"
    assert PREPROCESSING_PIPELINE_PATH.exists(), f"Missing {PREPROCESSING_PIPELINE_PATH}"


def test_model_loader_singleton():
    """Verify that ModelLoader operates as a singleton and caches artifacts."""
    loader1 = get_model_loader()
    loader2 = ModelLoader()
    assert loader1 is loader2

    loader1.load_artifacts()
    assert loader1.is_loaded is True
    assert loader1.model is not None
    assert loader1.pipeline is not None
    assert len(loader1.raw_feature_names) == 121
    assert len(loader1.feature_names) == 245


def test_smoke_test_execution():
    """Verify that internal smoke test passes on valid synthetic input."""
    loader = get_model_loader()
    loader.load_artifacts()
    assert loader.run_smoke_test() is True
