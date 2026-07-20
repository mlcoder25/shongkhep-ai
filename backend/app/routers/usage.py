from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, UsageLog
from app.schemas import UsageStatsResponse, UsageLogEntry
from app.dependencies import get_current_user

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/stats", response_model=UsageStatsResponse)
def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100, description="Number of recent logs to return"),
):
    """Return usage statistics and recent request logs for the authenticated user."""
    total_chars = (
        db.query(func.sum(UsageLog.characters_used))
        .filter(UsageLog.user_id == current_user.id)
        .scalar()
        or 0
    )

    recent_logs = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == current_user.id)
        .order_by(UsageLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return UsageStatsResponse(
        total_requests=current_user.usage_count,
        total_characters_processed=total_chars,
        plan=current_user.plan,
        monthly_limit=current_user.monthly_limit,
        usage_count=current_user.usage_count,
        remaining_requests=current_user.remaining_requests,
        usage_percentage=current_user.usage_percentage,
        recent_logs=[UsageLogEntry.model_validate(log) for log in recent_logs],
    )
