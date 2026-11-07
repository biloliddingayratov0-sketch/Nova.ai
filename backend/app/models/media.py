from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")  # 'text' or 'image'
    source_image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="nova-video-v1")
    style: Mapped[str] = mapped_column(String(50), nullable=False, default="Cinematic")
    ratio: Mapped[str] = mapped_column(String(10), nullable=False, default="16:9")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    video_url: Mapped[str] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AudioJob(Base):
    __tablename__ = "audio_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)  # 'music', 'voice_tts', 'voice_stt'
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Audio")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(50), nullable=True, default="Electronic")
    mood: Mapped[str] = mapped_column(String(50), nullable=True, default="Energetic")
    voice: Mapped[str] = mapped_column(String(50), nullable=True, default="alloy")
    language: Mapped[str] = mapped_column(String(20), nullable=True, default="en")
    speed: Mapped[float] = mapped_column(Float, nullable=True, default=1.0)
    duration: Mapped[int] = mapped_column(Integer, nullable=True, default=30)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    audio_url: Mapped[str] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AudioStudioFile(Base):
    __tablename__ = "audio_studio_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="mp3")
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=True, default=44100)
    channels: Mapped[int] = mapped_column(Integer, nullable=True, default=2)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

