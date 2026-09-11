import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from app.tasks.content_generation_job import run_content_generation

logger = logging.getLogger("matrixcms.scheduler")

_scheduler = None


def get_scheduler() -> BackgroundScheduler:
    """Singleton getter for BackgroundScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    """Configure and start the periodic content generation scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        minutes = settings.SCHEDULER_INTERVAL_MINUTES
        scheduler.add_job(
            func=run_content_generation,
            trigger=IntervalTrigger(minutes=minutes),
            id="periodic_content_generation",
            name="Periodic Outreach Content Generation",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started: Content generation running every %s minutes.", minutes)
    return scheduler


def shutdown_scheduler():
    """Shut down scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
