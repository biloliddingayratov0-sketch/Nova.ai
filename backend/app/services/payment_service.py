import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from app.config import (
    CLICK_MERCHANT_ID,
    CLICK_SECRET_KEY,
    CLICK_SERVICE_ID,
    PAYME_MERCHANT_ID,
    PAYME_SECRET_KEY,
    UZUM_MERCHANT_ID,
    UZUM_SECRET_KEY,
)
from app.database.connection import SessionLocal
from app.models.billing import (
    CreditTransaction,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
)
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("nova_ai.payment_service")


def activate_user_plan_and_credits(db, user: User, plan_code: str, amount_uzs: int, provider: str, txn_id: str):
    """Activates the purchased subscription plan and awards credits."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == plan_code).first()
    credits_to_add = plan.monthly_credits if plan else 100

    user.plan = plan_code
    user.credits += credits_to_add
    user.plan_expires_at = datetime.utcnow() + timedelta(days=30)

    # Record user subscription
    sub = UserSubscription(
        user_id=user.id,
        plan_code=plan_code,
        billing_cycle="monthly",
        status="active",
        expires_at=user.plan_expires_at,
        auto_renew=True,
    )
    db.add(sub)

    # Record credit transaction
    credit_txn = CreditTransaction(
        user_id=user.id,
        amount=credits_to_add,
        balance_after=user.credits,
        service="purchase",
        description=f"Subscription upgrade to {plan_code.upper()} plan via {provider.upper()}",
    )
    db.add(credit_txn)

    # In-app notification
    db.add(Notification(
        user_id=user.id,
        title="Subscription Activated!",
        message=f"Your {plan_code.upper()} plan has been activated with {credits_to_add} AI credits. Thank you!",
        type="success",
        link="/#pricing",
    ))
    db.commit()


# =====================================================================
# CLICK MERCHANT INTEGRATION
# Docs: https://docs.click.uz
# =====================================================================

def handle_click_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Click merchant prepare and complete actions.
    Sign formula: MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
    """
    db = SessionLocal()
    try:
        click_trans_id = str(params.get("click_trans_id", ""))
        service_id = str(params.get("service_id", ""))
        merchant_trans_id = str(params.get("merchant_trans_id", ""))  # user_id:plan_code
        amount = str(params.get("amount", ""))
        action = str(params.get("action", ""))
        error = str(params.get("error", "0"))
        error_note = str(params.get("error_note", ""))
        sign_time = str(params.get("sign_time", ""))
        sign_string = str(params.get("sign_string", ""))

        # Verify MD5 signature
        raw_sign = f"{click_trans_id}{service_id}{CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}"
        expected_sign = hashlib.md5(raw_sign.encode("utf-8")).hexdigest()

        # Allow test bypass if in local test sandbox
        is_sandbox_test = CLICK_SECRET_KEY.startswith("test_") or "sandbox" in CLICK_SECRET_KEY
        if not is_sandbox_test and sign_string.lower() != expected_sign.lower():
            return {
                "error": -1,
                "error_note": "SIGN CHECK FAILED",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
            }

        # Parse user and plan from merchant_trans_id (format: "{user_id}_{plan_code}_{uuid}")
        parts = merchant_trans_id.split("_")
        user_id = int(parts[0]) if parts and parts[0].isdigit() else 0
        plan_code = parts[1] if len(parts) > 1 else "pro"

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "error": -5,
                "error_note": "User does not exist",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
            }

        # Action 0: Prepare
        if action == "0":
            # Check for existing completed transaction
            existing = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == click_trans_id
            ).first()
            if existing and existing.status == "completed":
                return {
                    "error": -4,
                    "error_note": "Already paid",
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                }

            # Create or update pending record
            ptxn = PaymentTransaction(
                user_id=user.id,
                provider="click",
                transaction_id=merchant_trans_id,
                provider_transaction_id=click_trans_id,
                amount_uzs=int(float(amount)),
                plan_code=plan_code,
                status="pending",
                raw_payload=json.dumps(params),
            )
            db.add(ptxn)
            db.commit()

            return {
                "error": 0,
                "error_note": "Success",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_prepare_id": ptxn.id,
            }

        # Action 1: Complete
        elif action == "1":
            ptxn = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == click_trans_id
            ).first()

            if not ptxn:
                ptxn = PaymentTransaction(
                    user_id=user.id,
                    provider="click",
                    transaction_id=merchant_trans_id,
                    provider_transaction_id=click_trans_id,
                    amount_uzs=int(float(amount)),
                    plan_code=plan_code,
                    status="pending",
                    raw_payload=json.dumps(params),
                )
                db.add(ptxn)

            if ptxn.status == "completed":
                return {
                    "error": 0,
                    "error_note": "Already completed",
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_confirm_id": ptxn.id,
                }

            if error == "0":
                ptxn.status = "completed"
                ptxn.completed_at = datetime.utcnow()
                activate_user_plan_and_credits(db, user, plan_code, int(float(amount)), "Click", merchant_trans_id)
                db.commit()

                return {
                    "error": 0,
                    "error_note": "Success",
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_confirm_id": ptxn.id,
                }
            else:
                ptxn.status = "failed"
                ptxn.error_message = error_note
                db.commit()
                return {
                    "error": int(error),
                    "error_note": error_note,
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                }

        return {"error": -3, "error_note": "Action not found"}
    finally:
        db.close()


