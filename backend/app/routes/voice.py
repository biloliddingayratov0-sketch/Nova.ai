from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import CreditTransaction
from app.models.media import AudioJob
from app.models.user import User
from app.services.audio_service import text_to_speech, transcribe_audio

router = APIRouter(prefix="/api/voice", tags=["AI Voice Assistant"])


@router.post("/tts")
def generate_speech(
    text: str = Form(...),
    voice: str = Form("alloy"),
    speed: float = Form(1.0),
    language: str = Form("en"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Text exceeds 4000 character limit")

    if user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits for voice generation.")

    # Deduct 1 credit
    user.credits -= 1
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-1,
        balance_after=user.credits,
        service="voice",
        description=f"Generated voice TTS: '{text[:25]}...'",
    ))

    filename, provider = text_to_speech(text, voice, speed, language)

    job = AudioJob(
        user_id=user.id,
        job_type="voice_tts",
        title=f"Voice: {text[:30]}",
        prompt=text,
        voice=voice,
        language=language,
        speed=speed,
        status="completed",
        audio_url=f"/media/audio/{filename}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "success": True,
        "id": job.id,
        "audio_url": job.audio_url,
        "filename": filename,
        "provider": provider,
        "remaining_credits": user.credits,
    }


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    transcript = transcribe_audio(content, audio.filename or "recording.wav")
    return {
        "success": True,
        "transcript": transcript,
    }


@router.get("/history")
def list_voice_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = db.query(AudioJob).filter(
        AudioJob.user_id == user.id, AudioJob.job_type == "voice_tts"
    ).order_by(AudioJob.created_at.desc()).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "text": j.prompt,
            "voice": j.voice,
            "language": j.language,
            "speed": j.speed,
            "audio_url": j.audio_url,
            "created_at": j.created_at,
        }
        for j in jobs
    ]

