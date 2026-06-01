import pandas as pd

from app.services.model_loader import (
    model
)


def predict_fraud_probability(
    amount,
    tx_count,
    country_risk,
    country_changed
):

    features = pd.DataFrame([
        {
            "amount": amount,
            "tx_count": tx_count,
            "country_risk": country_risk,
            "country_changed": country_changed
        }
    ])

    probability = model.predict_proba(
        features
    )[0][1]

    return float(probability)