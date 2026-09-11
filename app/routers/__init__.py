"""API Routers package."""
from app.routers import (
    auth,
    expeditions,
    reports,
    datasets,
    publications,
    media,
    activities,
    search,
    generated_content,
)

__all__ = [
    "auth",
    "expeditions",
    "reports",
    "datasets",
    "publications",
    "media",
    "activities",
    "search",
    "generated_content",
]
