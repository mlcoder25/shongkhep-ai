"""
Admin router — protected by both JWT + admin flag.
Exposes platform-wide stats and user management operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, UsageLog, PlanType, PLAN_LIMITS
from app.schemas import AdminUserListEntry, AdminStatsResponse, UpgradePlanRequest
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


@router.get("/stats", response_model=AdminStatsResponse)
def platform_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Platform-wide statistics for admin dashboard."""
    total_users  = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()

    users_by_plan = {}
    for plan in PlanType:
        count = db.query(func.count(User.id)).filter(User.plan == plan).scalar()
        users_by_plan[plan.value] = count

    total_requests = db.query(func.count(UsageLog.id)).scalar()

    from app import summarizer, cache
    model_info   = summarizer.get_model_info()
    redis_health = cache.health_check()

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        users_by_plan=users_by_plan,
        total_requests_all_time=total_requests,
        model_info=model_info,
        redis_health=redis_health,
    )


@router.get("/users", response_model=List[AdminUserListEntry])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    plan: Optional[str] = None,
):
    query = db.query(User)
    if plan:
        query = query.filter(User.plan == plan)
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/users/{user_id}/plan")
def admin_set_plan(
    user_id: str,
    payload: UpgradePlanRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.plan = payload.plan
    user.monthly_limit = PLAN_LIMITS[payload.plan]
    db.commit()
    return {"message": f"Plan updated to {payload.plan.value}", "monthly_limit": user.monthly_limit}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot deactivate another admin.")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} deactivated."}


@router.post("/users/{user_id}/reset-usage")
def reset_user_usage(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    from datetime import datetime
    user.usage_count = 0
    user.last_reset_at = datetime.utcnow()
    db.commit()
    return {"message": f"Usage reset for {user.email}."}
