from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class CodeProject(Base):
    __tablename__ = "code_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Project")
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="python")
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_structure: Mapped[str] = mapped_column(Text, nullable=True, default="")
    files_json: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

