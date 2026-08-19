from datetime import datetime, timezone, timedelta
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select
from app.core.logging import logger
from app.core.database import SessionLocal
from app.core.config import get_pipeline_config, get_selection_config
from app.models.models import (
    Concept, SearchRun, VideoCandidate, Video, Channel, 
    PopulationRun, PopulationMember
)
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.selector import SelectorService

class DiscoveryEngine:
    def __init__(self, youtube_service: YouTubeService, semantic_service: SemanticService, selector_service: SelectorService):
        self.youtube = youtube_service
        self.semantic = semantic_service
        self.selector = selector_service

    def run_discovery_for_concept(self, concept: Concept, 
                                 published_after: datetime, 
                                 published_before: datetime) -> Optional[PopulationRun]:
        """
        Runs discovery, candidate ingestion, classification, and population selection for one concept.
        """
        db = SessionLocal()
        
        # Load configs
        pipeline_config = get_pipeline_config()
        limit = pipeline_config.get("discovery", {}).get("max_results_per_query", 50)
        selection_config = get_selection_config()
        target_pop_size = selection_config.get("target_population_size", 5)

        logger.info(f"Starting discovery for concept: '{concept.name}' between {published_after} and {published_before}.")

        raw_candidates_pool = []
        search_runs = []

        try:
            # 1. Execute Search Query for each query defined in the concept
            queries = concept.search_queries
            for query in queries:
                # Insert pending search run
                search_run = SearchRun(
                    concept_id=concept.id,
                    started_at=datetime.now(timezone.utc),
                    published_after=published_after,
                    published_before=published_before,
                    query=query,
                    requested_limit=limit,
                    status="pending"
                )
                db.add(search_run)
                db.commit()
                db.refresh(search_run)
                search_runs.append(search_run)

                try:
                    # Query YouTube API
                    found_videos = self.youtube.search_videos(
                        query=query,
                        limit=limit,
                        published_after=published_after,
                        published_before=published_before
                    )
                    
                    search_run.completed_at = datetime.now(timezone.utc)
                    search_run.returned_count = len(found_videos)
                    search_run.status = "success"
                    db.add(search_run)
                    
                    # Accumulate videos
                    for fv in found_videos:
                        fv["search_run_id"] = search_run.id
                        raw_candidates_pool.append(fv)
                        
                except Exception as e:
                    logger.error(f"Search query '{query}' failed: {e}")
                    search_run.completed_at = datetime.now(timezone.utc)
                    search_run.status = "failed"
                    search_run.error_message = str(e)
                    db.add(search_run)
            
            db.commit()

            if not raw_candidates_pool:
                logger.warning(f"No candidates found for concept '{concept.name}' search queries.")
                return None

            # Remove duplicates by video_id in this pool (keep first search run reference)
            seen_ids = set()
            dedup_pool = []
            for item in raw_candidates_pool:
                if item["video_id"] not in seen_ids:
                    seen_ids.add(item["video_id"])
                    dedup_pool.append(item)

            # 2. Query channel subscriber counts and other video details
            # This handles registers of video age, languages, categories, etc.
            video_ids = [v["video_id"] for v in dedup_pool]
            video_details = self.youtube.get_videos_details(video_ids)
            details_map = {v["video_id"]: v for v in video_details}
            
            channel_ids = list(set([v["channel_id"] for v in video_details if v.get("channel_id")]))
            channels_details = self.youtube.get_channels_details(channel_ids)
            channel_details_map = {c["channel_id"]: c for c in channels_details}

            # 3. Add canonical Channels & Videos (idempotent registry)
            # Create a dictionary representing all candidates data for Selector
            selector_candidates = []
            
            for item in dedup_pool:
                vid = item["video_id"]
                details = details_map.get(vid)
                if not details:
                    continue  # Video details failed to fetch
                
                chan_id = details.get("channel_id")
                chan_title = item.get("channel_title", "Unknown")
                chan_details = channel_details_map.get(chan_id)
                sub_count = chan_details.get("subscriber_count") if chan_details else 0
                
                # Check / register Channel
                channel_obj = db.query(Channel).filter(Channel.channel_id == chan_id).first()
                if not channel_obj:
                    channel_obj = Channel(
                        channel_id=chan_id,
                        title=chan_details.get("title") if chan_details else chan_title,
                        subscriber_count=sub_count,
                        video_count=chan_details.get("video_count") if chan_details else 0,
                        country=chan_details.get("country") if chan_details else None,
                        published_at=datetime.fromisoformat(chan_details.get("published_at").replace('Z', '+00:00')) if chan_details and chan_details.get("published_at") else None,
                        first_seen_at=datetime.now(timezone.utc),
                        last_observed_at=datetime.now(timezone.utc)
                    )
                    db.add(channel_obj)
                    db.flush()
                else:
                    # Update subscriber count if we saw a newer count
                    if sub_count > 0:
                        channel_obj.subscriber_count = sub_count
                    channel_obj.last_observed_at = datetime.now(timezone.utc)
                    db.add(channel_obj)

                # Check / register Video
                video_obj = db.query(Video).filter(Video.video_id == vid).first()
                published_dt = datetime.fromisoformat(details["published_at"].replace('Z', '+00:00'))
                
                if not video_obj:
                    video_obj = Video(
                        video_id=vid,
                        channel_id=chan_id,
                        title=details["title"],
                        description=details["description"],
                        published_at=published_dt,
                        duration_seconds=details.get("duration_seconds"),
                        category_id=details.get("category_id"),
                        language=details.get("language"),
                        thumbnail_url=details.get("thumbnail_url"),
                        first_discovered_at=datetime.now(timezone.utc),
                        last_seen_at=datetime.now(timezone.utc),
                        status="active"
                    )
                    db.add(video_obj)
                    db.flush()
                else:
                    video_obj.last_seen_at = datetime.now(timezone.utc)
                    db.add(video_obj)

                # 4. Semantic Relevance Scoring
                # Construct snippet: Title + Description
                snippet = f"{details['title']} {details['description'] or ''}"
                # Embed and compute similarity
                semantic_score = self.semantic.compute_similarity(concept.name, snippet)

                # Prepare payload for Selector
                selector_candidates.append({
                    "video_id": vid,
                    "search_run_id": item["search_run_id"],
                    "language": details.get("language"),
                    "subscriber_count": sub_count,
                    "semantic_score": semantic_score,
                    "title": details["title"]
                })

            db.commit()

            # 5. Creator Classification (Percentile-based relative buckets)
            classified_candidates = self.selector.classify_creator_sizes(selector_candidates)

            # 6. Deterministic Population Selection
            selected, rejected = self.selector.select_population(classified_candidates, target_pop_size)

            # 7. Persist Candidates to `video_candidates`
            all_processed_candidates = selected + rejected
            for ac in all_processed_candidates:
                candidate_obj = VideoCandidate(
                    search_run_id=ac["search_run_id"],
                    video_id=ac["video_id"],
                    semantic_score=ac.get("semantic_score"),
                    language_score=1.0 if ac.get("language") == "en" else 0.0,
                    metadata_score=1.0,
                    creator_size_bucket=ac.get("creator_size_bucket"),
                    selection_status=ac["selection_status"],
                    rejection_reason=ac.get("rejection_reason"),
                    evaluated_at=ac["evaluated_at"]
                )
                db.add(candidate_obj)
            
            db.commit()

            # 8. Register `population_run` and `population_members`
            # For this run, pick any search run ID as primary or map from search runs
            primary_search_run_id = search_runs[0].id if search_runs else None
            
            pop_run = PopulationRun(
                concept_id=concept.id,
                search_run_id=primary_search_run_id,
                target_size=target_pop_size,
                actual_size=len(selected),
                selection_strategy="percentile_stratified",
                started_at=datetime.now(timezone.utc),
                status="success"
            )
            db.add(pop_run)
            db.commit()
            db.refresh(pop_run)

            # Register members
            for index, member in enumerate(selected):
                member_obj = PopulationMember(
                    population_run_id=pop_run.id,
                    video_id=member["video_id"],
                    creator_size_bucket=member["creator_size_bucket"],
                    selection_score=member["selection_score"],
                    rank=member["selection_rank"],
                    selected_at=datetime.now(timezone.utc)
                )
                db.add(member_obj)

            pop_run.completed_at = datetime.now(timezone.utc)
            db.add(pop_run)
            db.commit()

            logger.info(f"Population Selection completed for concept '{concept.name}'. Selected: {len(selected)} members.")
            return pop_run

        except Exception as e:
            db.rollback()
            logger.error(f"Fatal error in run_discovery_for_concept: {e}")
            return None
        finally:
            db.close()

    def run_discovery(self, lookback_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Runs discovery pipeline for all active concepts.
        """
        db = SessionLocal()
        try:
            active_concepts = db.query(Concept).filter(Concept.active == True).all()
            if not active_concepts:
                logger.info("No active concepts found for discovery.")
                return {"status": "success", "runs_created": 0}

            # Setup lookback window
            days = lookback_days or get_pipeline_config().get("discovery", {}).get("lookback_days", 7)
            now = datetime.now(timezone.utc)
            published_after = now - timedelta(days=days)
            published_before = now

            processed_count = 0
            for concept in active_concepts:
                pop_run = self.run_discovery_for_concept(concept, published_after, published_before)
                if pop_run:
                    processed_count += 1
            
            return {
                "status": "success",
                "processed_concepts": len(active_concepts),
                "successful_selections": processed_count
            }
        except Exception as e:
            logger.error(f"Fatal error in run_discovery: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            db.close()
