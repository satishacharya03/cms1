from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL.strip().strip("<>\"' \t\r\n")
# Render and other cloud providers provide 'postgres://' URLs, but SQLAlchemy requires 'postgresql://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)


connect_args = {}
engine_kwargs = {
    "echo": (settings.APP_ENV == "debug"),
}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Production settings for PostgreSQL / MySQL / etc.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
