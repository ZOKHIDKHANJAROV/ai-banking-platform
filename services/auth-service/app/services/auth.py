from datetime import datetime
from datetime import timedelta
from datetime import timezone

import jwt

from app.core.config import settings


def authenticate_user(
    username: str,
    password: str
) -> bool:
    return (
        username == settings.AUTH_USERNAME
        and password == settings.AUTH_PASSWORD
    )


def create_access_token(
    subject: str
) -> tuple[str, int]:
    issued_at = datetime.now(
        timezone.utc
    )
    expires_at = issued_at + timedelta(
        minutes=settings.JWT_EXPIRES_MINUTES
    )
    payload = {
        "sub": subject,
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER,
        "iat": issued_at,
        "exp": expires_at
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token, settings.JWT_EXPIRES_MINUTES * 60
