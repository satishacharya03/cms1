from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Publication, Expedition, User, UserRole
from app.schemas import PublicationCreate, PublicationUpdate, PublicationResponse
from app.dependencies import require_role

router = APIRouter(prefix="/api/publications", tags=["Publications"])


@router.get("", response_model=List[PublicationResponse])
def list_publications(
    expedition_id: Optional[int] = None,
    year: Optional[int] = None,
    published: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List scientific publications with optional filtering."""
    query = db.query(Publication)
    if expedition_id:
        query = query.filter(Publication.expedition_id == expedition_id)
    if year:
        query = query.filter(Publication.year == year)
    if published is not None:
        query = query.filter(Publication.published == published)
    return query.order_by(Publication.year.desc(), Publication.created_at.desc()).all()


@router.get("/{publication_id}", response_model=PublicationResponse)
def get_publication(publication_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a single scientific publication."""
    pub = db.query(Publication).filter(Publication.id == publication_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")
    return pub


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
def create_publication(
    pub_in: PublicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Register a new research publication."""
    expedition = db.query(Expedition).filter(Expedition.id == pub_in.expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Linked expedition not found.")

    pub = Publication(
        expedition_id=pub_in.expedition_id,
        title=pub_in.title,
        authors=pub_in.authors,
        journal=pub_in.journal,
        year=pub_in.year,
        doi=pub_in.doi,
        abstract=pub_in.abstract,
        link=pub_in.link,
        published=pub_in.published,
    )
    db.add(pub)
    db.commit()
    db.refresh(pub)
    return pub


@router.put("/{publication_id}", response_model=PublicationResponse)
def update_publication(
    publication_id: int,
    pub_in: PublicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Update publication metadata."""
    pub = db.query(Publication).filter(Publication.id == publication_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")

    update_data = pub_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(pub, field, val)

    db.commit()
    db.refresh(pub)
    return pub


@router.post("/{publication_id}/publish", response_model=PublicationResponse)
def publish_publication(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Publish a scientific publication."""
    pub = db.query(Publication).filter(Publication.id == publication_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")
    pub.published = True
    db.commit()
    db.refresh(pub)
    return pub


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publication(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)),
):
    """Delete a publication record."""
    pub = db.query(Publication).filter(Publication.id == publication_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")
    db.delete(pub)
    db.commit()
    return None
