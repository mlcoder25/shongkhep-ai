from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, PLAN_LIMITS
from app.schemas import UpgradePlanRequest, UpgradePlanResponse  # Added missing import
from app.dependencies import get_current_user

router = APIRouter(prefix="/plans", tags=["Plans & Billing"])

PLAN_PRICES = {
    "free":     {"bdt": 0,    "usd": 0},
    "student":  {"bdt": 49,   "usd": 0.5},
    "basic":    {"bdt": 149,  "usd": 1.5},
    "pro":      {"bdt": 399,  "usd": 4},
    "business": {"bdt": 999,  "usd": 10},
}

@router.get("/info")
def get_plan_info():
    """Return pricing and limits for all available plans."""
    return {
        "plans": [
            {
                "name": "free",
                "monthly_requests": 50,
                "price_bdt": 0,
                "price_usd": 0,
                "features": ["50 summaries/month", "API access", "Bangla + English"],
            },
            {
                "name": "student",
                "monthly_requests": 300,
                "price_bdt": 49,
                "price_usd": 0.5,
                "features": ["300 summaries/month", "API access", "Bangla + English", "PDF support"],
            },
            {
                "name": "basic",
                "monthly_requests": 1000,
                "price_bdt": 149,
                "price_usd": 1.5,
                "features": ["1,000 summaries/month", "Priority access", "Full analytics", "Webhooks"],
                "highlight": True,
            },
            {
                "name": "pro",
                "monthly_requests": 5000,
                "price_bdt": 399,
                "price_usd": 4,
                "features": ["5,000 summaries/month", "Dedicated support", "All features", "Higher rate limits"],
            },
            {
                "name": "business",
                "monthly_requests": 20000,
                "price_bdt": 999,
                "price_usd": 10,
                "features": ["20,000 summaries/month", "Priority support", "Custom webhook", "Invoice billing"],
            },
        ]
    }

@router.post("/upgrade", response_model=UpgradePlanResponse)
def upgrade_plan(
    payload: UpgradePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upgrade (or downgrade) the authenticated user's plan.
    
    NOTE: In production this endpoint would integrate with a payment gateway
    (e.g. SSLCommerz or bKash for Bangladesh). Currently mocked.
    """
    if current_user.plan == payload.plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already on the {payload.plan.value} plan",
        )

    new_limit = PLAN_LIMITS[payload.plan]
    current_user.plan = payload.plan
    current_user.monthly_limit = new_limit
    db.commit()
    db.refresh(current_user)

    return UpgradePlanResponse(
        message=f"Plan upgraded to {payload.plan.value} successfully! Payment integration coming soon.",
        new_plan=payload.plan,
        new_monthly_limit=new_limit,
    )
