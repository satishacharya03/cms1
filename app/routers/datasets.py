from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models import Dataset, Expedition, User, UserRole
from app.schemas import DatasetResponse
from app.dependencies import require_role
from app.services.storage import save_file, get_file_path, file_exists, delete_file

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.get("", response_model=List[DatasetResponse])
def list_datasets(
    expedition_id: Optional[int] = None,
    published: Optional[bool] = None,
    year: Optional[int] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List scientific datasets with optional filtering."""
    query = db.query(Dataset)
    if expedition_id:
        query = query.filter(Dataset.expedition_id == expedition_id)
    if published is not None:
        query = query.filter(Dataset.published == published)
    if year:
        query = query.filter(extract("year", Dataset.created_at) == year)
    if keywords:
        query = query.filter(Dataset.keywords.ilike(f"%{keywords}%"))
    return query.order_by(Dataset.created_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Retrieve metadata for a specific dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Download the raw scientific dataset file (CSV, NetCDF, GeoJSON, etc.)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not file_exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found on server.")

    file_path = get_file_path(dataset.file_path)
    filename = file_path.name.split("_", 1)[-1] if "_" in file_path.name else file_path.name
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    title: str = Form(...),
    expedition_id: int = Form(...),
    variables: str = Form(...),
    units: str = Form(...),
    temporal_coverage: str = Form(...),
    spatial_coverage: str = Form(...),
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
    """Create a new scientific dataset with file upload."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Linked expedition does not exist.")

    saved_rel_path = save_file(file, "datasets")

    dataset = Dataset(
        expedition_id=expedition_id,
        title=title,
        variables=variables,
        units=units,
        temporal_coverage=temporal_coverage,
        spatial_coverage=spatial_coverage,
        file_path=saved_rel_path,
        doi=doi,
        license=license,
        keywords=keywords,
        published=published,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.put("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: int,
    title: Optional[str] = Form(None),
    expedition_id: Optional[int] = Form(None),
    variables: Optional[str] = Form(None),
    units: Optional[str] = Form(None),
    temporal_coverage: Optional[str] = Form(None),
    spatial_coverage: Optional[str] = Form(None),
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
    """Update dataset metadata and optionally replace file."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if expedition_id is not None:
        expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
        if not expedition:
            raise HTTPException(status_code=404, detail="Linked expedition not found.")
        dataset.expedition_id = expedition_id

    if title is not None:
        dataset.title = title
    if variables is not None:
        dataset.variables = variables
    if units is not None:
        dataset.units = units
    if temporal_coverage is not None:
        dataset.temporal_coverage = temporal_coverage
    if spatial_coverage is not None:
        dataset.spatial_coverage = spatial_coverage
    if doi is not None:
        dataset.doi = doi
    if license is not None:
        dataset.license = license
    if keywords is not None:
        dataset.keywords = keywords
    if published is not None:
        dataset.published = published

    if file is not None and file.filename:
        delete_file(dataset.file_path)
        dataset.file_path = save_file(file, "datasets")

    db.commit()
    db.refresh(dataset)
    return dataset


@router.post("/{dataset_id}/publish", response_model=DatasetResponse)
def publish_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value, UserRole.RESEARCHER.value)
    ),
):
    """Publish dataset, enabling public access and queuing automated outreach generation."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    dataset.published = True
    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value, UserRole.DATA_MANAGER.value)),
):
    """Delete dataset record and its file."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    delete_file(dataset.file_path)
    db.delete(dataset)
    db.commit()
    return None
