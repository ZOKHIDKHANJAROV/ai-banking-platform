from app.services.ml_fraud_engine import (
    predict_fraud_probability
)

prob = predict_fraud_probability(
    [50000, 15, 1, 1, 1]
)

print(prob)