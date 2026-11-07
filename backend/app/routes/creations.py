from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.chat import Conversation
from app.models.code import CodeProject
from app.models.image import ImageHistory
from app.models.media import AudioJob, VideoJob
from app.models.user import User

router = APIRouter(prefix="/api/creations", tags=["My Creations Library"])


@router.get("/")
def get_all_creations(
    category: str = Query("all", pattern="^(all|images|edited|videos|music|code|conversations)$"),
    search: Optional[str] = None,
    favorites_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = []

    # 1. Images & Edited Images
    if category in ("all", "images", "edited"):
        q = db.query(ImageHistory).filter(ImageHistory.user_id == user.id)
        if category == "images":
            q = q.filter(ImageHistory.operation == "generate")
        elif category == "edited":
            q = q.filter(ImageHistory.operation == "edit")
        if favorites_only:
            q = q.filter(ImageHistory.is_favorite == True)
        if search:
            q = q.filter(ImageHistory.prompt.ilike(f"%{search}%"))
        
        for img in q.all():
            items.append({
                "id": img.id,
                "type": "image",
                "subtype": img.operation,
                "title": img.prompt[:60],
                "description": img.prompt,
                "media_url": f"/generated/{img.filename}",
                "filename": img.filename,
                "style": img.style,
                "ratio": img.ratio,
                "is_favorite": img.is_favorite,
                "created_at": img.created_at,
            })

    # 2. Videos
    if category in ("all", "videos"):
        q = db.query(VideoJob).filter(VideoJob.user_id == user.id)
        if favorites_only:
            q = q.filter(VideoJob.is_favorite == True)
        if search:
            q = q.filter(VideoJob.prompt.ilike(f"%{search}%"))
        for v in q.all():
            items.append({
                "id": v.id,
                "type": "video",
                "subtype": v.source_type,
                "title": v.prompt[:60],
                "description": v.prompt,
                "media_url": v.video_url,
                "thumbnail_url": v.thumbnail_url,
                "style": v.style,
                "ratio": v.ratio,
                "duration": v.duration,
                "is_favorite": v.is_favorite,
                "created_at": v.created_at,
            })

    # 3. Music & Audio
    if category in ("all", "music"):
        q = db.query(AudioJob).filter(AudioJob.user_id == user.id, AudioJob.job_type == "music")
        if favorites_only:
            q = q.filter(AudioJob.is_favorite == True)
        if search:
            q = q.filter(AudioJob.title.ilike(f"%{search}%"))
        for m in q.all():
            items.append({
                "id": m.id,
                "type": "music",
                "subtype": m.genre or "General",
                "title": m.title,
                "description": m.prompt,
                "media_url": m.audio_url,
                "genre": m.genre,
                "mood": m.mood,
                "duration": m.duration,
                "is_favorite": m.is_favorite,
                "created_at": m.created_at,
            })

    # 4. Code Projects
    if category in ("all", "code"):
        q = db.query(CodeProject).filter(CodeProject.user_id == user.id)
        if search:
            q = q.filter(CodeProject.title.ilike(f"%{search}%"))
        for cp in q.all():
            items.append({
                "id": cp.id,
                "type": "code",
                "subtype": cp.language,
                "title": cp.title,
                "description": cp.description,
                "language": cp.language,
                "code_snippet": cp.code[:200],
                "is_favorite": False,
                "created_at": cp.created_at,
            })

    # 5. Conversations
    if category in ("all", "conversations"):
        q = db.query(Conversation).filter(Conversation.user_id == user.id)
        if search:
            q = q.filter(Conversation.title.ilike(f"%{search}%"))
        for c in q.all():
            items.append({
                "id": c.id,
                "type": "conversation",
                "subtype": c.model,
                "title": c.title,
                "description": f"{len(c.messages)} messages",
                "is_favorite": False,
                "created_at": c.created_at,
            })

    # Sort
    items.sort(key=lambda x: x["created_at"], reverse=(sort == "desc"))

    # Paginate
    total = len(items)
    start_idx = (page - 1) * limit
    paginated_items = items[start_idx : start_idx + limit]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "category": category,
        "items": paginated_items,
    }


@router.delete("/{item_type}/{item_id}")
def delete_creation_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if item_type == "image":
        item = db.query(ImageHistory).filter(ImageHistory.id == item_id, ImageHistory.user_id == user.id).first()
    elif item_type == "video":
        item = db.query(VideoJob).filter(VideoJob.id == item_id, VideoJob.user_id == user.id).first()
    elif item_type == "music":
        item = db.query(AudioJob).filter(AudioJob.id == item_id, AudioJob.user_id == user.id).first()
    elif item_type == "code":
        item = db.query(CodeProject).filter(CodeProject.id == item_id, CodeProject.user_id == user.id).first()
    elif item_type == "conversation":
        item = db.query(Conversation).filter(Conversation.id == item_id, Conversation.user_id == user.id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"success": True, "message": f"{item_type.capitalize()} deleted successfully"}
