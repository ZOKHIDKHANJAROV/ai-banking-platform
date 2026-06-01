import numpy as np
import pandas as pd

from xgboost import XGBClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

import joblib


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
    (
        data["country_risk"] == 1
    )
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

model = XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1
)

model.fit(
    X_train,
    y_train
)

preds = model.predict(X_test)

print(
    classification_report(
        y_test,
        preds
    )
)

joblib.dump(
    model,
    "model.pkl"
)

print("Model saved")