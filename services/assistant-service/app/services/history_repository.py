from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text


@dataclass
class FraudKnowledgeRecord:
    alert_id: int
    transaction_id: int
    user_id: int | None
    amount: float | None
    currency: str | None
    country: str | None
    device_type: str | None
    transaction_status: str | None
    transaction_created_at: datetime | None
    fraud_score: float
    fraud_probability: float
    risk_level: str
    alert_created_at: datetime | None
    model_name: str | None
    model_version: str | None
    model_role: str | None
    model_source: str | None
    features_json: str | None
    notification_summary: str | None
    credit_score: float | None
    repayment_probability: float | None
    score_band: str | None


QUERY = text(
    """
    WITH latest_predictions AS (
        SELECT DISTINCT ON (mp.transaction_id)
            mp.transaction_id,
            mp.model_name,
            mp.model_version,
            mp.model_role,
            mp.model_source,
            mp.features_json
        FROM model_predictions mp
        WHERE COALESCE(mp.is_live_decision, TRUE) = TRUE
        ORDER BY mp.transaction_id, mp.created_at DESC, mp.id DESC
    ),
    notification_rollups AS (
        SELECT
            n.transaction_id,
            string_agg(
                n.channel || ':' || n.status,
                ', ' ORDER BY n.channel || ':' || n.status
            ) AS notification_summary
        FROM notifications n
        GROUP BY n.transaction_id
    ),
    latest_scores AS (
        SELECT DISTINCT ON (cs.user_id)
            cs.user_id,
            cs.credit_score,
            cs.repayment_probability,
            cs.score_band
        FROM credit_scores cs
        ORDER BY cs.user_id, cs.created_at DESC, cs.id DESC
    )
    SELECT
        fa.id AS alert_id,
        fa.transaction_id,
        t.user_id,
        t.amount,
        t.currency,
        t.country,
        t.device_type,
        t.status AS transaction_status,
        t.created_at AS transaction_created_at,
        fa.fraud_score,
        fa.fraud_probability,
        fa.risk_level,
        fa.created_at AS alert_created_at,
        lp.model_name,
        lp.model_version,
        lp.model_role,
        lp.model_source,
        lp.features_json,
        nr.notification_summary,
        ls.credit_score,
        ls.repayment_probability,
        ls.score_band
    FROM fraud_alerts fa
    LEFT JOIN transactions t
        ON t.id = fa.transaction_id
    LEFT JOIN latest_predictions lp
        ON lp.transaction_id = fa.transaction_id
    LEFT JOIN notification_rollups nr
        ON nr.transaction_id = fa.transaction_id
    LEFT JOIN latest_scores ls
        ON ls.user_id = t.user_id
    ORDER BY fa.created_at DESC, fa.id DESC
    LIMIT :limit
    """
)


async def fetch_fraud_knowledge_records(
    session,
    *,
    limit: int
) -> list[FraudKnowledgeRecord]:
    result = await session.execute(
        QUERY,
        {"limit": limit}
    )

    records = []

    for row in result.mappings():
        records.append(
            FraudKnowledgeRecord(
                alert_id=row["alert_id"],
                transaction_id=row["transaction_id"],
                user_id=row["user_id"],
                amount=row["amount"],
                currency=row["currency"],
                country=row["country"],
                device_type=row["device_type"],
                transaction_status=row["transaction_status"],
                transaction_created_at=row["transaction_created_at"],
                fraud_score=row["fraud_score"],
                fraud_probability=row["fraud_probability"],
                risk_level=row["risk_level"],
                alert_created_at=row["alert_created_at"],
                model_name=row["model_name"],
                model_version=row["model_version"],
                model_role=row["model_role"],
                model_source=row["model_source"],
                features_json=row["features_json"],
                notification_summary=row["notification_summary"],
                credit_score=row["credit_score"],
                repayment_probability=row["repayment_probability"],
                score_band=row["score_band"],
            )
        )

    return records
