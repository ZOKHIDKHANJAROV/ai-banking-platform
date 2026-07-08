import logging
from pathlib import Path

from app.core.config import settings


logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self):
        self._model = None
        self._source = "uninitialized"

    def _get_mlflow(self):
        import mlflow

        return mlflow

    def _get_registered_versions(self):
        mlflow = self._get_mlflow()
        client = mlflow.MlflowClient(
            tracking_uri=settings.MLFLOW_TRACKING_URI
        )

        return client.search_model_versions(
            f"name = '{settings.MLFLOW_MODEL_NAME}'"
        )

    def _resolve_model_version(self):
        versions = self._get_registered_versions()

        if not versions:
            raise RuntimeError(
                "No registered MLflow model versions found for "
                f"{settings.MLFLOW_MODEL_NAME}"
            )

        stage = settings.MLFLOW_MODEL_STAGE.strip()

        if stage and stage.lower() != "latest":
            matching_versions = [
                item
                for item in versions
                if getattr(
                    item,
                    "current_stage",
                    ""
                ).lower() == stage.lower()
            ]

            if not matching_versions:
                raise RuntimeError(
                    "No registered MLflow model versions found for "
                    f"{settings.MLFLOW_MODEL_NAME} in stage {stage}"
                )

            return max(
                matching_versions,
                key=lambda item: int(item.version)
            )

        return max(
            versions,
            key=lambda item: int(item.version)
        )

    def _resolve_model_uri(self):
        mlflow = self._get_mlflow()
        version = self._resolve_model_version()
        client = mlflow.MlflowClient(
            tracking_uri=settings.MLFLOW_TRACKING_URI
        )
        run = client.get_run(
            version.run_id
        )
        artifact_uri = run.info.artifact_uri
        source_uri = getattr(
            version,
            "source",
            ""
        )

        if source_uri.startswith("models:/m-"):
            model_id = source_uri.removeprefix(
                "models:/"
            )
            return (
                version,
                str(
                    Path("/mlflow/artifacts")
                    / run.info.experiment_id
                    / "models"
                    / model_id
                    / "artifacts"
                )
            )

        if artifact_uri.startswith("mlflow-artifacts:/"):
            artifact_root = Path("/mlflow/artifacts") / artifact_uri.removeprefix(
                "mlflow-artifacts:/"
            ).lstrip("/")
            return (
                version,
                str(artifact_root / "model")
            )

        if artifact_uri.startswith("/mlflow/"):
            return (
                version,
                str(Path(artifact_uri) / "model")
            )

        return (
            version,
            f"runs:/{version.run_id}/model"
        )

    def load(self):
        if self._model is not None:
            return self._model

        mlflow = self._get_mlflow()
        mlflow.set_tracking_uri(
            settings.MLFLOW_TRACKING_URI
        )
        version, model_uri = self._resolve_model_uri()

        logger.info(
            "Loading fraud model from MLflow registry version=%s uri=%s",
            version.version,
            model_uri
        )

        self._model = mlflow.pyfunc.load_model(
            model_uri
        )
        self._source = model_uri

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
