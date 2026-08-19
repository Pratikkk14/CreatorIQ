import pytest
from datetime import datetime, timezone, date, timedelta
from app.core import database
from app.models.models import Concept, Video, VideoObservation, ConceptDailySignal
from app.services import YouTubeService, SemanticService, SelectorService
from app.services.discovery_engine import DiscoveryEngine
from app.services.observation_engine import ObservationEngine
from app.services.aggregation_engine import AggregationEngine
from tests.conftest import MockYouTubeProvider

def test_pipeline_idempotency(db_session):
    """
    Verifies that running pipeline discovery, observations, and signal generation
    repeatedly does not cause duplication in canonical tables.
    """
    database.SessionLocal = lambda: db_session

    mock_prov = MockYouTubeProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=mock_prov)
    sem_service = SemanticService()
    sem_service.compute_similarity = lambda t1, t2: 0.8 if any(__import__('re').search(rf'\b{v}\b', t2) for v in ["mock_vid_1", "mock_vid_2", "mock_vid_3", "mock_vid_4", "mock_vid_5"]) else 0.1
    sel_service = SelectorService()

    disc_eng = DiscoveryEngine(yt_service, sem_service, sel_service)
    obs_eng = ObservationEngine(yt_service)
    agg_eng = AggregationEngine()

    concept = db_session.query(Concept).first()
    assert concept is not None

    # Date variables
    target_dt = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    target_d = date(2026, 8, 19)

    # 1. Execute Discovery Twice
    disc_eng.run_discovery_for_concept(concept, target_dt - timedelta(days=7), target_dt)
    videos_count_1 = db_session.query(Video).count()
    
    # Run discovery again
    disc_eng.run_discovery_for_concept(concept, target_dt - timedelta(days=7), target_dt)
    videos_count_2 = db_session.query(Video).count()

    # Canonical videos must NOT be duplicated
    assert videos_count_1 == 12
    assert videos_count_2 == 12

    # 2. Execute Observation Twice for same timestamp
    obs_eng.run_observation(observation_time=target_dt)
    obs_count_1 = db_session.query(VideoObservation).count()
    assert obs_count_1 == 5
    
    # Run observation again for same timestamp
    obs_eng.run_observation(observation_time=target_dt)
    obs_count_2 = db_session.query(VideoObservation).count()
    
    # Observation rows must NOT be duplicated
    assert obs_count_2 == 5

    # 3. Execute Signal Generation Twice for same date
    agg_eng.aggregate_concept_signals(concept.id, target_d)
    signals_count_1 = db_session.query(ConceptDailySignal).count()
    assert signals_count_1 == 1
    
    # Run aggregation again
    agg_eng.aggregate_concept_signals(concept.id, target_d)
    signals_count_2 = db_session.query(ConceptDailySignal).count()
    
    # Concept signals must NOT be duplicated
    assert signals_count_2 == 1
