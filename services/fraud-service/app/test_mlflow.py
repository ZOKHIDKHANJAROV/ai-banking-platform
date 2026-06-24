from app.services.mlflow_model_loader import (
    model
)

result = model.predict([
    [50000, 15, 1, 1, 1]
])

print(result)