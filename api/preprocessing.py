"""
=========================================================
FinTrustX API Preprocessing Engine
=========================================================
Transforms raw incoming JSON applicant payloads into the exact
245-dimensional feature format expected by the XGBoost model
using the persisted fitted ColumnTransformer.

Author: Anurag Kashyap
=========================================================
"""

import logging
from typing import Any, Dict, List, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def transform_raw_to_features(
    raw_inputs: Union[Dict[str, Any], List[Dict[str, Any]]],
    pipeline: Any,
    raw_feature_names: List[str]
) -> np.ndarray:
    """
    Convert raw applicant payload(s) to preprocessed model feature matrix.
    
    Parameters
    ----------
    raw_inputs : dict or list of dict
        Incoming applicant feature dictionary or list of applicant dictionaries.
    pipeline : ColumnTransformer
        Fitted Scikit-Learn ColumnTransformer loaded from preprocessing_pipeline.joblib.
    raw_feature_names : list of str
        List of all 121 raw features expected by the pipeline.
        
    Returns
    -------
    np.ndarray
        Transformed 2D feature matrix of shape (n_samples, 245).
    """
    if isinstance(raw_inputs, dict):
        records = [raw_inputs]
    else:
        records = raw_inputs

    # Build DataFrame ensuring all expected raw columns exist
    df_raw = pd.DataFrame(records)
    
    # Fill any unprovided raw columns with NaN so SimpleImputer handles them (vectorized to eliminate fragmentation warnings)
    missing_cols = [c for c in raw_feature_names if c not in df_raw.columns]
    if missing_cols:
        df_missing = pd.DataFrame(np.nan, index=df_raw.index, columns=missing_cols)
        df_raw = pd.concat([df_raw, df_missing], axis=1)

    # Reorder columns to exactly match pipeline.feature_names_in_
    df_aligned = df_raw[raw_feature_names]

    # Execute transform (Never call fit or fit_transform during inference)
    try:
        transformed = pipeline.transform(df_aligned)
    except Exception as e:
        logger.error(f"Preprocessing transform failed: {e}")
        raise ValueError(f"Feature preprocessing failed: {e}") from e

    return transformed
