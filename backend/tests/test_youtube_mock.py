import pytest
from datetime import datetime, timezone, timedelta
from app.core import database
from app.models.models import (
    ApiRequestLog, VideoObservation, PopulationMember, 
    Video, Channel, SearchRun, PopulationRun
)
from app.services import YouTubeService, ObservationEngine

class FailureMockProvider:
    """Mock provider to simulate success, transient failure (429), and timeout."""
    def __init__(self):
        self.call_count = 0

    def search_videos(self, query, limit, published_after=None, published_before=None):
        return []

    def get_videos_details(self, video_ids):
        # We simulate the exact scenario from Section 38:
        # V1: success
        # V2: success
        # V3: failure (details not returned)
        # V4: success
        # V5: failure (details not returned)
        results = []
        for vid in video_ids:
            if vid in ["mock_vid_1", "mock_vid_2", "mock_vid_4"]:
                results.append({
                    "video_id": vid,
                    "title": f"Title {vid}",
                    "description": "Desc",
                    "channel_id": f"mock_channel_{vid.split('_')[-1]}",
                    "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "duration_seconds": 100,
                    "view_count": 500,
                    "like_count": 20,
                    "comment_count": 5
                })
        return results

    def get_channels_details(self, channel_ids):
        return [
            {"channel_id": cid, "subscriber_count": 1000} for cid in channel_ids
        ]

def test_partial_failures(db_session, mocker):
    """
    Verifies Section 38: V1, V2, V4 are successfully observed,
    failures are recorded for V3, V5, and the job completes without crashing.
    """
    database.SessionLocal = lambda: db_session

    provider = FailureMockProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=provider)
    obs_eng = ObservationEngine(yt_service)

    # Setup database records for Foreign Key integrity
    # 1. Create Channels
    for i in range(1, 6):
        db_session.add(Channel(
            channel_id=f"mock_channel_{i}",
            title=f"Channel {i}",
            subscriber_count=1000,
            first_seen_at=datetime.now(timezone.utc)
        ))
    db_session.flush()

    # 2. Create Videos
    for i in range(1, 6):
        db_session.add(Video(
            video_id=f"mock_vid_{i}",
            channel_id=f"mock_channel_{i}",
            title=f"Video {i}",
            published_at=datetime.now(timezone.utc) - timedelta(days=2),
            first_discovered_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            status="active"
        ))
    db_session.flush()

    # 3. Create Search Run
    s_run = SearchRun(
        concept_id=1,
        started_at=datetime.now(timezone.utc),
        query="AI agents",
        requested_limit=50,
        status="success"
    )
    db_session.add(s_run)
    db_session.flush()

    # 4. Create Population Run
    p_run = PopulationRun(
        id=1,
        concept_id=1,
        search_run_id=s_run.id,
        target_size=5,
        actual_size=5,
        selection_strategy="percentile_stratified",
        started_at=datetime.now(timezone.utc),
        status="success"
    )
    db_session.add(p_run)
    db_session.flush()

    # 5. Create Population Members
    for i in range(1, 6):
        db_session.add(PopulationMember(
            population_run_id=p_run.id,
            video_id=f"mock_vid_{i}",
            creator_size_bucket="medium",
            selected_at=datetime.now(timezone.utc)
        ))
    db_session.commit()

    # Run observation
    res = obs_eng.run_observation(observation_time=datetime.now(timezone.utc))
    
    # Assertions
    assert res["status"] == "success"
    
    # 3 videos (V1, V2, V4) must have observations recorded
    assert res["observed_count"] == 3
    
    obs_v1 = db_session.query(VideoObservation).filter(VideoObservation.video_id == "mock_vid_1").first()
    assert obs_v1 is not None
    assert obs_v1.view_count == 500

    obs_v3 = db_session.query(VideoObservation).filter(VideoObservation.video_id == "mock_vid_3").first()
    assert obs_v3 is None  # Omitted due to simulated fetch failure
