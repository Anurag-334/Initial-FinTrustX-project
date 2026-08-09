"""
===========================================================
Feature Engineering Module
===========================================================

Author : Anurag Kashyap

Description
-----------
Creates new features from raw Home Credit data.

Compatible with Scikit-Learn Pipeline.

===========================================================
"""

import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, TransformerMixin


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Feature Engineering Transformer
    """

    def __init__(self):

        pass

    # -------------------------------------------------

    def fit(self, X, y=None):
        return self

    # -------------------------------------------------

    def transform(self, X):

        df = X.copy()

        # ===============================================
        # Handle Special Values
        # ===============================================

        # DAYS_EMPLOYED = 365243 means "Not employed"

        df["DAYS_EMPLOYED"] = df["DAYS_EMPLOYED"].replace(
            365243,
            np.nan
        )

        # ===============================================
        # Age
        # ===============================================

        df["AGE_YEARS"] = (
            -df["DAYS_BIRTH"] / 365
        )

        # ===============================================
        # Employment Years
        # ===============================================

        df["EMPLOYMENT_YEARS"] = (
            -df["DAYS_EMPLOYED"] / 365
        )

        # ===============================================
        # Credit / Income
        # ===============================================

        df["CREDIT_INCOME_RATIO"] = (
            df["AMT_CREDIT"] /
            (df["AMT_INCOME_TOTAL"] + 1)
        )

        # ===============================================
        # Annuity / Income
        # ===============================================

        df["ANNUITY_INCOME_RATIO"] = (
            df["AMT_ANNUITY"] /
            (df["AMT_INCOME_TOTAL"] + 1)
        )

        # ===============================================
        # Goods / Credit
        # ===============================================

        df["GOODS_CREDIT_RATIO"] = (
            df["AMT_GOODS_PRICE"] /
            (df["AMT_CREDIT"] + 1)
        )

        # ===============================================
        # Income Per Family Member
        # ===============================================

        df["INCOME_PER_PERSON"] = (
            df["AMT_INCOME_TOTAL"] /
            (df["CNT_FAM_MEMBERS"] + 1)
        )

        # ===============================================
        # Children Ratio
        # ===============================================

        df["CHILDREN_RATIO"] = (
            df["CNT_CHILDREN"] /
            (df["CNT_FAM_MEMBERS"] + 1)
        )

        # ===============================================
        # Credit Per Person
        # ===============================================

        df["CREDIT_PER_PERSON"] = (
            df["AMT_CREDIT"] /
            (df["CNT_FAM_MEMBERS"] + 1)
        )

        # ===============================================
        # Employment Age Ratio
        # ===============================================

        df["EMPLOYMENT_AGE_RATIO"] = (
            df["EMPLOYMENT_YEARS"] /
            (df["AGE_YEARS"] + 1)
        )

        # ===============================================
        # External Sources Mean
        # ===============================================

        ext_cols = [
            "EXT_SOURCE_1",
            "EXT_SOURCE_2",
            "EXT_SOURCE_3"
        ]

        existing = [
            col for col in ext_cols
            if col in df.columns
        ]

        if existing:

            df["EXT_SOURCE_MEAN"] = (
                df[existing]
                .mean(axis=1)
            )

            df["EXT_SOURCE_STD"] = (
                df[existing]
                .std(axis=1)
            )

        # ===============================================
        # Credit Term
        # ===============================================

        df["CREDIT_TERM"] = (
            df["AMT_ANNUITY"] /
            (df["AMT_CREDIT"] + 1)
        )

        # ===============================================
        # Phone Change Years
        # ===============================================

        df["PHONE_CHANGE_YEARS"] = (
            -df["DAYS_LAST_PHONE_CHANGE"] / 365
        )

        # ===============================================
        # Registration Years
        # ===============================================

        df["REGISTRATION_YEARS"] = (
            -df["DAYS_REGISTRATION"] / 365
        )

        # ===============================================
        # ID Publish Years
        # ===============================================

        df["ID_PUBLISH_YEARS"] = (
            -df["DAYS_ID_PUBLISH"] / 365
        )

        # ===============================================
        # Family Size Category
        # ===============================================

        df["LARGE_FAMILY"] = (
            df["CNT_FAM_MEMBERS"] >= 5
        ).astype(int)

        # ===============================================
        # Has Car
        # ===============================================

        if "FLAG_OWN_CAR" in df.columns:

            df["HAS_CAR"] = (
                df["FLAG_OWN_CAR"] == "Y"
            ).astype(int)

        # ===============================================
        # Has House
        # ===============================================

        if "FLAG_OWN_REALTY" in df.columns:

            df["HAS_HOUSE"] = (
                df["FLAG_OWN_REALTY"] == "Y"
            ).astype(int)

        return df