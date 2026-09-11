"""
Admin Generated Content Outreach Review Router for MATRIXCMS.
Enables review, editing, approval, rejection, and manual triggers of
LLM-generated multi-platform outreach drafts (web_summary, tweet, linkedin, instagram).
All endpoints protected and restricted to admin and data_manager roles.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    GeneratedContent,
    Activity,
    Report,
    Dataset,
    User,
    UserRole,
    ContentSourceType,
    PlatformType,
    ContentStatus,
    ActivityType,
)
from app.schemas import (
    GeneratedContentResponse,
    GeneratedContentUpdate,
)
from app.dependencies import require_role
from app.tasks.content_generation_job import run_content_generation

router = APIRouter(prefix="/api/admin/generated-content", tags=["Admin Outreach Review"])


@router.get("", response_model=List[GeneratedContentResponse])
def list_generated_content(
    response: Response,
    source_type: Optional[ContentSourceType] = Query(
        None, description="Filter by source type: report, dataset, activity"
    ),
    platform: Optional[PlatformType] = Query(
        None, description="Filter by platform: web_summary, tweet, linkedin, instagram"
    ),
    status_filter: Optional[ContentStatus] = Query(
        None, alias="status", description="Filter by review status: pending_review, approved, rejected"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    List generated outreach content items with optional filtering and pagination.
    Protected: Admin and Data Manager only.
    """
    query = db.query(GeneratedContent)

    if source_type is not None:
        type_val = source_type.value if hasattr(source_type, "value") else str(source_type)
        query = query.filter(GeneratedContent.source_type == type_val)

    if platform is not None:
        plat_val = platform.value if hasattr(platform, "value") else str(platform)
        query = query.filter(GeneratedContent.platform == plat_val)

    if status_filter is not None:
        stat_val = status_filter.value if hasattr(status_filter, "value") else str(status_filter)
        query = query.filter(GeneratedContent.status == stat_val)

    total = query.count()
    response.headers["X-Total-Count"] = str(total)

    items = (
        query.order_by(GeneratedContent.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return items


@router.post("/trigger")
def trigger_content_generation(
    background_tasks: BackgroundTasks,
    background: bool = Query(
        False, description="Run content generation scan asynchronously in background"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    Manual scan trigger calling run_content_generation.
    Scans for published reports, datasets, and activities lacking outreach drafts and generates them.
    Protected: Admin and Data Manager only.
    """
    if background:
        background_tasks.add_task(run_content_generation)
        return {
            "status": "accepted",
            "message": "Outreach content generation scan scheduled in background.",
        }

    run_content_generation(db)
    return {
        "status": "success",
        "message": "Outreach content generation scan completed successfully.",
    }


@router.get("/{id}", response_model=GeneratedContentResponse)
def get_generated_content(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    Retrieve full details of a specific generated content draft.
    Protected: Admin and Data Manager only.
    """
    item = db.query(GeneratedContent).filter(GeneratedContent.id == id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content record not found.",
        )
    return item


@router.put("/{id}", response_model=GeneratedContentResponse)
def update_generated_content(
    id: int,
    gc_in: GeneratedContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    Edit generated outreach draft content and/or status.
    Protected: Admin and Data Manager only.
    """
    item = db.query(GeneratedContent).filter(GeneratedContent.id == id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content record not found.",
        )

    update_data = gc_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if field == "status" and val is not None:
            setattr(item, field, val.value if hasattr(val, "value") else str(val))
        else:
            setattr(item, field, val)

    db.commit()
    db.refresh(item)
    return item


@router.post("/{id}/approve", response_model=GeneratedContentResponse)
def approve_generated_content(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    Approve generated outreach content draft.
    Sets status to approved; if platform is web_summary, automatically creates an Activity of type news.
    Protected: Admin and Data Manager only.
    """
    item = db.query(GeneratedContent).filter(GeneratedContent.id == id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content record not found.",
        )

    was_approved = item.status == ContentStatus.APPROVED.value
    item.status = ContentStatus.APPROVED.value

    # If platform is web_summary and was not already approved, create Activity of type news
    if item.platform == PlatformType.WEB_SUMMARY.value and not was_approved:
        news_title = "Outreach News"
        related_expeditions = []

        if item.source_type == ContentSourceType.REPORT.value:
            report = db.query(Report).filter(Report.id == item.source_id).first()
            if report:
                news_title = f"News: {report.title}"
                if report.expedition_id:
                    related_expeditions = [report.expedition_id]
        elif item.source_type == ContentSourceType.DATASET.value:
            dataset = db.query(Dataset).filter(Dataset.id == item.source_id).first()
            if dataset:
                news_title = f"News: {dataset.title}"
                if dataset.expedition_id:
                    related_expeditions = [dataset.expedition_id]
        elif item.source_type == ContentSourceType.ACTIVITY.value:
            act = db.query(Activity).filter(Activity.id == item.source_id).first()
            if act:
                news_title = f"News Update: {act.title}"
                if act.related_expedition_ids:
                    related_expeditions = act.related_expedition_ids

        if not news_title or news_title == "Outreach News":
            news_title = f"Scientific News: {item.source_type.title()} #{item.source_id}"

        activity = Activity(
            activity_type=ActivityType.NEWS.value,
            title=news_title[:255],
            date=datetime.now(timezone.utc).date(),
            description=item.content,
            related_expedition_ids=related_expeditions,
            published=True,
        )
        db.add(activity)

    db.commit()
    db.refresh(item)
    return item


@router.post("/{id}/reject", response_model=GeneratedContentResponse)
def reject_generated_content(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)
    ),
):
    """
    Reject generated outreach content draft (sets status to rejected).
    Protected: Admin and Data Manager only.
    """
    item = db.query(GeneratedContent).filter(GeneratedContent.id == id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content record not found.",
        )

    item.status = ContentStatus.REJECTED.value
    db.commit()
    db.refresh(item)
    return item
