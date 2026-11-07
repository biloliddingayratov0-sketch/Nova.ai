from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import GENERATED_DIR, MAX_HISTORY_PER_PAGE
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.image import ImageHistory
from app.models.user import User

router = APIRouter(prefix="/api/history", tags=["Image History"])


def _format(item: ImageHistory):
    return {
        "id": item.id,
        "prompt": item.prompt,
        "filename": item.filename,
        "operation": item.operation,
        "style": item.style,
        "ratio": item.ratio,
        "is_favorite": item.is_favorite,
        "image": f"/generated/{item.filename}",
        "created_at": item.created_at,
    }


@router.get("/")
def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=MAX_HISTORY_PER_PAGE),
    operation: str = Query(None),
    favorites_only: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(ImageHistory).filter(ImageHistory.user_id == user.id)

    if operation:
        query = query.filter(ImageHistory.operation == operation)
    if favorites_only:
        query = query.filter(ImageHistory.is_favorite == True)

    total = query.count()
    records = (
        query.order_by(ImageHistory.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "items": [_format(item) for item in records],
    }


@router.patch("/{image_id}/favorite")
def toggle_favorite(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = (
        db.query(ImageHistory)
        .filter(
            ImageHistory.id == image_id,
            ImageHistory.user_id == user.id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")

    item.is_favorite = not item.is_favorite
    db.commit()
    return {"success": True, "is_favorite": item.is_favorite}


@router.delete("/{image_id}")
def delete_history(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = (
        db.query(ImageHistory)
        .filter(
            ImageHistory.id == image_id,
            ImageHistory.user_id == user.id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")

    filename = item.filename
    db.delete(item)
    db.commit()

    still_used = db.query(ImageHistory).filter(
        ImageHistory.filename == filename
    ).first()

    if still_used is None:
        file_path = (GENERATED_DIR / filename).resolve()
        if file_path.is_relative_to(GENERATED_DIR.resolve()) and file_path.exists():
            file_path.unlink()

    return {"success": True, "message": "Deleted"}


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(ImageHistory).filter(ImageHistory.user_id == user.id).count()
    generated = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id,
        ImageHistory.operation == "generate",
    ).count()
    edited = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id,
        ImageHistory.operation == "edit",
    ).count()
    favorites = db.query(ImageHistory).filter(
        ImageHistory.user_id == user.id,
        ImageHistory.is_favorite == True,
    ).count()

    return {
        "total": total,
        "generated": generated,
        "edited": edited,
        "favorites": favorites,
    }
