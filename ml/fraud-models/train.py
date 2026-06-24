import mlflow
import mlflow.xgboost

import pandas as pd

from xgboost import XGBClassifier

from sklearn.metrics import accuracy_score

data = pd.read_csv(
    "fraud_dataset.csv"
)

X = data.drop(
    columns=["fraud"]
)

y = data["fraud"]

mlflow.set_tracking_uri(
    "http://localhost:5000"
)

mlflow.set_experiment(
    "fraud-detection"
)

with mlflow.start_run():

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )

    model.fit(X, y)

    predictions = model.predict(X)

    accuracy = accuracy_score(
        y,
        predictions
    )

    mlflow.log_param(
        "n_estimators",
        100
    )

    mlflow.log_param(
        "max_depth",
        5
    )

    mlflow.log_metric(
        "accuracy",
        accuracy
    )

    mlflow.xgboost.log_model(
        model,
        name="fraud-model"
    )

    print(
        f"Accuracy: {accuracy:.4f}"
    )