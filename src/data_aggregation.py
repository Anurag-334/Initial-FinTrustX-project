"""
===========================================================
Data Aggregation Module
===========================================================

Author : FinTrustX Engineering Team
Description:
------------
Orchestrates memory-efficient, status-partitioned aggregations
for supplementary datasets (bureau.csv, previous_application.csv)
per applicant (SK_ID_CURR) with strict memory management (R2)
and guarantees safe left-merging on application_train.csv.

Conforms to:
- PEP8, Black formatting (line length <= 88)
- Type hints on all public functions and methods
- Explicit logging via logging.getLogger
- Specific exception handling
- Peak RAM usage strictly < 1.8 GB
===========================================================
"""

import gc
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from src.config import RAW_DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_BUREAU_USECOLS = [
    "SK_ID_CURR",
    "SK_ID_BUREAU",
    "CREDIT_ACTIVE",
    "CREDIT_TYPE",
    "DAYS_CREDIT",
    "CREDIT_DAY_OVERDUE",
    "DAYS_CREDIT_ENDDATE",
    "AMT_CREDIT_MAX_OVERDUE",
    "CNT_CREDIT_PROLONG",
    "AMT_CREDIT_SUM",
    "AMT_CREDIT_SUM_DEBT",
    "AMT_CREDIT_SUM_LIMIT",
    "AMT_CREDIT_SUM_OVERDUE",
    "DAYS_CREDIT_UPDATE",
    "AMT_ANNUITY",
]

