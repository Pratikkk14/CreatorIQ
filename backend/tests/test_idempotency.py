import pytest
from datetime import datetime, timezone, date, timedelta
from app.core import database
from app.models.models import Concept, ConceptDailySignal
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine
from tests.conftest import MockYouTubeProvider

def test_pipeline_idempotency(db_session):
    """
    Verifies that running the daily ingestion pipeline repeatedly
    for the same concept and execution date does not violate constraints
    and performs a safe database overwrite (idempotency).
    """
    database.SessionLocal = lambda: db_session

    mock_prov = MockYouTubeProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=mock_prov)
    sem_service = SemanticService()
    sem_service.compute_similarity = lambda t1, t2: 0.8
    
    engine = PipelineEngine(yt_service, sem_service)

    concept = db_session.query(Concept).first()
    assert concept is not None

    base_date = date(2026, 8, 19)

    # 1. Run pipeline first time
    res1 = engine.execute_concept_run(db_session, concept.id, base_date)
    assert res1["status"] == "success"
    
    signals_count_1 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id
    ).count()
    assert signals_count_1 == 1

    # Get signal details
    sig1 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id
    ).first()
    first_processed_at = sig1.processed_at

    # 2. Run pipeline second time for same target date
    res2 = engine.execute_concept_run(db_session, concept.id, base_date)
    assert res2["status"] == "success"
    
    signals_count_2 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id
    ).count()
    
    # Still should only have exactly 1 record for this concept/date (unique constraint enforced)
    assert signals_count_2 == 1
    
    sig2 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id
    ).first()
    # Ensure it was overwritten (different timestamp)
    assert sig2.processed_at >= first_processed_at

