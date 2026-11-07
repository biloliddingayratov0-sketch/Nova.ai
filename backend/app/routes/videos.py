import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import CreditTransaction
from app.models.media import VideoJob
from app.models.user import User
from app.services.ai_service import save_image_bytes
from app.services.video_service import process_video_generation_job

router = APIRouter(prefix="/api/videos", tags=["AI Video Generator"])


@router.post("/generate")
async def create_video_job(
    prompt: str = Form(...),
    source_type: str = Form("text"),  # 'text' or 'image'
    style: str = Form("Cinematic"),
    ratio: str = Form("16:9"),
    duration: int = Form(5),
    image: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.credits < 5:
        raise HTTPException(
            status_code=402,
            detail=f"Video generation requires 5 AI credits (you have {user.credits}). Upgrade to Pro/Premium for more.",
        )

    source_image_url = None
    if source_type == "image" and image:
        content = await image.read()
        if content:
            img_filename = save_image_bytes(content, "png")
            source_image_url = f"/generated/{img_filename}"

    # Deduct 5 credits
    user.credits -= 5
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-5,
        balance_after=user.credits,
        service="video",
        description=f"Generated AI video: '{prompt[:30]}...'",
    ))

    job = VideoJob(
        user_id=user.id,
        prompt=prompt,
        source_type=source_type,
        source_image_url=source_image_url,
        model="nova-video-v1",
        style=style,
        ratio=ratio,
        duration=duration,
        status="pending",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch background worker
    asyncio.create_task(process_video_generation_job(job.id))

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "message": "Video generation job started in background.",
        "remaining_credits": user.credits,
    }


@router.get("/jobs/{job_id}")
def get_video_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(VideoJob).filter(
        VideoJob.id == job_id, VideoJob.user_id == user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    return {
        "id": job.id,
        "prompt": job.prompt,
        "status": job.status,
        "progress": job.progress,
        "video_url": job.video_url,
        "thumbnail_url": job.thumbnail_url,
        "error_message": job.error_message,
        "style": job.style,
        "ratio": job.ratio,
        "created_at": job.created_at,
    }


@router.get("/history")
def list_user_videos(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    videos = db.query(VideoJob).filter(
        VideoJob.user_id == user.id
    ).order_by(VideoJob.created_at.desc()).all()
    return [
        {
            "id": v.id,
            "prompt": v.prompt,
            "source_type": v.source_type,
            "style": v.style,
            "ratio": v.ratio,
            "duration": v.duration,
            "status": v.status,
            "video_url": v.video_url,
            "thumbnail_url": v.thumbnail_url,
            "is_favorite": v.is_favorite,
            "created_at": v.created_at,
        }
        for v in videos
    ]


@router.delete("/jobs/{job_id}")
def delete_video_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(VideoJob).filter(
        VideoJob.id == job_id, VideoJob.user_id == user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    db.delete(job)
    db.commit()
    return {"success": True, "message": "Video deleted"}


@router.patch("/jobs/{job_id}/favorite")
def toggle_video_favorite(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(VideoJob).filter(
        VideoJob.id == job_id, VideoJob.user_id == user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    job.is_favorite = not job.is_favorite
    db.commit()
    return {"success": True, "is_favorite": job.is_favorite}

