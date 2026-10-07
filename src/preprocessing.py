"""
===========================================================
Preprocessing Module
===========================================================

Author : Anurag Kashyap

Description
-----------
Professional preprocessing pipeline.

Features:
---------
✔ Missing Value Imputation
✔ One-Hot Encoding
✔ Standard Scaling
✔ ColumnTransformer
✔ Pipeline
✔ Save & Load Pipeline
✔ Feature Name Extraction

===========================================================
"""

import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler
)

from src.config import MODEL_DIR

logger = logging.getLogger(__name__)


class DataPreprocessor:

    def __init__(self):

        self.numeric_features = None
        self.categorical_features = None

        self.preprocessor = None

    # -------------------------------------------------

    def detect_features(
        self,
        df: pd.DataFrame,
        target_column: Optional[str] = "TARGET",
        exclude_columns: Optional[Union[List[str], Set[str]]] = None,
    ) -> Tuple[List[str], List[str]]:

        """
        Automatically detect numerical and categorical feature columns.

        Excludes target column and identifier columns (e.g., SK_ID_CURR) to
        prevent data leakage into machine learning models.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataset.
        target_column : str, optional
            Name of target variable column (default: "TARGET"). If None or
            not present in df.columns, no target is dropped.
        exclude_columns : list or set of str, optional
            Columns to exclude from features. Defaults to ["SK_ID_CURR"]
            to ensure applicant ID is never treated as a feature.

        Returns
        -------
        Tuple[List[str], List[str]]
            Tuple containing (numeric_features, categorical_features).
        """

        drop_cols: Set[str] = set()

        if target_column is not None and target_column in df.columns:
            drop_cols.add(target_column)

        if exclude_columns is None:
            drop_cols.add("SK_ID_CURR")
        else:
            drop_cols.update(exclude_columns)
            drop_cols.add("SK_ID_CURR")

        feature_cols = [c for c in df.columns if c not in drop_cols]
        X = df[feature_cols]

        self.numeric_features = X.select_dtypes(
            include=["number"]
        ).columns.tolist()

        self.categorical_features = X.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        logger.info("=" * 60)
        logger.info("Feature Detection")
        logger.info("=" * 60)
        logger.info(f"Numerical : {len(self.numeric_features)}")
        logger.info(f"Categorical : {len(self.categorical_features)}")
        if "SK_ID_CURR" in df.columns:
            logger.info("Excluded applicant ID: SK_ID_CURR")

        return (
            self.numeric_features,
            self.categorical_features,
        )

    # -------------------------------------------------

    def build_pipeline(self):

        """
        Create preprocessing pipeline.
        """

        numeric_pipeline = Pipeline([

            (
                "imputer",

                SimpleImputer(
                    strategy="median"
                )
            ),

            (
                "scaler",

                StandardScaler()
            )

        ])

        categorical_pipeline = Pipeline([

            (
                "imputer",

                SimpleImputer(
                    strategy="most_frequent"
                )
            ),

            (
                "encoder",

                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            )

        ])

        self.preprocessor = ColumnTransformer([

            (

                "num",

                numeric_pipeline,

                self.numeric_features

            ),

            (

                "cat",

                categorical_pipeline,

                self.categorical_features

            )

        ])

        return self.preprocessor

    # -------------------------------------------------

    def fit_transform(self, X):

        """
        Fit preprocessing
        and transform dataset.
        """

        X_processed = self.preprocessor.fit_transform(X) # type: ignore

        return X_processed

    # -------------------------------------------------

    def transform(self, X):

        """
        Transform new data.
        """

        return self.preprocessor.transform(X)  # type: ignore

    # -------------------------------------------------

    def save_pipeline(self,
                      filename="preprocessor.joblib"):

        """
        Save pipeline.
        """

        MODEL_DIR.mkdir(
            exist_ok=True
        )

        joblib.dump(

            self.preprocessor,

            MODEL_DIR / filename

        )

        print(
            f"Pipeline saved to {MODEL_DIR / filename}"
        )

    # -------------------------------------------------

    def load_pipeline(self,
                      filename="preprocessor.joblib"):

        """
        Load saved pipeline.
        """

        self.preprocessor = joblib.load(

            MODEL_DIR / filename

        )

        return self.preprocessor

    # -------------------------------------------------

    def get_feature_names(self):

        """
        Return transformed feature names.
        """

        if self.preprocessor is None:
            raise ValueError("Pipeline has not been built. Call build_pipeline() first.")
        
        return self.preprocessor.get_feature_names_out()

    # -------------------------------------------------

    def summary(self):

        print("=" * 60)

        print("Preprocessing Pipeline")

        print("=" * 60)

        print(self.preprocessor)