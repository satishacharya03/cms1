# MATRIXCMS: Scientific Expeditions & Research Repository

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![FAIR Compliant](https://img.shields.io/badge/Data_Standard-FAIR_%26_ISO_19115-success.svg)](#academic-data-standards)
[![Tests: Pytest](https://img.shields.io/badge/tests-30%20passed-brightgreen.svg)](#testing-suite)

> **MATRIXCMS** is an institutional open-science repository and research expedition content management system engineered for the **Department of Computer Science & Engineering, Chandigarh**. It provides end-to-end archival, cataloging, metadata compliance, and automated public outreach generation for scientific field campaigns, datasets, technical cruise reports, peer-reviewed publications, and high-resolution media.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Core Features](#core-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Step-by-Step Installation & Setup](#step-by-step-installation--setup)
- [Running the Application](#running-the-application)
- [Running the Background Scheduler](#running-the-background-scheduler)
- [Testing Suite](#testing-suite)
- [Authentication & Role-Based Access Control (RBAC)](#authentication--role-based-access-control-rbac)
- [Free LLM Integration Guide](#free-llm-integration-guide)
- [Storage Abstraction & S3 Migration](#storage-abstraction--s3-migration)
- [Academic Data Standards & FAIR Stewardship](#academic-data-standards--fair-stewardship)
- [API Documentation](#api-documentation)
- [License](#license)

---

## Project Overview

Modern scientific research campaigns—ranging from glaciological sensor network deployments in the Himalayas to canopy microclimate logging in the Western Ghats—produce voluminous, heterogeneous data artifacts. Without a standardized repository, critical research outputs face data drift, lack persistent identifiers, and remain isolated from scientific peers and public awareness.

**MATRIXCMS** resolves these challenges by uniting institutional archival standards with modern automated scientific communication:
1. **Scientific Expeditions Archive**: Centralizes field expedition campaigns, coordinates (bounding boxes), operational status (`planned`, `ongoing`, `completed`, `archived`), and multi-institutional partnerships.
2. **Open Datasets Catalog**: Stores tabular, spatial, and sensor data (CSV, NetCDF, HDF5) annotated with standardized variable descriptions, temporal boundaries, file checksums, and CC-BY-4.0 licenses.
3. **Cruise & Technical Reports**: Preserves field and technical documentation with downloadable physical PDF documents and author attribution.
4. **Peer-Reviewed Publications**: Catalogs journal and conference papers indexed with persistent DOIs, journal volumes, and citation metadata.
5. **Media Asset Repository**: Curates high-resolution photographic and video field assets with camera EXIF, GPS location tags, and copyright stewardship.
6. **Academic Activities & News**: Showcases workshops, field training sessions, symposia, and outreach activities.
7. **Automated AI Outreach Synthesis**: Automatically generates multi-platform dissemination drafts (Web summaries, Twitter/X threads, LinkedIn research spotlights, Instagram field captions) with human-in-the-loop review.

---

## Core Features

- **Dublin Core & ISO 19115 Metadata**: Built upon established academic schemas, supporting bibliographic attribution, geospatial bounding coordinates, and temporal ranges.
- **Automated AI Content Engine**: Integrates OpenAI-compatible LLM endpoints (Groq, Cloudflare Workers AI, local Ollama) to summarize newly uploaded expeditions, datasets, and reports into tailored outreach formats.
- **Robust Fallback Engine**: If no LLM API key is provided or external networks fail, the system automatically falls back to deterministic heuristic text synthesis—ensuring zero downtime.
- **Human-in-the-Loop Content Approval**: Generated drafts remain in `pending` review. Administrators and Data Managers can edit, approve (auto-publishing to the Activities feed), or reject drafts.
- **Unified Full-Text Search**: Search across expeditions, datasets, reports, publications, media, and activities in a single query with filters for year, type, and status.
- **Granular RBAC**: Strict multi-tier authorization powered by cryptographically signed JWT tokens for `admin`, `data_manager`, `researcher`, and `public` users.
- **Pluggable Storage Abstraction**: Decoupled physical asset storage supporting sanitized, collision-free local filesystem paths with seamless migration to AWS S3, MinIO, or Cloudflare R2.
- **Bespoke Academic Design**: Fast, responsive, server-rendered Jinja2 interface adhering to clean typographic principles and academic portal guidelines.

---

## Architecture & Tech Stack

```
                                  +---------------------------------------+
                                  |         Browser / API Clients         |
                                  +---------------------------------------+
                                                      |
                                           HTTPS / REST / JWT Auth
                                                      v
+---------------------------------------------------------------------------------------------------+
| MATRIXCMS Application Layer (FastAPI)                                                             |
|                                                                                                   |
|  +----------------------+  +---------------------+  +--------------------+  +------------------+  |
|  | Web Router (Jinja2)  |  | REST API Endpoints  |  | Search Engine      |  | Auth & Security  |  |
|  | - Portals & Catalogs |  | - Expeditions / Data|  | - Multi-entity q=  |  | - JWT Tokens     |  |
|  | - Admin Review Panel |  | - Reports / Pubs    |  | - Year/Type filter |  | - Bcrypt / RBAC  |  |
|  +----------------------+  +---------------------+  +--------------------+  +------------------+  |
|            |                          |                        |                      |           |
|            +--------------------------+------------------------+----------------------+           |
|                                       v                                                           |
|                          +--------------------------+                                             |
|                          |    SQLAlchemy 2.0 ORM    |                                             |
|                          +--------------------------+                                             |
+---------------------------------------------------------------------------------------------------+
        |                                       |                                   |
        v                                       v                                   v
+-----------------------+           +-----------------------+           +-----------------------+
| Relational Storage    |           | Storage Abstraction   |           | Outreach Engine       |
| - SQLite (Dev)        |           | - Local Filesystem    |           | - Groq / Llama 3.1    |
| - PostgreSQL (Prod)   |           | - S3 / MinIO (Cloud)  |           | - Ollama (Local)      |
| - Alembic Migrations  |           | - Upload Validation   |           | - Heuristic Fallback  |
+-----------------------+           +-----------------------+           +-----------------------+
                                                                                    ^
                                                                                    |
                                                                        +-----------------------+
                                                                        | Background Scheduler  |
                                                                        | - APScheduler 3.x     |
                                                                        | - Periodic Batch Scan |
                                                                        +-----------------------+
```

### Technology Matrix

| Layer | Component | Version | Description |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.10 - 3.12 | Core programming environment |
| **Framework** | FastAPI | 0.110+ | High-performance asynchronous web framework |
| **ASGI Server** | Uvicorn | 0.28+ | Lightning-fast ASGI web server |
| **ORM** | SQLAlchemy | 2.0.25+ | Next-generation Python SQL toolkit and Object Relational Mapper |
| **Database Migrations** | Alembic | 1.13+ | Schema change management and versioning |
| **Validation** | Pydantic v2 | 2.6+ | Runtime data validation and settings management |
| **Templates** | Jinja2 | 3.1.3+ | Expressive server-side template engine |
| **Background Jobs** | APScheduler | 3.10.4+ | Advanced Python task scheduler for batch AI synthesis |
| **Security** | Python-Jose & Passlib | 3.3+ / 1.7+ | Cryptographic JWT generation and bcrypt password hashing |
| **HTTP Client** | HTTPX | 0.27+ | Async/sync HTTP client for OpenAI-compatible LLM communication |
| **Testing** | Pytest & pytest-asyncio | 8.0+ | Automated test framework and async fixtures |

---

## Directory Structure

```
cms1/
|-- alembic/                        # Database migration scripts
|   |-- versions/
|   |   `-- 0001_initial_schema.py   # Baseline schema definition
|   `-- env.py                      # Alembic database context loader
|-- alembic.ini                     # Alembic configuration
|-- app/
|   |-- __init__.py
|   |-- auth.py                     # Password hashing, JWT encode/decode, token helpers
|   |-- config.py                   # Pydantic Settings (.env configuration loader)
|   |-- database.py                 # SQLAlchemy engine, session maker, Base declarative
|   |-- dependencies.py             # Auth dependencies & RBAC role checkers
|   |-- main.py                     # FastAPI application factory, middleware, mount points
|   |-- models.py                   # SQLAlchemy models (User, Expedition, Dataset, etc.)
|   |-- schemas.py                  # Pydantic schemas for request/response serialization
|   |-- routers/                    # Endpoint routing controllers
|   |   |-- __init__.py
|   |   |-- auth.py                 # /api/auth (register, login, token refresh)
|   |   |-- expeditions.py          # /api/expeditions (CRUD operations)
|   |   |-- datasets.py             # /api/datasets (CRUD & file upload)
|   |   |-- reports.py              # /api/reports (CRUD & PDF upload)
|   |   |-- publications.py         # /api/publications (CRUD & citation metadata)
|   |   |-- media.py                # /api/media (CRUD & multimedia file upload)
|   |   |-- activities.py           # /api/activities (Institutional news & events)
|   |   |-- search.py               # /api/search (Multi-entity unified search)
|   |   |-- admin.py                # /api/admin (Outreach approval, re-triggering)
|   |   `-- web.py                  # Server-rendered HTML web views
|   |-- services/                   # Business logic and external service integrations
|   |   |-- __init__.py
|   |   |-- content_generator.py    # OpenAI-compatible LLM outreach & heuristic fallback
|   |   |-- scheduler.py            # APScheduler batch job setup and runner
|   |   `-- storage.py              # Filesystem storage abstraction (S3 compatible)
|   |-- static/                     # Static UI assets
|   |   |-- css/
|   |   |   `-- style.css           # Academic typography & responsive styles
|   |   `-- js/
|   |       `-- main.js             # Client interactivity, modals, search handlers
|   |-- tasks/
|   |   |-- __init__.py
|   |   `-- content_generation_job.py # Batch un-generated record scanner
|   `-- templates/                  # Jinja2 HTML templates
|       |-- base.html               # Institutional layout, masthead, nav, footer
|       |-- home.html               # Homepage with metrics, featured expeditions, news
|       |-- expeditions/            # Expedition list and detailed views
|       |-- datasets/               # Dataset catalog and detail pages
|       |-- reports/                # Report repository
|       |-- publications/           # Peer-reviewed publication catalog
|       |-- media/                  # Media gallery with modal viewer
|       |-- activities/             # Activities and outreach feed
|       |-- admin/                  # Admin outreach approval console
|       |-- search.html             # Unified search results view
|       |-- about.html              # Institutional overview & standards
|       |-- login.html              # Authentication login view
|       `-- register.html           # User registration view
|-- scripts/
|   |-- seed_data.py                # Academic data seeder with physical files
|   `-- run_scheduler.py            # Standalone daemon for background content generation
|-- storage/
|   `-- uploads/                    # Local storage root for uploaded research files
|-- tests/                          # Pytest verification test suite
|   |-- __init__.py
|   |-- conftest.py                 # Test fixtures & isolated in-memory DB setup
|   |-- test_api.py                 # Integration tests for core API endpoints
|   |-- test_content_generator.py   # Unit tests for LLM generation & heuristic fallbacks
|   |-- test_routers.py             # Router-level functional tests
|   `-- test_templates.py           # Jinja2 template rendering tests
|-- .env.example                    # Sample environment variable template
|-- requirements.txt                # Pinned project dependencies
`-- README.md                       # Comprehensive documentation
```

---

## Prerequisites

Ensure the following tools are installed on your workstation or server:
- **Python 3.10, 3.11, or 3.12**
- **Git**
- *(Optional)* **Ollama** if running local, offline LLM inference.

---

## Step-by-Step Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/chandigarh-cse/matrixcms.git
cd matrixcms
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Install all core and development dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the provided `.env.example` to `.env`:

```bash
# On Linux / macOS:
cp .env.example .env

# On Windows (PowerShell):
Copy-Item .env.example .env
```

Review the defaults in `.env`:
```ini
PROJECT_NAME=MATRIXCMS
INSTITUTION=Chandigarh
DEPARTMENT=CSE
DATABASE_URL=sqlite:///./matrixcms.db
SECRET_KEY=matrixcms_secret_key_change_in_production_f72389d7fae29bc
STORAGE_ROOT=./storage/uploads
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_placeholder_replace_with_your_free_key
LLM_MODEL=llama-3.1-8b-instruct
```

> **Note**: You can run MATRIXCMS immediately with the default placeholder key. If an invalid or placeholder key is detected, the built-in heuristic fallback engine will cleanly synthesize high-quality outreach text without failing.

### 5. Apply Database Migrations

Run Alembic to create all relational tables:
```bash
alembic upgrade head
```

### 6. Seed Academic Demo Data

Populate the database with realistic scientific datasets, expeditions, physical PDFs, CSV data files, and pre-seeded user accounts:
```bash
python scripts/seed_data.py
```

*Output summary:*
```
Writing physical asset files to storage root...
  [Report PDF] -> reports/2025/06/hgds2025_glaciology_technical_report.pdf
  [Dataset CSV] -> datasets/2025/06/glacier_temperature_timeseries_2025.csv
  [Media Image] -> media/2025/06/sensor_mast_glacier_summit.jpg
[1/8] Seeding Users...
[2/8] Seeding Expeditions...
[3/8] Seeding Reports...
[4/8] Seeding Datasets...
[5/8] Seeding Publications...
[6/8] Seeding Media Assets...
[7/8] Seeding Activities...
[8/8] Seeding Generated Outreach Content...
SEEDING COMPLETE: All academic records & physical files created successfully.
```

---

## Running the Application

Start the web application server with Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, access:
- **Web Portal**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running the Background Scheduler

MATRIXCMS includes a standalone periodic background worker powered by APScheduler. It scans the database every 15 minutes (configurable via `SCHEDULER_INTERVAL_MINUTES`) for any newly registered expeditions, datasets, or reports that lack generated outreach content, triggers LLM or heuristic generation, and stages drafts for admin review.

In a separate terminal window:
```bash
python scripts/run_scheduler.py
```

*Scheduler Log Output:*
```
[2026-09-09 11:35:00] [INFO] matrixcms.runner: MATRIXCMS Periodic Content Generation Scheduler
[2026-09-09 11:35:00] [INFO] matrixcms.runner: Institution: Chandigarh | Department: CSE
[2026-09-09 11:35:00] [INFO] matrixcms.runner: Executing immediate content scan on startup...
[2026-09-09 11:35:01] [INFO] matrixcms.runner: Scan finished: 0 new items queued for generation.
[2026-09-09 11:35:01] [INFO] matrixcms.runner: Scheduler is now running. Press Ctrl+C to terminate.
```

---

## Testing Suite

MATRIXCMS features a comprehensive test suite built with `pytest` and `pytest-asyncio` utilizing an isolated, in-memory SQLite test database.

Run all tests:
```bash
pytest
```
Or with verbose output:
```bash
python -m pytest tests/ -v
```

### Test Coverage Summary (30 Tests Passed)

```
tests/test_api.py::test_health_check_and_root_endpoint PASSED            [  3%]
tests/test_api.py::test_user_registration PASSED                         [  6%]
tests/test_api.py::test_user_login_and_jwt_token PASSED                  [ 10%]
tests/test_api.py::test_expedition_creation_with_auth PASSED             [ 13%]
tests/test_api.py::test_dataset_creation_with_file_upload PASSED         [ 16%]
tests/test_api.py::test_unified_search_endpoint PASSED                   [ 20%]
tests/test_api.py::test_generated_content_list_and_approval PASSED       [ 23%]
tests/test_content_generator.py::test_heuristic_fallback_when_api_key_is_placeholder PASSED [ 26%]
tests/test_content_generator.py::test_mock_llm_valid_json_response PASSED [ 30%]
tests/test_content_generator.py::test_mock_llm_markdown_code_block_json PASSED [ 33%]
tests/test_content_generator.py::test_mock_llm_http_error_falls_back_to_heuristic PASSED [ 36%]
tests/test_content_generator.py::test_mock_llm_missing_keys_falls_back_to_heuristic PASSED [ 40%]
tests/test_content_generator.py::test_dataset_heuristic_generation PASSED [ 43%]
tests/test_routers.py::test_list_activities PASSED                       [ 46%]
tests/test_routers.py::test_list_activities_filter PASSED                [ 50%]
tests/test_routers.py::test_get_activity PASSED                          [ 53%]
tests/test_routers.py::test_create_activity_permissions PASSED           [ 56%]
tests/test_routers.py::test_unified_search_all PASSED                    [ 60%]
tests/test_routers.py::test_unified_search_query_keyword PASSED          [ 63%]
tests/test_routers.py::test_unified_search_type_filter PASSED            [ 66%]
tests/test_routers.py::test_unified_search_public_vs_admin_visibility PASSED [ 70%]
tests/test_routers.py::test_unified_search_expedition_and_year_filters PASSED [ 73%]
tests/test_routers.py::test_unified_search_pagination PASSED             [ 76%]
tests/test_routers.py::test_list_generated_content_permissions PASSED    [ 80%]
tests/test_routers.py::test_list_generated_content_filter PASSED         [ 83%]
tests/test_routers.py::test_get_and_update_generated_content PASSED      [ 86%]
tests/test_routers.py::test_approve_web_summary_creates_activity PASSED  [ 90%]
tests/test_routers.py::test_reject_generated_content PASSED              [ 93%]
tests/test_routers.py::test_trigger_content_generation PASSED            [ 96%]
tests/test_templates.py::test_templates_rendering PASSED                 [100%]
=================================== 30 passed in 9.5s ===================================
```

---

## Authentication & Role-Based Access Control (RBAC)

MATRIXCMS enforces Role-Based Access Control (RBAC) using OAuth2 Bearer tokens with JWT authentication.

### Role Hierarchy & Permissions

| Role | Access Level | Permitted Actions |
| :--- | :--- | :--- |
| **`admin`** | Full System Access | Review, edit, approve, and reject AI outreach drafts; manage user roles; trigger on-demand AI content generation; full CRUD across all entities. |
| **`data_manager`** | Operational Steward | Create, update, and manage expeditions, datasets, reports, publications, and media; upload large data files; review content drafts. |
| **`researcher`** | Academic Contributor | Submit field reports, upload datasets and publications associated with authorized expeditions. |
| **`public`** | Anonymous / Read-Only | Browse public catalog, search records, view public news & activities, download open data files. |

### Seeded Credentials for Testing

The following default accounts are provisioned by `python scripts/seed_data.py`:

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@chandigarh.edu` | `admin123` |
| **Data Manager** | `datamanager@chandigarh.edu` | `data123` |
| **Researcher** | `researcher@chandigarh.edu` | `research123` |
| **Public / Student** | `student@chandigarh.edu` | `student123` |

### Acquiring a JWT Token via API

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@chandigarh.edu", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Include the token in protected requests:
```bash
curl -X GET "http://localhost:8000/api/admin/generated-content" \
     -H "Authorization: Bearer <access_token>"
```

---

## Free LLM Integration Guide

MATRIXCMS utilizes an OpenAI-compatible HTTP client in `app/services/content_generator.py`. This enables plug-and-play integration with several **100% free** LLM providers.

### Option 1: Groq Cloud (Recommended for Speed)
Groq provides a generous free tier with ultra-fast inference for open-weights models.
1. Sign up at [console.groq.com](https://console.groq.com) and create an API key.
2. In your `.env` file:
   ```ini
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=gsk_your_actual_groq_api_key
   LLM_MODEL=llama-3.1-8b-instruct
   ```

### Option 2: Local Ollama (100% Offline & Private)
If you prefer zero external internet calls:
1. Install [Ollama](https://ollama.ai) and pull Llama 3.1:
   ```bash
   ollama run llama3.1:8b
   ```
2. In your `.env` file:
   ```ini
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_API_KEY=ollama
   LLM_MODEL=llama3.1:8b
   ```

### Option 3: Cloudflare Workers AI
Cloudflare offers free daily neurons for open models:
1. Obtain your Account ID and Workers AI API Token from the Cloudflare dashboard.
2. In your `.env` file:
   ```ini
   LLM_BASE_URL=https://api.cloudflare.com/client/v4/accounts/<YOUR_ACCOUNT_ID>/ai/v1
   LLM_API_KEY=<YOUR_CLOUDFLARE_TOKEN>
   LLM_MODEL=@cf/meta/llama-3.1-8b-instruct
   ```

### Robust Heuristic Fallback Engine
If an API key is missing or set to `gsk_placeholder...`, or if an upstream rate limit (HTTP 429) or network outage occurs, `app.services.content_generator` automatically invokes its internal heuristic synthesizer. 

The fallback engine deterministically generates platform-tailored text respecting:
- **`web_summary`**: Multi-paragraph academic overview with DOI and expedition links.
- **`tweet`**: Strict < 280-character post with relevant scientific hashtags.
- **`linkedin`**: Professional 3-paragraph research impact overview.
- **`instagram`**: Engaging field caption with visual indicators and hashtag cluster.

---

## Storage Abstraction & S3 Migration

File storage is abstracted through `app/services/storage.py`. Files uploaded to `/api/datasets`, `/api/reports`, or `/api/media` are validated against strict MIME/extension rules, sanitized against path traversal vulnerabilities, and partitioned chronologically:

```
storage/uploads/
|-- datasets/
|   `-- 2025/
|       `-- 06/
|           `-- a1b2c3d4_glacier_temperature_timeseries_2025.csv
|-- reports/
|   `-- 2025/
|       `-- 06/
|           `-- f8e7d6c5_hgds2025_glaciology_technical_report.pdf
`-- media/
    `-- 2025/
        `-- 06/
            `-- 9a8b7c6d_sensor_mast_glacier_summit.jpg
```

### Zero-Downtime Migration to AWS S3 / MinIO / Cloudflare R2

Because `app/services/storage.py` exposes high-level functions (`save_file`, `get_file_path`, `file_exists`, `delete_file`), migrating to AWS S3 requires updating only `storage.py` without modifying any route handlers:

```python
# S3 Implementation Example for app/services/storage.py
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
)
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "matrixcms-assets")

def save_file_s3(upload_file: UploadFile, subdir: str) -> str:
    key = f"{subdir}/{datetime.now().strftime('%Y/%m')}/{uuid.uuid4().hex[:8]}_{sanitize_filename(upload_file.filename)}"
    s3_client.upload_fileobj(upload_file.file, S3_BUCKET, key)
    return key
```

---

## Academic Data Standards & FAIR Stewardship

MATRIXCMS adheres to international open-science data governance frameworks:

### 1. Dublin Core Metadata Element Set (ISO 15836)
All repository items are mapped to Dublin Core elements:
- `dc:title` & `dc:creator`: Expedition lead investigators and publication authors.
- `dc:subject`: Scientific taxonomy, keywords, and disciplines (Glaciology, Hydrology, Canopy Ecology).
- `dc:date`: ISO 8601 timestamps for field acquisition, release, and embargo dates.
- `dc:identifier`: Persistent DOIs (e.g., `10.5281/zenodo.matrix.2025.01`).
- `dc:rights`: Open science licensing (`CC-BY-4.0`).

### 2. ISO 19115 Geographic Metadata
Expeditions and field datasets record geographic coordinates:
- Bounding latitudes and longitudes (`north_bound_latitude`, `south_bound_latitude`, `east_bound_longitude`, `west_bound_longitude`).
- Elevation profiles and sea/lake borehole depths.

### 3. The FAIR Guiding Principles
- **Findable**: Global persistent DOIs and multi-entity unified search indexing.
- **Accessible**: Open REST endpoints and standard HTTP download capabilities.
- **Interoperable**: Standard open formats (CSV, NetCDF, GeoTIFF, PDF-1.4).
- **Reusable**: Permissive Creative Commons licensing and clear methodology provenance.

---

## API Documentation

When the server is running, explore the interactive documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Primary Endpoint Overview

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Institutional portal landing page |
| `/api/auth/register` | `POST` | Public | Register new user account |
| `/api/auth/login` | `POST` | Public | Authenticate user and receive JWT bearer token |
| `/api/expeditions` | `GET`, `POST` | Public / Data Mgr | List expeditions or create a new field expedition |
| `/api/expeditions/{id}`| `GET`, `PUT`, `DELETE`| Public / Data Mgr | Retrieve or modify expedition details |
| `/api/datasets` | `GET`, `POST` | Public / Researcher | Browse datasets or upload new data with file attachment |
| `/api/reports` | `GET`, `POST` | Public / Researcher | Browse reports or upload technical PDF report |
| `/api/publications` | `GET`, `POST` | Public / Researcher | Peer-reviewed publication catalog with DOI |
| `/api/media` | `GET`, `POST` | Public / Data Mgr | Multimedia asset library (images, videos) |
| `/api/activities` | `GET`, `POST` | Public / Data Mgr | Academic news, seminars, and field updates |
| `/api/search` | `GET` | Public | Unified full-text search across all entity categories |
| `/api/admin/generated-content` | `GET` | Admin / Data Mgr | List staged AI outreach drafts with status filter |
| `/api/admin/generated-content/{id}/approve` | `POST` | Admin | Approve outreach draft (auto-publishes to Activities) |
| `/api/admin/generated-content/{id}/reject` | `POST` | Admin | Reject draft with optional revision feedback |
| `/api/admin/trigger-generation` | `POST` | Admin | Manually trigger AI outreach synthesis for an item |

---

## License

This project is licensed under the **MIT License**.

All scientific datasets, cruise reports, and publication preprints managed within MATRIXCMS are curated under the **Creative Commons Attribution 4.0 International (CC-BY-4.0)** license, permitting sharing and adaptation with appropriate attribution.

---

*Department of Computer Science & Engineering, Chandigarh*  
*Contact: `cse-expeditions@chandigarh.edu`*
