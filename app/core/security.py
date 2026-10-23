# ============================================================
# app/core/security.py
# ============================================================
# PURPOSE:
#   Handles all authentication logic:
#   1. Hashing passwords (so we never store plain text)
#   2. Creating JWT tokens (login tokens given to users)
#   3. Verifying JWT tokens (checking if a user is logged in)
#
# JWT = JSON Web Token
#   It's a string like "eyJhbGci..."
#   When a user logs in, we give them this token.
#   They send it with every API request.
#   We verify it to know WHO is making the request.
# ============================================================

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ── Password Hashing Setup ────────────────────────────────
# bcrypt is the industry standard — it's slow by design
# (makes brute-force attacks very hard)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Token Extraction Helper ──────────────────────────────
def extract_token(authorization: str = "") -> str:
    """
    Extracts the JWT token from the Authorization header.
    Expected format: "Bearer <token>"
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use: Bearer <token>"
        )
    return authorization.replace("Bearer ", "")


# ============================================================
# FUNCTION 1: Hash a plain text password
# ============================================================

def hash_password(plain_password: str) -> str:
    """
    Converts "mypassword123" → "$2b$12$abc...xyz" (hashed version)
    We store the hash in the DB, NEVER the original password.

    Example:
        hashed = hash_password("mypassword123")
        # Returns: "$2b$12$SomeRandomLookingString..."
    """
    return pwd_context.hash(plain_password)


# ============================================================
# FUNCTION 2: Verify a password against its hash
# ============================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if the password a user typed matches the stored hash.
    Returns True if correct, False if wrong.

    Example:
        is_correct = verify_password("mypassword123", stored_hash)
        # Returns: True or False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# FUNCTION 3: Create a JWT access token
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT token that the user will use for all future requests.

    HOW IT WORKS:
        1. We take some data (e.g., {"user_id": 5, "role": "manager"})
        2. Add an expiry time
        3. Encode it with our SECRET_KEY
        4. Return the token string

    Example:
        token = create_access_token({"sub": "user_id:5"})
        # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    # Copy the data so we don't mutate the original dict
    to_encode = data.copy()

    # Set expiry time (default: whatever is in settings)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # "exp" is a standard JWT field for expiry
    to_encode.update({"exp": expire})

    # Encode and sign the token with our secret key
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"   # HMAC-SHA256 — standard secure algorithm
    )

    return encoded_jwt


# ============================================================
# FUNCTION 4: Decode and verify a JWT token
# ============================================================

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes a JWT token and returns the data inside.
    Returns None if the token is invalid or expired.

    Example:
        payload = decode_access_token("eyJhbGci...")
        # Returns: {"sub": "user_id:5", "exp": 1234567890}
        # OR returns: None (if token is bad)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload

    except JWTError:
        # Token is invalid, expired, or tampered with
        return None

