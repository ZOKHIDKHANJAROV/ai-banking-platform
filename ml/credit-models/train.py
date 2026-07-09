import asyncio
import json
import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


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


TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "http://localhost:5000"
)
MODEL_NAME = os.getenv(
    "MLFLOW_MODEL_NAME",
    "CreditScoringModel"
)
EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "credit-scoring-registry"
)
TRAINING_DATABASE_URL = os.getenv(
    "TRAINING_DATABASE_URL"
) or os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:admin@localhost:5432/banking"
)
MODEL_PARAMS = {
    "model_type": "StandardScaler+LogisticRegression",
    "max_iter": 1000,
    "random_state": 42
}


def build_training_dataframe(
    rows: int = 30000
) -> pd.DataFrame:
    np.random.seed(42)
    data = pd.DataFrame({
        "age": np.random.randint(21, 70, rows),
        "monthly_income": np.random.randint(500, 12000, rows),
        "existing_debt": np.random.randint(0, 25000, rows),
        "credit_history_months": np.random.randint(3, 360, rows),
        "delinquency_count": np.random.randint(0, 8, rows),
        "utilization_ratio": np.random.uniform(0.0, 1.0, rows),
        "active_loans": np.random.randint(0, 6, rows)
    })
    data["debt_to_income_ratio"] = (
        data["existing_debt"] / data["monthly_income"]
    ).clip(upper=5.0)
    data["repaid"] = (
        (
            (data["monthly_income"] > 2500)
            &
            (data["debt_to_income_ratio"] < 1.2)
            &
            (data["utilization_ratio"] < 0.75)
        )
        &
        (data["delinquency_count"] < 3)
        &
        (data["credit_history_months"] > 12)
    ).astype(int)

    return data


def build_model():
    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler()
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=MODEL_PARAMS["max_iter"],
                    random_state=MODEL_PARAMS["random_state"]
                )
            )
        ]
    )


def train_model():
    data = build_training_dataframe()
    features = data[
        [
            "age",
            "monthly_income",
            "existing_debt",
            "credit_history_months",
            "delinquency_count",
            "utilization_ratio",
            "active_loans",
            "debt_to_income_ratio"
        ]
    ]
    target = data["repaid"]

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42
    )

    model = build_model()
    model.fit(
        X_train,
        y_train
    )
    predictions = model.predict(
        X_test
    )
    accuracy = accuracy_score(
        y_test,
        predictions
    )

    return model, accuracy


def find_model_version(
    client,
    run_id: str
) -> int | None:
    versions = client.search_model_versions(
        f"name = '{MODEL_NAME}'"
    )
    matching_versions = [
        item
        for item in versions
        if item.run_id == run_id
    ]

    if not matching_versions:
        return None

    latest = max(
        matching_versions,
        key=lambda item: int(item.version)
    )

    return int(latest.version)


def normalize_database_url(
    database_url: str
) -> str:
    return (
        database_url
        .replace("+asyncpg", "")
        .replace("+aiosqlite", "")
    )


