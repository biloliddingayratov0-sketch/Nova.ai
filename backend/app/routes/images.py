from io import BytesIO
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import GENERATED_DIR
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.image import ImageHistory
from app.models.user import User
from app.models.billing import CreditTransaction
from app.models.notification import Notification
from app.services.ai_service import edit_image, generate_image, generate_variation

logger = logging.getLogger("nova_ai.routes.images")

router = APIRouter(prefix="/api/images", tags=["AI Images"])

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
SIZES = {
    "1:1": "1024x1024",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
    "4:3": "1024x768",
    "3:2": "1080x720",
}
ALLOWED_STYLES = {
    "Photorealistic", "Cinematic", "Anime", "3D Render",
    "Digital Art", "Fantasy", "Minimalist", "Architecture",
    "Product Photography", "Portrait", "Oil Painting",
}


def validate_image_bytes(image_bytes: bytes) -> None:
    if len(image_bytes) < 12:
        raise HTTPException(status_code=400, detail="Corrupted image file")

    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_webp = image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[8:16]

    if not (is_png or is_jpeg or is_webp):
        raise HTTPException(
            status_code=400,
            detail="File content does not match allowed image formats (PNG, JPEG, WEBP)",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as uploaded:
            uploaded.verify()
            if uploaded.format not in ("PNG", "JPEG", "WEBP"):
                raise HTTPException(status_code=400, detail="Unsupported image format")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or malicious image file")


def validate_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    if len(prompt) > 2000:
        raise HTTPException(status_code=400, detail="Prompt is too long (max 2000 chars)")
    return prompt


def validate_style(style: str) -> str:
    if style not in ALLOWED_STYLES:
        return "Photorealistic"
    return style


def deduct_user_credits(db: Session, user: User, amount: int, service: str, description: str):
    if user.credits < amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient AI credits ({user.credits} available, {amount} required). Please upgrade your subscription.",
        )
    user.credits -= amount
    txn = CreditTransaction(
        user_id=user.id,
        amount=-amount,
        balance_after=user.credits,
        service=service,
        description=description,
    )
    db.add(txn)
    db.commit()


def save_history(
    db: Session,
    user: User,
    prompt: str,
    filename: str,
    operation: str,
    style: str = "Photorealistic",
    ratio: str = "1:1",
) -> ImageHistory:
    record = ImageHistory(
        user_id=user.id,
        prompt=prompt,
        filename=filename,
        operation=operation,
        style=style,
        ratio=ratio,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/generate")
def create_image(
    prompt: str = Form(...),
    ratio: str = Form("1:1"),
    style: str = Form("Photorealistic"),
    negative_prompt: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prompt = validate_prompt(prompt)
    style = validate_style(style)
    if ratio not in SIZES:
        ratio = "1:1"

    # Check and deduct 2 credits for generation
    deduct_user_credits(db, user, 2, "image_generate", f"Generated image: '{prompt[:30]}...'")

    full_prompt = prompt
    if negative_prompt.strip():
        full_prompt += f" (Avoid: {negative_prompt.strip()})"

    try:
        filename, provider = generate_image(full_prompt, SIZES.get(ratio, "1024x1024"), style)
        record = save_history(db, user, prompt, filename, "generate", style, ratio)
        
        # Notification
        db.add(Notification(
            user_id=user.id,
            title="Image Generation Complete",
            message=f"Your image '{prompt[:35]}...' has been generated using {provider}.",
            type="success",
            link=f"/generated/{filename}",
        ))
        db.commit()

        return {
            "success": True,
            "id": record.id,
            "filename": filename,
            "image": f"/generated/{filename}",
            "provider": provider,
            "remaining_credits": user.credits,
        }
    except HTTPException:
        # Refund on failure
        user.credits += 2
        db.commit()
        raise
    except Exception as exc:
        user.credits += 2
        db.commit()
        logger.error(f"Generate image failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"AI image generation failed: {str(exc)}",
        ) from exc


@router.post("/edit")
async def transform_image(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    ratio: str = Form("1:1"),
    style: str = Form("Photorealistic"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prompt = validate_prompt(prompt)
    style = validate_style(style)

    if ratio not in SIZES:
        ratio = "1:1"
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PNG, JPEG, and WEBP images are supported",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image exceeds 15MB limit")

    validate_image_bytes(image_bytes)

    # Deduct 2 credits for image editing
    deduct_user_credits(db, user, 2, "image_edit", f"Edited image: '{prompt[:30]}...'")

    try:
        filename, provider = edit_image(
            image_bytes,
            image.filename or "upload.png",
            prompt,
            SIZES.get(ratio, "1024x1024"),
            style,
        )
        record = save_history(db, user, prompt, filename, "edit", style, ratio)

        db.add(Notification(
            user_id=user.id,
            title="Image Editing Complete",
            message=f"Your image transformation '{prompt[:35]}...' succeeded using {provider}.",
            type="success",
            link=f"/generated/{filename}",
        ))
        db.commit()

        return {
            "success": True,
            "id": record.id,
            "filename": filename,
            "image": f"/generated/{filename}",
            "provider": provider,
            "remaining_credits": user.credits,
        }
    except HTTPException:
        user.credits += 2
        db.commit()
        raise
    except Exception as exc:
        user.credits += 2
        db.commit()
        logger.error(f"Image edit failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"AI image editing failed: {str(exc)}",
        ) from exc


@router.post("/variation")
async def create_variation(
    image: UploadFile = File(...),
    ratio: str = Form("1:1"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PNG, JPEG, and WEBP images are supported",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image exceeds 15MB")

    validate_image_bytes(image_bytes)

    if ratio not in SIZES:
        ratio = "1:1"

    deduct_user_credits(db, user, 2, "image_variation", "Image variation created")

    try:
        filename, provider = generate_variation(image_bytes, SIZES.get(ratio, "1024x1024"))
        record = save_history(db, user, "Image variation", filename, "variation", ratio=ratio)
        return {
            "success": True,
            "id": record.id,
            "filename": filename,
            "image": f"/generated/{filename}",
            "provider": provider,
            "remaining_credits": user.credits,
        }
    except HTTPException:
        user.credits += 2
        db.commit()
        raise
    except Exception as exc:
        user.credits += 2
        db.commit()
        logger.error(f"Image variation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"AI image variation failed: {str(exc)}",
        ) from exc
