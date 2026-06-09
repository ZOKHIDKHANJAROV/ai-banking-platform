import pandas as pd

from xgboost import XGBClassifier

import joblib

data = pd.read_csv(
    "fraud_dataset.csv"
)

X = data.drop(
    columns=["fraud"]
)

y = data["fraud"]

model = XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1
)

model.fit(X, y)

joblib.dump(
    model,
    "fraud_model.pkl"
)

print(
    "Model saved"
)