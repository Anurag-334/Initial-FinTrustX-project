"""
XGBoost model wrapper inheriting from BaseModel.
Supports flexible hyperparameters, histogram tree method, and early stopping.
"""

from typing import Any, Dict, Optional

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

from .base_model import BaseModel


class XGBoostModel(BaseModel):
    """
    XGBoost Classifier wrapper with flexible hyperparameter support,
    histogram-based tree method (tree_method="hist"), and early stopping.
    """

    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the XGBoost model.

        Parameters
        ----------
        params : Optional[Dict[str, Any]], optional
            Dictionary of hyperparameters.
        **kwargs : Any
            Additional hyperparameters passed as keyword arguments.
        """
        super().__init__("XGBoost")
        self.params: Dict[str, Any] = {}
        if params is not None:
            self.params.update(params)
        if kwargs:
            self.params.update(kwargs)

        self.build_model()

    def build_model(self) -> None:
        """
        Build the XGBClassifier with default parameters updated by user configuration.
        """
        if XGBClassifier is None:
            self.model = None
            return

        default_params: Dict[str, Any] = {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "max_depth": 6,
            "tree_method": "hist",
            "eval_metric": "auc",
            "random_state": 42,
            "n_jobs": -1,
        }
        default_params.update(self.params)
        self.model = XGBClassifier(**default_params)

    def fit(
        self,
        X_train: Any,
        y_train: Any,
        eval_set: Optional[Any] = None,
        verbose: bool = False,
        early_stopping_rounds: Optional[int] = None,
        **kwargs: Any,
    ) -> "XGBoostModel":
        """
        Fit the model on training data.

        Parameters
        ----------
        X_train : Any
            Training feature matrix.
        y_train : Any
            Training labels.
        eval_set : Optional[Any], optional
            Validation dataset pairs [(X_val, y_val)] for monitoring.
        verbose : bool, default=False
            Whether to print evaluation metric progress.
        early_stopping_rounds : Optional[int], optional
            Validation rounds for early stopping patience.
        **kwargs : Any
            Additional arguments passed to XGBClassifier.fit().

        Returns
        -------
        XGBoostModel
            Self instance.
        """
        if self.model is None:
            raise ValueError("Model has not been built. Call build_model() first.")

        if early_stopping_rounds is not None:
            self.model.set_params(early_stopping_rounds=early_stopping_rounds)

        fit_kwargs = dict(kwargs)
        if eval_set is not None:
            fit_kwargs["eval_set"] = eval_set
            fit_kwargs["verbose"] = verbose

        self.model.fit(X_train, y_train, **fit_kwargs)
        return self

    @property
    def best_iteration(self) -> Optional[int]:
        """Return best iteration from early stopping if available."""
        if self.model is not None and hasattr(self.model, "best_iteration"):
            return self.model.best_iteration
        return None

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Return parameters of the underlying model."""
        if self.model is not None:
            return self.model.get_params(deep=deep)
        return self.params