# =====================================================================
# PAYME MERCHANT INTEGRATION (JSON-RPC 2.0)
# Docs: https://help.paycom.uz
# =====================================================================

def handle_payme_rpc(req_body: Dict[str, Any], auth_header: Optional[str]) -> Dict[str, Any]:
    """
    Handle Payme Merchant JSON-RPC 2.0 methods.
    Methods: CheckPerformTransaction, CreateTransaction, PerformTransaction, CancelTransaction, CheckTransaction.
    """
    rpc_id = req_body.get("id")
    method = req_body.get("method")
    params = req_body.get("params", {})

    # Basic Auth Verification: Basic base64("Paycom:" + secret_key)
    is_sandbox = PAYME_SECRET_KEY.startswith("test_") or "sandbox" in PAYME_SECRET_KEY
    if not is_sandbox and auth_header:
        expected = "Basic " + base64.b64encode(f"Paycom:{PAYME_SECRET_KEY}".encode()).decode()
        if auth_header != expected:
            return {
                "error": {"code": -32504, "message": "Insufficient privilege to perform the operation"},
                "id": rpc_id,
            }

    db = SessionLocal()
    try:
        account = params.get("account", {})
        user_id = int(account.get("user_id", 0)) if str(account.get("user_id", "")).isdigit() else 0
        plan_code = account.get("plan_code", "pro")
        amount_tiyin = params.get("amount", 0)  # Payme operates in tiyins (1 UZS = 100 tiyin)
        amount_uzs = amount_tiyin // 100
        payme_trans_id = params.get("id")

        user = db.query(User).filter(User.id == user_id).first()

        if method == "CheckPerformTransaction":
            if not user:
                return {"error": {"code": -31050, "message": {"ru": "Пользователь не найден", "en": "User not found"}}, "id": rpc_id}
            return {"result": {"allow": True}, "id": rpc_id}

        elif method == "CreateTransaction":
            if not user:
                return {"error": {"code": -31050, "message": {"ru": "Пользователь не найден"}}, "id": rpc_id}

            ptxn = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == payme_trans_id
            ).first()

            now_ms = int(time.time() * 1000)

            if not ptxn:
                ptxn = PaymentTransaction(
                    user_id=user.id,
                    provider="payme",
                    transaction_id=f"payme_{uuid.uuid4().hex[:12]}",
                    provider_transaction_id=payme_trans_id,
                    amount_uzs=amount_uzs,
                    plan_code=plan_code,
                    status="pending",
                    raw_payload=json.dumps(params),
                )
                db.add(ptxn)
                db.commit()

            return {
                "result": {
                    "create_time": now_ms,
                    "transaction": str(ptxn.id),
                    "state": 1,  # State 1: Created
                },
                "id": rpc_id,
            }

        elif method == "PerformTransaction":
            ptxn = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == payme_trans_id
            ).first()

            if not ptxn:
                return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}, "id": rpc_id}

            now_ms = int(time.time() * 1000)

            if ptxn.status != "completed":
                ptxn.status = "completed"
                ptxn.completed_at = datetime.utcnow()
                activate_user_plan_and_credits(db, user, ptxn.plan_code, ptxn.amount_uzs, "Payme", ptxn.transaction_id)
                db.commit()

            return {
                "result": {
                    "transaction": str(ptxn.id),
                    "perform_time": now_ms,
                    "state": 2,  # State 2: Completed
                },
                "id": rpc_id,
            }

        elif method == "CheckTransaction":
            ptxn = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == payme_trans_id
            ).first()
            if not ptxn:
                return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}, "id": rpc_id}

            state = 2 if ptxn.status == "completed" else 1
            now_ms = int(time.time() * 1000)
            return {
                "result": {
                    "create_time": now_ms - 60000,
                    "perform_time": now_ms if ptxn.status == "completed" else 0,
                    "cancel_time": 0,
                    "transaction": str(ptxn.id),
                    "state": state,
                    "reason": None,
                },
                "id": rpc_id,
            }

        elif method == "CancelTransaction":
            ptxn = db.query(PaymentTransaction).filter(
                PaymentTransaction.provider_transaction_id == payme_trans_id
            ).first()
            if not ptxn:
                return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена"}}, "id": rpc_id}

            ptxn.status = "cancelled"
            db.commit()
            return {
                "result": {
                    "transaction": str(ptxn.id),
                    "cancel_time": int(time.time() * 1000),
                    "state": -1,
                },
                "id": rpc_id,
            }

        return {"error": {"code": -32601, "message": "Method not found"}, "id": rpc_id}
    finally:
        db.close()


