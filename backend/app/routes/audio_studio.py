import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import AUDIO_DIR
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.media import AudioStudioFile
from app.models.user import User
from app.services.audio_service import inspect_audio_file, process_audio_studio

router = APIRouter(prefix="/api/audio-studio", tags=["Audio Studio"])

ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a"}


@router.post("/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(status_code=400, detail="Only WAV, MP3, OGG, and M4A audio files are allowed")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 30 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file exceeds 30 MB limit")

    filename = f"studio_raw_{uuid.uuid4().hex}{ext}"
    filepath = AUDIO_DIR / filename
    filepath.write_bytes(content)

    meta = inspect_audio_file(str(filepath))

    record = AudioStudioFile(
        user_id=user.id,
        filename=filename,
        original_name=file.filename or "audio",
        file_path=str(filepath),
        file_size=len(content),
        duration_seconds=meta.get("duration_seconds", 0.0),
        format=meta.get("format", ext.lstrip(".")),
        sample_rate=meta.get("sample_rate", 44100),
        channels=meta.get("channels", 2),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "id": record.id,
        "filename": filename,
        "original_name": record.original_name,
        "audio_url": f"/media/audio/{filename}",
        "metadata": meta,
    }


@router.post("/process")
def process_audio(
    file_id: int = Form(...),
    start_sec: float = Form(0.0),
    end_sec: Optional[float] = Form(None),
    volume: float = Form(1.0),  # 0.1 to 3.0
    target_format: str = Form("wav"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.query(AudioStudioFile).filter(
        AudioStudioFile.id == file_id, AudioStudioFile.user_id == user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audio file not found")

    volume = max(0.05, min(4.0, volume))
    out_filename = f"studio_proc_{uuid.uuid4().hex}.{target_format}"
    
    result_filename = process_audio_studio(
        record.file_path,
        out_filename,
        start_sec=start_sec,
        end_sec=end_sec,
        volume_multiplier=volume,
        target_format=target_format,
    )
    
    out_filepath = AUDIO_DIR / result_filename
    meta = inspect_audio_file(str(out_filepath))

    new_record = AudioStudioFile(
        user_id=user.id,
        filename=result_filename,
        original_name=f"processed_{record.original_name}",
        file_path=str(out_filepath),
        file_size=os.path.getsize(str(out_filepath)),
        duration_seconds=meta.get("duration_seconds", 0.0),
        format=target_format,
        sample_rate=meta.get("sample_rate", 44100),
        channels=meta.get("channels", 2),
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return {
        "success": True,
        "id": new_record.id,
        "audio_url": f"/media/audio/{result_filename}",
        "filename": result_filename,
        "metadata": meta,
    }


@router.get("/files")
def list_studio_files(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    files = db.query(AudioStudioFile).filter(
        AudioStudioFile.user_id == user.id
    ).order_by(AudioStudioFile.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "original_name": f.original_name,
            "audio_url": f"/media/audio/{f.filename}",
            "file_size": f.file_size,
            "duration": f.duration_seconds,
            "format": f.format,
            "created_at": f.created_at,
        }
        for f in files
    ]


@router.delete("/files/{file_id}")
def delete_studio_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = db.query(AudioStudioFile).filter(
        AudioStudioFile.id == file_id, AudioStudioFile.user_id == user.id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        if os.path.exists(f.file_path):
            os.remove(f.file_path)
    except Exception:
        pass

    db.delete(f)
    db.commit()
    return {"success": True, "message": "File deleted"}

