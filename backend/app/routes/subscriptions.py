import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import CLICK_MERCHANT_ID, CLICK_SERVICE_ID, PAYME_MERCHANT_ID
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import (
    CreditTransaction,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
)
from app.models.user import User

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


class CheckoutRequest(BaseModel):
    plan_code: str  # 'pro' or 'premium'
    provider: str   # 'click', 'payme', 'uzum'


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    return [
        {
            "id": p.id,
            "plan_code": p.plan_code,
            "name": p.name,
            "description": p.description,
            "price_month_uzs": p.price_month_uzs,
            "price_year_uzs": p.price_year_uzs,
            "monthly_credits": p.monthly_credits,
            "max_chat_messages": p.max_chat_messages,
            "max_images": p.max_images,
            "max_edits": p.max_edits,
            "max_videos": p.max_videos,
            "max_audio": p.max_audio,
            "features": json.loads(p.features_json or "[]"),
        }
        for p in plans
    ]


@router.get("/current")
def get_current_subscription(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == user.plan).first()
    sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == user.id, UserSubscription.status == "active"
    ).order_by(UserSubscription.started_at.desc()).first()

    return {
        "plan_code": user.plan,
        "plan_name": plan.name if plan else user.plan.capitalize(),
        "credits": user.credits,
        "expires_at": user.plan_expires_at,
        "is_active": user.is_active,
        "subscription_details": {
            "billing_cycle": sub.billing_cycle if sub else "monthly",
            "started_at": sub.started_at if sub else user.created_at,
            "auto_renew": sub.auto_renew if sub else False,
        } if sub else None,
    }


@router.get("/history")
def get_billing_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    credit_txns = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user.id
    ).order_by(CreditTransaction.created_at.desc()).limit(50).all()

    payment_txns = db.query(PaymentTransaction).filter(
        PaymentTransaction.user_id == user.id
    ).order_by(PaymentTransaction.created_at.desc()).limit(20).all()

    return {
        "credit_ledger": [
            {
                "id": c.id,
                "amount": c.amount,
                "balance_after": c.balance_after,
                "service": c.service,
                "description": c.description,
                "created_at": c.created_at,
            }
            for c in credit_txns
        ],
        "payments": [
            {
                "id": p.id,
                "provider": p.provider,
                "transaction_id": p.transaction_id,
                "amount_uzs": p.amount_uzs,
                "plan_code": p.plan_code,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in payment_txns
        ],
    }


@router.post("/checkout")
def create_checkout_session(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == req.plan_code).first()
    if not plan or plan.plan_code == "free":
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    order_id = f"{user.id}_{req.plan_code}_{uuid.uuid4().hex[:8]}"
    amount_uzs = plan.price_month_uzs

    # Generate payment URLs according to provider protocols
    checkout_data = {
        "order_id": order_id,
        "plan_code": req.plan_code,
        "plan_name": plan.name,
        "amount_uzs": amount_uzs,
        "provider": req.provider,
    }

    if req.provider == "click":
        # Click checkout URL: https://my.click.uz/services/pay?service_id=...&merchant_id=...&amount=...&transaction_param=...
        url = f"https://my.click.uz/services/pay?service_id={CLICK_SERVICE_ID}&merchant_id={CLICK_MERCHANT_ID}&amount={amount_uzs}&transaction_param={order_id}"
        checkout_data["payment_url"] = url

    elif req.provider == "payme":
        # Payme base64 encoded checkout link: m=merchant_id;ac.user_id=...;ac.plan_code=...;a=amount_tiyin
        param_str = f"m={PAYME_MERCHANT_ID};ac.user_id={user.id};ac.plan_code={req.plan_code};a={amount_uzs * 100}"
        import base64
        encoded = base64.b64encode(param_str.encode()).decode()
        url = f"https://checkout.paycom.uz/{encoded}"
        checkout_data["payment_url"] = url

    elif req.provider == "uzum":
        # Uzum Bank checkout
        checkout_data["payment_url"] = f"https://www.uzumbank.uz/pay?orderNumber={order_id}&amount={amount_uzs * 100}"

    return checkout_data