def persist_training_log(
    *,
    database_url: str,
    experiment_name: str,
    model_name: str,
    model_version: int | None,
    run_id: str | None,
    accuracy: float | None,
    parameters: dict,
    metrics: dict,
    status: str,
    error_message: str | None = None
):
    normalized_database_url = normalize_database_url(
        database_url
    )

    if normalized_database_url.startswith(
        "sqlite:///"
    ):
        engine = create_engine(
            normalized_database_url
        )

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS training_logs (
                        id INTEGER PRIMARY KEY,
                        experiment_name VARCHAR NOT NULL,
                        model_name VARCHAR NOT NULL,
                        model_version INTEGER NULL,
                        run_id VARCHAR NULL,
                        accuracy FLOAT NULL,
                        parameters_json TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        status VARCHAR NOT NULL,
                        error_message TEXT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO training_logs (
                        experiment_name,
                        model_name,
                        model_version,
                        run_id,
                        accuracy,
                        parameters_json,
                        metrics_json,
                        status,
                        error_message
                    ) VALUES (
                        :experiment_name,
                        :model_name,
                        :model_version,
                        :run_id,
                        :accuracy,
                        :parameters_json,
                        :metrics_json,
                        :status,
                        :error_message
                    )
                    """
                ),
                {
                    "experiment_name": experiment_name,
                    "model_name": model_name,
                    "model_version": model_version,
                    "run_id": run_id,
                    "accuracy": accuracy,
                    "parameters_json": json.dumps(
                        parameters,
                        sort_keys=True
                    ),
                    "metrics_json": json.dumps(
                        metrics,
                        sort_keys=True
                    ),
                    "status": status,
                    "error_message": error_message
                }
            )

        return

    async def persist_with_asyncpg():
        import asyncpg

        url = make_url(
            normalized_database_url
        )
        connection = await asyncpg.connect(
            user=url.username,
            password=url.password,
            host=url.host,
            port=url.port or 5432,
            database=url.database
        )

        try:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS training_logs (
                    id SERIAL PRIMARY KEY,
                    experiment_name VARCHAR NOT NULL,
                    model_name VARCHAR NOT NULL,
                    model_version INTEGER NULL,
                    run_id VARCHAR NULL,
                    accuracy DOUBLE PRECISION NULL,
                    parameters_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    status VARCHAR NOT NULL,
                    error_message TEXT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            await connection.execute(
                """
                INSERT INTO training_logs (
                    experiment_name,
                    model_name,
                    model_version,
                    run_id,
                    accuracy,
                    parameters_json,
                    metrics_json,
                    status,
                    error_message
                ) VALUES (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7,
                    $8,
                    $9
                )
                """,
                experiment_name,
                model_name,
                model_version,
                run_id,
                accuracy,
                json.dumps(
                    parameters,
                    sort_keys=True
                ),
                json.dumps(
                    metrics,
                    sort_keys=True
                ),
                status,
                error_message
            )
        finally:
            await connection.close()

    asyncio.run(
        persist_with_asyncpg()
    )


def register_model(
    model,
    accuracy: float
):
    import mlflow
    import mlflow.sklearn

    mlflow.set_tracking_uri(
        TRACKING_URI
    )
    mlflow.set_experiment(
        EXPERIMENT_NAME
    )

    with mlflow.start_run() as run:
        for key, value in MODEL_PARAMS.items():
            mlflow.log_param(
                key,
                value
            )

        mlflow.log_metric(
            "accuracy",
            accuracy
        )

        mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            registered_model_name=MODEL_NAME,
            serialization_format="cloudpickle"
        )

    client = mlflow.MlflowClient(
        tracking_uri=TRACKING_URI
    )

    return {
        "run_id": run.info.run_id,
        "model_version": find_model_version(
            client,
            run.info.run_id
        ),
        "metrics": {
            "accuracy": accuracy
        }
    }


def main():
    model, accuracy = train_model()
    print(
        f"Accuracy: {accuracy}"
    )

    try:
        registration = register_model(
            model,
            accuracy
        )
        persist_training_log(
            database_url=TRAINING_DATABASE_URL,
            experiment_name=EXPERIMENT_NAME,
            model_name=MODEL_NAME,
            model_version=registration["model_version"],
            run_id=registration["run_id"],
            accuracy=accuracy,
            parameters=MODEL_PARAMS,
            metrics=registration["metrics"],
            status="SUCCESS"
        )
    except Exception as exc:
        persist_training_log(
            database_url=TRAINING_DATABASE_URL,
            experiment_name=EXPERIMENT_NAME,
            model_name=MODEL_NAME,
            model_version=None,
            run_id=None,
            accuracy=accuracy,
            parameters=MODEL_PARAMS,
            metrics={
                "accuracy": accuracy
            },
            status="FAILED",
            error_message=str(exc)
        )
        print(
            f"Skipping MLflow registration: {exc}"
        )


if __name__ == "__main__":
    main()
