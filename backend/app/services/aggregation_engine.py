from datetime import datetime, timezone, date, timedelta
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import select, func, and_
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.models import (
    Concept, PopulationRun, PopulationMember, VideoObservation, 
    VideoMetric, ConceptDailySignal, VideoCandidate
)

class AggregationEngine:
    def aggregate_concept_signals(self, concept_id: int, target_date: date) -> Optional[ConceptDailySignal]:
        """
        Aggregates metrics for a single concept on a specific date.
        """
        db = SessionLocal()
        try:
            # 1. Find the population members for this concept
            # We fetch the latest active population run for this concept
            pop_run = db.query(PopulationRun).filter(
                PopulationRun.concept_id == concept_id,
                PopulationRun.status == "success"
            ).order_by(PopulationRun.started_at.desc()).first()
            
            if not pop_run:
                logger.warning(f"No successful population run found for concept {concept_id}.")
                return None
                
            members = db.query(PopulationMember).filter(
                PopulationMember.population_run_id == pop_run.id
            ).all()
            
            if not members:
                logger.warning(f"No population members found for run {pop_run.id}.")
                return None

            video_ids = [m.video_id for m in members]
            member_bucket_map = {m.video_id: m.creator_size_bucket for m in members}
            
            # 2. Query all observations for these videos on target_date
            # We match the date of observed_at
            start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
            end_dt = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)
            
            observations = db.query(VideoObservation).filter(
                VideoObservation.video_id.in_(video_ids),
                VideoObservation.observed_at >= start_dt,
                VideoObservation.observed_at <= end_dt
            ).all()
            
            # Coverage calculation
            population_size = len(video_ids)
            received_obs_count = len(observations)
            coverage = float(received_obs_count / population_size) if population_size > 0 else 0.0
            
            if not observations:
                logger.warning(f"No observations found for concept {concept_id} on {target_date}.")
                # We can still register a signal with coverage = 0.0
                signal = ConceptDailySignal(
                    concept_id=concept_id,
                    signal_date=target_date,
                    population_size=population_size,
                    observation_coverage=coverage,
                    created_at=datetime.now(timezone.utc)
                )
                return self._upsert_signal(db, signal)
                
            obs_ids = [o.id for o in observations]
            obs_video_map = {o.id: o.video_id for o in observations}
            
            # 3. Retrieve derived metrics
            metrics = db.query(VideoMetric).filter(
                VideoMetric.observation_id.in_(obs_ids)
            ).all()
            
            if not metrics:
                logger.warning(f"No metrics calculated for observations on {target_date}.")
                signal = ConceptDailySignal(
                    concept_id=concept_id,
                    signal_date=target_date,
                    population_size=population_size,
                    observation_coverage=coverage,
                    created_at=datetime.now(timezone.utc)
                )
                return self._upsert_signal(db, signal)

            # 4. Extract lists for median/percentile calculations
            velocities = []
            growths = []
            accelerations = []
            norm_velocities = []
            reach_ratios = []
            interactions = []
            
            # Group velocities by creator bucket
            by_bucket = {"big": [], "medium": [], "small": []}
            
            for m in metrics:
                vid = obs_video_map.get(m.observation_id)
                bucket = member_bucket_map.get(vid, "medium")
                
                if m.view_velocity is not None:
                    velocities.append(m.view_velocity)
                    by_bucket[bucket].append(m.view_velocity)
                if m.view_growth is not None:
                    growths.append(m.view_growth)
                if m.view_acceleration is not None:
                    accelerations.append(m.view_acceleration)
                if m.normalized_velocity is not None:
                    norm_velocities.append(m.normalized_velocity)
                if m.reach_ratio is not None:
                    reach_ratios.append(m.reach_ratio)
                if m.interaction_density is not None:
                    interactions.append(m.interaction_density)

            # Compute aggregates safely (handling empty arrays)
            median_velocity = float(np.median(velocities)) if velocities else None
            median_growth = float(np.median(growths)) if growths else None
            median_acceleration = float(np.median(accelerations)) if accelerations else None
            median_norm_velocity = float(np.median(norm_velocities)) if norm_velocities else None
            median_reach = float(np.median(reach_ratios)) if reach_ratios else None
            median_interaction = float(np.median(interactions)) if interactions else None
            
            p25_vel = float(np.percentile(velocities, 25)) if velocities else None
            p75_vel = float(np.percentile(velocities, 75)) if velocities else None
            std_vel = float(np.std(velocities)) if velocities else None
            
            # Stratified signals (median velocity per bucket)
            big_signal = float(np.median(by_bucket["big"])) if by_bucket["big"] else None
            medium_signal = float(np.median(by_bucket["medium"])) if by_bucket["medium"] else None
            small_signal = float(np.median(by_bucket["small"])) if by_bucket["small"] else None

            # Create signal record
            signal = ConceptDailySignal(
                concept_id=concept_id,
                signal_date=target_date,
                population_size=population_size,
                observation_coverage=coverage,
                median_view_velocity=median_velocity,
                median_view_growth=median_growth,
                median_view_acceleration=median_acceleration,
                median_normalized_velocity=median_norm_velocity,
                median_reach_ratio=median_reach,
                median_interaction_density=median_interaction,
                p25_velocity=p25_vel,
                p75_velocity=p75_vel,
                velocity_std=std_vel,
                big_creator_signal=big_signal,
                medium_creator_signal=medium_signal,
                small_creator_signal=small_signal,
                created_at=datetime.now(timezone.utc)
            )
            
            return self._upsert_signal(db, signal)
            
        except Exception as e:
            logger.error(f"Failed to generate signal for concept {concept_id} on {target_date}: {e}")
            return None
        finally:
            db.close()

    def _upsert_signal(self, db, signal: ConceptDailySignal) -> ConceptDailySignal:
        """Helper to upsert a daily signal based on concept_id and signal_date."""
        existing = db.query(ConceptDailySignal).filter(
            ConceptDailySignal.concept_id == signal.concept_id,
            ConceptDailySignal.signal_date == signal.signal_date
        ).first()
        
        if existing:
            # Update fields
            existing.population_size = signal.population_size
            existing.observation_coverage = signal.observation_coverage
            existing.median_view_velocity = signal.median_view_velocity
            existing.median_view_growth = signal.median_view_growth
            existing.median_view_acceleration = signal.median_view_acceleration
            existing.median_normalized_velocity = signal.median_normalized_velocity
            existing.median_reach_ratio = signal.median_reach_ratio
            existing.median_interaction_density = signal.interaction_density_density if hasattr(signal, 'interaction_density_density') else signal.median_interaction_density
            existing.p25_velocity = signal.p25_velocity
            existing.p75_velocity = signal.p75_velocity
            existing.velocity_std = signal.velocity_std
            existing.big_creator_signal = signal.big_creator_signal
            existing.medium_creator_signal = signal.medium_creator_signal
            existing.small_creator_signal = signal.small_creator_signal
            existing.created_at = datetime.now(timezone.utc)
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            db.add(signal)
            db.commit()
            db.refresh(signal)
            return signal

    def run_aggregation(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Runs signal aggregation for all active concepts on the target date (default: yesterday).
        """
        db = SessionLocal()
        t_date = target_date or (datetime.now(timezone.utc) - timedelta(days=1)).date()
        
        try:
            active_concepts = db.query(Concept).filter(Concept.active == True).all()
            if not active_concepts:
                logger.info("No active concepts found for aggregation.")
                return {"status": "success", "processed_count": 0}
                
            processed_count = 0
            for concept in active_concepts:
                signal = self.aggregate_concept_signals(concept.id, t_date)
                if signal:
                    processed_count += 1
                    
            logger.info(f"Signal aggregation completed. Concepts processed: {processed_count} for date {t_date}.")
            return {"status": "success", "processed_count": processed_count, "date": str(t_date)}
        except Exception as e:
            logger.error(f"Fatal error in signal aggregation job: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            db.close()
