from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.models import Video, VideoObservation, PopulationMember, PopulationRun, Channel
from app.services.youtube_api import YouTubeService

class ObservationEngine:
    def __init__(self, youtube_service: YouTubeService):
        self.youtube = youtube_service

    def run_observation(self, observation_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Runs the routine observation job for all currently active population members.
        Optional observation_time override (useful for backfills/E2E testing).
        """
        db = SessionLocal()
        obs_time = observation_time or datetime.now(timezone.utc)
        
        try:
            # 1. Fetch all active video IDs that belong to a selected population
            # We select all video_ids present in active population members
            # In a real environment, we'd query population_members from the latest population runs
            query = select(PopulationMember.video_id).distinct()
            active_video_ids = [row[0] for row in db.execute(query).all()]
            
            if not active_video_ids:
                logger.info("No active population members found to observe.")
                return {"status": "success", "observed_count": 0, "failed_count": 0}
                
            logger.info(f"Starting observation for {len(active_video_ids)} active videos.")
            
            # 2. Batch retrieve video details (views, likes, comments, channel_id)
            video_details = self.youtube.get_videos_details(active_video_ids)
            details_map = {v["video_id"]: v for v in video_details}
            
            # 3. Retrieve channel subscriber counts for channels of these videos
            channel_ids = list(set([v["channel_id"] for v in video_details if v.get("channel_id")]))
            channels_details = self.youtube.get_channels_details(channel_ids)
            channel_sub_map = {c["channel_id"]: c["subscriber_count"] for c in channels_details}
            
            # 4. Check for videos that are missing from the API response (deleted/private)
            missing_video_ids = set(active_video_ids) - set(details_map.keys())
            for missing_id in missing_video_ids:
                logger.warning(f"Video {missing_id} was not returned by YouTube API (possibly private or deleted).")
                # Mark status in canonical videos table
                video = db.query(Video).filter(Video.video_id == missing_id).first()
                if video:
                    video.status = "missing"
                    video.last_seen_at = obs_time
                    db.add(video)
            
            db.commit()

            observed_count = 0
            failed_count = 0
            
            # 5. Insert observations immutably
            for v_id, details in details_map.items():
                chan_id = details.get("channel_id")
                sub_count = channel_sub_map.get(chan_id) if chan_id else None
                
                # Fetch video published_at to compute video age
                video_obj = db.query(Video).filter(Video.video_id == v_id).first()
                published_at = video_obj.published_at if video_obj else None
                
                age_seconds = None
                if published_at:
                    # Make sure published_at is timezone-aware
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                    age_seconds = int((obs_time - published_at).total_seconds())

                # Update channel last_observed_at & sub_count in DB if channel exists
                if chan_id:
                    channel_obj = db.query(Channel).filter(Channel.channel_id == chan_id).first()
                    if channel_obj:
                        channel_obj.subscriber_count = sub_count or channel_obj.subscriber_count
                        channel_obj.last_observed_at = obs_time
                        db.add(channel_obj)

                # Update video last_seen_at in DB
                if video_obj:
                    video_obj.last_seen_at = obs_time
                    db.add(video_obj)
                
                # Create observation record
                observation = VideoObservation(
                    video_id=v_id,
                    observed_at=obs_time,
                    view_count=details.get("view_count") if details.get("view_count") is not None else 0, # Should not be null but default to 0 if YouTube hides views (rare)
                    like_count=details.get("like_count"),
                    comment_count=details.get("comment_count"),
                    subscriber_count=sub_count,
                    video_age_seconds=age_seconds,
                    api_source="mock" if self.youtube.use_mock else "youtube_data_api",
                    request_id=None
                )
                
                # We handle duplicates/idempotency by catching IntegrityError
                # since we have a unique constraint on (video_id, observed_at)
                try:
                    db.add(observation)
                    db.flush()  # Push to DB to check constraint
                    observed_count += 1
                except IntegrityError:
                    db.rollback()
                    logger.info(f"Duplicate observation detected for video {v_id} at {obs_time}. Skipping (Idempotency).")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to save observation for video {v_id}: {e}")
                    failed_count += 1
            
            db.commit()
            logger.info(f"Observation completed. Observed: {observed_count}, Failed: {failed_count}.")
            return {
                "status": "success",
                "observed_count": observed_count,
                "failed_count": failed_count
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Fatal error in observation job: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            db.close()
