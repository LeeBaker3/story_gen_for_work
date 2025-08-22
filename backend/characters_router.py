from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

from . import schemas, auth, crud, database, ai_services
from .logging_config import app_logger, error_logger

router = APIRouter(prefix="/characters", tags=["characters"])


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
            base_dir_on_disk = os.path.join("data", base_dir_for_db)
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
    base_dir_on_disk = os.path.join("data", base_dir_for_db)
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


@router.delete("/{char_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(char_id: int, db: Session = Depends(database.get_db), current_user: database.User = Depends(auth.get_current_active_user)):
    ok = crud.delete_character(db, current_user.id, char_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Character not found")
    return None
