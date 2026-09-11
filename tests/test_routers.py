"""
Comprehensive integration tests for activities, search, and generated_content routers.
"""
from datetime import date, datetime, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (
    User,
    UserRole,
    Expedition,
    Report,
    Dataset,
    Publication,
    Media,
    Activity,
    ActivityType,
    GeneratedContent,
    ContentSourceType,
    PlatformType,
    ContentStatus,
)
from app.auth import hash_password, create_access_token
from app.routers import (
    activities,
    search,
    generated_content,
    expeditions,
    reports,
    datasets,
    publications,
    media,
    auth,
)

# In-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth.router)
app.include_router(activities.router)
app.include_router(search.router)
app.include_router(generated_content.router)
app.include_router(expeditions.router)
app.include_router(reports.router)
app.include_router(datasets.router)
app.include_router(publications.router)
app.include_router(media.router)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    db = TestingSessionLocal()

    # Create test users
    admin_user = User(
        email="admin@test.org",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN.value,
    )
    dm_user = User(
        email="dm@test.org",
        hashed_password=hash_password("dmpass123"),
        role=UserRole.DATA_MANAGER.value,
    )
    res_user = User(
        email="researcher@test.org",
        hashed_password=hash_password("respass123"),
        role=UserRole.RESEARCHER.value,
    )
    pub_user = User(
        email="public@test.org",
        hashed_password=hash_password("publicpass123"),
        role=UserRole.PUBLIC.value,
    )
    db.add_all([admin_user, dm_user, res_user, pub_user])
    db.commit()

    # Create test expedition
    expedition = Expedition(
        name="Arctic Permafrost 2026",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        region="Svalbard",
        objectives="Monitor deep soil temperature and methane thaw emissions.",
        team_leader="Dr. Elena Rostova",
        status="ongoing",
    )
    db.add(expedition)
    db.commit()
    db.refresh(expedition)

    # Create test report
    rep_pub = Report(
        expedition_id=expedition.id,
        title="Methane Flux Measurements in Svalbard Tundra",
        authors="Rostova, E.; Hansen, P.",
        abstract="High-precision flux chamber measurements indicate elevated methane thaw signatures.",
        file_path="reports/sample.pdf",
        doi="10.1000/182",
        keywords="methane, permafrost, tundra, climate",
        published=True,
    )
    rep_unpub = Report(
        expedition_id=expedition.id,
        title="Draft Confidential Analysis",
        authors="Rostova, E.",
        abstract="Preliminary unverified field sensor readings.",
        file_path="reports/draft.pdf",
        keywords="confidential, draft",
        published=False,
    )
    db.add_all([rep_pub, rep_unpub])
    db.flush()

    # Create test dataset
    ds_pub = Dataset(
        expedition_id=expedition.id,
        title="Svalbard Soil Thermistor Array Timeseries",
        variables="temperature, moisture",
        units="Celsius, percent",
        temporal_coverage="2026-06-01 to 2026-08-31",
        spatial_coverage="Svalbard 78N",
        file_path="datasets/soil.csv",
        doi="10.1000/183",
        keywords="temperature, moisture, soil",
        published=True,
    )
    ds_unpub = Dataset(
        expedition_id=expedition.id,
        title="Unpublished Raw Log Dataset",
        variables="raw_voltages",
        units="mV",
        temporal_coverage="2026-06-01",
        spatial_coverage="Svalbard",
        file_path="datasets/raw.csv",
        published=False,
    )
    db.add_all([ds_pub, ds_unpub])
    db.flush()

    # Create test publication
    pub = Publication(
        expedition_id=expedition.id,
        title="Permafrost Dynamics in a Warming Arctic",
        authors="Rostova et al.",
        journal="Polar Research Journal",
        year=2026,
        doi="10.1000/184",
        abstract="Long-term temperature loggers demonstrate accelerated active-layer deepening.",
        link="https://doi.org/10.1000/184",
        published=True,
    )
    db.add(pub)

    # Create test media
    med = Media(
        expedition_id=expedition.id,
        media_type="photo",
        caption="Deploying eddy covariance flux tower over tundra",
        location="Svalbard",
        file_path="media/tower.jpg",
        tags="tower, flux, permafrost",
        published=True,
    )
    db.add(med)

    # Create test activity
    act = Activity(
        activity_type=ActivityType.EVENT.value,
        title="Arctic Science Summit 2026",
        date=date(2026, 9, 15),
        description="Public dissemination conference on Svalbard climate findings.",
        related_expedition_ids=[expedition.id],
        published=True,
    )
    db.add(act)

    # Create test generated content
    gc = GeneratedContent(
        source_type=ContentSourceType.REPORT.value,
        source_id=rep_pub.id,
        platform=PlatformType.WEB_SUMMARY.value,
        content="Groundbreaking study reveals elevated methane emissions in warming Arctic tundra.",
        status=ContentStatus.PENDING_REVIEW.value,
    )
    gc_tweet = GeneratedContent(
        source_type=ContentSourceType.REPORT.value,
        source_id=rep_pub.id,
        platform=PlatformType.TWEET.value,
        content="New findings on Arctic methane released! Check out the latest findings.",
        status=ContentStatus.PENDING_REVIEW.value,
    )
    db.add_all([gc, gc_tweet])

    db.commit()
    db.close()


def auth_header(role: str) -> dict:
    emails = {
        "admin": "admin@test.org",
        "data_manager": "dm@test.org",
        "researcher": "researcher@test.org",
        "public": "public@test.org",
    }
    email = emails[role]
    token = create_access_token({"sub": email, "role": role})
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# ACTIVITIES ROUTER TESTS
# =========================================================================

