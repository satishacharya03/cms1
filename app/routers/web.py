import math
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, extract

from app.config import settings
from app.database import get_db
from app.models import (
    User,
    UserRole,
    Expedition,
    ExpeditionStatus,
    Report,
    Dataset,
    Publication,
    Media,
    MediaType,
    Activity,
    ActivityType,
    GeneratedContent,
    ContentSourceType,
    PlatformType,
    ContentStatus,
)
from app.auth import authenticate_user, hash_password, create_access_token
from app.dependencies import get_current_user_optional
from app.tasks.content_generation_job import run_content_generation

router = APIRouter(tags=["Web Pages"])
templates = Jinja2Templates(directory="app/templates")

_orig_template_response = templates.TemplateResponse

def _compat_template_response(name_or_request, *args, **kwargs):
    if isinstance(name_or_request, str):
        name = name_or_request
        ctx = args[0] if args else kwargs.get("context", {})
        req = kwargs.get("request") or (ctx.get("request") if isinstance(ctx, dict) else None)
        status_code = kwargs.get("status_code", 200)
        return _orig_template_response(request=req, name=name, context=ctx, status_code=status_code)
    return _orig_template_response(name_or_request, *args, **kwargs)

templates.TemplateResponse = _compat_template_response


class SearchItem(dict):
    """Dual-access dictionary for Jinja2 templates (supports item.key and item['key'])."""
    def __init__(self, type: str, id: int, title: str, snippet: str, link: str, date_str: str, metadata_extra: Optional[Dict[str, Any]] = None):
        data = {
            "type": type,
            "id": id,
            "title": title,
            "snippet": snippet,
            "link": link,
            "date_str": date_str,
            "metadata_extra": metadata_extra or {},
        }
        super().__init__(data)
        self.__dict__.update(data)


