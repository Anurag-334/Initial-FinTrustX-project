from sklearn.ensemble import RandomForestClassifier

from .base_model import BaseModel


class RandomForestModel(BaseModel):

    def __init__(self):

        super().__init__("Random Forest")

        self.build_model()

    def build_model(self):

        self.model = RandomForestClassifier(

            n_estimators=300,

            random_state=42,

            class_weight="balanced",

            n_jobs=-1

        )