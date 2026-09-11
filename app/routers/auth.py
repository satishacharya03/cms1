from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    First registered user automatically gains ADMIN role if no admin exists;
    subsequent registrations default to the requested role or PUBLIC.
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # If this is the very first user in the system, promote to admin
    is_first_user = db.query(User).count() == 0
    assigned_role = UserRole.ADMIN.value if is_first_user else (user_in.role.value if user_in.role else UserRole.PUBLIC.value)

    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=assigned_role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password, returning a JWT access token."""
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details for the currently authenticated user."""
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Admin-only endpoint to view all system users."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Admin-only endpoint to elevate or modify user roles."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.role = new_role.value
    db.commit()
    db.refresh(user)
    return user