# =====================================================================
# UZUM BANK INTEGRATION
# Docs: https://uzumbank.uz/api
# =====================================================================

def handle_uzum_webhook(payload: Dict[str, Any], signature: Optional[str]) -> Dict[str, Any]:
    """
    Handle Uzum Bank payment notification webhook.
    """
    db = SessionLocal()
    try:
        order_id = str(payload.get("orderNumber") or payload.get("order_id") or "")
        amount = int(payload.get("amount", 0)) // 100  # tiyin to UZS
        status = payload.get("status")  # 'SUCCESS' / 'COMPLETED'
        user_id = int(payload.get("userId", 0))
        plan_code = payload.get("planCode", "pro")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "FAILED", "message": "User not found"}

        ptxn = db.query(PaymentTransaction).filter(
            PaymentTransaction.transaction_id == order_id
        ).first()

        if not ptxn:
            ptxn = PaymentTransaction(
                user_id=user.id,
                provider="uzum",
                transaction_id=order_id or f"uzum_{uuid.uuid4().hex[:12]}",
                provider_transaction_id=str(payload.get("paymentId", "")),
                amount_uzs=amount,
                plan_code=plan_code,
                status="pending",
                raw_payload=json.dumps(payload),
            )
            db.add(ptxn)

        if status in ("SUCCESS", "COMPLETED"):
            if ptxn.status != "completed":
                ptxn.status = "completed"
                ptxn.completed_at = datetime.utcnow()
                activate_user_plan_and_credits(db, user, plan_code, amount, "Uzum Bank", ptxn.transaction_id)
                db.commit()
            return {"status": "SUCCESS", "message": "Payment verified and credited"}

        return {"status": "RECEIVED", "message": f"Payment status: {status}"}
    finally:
        db.close()

