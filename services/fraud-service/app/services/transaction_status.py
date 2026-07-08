from sqlalchemy import text


RISK_LEVEL_TO_TRANSACTION_STATUS = {
    "LOW": "APPROVED",
    "MEDIUM": "REVIEW",
    "HIGH": "BLOCKED",
}


def map_risk_level_to_transaction_status(
    risk_level: str
) -> str:
    return RISK_LEVEL_TO_TRANSACTION_STATUS.get(
        risk_level,
        "REVIEW"
    )


async def update_transaction_status(
    session,
    transaction_id: int,
    status: str
) -> bool:
    result = await session.execute(
        text(
            """
            UPDATE transactions
            SET status = :status
            WHERE id = :transaction_id
            """
        ),
        {
            "transaction_id": transaction_id,
            "status": status
        }
    )

    return result.rowcount > 0
