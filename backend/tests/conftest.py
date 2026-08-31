import pytest
import os
import sys
from typing import List
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 1. Override the database settings to use SQLite before importing database/models/services
from app.core.config import settings
settings.database_url = "sqlite:///:memory:"
settings.postgres_db = "sqlite:///:memory:"

# 2. Import database module and re-initialize it for tests
from app.core import database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=test_engine)

# Re-bind the core database module session and engine references
database.engine = test_engine
database.SessionLocal = TestingSessionLocal

from app.models.models import Concept

@pytest.fixture(name="db_session", scope="function")
def fixture_db_session():
    # Create all tables in the test engine
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    
    # Seed default concept
    concept = Concept(
        id=1,
        name="AI Agents",
        description="Monitors agentic AI workflows, frameworks, and LLM automation tools",
        active=True,
        include_terms=["AI agents", "agentic AI", "AI automation"],
        exclude_terms=[]
    )
    session.add(concept)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables on teardown to isolate tests
        Base.metadata.drop_all(bind=test_engine)

class MockYouTubeProvider:
    """Mock provider matching YouTube API responses for E2E tests."""
    def __init__(self):
        self.day = 0
        # Set stats for each day (Day 0, Day 1, Day 2)
        # 5 videos selected in population
        self.video_stats_by_day = {
            0: {
                "mock_vid_1": {"views": 100, "likes": 5, "comments": 1, "subs": 5000}, # medium
                "mock_vid_2": {"views": 200, "likes": 10, "comments": 2, "subs": 100},   # small
                "mock_vid_3": {"views": 300, "likes": 15, "comments": 3, "subs": 100000}, # big
                "mock_vid_4": {"views": 400, "likes": 20, "comments": 4, "subs": 200},   # small
                "mock_vid_5": {"views": 500, "likes": 25, "comments": 5, "subs": 200000} # big
            },
            1: {
                "mock_vid_1": {"views": 250, "likes": 12, "comments": 3, "subs": 5000},
                "mock_vid_2": {"views": 350, "likes": 18, "comments": 4, "subs": 100},
                "mock_vid_3": {"views": 900, "likes": 45, "comments": 9, "subs": 100000},
                "mock_vid_4": {"views": 450, "likes": 22, "comments": 5, "subs": 200},
                "mock_vid_5": {"views": 1000, "likes": 50, "comments": 10, "subs": 200000}
            },
            2: {
                "mock_vid_1": {"views": 500, "likes": 25, "comments": 6, "subs": 5000},
                "mock_vid_2": {"views": 700, "likes": 35, "comments": 7, "subs": 100},
                "mock_vid_3": {"views": 1800, "likes": 90, "comments": 18, "subs": 100000},
                "mock_vid_4": {"views": 700, "likes": 35, "comments": 8, "subs": 200},
                "mock_vid_5": {"views": 2500, "likes": 120, "comments": 25, "subs": 200000}
            }
        }

    def search_videos(self, query: str, limit: int, published_after=None, published_before=None):
        # Return 12 candidate videos (Section 33 E2E test requirement)
        videos = []
        now = datetime.now(timezone.utc)
        
        # 12 candidates: mock_vid_1 to mock_vid_12
        for i in range(1, 13):
            video_id = f"mock_vid_{i}"
            # Make first 8 highly relevant, next 4 generic
            title = f"Building AI agents {i} - Complete Framework" if i <= 8 else f"Unrelated topic {i}"
            desc = "This is a search query candidate video description for agentic AI automation."
            videos.append({
                "video_id": video_id,
                "title": title,
                "description": desc,
                "channel_id": f"mock_channel_{i}",
                "channel_title": f"Creator Studio {i}",
                "published_at": (now - timedelta(days=2)).isoformat(),
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/default.jpg"
            })
        return videos[:limit]

    def get_videos_details(self, video_ids: List[str]):
        # Depending on current day, return statistics
        day_stats = self.video_stats_by_day.get(self.day, {})
        now = datetime.now(timezone.utc)
        
        results = []
        for vid in video_ids:
            stats = day_stats.get(vid, {"views": 10, "likes": 1, "comments": 0, "subs": 100})
            
            # Non-selected candidates (mock_vid_6 to mock_vid_12) get basic static values
            views = stats.get("views")
            likes = stats.get("likes")
            comments = stats.get("comments")
            
            results.append({
                "video_id": vid,
                "title": f"Mock Video Title {vid}",
                "description": "Mock video description detailing AI agents and workflows.",
                "channel_id": f"mock_channel_{vid.split('_')[-1]}",
                "published_at": (now - timedelta(days=2)).isoformat(),
                "duration_seconds": 360,
                "category_id": "27",
                "language": "en",
                "thumbnail_url": f"https://img.youtube.com/vi/{vid}/default.jpg",
                "view_count": views,
                "like_count": likes,
                "comment_count": comments
            })
        return results

    def get_channels_details(self, channel_ids: List[str]):
        results = []
        for cid in channel_ids:
            num = int(cid.split('_')[-1])
            vid_id = f"mock_vid_{num}"
            
            # Get subscriber count configured for this video
            sub_count = 100
            for d in [0, 1, 2]:
                if vid_id in self.video_stats_by_day[d]:
                    sub_count = self.video_stats_by_day[d][vid_id]["subs"]
                    break
            
            # Specific counts for candidate videos 6 to 12 to shape percentiles
            if sub_count == 100:
                mapping = {
                    6: 300,
                    7: 400,
                    8: 10000,
                    9: 20000,
                    10: 30000,
                    11: 300000,
                    12: 400000
                }
                sub_count = mapping.get(num, 100)
                
            results.append({
                "channel_id": cid,
                "title": f"Channel Title for {cid}",
                "subscriber_count": sub_count,
                "video_count": 42,
                "country": "US",
                "published_at": (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
            })
        return results
