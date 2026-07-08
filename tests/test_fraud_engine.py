from app.services.fraud_engine import (
    calculate_fraud_score
)


def test_calculate_fraud_score_caps_at_one():
    score = calculate_fraud_score(
        amount=20000,
        country="NG",
        tx_count=50,
        previous_country="US"
    )

    assert score == 1.0


def test_calculate_fraud_score_for_low_risk_transaction():
    score = calculate_fraud_score(
        amount=50,
        country="US",
        tx_count=1,
        previous_country="US"
    )

    assert score == 0.0
