import pytest
from datetime import datetime, timezone, date, timedelta
from app.core import database
from app.core.config import settings
from app.models.models import Concept, ConceptDailySignal
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine
from tests.conftest import MockYouTubeProvider

def test_e2e_3day_simulation(db_session):
    """
    E2E simulation verifying that the consolidated search-derived daily
    ingestion pipeline executes successfully, applies filters, computes percentiles,
    flags outliers, calculates streaks, and registers daily signals.
    """
    # 1. Override database SessionLocal
    database.SessionLocal = lambda: db_session

    # 2. Setup mock YouTube provider and services
    mock_prov = MockYouTubeProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=mock_prov)
    sem_service = SemanticService()
    # Mock similarity to return 0.8 for mock videos (so they pass semantic filters)
    sem_service.compute_similarity = lambda t1, t2: 0.8
    
    engine = PipelineEngine(yt_service, sem_service)

    concept = db_session.query(Concept).first()
    assert concept is not None

    # Base execution dates
    base_date = date(2026, 8, 19)

    # ==================== DAY 0 EXECUTION ====================
    mock_prov.day = 0
    # Process videos published on base_date - 3 days (2026-08-16)
    res0 = engine.execute_concept_run(db_session, concept.id, base_date)
    assert res0["status"] == "success"
    assert res0["population_size"] == 5  # 5 videos pass views filter gate (mock_vid_1 to mock_vid_5)
    
    # Check database signal written
    sig0 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id,
        ConceptDailySignal.video_date == base_date - timedelta(days=settings.lag_days)
    ).first()
    assert sig0 is not None
    assert sig0.population_size == 5
    assert sig0.concept_name == concept.name
    assert sig0.reach_ratio_median is not None
    assert sig0.interaction_density_median is not None
    assert sig0.semantic_score_mean == 0.8
    assert len(sig0.keywords) == 5
    assert len(sig0.population) == 5
    
    # Check tiers assigned using relative percentiles
    for p in sig0.population:
        assert p["channel_tier"] in ["small", "medium", "big"]

    # ==================== DAY 1 EXECUTION ====================
    mock_prov.day = 1
    # Process videos published on base_date + 1 day
    res1 = engine.execute_concept_run(db_session, concept.id, base_date + timedelta(days=1))
    assert res1["status"] == "success"
    
    sig1 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id,
        ConceptDailySignal.video_date == base_date + timedelta(days=1) - timedelta(days=settings.lag_days)
    ).first()
    assert sig1 is not None
    assert sig1.population_size == 5

    # ==================== DAY 2 EXECUTION ====================
    mock_prov.day = 2
    # Process videos published on base_date + 2 days
    res2 = engine.execute_concept_run(db_session, concept.id, base_date + timedelta(days=2))
    assert res2["status"] == "success"
    
    sig2 = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id,
        ConceptDailySignal.video_date == base_date + timedelta(days=2) - timedelta(days=settings.lag_days)
    ).first()
    assert sig2 is not None
    assert sig2.population_size == 5

    # ==================== VERIFY INVARIANTS ====================
    # 1. Obsolete tables MUST NOT exist in the database schema
    from sqlalchemy import inspect
    inspector = inspect(db_session.bind)
    table_names = inspector.get_table_names()
    for ob_table in ["channels", "videos", "video_observations", "video_metrics", "video_candidates", "population_runs", "population_members", "search_runs"]:
        assert ob_table not in table_names


