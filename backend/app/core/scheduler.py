from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.core.config import settings
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.models import Concept
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine

# SQLAlchemy jobstore to persist scheduled job configurations across app reloads
jobstores = {
    "default": SQLAlchemyJobStore(url="sqlite:///jobs.db")
}

scheduler = BackgroundScheduler(jobstores=jobstores)

def run_pipeline_for_all_active_concepts():
    """Fetches all active concepts and executes the intelligence pipeline run for each."""
    logger.info("Executing scheduled daily trend prediction ingestion runs...")
    db = SessionLocal()
    try:
        yt_service = YouTubeService()
        sem_service = SemanticService()
        engine = PipelineEngine(yt_service, sem_service)
        
        active_concepts = db.query(Concept).filter(Concept.active == True).all()
        logger.info(f"Found {len(active_concepts)} active concepts for ingestion.")
        
        for concept in active_concepts:
            try:
                engine.execute_concept_run(db, concept.id)
            except Exception as e:
                logger.error(f"Error during scheduled run for concept '{concept.name}': {e}")
    finally:
        db.close()

def start_scheduler():
    """Initializes and starts the background cron scheduler."""
    if scheduler.running:
        logger.info("Scheduler is already running.")
        return
        
    # Clear any stale scheduled jobs in SQLite jobstore
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass
    
    # Configure real-time cron trigger to run 3 times a day (00:00, 08:00, 16:00 UTC)
    scheduler.add_job(
        run_pipeline_for_all_active_concepts,
        trigger="cron",
        hour="0,8,16",
        minute=settings.scheduler_minute,
        timezone=settings.scheduler_timezone,
        id="realtime_trend_ingestion_pipeline"
    )
    
    scheduler.start()
    logger.info(
        f"Background cron scheduler successfully started. "
        f"Real-time ingestion job configured to run 3x daily (00:00, 08:00, 16:00 {settings.scheduler_timezone})."
    )

def stop_scheduler():
    """Stops the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background cron scheduler successfully shut down.")
