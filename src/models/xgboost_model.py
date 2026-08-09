try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

from .base_model import BaseModel


class XGBoostModel(BaseModel):

    def __init__(self):

        super().__init__("XGBoost")

        self.build_model()

    def build_model(self):
        if XGBClassifier is None:
            self.model = None
            return

        self.model = XGBClassifier(

            n_estimators=300,

            learning_rate=0.05,

            max_depth=6,

            eval_metric="logloss",

            random_state=42

        )