import sys

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


for stream_name in ["stdout", "stderr"]:
    stream = getattr(
        sys,
        stream_name,
        None
    )

    if stream is not None and hasattr(stream, "reconfigure"):
        stream.reconfigure(
            encoding="utf-8"
        )

np.random.seed(42)

EXPERIMENT_NAME = "fraud-detection-registry"

rows = 50000

data = pd.DataFrame({
    "amount": np.random.randint(10, 20000, rows),
    "tx_count": np.random.randint(1, 50, rows),
    "country_risk": np.random.randint(0, 2, rows),
    "country_changed": np.random.randint(0, 2, rows)
})

data["fraud"] = (
    (
        (data["amount"] > 10000)
        &
        (data["tx_count"] > 15)
    )
    |
    (data["country_risk"] == 1)
    |
    (
        data["country_changed"] == 1
        &
        (data["tx_count"] > 10)
    )
).astype(int)

X = data[
    [
        "amount",
        "tx_count",
        "country_risk",
        "country_changed"
    ]
]

y = data["fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

model = RandomForestClassifier(
    n_estimators=120,
    max_depth=8,
    random_state=42
)

model.fit(
    X_train,
    y_train
)

preds = model.predict(
    X_test
)

accuracy = accuracy_score(
    y_test,
    preds
)

print(
    f"Accuracy: {accuracy}"
)

try:
    import mlflow
    import mlflow.sklearn

    mlflow.set_tracking_uri(
        "http://localhost:5000"
    )

    mlflow.set_experiment(
        EXPERIMENT_NAME
    )

    with mlflow.start_run():
        mlflow.log_param(
            "model_type",
            "RandomForestClassifier"
        )
        mlflow.log_param(
            "n_estimators",
            120
        )
        mlflow.log_param(
            "max_depth",
            8
        )
        mlflow.log_metric(
            "accuracy",
            accuracy
        )

        mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            registered_model_name="FraudDetectionModel",
            serialization_format="cloudpickle"
        )
except Exception as exc:
    print(
        f"Skipping MLflow registration: {exc}"
    )
