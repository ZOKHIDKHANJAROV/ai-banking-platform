from app.services.model_loader import (
    ModelLoader
)


class DummyProbabilityModel:
    def predict_proba(self, features):
        return [[0.15, 0.85]]


class DummyPredictionModel:
    def predict(self, features):
        return [1]


def test_model_loader_prefers_predict_proba():
    loader = ModelLoader()
    loader._model = DummyProbabilityModel()

    probability = loader.predict_probability(
        features=None
    )

    assert probability == 0.85


def test_model_loader_normalizes_predict_output():
    loader = ModelLoader()
    loader._model = DummyPredictionModel()

    probability = loader.predict_probability(
        features=None
    )

    assert probability == 1.0
