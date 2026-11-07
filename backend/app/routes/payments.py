from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.payment_service import (
    activate_user_plan_and_credits,
    handle_click_request,
    handle_payme_rpc,
    handle_uzum_webhook,
)

router = APIRouter(prefix="/api/payments", tags=["Payment Providers"])


# --- CLICK WEBHOOKS ---
@router.post("/click/prepare")
async def click_prepare(request: Request):
    form_data = await request.form()
    params = dict(form_data)
    if not params:
        try:
            params = await request.json()
        except Exception:
            params = {}
    return handle_click_request(params)


@router.post("/click/complete")
async def click_complete(request: Request):
    form_data = await request.form()
    params = dict(form_data)
    if not params:
        try:
            params = await request.json()
        except Exception:
            params = {}
    return handle_click_request(params)


# --- PAYME JSON-RPC ---
@router.post("/payme")
async def payme_rpc(request: Request, authorization: Optional[str] = Header(None)):
    req_body = await request.json()
    return handle_payme_rpc(req_body, authorization)


# --- UZUM BANK WEBHOOK ---
@router.post("/uzum")
async def uzum_webhook(request: Request, x_signature: Optional[str] = Header(None)):
    payload = await request.json()
    return handle_uzum_webhook(payload, x_signature)


# --- SANDBOX SIMULATOR (Safe testing for developers & evaluation) ---
class SandboxPaymentRequest(BaseModel):
    provider: str  # 'click', 'payme', 'uzum'
    plan_code: str # 'pro', 'premium'


@router.post("/sandbox-simulate")
def sandbox_simulate_payment(
    req: SandboxPaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Allows safe sandbox payment testing for verification without real money.
    Strictly verifies plan and updates database state.
    """
    if req.plan_code not in ("pro", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan code")

    amounts = {"pro": 99000, "premium": 249000}
    amount_uzs = amounts.get(req.plan_code, 99000)
    fake_txn_id = f"sandbox_{req.provider}_{user.id}_{req.plan_code}"

    activate_user_plan_and_credits(
        db,
        user,
        req.plan_code,
        amount_uzs,
        f"{req.provider.capitalize()} Sandbox",
        fake_txn_id,
    )

    return {
        "success": True,
        "message": f"Sandbox payment confirmed! {req.plan_code.upper()} plan activated.",
        "plan": user.plan,
        "credits": user.credits,
        "expires_at": user.plan_expires_at,
    }

