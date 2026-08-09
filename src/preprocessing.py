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

from pathlib import Path
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


class DataPreprocessor:

    def __init__(self):

        self.numeric_features = None
        self.categorical_features = None

        self.preprocessor = None

    # -------------------------------------------------

    def detect_features(self, df, target_column="TARGET"):

        """
        Automatically detect
        numerical and categorical columns.
        """

        X = df.drop(columns=[target_column])

        self.numeric_features = X.select_dtypes(
            include=["number"]
        ).columns.tolist()

        self.categorical_features = X.select_dtypes(
            include=["object", "string"]
        ).columns.tolist()

        print("=" * 60)
        print("Feature Detection")
        print("=" * 60)

        print(f"Numerical : {len(self.numeric_features)}")
        print(f"Categorical : {len(self.categorical_features)}")

        return (
            self.numeric_features,
            self.categorical_features
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