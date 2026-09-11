"""
Authentication Router (Production Ready)
=========================================

Handles registration, login, token refresh/rotation, logout, session
listing, OTP-based email verification, OTP-based password reset, and
Google Sign-In.

Bug fixes vs. the original version:
  * ``/auth/refresh`` and ``/auth/logout`` used raw ``jwt.decode()`` without
    the ``audience``/``issuer`` the tokens are actually signed with (see
    ``app.core.security``). PyJWT raises ``InvalidAudienceError`` whenever a
    token has an ``aud`` claim and no ``audience`` is passed to decode() —
    so *every* refresh/logout call failed with a 401/400, even for perfectly
    valid tokens. Fixed by reusing ``app.core.security.decode_token``
    everywhere, which already validates issuer/audience/expiry consistently.
  * ``/auth/refresh`` cast the user id with ``int(user_id)``, but user IDs
    are UUIDs, not integers — this raised an unhandled ``ValueError`` (HTTP
    500) on every refresh. Fixed with ``uuid.UUID(user_id)``.
"""

import asyncio
import json
import logging
import secrets
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user, log_audit
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models import User
from app.schemas import (
    ForgotPassword,
    GoogleAuth,
    OTPVerify,
    ResetPassword,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ==========================================================
# Helpers
# ==========================================================

async def _create_user_session(user_id: uuid.UUID, request: Request, redis: Any) -> dict:
    """Generate a fresh access/refresh token pair and store the refresh
    session in Redis, keyed by ``refresh:{user_id}:{jti}``."""
    sub = str(user_id)
    access_token = create_access_token(data={"sub": sub})
    refresh_token = create_refresh_token(data={"sub": sub})

    # Decode our own freshly-minted token purely to pull out its jti — this
    # goes through the same validated decode path as everywhere else, so it
    # also acts as a sanity check that token creation is configured correctly.
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload is None or not payload.get("jti"):
        logger.error("create_refresh_token did not yield a valid, decodable token with a jti claim.")
        raise HTTPException(status_code=500, detail="Internal server error during token generation")

    jti = payload["jti"]
    session_key = f"refresh:{sub}:{jti}"
    expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    session_data = {
        "device_info": f"{get_client_ip(request)} | {request.headers.get('user-agent', 'Unknown Device')}",
        "last_active": datetime.now(timezone.utc).isoformat(),
    }
    await redis.setex(session_key, expire_seconds, json.dumps(session_data))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def _generate_otp() -> str:
    """Cryptographically-secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def _store_otp(redis: Any, purpose: str, email: str, otp: str) -> None:
    await redis.setex(f"otp:{purpose}:{email.lower()}", settings.OTP_EXPIRE_MINUTES * 60, otp)


async def _verify_and_consume_otp(redis: Any, purpose: str, email: str, otp: str) -> bool:
    key = f"otp:{purpose}:{email.lower()}"
    stored = await redis.get(key)
    if stored is None:
        return False
    stored_str = stored.decode() if isinstance(stored, bytes) else stored
    if not secrets.compare_digest(stored_str, otp):
        return False
    await redis.delete(key)
    return True


def _send_email_sync(to_email: str, subject: str, body: str) -> None:
    """Best-effort SMTP send. Falls back to logging the message (dev mode)
    when SMTP credentials aren't configured, so local development/demos keep
    working without a real mail server."""
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.info("[DEV MODE - SMTP not configured] Email to %s | %s\n%s", to_email, subject, body)
        return

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = to_email

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(message["From"], [to_email], message.as_string())
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)


async def _send_email(to_email: str, subject: str, body: str) -> None:
    await asyncio.to_thread(_send_email_sync, to_email, subject, body)


# ==========================================================
# Register
# ==========================================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        is_verified=True,  # Direct verification for MVP. Flip to False and
        # call POST /auth/send-verification-otp if you want to require OTP
        # email verification before login.
    )
    db.add(user)
    await db.flush()

    await log_audit(db, user.id, "register", "user", {}, get_client_ip(request))
    await db.commit()

    return {"message": "Registration successful."}


# ==========================================================
# Login
# ==========================================================
@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    try:
        redis = await get_redis()
        tokens = await _create_user_session(user.id, request, redis)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login/session error: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    await log_audit(db, user.id, "login", "auth", {}, get_client_ip(request))
    await db.commit()

    return TokenResponse(**tokens)


# ==========================================================
# Token Refresh (rotates the refresh token)
# ==========================================================
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    data: RefreshRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user_id_str = payload.get("sub")
    jti = payload.get("jti")
    if not user_id_str or not jti:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account no longer exists")

    try:
        redis = await get_redis()
        session_key = f"refresh:{user_id_str}:{jti}"

        session_exists = await redis.get(session_key)
        if not session_exists:
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        await redis.delete(session_key)  # rotate: the old refresh token can't be replayed
        tokens = await _create_user_session(user.id, request, redis)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Refresh error: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    return TokenResponse(**tokens)


# ==========================================================
# Logout / Logout-all / Active sessions
# ==========================================================
@router.post("/logout")
async def logout(
    data: LogoutRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if payload is None or not payload.get("jti"):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    try:
        redis = await get_redis()
        await redis.delete(f"refresh:{current_user.id}:{payload['jti']}")
    except Exception as exc:
        logger.warning("Logout Redis error (continuing so the client isn't stuck): %s", exc)

    await log_audit(db, current_user.id, "logout", "auth", {}, get_client_ip(request))
    await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        redis = await get_redis()
        async for key in redis.scan_iter(f"refresh:{current_user.id}:*"):
            await redis.delete(key)
    except Exception as exc:
        logger.error("Logout-all error: %s", exc)
        raise HTTPException(status_code=503, detail="Service unavailable")

    await log_audit(db, current_user.id, "logout_all", "auth", {}, get_client_ip(request))
    await db.commit()
    return {"message": "Logged out from all devices"}


@router.get("/sessions")
async def sessions(current_user: Annotated[User, Depends(get_current_user)]):
    active_sessions = []
    try:
        redis = await get_redis()
        async for key in redis.scan_iter(f"refresh:{current_user.id}:*"):
            raw = await redis.get(key)
            if not raw:
                continue
            raw_str = raw.decode() if isinstance(raw, bytes) else raw
            key_str = key.decode() if isinstance(key, bytes) else key
            try:
                meta = json.loads(raw_str)
                device_info = meta.get("device_info", "Unknown Device")
                last_active = meta.get("last_active", "Unknown")
            except json.JSONDecodeError:
                device_info, last_active = raw_str, "Unknown"

            active_sessions.append(
                {
                    "session_id": key_str.split(":")[-1],
                    "device_info": device_info,
                    "last_active": last_active,
                }
            )
    except Exception as exc:
        logger.error("Session retrieval error: %s", exc)
        raise HTTPException(status_code=503, detail="Unable to retrieve sessions")

    return {"total": len(active_sessions), "active_sessions": active_sessions}


# ==========================================================
# Email Verification (OTP)
# ==========================================================
@router.post("/send-verification-otp")
async def send_verification_otp(
    data: ForgotPassword,  # body shape is just {email}
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user and not user.is_verified:
        otp = _generate_otp()
        redis = await get_redis()
        await _store_otp(redis, "verify", data.email, otp)
        await _send_email(
            data.email,
            "Verify your MediCare AI account",
            f"Your verification code is {otp}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes.",
        )

    # Identical response whether or not the account exists/needs verification,
    # so this endpoint can't be used to enumerate registered emails.
    return {"message": "If the account exists and needs verification, an OTP has been sent."}


@router.post("/verify-otp")
async def verify_otp(
    data: OTPVerify,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    redis = await get_redis()
    ok = await _verify_and_consume_otp(redis, "verify", data.email, data.otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()
    return {"message": "Email verified successfully."}


# ==========================================================
# Forgot / Reset Password (OTP)
# ==========================================================
@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPassword,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user:
        otp = _generate_otp()
        redis = await get_redis()
        await _store_otp(redis, "reset", data.email, otp)
        await _send_email(
            data.email,
            "MediCare AI password reset code",
            f"Your password reset code is {otp}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
            "If you didn't request this, you can safely ignore this email.",
        )

    return {"message": "If the email exists, a reset OTP has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPassword,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    redis = await get_redis()
    ok = await _verify_and_consume_otp(redis, "reset", data.email, data.otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    # The password (trust boundary) just changed — revoke every existing
    # refresh session so old logins can't keep using the account.
    try:
        async for key in redis.scan_iter(f"refresh:{user.id}:*"):
            await redis.delete(key)
    except Exception as exc:
        logger.warning("Could not revoke sessions after password reset: %s", exc)

    return {"message": "Password reset successful. Please log in with your new password."}


# ==========================================================
# Google Sign-In
# ==========================================================
@router.post("/google", response_model=TokenResponse)
async def google_login(
    data: GoogleAuth,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google Sign-In is not configured on this server")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        idinfo = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            data.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = idinfo.get("email")
    google_id = idinfo.get("sub")
    if not email or not google_id:
        raise HTTPException(status_code=401, detail="Google token missing required claims")
    if not idinfo.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_id  # link an existing email/password account
        else:
            user = User(
                email=email,
                full_name=idinfo.get("name") or email.split("@")[0],
                avatar_url=idinfo.get("picture"),
                google_id=google_id,
                is_verified=True,
                hashed_password=None,
            )
            db.add(user)
        await db.flush()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    try:
        redis = await get_redis()
        tokens = await _create_user_session(user.id, request, redis)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Google login session error: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    await log_audit(db, user.id, "login_google", "auth", {}, get_client_ip(request))
    await db.commit()

    return TokenResponse(**tokens)


# ==========================================================
# Current User Profile
# ==========================================================
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Return the fully loaded authenticated user's profile."""
    return current_user