def build_context(
    request: Request,
    current_user: Optional[User] = None,
    msg: Optional[str] = None,
    error: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Helper to assemble base template context with auth and message support."""
    # Query parameters fallback for messages/alerts
    effective_msg = msg if msg is not None else request.query_params.get("msg")
    effective_error = error if error is not None else request.query_params.get("error")

    ctx = {
        "request": request,
        "current_user": current_user,
        "portal_title": settings.PORTAL_TITLE,
        "project_name": settings.PROJECT_NAME,
        "institution": settings.INSTITUTION,
        "department": settings.DEPARTMENT,
        "msg": effective_msg,
        "error": effective_error,
    }
    ctx.update(kwargs)
    return ctx


# ==============================================================================
# 1. PUBLIC WEB ROUTES
# ==============================================================================

@router.get("/", response_class=HTMLResponse)
def home_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Home landing page with featured expeditions, latest datasets, and recent activities."""
    featured_expeditions = (
        db.query(Expedition)
        .order_by(Expedition.start_date.desc())
        .limit(6)
        .all()
    )

    latest_datasets = (
        db.query(Dataset)
        .filter(Dataset.published == True)
        .order_by(Dataset.created_at.desc())
        .limit(6)
        .all()
    )

    latest_activities = (
        db.query(Activity)
        .filter(Activity.published == True)
        .order_by(Activity.date.desc(), Activity.created_at.desc())
        .limit(5)
        .all()
    )

    metrics = {
        "expeditions_count": db.query(Expedition).count(),
        "datasets_count": db.query(Dataset).filter(Dataset.published == True).count(),
        "reports_count": db.query(Report).filter(Report.published == True).count(),
        "publications_count": db.query(Publication).filter(Publication.published == True).count(),
        "media_count": db.query(Media).filter(Media.published == True).count(),
    }

    ctx = build_context(
        request,
        current_user,
        expeditions=featured_expeditions,
        featured_expeditions=featured_expeditions,
        datasets=latest_datasets,
        latest_datasets=latest_datasets,
        activities=latest_activities,
        latest_activities=latest_activities,
        metrics=metrics,
    )
    return templates.TemplateResponse("home.html", ctx)


@router.get("/expeditions", response_class=HTMLResponse)
def expeditions_list(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Expeditions listing with status and region filters."""
    query = db.query(Expedition)
    if status_filter:
        query = query.filter(Expedition.status == status_filter)
    if region:
        query = query.filter(Expedition.region.ilike(f"%{region}%"))

    expeditions = query.order_by(Expedition.start_date.desc()).all()

    # Collect distinct regions for filter dropdown
    distinct_regions = [
        r[0] for r in db.query(Expedition.region).distinct().all() if r[0]
    ]

    ctx = build_context(
        request,
        current_user,
        expeditions=expeditions,
        selected_status=status_filter,
        selected_region=region,
        distinct_regions=distinct_regions,
        statuses=[s.value for s in ExpeditionStatus],
    )
    return templates.TemplateResponse("expeditions_list.html", ctx)


@router.get("/expeditions/{expedition_id}", response_class=HTMLResponse)
def expedition_detail(
    expedition_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Expedition detail page showing tabs for its reports, datasets, publications, and media."""
    expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedition not found.")

    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    reports_query = db.query(Report).filter(Report.expedition_id == expedition_id)
    datasets_query = db.query(Dataset).filter(Dataset.expedition_id == expedition_id)
    publications_query = db.query(Publication).filter(Publication.expedition_id == expedition_id)
    media_query = db.query(Media).filter(Media.expedition_id == expedition_id)

    if not is_staff:
        reports_query = reports_query.filter(Report.published == True)
        datasets_query = datasets_query.filter(Dataset.published == True)
        publications_query = publications_query.filter(Publication.published == True)
        media_query = media_query.filter(Media.published == True)

    reports = reports_query.order_by(Report.created_at.desc()).all()
    datasets = datasets_query.order_by(Dataset.created_at.desc()).all()
    publications = publications_query.order_by(Publication.year.desc(), Publication.created_at.desc()).all()
    media_items = media_query.order_by(Media.created_at.desc()).all()

    ctx = build_context(
        request,
        current_user,
        expedition=expedition,
        reports=reports,
        datasets=datasets,
        publications=publications,
        media=media_items,
        media_items=media_items,
    )
    return templates.TemplateResponse("expeditions_detail.html", ctx)


@router.get("/datasets", response_class=HTMLResponse)
def datasets_list(
    request: Request,
    q: Optional[str] = None,
    expedition_id: Optional[int] = None,
    year: Optional[int] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Scientific data catalog list with search and filters."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    query = db.query(Dataset)
    if not is_staff:
        query = query.filter(Dataset.published == True)

    if expedition_id:
        query = query.filter(Dataset.expedition_id == expedition_id)
    if year:
        query = query.filter(extract("year", Dataset.created_at) == year)
    if keywords:
        query = query.filter(Dataset.keywords.ilike(f"%{keywords}%"))
    if q:
        query = query.filter(
            or_(
                Dataset.title.ilike(f"%{q}%"),
                Dataset.variables.ilike(f"%{q}%"),
                Dataset.spatial_coverage.ilike(f"%{q}%"),
                Dataset.keywords.ilike(f"%{q}%"),
            )
        )

    datasets = query.order_by(Dataset.created_at.desc()).all()
    expeditions = db.query(Expedition).order_by(Expedition.name.asc()).all()

    ctx = build_context(
        request,
        current_user,
        datasets=datasets,
        expeditions=expeditions,
        q=q,
        selected_expedition_id=expedition_id,
        selected_year=year,
        keywords=keywords,
    )
    return templates.TemplateResponse("datasets_list.html", ctx)


@router.get("/datasets/{dataset_id}", response_class=HTMLResponse)
def dataset_detail(
    dataset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Dataset detail with variable breakdown and download link."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]
    if not dataset.published and not is_staff:
        raise HTTPException(status_code=404, detail="Dataset not found or access restricted.")

    # Breakdown variables and units into structured pairs
    variables_raw = [v.strip() for v in (dataset.variables or "").split(",") if v.strip()]
    units_raw = [u.strip() for u in (dataset.units or "").split(",") if u.strip()]
    breakdown = []
    for idx, var in enumerate(variables_raw):
        unit = units_raw[idx] if idx < len(units_raw) else "dimensionless"
        breakdown.append({"variable": var, "unit": unit})

    ctx = build_context(
        request,
        current_user,
        dataset=dataset,
        variable_breakdown=breakdown,
        variables_breakdown=breakdown,
    )
    return templates.TemplateResponse("datasets_detail.html", ctx)


@router.get("/reports", response_class=HTMLResponse)
def reports_list(
    request: Request,
    expedition_id: Optional[int] = None,
    year: Optional[int] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Technical and field reports list with filtering."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    query = db.query(Report)
    if not is_staff:
        query = query.filter(Report.published == True)

    if expedition_id:
        query = query.filter(Report.expedition_id == expedition_id)
    if year:
        query = query.filter(extract("year", Report.created_at) == year)
    if keywords:
        query = query.filter(Report.keywords.ilike(f"%{keywords}%"))

    reports = query.order_by(Report.created_at.desc()).all()
    expeditions = db.query(Expedition).order_by(Expedition.name.asc()).all()

    ctx = build_context(
        request,
        current_user,
        reports=reports,
        expeditions=expeditions,
        selected_expedition_id=expedition_id,
        selected_year=year,
        keywords=keywords,
    )
    return templates.TemplateResponse("reports_list.html", ctx)


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def report_detail(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Report detail view with metadata and direct document download."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]
    if not report.published and not is_staff:
        raise HTTPException(status_code=404, detail="Report not found or access restricted.")

    ctx = build_context(
        request,
        current_user,
        report=report,
    )
    return templates.TemplateResponse("reports_detail.html", ctx)


@router.get("/publications", response_class=HTMLResponse)
def publications_list(
    request: Request,
    expedition_id: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Peer-reviewed bibliography list with DOI and outbound links."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    query = db.query(Publication)
    if not is_staff:
        query = query.filter(Publication.published == True)

    if expedition_id:
        query = query.filter(Publication.expedition_id == expedition_id)
    if year:
        query = query.filter(Publication.year == year)

    publications = query.order_by(Publication.year.desc(), Publication.created_at.desc()).all()
    expeditions = db.query(Expedition).order_by(Expedition.name.asc()).all()
    years = [y[0] for y in db.query(Publication.year).distinct().order_by(Publication.year.desc()).all() if y[0]]

    ctx = build_context(
        request,
        current_user,
        publications=publications,
        expeditions=expeditions,
        years=years,
        selected_expedition_id=expedition_id,
        selected_year=year,
    )
    return templates.TemplateResponse("publications_list.html", ctx)


@router.get("/publications/{publication_id}", response_class=HTMLResponse)
def publication_detail(
    publication_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Publication detail page."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found.")

    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]
    if not publication.published and not is_staff:
        raise HTTPException(status_code=404, detail="Publication not found or access restricted.")

    ctx = build_context(
        request,
        current_user,
        publication=publication,
    )
    return templates.TemplateResponse("publications_detail.html", ctx)


@router.get("/media", response_class=HTMLResponse)
def media_gallery(
    request: Request,
    media_type: Optional[str] = Query(None, alias="type"),
    tags: Optional[str] = None,
    expedition_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Media gallery grid with filter by type (photo/video), tags, and expedition."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    query = db.query(Media)
    if not is_staff:
        query = query.filter(Media.published == True)

    if media_type:
        query = query.filter(Media.media_type == media_type)
    if tags:
        query = query.filter(Media.tags.ilike(f"%{tags}%"))
    if expedition_id:
        query = query.filter(Media.expedition_id == expedition_id)

    media_items = query.order_by(Media.created_at.desc()).all()
    expeditions = db.query(Expedition).order_by(Expedition.name.asc()).all()

    ctx = build_context(
        request,
        current_user,
        media=media_items,
        media_items=media_items,
        expeditions=expeditions,
        selected_type=media_type,
        tags=tags,
        selected_tags=tags,
        selected_expedition_id=expedition_id,
    )
    return templates.TemplateResponse("media_gallery.html", ctx)


@router.get("/activities", response_class=HTMLResponse)
def activities_list(
    request: Request,
    activity_type: Optional[str] = Query(None, alias="type"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Institutional news, events, and workshops list."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    query = db.query(Activity)
    if not is_staff:
        query = query.filter(Activity.published == True)

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)

    activities = query.order_by(Activity.date.desc(), Activity.created_at.desc()).all()

    ctx = build_context(
        request,
        current_user,
        activities=activities,
        selected_type=activity_type,
    )
    return templates.TemplateResponse("activities_list.html", ctx)


@router.get("/activities/{activity_id}", response_class=HTMLResponse)
def activity_detail(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Activity detail page with related expedition references."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found.")

    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]
    if not activity.published and not is_staff:
        raise HTTPException(status_code=404, detail="Activity not found or access restricted.")

    related_expeditions = []
    if activity.related_expedition_ids and isinstance(activity.related_expedition_ids, list):
        related_expeditions = (
            db.query(Expedition)
            .filter(Expedition.id.in_(activity.related_expedition_ids))
            .all()
        )

    ctx = build_context(
        request,
        current_user,
        activity=activity,
        related_expeditions=related_expeditions,
    )
    return templates.TemplateResponse("activities_detail.html", ctx)


@router.get("/about", response_class=HTMLResponse)
def about_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """About page with Chandigarh CSE institution information, portal mission, and contact."""
    ctx = build_context(
        request,
        current_user,
        institution=settings.INSTITUTION,
        department=settings.DEPARTMENT,
        llm_model=settings.LLM_MODEL,
    )
    return templates.TemplateResponse("about.html", ctx)


@router.get("/search", response_class=HTMLResponse)
def unified_search(
    request: Request,
    q: Optional[str] = None,
    search_type: Optional[str] = Query(None, alias="type"),
    expedition_id: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Unified search across Expeditions, Reports, Datasets, Publications, Media, and Activities."""
    is_staff = current_user and current_user.role in [
        UserRole.ADMIN.value,
        UserRole.DATA_MANAGER.value,
        UserRole.RESEARCHER.value,
    ]

    results: List[SearchItem] = []
    q_clean = q.strip() if q else ""
    target_type = search_type.lower() if search_type else "all"

    # 1. Search Expeditions
    if target_type in ["all", "expedition", "expeditions"]:
        exp_q = db.query(Expedition)
        if q_clean:
            exp_q = exp_q.filter(
                or_(
                    Expedition.name.ilike(f"%{q_clean}%"),
                    Expedition.objectives.ilike(f"%{q_clean}%"),
                    Expedition.region.ilike(f"%{q_clean}%"),
                    Expedition.team_leader.ilike(f"%{q_clean}%"),
                )
            )
        if location:
            exp_q = exp_q.filter(Expedition.region.ilike(f"%{location}%"))
        if year_from:
            exp_q = exp_q.filter(extract("year", Expedition.start_date) >= year_from)
        if year_to:
            exp_q = exp_q.filter(extract("year", Expedition.start_date) <= year_to)

        for exp in exp_q.order_by(Expedition.start_date.desc()).limit(30).all():
            snippet = (exp.objectives[:180] + "...") if len(exp.objectives) > 180 else exp.objectives
            results.append(
                SearchItem(
                    type="Expedition",
                    id=exp.id,
                    title=exp.name,
                    snippet=snippet,
                    link=f"/expeditions/{exp.id}",
                    date_str=str(exp.start_date),
                    metadata_extra={"region": exp.region, "team_leader": exp.team_leader, "status": exp.status},
                )
            )

    # 2. Search Reports
    if target_type in ["all", "report", "reports"]:
        rep_q = db.query(Report)
        if not is_staff:
            rep_q = rep_q.filter(Report.published == True)
        if expedition_id:
            rep_q = rep_q.filter(Report.expedition_id == expedition_id)
        if q_clean:
            rep_q = rep_q.filter(
                or_(
                    Report.title.ilike(f"%{q_clean}%"),
                    Report.abstract.ilike(f"%{q_clean}%"),
                    Report.authors.ilike(f"%{q_clean}%"),
                    Report.keywords.ilike(f"%{q_clean}%"),
                )
            )
        if year_from:
            rep_q = rep_q.filter(extract("year", Report.created_at) >= year_from)
        if year_to:
            rep_q = rep_q.filter(extract("year", Report.created_at) <= year_to)

        for rep in rep_q.order_by(Report.created_at.desc()).limit(30).all():
            snippet = (rep.abstract[:180] + "...") if len(rep.abstract) > 180 else rep.abstract
            results.append(
                SearchItem(
                    type="Report",
                    id=rep.id,
                    title=rep.title,
                    snippet=snippet,
                    link=f"/reports/{rep.id}",
                    date_str=rep.created_at.strftime("%Y-%m-%d"),
                    metadata_extra={"authors": rep.authors, "doi": rep.doi, "license": rep.license},
                )
            )

    # 3. Search Datasets
    if target_type in ["all", "dataset", "datasets"]:
        data_q = db.query(Dataset)
        if not is_staff:
            data_q = data_q.filter(Dataset.published == True)
        if expedition_id:
            data_q = data_q.filter(Dataset.expedition_id == expedition_id)
        if q_clean:
            data_q = data_q.filter(
                or_(
                    Dataset.title.ilike(f"%{q_clean}%"),
                    Dataset.variables.ilike(f"%{q_clean}%"),
                    Dataset.spatial_coverage.ilike(f"%{q_clean}%"),
                    Dataset.keywords.ilike(f"%{q_clean}%"),
                )
            )
        if location:
            data_q = data_q.filter(Dataset.spatial_coverage.ilike(f"%{location}%"))
        if year_from:
            data_q = data_q.filter(extract("year", Dataset.created_at) >= year_from)
        if year_to:
            data_q = data_q.filter(extract("year", Dataset.created_at) <= year_to)

        for ds in data_q.order_by(Dataset.created_at.desc()).limit(30).all():
            snippet = f"Variables: {ds.variables} | Coverage: {ds.spatial_coverage} ({ds.temporal_coverage})"
            results.append(
                SearchItem(
                    type="Dataset",
                    id=ds.id,
                    title=ds.title,
                    snippet=snippet,
                    link=f"/datasets/{ds.id}",
                    date_str=ds.created_at.strftime("%Y-%m-%d"),
                    metadata_extra={"variables": ds.variables, "doi": ds.doi, "license": ds.license},
                )
            )

    # 4. Search Publications
    if target_type in ["all", "publication", "publications"]:
        pub_q = db.query(Publication)
        if not is_staff:
            pub_q = pub_q.filter(Publication.published == True)
        if expedition_id:
            pub_q = pub_q.filter(Publication.expedition_id == expedition_id)
        if q_clean:
            pub_q = pub_q.filter(
                or_(
                    Publication.title.ilike(f"%{q_clean}%"),
                    Publication.abstract.ilike(f"%{q_clean}%"),
                    Publication.authors.ilike(f"%{q_clean}%"),
                    Publication.journal.ilike(f"%{q_clean}%"),
                )
            )
        if year_from:
            pub_q = pub_q.filter(Publication.year >= year_from)
        if year_to:
            pub_q = pub_q.filter(Publication.year <= year_to)

        for pub in pub_q.order_by(Publication.year.desc()).limit(30).all():
            snippet = f"{pub.authors} ({pub.year}). {pub.journal}. {pub.abstract[:120]}..."
            results.append(
                SearchItem(
                    type="Publication",
                    id=pub.id,
                    title=pub.title,
                    snippet=snippet,
                    link=f"/publications/{pub.id}",
                    date_str=str(pub.year),
                    metadata_extra={"journal": pub.journal, "year": pub.year, "doi": pub.doi},
                )
            )

    # 5. Search Media
    if target_type in ["all", "media"]:
        med_q = db.query(Media)
        if not is_staff:
            med_q = med_q.filter(Media.published == True)
        if expedition_id:
            med_q = med_q.filter(Media.expedition_id == expedition_id)
        if q_clean:
            med_q = med_q.filter(
                or_(
                    Media.caption.ilike(f"%{q_clean}%"),
                    Media.tags.ilike(f"%{q_clean}%"),
                    Media.location.ilike(f"%{q_clean}%"),
                )
            )
        if location:
            med_q = med_q.filter(Media.location.ilike(f"%{location}%"))

        for m in med_q.order_by(Media.created_at.desc()).limit(30).all():
            snippet = f"{m.media_type.capitalize()} - {m.caption}"
            results.append(
                SearchItem(
                    type="Media",
                    id=m.id,
                    title=f"Media: {m.caption[:60]}",
                    snippet=snippet,
                    link=f"/media",
                    date_str=m.created_at.strftime("%Y-%m-%d"),
                    metadata_extra={"media_type": m.media_type, "location": m.location, "tags": m.tags},
                )
            )

    # 6. Search Activities
    if target_type in ["all", "activity", "activities", "news", "event", "workshop"]:
        act_q = db.query(Activity)
        if not is_staff:
            act_q = act_q.filter(Activity.published == True)
        if q_clean:
            act_q = act_q.filter(
                or_(
                    Activity.title.ilike(f"%{q_clean}%"),
                    Activity.description.ilike(f"%{q_clean}%"),
                )
            )
        if year_from:
            act_q = act_q.filter(extract("year", Activity.date) >= year_from)
        if year_to:
            act_q = act_q.filter(extract("year", Activity.date) <= year_to)

        for act in act_q.order_by(Activity.date.desc()).limit(30).all():
            snippet = (act.description[:180] + "...") if len(act.description) > 180 else act.description
            results.append(
                SearchItem(
                    type="Activity",
                    id=act.id,
                    title=act.title,
                    snippet=snippet,
                    link=f"/activities/{act.id}",
                    date_str=str(act.date),
                    metadata_extra={"activity_type": act.activity_type},
                )
            )

    expeditions = db.query(Expedition).order_by(Expedition.name.asc()).all()

    ctx = build_context(
        request,
        current_user,
        q=q_clean,
        results=results,
        total_count=len(results),
        total=len(results),
        selected_type=search_type,
        expeditions=expeditions,
        selected_expedition_id=expedition_id,
        year_from=year_from,
        year_to=year_to,
        location=location,
    )
    return templates.TemplateResponse("search.html", ctx)


# ==============================================================================
# 2. AUTHENTICATION (WEB FORMS & SESSIONS)
# ==============================================================================

@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    next_url: Optional[str] = Query(None, alias="next"),
    msg: Optional[str] = None,
    error: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Renders user login form."""
    if current_user:
        target = "/admin/dashboard" if current_user.role in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value] else "/"
        return RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)

    ctx = build_context(request, current_user, next=next_url, msg=msg, error=error)
    return templates.TemplateResponse("login.html", ctx)


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None, alias="next"),
    db: Session = Depends(get_db),
):
    """Process user login form, authenticate credentials, and set JWT cookie."""
    user = authenticate_user(db, email.strip().lower(), password)
    if not user:
        redirect_target = f"/login?error=Invalid+email+or+password."
        if next_url:
            redirect_target += f"&next={next_url}"
        return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)

    token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})

    # Determine safe redirect destination
    target = "/"
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        target = next_url
    elif user.role in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value]:
        target = "/admin/dashboard"

    response = RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_form(
    request: Request,
    msg: Optional[str] = None,
    error: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Renders user registration form."""
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    ctx = build_context(request, current_user, msg=msg, error=error)
    return templates.TemplateResponse("register.html", ctx)


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: Optional[str] = Form("public"),
    db: Session = Depends(get_db),
):
    """Process user registration, hashing password and redirecting to login."""
    clean_email = email.strip().lower()
    if len(password) < 6:
        return RedirectResponse(
            url="/register?error=Password+must+be+at+least+6+characters.",
            status_code=status.HTTP_302_FOUND,
        )

    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        return RedirectResponse(
            url="/register?error=An+account+with+this+email+already+exists.",
            status_code=status.HTTP_302_FOUND,
        )

    # First user automatically promoted to admin
    is_first_user = db.query(User).count() == 0
    assigned_role = UserRole.ADMIN.value if is_first_user else (role if role in [r.value for r in UserRole] else UserRole.PUBLIC.value)

    new_user = User(
        email=clean_email,
        hashed_password=hash_password(password),
        role=assigned_role,
    )
    db.add(new_user)
    db.commit()

    return RedirectResponse(
        url="/login?msg=Account+registered+successfully.+Please+sign+in.",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/logout")
def logout():
    """Clear access_token cookie and redirect to home."""
    response = RedirectResponse(url="/?msg=You+have+been+successfully+logged+out.", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


# ==============================================================================
# 3. ADMIN MANAGEMENT & OUTREACH WORKFLOW
# ==============================================================================

def verify_admin_access(current_user: Optional[User]) -> None:
    """Ensure user is logged in with administrative privileges."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative login required.",
        )
    if current_user.role not in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )


