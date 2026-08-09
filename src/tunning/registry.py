"""
=========================================================
Model Registry
=========================================================

Central registry for all tunable models.

Author : Anurag Kashyap
=========================================================
"""

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None

from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from src.config import *

MODEL_REGISTRY = {

    "decision_tree":{

        "model":DecisionTreeClassifier,

        "space":DECISION_TREE_SPACE,

        "study":STUDY_NAMES["decision_tree"],

        "model_file":MODEL_NAMES["decision_tree"],

        "parameter_file":PARAMETER_FILES["decision_tree"]

    },

    "random_forest":{

        "model":RandomForestClassifier,

        "space":RANDOM_FOREST_SPACE,

        "study":STUDY_NAMES["random_forest"],

        "model_file":MODEL_NAMES["random_forest"],

        "parameter_file":PARAMETER_FILES["random_forest"]

    },

    "xgboost":{

        "model":XGBClassifier,

        "space":XGBOOST_SPACE,

        "study":STUDY_NAMES["xgboost"],

        "model_file":MODEL_NAMES["xgboost"],

        "parameter_file":PARAMETER_FILES["xgboost"]

    },

    "catboost":{

        "model":CatBoostClassifier,

        "space":CATBOOST_SPACE,

        "study":STUDY_NAMES["catboost"],

        "model_file":MODEL_NAMES["catboost"],

        "parameter_file":PARAMETER_FILES["catboost"]

    }

}