from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

from . import schemas, auth, crud, database, ai_services, storage_paths
from .settings import get_settings
from .logging_config import app_logger, error_logger

router = APIRouter(prefix="/characters", tags=["characters"])


def _ext_from_upload(upload: UploadFile) -> str:
    """Map supported image content types (and extensions) to a safe extension."""
    content_type = (upload.content_type or "").lower().strip()
    if content_type == "image/jpeg":
        return "jpg"
    if content_type == "image/png":
        return "png"
    if content_type == "image/webp":
        return "webp"

    filename = (upload.filename or "").lower()
    if filename.endswith(".jpeg") or filename.endswith(".jpg"):
        return "jpg"
    if filename.endswith(".png"):
        return "png"
    if filename.endswith(".webp"):
        return "webp"

    raise HTTPException(
        status_code=415,
        detail="Unsupported file type. Please upload a JPG, PNG, or WEBP image.",
    )


async def _write_upload_to_path(upload: UploadFile, out_path: str, max_bytes: int) -> int:
    """Stream an UploadFile to disk with a hard byte limit."""
    written = 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max allowed is {max_bytes} bytes.",
                )
            f.write(chunk)
    return written


@router.post("/", response_model=schemas.CharacterOut, status_code=status.HTTP_201_CREATED)
async def create_character(
    payload: schemas.CharacterCreate,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    # Name-based dedupe: if a character with same name exists (case-insensitive) for this user,
    # update it with provided fields; else create new.
    existing = crud.get_character_by_name_ci(
        db, current_user.id, (payload.name or "").strip())
    if existing:
        update_data = schemas.CharacterUpdate(
            description=payload.description,
            age=payload.age,
            gender=payload.gender,
            clothing_style=payload.clothing_style,
            key_traits=payload.key_traits,
            image_style=payload.image_style,
        )
        ch = crud.update_character(
            db, current_user.id, existing.id, update_data)
    else:
        ch = crud.create_character(db, current_user.id, payload)

    # Optionally generate first image
    if payload.generate_image:
        try:
            # Build prompt from fields
            details = []
            if ch.description:
                details.append(ch.description)
            if ch.clothing_style:
                details.append(f"wearing {ch.clothing_style}")
            if ch.key_traits:
                details.append(f"traits: {ch.key_traits}")
            if ch.age:
                details.append(f"age {ch.age}")
            if ch.gender:
                details.append(f"{ch.gender}")
            prompt = f"Character portrait of {ch.name}, " + ", ".join(details)

            # Map storage paths
            base_dir_for_db = os.path.join(
                "images", f"user_{current_user.id}", "characters", f"{ch.id}")
            settings = get_settings()
            base_dir_on_disk = os.path.join(settings.data_dir, base_dir_for_db)
            os.makedirs(base_dir_on_disk, exist_ok=True)
            img_id = str(uuid.uuid4())
            file_name = f"{img_id}.png"
            img_path_for_db = os.path.join(base_dir_for_db, file_name)
            img_path_on_disk = os.path.join(base_dir_on_disk, file_name)

            # Generate
            # generate_image is sync; run in a thread
            image_bytes = await ai_services.asyncio.to_thread(

                ai_services.generate_image, prompt, None, "1024x1024"
            )
            if image_bytes:
                with open(img_path_on_disk, "wb") as f:
                    f.write(image_bytes)
                crud.add_character_image(
                    db, current_user.id, ch.id, img_path_for_db, prompt, ch.image_style)
        except Exception as e:
            error_logger.error(
                f"Failed to generate character image for {ch.id}: {e}", exc_info=True)

    return ch


@router.get("/", response_model=schemas.PaginatedCharacters)
def list_characters(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    total, items = crud.list_characters(
        db, current_user.id, q=q, page=page, page_size=page_size)
    list_items = []
    for ch in items:
        thumb = ch.current_image.file_path if ch.current_image else None
        list_items.append(schemas.CharacterListItem(
            id=ch.id, name=ch.name, updated_at=ch.updated_at, thumbnail_path=thumb))
    return schemas.PaginatedCharacters(items=list_items, total=total, page=page, page_size=page_size)


@router.get("/{char_id}", response_model=schemas.CharacterOut)
def get_character(char_id: int, db: Session = Depends(database.get_db), current_user: database.User = Depends(auth.get_current_active_user)):
    ch = crud.get_character(db, current_user.id, char_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")
    return ch


@router.post("/{char_id}/photo", response_model=schemas.CharacterPhotoUploadResponse)
async def upload_character_photo(
    char_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Upload a private character photo for reference-image generation.

    The uploaded photo is stored outside `DATA_DIR` so it is never publicly
    accessible via `/static_content`.
    """
    ch = crud.get_character(db, current_user.id, char_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    settings = get_settings()
    ext = _ext_from_upload(photo)

    upload_dir = storage_paths.character_uploads_abs(current_user.id, ch.id)
    final_path = os.path.join(upload_dir, f"photo.{ext}")

    # Remove any previous uploaded photo regardless of extension.
    for candidate in storage_paths.character_uploaded_photo_candidates_abs(
        current_user.id, ch.id
    ):
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass

    tmp_path = os.path.join(upload_dir, f"upload_{uuid.uuid4().hex}.tmp")
    try:
        size_bytes = await _write_upload_to_path(photo, tmp_path, settings.max_upload_bytes)
        os.replace(tmp_path, final_path)
    finally:
        # Ensure temp file is cleaned up if anything failed.
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return schemas.CharacterPhotoUploadResponse(
        character_id=ch.id,
        content_type=photo.content_type or "",
        size_bytes=size_bytes,
    )


@router.put("/{char_id}", response_model=schemas.CharacterOut)
def update_character(char_id: int, payload: schemas.CharacterUpdate, db: Session = Depends(database.get_db), current_user: database.User = Depends(auth.get_current_active_user)):
    ch = crud.update_character(db, current_user.id, char_id, payload)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")
    return ch


@router.post("/{char_id}/regenerate-image", response_model=schemas.CharacterOut)
async def regenerate_character_image(char_id: int, payload: schemas.RegenerateImageRequest, db: Session = Depends(database.get_db), current_user: database.User = Depends(auth.get_current_active_user)):
    ch = crud.get_character(db, current_user.id, char_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build prompt using new description or existing
    description = payload.description if payload and payload.description else ch.description or ""
    style = payload.image_style if payload and payload.image_style else ch.image_style or ""
    parts = [f"Character portrait of {ch.name}"]
    if description:
        parts.append(description)
    if ch.clothing_style:
        parts.append(f"wearing {ch.clothing_style}")
    if ch.key_traits:
        parts.append(f"traits: {ch.key_traits}")
    if ch.age:
        parts.append(f"age {ch.age}")
    if ch.gender:
        parts.append(f"{ch.gender}")
    if style:
        parts.append(f"style: {style}")
    prompt = ", ".join(parts)

    # Storage paths
    base_dir_for_db = os.path.join(
        "images", f"user_{current_user.id}", "characters", f"{ch.id}")
    settings = get_settings()
    base_dir_on_disk = os.path.join(settings.data_dir, base_dir_for_db)
    os.makedirs(base_dir_on_disk, exist_ok=True)
    img_id = str(uuid.uuid4())
    file_name = f"{img_id}.png"
    img_path_for_db = os.path.join(base_dir_for_db, file_name)
    img_path_on_disk = os.path.join(base_dir_on_disk, file_name)

    try:
        try:
            image_bytes = await ai_services.asyncio.to_thread(
                ai_services.generate_image, prompt, None, "1024x1024"
            )
        except ValueError as ve:
            # Likely missing OPENAI_API_KEY / client not configured
            raise HTTPException(status_code=503, detail=str(ve))
        except PermissionError as pe:
            # OpenAI auth failed (bad/expired API key)
            raise HTTPException(status_code=401, detail=str(pe))
        if image_bytes:
            with open(img_path_on_disk, "wb") as f:
                f.write(image_bytes)
            crud.add_character_image(
                db, current_user.id, ch.id, img_path_for_db, prompt, style)
        else:
            raise HTTPException(
                status_code=500, detail="Image generation failed")
    except Exception as e:
        error_logger.error(
            f"Failed to regenerate character image for {ch.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Image generation error: {e}")

    # Return fresh object
    ch = crud.get_character(db, current_user.id, char_id)
    return ch


@router.post("/{char_id}/generate-from-photo", response_model=schemas.CharacterOut)
async def generate_reference_image_from_photo(
    char_id: int,
    payload: schemas.GenerateReferenceFromPhotoRequest,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Generate a character reference image using the uploaded photo as input."""
    ch = crud.get_character(db, current_user.id, char_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    # Persist any updated description/style from step 3.
    update = schemas.CharacterUpdate(
        description=payload.description,
        image_style=payload.image_style,
    )
    ch = crud.update_character(db, current_user.id, ch.id, update) or ch

    # Find the private uploaded photo.
    photo_path = None
    for candidate in storage_paths.character_uploaded_photo_candidates_abs(
        current_user.id, ch.id
    ):
        if os.path.exists(candidate):
            photo_path = candidate
            break
    if not photo_path:
        raise HTTPException(
            status_code=400,
            detail="No uploaded photo found for this character. Upload a photo first.",
        )

    # Build prompt.
    description = (payload.description or ch.description or "").strip()
    if not description:
        raise HTTPException(
            status_code=400,
            detail="A description is required to generate an image.",
        )
    business_style = (payload.image_style or ch.image_style or "").strip()

    # Follow the same prompt-pattern used in `backend/ai_services.py`:
    # - prefer style at the front ("A {style} style ...")
    # - optionally map the business style to a richer phrase
    # - choose OpenAI style (vivid/natural) via the DB mapping, but never fail generation
    openai_style: Optional[str] = None
    style_reference = business_style
    try:
        if business_style:
            openai_style = ai_services.get_openai_image_style(
                db=db,
                business_style=business_style,
            )
    except Exception:
        openai_style = None

    try:
        if business_style and getattr(get_settings(), "enable_image_style_mapping", False):
            mapped = ai_services.map_style(business_style)
            if mapped:
                style_reference = mapped
    except Exception:
        style_reference = business_style

    parts = []
    if style_reference:
        parts.append(f"A {style_reference} style character portrait of {ch.name}")
    else:
        parts.append(f"A character portrait of {ch.name}")
    parts.append(description)
    if ch.clothing_style:
        parts.append(f"wearing {ch.clothing_style}")
    if ch.key_traits:
        parts.append(f"traits: {ch.key_traits}")
    if ch.age:
        parts.append(f"age {ch.age}")
    if ch.gender:
        parts.append(f"{ch.gender}")
    prompt = ". ".join([p for p in parts if p])

    # Match the reference-image design: a single character sheet image that includes
    # three angles/views (front/side/back) in one frame.
    prompt = (
        f"{prompt}. "
        "Create a full-body character sheet as a single image with three views of the same character: "
        "front view, side view, and back view. "
        "The character should be centered and not cropped (head and feet fully visible). "
        "Use a simple background (not transparent). "
        "No text, no labels, no watermark."
    )

    # Storage paths for the generated reference image (public under DATA_DIR).
    settings = get_settings()
    base_dir_for_db = os.path.join(
        "images", f"user_{current_user.id}", "characters", f"{ch.id}"
    )
    base_dir_on_disk = os.path.join(settings.data_dir, base_dir_for_db)
    os.makedirs(base_dir_on_disk, exist_ok=True)
    img_id = str(uuid.uuid4())
    file_name = f"{img_id}.png"
    img_path_for_db = os.path.join(base_dir_for_db, file_name)
    img_path_on_disk = os.path.join(base_dir_on_disk, file_name)

    try:
        try:
            image_bytes = await ai_services.asyncio.to_thread(
                ai_services.generate_image,
                prompt=prompt,
                reference_image_paths=[photo_path],
                size="1024x1536",
                openai_style=openai_style,
            )
        except ValueError as ve:
            raise HTTPException(status_code=503, detail=str(ve))
        except PermissionError as pe:
            raise HTTPException(status_code=401, detail=str(pe))
        except Exception as e:
            # OpenAI SDK errors (including billing hard limit) currently surface as
            # generic exceptions here. Return an actionable message.
            msg = str(e)
            if "billing_hard_limit" in msg or "Billing hard limit" in msg:
                raise HTTPException(
                    status_code=402,
                    detail="OpenAI billing hard limit reached. Add credits or raise the limit to generate images.",
                )
            raise HTTPException(
                status_code=502,
                detail="OpenAI image generation failed. Check server logs for details.",
            )

        if not image_bytes:
            raise HTTPException(
                status_code=500, detail="Image generation failed")
        with open(img_path_on_disk, "wb") as f:
            f.write(image_bytes)
        crud.add_character_image(
            db, current_user.id, ch.id, img_path_for_db, prompt, business_style
        )
    except HTTPException:
        raise
    except Exception as e:
        error_logger.error(
            f"Failed to generate character reference image from photo for {ch.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Image generation error")

    return crud.get_character(db, current_user.id, ch.id)


@router.delete("/{char_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(char_id: int, db: Session = Depends(database.get_db), current_user: database.User = Depends(auth.get_current_active_user)):
    ok = crud.delete_character(db, current_user.id, char_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Character not found")
    return None