def test_list_activities():
    res = client.get("/api/activities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Arctic Science Summit 2026"


def test_list_activities_filter():
    res = client.get("/api/activities?activity_type=event&published=true")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["activity_type"] == "event"

    res_empty = client.get("/api/activities?activity_type=workshop")
    assert res_empty.status_code == 200
    assert len(res_empty.json()) == 0


def test_get_activity():
    res = client.get("/api/activities/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1

    res_not_found = client.get("/api/activities/9999")
    assert res_not_found.status_code == 404


def test_create_activity_permissions():
    payload = {
        "activity_type": "workshop",
        "title": "Field Sensor Calibration Workshop",
        "date": "2026-10-01",
        "description": "Hands-on calibration training for Arctic soil instrumentation.",
        "related_expedition_ids": [1],
        "published": False,
    }

    # Unauthenticated should fail (401)
    res_no_auth = client.post("/api/activities", json=payload)
    assert res_no_auth.status_code == 401

    # Public role should fail (403)
    res_pub = client.post("/api/activities", json=payload, headers=auth_header("public"))
    assert res_pub.status_code == 403

    # Researcher role should succeed (201)
    res_res = client.post("/api/activities", json=payload, headers=auth_header("researcher"))
    assert res_res.status_code == 201
    created_id = res_res.json()["id"]
    assert res_res.json()["title"] == payload["title"]

    # Test update (PUT)
    update_payload = {"title": "Updated Sensor Calibration Workshop"}
    res_put = client.put(f"/api/activities/{created_id}", json=update_payload, headers=auth_header("data_manager"))
    assert res_put.status_code == 200
    assert res_put.json()["title"] == "Updated Sensor Calibration Workshop"

    # Test publish
    res_pub_post = client.post(f"/api/activities/{created_id}/publish", headers=auth_header("admin"))
    assert res_pub_post.status_code == 200
    assert res_pub_post.json()["published"] is True

    # Test delete
    res_del = client.delete(f"/api/activities/{created_id}", headers=auth_header("admin"))
    assert res_del.status_code == 204

    # Verify deleted
    res_check = client.get(f"/api/activities/{created_id}")
    assert res_check.status_code == 404


# =========================================================================
# SEARCH ROUTER TESTS
# =========================================================================

def test_unified_search_all():
    res = client.get("/api/search")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "results" in data
    assert data["total"] > 0


def test_unified_search_query_keyword():
    res = client.get("/api/search?q=methane")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    types = [r["type"] for r in data["results"]]
    assert "report" in types


def test_unified_search_type_filter():
    res = client.get("/api/search?type=report")
    assert res.status_code == 200
    data = res.json()
    for item in data["results"]:
        assert item["type"] == "report"

    res_exp = client.get("/api/search?type=expedition")
    assert res_exp.status_code == 200
    for item in res_exp.json()["results"]:
        assert item["type"] == "expedition"


def test_unified_search_public_vs_admin_visibility():
    # Public user: should NOT see unpublished reports or datasets
    res_public = client.get("/api/search?q=confidential")
    assert res_public.status_code == 200
    assert res_public.json()["total"] == 0

    # Admin user: SHOULD see unpublished records
    res_admin = client.get("/api/search?q=confidential", headers=auth_header("admin"))
    assert res_admin.status_code == 200
    assert res_admin.json()["total"] >= 1
    assert any("Confidential" in r["title"] for r in res_admin.json()["results"])


def test_unified_search_expedition_and_year_filters():
    res = client.get("/api/search?expedition_id=1&year_from=2025&year_to=2027")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


def test_unified_search_pagination():
    res_p1 = client.get("/api/search?size=2&page=1")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["results"]) <= 2
    assert data_p1["page"] == 1
    assert data_p1["size"] == 2


# =========================================================================
# GENERATED CONTENT ROUTER TESTS
# =========================================================================

def test_list_generated_content_permissions():
    # Unauthenticated -> 401
    res = client.get("/api/admin/generated-content")
    assert res.status_code == 401

    # Researcher -> 403 (only admin & data_manager allowed)
    res_res = client.get("/api/admin/generated-content", headers=auth_header("researcher"))
    assert res_res.status_code == 403

    # Admin -> 200
    res_admin = client.get("/api/admin/generated-content", headers=auth_header("admin"))
    assert res_admin.status_code == 200
    items = res_admin.json()
    assert isinstance(items, list)
    assert len(items) >= 2


def test_list_generated_content_filter():
    res = client.get(
        "/api/admin/generated-content?platform=web_summary&status=pending_review",
        headers=auth_header("data_manager"),
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["platform"] == "web_summary"


def test_get_and_update_generated_content():
    # Get ID 1
    res = client.get("/api/admin/generated-content/1", headers=auth_header("admin"))
    assert res.status_code == 200
    assert res.json()["id"] == 1

    # Update content
    new_text = "Updated outreach text for web summary."
    res_put = client.put(
        "/api/admin/generated-content/1",
        json={"content": new_text},
        headers=auth_header("admin"),
    )
    assert res_put.status_code == 200
    assert res_put.json()["content"] == new_text


def test_approve_web_summary_creates_activity():
    # Approve web_summary (ID 1)
    res_app = client.post("/api/admin/generated-content/1/approve", headers=auth_header("admin"))
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    # Verify Activity of type news was automatically created
    res_act = client.get("/api/activities?activity_type=news")
    assert res_act.status_code == 200
    news_items = res_act.json()
    assert len(news_items) >= 1
    assert any("Methane" in n["title"] for n in news_items)


def test_reject_generated_content():
    # Reject tweet (ID 2)
    res_rej = client.post("/api/admin/generated-content/2/reject", headers=auth_header("admin"))
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"


def test_trigger_content_generation():
    res = client.post("/api/admin/generated-content/trigger", headers=auth_header("admin"))
    assert res.status_code == 200
    assert res.json()["status"] == "success"
