import asyncio

from fastapi.testclient import TestClient

from tests.helpers import import_service_module


def build_assistant_module(
    tmp_path
):
    database_path = tmp_path / "assistant.db"

    return import_service_module(
        "services/assistant-service",
        env_overrides={
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_COLLECTION_NAME": "assistant-test-collection",
            "OPENAI_API_KEY": "",
        }
    )


def prepare_assistant_app(
    assistant_module,
    monkeypatch
):
    async def fake_ensure_collection():
        return None

    monkeypatch.setattr(
        assistant_module.qdrant_store,
        "ensure_collection",
        fake_ensure_collection
    )


def test_assistant_health_endpoint(
    tmp_path,
    monkeypatch
):
    assistant_module = build_assistant_module(
        tmp_path
    )
    prepare_assistant_app(
        assistant_module,
        monkeypatch
    )

    with TestClient(assistant_module.app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "req-assistant-1",
                "X-Correlation-ID": "corr-assistant-1"
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "service": "assistant-service",
        "status": "running",
        "assistant_mode": "retrieval_only",
        "qdrant_collection": "assistant-test-collection"
    }
    assert response.headers["X-Request-ID"] == "req-assistant-1"
    assert response.headers["X-Correlation-ID"] == "corr-assistant-1"


def test_reindex_endpoint_indexes_documents(
    tmp_path,
    monkeypatch
):
    assistant_module = build_assistant_module(
        tmp_path
    )
    prepare_assistant_app(
        assistant_module,
        monkeypatch
    )

    captured = {}

    async def fake_fetch_fraud_knowledge_records(
        session,
        *,
        limit
    ):
        captured["limit"] = limit
        return [
            assistant_module.FraudKnowledgeRecord(
                alert_id=11,
                transaction_id=77,
                user_id=42,
                amount=12000.0,
                currency="USD",
                country="NG",
                device_type="ios",
                transaction_status="BLOCKED",
                transaction_created_at=None,
                fraud_score=0.9,
                fraud_probability=0.95,
                risk_level="HIGH",
                alert_created_at=None,
                model_name="FraudDetectionModel",
                model_version="5",
                model_role="CHAMPION",
                model_source="registry://fraud-model",
                features_json='{"amount": 12000.0}',
                notification_summary="SMS:SENT",
                credit_score=710.0,
                repayment_probability=0.88,
                score_band="A2"
            )
        ]

    async def fake_upsert_documents(documents):
        captured["documents"] = documents

    monkeypatch.setattr(
        assistant_module,
        "fetch_fraud_knowledge_records",
        fake_fetch_fraud_knowledge_records
    )
    monkeypatch.setattr(
        assistant_module.qdrant_store,
        "upsert_documents",
        fake_upsert_documents
    )

    with TestClient(assistant_module.app) as client:
        response = client.post(
            "/knowledge/reindex",
            json={
                "limit": 25
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "collection_name": "assistant-test-collection",
        "indexed_count": 1
    }
    assert captured["limit"] == 25
    assert len(captured["documents"]) == 1
    assert captured["documents"][0]["id"] == 11
    assert captured["documents"][0]["payload"]["transaction_id"] == 77


def test_query_endpoint_returns_sources_and_previous_response_id(
    tmp_path,
    monkeypatch
):
    assistant_module = build_assistant_module(
        tmp_path
    )
    prepare_assistant_app(
        assistant_module,
        monkeypatch
    )

    captured = {}

    async def fake_answer_question(
        *,
        question,
        previous_response_id,
        top_k
    ):
        captured["question"] = question
        captured["previous_response_id"] = previous_response_id
        captured["top_k"] = top_k
        return {
            "answer": "Transaction 77 was blocked after a high-risk fraud alert.",
            "assistant_mode": "llm_retrieval",
            "response_id": "resp_123",
            "sources": [
                {
                    "alert_id": 11,
                    "transaction_id": 77,
                    "risk_level": "HIGH",
                    "score": 0.9,
                    "snippet": "Alert 11 for transaction 77.",
                    "document": "Alert 11 for transaction 77.",
                    "similarity_score": 0.97,
                }
            ]
        }

    monkeypatch.setattr(
        assistant_module,
        "answer_question",
        fake_answer_question
    )

    with TestClient(assistant_module.app) as client:
        response = client.post(
            "/assistant/query",
            json={
                "question": "What happened with transaction 77?",
                "previous_response_id": "resp_prev",
                "top_k": 3
            }
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Transaction 77 was blocked after a high-risk fraud alert.",
        "assistant_mode": "llm_retrieval",
        "response_id": "resp_123",
        "previous_response_id": "resp_prev",
        "sources": [
            {
                "alert_id": 11,
                "transaction_id": 77,
                "risk_level": "HIGH",
                "score": 0.9,
                "snippet": "Alert 11 for transaction 77.",
                "similarity_score": 0.97
            }
        ]
    }
    assert captured == {
        "question": "What happened with transaction 77?",
        "previous_response_id": "resp_prev",
        "top_k": 3
    }


def test_build_index_documents_uses_zero_vectors_without_openai(
    tmp_path,
    monkeypatch
):
    assistant_module = build_assistant_module(
        tmp_path
    )

    async def fake_embed_texts(texts):
        raise AssertionError("embed_texts should not be called")

    monkeypatch.setattr(
        assistant_module.openai_service,
        "embed_texts",
        fake_embed_texts
    )

    documents = asyncio.run(
        assistant_module.build_index_documents(
            [
                assistant_module.FraudKnowledgeRecord(
                    alert_id=15,
                    transaction_id=99,
                    user_id=8,
                    amount=3500.0,
                    currency="USD",
                    country="US",
                    device_type="web",
                    transaction_status="REVIEW",
                    transaction_created_at=None,
                    fraud_score=0.4,
                    fraud_probability=0.62,
                    risk_level="MEDIUM",
                    alert_created_at=None,
                    model_name=None,
                    model_version=None,
                    model_role=None,
                    model_source=None,
                    features_json=None,
                    notification_summary=None,
                    credit_score=None,
                    repayment_probability=None,
                    score_band=None
                )
            ]
        )
    )

    assert len(documents) == 1
    assert len(documents[0]["vector"]) == 1536
    assert documents[0]["payload"]["alert_id"] == 15
