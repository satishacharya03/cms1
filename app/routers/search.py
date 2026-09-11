"""
Unified Search Router for MATRIXCMS.
Enables cross-entity search across Expeditions, Reports, Datasets, Publications, Media, and Activities.
Respects public visibility filters (published=True) for anonymous or public users,
while granting researchers, data managers, and admins visibility across all records.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, extract

from app.database import get_db
from app.models import (
    Expedition,
    Report,
    Dataset,
    Publication,
    Media,
    Activity,
    User,
    UserRole,
)
from app.schemas import SearchResponse, SearchResult
from app.dependencies import get_current_user_optional

router = APIRouter(prefix="/api/search", tags=["Search"])


def _activity_matches_expedition(activity: Activity, target_exp_id: int) -> bool:
    """Check whether an Activity's related_expedition_ids JSON list contains target_exp_id."""
    ids = activity.related_expedition_ids
    if not ids:
        return False
    if isinstance(ids, list):
        return target_exp_id in ids
    if isinstance(ids, int):
        return ids == target_exp_id
    if isinstance(ids, str):
        try:
            parsed = json.loads(ids)
            if isinstance(parsed, list):
                return target_exp_id in parsed
        except Exception:
            return str(target_exp_id) in ids
    return False


@router.get("", response_model=SearchResponse)
def unified_search(
    q: Optional[str] = Query(
        None, description="Search query keyword matching title, abstract, or metadata"
    ),
    type: Optional[str] = Query(
        None,
        description="Filter by entity type: report, dataset, publication, media, activity, expedition",
    ),
    expedition_id: Optional[int] = Query(
        None, description="Filter records belonging to or linked with an expedition ID"
    ),
    year_from: Optional[int] = Query(
        None, description="Earliest year filter"
    ),
    year_to: Optional[int] = Query(
        None, description="Latest year filter"
    ),
    location: Optional[str] = Query(
        None, description="Geographic location or region filter"
    ),
    keywords: Optional[str] = Query(
        None, description="Optional extra keyword filter"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Unified multi-entity search endpoint.
    Searches across Expedition, Report, Dataset, Publication, Media, and Activity.
    For public requests (unauthenticated or public role), results are filtered to published items only.
    """
    is_public = current_user is None or current_user.role == UserRole.PUBLIC.value

    # Normalize type filter
    requested_type = type.lower().strip() if type else None
    if requested_type in ("all", ""):
        requested_type = None

    all_matched: List[Tuple[int, datetime, SearchResult]] = []

    clean_q = q.strip() if q and q.strip() else None
    q_pattern = f"%{clean_q}%" if clean_q else None
    loc_pattern = f"%{location.strip()}%" if location and location.strip() else None
    kw_pattern = f"%{keywords.strip()}%" if keywords and keywords.strip() else None

    # Helper scoring for relevance
    def calculate_score(title: str, snippet: str) -> int:
        if not clean_q:
            return 0
        q_lower = clean_q.lower()
        score = 0
        if q_lower in title.lower():
            score += 10
        if q_lower in snippet.lower():
            score += 2
        return score

    # 1. EXPEDITIONS
    if requested_type is None or requested_type in ("expedition", "expeditions"):
        exp_query = db.query(Expedition)
        if expedition_id is not None:
            exp_query = exp_query.filter(Expedition.id == expedition_id)
        if clean_q:
            exp_query = exp_query.filter(
                or_(
                    Expedition.name.ilike(q_pattern),
                    Expedition.objectives.ilike(q_pattern),
                    Expedition.region.ilike(q_pattern),
                    Expedition.team_leader.ilike(q_pattern),
                )
            )
        if kw_pattern:
            exp_query = exp_query.filter(
                or_(
                    Expedition.name.ilike(kw_pattern),
                    Expedition.objectives.ilike(kw_pattern),
                )
            )
        if year_from is not None:
            exp_query = exp_query.filter(extract("year", Expedition.start_date) >= year_from)
        if year_to is not None:
            exp_query = exp_query.filter(extract("year", Expedition.start_date) <= year_to)
        if loc_pattern:
            exp_query = exp_query.filter(Expedition.region.ilike(loc_pattern))

        expeditions: List[Expedition] = exp_query.all()
        for exp in expeditions:
            dt = datetime.combine(exp.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            snippet = exp.objectives[:220] + ("..." if len(exp.objectives) > 220 else "")
            res = SearchResult(
                type="expedition",
                id=exp.id,
                title=exp.name,
                snippet=snippet,
                link=f"/expeditions/{exp.id}",
                date_str=str(exp.start_date),
                metadata_extra={
                    "region": exp.region,
                    "team_leader": exp.team_leader,
                    "status": exp.status,
                    "start_date": str(exp.start_date),
                    "end_date": str(exp.end_date),
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # 2. REPORTS
    if requested_type is None or requested_type in ("report", "reports"):
        rep_query = db.query(Report)
        if is_public:
            rep_query = rep_query.filter(Report.published == True)
        if expedition_id is not None:
            rep_query = rep_query.filter(Report.expedition_id == expedition_id)
        if clean_q:
            rep_query = rep_query.filter(
                or_(
                    Report.title.ilike(q_pattern),
                    Report.abstract.ilike(q_pattern),
                    Report.authors.ilike(q_pattern),
                    Report.keywords.ilike(q_pattern),
                )
            )
        if kw_pattern:
            rep_query = rep_query.filter(Report.keywords.ilike(kw_pattern))
        if year_from is not None:
            rep_query = rep_query.filter(extract("year", Report.created_at) >= year_from)
        if year_to is not None:
            rep_query = rep_query.filter(extract("year", Report.created_at) <= year_to)
        if loc_pattern:
            rep_query = rep_query.join(Expedition, Report.expedition_id == Expedition.id).filter(
                Expedition.region.ilike(loc_pattern)
            )

        reports: List[Report] = rep_query.all()
        for rep in reports:
            dt = (
                rep.created_at.replace(tzinfo=timezone.utc)
                if rep.created_at.tzinfo is None
                else rep.created_at
            )
            snippet = rep.abstract[:220] + ("..." if len(rep.abstract) > 220 else "")
            res = SearchResult(
                type="report",
                id=rep.id,
                title=rep.title,
                snippet=snippet,
                link=f"/reports/{rep.id}",
                date_str=rep.created_at.strftime("%Y-%m-%d") if rep.created_at else None,
                metadata_extra={
                    "authors": rep.authors,
                    "doi": rep.doi,
                    "license": rep.license,
                    "expedition_id": rep.expedition_id,
                    "published": rep.published,
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # 3. DATASETS
    if requested_type is None or requested_type in ("dataset", "datasets"):
        ds_query = db.query(Dataset)
        if is_public:
            ds_query = ds_query.filter(Dataset.published == True)
        if expedition_id is not None:
            ds_query = ds_query.filter(Dataset.expedition_id == expedition_id)
        if clean_q:
            ds_query = ds_query.filter(
                or_(
                    Dataset.title.ilike(q_pattern),
                    Dataset.variables.ilike(q_pattern),
                    Dataset.spatial_coverage.ilike(q_pattern),
                    Dataset.keywords.ilike(q_pattern),
                )
            )
        if kw_pattern:
            ds_query = ds_query.filter(Dataset.keywords.ilike(kw_pattern))
        if year_from is not None:
            ds_query = ds_query.filter(extract("year", Dataset.created_at) >= year_from)
        if year_to is not None:
            ds_query = ds_query.filter(extract("year", Dataset.created_at) <= year_to)
        if loc_pattern:
            ds_query = ds_query.outerjoin(Expedition, Dataset.expedition_id == Expedition.id).filter(
                or_(
                    Dataset.spatial_coverage.ilike(loc_pattern),
                    Expedition.region.ilike(loc_pattern),
                )
            )

        datasets: List[Dataset] = ds_query.all()
        for ds in datasets:
            dt = (
                ds.created_at.replace(tzinfo=timezone.utc)
                if ds.created_at.tzinfo is None
                else ds.created_at
            )
            snippet = f"Variables: {ds.variables} | Units: {ds.units} | Spatial: {ds.spatial_coverage}"
            res = SearchResult(
                type="dataset",
                id=ds.id,
                title=ds.title,
                snippet=snippet[:220] + ("..." if len(snippet) > 220 else ""),
                link=f"/datasets/{ds.id}",
                date_str=ds.created_at.strftime("%Y-%m-%d") if ds.created_at else None,
                metadata_extra={
                    "variables": ds.variables,
                    "units": ds.units,
                    "spatial_coverage": ds.spatial_coverage,
                    "temporal_coverage": ds.temporal_coverage,
                    "doi": ds.doi,
                    "license": ds.license,
                    "expedition_id": ds.expedition_id,
                    "published": ds.published,
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # 4. PUBLICATIONS
    if requested_type is None or requested_type in ("publication", "publications"):
        pub_query = db.query(Publication)
        if is_public:
            pub_query = pub_query.filter(Publication.published == True)
        if expedition_id is not None:
            pub_query = pub_query.filter(Publication.expedition_id == expedition_id)
        if clean_q:
            pub_query = pub_query.filter(
                or_(
                    Publication.title.ilike(q_pattern),
                    Publication.abstract.ilike(q_pattern),
                    Publication.authors.ilike(q_pattern),
                    Publication.journal.ilike(q_pattern),
                )
            )
        if kw_pattern:
            pub_query = pub_query.filter(Publication.abstract.ilike(kw_pattern))
        if year_from is not None:
            pub_query = pub_query.filter(Publication.year >= year_from)
        if year_to is not None:
            pub_query = pub_query.filter(Publication.year <= year_to)
        if loc_pattern:
            pub_query = pub_query.join(Expedition, Publication.expedition_id == Expedition.id).filter(
                Expedition.region.ilike(loc_pattern)
            )

        publications: List[Publication] = pub_query.all()
        for pub in publications:
            dt = datetime(pub.year, 1, 1, tzinfo=timezone.utc)
            snippet = pub.abstract[:220] + ("..." if len(pub.abstract) > 220 else "")
            res = SearchResult(
                type="publication",
                id=pub.id,
                title=pub.title,
                snippet=snippet,
                link=pub.link or f"/publications/{pub.id}",
                date_str=str(pub.year),
                metadata_extra={
                    "authors": pub.authors,
                    "journal": pub.journal,
                    "year": pub.year,
                    "doi": pub.doi,
                    "expedition_id": pub.expedition_id,
                    "published": pub.published,
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # 5. MEDIA
    if requested_type is None or requested_type == "media":
        med_query = db.query(Media)
        if is_public:
            med_query = med_query.filter(Media.published == True)
        if expedition_id is not None:
            med_query = med_query.filter(Media.expedition_id == expedition_id)
        if clean_q:
            med_query = med_query.filter(
                or_(
                    Media.caption.ilike(q_pattern),
                    Media.tags.ilike(q_pattern),
                    Media.location.ilike(q_pattern),
                )
            )
        if kw_pattern:
            med_query = med_query.filter(Media.tags.ilike(kw_pattern))
        if year_from is not None:
            med_query = med_query.filter(extract("year", Media.created_at) >= year_from)
        if year_to is not None:
            med_query = med_query.filter(extract("year", Media.created_at) <= year_to)
        if loc_pattern:
            med_query = med_query.outerjoin(Expedition, Media.expedition_id == Expedition.id).filter(
                or_(
                    Media.location.ilike(loc_pattern),
                    Expedition.region.ilike(loc_pattern),
                )
            )

        media_items: List[Media] = med_query.all()
        for med in media_items:
            raw_dt = med.timestamp or med.created_at
            dt = (
                raw_dt.replace(tzinfo=timezone.utc)
                if raw_dt.tzinfo is None
                else raw_dt
            )
            snippet = med.caption[:220] + ("..." if len(med.caption) > 220 else "")
            res = SearchResult(
                type="media",
                id=med.id,
                title=med.caption[:80] + ("..." if len(med.caption) > 80 else ""),
                snippet=snippet,
                link=f"/media/{med.id}",
                date_str=raw_dt.strftime("%Y-%m-%d") if raw_dt else None,
                metadata_extra={
                    "media_type": med.media_type,
                    "location": med.location,
                    "tags": med.tags,
                    "file_path": med.file_path,
                    "expedition_id": med.expedition_id,
                    "published": med.published,
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # 6. ACTIVITIES
    if requested_type is None or requested_type in ("activity", "activities"):
        act_query = db.query(Activity)
        if is_public:
            act_query = act_query.filter(Activity.published == True)
        if clean_q:
            act_query = act_query.filter(
                or_(
                    Activity.title.ilike(q_pattern),
                    Activity.description.ilike(q_pattern),
                    Activity.activity_type.ilike(q_pattern),
                )
            )
        if kw_pattern:
            act_query = act_query.filter(
                or_(
                    Activity.title.ilike(kw_pattern),
                    Activity.description.ilike(kw_pattern),
                )
            )
        if year_from is not None:
            act_query = act_query.filter(extract("year", Activity.date) >= year_from)
        if year_to is not None:
            act_query = act_query.filter(extract("year", Activity.date) <= year_to)
        if loc_pattern:
            act_query = act_query.filter(
                or_(
                    Activity.description.ilike(loc_pattern),
                    Activity.title.ilike(loc_pattern),
                )
            )

        activities: List[Activity] = act_query.all()
        for act in activities:
            if expedition_id is not None and not _activity_matches_expedition(act, expedition_id):
                continue

            dt = datetime.combine(act.date, datetime.min.time()).replace(tzinfo=timezone.utc)
            snippet = act.description[:220] + ("..." if len(act.description) > 220 else "")
            res = SearchResult(
                type="activity",
                id=act.id,
                title=act.title,
                snippet=snippet,
                link=f"/activities/{act.id}",
                date_str=str(act.date),
                metadata_extra={
                    "activity_type": act.activity_type,
                    "date": str(act.date),
                    "published": act.published,
                    "related_expedition_ids": act.related_expedition_ids,
                },
            )
            all_matched.append((calculate_score(res.title, res.snippet), dt, res))

    # Sort results by relevance score (descending), then date (descending)
    all_matched.sort(key=lambda x: (x[0], x[1]), reverse=True)

    total_count = len(all_matched)
    start_index = (page - 1) * size
    end_index = start_index + size
    paginated_results = [item[2] for item in all_matched[start_index:end_index]]

    return SearchResponse(
        total=total_count,
        page=page,
        size=size,
        results=paginated_results,
    )
