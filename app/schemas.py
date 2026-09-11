from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import (
    UserRole,
    ExpeditionStatus,
    MediaType,
    ActivityType,
    ContentSourceType,
    PlatformType,
    ContentStatus,
)


# ===================== USER SCHEMAS =====================

class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.PUBLIC


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[UserRole] = UserRole.PUBLIC


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# ===================== EXPEDITION SCHEMAS =====================

class ExpeditionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    start_date: date
    end_date: date
    region: str = Field(..., min_length=2, max_length=255)
    objectives: str = Field(..., min_length=5)
    team_leader: str = Field(..., min_length=2, max_length=255)
    status: ExpeditionStatus = ExpeditionStatus.PLANNED


class ExpeditionCreate(ExpeditionBase):
    pass


class ExpeditionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    region: Optional[str] = Field(None, min_length=2, max_length=255)
    objectives: Optional[str] = None
    team_leader: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[ExpeditionStatus] = None


class ExpeditionResponse(ExpeditionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== REPORT SCHEMAS =====================

class ReportBase(BaseModel):
    expedition_id: int
    title: str = Field(..., min_length=2, max_length=255)
    authors: str = Field(..., min_length=2)
    abstract: str = Field(..., min_length=5)
    doi: Optional[str] = None
    license: str = "CC-BY-4.0"
    keywords: Optional[str] = None
    published: bool = False


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    expedition_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    authors: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    license: Optional[str] = None
    keywords: Optional[str] = None
    published: Optional[bool] = None


class ReportResponse(ReportBase):
    id: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== DATASET SCHEMAS =====================

class DatasetBase(BaseModel):
    expedition_id: int
    title: str = Field(..., min_length=2, max_length=255)
    variables: str
    units: str
    temporal_coverage: str
    spatial_coverage: str
    doi: Optional[str] = None
    license: str = "CC-BY-4.0"
    keywords: Optional[str] = None
    published: bool = False


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    expedition_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    variables: Optional[str] = None
    units: Optional[str] = None
    temporal_coverage: Optional[str] = None
    spatial_coverage: Optional[str] = None
    doi: Optional[str] = None
    license: Optional[str] = None
    keywords: Optional[str] = None
    published: Optional[bool] = None


class DatasetResponse(DatasetBase):
    id: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== PUBLICATION SCHEMAS =====================

class PublicationBase(BaseModel):
    expedition_id: int
    title: str = Field(..., min_length=2, max_length=255)
    authors: str = Field(..., min_length=2)
    journal: str = Field(..., min_length=2, max_length=255)
    year: int = Field(..., ge=1900, le=2100)
    doi: Optional[str] = None
    abstract: str = Field(..., min_length=5)
    link: str = Field(..., min_length=2, max_length=500)
    published: bool = False


class PublicationCreate(PublicationBase):
    pass


class PublicationUpdate(BaseModel):
    expedition_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = Field(None, ge=1900, le=2100)
    doi: Optional[str] = None
    abstract: Optional[str] = None
    link: Optional[str] = None
    published: Optional[bool] = None


class PublicationResponse(PublicationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== MEDIA SCHEMAS =====================

class MediaBase(BaseModel):
    expedition_id: int
    media_type: MediaType = MediaType.PHOTO
    caption: str = Field(..., min_length=2)
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    tags: Optional[str] = None
    license: str = "CC-BY-4.0"
    published: bool = False


class MediaCreate(MediaBase):
    pass


class MediaUpdate(BaseModel):
    expedition_id: Optional[int] = None
    media_type: Optional[MediaType] = None
    caption: Optional[str] = None
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    tags: Optional[str] = None
    license: Optional[str] = None
    published: Optional[bool] = None


class MediaResponse(MediaBase):
    id: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== ACTIVITY SCHEMAS =====================

class ActivityBase(BaseModel):
    activity_type: ActivityType = ActivityType.NEWS
    title: str = Field(..., min_length=2, max_length=255)
    date: date
    description: str = Field(..., min_length=5)
    related_expedition_ids: Optional[List[int]] = None
    published: bool = False


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    activity_type: Optional[ActivityType] = None
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    date: Optional[date] = None
    description: Optional[str] = None
    related_expedition_ids: Optional[List[int]] = None
    published: Optional[bool] = None


class ActivityResponse(ActivityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== SEARCH SCHEMAS =====================

class SearchRequest(BaseModel):
    q: Optional[str] = None
    type: Optional[str] = None  # report, dataset, publication, media, activity
    expedition_id: Optional[int] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    location: Optional[str] = None
    keywords: Optional[str] = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class SearchResult(BaseModel):
    type: str
    id: int
    title: str
    snippet: str
    link: str
    date_str: Optional[str] = None
    metadata_extra: Optional[dict] = None


class SearchResponse(BaseModel):
    total: int
    page: int
    size: int
    results: List[SearchResult]


# ===================== GENERATED CONTENT SCHEMAS =====================

class GeneratedContentBase(BaseModel):
    source_type: ContentSourceType
    source_id: int
    platform: PlatformType
    content: str
    status: ContentStatus = ContentStatus.PENDING_REVIEW


class GeneratedContentCreate(GeneratedContentBase):
    pass


class GeneratedContentUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[ContentStatus] = None


class GeneratedContentResponse(GeneratedContentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
