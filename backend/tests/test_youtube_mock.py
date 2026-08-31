import pytest
from datetime import datetime, timezone, date, timedelta
from app.core import database
from app.models.models import Concept, ConceptDailySignal
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine

class FailureMockProvider:
    """Mock provider simulating partial details failures where V3 and V5 details are missing."""
    def __init__(self):
        pass

    def search_videos(self, query, limit, published_after=None, published_before=None):
        return [
            {"video_id": f"mock_vid_{i}", "channel_id": f"mock_channel_{i}"}
            for i in range(1, 6)
        ]

    def get_videos_details(self, video_ids):
        # Return details only for V1, V2, V4 (V3 and V5 details are omitted)
        results = []
        for vid in video_ids:
            if vid in ["mock_vid_1", "mock_vid_2", "mock_vid_4"]:
                results.append({
                    "video_id": vid,
                    "title": f"Mock Video Title {vid} - AI Agents complete automation",
                    "description": "This is a detailed video description of AI agents and workflow automation that is at least 30 characters long.",
                    "channel_id": f"mock_channel_{vid.split('_')[-1]}",
                    "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "duration_seconds": 120,
                    "view_count": 500,
                    "like_count": 20,
                    "comment_count": 5
                })
        return results

    def get_channels_details(self, channel_ids):
        return [
            {"channel_id": cid, "subscriber_count": 1000} for cid in channel_ids
        ]

def test_partial_metadata_failures(db_session):
    """
    Verifies that when some video details are missing, they are skipped
    and tracked in the filter audit log, while surviving videos proceed successfully.
    """
    database.SessionLocal = lambda: db_session

    provider = FailureMockProvider()
    yt_service = YouTubeService(use_mock=True, mock_provider=provider)
    sem_service = SemanticService()
    sem_service.compute_similarity = lambda t1, t2: 0.8

    engine = PipelineEngine(yt_service, sem_service)
    concept = db_session.query(Concept).first()
    assert concept is not None

    base_date = date(2026, 8, 19)

    res = engine.execute_concept_run(db_session, concept.id, base_date)
    assert res["status"] == "success"
    assert res["population_size"] == 3  # V1, V2, V4 survived. V3, V5 details missing

    # Check daily signal database state
    sig = db_session.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept.id,
        ConceptDailySignal.video_date == base_date - timedelta(days=3)
    ).first()
    assert sig is not None
    assert sig.population_size == 3
    
    # Audit log should show 2 rejections due to missing stats
    audit = sig.filter_audit
    assert audit["rejections"]["rejected_by_missing_stats"] == 2
