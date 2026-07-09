import logging
from pathlib import Path

from app.core.config import settings


logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(
        self,
        *,
        model_name: str | None = None,
        model_stage: str | None = None,
        role: str = "champion",
        enabled: bool = True
    ):
        self._model = None
        self._source = "uninitialized"
        self._version = None
        self._model_name = (
            model_name
            or settings.MLFLOW_MODEL_NAME
        )
        self._model_stage = (
            model_stage
            or settings.MLFLOW_MODEL_STAGE
        )
        self._role = role.upper()
        self._enabled = enabled

    def _get_mlflow(self):
        import mlflow

        return mlflow

    def _get_registered_versions(self):
        mlflow = self._get_mlflow()
        client = mlflow.MlflowClient(
            tracking_uri=settings.MLFLOW_TRACKING_URI
        )

        return client.search_model_versions(
            f"name = '{self._model_name}'"
        )

    def _resolve_model_version(self):
        versions = self._get_registered_versions()

        if not versions:
            raise RuntimeError(
                "No registered MLflow model versions found for "
                f"{self._model_name}"
            )

        stage = self._model_stage.strip()

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
                    f"{self._model_name} in stage {stage}"
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
        if not self._enabled:
            return None

        if self._model is not None:
            return self._model

        mlflow = self._get_mlflow()
        mlflow.set_tracking_uri(
            settings.MLFLOW_TRACKING_URI
        )
        version, model_uri = self._resolve_model_uri()

        logger.info(
            "Loading %s fraud model from MLflow registry "
            "name=%s stage=%s version=%s uri=%s",
            self._role.lower(),
            self._model_name,
            self._model_stage,
            version.version,
            model_uri
        )

        self._model = mlflow.pyfunc.load_model(
            model_uri
        )
        self._source = model_uri
        self._version = str(version.version)

        return self._model

    def predict_probability(self, features):
        model = self.load()

        if model is None:
            raise RuntimeError(
                f"{self._role.title()} model is not enabled"
            )

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
        if self._model is None and self._enabled:
            self.load()

        return self._source

    @property
    def version(self):
        if self._model is None and self._enabled:
            self.load()

        return self._version

    @property
    def model_name(self):
        return self._model_name

    @property
    def role(self):
        return self._role

    @property
    def is_enabled(self):
        return self._enabled


model_loader = ModelLoader()
challenger_model_loader = ModelLoader(
    model_name=(
        settings.MLFLOW_CHALLENGER_MODEL_NAME
        or settings.MLFLOW_MODEL_NAME
    ),
    model_stage=settings.MLFLOW_CHALLENGER_MODEL_STAGE,
    role="challenger",
    enabled=settings.MLFLOW_ENABLE_CHALLENGER_SHADOW
)
