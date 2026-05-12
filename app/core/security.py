from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from jose import jwt

from app.core.config import settings

# Use bcrypt directly to avoid passlib's detect_wrap_bug incompatibility
# with bcrypt >= 4.x (which rejects passwords > 72 bytes).
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(_BCRYPT_ROUNDS)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(
    subject: str,
    role: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    """Return (encoded_token, jti, expires_at)."""
    jti = str(uuid4())
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "email": email,
        "role": role,
        "jti": jti,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expires_at


def create_refresh_token() -> tuple[str, datetime]:
    """Return (opaque_token, expires_at). Stored in DB, not a JWT."""
    token = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError on any failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
