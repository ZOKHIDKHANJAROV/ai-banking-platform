import json

from sqlalchemy import select

from app.models.model_prediction import ModelPrediction


async def save_model_prediction(
    session,
    transaction_id: int,
    fraud_probability: float,
    risk_level: str,
    model_name: str,
    model_version: str | None,
    model_role: str,
    is_live_decision: bool,
    model_source: str,
    features: dict
):
    prediction = ModelPrediction(
        transaction_id=transaction_id,
        fraud_probability=fraud_probability,
        risk_level=risk_level,
        model_name=model_name,
        model_version=model_version,
        model_role=model_role,
        is_live_decision=is_live_decision,
        model_source=model_source,
        features_json=json.dumps(
            features,
            sort_keys=True
        )
    )
    session.add(prediction)
    await session.flush()

    return prediction


async def get_predictions(
    session
):
    result = await session.execute(
        select(ModelPrediction).order_by(
            ModelPrediction.created_at.desc(),
            ModelPrediction.id.desc()
        )
    )

    return result.scalars().all()


async def get_prediction_by_id(
    session,
    prediction_id: int
):
    result = await session.execute(
        select(ModelPrediction).where(
            ModelPrediction.id == prediction_id
        )
    )

    return result.scalar_one_or_none()
