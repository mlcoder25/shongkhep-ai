import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Webhook
from app.schemas import WebhookCreateRequest, WebhookResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

ALLOWED_EVENTS = {"summarize.complete", "limit.reached", "limit.warning"}


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Webhook).filter(Webhook.user_id == current_user.id).all()


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Webhook).filter(Webhook.user_id == current_user.id).count()
    if existing >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 webhooks per account.")

    events = payload.events or ["summarize.complete"]
    invalid = [e for e in events if e not in ALLOWED_EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}. Allowed: {ALLOWED_EVENTS}")

    webhook = Webhook(
        user_id=current_user.id,
        url=payload.url,
        secret=payload.secret or secrets.token_hex(32),
        events=",".join(events),
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id,
    ).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    db.delete(hook)
    db.commit()


@router.post("/{webhook_id}/test", status_code=status.HTTP_202_ACCEPTED)
def test_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a test ping to the webhook URL."""
    hook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == current_user.id,
    ).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    try:
        from app.tasks import deliver_webhook
        deliver_webhook.delay(
            hook.url,
            {"event": "test", "message": "Shongkhep AI webhook test ping", "user_id": str(current_user.id)},
            hook.secret,
        )
        return {"message": "Test ping queued."}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}")
