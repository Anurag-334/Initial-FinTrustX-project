"""
===========================================
Data Loader Module
===========================================

Author : Anurag Kashyap

Description:
------------
Loads datasets, validates them,
optimizes memory usage,
and provides dataset statistics.

Used by:

- EDA
- Feature Engineering
- ML Models
- Deep Learning
- FastAPI

===========================================
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import pandas as pd
import numpy as np
import logging

from src.config import (
    RAW_DATA_DIR,
    TARGET_COLUMN
)

# --------------------------------------------------------
# Logger
# --------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class DataLoader:

    """
    Professional Data Loading Class
    """

    def __init__(self):

        self.raw_data_dir = RAW_DATA_DIR

    # --------------------------------------------------

    def load_csv(
        self,
        filename: str,
        usecols: Optional[Union[List[str], Callable[[str], bool]]] = None,
        dtype: Optional[Union[Dict[str, Any], str, type]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:

        """
        Load CSV file from raw data directory.

        Parameters
        ----------
        filename : str
            Name of CSV file located within self.raw_data_dir.
        usecols : list of str or callable, optional
            Subset of columns to read. If None, all columns are returned.
        dtype : dict, str, or type, optional
            Data type specification for columns.
        **kwargs : Any
            Additional keyword arguments forwarded to pd.read_csv.

        Returns
        -------
        DataFrame
            Loaded dataset.

        Raises
        ------
        FileNotFoundError
            If specified file does not exist.
        """

        path = self.raw_data_dir / filename

        if not path.exists():

            raise FileNotFoundError(
                f"{path} not found."
            )

        logger.info(f"Loading {filename}")

        df = pd.read_csv(
            path,
            usecols=usecols,
            dtype=dtype,
            **kwargs,
        )

        logger.info(f"Shape : {df.shape}")

        return df

    # --------------------------------------------------

    def optimize_memory(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        """
        Reduce memory usage.
        """

        start = df.memory_usage().sum() / 1024**2

        logger.info(
            f"Memory Before : {start:.2f} MB"
        )

        for col in df.columns:

            col_type = df[col].dtype

            if str(col_type)[:3] == "int":

                df[col] = pd.to_numeric(
                    df[col],
                    downcast="integer"
                )

            elif str(col_type)[:5] == "float":

                df[col] = pd.to_numeric(
                    df[col],
                    downcast="float"
                )

        end = df.memory_usage().sum() / 1024**2

        logger.info(
            f"Memory After : {end:.2f} MB"
        )

        logger.info(
            f"Reduced : {(start-end):.2f} MB"
        )

        return df

    # --------------------------------------------------

    def dataset_summary(
        self,
        df: pd.DataFrame
    ):

        """
        Print dataset summary.
        """

        print("=" * 60)
        print("DATASET SUMMARY")
        print("=" * 60)

        print(f"Rows : {df.shape[0]}")
        print(f"Columns : {df.shape[1]}")

        print()

        print(df.info())

        print()

        print(df.describe().T)

    # --------------------------------------------------

    def missing_summary(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        """
        Missing value summary.
        """

        missing = pd.DataFrame({

            "Missing":

            df.isnull().sum(),

            "Percentage":

            df.isnull().mean() * 100

        })

        missing = missing[

            missing["Missing"] > 0

        ].sort_values(

            by="Percentage",

            ascending=False

        )

        return missing

    # --------------------------------------------------

    def class_distribution(
        self,
        df: pd.DataFrame
    ):

        """
        Print target distribution.
        """

        if TARGET_COLUMN not in df.columns:

            return

        print()

        print("=" * 60)

        print("TARGET DISTRIBUTION")

        print("=" * 60)

        print(df[TARGET_COLUMN].value_counts())

        print()

        print(

            df[TARGET_COLUMN]

            .value_counts(normalize=True)

            * 100

        )

    # --------------------------------------------------

    def categorical_columns(
        self,
        df: pd.DataFrame
    ):

        return df.select_dtypes(

            include=["object", "string"]

        ).columns.tolist()

    # --------------------------------------------------

    def numerical_columns(
        self,
        df: pd.DataFrame
    ):

        return df.select_dtypes(

            exclude=["object", "string"]

        ).columns.tolist()

    # --------------------------------------------------

    def report(
        self,
        df: pd.DataFrame
    ):

        """
        Complete Report
        """

        self.dataset_summary(df)

        self.class_distribution(df)

        print()

        print("=" * 60)

        print("MISSING VALUES")

        print("=" * 60)

        print(

            self.missing_summary(df)

            .head(20)

        )

        print()

        print("=" * 60)

        print("FEATURE TYPES")

        print("=" * 60)

        print(

            f"Categorical : {len(self.categorical_columns(df))}"

        )

        print(

            f"Numerical : {len(self.numerical_columns(df))}"

        )