from abc import ABC, abstractmethod
import joblib
from pathlib import Path


class BaseModel(ABC):

    """
    Abstract base class for all ML models.
    """

    def __init__(self, name):

        self.name = name
        self.model = None

    @abstractmethod
    def build_model(self):
        """
        Build model architecture.
        """
        pass

    def fit(self, X_train, y_train):

        if self.model is None:
            raise ValueError("Model has not been built. Call build_model() first.")
        self.model.fit(X_train, y_train)

    def predict(self, X):

        if self.model is None:
            raise ValueError("Model is not initialized.")
        return self.model.predict(X)

    def predict_proba(self, X):

        if self.model is None:
            raise ValueError("Model is not initialized.")
        return self.model.predict_proba(X)[:, 1]

    def save(self, path):

        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        joblib.dump(self.model, path)

    def load(self, path):

        self.model = joblib.load(path)

    def get_model(self):

        return self.model