import time
import numpy as np
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from langdetect import detect

from app.core.config import settings
from app.core.logging import logger
from app.models.models import Concept, ConceptDailySignal, ApiRequestLog
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService

def is_english(title: str, description: str) -> bool:
    """Helper to detect if title and description are in English."""
    text = f"{title} {description}".strip()
    if not text:
        return False
    try:
        lang = detect(text)
        return lang == "en"
    except Exception as e:
        logger.warning(f"Language detection failed for text: '{text[:50]}...'. Error: {e}")
        return False

class PipelineEngine:
    def __init__(self, youtube_service: YouTubeService, semantic_service: SemanticService):
        self.youtube = youtube_service
        self.semantic = semantic_service

    def get_target_window(self, target_date: date) -> Tuple[datetime, datetime]:
        """Calculates 24h UTC window for D-3 lag date."""
        start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=24) - timedelta(seconds=1)
        return start, end

    def execute_concept_run(self, db: Session, concept_id: str, execution_date: Optional[date] = None) -> Dict[str, Any]:
        """Executes the daily intelligence extraction pipeline for a single concept."""
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise ValueError(f"Concept with ID {concept_id} not found in database.")

        if not execution_date:
            execution_date = datetime.now(timezone.utc).date()

        # D-3 Lag target date
        target_date = execution_date - timedelta(days=settings.lag_days)
        window_start, window_end = self.get_target_window(target_date)

        logger.info(
            f"=== RUNNING PIPELINE: Concept '{concept.name}' (ID: {concept.id}) on {execution_date} "
            f"for video publication window: {window_start.isoformat()} -> {window_end.isoformat()} ==="
        )

        # 1. Search YouTube (max 40 candidates)
        # Construct the query utilizing build_query (OR terms and exclusion)
        q = YouTubeService.build_query(concept.include_terms, concept.exclude_terms)
        logger.info(f"Generated YouTube Search query: '{q}'")

        raw_candidates = []
        try:
            raw_candidates = self.youtube.search_videos(
                query=q,
                limit=settings.search_max_results,
                published_after=window_start,
                published_before=window_end
            )
        except Exception as e:
            logger.error(f"YouTube search failed for concept '{concept.name}': {e}")
            # Persist zero signal to DB
            return self._persist_empty_run(db, concept, execution_date, target_date, "youtube_search_failed")

        raw_search_size = len(raw_candidates)
        logger.info(f"Retrieved {raw_search_size} raw candidate videos from YouTube search.")

        if raw_search_size == 0:
            return self._persist_empty_run(db, concept, execution_date, target_date, "no_search_results")

        # 2. Retrieve detailed statistics (views, likes, comments, subscriber counts)
        video_ids = [v["video_id"] for v in raw_candidates]
        channel_ids = list(set([v["channel_id"] for v in raw_candidates]))

        video_stats = {}
        channel_stats = {}
        try:
            video_stats = self.youtube.get_videos_details(video_ids)
            # Map into a dict for easy lookup
            video_details_map = {item["video_id"]: item for item in video_stats}
            
            channel_stats = self.youtube.get_channels_details(channel_ids)
            channel_details_map = {item["channel_id"]: item for item in channel_stats}
        except Exception as e:
            logger.error(f"Failed to fetch metadata details for videos/channels: {e}")
            return self._persist_empty_run(db, concept, execution_date, target_date, "metadata_fetching_failed")

        # 3. Filtering Stage
        # Initialize counts and reasons for auditing
        after_raw_filter_count = 0
        after_lang_filter_count = 0
        after_semantic_filter_count = 0

        rejected_by_views = 0
        rejected_by_subscribers = 0
        rejected_by_duration = 0
        rejected_by_description = 0
        rejected_by_language = 0
        rejected_by_semantic_threshold = 0
        rejected_by_missing_stats = 0

        processed_videos = []

        for cand in raw_candidates:
            v_id = cand["video_id"]
            details = video_details_map.get(v_id)
            c_id = cand["channel_id"]
            c_details = channel_details_map.get(c_id)

            if not details or not c_details:
                rejected_by_missing_stats += 1
                continue

            # Merge stats
            views = details.get("view_count", 0)
            subs = c_details.get("subscriber_count", 0)
            duration = details.get("duration_seconds", 0)
            title = details.get("title", "")
            description = details.get("description", "")
            likes = details.get("like_count", 0)
            comments = details.get("comment_count", 0)

            # --- Stage 1: Hard Filter Gate ---
            if views < settings.min_views:
                rejected_by_views += 1
                continue
            if subs < settings.min_subscribers:
                rejected_by_subscribers += 1
                continue
            if duration < settings.min_duration_seconds:
                rejected_by_duration += 1
                continue
            if len(description or "") < settings.min_description_chars:
                rejected_by_description += 1
                continue

            after_raw_filter_count += 1

            # --- Stage 2: Language Filtering ---
            if not is_english(title, description):
                rejected_by_language += 1
                continue

            after_lang_filter_count += 1

            # --- Stage 3: Semantic Concept Identity Filtering ---
            # Compare concept.name against video title + video description[:300]
            # Videos that fail to match the semantic model for this concept are filtered out
            video_text = f"{title} {description[:300]}"
            try:
                score = self.semantic.compute_similarity(concept.name, video_text)
            except Exception as e:
                logger.error(f"Semantic scoring explicitly failed for video {v_id}: {e}")
                # Re-raise to fail the entire run explicitly
                raise e

            if score <= settings.semantic_score_threshold:
                rejected_by_semantic_threshold += 1
                continue

            after_semantic_filter_count += 1

            # Video survived all filters - add to final population list
            processed_videos.append({
                "video_id": v_id,
                "channel_id": c_id,
                "title": title,
                "description": description,
                "published_at": details.get("published_at"),
                "view_count": views,
                "like_count": likes,
                "comment_count": comments,
                "subscriber_count": subs,
                "duration": duration,
                "semantic_score": score
            })

        final_population_size = len(processed_videos)
        logger.info(f"Final population size: {final_population_size} videos survived all filters.")

        filter_audit_log = {
            "raw_search_size": raw_search_size,
            "after_raw_filter": after_raw_filter_count,
            "after_language_filter": after_lang_filter_count,
            "after_semantic_filter": after_semantic_filter_count,
            "rejections": {
                "rejected_by_views": rejected_by_views,
                "rejected_by_subscribers": rejected_by_subscribers,
                "rejected_by_duration": rejected_by_duration,
                "rejected_by_description": rejected_by_description,
                "rejected_by_language": rejected_by_language,
                "rejected_by_semantic_threshold": rejected_by_semantic_threshold,
                "rejected_by_missing_stats": rejected_by_missing_stats
            }
        }

        if final_population_size == 0:
            return self._persist_empty_run(
                db, concept, execution_date, target_date, "no_surviving_candidates", filter_audit_log
            )

        # 4. Relative Channel Bucketing (SMALL, MEDIUM, BIG)
        subs_list = [v["subscriber_count"] for v in processed_videos]
        q25 = float(np.percentile(subs_list, 25))
        q75 = float(np.percentile(subs_list, 75))

        small_count = 0
        medium_count = 0
        big_count = 0

        for v in processed_videos:
            sub_c = v["subscriber_count"]
            if sub_c < q25:
                tier = "small"
                small_count += 1
            elif sub_c < q75:
                tier = "medium"
                medium_count += 1
            else:
                tier = "big"
                big_count += 1
            v["channel_tier"] = tier

        # 5. Engagement Metrics & Composite Trend Score Calculation
        for v in processed_videos:
            subs = v["subscriber_count"]
            views = v["view_count"]
            likes = v["like_count"]
            comments = v["comment_count"]
            score = v["semantic_score"]

            # Safe Division: Reach ratio = (view count / subscribers) / 100
            rr = float((views / subs) / 100) if subs > 0 else 0.0
            # Interaction density = (likes + comments) / view
            id_density = float((likes + comments) / views) if views > 0 else 0.0

            v["reach_ratio"] = rr
            v["interaction_density"] = id_density

            # Composite Trend Score (0 - 100 Scale)
            norm_reach = min(100.0, rr * 50.0)
            norm_interaction = min(100.0, id_density * 1000.0)
            norm_semantic = float(score * 100.0)
            
            trend_score = round(0.45 * norm_reach + 0.35 * norm_interaction + 0.20 * norm_semantic, 2)
            v["trend_score"] = trend_score

        # Aggregated Daily Medians & Means
        reach_ratios = [v["reach_ratio"] for v in processed_videos]
        interaction_densities = [v["interaction_density"] for v in processed_videos]
        semantic_scores = [v["semantic_score"] for v in processed_videos]
        trend_scores = [v["trend_score"] for v in processed_videos]

        reach_ratio_median = float(np.median(reach_ratios))
        interaction_density_median = float(np.median(interaction_densities))
        semantic_score_mean = float(np.mean(semantic_scores))
        trend_score_median = float(np.median(trend_scores))

        # 6. Statistical Outlier Detection (μ + 2σ)
        high_variance_flags = []
        if final_population_size >= 2:
            mean_rr = np.mean(reach_ratios)
            std_rr = np.std(reach_ratios)
            
            mean_id = np.mean(interaction_densities)
            std_id = np.std(interaction_densities)

            for v in processed_videos:
                is_rr_outlier = v["reach_ratio"] > (mean_rr + 2 * std_rr) if std_rr > 0 else False
                is_id_outlier = v["interaction_density"] > (mean_id + 2 * std_id) if std_id > 0 else False
                
                v["reach_ratio_outlier"] = bool(is_rr_outlier)
                v["interaction_density_outlier"] = bool(is_id_outlier)

                if is_rr_outlier or is_id_outlier:
                    high_variance_flags.append({
                        "video_id": v["video_id"],
                        "title": v["title"],
                        "reach_ratio": v["reach_ratio"],
                        "reach_ratio_outlier": bool(is_rr_outlier),
                        "interaction_density": v["interaction_density"],
                        "interaction_density_outlier": bool(is_id_outlier),
                        "channel_tier": v["channel_tier"],
                        "trend_score": v["trend_score"]
                    })
        else:
            # Under 2 videos, cannot compute standard deviation
            for v in processed_videos:
                v["reach_ratio_outlier"] = False
                v["interaction_density_outlier"] = False

        # 7. Top Outlier Selection
        top_outlier = None
        if high_variance_flags:
            # Consistently choose the flagged outlier with the maximum reach_ratio
            high_variance_flags.sort(key=lambda x: x["reach_ratio"], reverse=True)
            top_outlier = high_variance_flags[0]

        top_outlier_video_id = top_outlier["video_id"] if top_outlier else None
        top_outlier_reach_ratio = top_outlier["reach_ratio"] if top_outlier else None
        top_outlier_interaction_density = top_outlier["interaction_density"] if top_outlier else None
        top_outlier_semantic_score = next((v["semantic_score"] for v in processed_videos if v["video_id"] == top_outlier_video_id), None) if top_outlier else None
        top_outlier_channel_tier = top_outlier["channel_tier"] if top_outlier else None

        # 8. Outlier Streak Calculation
        outlier_streak = 0
        if top_outlier_video_id:
            # Query previous run's record
            prev_signal = db.query(ConceptDailySignal).filter(
                ConceptDailySignal.concept_id == concept.id
            ).order_by(ConceptDailySignal.video_date.desc()).first()

            if prev_signal and prev_signal.top_outlier_video_id == top_outlier_video_id:
                outlier_streak = prev_signal.outlier_streak + 1
            else:
                outlier_streak = 1
        else:
            outlier_streak = 0

        # Keywords: list of titles of all videos in final population
        keywords = [v["title"] for v in processed_videos]

        # Save Daily Signal Record
        daily_signal = ConceptDailySignal(
            concept_id=concept.id,
            concept_name=concept.name,
            processed_at=datetime.now(timezone.utc),
            video_date=target_date,
            population_size=final_population_size,
            
            reach_ratio_median=reach_ratio_median,
            interaction_density_median=interaction_density_median,
            semantic_score_mean=semantic_score_mean,
            trend_score_median=trend_score_median,
            
            top_outlier_video_id=top_outlier_video_id,
            top_outlier_reach_ratio=top_outlier_reach_ratio,
            top_outlier_interaction_density=top_outlier_interaction_density,
            top_outlier_semantic_score=top_outlier_semantic_score,
            top_outlier_channel_tier=top_outlier_channel_tier,
            outlier_streak=outlier_streak,
            
            big_channel_count=big_count,
            medium_channel_count=medium_count,
            small_channel_count=small_count,
            
            keywords=keywords,
            population=processed_videos,
            high_variance_flags=high_variance_flags,
            filter_audit=filter_audit_log
        )

        try:
            # Delete any existing record for same concept & video_date to enforce unique constraint
            db.query(ConceptDailySignal).filter(
                ConceptDailySignal.concept_id == concept.id,
                ConceptDailySignal.video_date == target_date
            ).delete()

            db.add(daily_signal)
            db.commit()
            db.refresh(daily_signal)
            logger.info(f"√ Daily Concept Signal record successfully written to DB (ID: {daily_signal.id})")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist ConceptDailySignal database record: {e}")
            raise e

        return {
            "status": "success",
            "concept_id": concept.id,
            "video_date": target_date.isoformat(),
            "population_size": final_population_size,
            "outlier_streak": outlier_streak
        }

    def _persist_empty_run(self, db: Session, concept: Concept, execution_date: date, 
                            target_date: date, reason: str, filter_audit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Utility to write an appropriate zero-population daily signal record on extraction failures or empty search results."""
        logger.warning(f"Pipeline running for concept '{concept.name}' on {execution_date} returned a zero population. Reason: {reason}")
        
        daily_signal = ConceptDailySignal(
            concept_id=concept.id,
            concept_name=concept.name,
            processed_at=datetime.now(timezone.utc),
            video_date=target_date,
            population_size=0,
            
            reach_ratio_median=None,
            interaction_density_median=None,
            semantic_score_mean=None,
            
            top_outlier_video_id=None,
            top_outlier_reach_ratio=None,
            top_outlier_interaction_density=None,
            top_outlier_semantic_score=None,
            top_outlier_channel_tier=None,
            outlier_streak=0,
            
            big_channel_count=0,
            medium_channel_count=0,
            small_channel_count=0,
            
            keywords=[],
            population=[],
            high_variance_flags=[],
            filter_audit=filter_audit or {"raw_search_size": 0, "after_raw_filter": 0, "rejections": {}, "reason": reason}
        )
        try:
            db.query(ConceptDailySignal).filter(
                ConceptDailySignal.concept_id == concept.id,
                ConceptDailySignal.video_date == target_date
            ).delete()
            db.add(daily_signal)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to write zero-population record: {e}")
        
        return {
            "status": "zero_population",
            "concept_id": concept.id,
            "video_date": target_date.isoformat(),
            "population_size": 0,
            "reason": reason
        }
