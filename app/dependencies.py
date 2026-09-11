from typing import Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def extract_token_from_request(request: Request, header_token: Optional[str] = None) -> Optional[str]:
    """Extract token either from Authorization header or from access_token cookie."""
    if header_token:
        return header_token
    # Check Authorization header directly
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    # Check Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:].strip()
        return cookie_token.strip()
    return None


def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get the authenticated user if present; otherwise return None (non-blocking for public pages)."""
    raw_token = extract_token_from_request(request, token)
    if not raw_token:
        return None
    payload = decode_token(raw_token)
    if not payload:
        return None
    email: Optional[str] = payload.get("sub")
    if not email:
        return None
    user = db.query(User).filter(User.email == email).first()
    return user


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate token and return current User. Raises 401 if unauthenticated."""
    user = get_current_user_optional(request, token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """Factory creating a FastAPI dependency to enforce role-based access control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Admin has access to everything
        if current_user.role == UserRole.ADMIN.value:
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}. Your role: {current_user.role}",
            )
        return current_user

    return role_checker
