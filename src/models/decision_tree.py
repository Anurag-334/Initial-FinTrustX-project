from sklearn.tree import DecisionTreeClassifier

from .base_model import BaseModel


class DecisionTreeModel(BaseModel):

    def __init__(self):

        super().__init__("Decision Tree")

        self.build_model()

    def build_model(self):

        self.model = DecisionTreeClassifier(

            max_depth=10,

            random_state=42,

            class_weight="balanced"

        )