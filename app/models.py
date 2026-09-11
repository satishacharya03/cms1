import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DATA_MANAGER = "data_manager"
    RESEARCHER = "researcher"
    PUBLIC = "public"


class ExpeditionStatus(str, enum.Enum):
    PLANNED = "planned"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MediaType(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"


class ActivityType(str, enum.Enum):
    NEWS = "news"
    EVENT = "event"
    WORKSHOP = "workshop"


class ContentSourceType(str, enum.Enum):
    REPORT = "report"
    DATASET = "dataset"
    ACTIVITY = "activity"


class PlatformType(str, enum.Enum):
    WEB_SUMMARY = "web_summary"
    TWEET = "tweet"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"


class ContentStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.PUBLIC.value, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class Expedition(Base):
    __tablename__ = "expeditions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    region = Column(String(255), index=True, nullable=False)
    objectives = Column(Text, nullable=False)
    team_leader = Column(String(255), nullable=False)
    status = Column(String(50), default=ExpeditionStatus.PLANNED.value, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    reports = relationship("Report", back_populates="expedition", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="expedition", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="expedition", cascade="all, delete-orphan")
    media = relationship("Media", back_populates="expedition", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    expedition_id = Column(Integer, ForeignKey("expeditions.id"), nullable=False, index=True)
    title = Column(String(255), index=True, nullable=False)
    authors = Column(Text, nullable=False)
    abstract = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=False)
    doi = Column(String(255), unique=True, nullable=True, index=True)
    license = Column(String(100), default="CC-BY-4.0", nullable=False)
    keywords = Column(Text, index=True, nullable=True)
    published = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    expedition = relationship("Expedition", back_populates="reports")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    expedition_id = Column(Integer, ForeignKey("expeditions.id"), nullable=False, index=True)
    title = Column(String(255), index=True, nullable=False)
    variables = Column(Text, nullable=False)
    units = Column(Text, nullable=False)
    temporal_coverage = Column(Text, nullable=False)
    spatial_coverage = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=False)
    doi = Column(String(255), unique=True, nullable=True, index=True)
    license = Column(String(100), default="CC-BY-4.0", nullable=False)
    keywords = Column(Text, index=True, nullable=True)
    published = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    expedition = relationship("Expedition", back_populates="datasets")


class Publication(Base):
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True)
    expedition_id = Column(Integer, ForeignKey("expeditions.id"), nullable=False, index=True)
    title = Column(String(255), index=True, nullable=False)
    authors = Column(Text, nullable=False)
    journal = Column(String(255), nullable=False)
    year = Column(Integer, index=True, nullable=False)
    doi = Column(String(255), unique=True, nullable=True, index=True)
    abstract = Column(Text, nullable=False)
    link = Column(String(500), nullable=False)
    published = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    expedition = relationship("Expedition", back_populates="publications")


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    expedition_id = Column(Integer, ForeignKey("expeditions.id"), nullable=False, index=True)
    media_type = Column(String(50), default=MediaType.PHOTO.value, nullable=False)
    caption = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    file_path = Column(String(500), nullable=False)
    tags = Column(Text, nullable=True)
    license = Column(String(100), default="CC-BY-4.0", nullable=False)
    published = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    expedition = relationship("Expedition", back_populates="media")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    activity_type = Column(String(50), default=ActivityType.NEWS.value, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    related_expedition_ids = Column(JSON, nullable=True)
    published = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), index=True, nullable=False)
    source_id = Column(Integer, index=True, nullable=False)
    platform = Column(String(50), index=True, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default=ContentStatus.PENDING_REVIEW.value, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


# Indexing for composite / fast lookups
Index("ix_generated_content_lookup", GeneratedContent.source_type, GeneratedContent.source_id, GeneratedContent.platform)
Index("ix_reports_pub_exp", Report.published, Report.expedition_id)
Index("ix_datasets_pub_exp", Dataset.published, Dataset.expedition_id)
Index("ix_publications_pub_exp", Publication.published, Publication.expedition_id)
Index("ix_media_pub_exp", Media.published, Media.expedition_id)
Index("ix_activities_pub_type", Activity.published, Activity.activity_type)
