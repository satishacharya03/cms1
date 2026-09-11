"""
API Integration Test Suite for MATRIXCMS.
Validates core authentication, expeditions catalog, dataset upload,
unified search, and automated outreach moderation workflows.
"""
import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import (
    User,
    UserRole,
    Expedition,
    ExpeditionStatus,
    Dataset,
    GeneratedContent,
    ContentSourceType,
    PlatformType,
    ContentStatus,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def test_admin_user(client):
    """
    Fixture ensuring an admin user exists and returning its credentials + JWT headers.
    """
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"admin_test_{unique_suffix}@chandigarh.ac.in"
    password = "SecureAdminPass123!"

    # Register user
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": "admin"},
    )
    assert reg_res.status_code == 201

    # Ensure role is admin in DB
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = UserRole.ADMIN.value
        db.commit()
    db.close()

    # Login to acquire access token
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "email": email,
        "password": password,
        "token": token,
        "headers": headers,
    }


def test_health_check_and_root_endpoint(client):
    """
    1. Health check / root endpoint (GET / returns 200).
    Ensures home page renders cleanly with institutional portal branding.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "MATRIXCMS" in response.text


def test_user_registration(client):
    """
    2. User registration (POST /api/auth/register).
    Validates user creation, role assignment, and conflict handling.
    """
    unique_id = uuid.uuid4().hex[:8]
    new_email = f"researcher_{unique_id}@chandigarh.ac.in"
    password = "ResearcherPassword456!"

    # Successful registration
    response = client.post(
        "/api/auth/register",
        json={
            "email": new_email,
            "password": password,
            "role": "researcher",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == new_email
    assert "id" in data
    assert "password" not in data  # Never expose hashed or raw password

    # Duplicate registration should return 400 Bad Request
    duplicate_res = client.post(
        "/api/auth/register",
        json={
            "email": new_email,
            "password": password,
            "role": "researcher",
        },
    )
    assert duplicate_res.status_code == 400
    assert "already exists" in duplicate_res.json()["detail"].lower()


def test_user_login_and_jwt_token(client):
    """
    3. User login and JWT token acquisition (POST /api/auth/login).
    Verifies credential authentication, bearer token emission, and rejection on invalid password.
    """
    unique_id = uuid.uuid4().hex[:8]
    email = f"login_test_{unique_id}@chandigarh.ac.in"
    password = "ValidPassword789!"

    # Register first
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": "public"},
    )

    # Valid login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == email

    # Invalid password login
    bad_login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login_res.status_code == 401


def test_expedition_creation_with_auth(client, test_admin_user):
    """
    4. Expedition creation with auth (POST /api/expeditions).
    Tests role-enforced expedition creation and metadata validation.
    """
    unique_id = uuid.uuid4().hex[:6]
    exp_payload = {
        "name": f"Himalayan Cryosphere Traverse {unique_id}",
        "start_date": "2026-05-01",
        "end_date": "2026-06-30",
        "region": "Chandra Basin, Western Himalaya",
        "objectives": "Survey mass balance, albedo variation, and glacial lake outburst hazards.",
        "team_leader": "Dr. Aarav Patel",
        "status": "planned",
    }

    # Unauthenticated should fail with 401
    unauth_res = client.post("/api/expeditions", json=exp_payload)
    assert unauth_res.status_code == 401

    # Authenticated creation
    auth_res = client.post(
        "/api/expeditions",
        json=exp_payload,
        headers=test_admin_user["headers"],
    )
    assert auth_res.status_code == 201
    created_exp = auth_res.json()
    assert created_exp["name"] == exp_payload["name"]
    assert created_exp["region"] == exp_payload["region"]
    assert created_exp["status"] == "planned"
    assert "id" in created_exp

    # Verify retrieval
    get_res = client.get(f"/api/expeditions/{created_exp['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == exp_payload["name"]


def test_dataset_creation_with_file_upload(client, test_admin_user):
    """
    5. Dataset creation with file upload (POST /api/datasets with io.BytesIO file).
    Validates multipart form-data handling, file persistence, and download endpoint.
    """
    # Create prerequisite expedition
    exp_res = client.post(
        "/api/expeditions",
        json={
            "name": f"Antarctic Glaciology Campaign {uuid.uuid4().hex[:6]}",
            "start_date": "2026-01-10",
            "end_date": "2026-02-28",
            "region": "Amundsen Sea Embayment",
            "objectives": "Observe ice shelf grounding line dynamics.",
            "team_leader": "Dr. Sunita Sharma",
            "status": "ongoing",
        },
        headers=test_admin_user["headers"],
    )
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    # Construct mock scientific CSV in memory using io.BytesIO
    csv_bytes = (
        b"elevation_m,snow_depth_cm,swe_mm,density_g_cm3\n"
        b"3200,45.2,18.5,0.41\n"
        b"3500,78.6,32.1,0.42\n"
        b"4000,120.4,54.2,0.45\n"
    )
    file_payload = ("chandra_snow_profile.csv", io.BytesIO(csv_bytes), "text/csv")

    form_data = {
        "title": "Chandra Glacier Snow Depth and Density Profile",
        "expedition_id": exp_id,
        "variables": "snow_depth, snow_water_equivalent, density",
        "units": "cm, mm, g/cm3",
        "temporal_coverage": "2026-05-01 to 2026-05-15",
        "spatial_coverage": "32.35 N, 77.20 E",
        "doi": f"10.1000/cg.{uuid.uuid4().hex[:8]}",
        "license": "CC-BY-4.0",
        "keywords": "himalaya, glaciology, snow, hydrology",
        "published": True,
    }

    # Upload dataset
    upload_res = client.post(
        "/api/datasets",
        data=form_data,
        files={"file": file_payload},
        headers=test_admin_user["headers"],
    )
    assert upload_res.status_code == 201
    dataset = upload_res.json()
    assert dataset["title"] == form_data["title"]
    assert dataset["published"] is True
    assert "file_path" in dataset

    dataset_id = dataset["id"]

    # Verify download serves raw file content
    dl_res = client.get(f"/api/datasets/{dataset_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content == csv_bytes


def test_unified_search_endpoint(client, test_admin_user):
    """
    6. Unified search endpoint (GET /api/search?q=...).
    Validates cross-entity keyword query execution and response formatting.
    """
    keyword = f"Karakoram_{uuid.uuid4().hex[:6]}"

    # Create an expedition matching this unique keyword
    client.post(
        "/api/expeditions",
        json={
            "name": f"Expedition {keyword}",
            "start_date": "2026-07-01",
            "end_date": "2026-08-30",
            "region": "Karakoram Range",
            "objectives": "Glacial surge monitoring and velocity measurement.",
            "team_leader": "Dr. Rajesh Kumar",
            "status": "planned",
        },
        headers=test_admin_user["headers"],
    )

    # Query search endpoint
    search_res = client.get(f"/api/search?q={keyword}")
    assert search_res.status_code == 200
    search_data = search_res.json()

    assert "total" in search_data
    assert "results" in search_data
    assert search_data["total"] >= 1

    # Verify SearchResult contract
    matching_item = next((r for r in search_data["results"] if keyword in r["title"]), None)
    assert matching_item is not None
    assert "type" in matching_item
    assert "id" in matching_item
    assert "snippet" in matching_item
    assert "link" in matching_item


def test_generated_content_list_and_approval(client, test_admin_user):
    """
    7. Generated content list and approval endpoint:
    - Lists AI-generated outreach drafts via GET /api/admin/generated-content.
    - Approves draft via POST /api/admin/generated-content/{id}/approve.
    """
    # Insert a draft generated content record into database
    db = SessionLocal()
    draft = GeneratedContent(
        source_type=ContentSourceType.REPORT.value,
        source_id=1,
        platform=PlatformType.WEB_SUMMARY.value,
        content="Scientific update: New field findings published under Himalayan cryosphere survey.",
        status=ContentStatus.PENDING_REVIEW.value,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    draft_id = draft.id
    db.close()

    # 1. Admin accesses review queue
    list_res = client.get(
        "/api/admin/generated-content",
        headers=test_admin_user["headers"],
    )
    assert list_res.status_code == 200
    drafts_list = list_res.json()
    assert isinstance(drafts_list, list)
    target = next((d for d in drafts_list if d["id"] == draft_id), None)
    assert target is not None
    assert target["status"] == "pending_review"

    # 2. Admin approves the draft
    approve_res = client.post(
        f"/api/admin/generated-content/{draft_id}/approve",
        headers=test_admin_user["headers"],
    )
    assert approve_res.status_code == 200
    approved_item = approve_res.json()
    assert approved_item["id"] == draft_id
    assert approved_item["status"] == "approved"

    # 3. Verify in DB
    db = SessionLocal()
    recheck = db.query(GeneratedContent).filter(GeneratedContent.id == draft_id).first()
    assert recheck.status == ContentStatus.APPROVED.value
    db.close()
