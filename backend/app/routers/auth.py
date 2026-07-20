from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.models import User, PLAN_LIMITS, PlanType, generate_api_key
from app.schemas import (
    UserSignupRequest, UserLoginRequest,
    TokenResponse, UserProfileResponse,
    RegenerateKeyResponse,
)
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignupRequest, db: Session = Depends(get_db)):
    """Register a new user and return their profile (including API key)."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        api_key=generate_api_key(),
        plan=PlanType.FREE,
        monthly_limit=PLAN_LIMITS[PlanType.FREE],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    expire_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=expire_delta,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's full profile."""
    return current_user


@router.post("/regenerate-key", response_model=RegenerateKeyResponse)
def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Issue a new API key for the authenticated user (invalidates the old one)."""
    current_user.api_key = generate_api_key()
    db.commit()
    db.refresh(current_user)
    return RegenerateKeyResponse(
        api_key=current_user.api_key,
        message="API key regenerated successfully. Update your integrations.",
    )
