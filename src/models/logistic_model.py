from sklearn.linear_model import LogisticRegression

from .base_model import BaseModel


class LogisticRegressionModel(BaseModel):

    def __init__(self):

        super().__init__("Logistic Regression")

        self.build_model()

    def build_model(self):

        self.model = LogisticRegression(

            max_iter=1000,

            class_weight="balanced",

            random_state=42
        )