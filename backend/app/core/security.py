"""
Security utilities:
- Password hashing (Argon2)
- JWT Access Token
- JWT Refresh Token
- JWT Validation
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ==========================================================
# Password Hashing (Argon2)
# ==========================================================

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password.strip())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password safely."""
    try:
        return pwd_context.verify(
            plain_password.strip(),
            hashed_password,
        )
    except Exception:
        return False


# ==========================================================
# JWT Token Creation
# ==========================================================

def _base_payload(
    data: dict[str, Any],
    expire: datetime,
    token_type: str,
) -> dict[str, Any]:
    """Create common JWT payload."""

    now = datetime.now(timezone.utc)

    payload = data.copy()

    payload.update(
        {
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": uuid.uuid4().hex,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "type": token_type,
        }
    )

    return payload


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Generate Access Token."""

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = _base_payload(
        data=data,
        expire=expire,
        token_type="access",
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(
    data: dict[str, Any],
) -> str:
    """Generate Refresh Token."""

    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = _base_payload(
        data=data,
        expire=expire,
        token_type="refresh",
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ==========================================================
# JWT Validation
# ==========================================================

def decode_token(
    token: str,
    expected_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Decode and validate JWT.

    expected_type:
        "access"
        "refresh"
        None -> Skip token type validation
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )

        if (
            expected_type is not None
            and payload.get("type") != expected_type
        ):
            return None

        return payload

    except JWTError:
        return None