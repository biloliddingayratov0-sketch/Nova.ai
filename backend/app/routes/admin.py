import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.admin import AdminAuditLog, SystemSetting
from app.models.billing import PaymentTransaction, SubscriptionPlan
from app.models.chat import Conversation
from app.models.code import CodeProject
from app.models.image import ImageHistory
from app.models.media import AudioJob, VideoJob
from app.models.user import User

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required. Access denied.",
        )
    return current_user


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")


class StatusUpdateRequest(BaseModel):
    is_active: bool


class CreditAdjustmentRequest(BaseModel):
    credits: int
    reason: Optional[str] = "Admin manual adjustment"


class SettingUpdateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = ""


@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_images = db.query(ImageHistory).count()
    total_videos = db.query(VideoJob).count()
    total_audio = db.query(AudioJob).count()
    total_chat = db.query(Conversation).count()
    total_code = db.query(CodeProject).count()

    total_revenue_records = db.query(PaymentTransaction).filter(
        PaymentTransaction.status == "completed"
    ).all()
    total_revenue_uzs = sum(p.amount_uzs for p in total_revenue_records)

    pro_users = db.query(User).filter(User.plan == "pro").count()
    premium_users = db.query(User).filter(User.plan == "premium").count()

    return {
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "pro_subscribers": pro_users,
            "premium_subscribers": premium_users,
            "total_revenue_uzs": total_revenue_uzs,
        },
        "ai_workload": {
            "image_generations": total_images,
            "video_generations": total_videos,
            "audio_generations": total_audio,
            "chat_conversations": total_chat,
            "code_projects": total_code,
            "total_ai_operations": total_images + total_videos + total_audio + total_chat + total_code,
        },
    }


@router.get("/users")
def list_admin_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    plan: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = db.query(User)
    if search:
        q = q.filter((User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    if role:
        q = q.filter(User.role == role)
    if plan:
        q = q.filter(User.plan == plan)

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "credits": u.credits,
                "plan": u.plan,
                "plan_expires_at": u.plan_expires_at,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = req.role
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=f"Changed user {target.username} role to {req.role}",
        target_user_id=target.id,
        ip_address="127.0.0.1",
    ))
    db.commit()
    return {"success": True, "user_id": target.id, "role": target.role}


@router.patch("/users/{user_id}/status")
def toggle_user_active_status(
    user_id: int,
    req: StatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = req.is_active
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=f"Changed user {target.username} active status to {req.is_active}",
        target_user_id=target.id,
        ip_address="127.0.0.1",
    ))
    db.commit()
    return {"success": True, "user_id": target.id, "is_active": target.is_active}


@router.patch("/users/{user_id}/credits")
def adjust_user_credits(
    user_id: int,
    req: CreditAdjustmentRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.credits = max(0, req.credits)
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=f"Adjusted credits for {target.username} to {target.credits}. Reason: {req.reason}",
        target_user_id=target.id,
        ip_address="127.0.0.1",
    ))
    db.commit()
    return {"success": True, "user_id": target.id, "credits": target.credits}


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    logs = db.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "admin_id": l.admin_id,
            "action": l.action,
            "target_user_id": l.target_user_id,
            "ip_address": l.ip_address,
            "created_at": l.created_at,
        }
        for l in logs
    ]
