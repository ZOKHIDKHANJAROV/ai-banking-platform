import joblib
import numpy as np

MODEL_PATH = "models/fraud_model.pkl"

model = joblib.load(
    MODEL_PATH
)


def predict_fraud_probability(
    features: list
):

    probability = model.predict_proba(
        np.array([features])
    )[0][1]

    return float(probability)