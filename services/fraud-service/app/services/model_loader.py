import logging
from pathlib import Path

import joblib

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self):
        self._model = None
        self._source = "uninitialized"

    def _load_from_mlflow(self):
        import mlflow

        mlflow.set_tracking_uri(
            settings.MLFLOW_TRACKING_URI
        )

        model_uri = (
            f"models:/{settings.MLFLOW_MODEL_NAME}/"
            f"{settings.MLFLOW_MODEL_STAGE}"
        )

        logger.info(
            "Loading fraud model from MLflow: %s",
            model_uri
        )

        self._model = mlflow.pyfunc.load_model(
            model_uri
        )
        self._source = model_uri

    def _load_from_local_artifact(self):
        model_path = Path(__file__).resolve().parents[2] / settings.LOCAL_MODEL_PATH

        logger.info(
            "Loading fraud model from local artifact: %s",
            model_path
        )

        self._model = joblib.load(model_path)
        self._source = str(model_path)

    def load(self):
        if self._model is not None:
            return self._model

        try:
            self._load_from_mlflow()
        except Exception as exc:
            logger.warning(
                "Falling back to local model artifact because MLflow model load failed: %s",
                exc
            )
            self._load_from_local_artifact()

        return self._model

    def predict_probability(self, features):
        model = self.load()

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(
                features
            )
            return float(probabilities[0][1])

        prediction = model.predict(
            features
        )

        value = prediction[0]

        if hasattr(value, "item"):
            value = value.item()

        return max(
            0.0,
            min(1.0, float(value))
        )

    @property
    def source(self):
        if self._model is None:
            self.load()

        return self._source


model_loader = ModelLoader()
