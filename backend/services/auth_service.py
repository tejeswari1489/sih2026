"""
Auth Service — JWT token generation & verification, password hashing with direct bcrypt.
"""

import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt

# ---------------------------------------------------------------------------
# Config  (override via .env)
# ---------------------------------------------------------------------------
SECRET_KEY      = os.getenv("JWT_SECRET_KEY", "sih-super-secret-change-in-prod-2026")
ALGORITHM       = "HS256"
ACCESS_EXPIRE_H = int(os.getenv("JWT_EXPIRE_HOURS", "12"))


# ---------------------------------------------------------------------------
# Password helpers (Direct bcrypt implementation)
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
def create_access_token(data: dict) -> str:
    """Create a signed JWT that expires in ACCESS_EXPIRE_H hours."""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=ACCESS_EXPIRE_H)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Raises JWTError on invalid / expired tokens.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
