"""
FastAPI Dependencies
- Authentication
- Authorization
- Database Dependencies
- Audit Logging
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import AuditLog, User, UserRole

# ==========================================================
# Security Scheme
# ==========================================================

security = HTTPBearer()


# ==========================================================
# Current Authenticated User
# ==========================================================

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Return currently authenticated active user."""

    payload = decode_token(
        credentials.credentials,
        expected_type="access",
    )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id",
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


# ==========================================================
# Admin Dependency
# ==========================================================

async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow only admin users."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


# ==========================================================
# Audit Logging
# ==========================================================

async def log_audit(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    action: str,
    resource: str,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    """Create audit log entry."""

    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details or {},
        ip_address=ip,
    )

    db.add(audit)


# ==========================================================
# Client IP
# ==========================================================

def get_client_ip(request: Request) -> str:
    """Return real client IP."""

    forwarded = request.headers.get("X-Forwarded-For")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"