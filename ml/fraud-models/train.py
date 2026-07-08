import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

np.random.seed(42)

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
        "fraud-detection"
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

        model_info = mlflow.sklearn.log_model(
            model,
            artifact_path="model"
        )

    mlflow.register_model(
        model_info.model_uri,
        "FraudDetectionModel"
    )
except Exception as exc:
    print(
        f"Skipping MLflow registration: {exc}"
    )
