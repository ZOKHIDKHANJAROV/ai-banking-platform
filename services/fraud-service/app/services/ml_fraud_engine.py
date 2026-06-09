import joblib
import numpy as np

model = joblib.load(
    "fraud_model.pkl"
)


def predict_fraud_probability(
    features: list
):

    probability = model.predict_proba(
        np.array([features])
    )[0][1]

    return float(probability)