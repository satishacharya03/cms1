import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    Report,
    Dataset,
    Activity,
    GeneratedContent,
    ContentSourceType,
    PlatformType,
    ContentStatus,
)
from app.services.content_generator import generate_content_for_record

logger = logging.getLogger("matrixcms.content_generation_job")
logging.basicConfig(level=logging.INFO)


def _has_generated_content(db: Session, source_type: str, source_id: int) -> bool:
    """Check if generated content records already exist for this source record."""
    count = (
        db.query(GeneratedContent)
        .filter(
            GeneratedContent.source_type == source_type,
            GeneratedContent.source_id == source_id,
        )
        .count()
    )
    return count > 0


def run_content_generation(db_session: Session = None) -> None:
    """
    Background task to find newly published reports, datasets, and activities
    that lack outreach content, and generate draft multi-platform posts via LLM.
    """
    close_session = False
    if db_session is None:
        db_session = SessionLocal()
        close_session = True

    try:
        logger.info("Starting automated outreach content generation scan...")
        total_created = 0

        # 1. Check Published Reports
        published_reports: List[Report] = (
            db_session.query(Report)
            .filter(Report.published == True)
            .all()
        )
        for report in published_reports:
            if not _has_generated_content(db_session, ContentSourceType.REPORT.value, report.id):
                exp_name = report.expedition.name if report.expedition else "Scientific Expedition"
                metadata = {
                    "title": report.title,
                    "expedition_name": exp_name,
                    "abstract": report.abstract,
                    "authors": report.authors,
                    "doi": report.doi or "",
                    "keywords": report.keywords or "",
                    "license": report.license,
                    "link": f"/reports/{report.id}",
                }
                generated = asyncio.run(
                    generate_content_for_record(ContentSourceType.REPORT.value, metadata)
                )
                if generated:
                    for platform_key in [
                        PlatformType.WEB_SUMMARY.value,
                        PlatformType.TWEET.value,
                        PlatformType.LINKEDIN.value,
                        PlatformType.INSTAGRAM.value,
                    ]:
                        if platform_key in generated:
                            gc = GeneratedContent(
                                source_type=ContentSourceType.REPORT.value,
                                source_id=report.id,
                                platform=platform_key,
                                content=generated[platform_key],
                                status=ContentStatus.PENDING_REVIEW.value,
                            )
                            db_session.add(gc)
                            total_created += 1
                    db_session.commit()
                    logger.info("Generated outreach drafts for Report ID %s: %s", report.id, report.title)

        # 2. Check Published Datasets
        published_datasets: List[Dataset] = (
            db_session.query(Dataset)
            .filter(Dataset.published == True)
            .all()
        )
        for dataset in published_datasets:
            if not _has_generated_content(db_session, ContentSourceType.DATASET.value, dataset.id):
                exp_name = dataset.expedition.name if dataset.expedition else "Scientific Expedition"
                metadata = {
                    "title": dataset.title,
                    "expedition_name": exp_name,
                    "variables": dataset.variables,
                    "units": dataset.units,
                    "temporal_coverage": dataset.temporal_coverage,
                    "spatial_coverage": dataset.spatial_coverage,
                    "doi": dataset.doi or "",
                    "keywords": dataset.keywords or "",
                    "license": dataset.license,
                    "link": f"/datasets/{dataset.id}",
                }
                generated = asyncio.run(
                    generate_content_for_record(ContentSourceType.DATASET.value, metadata)
                )
                if generated:
                    for platform_key in [
                        PlatformType.WEB_SUMMARY.value,
                        PlatformType.TWEET.value,
                        PlatformType.LINKEDIN.value,
                        PlatformType.INSTAGRAM.value,
                    ]:
                        if platform_key in generated:
                            gc = GeneratedContent(
                                source_type=ContentSourceType.DATASET.value,
                                source_id=dataset.id,
                                platform=platform_key,
                                content=generated[platform_key],
                                status=ContentStatus.PENDING_REVIEW.value,
                            )
                            db_session.add(gc)
                            total_created += 1
                    db_session.commit()
                    logger.info("Generated outreach drafts for Dataset ID %s: %s", dataset.id, dataset.title)

        # 3. Check Published Activities
        published_activities: List[Activity] = (
            db_session.query(Activity)
            .filter(Activity.published == True)
            .all()
        )
        for activity in published_activities:
            if not _has_generated_content(db_session, ContentSourceType.ACTIVITY.value, activity.id):
                metadata = {
                    "title": activity.title,
                    "activity_type": activity.activity_type,
                    "date": str(activity.date),
                    "description": activity.description,
                    "link": f"/activities/{activity.id}",
                }
                generated = asyncio.run(
                    generate_content_for_record(ContentSourceType.ACTIVITY.value, metadata)
                )
                if generated:
                    for platform_key in [
                        PlatformType.WEB_SUMMARY.value,
                        PlatformType.TWEET.value,
                        PlatformType.LINKEDIN.value,
                        PlatformType.INSTAGRAM.value,
                    ]:
                        if platform_key in generated:
                            gc = GeneratedContent(
                                source_type=ContentSourceType.ACTIVITY.value,
                                source_id=activity.id,
                                platform=platform_key,
                                content=generated[platform_key],
                                status=ContentStatus.PENDING_REVIEW.value,
                            )
                            db_session.add(gc)
                            total_created += 1
                    db_session.commit()
                    logger.info("Generated outreach drafts for Activity ID %s: %s", activity.id, activity.title)

        logger.info("Outreach content scan complete. Total generated draft records: %s", total_created)

    except Exception as exc:
        db_session.rollback()
        logger.exception("Error during outreach content generation job: %s", exc)
    finally:
        if close_session:
            db_session.close()
