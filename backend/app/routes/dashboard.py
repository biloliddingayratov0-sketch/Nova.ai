from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.chat import Conversation
from app.models.code import CodeProject
from app.models.image import ImageHistory
from app.models.media import AudioJob, VideoJob
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["User Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_images_gen = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id, ImageHistory.operation == "generate"
    ).count()

    total_images_edit = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id, ImageHistory.operation == "edit"
    ).count()

    total_videos = db.query(VideoJob).filter(VideoJob.user_id == user.id).count()
    total_convs = db.query(Conversation).filter(Conversation.user_id == user.id).count()
    total_audio = db.query(AudioJob).filter(AudioJob.user_id == user.id).count()
    total_code = db.query(CodeProject).filter(CodeProject.user_id == user.id).count()

    # Recent creations across image, video, music
    recent_images = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id
    ).order_by(ImageHistory.created_at.desc()).limit(6).all()

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "bio": user.bio,
            "avatar_color": user.avatar_color,
            "role": user.role,
            "credits": user.credits,
            "plan": user.plan,
            "plan_expires_at": user.plan_expires_at,
            "created_at": user.created_at,
        },
        "statistics": {
            "total_generated_images": total_images_gen,
            "total_edited_images": total_images_edit,
            "total_images": total_images_gen + total_images_edit,
            "total_videos": total_videos,
            "total_conversations": total_convs,
            "total_audio_generations": total_audio,
            "total_code_projects": total_code,
            "credits_remaining": user.credits,
            "current_plan": user.plan,
        },
        "recent_activity": [
            {
                "id": img.id,
                "type": "image",
                "operation": img.operation,
                "prompt": img.prompt,
                "url": f"/generated/{img.filename}",
                "style": img.style,
                "created_at": img.created_at,
            }
            for img in recent_images
        ],
    }

