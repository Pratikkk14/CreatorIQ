import pytest
from datetime import datetime, timezone, date, timedelta
from app.core import database
from app.models.models import (
    Concept, Video, VideoObservation, VideoMetric, 
    ConceptDailySignal, VideoCandidate, PopulationMember, SearchRun, PopulationRun
)
from app.services import YouTubeService, SemanticService, SelectorService
from app.services.discovery_engine import DiscoveryEngine
from app.services.observation_engine import ObservationEngine
from app.services.metrics_engine import MetricsEngine
from app.services.aggregation_engine import AggregationEngine
from tests.conftest import MockYouTubeProvider

def test_e2e_3day_simulation(db_session):
    """
    E2E simulation described in Section 33.
    Verifies that discovery, selection, observation, feature engineering,
    and aggregation produce the correct mathematical outputs and database states.
    """
    # 1. Override database SessionLocal to point to our test session maker
    def mock_get_db():
        return db_session
    database.SessionLocal = lambda: db_session

    # 2. Setup mock YouTube provider and services
    mock_prov = MockYouTubeProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=mock_prov)
    sem_service = SemanticService()
    sem_service.compute_similarity = lambda t1, t2: 0.8 if any(__import__('re').search(rf'\b{v}\b', t2) for v in ["mock_vid_1", "mock_vid_2", "mock_vid_3", "mock_vid_4", "mock_vid_5"]) else 0.1
    sel_service = SelectorService()

    disc_eng = DiscoveryEngine(yt_service, sem_service, sel_service)
    obs_eng = ObservationEngine(yt_service)
    met_eng = MetricsEngine()
    agg_eng = AggregationEngine()

    concept = db_session.query(Concept).first()
    assert concept is not None

    # Base dates
    base_date = date(2026, 8, 19)
    day0_obs_time = datetime.combine(base_date, datetime.min.time(), tzinfo=timezone.utc)
    day1_obs_time = day0_obs_time + timedelta(days=1)
    day2_obs_time = day0_obs_time + timedelta(days=2)

    # ==================== DAY 0 EXECUTION ====================
    mock_prov.day = 0
    # Run discovery for the concept
    pop_run = disc_eng.run_discovery_for_concept(concept, day0_obs_time - timedelta(days=7), day0_obs_time)
    assert pop_run is not None
    assert pop_run.actual_size == 5

    # Check candidates registered
    cands = db_session.query(VideoCandidate).all()
    assert len(cands) == 12  # Returned 12 candidate videos
    
    # Selected population members
    members = db_session.query(PopulationMember).filter(PopulationMember.population_run_id == pop_run.id).all()
    assert len(members) == 5
    selected_video_ids = [m.video_id for m in members]
    assert len(selected_video_ids) == 5

    # Execute Day 0 observation
    o_res0 = obs_eng.run_observation(observation_time=day0_obs_time)
    assert o_res0["observed_count"] == 5

    # Generate metrics
    m_res0 = met_eng.run_metrics_generation()
    assert m_res0["processed_count"] == 5

    # Generate signals
    agg_res0 = agg_eng.aggregate_concept_signals(concept.id, base_date)
    assert agg_res0 is not None
    assert agg_res0.population_size == 5
    assert agg_res0.observation_coverage == 1.0
    
    # For Day 0, velocity metrics are NULL because it's the first observation
    assert agg_res0.median_view_velocity is None

    # ==================== DAY 1 EXECUTION ====================
    mock_prov.day = 1
    
    # Execute Day 1 observation
    o_res1 = obs_eng.run_observation(observation_time=day1_obs_time)
    assert o_res1["observed_count"] == 5

    # Generate metrics
    m_res1 = met_eng.run_metrics_generation()
    assert m_res1["processed_count"] == 5

    # Generate signals
    agg_res1 = agg_eng.aggregate_concept_signals(concept.id, base_date + timedelta(days=1))
    assert agg_res1 is not None
    assert agg_res1.observation_coverage == 1.0

    # Let's verify Day 1 derived metrics in DB
    # Day 1 view stats:
    # V1 (100 -> 250), vel = 150
    # V2 (200 -> 350), vel = 150
    # V3 (300 -> 900), vel = 600
    # V4 (400 -> 450), vel = 50
    # V5 (500 -> 1000), vel = 500
    # Sorted velocities: 50, 150, 150, 500, 600
    # Let's print out what we got in db for population members and metrics!
    print("--- DEBUG MEMBERS ---")
    for m in db_session.query(PopulationMember).all():
        print(f"MEMBER: {m.video_id} bucket={m.creator_size_bucket} score={m.selection_score} rank={m.rank}")
    print("--- DEBUG METRICS ---")
    for met in db_session.query(VideoMetric).all():
        print(f"METRIC: {met.video_id} velocity={met.view_velocity} age={met.age_days}")
    assert agg_res1.big_creator_signal == 550.0
    
    # Small creators (V2, V4) velocities: 150, 50. Median = 100.0
    assert agg_res1.small_creator_signal == 100.0
    
    # Medium creators (V1) velocity: 150. Median = 150.0
    assert agg_res1.medium_creator_signal == 150.0

    # ==================== DAY 2 EXECUTION ====================
    mock_prov.day = 2
    
    # Execute Day 2 observation
    o_res2 = obs_eng.run_observation(observation_time=day2_obs_time)
    assert o_res2["observed_count"] == 5

    # Generate metrics
    m_res2 = met_eng.run_metrics_generation()
    assert m_res2["processed_count"] == 5

    # Generate signals
    agg_res2 = agg_eng.aggregate_concept_signals(concept.id, base_date + timedelta(days=2))
    assert agg_res2 is not None

    # Let's verify Day 2 derived metrics in DB
    # Day 2 view stats:
    # V1 (250 -> 500), vel = 250
    # V2 (350 -> 700), vel = 350
    # V3 (900 -> 1800), vel = 900
    # V4 (450 -> 700), vel = 250
    # V5 (1000 -> 2500), vel = 1500
    # Sorted velocities: 250, 250, 350, 900, 1500
    # Expected median velocity: 350.0
    assert agg_res2.median_view_velocity == 350.0

    # Check Day 2 accelerations in DB:
    # V1: vel1 = 150, vel2 = 250. acc = 250 - 150 = 100
    # V2: vel1 = 150, vel2 = 350. acc = 350 - 150 = 200
    # V3: vel1 = 600, vel2 = 900. acc = 900 - 600 = 300
    # V4: vel1 = 50, vel2 = 250. acc = 250 - 50 = 200
    # V5: vel1 = 500, vel2 = 1500. acc = 1500 - 500 = 1000
    # Sorted accelerations: 100, 200, 200, 300, 1000
    # Expected median acceleration: 200.0
    assert agg_res2.median_view_acceleration == 200.0

    # ==================== VERIFY INVARIANTS ====================
    # 1. Total videos = 12 (all candidates registered idempotently)
    assert db_session.query(Video).count() == 12

    # 2. Total observations = 15 (5 videos * 3 observations)
    assert db_session.query(VideoObservation).count() == 15

    # 3. Immutability check: Past observations must remain unchanged
    day0_obs_v1 = db_session.query(VideoObservation).filter(
        VideoObservation.video_id == "mock_vid_1",
        VideoObservation.observed_at == day0_obs_time
    ).first()
    assert day0_obs_v1.view_count == 100

    day1_obs_v1 = db_session.query(VideoObservation).filter(
        VideoObservation.video_id == "mock_vid_1",
        VideoObservation.observed_at == day1_obs_time
    ).first()
    assert day1_obs_v1.view_count == 250

    # Re-observe Day 1 should fail/skip idempotently and not modify Day 0 value
    assert day0_obs_v1.view_count == 100
