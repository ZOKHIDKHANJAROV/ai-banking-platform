import sys
import types

import pytest

from tests.helpers import import_service_module


class DummyProbabilityModel:
    def predict_proba(self, features):
        return [[0.15, 0.85]]


class DummyPredictionModel:
    def predict(self, features):
        return [1]


class DummyVersion:
    def __init__(
        self,
        version: str,
        run_id: str | None = None,
        current_stage: str | None = None,
        source: str | None = None
    ):
        self.version = version
        self.run_id = run_id or f"run-{version}"
        self.current_stage = current_stage or ""
        self.source = source or f"models:/m-{version}"


class DummyRunInfo:
    def __init__(
        self,
        experiment_id: str,
        artifact_uri: str
    ):
        self.experiment_id = experiment_id
        self.artifact_uri = artifact_uri


class DummyRun:
    def __init__(
        self,
        experiment_id: str,
        artifact_uri: str
    ):
        self.info = DummyRunInfo(
            experiment_id=experiment_id,
            artifact_uri=artifact_uri
        )


def build_fake_mlflow(
    versions,
    loaded_uris,
    artifact_uri_builder=None
):
    artifact_uri_builder = artifact_uri_builder or (
        lambda run_id: f"mlflow-artifacts:/1/{run_id}/artifacts"
    )

    def search_model_versions(filter_string):
        return versions

    def get_run(run_id):
        return DummyRun(
            experiment_id="1",
            artifact_uri=artifact_uri_builder(run_id)
        )

    def load_model(model_uri):
        loaded_uris.append(model_uri)
        return DummyProbabilityModel()

    fake_module = types.SimpleNamespace(
        tracking_uri=None,
        set_tracking_uri=lambda uri: setattr(
            fake_module,
            "tracking_uri",
            uri
        ),
        MlflowClient=lambda tracking_uri=None: types.SimpleNamespace(
            tracking_uri=tracking_uri,
            search_model_versions=search_model_versions,
            get_run=get_run
        ),
        pyfunc=types.SimpleNamespace(
            load_model=load_model
        )
    )

    return fake_module


def build_model_loader_module(
    monkeypatch,
    mlflow_module,
    stage="latest"
):
    monkeypatch.setitem(
        sys.modules,
        "mlflow",
        mlflow_module
    )

    return import_service_module(
        "services/fraud-service",
        module_name="app.services.model_loader",
        env_overrides={
            "DATABASE_URL": "sqlite+aiosqlite:///fraud-loader.db",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "MLFLOW_TRACKING_URI": "http://mlflow-test:5000",
            "MLFLOW_MODEL_NAME": "FraudDetectionModel",
            "MLFLOW_MODEL_STAGE": stage
        }
    )


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def test_model_loader_loads_latest_registered_version(
    monkeypatch
):
    loaded_uris = []
    fake_mlflow = build_fake_mlflow(
        versions=[
            DummyVersion("2"),
            DummyVersion("5"),
            DummyVersion("3")
        ],
        loaded_uris=loaded_uris
    )
    model_loader_module = build_model_loader_module(
        monkeypatch,
        fake_mlflow
    )
    loader = model_loader_module.ModelLoader()

    loader.load()

    assert fake_mlflow.tracking_uri == "http://mlflow-test:5000"
    assert [
        normalize_path(path)
        for path in loaded_uris
    ] == [
        "/mlflow/artifacts/1/models/m-5/artifacts"
    ]
    assert normalize_path(loader.source) == "/mlflow/artifacts/1/models/m-5/artifacts"


def test_model_loader_uses_explicit_stage_uri(
    monkeypatch
):
    loaded_uris = []
    fake_mlflow = build_fake_mlflow(
        versions=[
            DummyVersion(
                version="4",
                current_stage="Production"
            )
        ],
        loaded_uris=loaded_uris
    )
    model_loader_module = build_model_loader_module(
        monkeypatch,
        fake_mlflow,
        stage="Production"
    )
    loader = model_loader_module.ModelLoader()

    loader.load()

    assert [
        normalize_path(path)
        for path in loaded_uris
    ] == [
        "/mlflow/artifacts/1/models/m-4/artifacts"
    ]


def test_model_loader_raises_when_registry_is_empty(
    monkeypatch
):
    fake_mlflow = build_fake_mlflow(
        versions=[],
        loaded_uris=[]
    )
    model_loader_module = build_model_loader_module(
        monkeypatch,
        fake_mlflow
    )
    loader = model_loader_module.ModelLoader()

    with pytest.raises(
        RuntimeError,
        match="No registered MLflow model versions found"
    ):
        loader.load()


def test_model_loader_prefers_predict_proba(
    monkeypatch
):
    fake_mlflow = build_fake_mlflow(
        versions=[],
        loaded_uris=[]
    )
    model_loader_module = build_model_loader_module(
        monkeypatch,
        fake_mlflow
    )
    loader = model_loader_module.ModelLoader()
    loader._model = DummyProbabilityModel()

    probability = loader.predict_probability(
        features=None
    )

    assert probability == 0.85


def test_model_loader_normalizes_predict_output(
    monkeypatch
):
    fake_mlflow = build_fake_mlflow(
        versions=[],
        loaded_uris=[]
    )
    model_loader_module = build_model_loader_module(
        monkeypatch,
        fake_mlflow
    )
    loader = model_loader_module.ModelLoader()
    loader._model = DummyPredictionModel()

    probability = loader.predict_probability(
        features=None
    )

    assert probability == 1.0