@router.get("/admin", response_class=HTMLResponse)
def admin_redirect():
    """Redirects /admin to /admin/dashboard."""
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)


@router.get("/admin/expeditions/new", response_class=HTMLResponse)
def admin_expeditions_new_redirect():
    """Redirects legacy /admin/expeditions/new to expeditions list UI."""
    return RedirectResponse(url="/expeditions", status_code=status.HTTP_302_FOUND)


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Admin dashboard featuring system counts, metrics, and pending content review queue."""
    if not current_user or current_user.role not in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value]:
        return RedirectResponse(url="/login?error=Admin+access+required.&next=/admin/dashboard", status_code=status.HTTP_302_FOUND)

    metrics = {
        "users_count": db.query(User).count(),
        "expeditions_count": db.query(Expedition).count(),
        "reports_count": db.query(Report).count(),
        "datasets_count": db.query(Dataset).count(),
        "publications_count": db.query(Publication).count(),
        "media_count": db.query(Media).count(),
        "activities_count": db.query(Activity).count(),
        "pending_drafts_count": db.query(GeneratedContent).filter(GeneratedContent.status == ContentStatus.PENDING_REVIEW.value).count(),
        "approved_drafts_count": db.query(GeneratedContent).filter(GeneratedContent.status == ContentStatus.APPROVED.value).count(),
        "rejected_drafts_count": db.query(GeneratedContent).filter(GeneratedContent.status == ContentStatus.REJECTED.value).count(),
    }

    recent_reports = db.query(Report).order_by(Report.created_at.desc()).limit(5).all()
    recent_datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(5).all()
    pending_content = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.status == ContentStatus.PENDING_REVIEW.value)
        .order_by(GeneratedContent.created_at.desc())
        .limit(10)
        .all()
    )

    ctx = build_context(
        request,
        current_user,
        metrics=metrics,
        recent_reports=recent_reports,
        recent_datasets=recent_datasets,
        pending_content=pending_content,
    )
    return templates.TemplateResponse("admin/dashboard.html", ctx)


@router.get("/admin/generated-content", response_class=HTMLResponse)
def admin_generated_content_list(
    request: Request,
    source_type: Optional[str] = None,
    platform: Optional[str] = None,
    content_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Admin outreach review queue with platform, source, and status filters."""
    if not current_user or current_user.role not in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value]:
        return RedirectResponse(url="/login?error=Admin+access+required.&next=/admin/generated-content", status_code=status.HTTP_302_FOUND)

    query = db.query(GeneratedContent)
    if source_type:
        query = query.filter(GeneratedContent.source_type == source_type)
    if platform:
        query = query.filter(GeneratedContent.platform == platform)
    if content_status:
        query = query.filter(GeneratedContent.status == content_status)

    total = query.count()
    total_pages = max(1, math.ceil(total / size))
    offset = (page - 1) * size

    items = query.order_by(GeneratedContent.created_at.desc()).offset(offset).limit(size).all()

    ctx = build_context(
        request,
        current_user,
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
        selected_source_type=source_type,
        selected_platform=platform,
        selected_status=content_status,
        source_types=[s.value for s in ContentSourceType],
        platforms=[p.value for p in PlatformType],
        statuses=[c.value for c in ContentStatus],
    )
    return templates.TemplateResponse("admin/generated_content_list.html", ctx)


