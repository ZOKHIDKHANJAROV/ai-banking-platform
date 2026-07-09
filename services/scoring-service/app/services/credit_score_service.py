import json

from sqlalchemy import select

from app.models.credit_score import CreditScore
from app.services.metrics import credit_scores_generated_total
from app.services.metrics import last_credit_score_value


async def save_credit_score(
    *,
    session,
    user_id: int,
    credit_score: float,
    repayment_probability: float,
    score_band: str,
    model_source: str,
    features: dict
):
    score = CreditScore(
        user_id=user_id,
        credit_score=credit_score,
        repayment_probability=repayment_probability,
        score_band=score_band,
        model_source=model_source,
        features_json=json.dumps(
            features,
            sort_keys=True
        )
    )
    session.add(score)
    await session.commit()
    await session.refresh(score)
    credit_scores_generated_total.labels(
        score_band
    ).inc()
    last_credit_score_value.set(
        credit_score
    )

    return score


async def get_scores(
    session
):
    result = await session.execute(
        select(CreditScore).order_by(
            CreditScore.created_at.desc(),
            CreditScore.id.desc()
        )
    )

    return result.scalars().all()


async def get_score_by_id(
    session,
    score_id: int
):
    result = await session.execute(
        select(CreditScore).where(
            CreditScore.id == score_id
        )
    )

    return result.scalar_one_or_none()
