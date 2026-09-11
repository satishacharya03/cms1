import logging
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.database import engine, Base
from app.tasks.content_generation_job import run_content_generation
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("matrixcms.runner")


def main():
    logger.info("==================================================")
    logger.info("MATRIXCMS Periodic Content Generation Scheduler")
    logger.info("Institution: %s | Department: %s", settings.INSTITUTION, settings.DEPARTMENT)
    logger.info("Database: %s", settings.DATABASE_URL)
    logger.info("LLM Model: %s via %s", settings.LLM_MODEL, settings.LLM_BASE_URL)
    logger.info("Scheduler Interval: Every %s minutes", settings.SCHEDULER_INTERVAL_MINUTES)
    logger.info("==================================================")

    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    # Run one immediate check on startup
    logger.info("Executing immediate content scan on startup...")
    run_content_generation()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_content_generation,
        trigger=IntervalTrigger(minutes=settings.SCHEDULER_INTERVAL_MINUTES),
        id="content_generation_worker",
        name="Outreach Content Generation",
        replace_existing=True,
    )

    try:
        logger.info("Scheduler is now running. Press Ctrl+C to terminate.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Terminating scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped cleanly.")


if __name__ == "__main__":
    main()
