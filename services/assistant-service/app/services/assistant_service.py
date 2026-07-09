from app.core.config import settings
from app.services.history_repository import FraudKnowledgeRecord
from app.services.metrics import assistant_retrieved_sources
from app.services.openai_service import openai_service
from app.services.qdrant_store import qdrant_store


def format_record_as_document(
    record: FraudKnowledgeRecord
) -> str:
    parts = [
        f"Alert {record.alert_id} for transaction {record.transaction_id}.",
        f"Risk level {record.risk_level} with fraud score {record.fraud_score:.2f} "
        f"and fraud probability {record.fraud_probability:.2f}.",
    ]

    if record.user_id is not None:
        parts.append(
            f"User {record.user_id} submitted {record.amount} {record.currency} "
            f"from {record.country} on device {record.device_type}."
        )
    if record.transaction_status:
        parts.append(
            f"Transaction status is {record.transaction_status}."
        )
    if record.model_name:
        parts.append(
            f"Champion model {record.model_name} version {record.model_version or 'unknown'} "
            f"produced the live decision."
        )
    if record.notification_summary:
        parts.append(
            f"Notifications sent: {record.notification_summary}."
        )
    if record.credit_score is not None:
        parts.append(
            f"Latest credit score is {record.credit_score:.2f} with repayment probability "
            f"{record.repayment_probability:.2f} in band {record.score_band}."
        )
    if record.features_json:
        parts.append(
            f"Model features snapshot: {record.features_json}."
        )

    return " ".join(parts)


async def build_index_documents(
    records: list[FraudKnowledgeRecord]
) -> list[dict]:
    texts = [
        format_record_as_document(record)
        for record in records
    ]

    if not texts:
        return []

    if openai_service.is_configured:
        vectors = await openai_service.embed_texts(
            texts
        )
    else:
        vectors = [
            [0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS
            for _ in texts
        ]

    return [
        {
            "id": record.alert_id,
            "vector": vector,
            "payload": {
                "alert_id": record.alert_id,
                "transaction_id": record.transaction_id,
                "risk_level": record.risk_level,
                "fraud_score": record.fraud_score,
                "fraud_probability": record.fraud_probability,
                "document": text,
            }
        }
        for record, text, vector in zip(
            records,
            texts,
            vectors,
            strict=True
        )
    ]


def build_retrieval_only_answer(
    question: str,
    sources: list[dict]
) -> str:
    if not sources:
        return (
            "No indexed fraud history matched this question closely enough."
        )

    summary_lines = [
        f"Question: {question}",
        "Most relevant fraud history entries:",
    ]

    for source in sources[:3]:
        summary_lines.append(
            f"- Alert {source['alert_id']} / transaction {source['transaction_id']} "
            f"is {source['risk_level']} risk with score {source['score']:.2f}. "
            f"Context: {source['snippet']}"
        )

    return "\n".join(summary_lines)


async def search_related_records(
    *,
    question: str,
    top_k: int
) -> list[dict]:
    if openai_service.is_configured:
        query_vector = (
            await openai_service.embed_texts(
                [question]
            )
        )[0]
    else:
        query_vector = [0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS

    search_results = await qdrant_store.search(
        query_vector=query_vector,
        limit=top_k
    )

    sources = []

    for item in search_results:
        payload = item.payload or {}
        document = str(
            payload.get(
                "document",
                ""
            )
        )
        sources.append(
            {
                "alert_id": int(payload.get("alert_id", item.id)),
                "transaction_id": int(payload.get("transaction_id", 0)),
                "risk_level": str(payload.get("risk_level", "UNKNOWN")),
                "score": float(payload.get("fraud_score", 0.0)),
                "snippet": document[:500],
                "document": document,
                "similarity_score": float(item.score),
            }
        )

    assistant_retrieved_sources.set(
        len(sources)
    )

    return sources


async def answer_question(
    *,
    question: str,
    previous_response_id: str | None,
    top_k: int
) -> dict:
    sources = await search_related_records(
        question=question,
        top_k=top_k
    )

    if openai_service.is_configured:
        answer, response_id = await openai_service.generate_answer(
            question=question,
            context_blocks=[
                item["document"]
                for item in sources
            ],
            previous_response_id=previous_response_id
        )
        assistant_mode = "llm_retrieval"
    else:
        answer = build_retrieval_only_answer(
            question,
            sources
        )
        response_id = None
        assistant_mode = "retrieval_only"

    return {
        "answer": answer,
        "assistant_mode": assistant_mode,
        "response_id": response_id,
        "sources": sources
    }
