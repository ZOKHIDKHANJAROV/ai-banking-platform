import mlflow
import mlflow.pyfunc

mlflow.set_tracking_uri(
    "http://banking_mlflow:5000"
)

model = mlflow.pyfunc.load_model(
    "models:/FraudDetectionModel/1"
)