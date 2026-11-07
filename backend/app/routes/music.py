from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import CreditTransaction
from app.models.media import AudioJob
from app.models.user import User
from app.services.audio_service import generate_music_track

router = APIRouter(prefix="/api/music", tags=["AI Music Generator"])

GENRES = {"Pop", "Hip-Hop", "Electronic", "Classical", "Jazz", "Rock", "Ambient", "Cinematic"}
MOODS = {"Happy", "Sad", "Energetic", "Relaxing", "Epic", "Romantic"}


@router.post("/generate")
def create_music(
    prompt: str = Form(...),
    genre: str = Form("Electronic"),
    mood: str = Form("Energetic"),
    duration: int = Form(15),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    if genre not in GENRES:
        genre = "Electronic"
    if mood not in MOODS:
        mood = "Energetic"

    duration = max(10, min(60, duration))

    if user.credits < 3:
        raise HTTPException(
            status_code=402,
            detail=f"Music generation requires 3 credits ({user.credits} available).",
        )

    user.credits -= 3
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-3,
        balance_after=user.credits,
        service="music",
        description=f"Generated AI music ({genre} - {mood}): '{prompt[:25]}...'",
    ))

    filename, provider = generate_music_track(prompt, genre, mood, duration)

    job = AudioJob(
        user_id=user.id,
        job_type="music",
        title=f"{genre} {mood}: {prompt[:30]}",
        prompt=prompt,
        genre=genre,
        mood=mood,
        duration=duration,
        status="completed",
        audio_url=f"/media/audio/{filename}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "success": True,
        "id": job.id,
        "title": job.title,
        "genre": job.genre,
        "mood": job.mood,
        "duration": job.duration,
        "audio_url": job.audio_url,
        "provider": provider,
        "remaining_credits": user.credits,
    }


@router.get("/history")
def list_music_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tracks = db.query(AudioJob).filter(
        AudioJob.user_id == user.id, AudioJob.job_type == "music"
    ).order_by(AudioJob.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "prompt": t.prompt,
            "genre": t.genre,
            "mood": t.mood,
            "duration": t.duration,
            "audio_url": t.audio_url,
            "is_favorite": t.is_favorite,
            "created_at": t.created_at,
        }
        for t in tracks
    ]


@router.delete("/{music_id}")
def delete_music(
    music_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    track = db.query(AudioJob).filter(
        AudioJob.id == music_id, AudioJob.user_id == user.id
    ).first()
    if not track:
        raise HTTPException(status_code=404, detail="Music track not found")
    db.delete(track)
    db.commit()
    return {"success": True, "message": "Music track deleted"}


@router.patch("/{music_id}/favorite")
def toggle_music_favorite(
    music_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    track = db.query(AudioJob).filter(
        AudioJob.id == music_id, AudioJob.user_id == user.id
    ).first()
    if not track:
        raise HTTPException(status_code=404, detail="Music track not found")
    track.is_favorite = not track.is_favorite
    db.commit()
    return {"success": True, "is_favorite": track.is_favorite}

