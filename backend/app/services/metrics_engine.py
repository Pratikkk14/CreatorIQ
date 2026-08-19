from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, desc
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.models import VideoObservation, VideoMetric, Video

class MetricsEngine:
    def calculate_metrics_for_observation(self, db_session, obs: VideoObservation) -> VideoMetric:
        """
        Calculates derived metrics for a specific observation.
        Uses database queries to find t-1 and t-2 observations of the same video.
        """
        video_id = obs.video_id
        
        # 1. Fetch t-1 observation (immediately preceding obs)
        t_minus_1 = db_session.query(VideoObservation).filter(
            VideoObservation.video_id == video_id,
            VideoObservation.observed_at < obs.observed_at
        ).order_index = desc(VideoObservation.observed_at)
        
        # Corrected query formatting
        prev_obs = db_session.query(VideoObservation).filter(
            VideoObservation.video_id == video_id,
            VideoObservation.observed_at < obs.observed_at
        ).order_by(desc(VideoObservation.observed_at)).first()

        # 2. Fetch t-2 observation (preceding t-1)
        prev_prev_obs = None
        if prev_obs:
            prev_prev_obs = db_session.query(VideoObservation).filter(
                VideoObservation.video_id == video_id,
                VideoObservation.observed_at < prev_obs.observed_at
            ).order_by(desc(VideoObservation.observed_at)).first()

        # Basic values
        age_seconds = obs.video_age_seconds or 0
        age_days = age_seconds / (24.0 * 3600.0) if age_seconds > 0 else 0.001
        
        views = obs.view_count
        likes = obs.like_count or 0
        comments = obs.comment_count or 0
        subs = obs.subscriber_count or 0

        # Calculations
        views_per_day = views / max(age_days, 0.001)
        
        # Velocity and Growth (requires t-1)
        view_velocity = None
        view_growth = None
        if prev_obs:
            view_velocity = float(views - prev_obs.view_count)
            if prev_obs.view_count > 0:
                view_growth = float(view_velocity / prev_obs.view_count)
            else:
                view_growth = 0.0
                
        # Acceleration (requires t-2)
        view_acceleration = None
        if prev_obs and prev_prev_obs:
            prev_velocity = float(prev_obs.view_count - prev_prev_obs.view_count)
            if view_velocity is not None:
                view_acceleration = float(view_velocity - prev_velocity)

        # Subscriber-based metrics
        views_per_subscriber = None
        normalized_velocity = None
        reach_ratio = None
        if subs > 0:
            views_per_subscriber = float(views / subs)
            reach_ratio = views_per_subscriber  # reach_ratio is equivalent to views_per_subscriber
            if view_velocity is not None:
                # view_velocity normalized by subscriber count
                normalized_velocity = float(view_velocity / subs)

        # Interaction density: (likes + comments) / views
        interaction_density = None
        if views > 0:
            interaction_density = float((likes + comments) / views)

        # Create or update metrics row
        metric = VideoMetric(
            video_id=video_id,
            observation_id=obs.id,
            age_days=age_days,
            views_per_day=views_per_day,
            view_velocity=view_velocity,
            view_growth=view_growth,
            view_acceleration=view_acceleration,
            views_per_subscriber=views_per_subscriber,
            normalized_velocity=normalized_velocity,
            reach_ratio=reach_ratio,
            interaction_density=interaction_density,
            created_at=datetime.now(timezone.utc)
        )
        return metric

    def run_metrics_generation(self) -> Dict[str, Any]:
        """
        Processes all observations that do not yet have derived metrics.
        """
        db = SessionLocal()
        try:
            # Find all observations that do not have associated metrics
            # We perform a left outer join and filter where Metric.id is null
            subquery = db.query(VideoMetric.observation_id)
            unprocessed_obs = db.query(VideoObservation).filter(
                ~VideoObservation.id.in_(subquery)
            ).all()

            if not unprocessed_obs:
                logger.info("No unprocessed observations found for metrics generation.")
                return {"status": "success", "processed_count": 0}

            logger.info(f"Generating metrics for {len(unprocessed_obs)} unprocessed observations.")
            
            processed_count = 0
            for obs in unprocessed_obs:
                try:
                    metric = self.calculate_metrics_for_observation(db, obs)
                    db.add(metric)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to calculate metrics for observation {obs.id}: {e}")
                    
            db.commit()
            logger.info(f"Metrics generation completed. Processed: {processed_count}.")
            return {"status": "success", "processed_count": processed_count}
        except Exception as e:
            db.rollback()
            logger.error(f"Fatal error in metrics generation job: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            db.close()
