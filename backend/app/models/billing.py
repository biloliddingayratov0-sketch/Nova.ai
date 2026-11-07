from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # 'free', 'pro', 'premium'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price_month_uzs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_year_uzs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_chat_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_images: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_edits: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    max_videos: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_audio: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    features_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")  # 'monthly', 'yearly'
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")  # 'active', 'cancelled', 'expired'
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # positive for add, negative for spend
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    service: Mapped[str] = mapped_column(String(50), nullable=False)  # 'image_generate', 'image_edit', 'chat', 'code', 'video', 'music', 'bonus', 'purchase'
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'click', 'payme', 'uzum'
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    provider_transaction_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    amount_uzs: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    credits_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # 'pending', 'completed', 'failed', 'cancelled'
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

