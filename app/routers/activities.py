"""
Activities Router for MATRIXCMS.
Handles CRUD and publishing workflows for news, events, and workshops.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, ActivityType, User, UserRole
from app.schemas import ActivityCreate, ActivityUpdate, ActivityResponse
from app.dependencies import require_role

router = APIRouter(prefix="/api/activities", tags=["Activities"])


@router.get("", response_model=List[ActivityResponse])
def list_activities(
    activity_type: Optional[ActivityType] = Query(
        None, description="Filter activities by type: news, event, workshop"
    ),
    published: Optional[bool] = Query(
        None, description="Filter activities by published status"
    ),
    db: Session = Depends(get_db),
):
    """
    List activities with optional filtering by activity_type and published status.
    Ordered by date descending, then creation timestamp descending.
    """
    query = db.query(Activity)

    if activity_type is not None:
        type_val = (
            activity_type.value
            if hasattr(activity_type, "value")
            else str(activity_type)
        )
        query = query.filter(Activity.activity_type == type_val)

    if published is not None:
        query = query.filter(Activity.published == published)

    return query.order_by(Activity.date.desc(), Activity.created_at.desc()).all()


@router.get("/{id}", response_model=ActivityResponse)
def get_activity(id: int, db: Session = Depends(get_db)):
    """
    Retrieve full details of a specific activity by its ID.
    """
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found.",
        )
    return activity


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity_in: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN.value,
            UserRole.DATA_MANAGER.value,
            UserRole.RESEARCHER.value,
        )
    ),
):
    """
    Create a new activity (news, event, or workshop).
    Protected: Requires researcher, data_manager, or admin role.
    """
    act_type = (
        activity_in.activity_type.value
        if hasattr(activity_in.activity_type, "value")
        else str(activity_in.activity_type)
    )

    activity = Activity(
        activity_type=act_type,
        title=activity_in.title,
        date=activity_in.date,
        description=activity_in.description,
        related_expedition_ids=activity_in.related_expedition_ids,
        published=activity_in.published,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.put("/{id}", response_model=ActivityResponse)
def update_activity(
    id: int,
    activity_in: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN.value,
            UserRole.DATA_MANAGER.value,
            UserRole.RESEARCHER.value,
        )
    ),
):
    """
    Update metadata for an existing activity.
    Protected: Requires researcher, data_manager, or admin role.
    """
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found.",
        )

    update_data = activity_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if field == "activity_type" and val is not None:
            setattr(
                activity,
                field,
                val.value if hasattr(val, "value") else str(val),
            )
        else:
            setattr(activity, field, val)

    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN.value,
            UserRole.DATA_MANAGER.value,
            UserRole.RESEARCHER.value,
        )
    ),
):
    """
    Delete an activity by ID.
    Protected: Requires researcher, data_manager, or admin role.
    """
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found.",
        )
    db.delete(activity)
    db.commit()
    return None


@router.post("/{id}/publish", response_model=ActivityResponse)
def publish_activity(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN.value,
            UserRole.DATA_MANAGER.value,
            UserRole.RESEARCHER.value,
        )
    ),
):
    """
    Publish an activity by setting published=True.
    Protected: Requires researcher, data_manager, or admin role.
    """
    activity = db.query(Activity).filter(Activity.id == id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found.",
        )
    activity.published = True
    db.commit()
    db.refresh(activity)
    return activity
