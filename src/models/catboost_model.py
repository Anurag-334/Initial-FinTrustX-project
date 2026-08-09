try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None

from .base_model import BaseModel


class CatBoostModel(BaseModel):

    def __init__(self):

        super().__init__("CatBoost")

        self.build_model()

    def build_model(self):
        if CatBoostClassifier is None:
            self.model = None
            return

        self.model = CatBoostClassifier(

            iterations=300,

            learning_rate=0.05,

            depth=6,

            verbose=False,

            random_state=42

        )