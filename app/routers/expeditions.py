from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models import Expedition, ExpeditionStatus, User, UserRole
from app.schemas import ExpeditionCreate, ExpeditionUpdate, ExpeditionResponse
from app.dependencies import require_role

router = APIRouter(prefix="/api/expeditions", tags=["Expeditions"])


@router.get("", response_model=List[ExpeditionResponse])
def list_expeditions(
    status_filter: Optional[ExpeditionStatus] = Query(None, alias="status"),
    region: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List expeditions with optional filtering by status, region, and year."""
    query = db.query(Expedition)
    if status_filter:
        query = query.filter(Expedition.status == status_filter.value)
    if region:
        query = query.filter(Expedition.region.ilike(f"%{region}%"))
    if year:
        query = query.filter(extract("year", Expedition.start_date) == year)
    return query.order_by(Expedition.start_date.desc()).all()


@router.get("/{expedition_id}", response_model=ExpeditionResponse)
def get_expedition(expedition_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of a specific scientific expedition."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedition not found.")
    return expedition


@router.post("", response_model=ExpeditionResponse, status_code=status.HTTP_201_CREATED)
def create_expedition(
    exp_in: ExpeditionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Create a new scientific expedition (researcher, data_manager, admin)."""
    expedition = Expedition(
        name=exp_in.name,
        start_date=exp_in.start_date,
        end_date=exp_in.end_date,
        region=exp_in.region,
        objectives=exp_in.objectives,
        team_leader=exp_in.team_leader,
        status=exp_in.status.value,
    )
    db.add(expedition)
    db.commit()
    db.refresh(expedition)
    return expedition


@router.put("/{expedition_id}", response_model=ExpeditionResponse)
def update_expedition(
    expedition_id: int,
    exp_in: ExpeditionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Update expedition metadata."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedition not found.")

    update_data = exp_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if field == "status" and val is not None:
            setattr(expedition, field, val.value if hasattr(val, "value") else str(val))
        else:
            setattr(expedition, field, val)

    db.commit()
    db.refresh(expedition)
    return expedition


@router.delete("/{expedition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expedition(
    expedition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)),
):
    """Delete an expedition (admin, data_manager only)."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedition not found.")
    db.delete(expedition)
    db.commit()
    return None
