import sqlite3

from tests.helpers import load_module


def test_persist_training_log_writes_record(
    tmp_path
):
    train_module = load_module(
        "fraud_train_module",
        "ml/fraud-models/train.py"
    )
    database_path = tmp_path / "training-logs.db"

    train_module.persist_training_log(
        database_url=f"sqlite:///{database_path.as_posix()}",
        experiment_name="fraud-detection-registry",
        model_name="FraudDetectionModel",
        model_version=7,
        run_id="run-777",
        accuracy=0.987,
        parameters={
            "n_estimators": 120
        },
        metrics={
            "accuracy": 0.987
        },
        status="SUCCESS",
        error_message=None
    )

    connection = sqlite3.connect(
        database_path
    )
    row = connection.execute(
        """
        SELECT
            experiment_name,
            model_name,
            model_version,
            run_id,
            accuracy,
            status
        FROM training_logs
        """
    ).fetchone()
    connection.close()

    assert row == (
        "fraud-detection-registry",
        "FraudDetectionModel",
        7,
        "run-777",
        0.987,
        "SUCCESS"
    )
