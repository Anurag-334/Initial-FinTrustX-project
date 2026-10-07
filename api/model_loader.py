"""
=========================================================
FinTrustX API Model Loader
=========================================================
Singleton loader that initializes and manages in-memory
artifacts (XGBoost model, ColumnTransformer, Feature Names,
and static performance metadata) on API startup.

Author: Anurag Kashyap
=========================================================
"""

import logging
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import pandas as pd
import numpy as np

from api.config import (
    XGBOOST_MODEL_PATH,
    PREPROCESSING_PIPELINE_PATH,
    FEATURE_NAMES_PATH,
    METRICS_REPORT_PATH,
)

logger = logging.getLogger(__name__)

ARTIFACT_CHECKSUMS = {
    "xgboost.joblib": "5c1b8484b4f7f3ffc9f0cdd7f6f8c214474a79b1bc0c5e09414987937791cb38",
    "preprocessing_pipeline.joblib": "138366150ef4157b65f7028ca3d689e466034c749570e7ab012750f9c0de25fd",
}


class ModelLoader:
    """
    Singleton manager for loading and caching machine learning artifacts.
    Guarantees artifacts are loaded only once on application startup.
    """
    _instance: Optional["ModelLoader"] = None

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
            
        self.model: Any = None
        self.pipeline: Any = None
        self.feature_names: List[str] = []
        self.raw_feature_names: List[str] = []
        self.metrics: Dict[str, float] = {}
        self.is_loaded: bool = False
        self._initialized = True

    def _verify_artifact_integrity(self, path: Path) -> None:
        """Verify SHA-256 hash of model artifact before loading."""
        basename = path.name
        expected = ARTIFACT_CHECKSUMS.get(basename)
        if expected is None:
            logger.warning(f"No integrity hash registered for {basename}")
            return
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                sha.update(chunk)
        actual = sha.hexdigest().lower()
        if actual != expected.lower():
            raise RuntimeError(f"Integrity check FAILED for {path} (expected {expected}, got {actual})")

    def load_artifacts(self) -> None:
        """Load all model artifacts, preprocessors, and feature lists from disk."""
        logger.info("Initializing FinTrustX artifact loading...")

        # 1. Load Preprocessing Pipeline
        if not PREPROCESSING_PIPELINE_PATH.exists():
            raise FileNotFoundError(
                f"Preprocessing pipeline not found at: {PREPROCESSING_PIPELINE_PATH}"
            )
        try:
            self._verify_artifact_integrity(PREPROCESSING_PIPELINE_PATH)
            self.pipeline = joblib.load(PREPROCESSING_PIPELINE_PATH)
            logger.info("Loaded preprocessing pipeline (ColumnTransformer).")
            if hasattr(self.pipeline, "feature_names_in_"):
                self.raw_feature_names = self.pipeline.feature_names_in_.tolist()
        except Exception as e:
            logger.error(f"Failed to load preprocessing pipeline: {e}")
            raise RuntimeError(f"Could not load preprocessing pipeline: {e}") from e

        # 2. Load XGBoost Model
        if not XGBOOST_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"XGBoost model artifact not found at: {XGBOOST_MODEL_PATH}"
            )
        try:
            self._verify_artifact_integrity(XGBOOST_MODEL_PATH)
            self.model = joblib.load(XGBOOST_MODEL_PATH)
            logger.info(f"Loaded XGBoost model artifact ({type(self.model).__name__}).")
        except Exception as e:
            logger.error(f"Failed to load XGBoost model: {e}")
            raise RuntimeError(f"Could not load XGBoost model: {e}") from e

        # 3. Load Feature Names
        if FEATURE_NAMES_PATH.exists():
            try:
                feat_df = pd.read_csv(FEATURE_NAMES_PATH)
                self.feature_names = feat_df.iloc[:, 0].tolist()
                logger.info(f"Loaded {len(self.feature_names)} preprocessed feature names.")
            except Exception as e:
                logger.warning(f"Could not load feature names CSV: {e}")
                self.feature_names = [f"feature_{i}" for i in range(getattr(self.model, "n_features_in_", 245))]
        else:
            self.feature_names = [f"feature_{i}" for i in range(getattr(self.model, "n_features_in_", 245))]

        # 4. Load Static Benchmark Metrics
        if METRICS_REPORT_PATH.exists():
            try:
                metrics_df = pd.read_csv(METRICS_REPORT_PATH)
                if "Model" in metrics_df.columns:
                    metrics_df = metrics_df.set_index("Model")
                elif metrics_df.columns[0] == "Unnamed: 0" or metrics_df.columns[0] == "":
                    metrics_df = metrics_df.rename(columns={metrics_df.columns[0]: "Model"}).set_index("Model")
                    
                target_key = "xgboost"
                for k in metrics_df.index:
                    if "xgboost" in str(k).lower():
                        target_key = k
                        break
                        
                if target_key in metrics_df.index:
                    row = metrics_df.loc[target_key]
                    self.metrics = {
                        "ROC AUC": float(row.get("ROC AUC", 0.0)),
                        "Average Precision": float(row.get("Average Precision", 0.0)),
                        "F1 Score": float(row.get("F1 Score", 0.0)),
                        "Recall": float(row.get("Recall", 0.0)),
                        "Precision": float(row.get("Precision", 0.0)),
                        "Balanced Accuracy": float(row.get("Balanced Accuracy", 0.0)),
                    }
                    logger.info(f"Loaded static XGBoost benchmark metrics: ROC-AUC={self.metrics['ROC AUC']:.4f}")
            except Exception as e:
                logger.warning(f"Could not load static metrics from reports: {e}")

        self.is_loaded = (self.model is not None and self.pipeline is not None)
        logger.info("FinTrustX artifacts loaded successfully and ready for inference.")

    def run_smoke_test(self) -> bool:
        """Run a fast internal smoke test with a synthetic sample."""
        if not self.is_loaded:
            return False
        try:
            raw_sample = {col: [np.nan] for col in self.raw_feature_names}
            sample_df = pd.DataFrame(raw_sample)
            transformed = self.pipeline.transform(sample_df)
            prob = self.model.predict_proba(transformed)[0][1]
            return 0.0 <= float(prob) <= 1.0
        except Exception as e:
            logger.error(f"Startup inference smoke test failed: {e}")
            return False


# Global singleton instance accessor
_model_loader_instance = ModelLoader()

def get_model_loader() -> ModelLoader:
    """Return singleton ModelLoader instance."""
    return _model_loader_instance
