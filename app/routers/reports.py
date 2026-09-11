from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models import Report, Expedition, User, UserRole
from app.schemas import ReportResponse
from app.dependencies import require_role
from app.services.storage import save_file, get_file_path, file_exists, delete_file

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("", response_model=List[ReportResponse])
def list_reports(
    expedition_id: Optional[int] = None,
    published: Optional[bool] = None,
    year: Optional[int] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List scientific reports with optional filters."""
    query = db.query(Report)
    if expedition_id:
        query = query.filter(Report.expedition_id == expedition_id)
    if published is not None:
        query = query.filter(Report.published == published)
    if year:
        query = query.filter(extract("year", Report.created_at) == year)
    if keywords:
        query = query.filter(Report.keywords.ilike(f"%{keywords}%"))
    return query.order_by(Report.created_at.desc()).all()


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Retrieve metadata for a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """Download the attached report document file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not file_exists(report.file_path):
        raise HTTPException(status_code=404, detail="Associated report file not found on server.")

    file_path = get_file_path(report.file_path)
    filename = file_path.name.split("_", 1)[-1] if "_" in file_path.name else file_path.name
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    title: str = Form(...),
    expedition_id: int = Form(...),
    authors: str = Form(...),
    abstract: str = Form(...),
    doi: Optional[str] = Form(None),
    license: str = Form("CC-BY-4.0"),
    keywords: Optional[str] = Form(None),
    published: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Create a new scientific report with document upload."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Linked expedition does not exist.")

    saved_rel_path = save_file(file, "reports")

    report = Report(
        expedition_id=expedition_id,
        title=title,
        authors=authors,
        abstract=abstract,
        file_path=saved_rel_path,
        doi=doi,
        license=license,
        keywords=keywords,
        published=published,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    title: Optional[str] = Form(None),
    expedition_id: Optional[int] = Form(None),
    authors: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    doi: Optional[str] = Form(None),
    license: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    published: Optional[bool] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Update report metadata and optionally upload a replacement file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if expedition_id is not None:
        expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
        if not expedition:
            raise HTTPException(status_code=404, detail="Linked expedition not found.")
        report.expedition_id = expedition_id

    if title is not None:
        report.title = title
    if authors is not None:
        report.authors = authors
    if abstract is not None:
        report.abstract = abstract
    if doi is not None:
        report.doi = doi
    if license is not None:
        report.license = license
    if keywords is not None:
        report.keywords = keywords
    if published is not None:
        report.published = published

    if file is not None and file.filename:
        delete_file(report.file_path)
        report.file_path = save_file(file, "reports")

    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/publish", response_model=ReportResponse)
def publish_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Set report status to published=True."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    report.published = True
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)),
):
    """Delete report record and clean up stored file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    delete_file(report.file_path)
    db.delete(report)
    db.commit()
    return None
