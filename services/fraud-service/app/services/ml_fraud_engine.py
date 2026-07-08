import pandas as pd

from app.services.model_loader import (
    model_loader
)


def build_features(
    amount,
    tx_count,
    country_risk,
    country_changed,
    previous_amount,
    amount_diff,
    device_changed,
    hour_of_day,
    day_of_week
):

    return pd.DataFrame([
        {
            "amount": amount,
            "tx_count": tx_count,
            "country_risk": country_risk,
            "country_changed": country_changed,
            "previous_amount": previous_amount,
            "amount_diff": amount_diff,
            "device_changed": device_changed,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week
        }
    ])


def predict_fraud_probability(
    amount,
    tx_count,
    country_risk,
    country_changed,
    previous_amount,
    amount_diff,
    device_changed,
    hour_of_day,
    day_of_week
):

    features = build_features(
        amount=amount,
        tx_count=tx_count,
        country_risk=country_risk,
        country_changed=country_changed,
        previous_amount=previous_amount,
        amount_diff=amount_diff,
        device_changed=device_changed,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week
    )

    return model_loader.predict_probability(
        features
    )