DEFAULT_PREV_USECOLS = [
    "SK_ID_CURR",
    "SK_ID_PREV",
    "NAME_CONTRACT_STATUS",
    "NAME_CONTRACT_TYPE",
    "AMT_ANNUITY",
    "AMT_APPLICATION",
    "AMT_CREDIT",
    "AMT_DOWN_PAYMENT",
    "RATE_DOWN_PAYMENT",
    "DAYS_DECISION",
    "CNT_PAYMENT",
    "DAYS_TERMINATION",
]


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast numerical columns to minimize memory footprint.

    Converts float64 -> float32 and int64 -> int8/int16/int32.
    Converts low-cardinality object strings to category.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame to downcast in-place.

    Returns
    -------
    pd.DataFrame
        Downcasted DataFrame.
    """
    for col in df.columns:
        col_type = df[col].dtype
        if pd.api.types.is_integer_dtype(col_type):
            c_min = df[col].min()
            c_max = df[col].max()
            if c_min >= -128 and c_max <= 127:
                df[col] = df[col].astype(np.int8)
            elif c_min >= -32768 and c_max <= 32767:
                df[col] = df[col].astype(np.int16)
            elif c_min >= -2147483648 and c_max <= 2147483647:
                df[col] = df[col].astype(np.int32)
        elif pd.api.types.is_float_dtype(col_type):
            df[col] = df[col].astype(np.float32)
        elif col_type == "object":
            num_unique = df[col].nunique(dropna=True)
            if len(df) > 0 and (num_unique / len(df)) < 0.5:
                df[col] = df[col].astype("category")
    return df


class DataAggregator:
    """
    Memory-safe aggregation pipeline for Home Credit supplementary datasets.
    """

    def __init__(self, raw_data_dir: Optional[Path] = None) -> None:
        """
        Initialize DataAggregator with raw data directory.

        Parameters
        ----------
        raw_data_dir : Optional[Path]
            Path to data/raw directory. Defaults to RAW_DATA_DIR from config.
        """
        self.raw_data_dir = raw_data_dir or RAW_DATA_DIR

    def aggregate_bureau(
        self,
        filename: str = "bureau.csv",
        usecols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Aggregate bureau.csv per applicant (SK_ID_CURR).

        Parameters
        ----------
        filename : str
            Filename of credit bureau CSV in raw_data_dir.
        usecols : Optional[List[str]]
            Subset of columns to read. Defaults to DEFAULT_BUREAU_USECOLS.

        Returns
        -------
        pd.DataFrame
            Aggregated bureau DataFrame indexed by SK_ID_CURR.
        """
        if usecols is None:
            usecols = DEFAULT_BUREAU_USECOLS

        path = self.raw_data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Bureau file not found at: {path}")

        logger.info(f"Loading {filename} with {len(usecols)} columns...")
        df_bureau = pd.read_csv(path, usecols=usecols)
        df_bureau = optimize_dtypes(df_bureau)

        # Pre-compute status partitions
        df_bureau["IS_ACTIVE"] = (
            df_bureau["CREDIT_ACTIVE"] == "Active"
        ).astype(np.int8)
        df_bureau["IS_CLOSED"] = (
            df_bureau["CREDIT_ACTIVE"] == "Closed"
        ).astype(np.int8)
        df_bureau["IS_MICROLOAN"] = (
            df_bureau["CREDIT_TYPE"] == "Microloan"
        ).astype(np.int8)

        df_bureau["ACTIVE_AMT_CREDIT_SUM_DEBT"] = df_bureau[
            "AMT_CREDIT_SUM_DEBT"
        ].where(df_bureau["IS_ACTIVE"] == 1, np.nan)
        df_bureau["ACTIVE_AMT_CREDIT_SUM"] = df_bureau[
            "AMT_CREDIT_SUM"
        ].where(df_bureau["IS_ACTIVE"] == 1, np.nan)
        df_bureau["ACTIVE_DAYS_CREDIT"] = df_bureau[
            "DAYS_CREDIT"
        ].where(df_bureau["IS_ACTIVE"] == 1, np.nan)

        agg_rules = {
            "SK_ID_BUREAU": ["count"],
            "IS_ACTIVE": ["sum", "mean"],
            "IS_CLOSED": ["sum", "mean"],
            "IS_MICROLOAN": ["sum", "mean"],
            "DAYS_CREDIT": ["min", "max", "mean"],
            "CREDIT_DAY_OVERDUE": ["max", "mean"],
            "DAYS_CREDIT_ENDDATE": ["min", "max", "mean"],
            "AMT_CREDIT_MAX_OVERDUE": ["max", "mean"],
            "CNT_CREDIT_PROLONG": ["sum", "max"],
            "AMT_CREDIT_SUM": ["sum", "mean", "max"],
            "AMT_CREDIT_SUM_DEBT": ["sum", "mean", "max"],
            "AMT_CREDIT_SUM_LIMIT": ["sum", "mean"],
            "AMT_CREDIT_SUM_OVERDUE": ["sum", "max"],
            "DAYS_CREDIT_UPDATE": ["max", "mean"],
            "AMT_ANNUITY": ["sum", "mean", "max"],
            "ACTIVE_AMT_CREDIT_SUM_DEBT": ["sum", "mean"],
            "ACTIVE_AMT_CREDIT_SUM": ["sum", "mean"],
            "ACTIVE_DAYS_CREDIT": ["max"],
        }

        logger.info("Executing GroupBy aggregation on Bureau records...")
        bureau_agg = df_bureau.groupby("SK_ID_CURR").agg(agg_rules)
        bureau_agg.columns = [
            f"BUREAU_{col}_{stat}".upper()
            for col, stat in bureau_agg.columns
        ]
        bureau_agg = bureau_agg.reset_index()

        # Derived intra-table ratios
        bureau_agg["BUREAU_DEBT_CREDIT_RATIO"] = (
            bureau_agg["BUREAU_AMT_CREDIT_SUM_DEBT_SUM"]
            / (bureau_agg["BUREAU_AMT_CREDIT_SUM_SUM"] + 1.0)
        )
        bureau_agg["BUREAU_ACTIVE_DEBT_RATIO"] = (
            bureau_agg["BUREAU_ACTIVE_AMT_CREDIT_SUM_DEBT_SUM"]
            / (bureau_agg["BUREAU_ACTIVE_AMT_CREDIT_SUM_SUM"] + 1.0)
        )
        bureau_agg["BUREAU_OVERDUE_DEBT_RATIO"] = (
            bureau_agg["BUREAU_AMT_CREDIT_SUM_OVERDUE_SUM"]
            / (bureau_agg["BUREAU_AMT_CREDIT_SUM_DEBT_SUM"] + 1.0)
        )
        bureau_agg["BUREAU_ACTIVE_LOAN_SHARE"] = (
            bureau_agg["BUREAU_IS_ACTIVE_SUM"]
            / (bureau_agg["BUREAU_SK_ID_BUREAU_COUNT"] + 1e-5)
        )
        bureau_agg["BUREAU_PROLONG_RATE"] = (
            bureau_agg["BUREAU_CNT_CREDIT_PROLONG_SUM"]
            / (bureau_agg["BUREAU_SK_ID_BUREAU_COUNT"] + 1e-5)
        )

        bureau_agg = optimize_dtypes(bureau_agg)

        del df_bureau
        gc.collect()
        logger.info(
            f"Bureau aggregation finished. Result shape: {bureau_agg.shape}"
        )
        return bureau_agg

    def aggregate_previous_application(
        self,
        filename: str = "previous_application.csv",
        usecols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Aggregate previous_application.csv per applicant (SK_ID_CURR).

        Parameters
        ----------
        filename : str
            Filename of previous application CSV in raw_data_dir.
        usecols : Optional[List[str]]
            Subset of columns to read. Defaults to DEFAULT_PREV_USECOLS.

        Returns
        -------
        pd.DataFrame
            Aggregated previous application DataFrame.
        """
        if usecols is None:
            usecols = DEFAULT_PREV_USECOLS

        path = self.raw_data_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Previous application file not found at: {path}"
            )

        logger.info(f"Loading {filename} with {len(usecols)} columns...")
        df_prev = pd.read_csv(path, usecols=usecols)
        df_prev = optimize_dtypes(df_prev)

        # Pre-compute status partitions
        df_prev["IS_APPROVED"] = (
            df_prev["NAME_CONTRACT_STATUS"] == "Approved"
        ).astype(np.int8)
        df_prev["IS_REFUSED"] = (
            df_prev["NAME_CONTRACT_STATUS"] == "Refused"
        ).astype(np.int8)
        df_prev["IS_CANCELED"] = (
            df_prev["NAME_CONTRACT_STATUS"] == "Canceled"
        ).astype(np.int8)

        df_prev["APPROVED_AMT_CREDIT"] = df_prev["AMT_CREDIT"].where(
            df_prev["IS_APPROVED"] == 1, np.nan
        )
        df_prev["REFUSED_AMT_APPLICATION"] = df_prev[
            "AMT_APPLICATION"
        ].where(df_prev["IS_REFUSED"] == 1, np.nan)
        df_prev["REFUSED_DAYS_DECISION"] = df_prev["DAYS_DECISION"].where(
            df_prev["IS_REFUSED"] == 1, np.nan
        )
        df_prev["APPROVED_DAYS_DECISION"] = df_prev["DAYS_DECISION"].where(
            df_prev["IS_APPROVED"] == 1, np.nan
        )
        df_prev["APP_CREDIT_RATIO"] = df_prev["AMT_APPLICATION"] / (
            df_prev["AMT_CREDIT"] + 1.0
        )

        agg_rules = {
            "SK_ID_PREV": ["count"],
            "IS_APPROVED": ["sum", "mean"],
            "IS_REFUSED": ["sum", "mean"],
            "IS_CANCELED": ["sum", "mean"],
            "AMT_ANNUITY": ["min", "max", "mean", "sum"],
            "AMT_APPLICATION": ["min", "max", "mean", "sum"],
            "AMT_CREDIT": ["min", "max", "mean", "sum"],
            "AMT_DOWN_PAYMENT": ["max", "mean", "sum"],
            "RATE_DOWN_PAYMENT": ["max", "mean"],
            "DAYS_DECISION": ["min", "max", "mean"],
            "CNT_PAYMENT": ["max", "mean", "sum"],
            "DAYS_TERMINATION": ["max", "mean"],
            "APP_CREDIT_RATIO": ["mean", "max"],
            "APPROVED_AMT_CREDIT": ["sum", "mean"],
            "REFUSED_AMT_APPLICATION": ["sum", "mean"],
            "REFUSED_DAYS_DECISION": ["max"],
            "APPROVED_DAYS_DECISION": ["max"],
        }

        logger.info(
            "Executing GroupBy aggregation on Previous Applications..."
        )
        prev_agg = df_prev.groupby("SK_ID_CURR").agg(agg_rules)
        prev_agg.columns = [
            f"PREV_{col}_{stat}".upper()
            for col, stat in prev_agg.columns
        ]
        prev_agg = prev_agg.reset_index()

        # Derived intra-table ratios
        prev_agg["PREV_APPROVAL_RATE"] = (
            prev_agg["PREV_IS_APPROVED_SUM"]
            / (prev_agg["PREV_SK_ID_PREV_COUNT"] + 1e-5)
        )
        prev_agg["PREV_REFUSAL_RATE"] = (
            prev_agg["PREV_IS_REFUSED_SUM"]
            / (prev_agg["PREV_SK_ID_PREV_COUNT"] + 1e-5)
        )
        prev_agg["PREV_CREDIT_TO_APPLICATION_RATIO"] = (
            prev_agg["PREV_AMT_CREDIT_SUM"]
            / (prev_agg["PREV_AMT_APPLICATION_SUM"] + 1.0)
        )
        prev_agg["PREV_DOWN_PAYMENT_RATIO"] = (
            prev_agg["PREV_AMT_DOWN_PAYMENT_SUM"]
            / (prev_agg["PREV_AMT_CREDIT_SUM"] + 1.0)
        )

        prev_agg = optimize_dtypes(prev_agg)

        del df_prev
        gc.collect()
        logger.info(
            f"Previous app aggregation finished. Result shape: {prev_agg.shape}"
        )
        return prev_agg

    def merge_features(
        self,
        main_df: pd.DataFrame,
        bureau_agg: pd.DataFrame,
        prev_agg: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Safely left-merge aggregated features onto the main training dataset.

        Preserves 100% of rows from main_df (307,511) and leaves target
        distribution unchanged. Computes cross-table macroeconomic credit ratios.

        Parameters
        ----------
        main_df : pd.DataFrame
            Main application DataFrame (application_train.csv).
        bureau_agg : pd.DataFrame
            Aggregated bureau records.
        prev_agg : pd.DataFrame
            Aggregated previous application records.

        Returns
        -------
        pd.DataFrame
            Augmented DataFrame with all merged features and cross-table ratios.
        """
        if len(main_df) == 0:
            raise ValueError("main_df is empty. Cannot perform merge.")

        if not bureau_agg["SK_ID_CURR"].is_unique:
            raise ValueError(
                "Duplicate SK_ID_CURR values detected in bureau_agg."
            )

        if not prev_agg["SK_ID_CURR"].is_unique:
            raise ValueError(
                "Duplicate SK_ID_CURR values detected in prev_agg."
            )

        initial_rows = len(main_df)
        logger.info(
            f"Initiating feature merge. Anchor shape: {main_df.shape}"
        )

        # 1. Left merge Bureau aggregations
        merged = main_df.merge(bureau_agg, on="SK_ID_CURR", how="left")
        if len(merged) != initial_rows:
            raise RuntimeError(
                f"Row count altered after bureau merge: "
                f"{len(merged)} vs expected {initial_rows}."
            )

        # 2. Left merge Previous Application aggregations
        merged = merged.merge(prev_agg, on="SK_ID_CURR", how="left")
        if len(merged) != initial_rows:
            raise RuntimeError(
                f"Row count altered after prev merge: "
                f"{len(merged)} vs expected {initial_rows}."
            )

        # 3. Create missing history indicator flags
        merged["FLAG_NO_BUREAU_DATA"] = (
            merged["BUREAU_SK_ID_BUREAU_COUNT"].isna().astype(np.int8)
        )
        merged["FLAG_NO_PREV_DATA"] = (
            merged["PREV_SK_ID_PREV_COUNT"].isna().astype(np.int8)
        )

        # 4. Zero-fill counts for applicants with no record
        merged["BUREAU_LOAN_COUNT"] = (
            merged["BUREAU_SK_ID_BUREAU_COUNT"].fillna(0).astype(np.int16)
        )
        merged["PREV_APP_COUNT"] = (
            merged["PREV_SK_ID_PREV_COUNT"].fillna(0).astype(np.int16)
        )

        # 5. Cross-Table Macroeconomic Credit Leverage Ratios
        merged["BUREAU_TOTAL_DEBT_TO_INCOME"] = (
            merged["BUREAU_AMT_CREDIT_SUM_DEBT_SUM"]
            / (merged["AMT_INCOME_TOTAL"] + 1.0)
        )
        merged["BUREAU_ANNUITY_TO_INCOME"] = (
            merged["BUREAU_AMT_ANNUITY_SUM"]
            / (merged["AMT_INCOME_TOTAL"] + 1.0)
        )
        merged["PREV_ANNUITY_TO_INCOME"] = (
            merged["PREV_AMT_ANNUITY_SUM"]
            / (merged["AMT_INCOME_TOTAL"] + 1.0)
        )
        merged["PREV_CURRENT_TO_PRIOR_CREDIT_RATIO"] = (
            merged["AMT_CREDIT"]
            / (merged["PREV_APPROVED_AMT_CREDIT_MEAN"] + 1.0)
        )
        merged["TOTAL_DEBT_TO_INCOME"] = (
            merged["AMT_CREDIT"]
            + merged["BUREAU_AMT_CREDIT_SUM_DEBT_SUM"].fillna(0)
        ) / (merged["AMT_INCOME_TOTAL"] + 1.0)

        merged = optimize_dtypes(merged)

        # Validation assertions
        assert len(merged) == initial_rows, "Final row count validation failed"
        assert (
            merged["SK_ID_CURR"].is_unique
        ), "Duplicate SK_ID_CURR in merged data"
        if "TARGET" in main_df.columns:
            assert merged["TARGET"].sum() == main_df["TARGET"].sum(), (
                "TARGET sum mismatch after merge!"
            )

        logger.info(
            f"Feature merge completed successfully. Final shape: {merged.shape}"
        )
        return merged