@router.get("/admin/generated-content/{content_id}", response_class=HTMLResponse)
def admin_generated_content_detail(
    content_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Detail review page for an AI-generated outreach draft with approve, reject, and edit forms."""
    if not current_user or current_user.role not in [UserRole.ADMIN.value, UserRole.DATA_MANAGER.value]:
        return RedirectResponse(
            url=f"/login?error=Admin+access+required.&next=/admin/generated-content/{content_id}",
            status_code=status.HTTP_302_FOUND,
        )

    item = db.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Generated content draft not found.")

    source_entity = None
    if item.source_type == ContentSourceType.REPORT.value:
        source_entity = db.query(Report).filter(Report.id == item.source_id).first()
    elif item.source_type == ContentSourceType.DATASET.value:
        source_entity = db.query(Dataset).filter(Dataset.id == item.source_id).first()
    elif item.source_type == ContentSourceType.ACTIVITY.value:
        source_entity = db.query(Activity).filter(Activity.id == item.source_id).first()

    ctx = build_context(
        request,
        current_user,
        item=item,
        source_entity=source_entity,
    )
    return templates.TemplateResponse("admin/generated_content_detail.html", ctx)


@router.post("/admin/generated-content/{content_id}/approve")
def admin_approve_content(
    content_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Approve a draft. If platform is web_summary, automatically creates an Activity of type news."""
    verify_admin_access(current_user)

    item = db.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Generated content draft not found.")

    item.status = ContentStatus.APPROVED.value
    item.updated_at = datetime.now(timezone.utc)

    # Auto-publish news activity if approved content is a web summary
    if item.platform == PlatformType.WEB_SUMMARY.value:
        title_prefix = "Scientific Outreach"
        expedition_id = None

        if item.source_type == ContentSourceType.REPORT.value:
            report = db.query(Report).filter(Report.id == item.source_id).first()
            if report:
                title_prefix = report.title
                expedition_id = report.expedition_id
        elif item.source_type == ContentSourceType.DATASET.value:
            dataset = db.query(Dataset).filter(Dataset.id == item.source_id).first()
            if dataset:
                title_prefix = dataset.title
                expedition_id = dataset.expedition_id
        elif item.source_type == ContentSourceType.ACTIVITY.value:
            activity = db.query(Activity).filter(Activity.id == item.source_id).first()
            if activity:
                title_prefix = activity.title

        news_activity = Activity(
            activity_type=ActivityType.NEWS.value,
            title=f"Outreach: {title_prefix[:200]}",
            date=date.today(),
            description=item.content,
            related_expedition_ids=[expedition_id] if expedition_id else None,
            published=True,
        )
        db.add(news_activity)

    db.commit()

    return RedirectResponse(
        url=f"/admin/generated-content/{content_id}?msg=Outreach+content+approved+successfully.",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/admin/generated-content/{content_id}/reject")
def admin_reject_content(
    content_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Reject an outreach draft."""
    verify_admin_access(current_user)

    item = db.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Generated content draft not found.")

    item.status = ContentStatus.REJECTED.value
    item.updated_at = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(
        url=f"/admin/generated-content/{content_id}?msg=Outreach+content+rejected.",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/admin/generated-content/{content_id}/update")
def admin_update_content(
    content_id: int,
    request: Request,
    content: str = Form(...),
    content_status: Optional[str] = Form(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Update editable content text and/or review status for a draft."""
    verify_admin_access(current_user)

    item = db.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Generated content draft not found.")

    item.content = content.strip()
    if content_status and content_status in [s.value for s in ContentStatus]:
        item.status = content_status
    item.updated_at = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(
        url=f"/admin/generated-content/{content_id}?msg=Outreach+content+updated+successfully.",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/admin/trigger-content-generation")
def admin_trigger_content_generation(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Trigger background AI content generation job manually and redirect with flash message."""
    verify_admin_access(current_user)

    try:
        run_content_generation(db)
        return RedirectResponse(
            url="/admin/generated-content?msg=Automated+outreach+content+generation+scan+executed+successfully.",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/admin/generated-content?error=Error+triggering+generation:+{str(exc)}",
            status_code=status.HTTP_302_FOUND,
        )
