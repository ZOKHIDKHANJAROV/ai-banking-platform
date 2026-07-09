import sqlite3

from tests.helpers import load_module


def test_credit_training_log_persistence_writes_record(
    tmp_path
):
    train_module = load_module(
        "credit_train_module",
        "ml/credit-models/train.py"
    )
    database_path = tmp_path / "credit-training.db"

    train_module.persist_training_log(
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        experiment_name="credit-scoring-registry",
        model_name="CreditScoringModel",
        model_version=2,
        run_id="credit-run-123",
        accuracy=0.934,
        parameters={"max_iter": 500},
        metrics={"accuracy": 0.934},
        status="SUCCESS"
    )

    with sqlite3.connect(database_path) as connection:
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

    assert row == (
        "credit-scoring-registry",
        "CreditScoringModel",
        2,
        "credit-run-123",
        0.934,
        "SUCCESS"
    )
