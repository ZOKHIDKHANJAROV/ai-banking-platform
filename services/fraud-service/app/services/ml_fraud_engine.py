import pandas as pd

from app.services.model_loader import (
    model_loader
)


def build_features(
    amount,
    tx_count,
    country_risk,
    country_changed
):

    return pd.DataFrame([
        {
            "amount": amount,
            "tx_count": tx_count,
            "country_risk": country_risk,
            "country_changed": country_changed
        }
    ])


def predict_fraud_probability(
    amount,
    tx_count,
    country_risk,
    country_changed
):

    features = build_features(
        amount=amount,
        tx_count=tx_count,
        country_risk=country_risk,
        country_changed=country_changed
    )

    return model_loader.predict_probability(
        features
    )
