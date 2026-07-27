# ============================================================
# app/api/routes/auth.py
# ============================================================
# PURPOSE:
#   Authentication endpoints — register, login, get current user.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import (
    UserCreate, UserResponse, LoginRequest, Token, MessageResponse
)
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter()


# ============================================================
# Helper Dependency: Extract Bearer Token from Authorization header
# ============================================================

def extract_token(authorization: str = Header(default="")) -> str:
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
# POST /auth/register — Create a new user
# ============================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new staff account.
    Password is hashed before storing — NEVER stored in plain text.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    # Validate role
    valid_roles = [r.value for r in UserRole]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    # Create user
    user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        store_id=user_data.store_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# POST /auth/login — Get JWT token
# ============================================================

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT token.
    Send this token in the Authorization header for future requests.
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your manager."
        )

    # Create token
    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
    })

    return Token(access_token=token)


# ============================================================
# GET /auth/me — Get current user info
# ============================================================

@router.get("/me", response_model=UserResponse)
def get_current_user(token: str = Depends(extract_token), db: Session = Depends(get_db)):
    """
    Returns the profile of the currently authenticated user.
    Send your JWT token in the Authorization header: Bearer <token>
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user




