"""
===========================================================
Machine Learning Training Engine
===========================================================

Author : Anurag Kashyap

Description
-----------
Train all classical ML models.

Models
------
• Logistic Regression
• Decision Tree
• Random Forest
• XGBoost
• CatBoost

===========================================================
"""

import time
import pandas as pd

from pathlib import Path

from src.evaluate import evaluate_model

from src.models.logistic_model import LogisticRegressionModel
from src.models.decision_tree import DecisionTreeModel
from src.models.random_forest import RandomForestModel
from src.models.xgboost_model import XGBoostModel
from src.models.catboost_model import CatBoostModel


class MLTrainer:

    def __init__(self):

        self.models = {

            "Logistic Regression":
                LogisticRegressionModel(),

            "Decision Tree":
                DecisionTreeModel(),

            "Random Forest":
                RandomForestModel(),

            "XGBoost":
                XGBoostModel(),

            "CatBoost":
                CatBoostModel()

        }

        self.results = []

    #########################################################

    def train_all(

            self,

            X_train,

            y_train,

            X_test,

            y_test

    ):

        """
        Train every model
        """

        for name, model in self.models.items():
            if model.get_model() is None:
                print(f"Skipping {name}: Underlying model package not installed.")
                continue

            print("=" * 70)

            print(f"Training : {name}")

            print("=" * 70)

            start = time.time()

            model.fit(
                X_train,
                y_train
            )

            training_time = time.time() - start

            metrics = evaluate_model(

                model.get_model(),

                X_test,

                y_test,

                plot=False

            )

            metrics["Model"] = name

            metrics["Training Time"] = training_time

            self.results.append(metrics)

            model.save(

                f"models/{name}.joblib"

            )
#
            comparison = pd.DataFrame(self.results)

            comparison.to_csv(

            "reports/model_comparison.csv",

            index=False

            )
#
        return pd.DataFrame(self.results)

    #########################################################

    def comparison_table(self):

        df = pd.DataFrame(self.results)

        df = df.sort_values(

            by="ROC AUC",

            ascending=False

        )

        return df

    #########################################################

    def best_model(self):

        df = self.comparison_table()

        best = df.iloc[0]

        print()

        print("=" * 60)

        print("BEST MODEL")

        print("=" * 60)

        print(best)

        return best