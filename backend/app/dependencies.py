from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User
from app.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate a JWT from the Authorization: Bearer <token> header.
    Returns the authenticated User model instance.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
        )
    return user


def get_user_by_api_key(
    db: Session = Depends(get_db),
    x_api_key: str = None,
) -> User:
    """
    Look up and return a User by their API key.
    This is a helper — use get_summarize_user for the full pipeline.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    user = db.query(User).filter(User.api_key == x_api_key, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return user


def get_summarize_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    # We also accept api key via header — handled manually in the endpoint
) -> User:
    """
    Dependency that accepts either JWT (Bearer) or API key for summarize endpoint.
    JWT takes priority.
    """
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            user = db.query(User).filter(
                User.id == payload["sub"],
                User.is_active == True,
            ).first()
            if user:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def enforce_monthly_limit(user: User) -> User:
    """
    Check if the user has exceeded their monthly usage limit.
    Reset count if a new calendar month has started.
    """
    now = datetime.utcnow()
    # Reset counter if we're in a new month
    if user.last_reset_at.month != now.month or user.last_reset_at.year != now.year:
        user.usage_count = 0
        user.last_reset_at = now

    if user.usage_count >= user.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly limit reached ({user.monthly_limit} requests). "
                f"Upgrade your plan to continue."
            ),
        )
    return user
