from app.main import (
    get_country_features,
    get_risk_level
)
from app.services.ml_fraud_engine import (
    build_features
)


def test_country_feature_flags_detect_changes_and_risk():
    country_risk, country_changed = get_country_features(
        country="NG",
        previous_country="US"
    )

    assert country_risk == 1
    assert country_changed == 1


def test_get_risk_level_uses_expected_thresholds():
    assert get_risk_level(0.9) == "HIGH"
    assert get_risk_level(0.6) == "MEDIUM"
    assert get_risk_level(0.2) == "LOW"


def test_build_features_returns_expected_columns():
    features = build_features(
        amount=99.5,
        tx_count=3,
        country_risk=1,
        country_changed=0
    )

    assert list(features.columns) == [
        "amount",
        "tx_count",
        "country_risk",
        "country_changed"
    ]
    assert features.iloc[0].to_dict() == {
        "amount": 99.5,
        "tx_count": 3.0,
        "country_risk": 1.0,
        "country_changed": 0.0
    }
