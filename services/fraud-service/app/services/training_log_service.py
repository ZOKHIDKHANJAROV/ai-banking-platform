from sqlalchemy import select

from app.models.training_log import TrainingLog


async def get_training_logs(
    session
):
    result = await session.execute(
        select(TrainingLog).order_by(
            TrainingLog.created_at.desc(),
            TrainingLog.id.desc()
        )
    )

    return result.scalars().all()


async def get_training_log_by_id(
    session,
    training_log_id: int
):
    result = await session.execute(
        select(TrainingLog).where(
            TrainingLog.id == training_log_id
        )
    )

    return result.scalar_one_or_none()
