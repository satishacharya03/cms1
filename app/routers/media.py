from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Media, MediaType, Expedition, User, UserRole
from app.schemas import MediaResponse
from app.dependencies import require_role
from app.services.storage import save_file, get_file_path, file_exists, delete_file

router = APIRouter(prefix="/api/media", tags=["Media"])


@router.get("", response_model=List[MediaResponse])
def list_media(
    expedition_id: Optional[int] = None,
    media_type: Optional[MediaType] = Query(None, alias="type"),
    published: Optional[bool] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List expedition photos and videos with optional filters."""
    query = db.query(Media)
    if expedition_id:
        query = query.filter(Media.expedition_id == expedition_id)
    if media_type:
        query = query.filter(Media.media_type == media_type.value)
    if published is not None:
        query = query.filter(Media.published == published)
    if tags:
        query = query.filter(Media.tags.ilike(f"%{tags}%"))
    return query.order_by(Media.created_at.desc()).all()


@router.get("/{media_id}", response_model=MediaResponse)
def get_media(media_id: int, db: Session = Depends(get_db)):
    """Retrieve metadata for a specific media item."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found.")
    return media


@router.get("/{media_id}/file")
def get_media_file(media_id: int, db: Session = Depends(get_db)):
    """Serve the raw photo or video file."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found.")
    if not file_exists(media.file_path):
        raise HTTPException(status_code=404, detail="Media file not found on storage.")

    file_path = get_file_path(media.file_path)
    # Infer mime
    ext = file_path.suffix.lower().lstrip(".")
    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
    }
    media_type_header = mime_map.get(ext, "application/octet-stream")
    return FileResponse(path=str(file_path), media_type=media_type_header)


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
def create_media(
    expedition_id: int = Form(...),
    media_type: MediaType = Form(MediaType.PHOTO),
    caption: str = Form(...),
    location: Optional[str] = Form(None),
    timestamp_str: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    license: str = Form("CC-BY-4.0"),
    published: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Upload a new expedition photo or video."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Linked expedition not found.")

    saved_rel_path = save_file(file, "media")

    ts = None
    if timestamp_str:
        try:
            ts = datetime.fromisoformat(timestamp_str)
        except Exception:
            ts = None

    media = Media(
        expedition_id=expedition_id,
        media_type=media_type.value,
        caption=caption,
        location=location,
        timestamp=ts,
        file_path=saved_rel_path,
        tags=tags,
        license=license,
        published=published,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.put("/{media_id}", response_model=MediaResponse)
def update_media(
    media_id: int,
    caption: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    license: Optional[str] = Form(None),
    published: Optional[bool] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Update media item caption, tags, or replace media file."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found.")

    if caption is not None:
        media.caption = caption
    if location is not None:
        media.location = location
    if tags is not None:
        media.tags = tags
    if license is not None:
        media.license = license
    if published is not None:
        media.published = published

    if file is not None and file.filename:
        delete_file(media.file_path)
        media.file_path = save_file(file, "media")

    db.commit()
    db.refresh(media)
    return media


@router.post("/{media_id}/publish", response_model=MediaResponse)
def publish_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Set media item status to published=True."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found.")
    media.published = True
    db.commit()
    db.refresh(media)
    return media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)),
):
    """Delete media record and stored media asset."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found.")
    delete_file(media.file_path)
    db.delete(media)
    db.commit()
    return None
