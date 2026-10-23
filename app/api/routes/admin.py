# ============================================================
# app/api/routes/admin.py
# ============================================================
# PURPOSE:
#   Admin endpoints — manage all users, view user data, deactivate accounts.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import UserResponse, MessageResponse
from app.core.security import extract_token, decode_access_token

router = APIRouter(tags=["admin"])


# ── Dependency: Get current admin user ──────────────────────

def get_current_admin(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# ── GET /admin/users — List all users ───────────────────────

@router.get("/users", response_model=List[UserResponse])
def list_all_users(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


# ── GET /admin/users/{id} — Get single user ─────────────────

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ── PATCH /admin/users/{id} — Update user (role, active) ────

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, updates: dict, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if "role" in updates:
        valid_roles = [r.value for r in __import__('app.models.models', fromlist=['UserRole']).UserRole]
        if updates["role"] not in valid_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        user.role = updates["role"]

    if "is_active" in updates:
        user.is_active = bool(updates["is_active"])

    if "full_name" in updates:
        user.full_name = updates["full_name"]

    db.commit()
    db.refresh(user)
    return user


# ── DELETE /admin/users/{id} — Deactivate user ──────────────

@router.delete("/users/{user_id}", response_model=MessageResponse)
def deactivate_user(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    return MessageResponse(message=f"User {user.email} deactivated")


# ── GET /admin/stats — Admin dashboard stats ────────────────

@router.get("/stats")
def admin_stats(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    customer_users = db.query(User).filter(User.role == "customer").count()
    shopkeeper_users = db.query(User).filter(User.role == "shopkeeper").count()
    staff_users = db.query(User).filter(User.role.in_(["floor_staff", "store_manager"])).count()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "customer_users": customer_users,
        "shopkeeper_users": shopkeeper_users,
        "staff_users": staff_users,
    }