import mlflow

MODEL_URI = (
    "models:/FraudDetectionModel/latest"
)

model = mlflow.pyfunc.load_model(
    MODEL_URI
)