from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=True, default="")
    avatar_color: Mapped[str] = mapped_column(String(20), nullable=True, default="#9c7cff")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # 'user', 'admin'
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # 'free', 'pro', 'premium'
    plan_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
