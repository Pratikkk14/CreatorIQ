from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from app.core.database import get_db, check_db_health
from app.core.config import settings, get_concepts_config
from app.models.models import (
    Concept, Video, VideoCandidate, PopulationMember, PopulationRun, 
    VideoObservation, VideoMetric, ConceptDailySignal, SearchRun, ApiRequestLog,
    Channel
)
from app.services import YouTubeService, SemanticService, SelectorService, DiscoveryEngine, ObservationEngine, MetricsEngine, AggregationEngine

router = APIRouter()

@router.get("/diagnostics")
def get_diagnostics(db: Session = Depends(get_db)):
    """
    Returns pipeline operational health diagnostic stats.
    """
    db_ok = check_db_health()
    yt_ok = bool(settings.youtube_api_key)
    
    # Counts
    concepts_count = db.query(Concept).count()
    videos_count = db.query(Video).count()
    candidates_count = db.query(VideoCandidate).count()
    members_count = db.query(PopulationMember).count()
    observations_count = db.query(VideoObservation).count()
    signals_count = db.query(ConceptDailySignal).count()
    
    # Failures count
    failures_count = db.query(ApiRequestLog).filter(ApiRequestLog.success == False).count()
    
    # Timestamps
    latest_obs = db.query(VideoObservation.observed_at).order_by(VideoObservation.observed_at.desc()).first()
    latest_sig = db.query(ConceptDailySignal.created_at).order_by(ConceptDailySignal.created_at.desc()).first()
    
    return {
        "database": "OK" if db_ok else "ERROR",
        "youtube_configuration": "OK" if yt_ok else "MISSING_KEY",
        "active_concepts": concepts_count,
        "videos": videos_count,
        "candidates": candidates_count,
        "population_members": members_count,
        "observations": observations_count,
        "signals": signals_count,
        "api_failures": failures_count,
        "latest_observation": latest_obs[0].isoformat() if latest_obs else None,
        "latest_signal": latest_sig[0].isoformat() if latest_sig else None
    }

@router.get("/concepts")
def list_concepts(db: Session = Depends(get_db)):
    return db.query(Concept).all()

@router.post("/concepts")
def create_concept(name: str, queries: List[str], description: Optional[str] = None, db: Session = Depends(get_db)):
    concept = Concept(name=name, search_queries=queries, description=description, active=True)
    try:
        db.add(concept)
        db.commit()
        db.refresh(concept)
        return concept
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/signals")
def get_signals(concept_id: int, start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_db)):
    query = db.query(ConceptDailySignal).filter(ConceptDailySignal.concept_id == concept_id)
    if start:
        query = query.filter(ConceptDailySignal.signal_date >= start)
    if end:
        query = query.filter(ConceptDailySignal.signal_date <= end)
    return query.order_by(ConceptDailySignal.signal_date.asc()).all()

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    search_runs = db.query(SearchRun).order_by(SearchRun.started_at.desc()).limit(20).all()
    pop_runs = db.query(PopulationRun).order_by(PopulationRun.started_at.desc()).limit(20).all()
    return {
        "search_runs": search_runs,
        "population_runs": pop_runs
    }

@router.get("/provenance")
def get_provenance(concept_id: int, target_date: date, db: Session = Depends(get_db)):
    """
    Traces the lineage of a daily concept signal back to the contributing videos and observations.
    """
    signal = db.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept_id,
        ConceptDailySignal.signal_date == target_date
    ).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Daily signal not found for this concept and date.")

    # Trace through population run
    pop_run = db.query(PopulationRun).filter(
        PopulationRun.concept_id == concept_id,
        PopulationRun.status == "success"
    ).order_by(PopulationRun.started_at.desc()).first()
    
    if not pop_run:
        return {"signal": signal, "contributions": []}

    members = db.query(PopulationMember).filter(
        PopulationMember.population_run_id == pop_run.id
    ).all()
    
    video_ids = [m.video_id for m in members]
    member_map = {m.video_id: m for m in members}

    # Query observations on this date
    start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)
    
    observations = db.query(VideoObservation).filter(
        VideoObservation.video_id.in_(video_ids),
        VideoObservation.observed_at >= start_dt,
        VideoObservation.observed_at <= end_dt
    ).all()
    
    obs_ids = [o.id for o in observations]
    obs_map = {o.video_id: o for o in observations}

    # Metrics
    metrics = db.query(VideoMetric).filter(
        VideoMetric.observation_id.in_(obs_ids)
    ).all()
    metrics_map = {m.video_id: m for m in metrics}

    # Video & Channel details
    videos = db.query(Video).filter(Video.video_id.in_(video_ids)).all()
    video_map = {v.video_id: v for v in videos}

    contributions = []
    for vid in video_ids:
        v_obj = video_map.get(vid)
        m_obj = member_map.get(vid)
        o_obj = obs_map.get(vid)
        met_obj = metrics_map.get(vid)
        
        contributions.append({
            "video_id": vid,
            "title": v_obj.title if v_obj else "Unknown",
            "creator_bucket": m_obj.creator_size_bucket if m_obj else "medium",
            "selection_score": m_obj.selection_score if m_obj else None,
            "selection_rank": m_obj.rank if m_obj else None,
            "observed": o_obj is not None,
            "view_count": o_obj.view_count if o_obj else None,
            "view_velocity": met_obj.view_velocity if met_obj else None,
            "view_growth": met_obj.view_growth if met_obj else None,
            "normalized_velocity": met_obj.normalized_velocity if met_obj else None,
            "reach_ratio": met_obj.reach_ratio if met_obj else None,
            "interaction_density": met_obj.interaction_density if met_obj else None
        })

    return {
        "signal": signal,
        "population_run_id": pop_run.id,
        "contributions": contributions
    }

# Background pipeline execution helper
def execute_pipeline_task(stage: str):
    db = SessionLocal()
    try:
        # Initialize engines
        yt = YouTubeService(use_mock=False) # Will fallback to mock if no keys
        sem = SemanticService()
        sel = SelectorService()
        
        disc_eng = DiscoveryEngine(yt, sem, sel)
        obs_eng = ObservationEngine(yt)
        met_eng = MetricsEngine()
        agg_eng = AggregationEngine()
        
        if stage == "discover":
            disc_eng.run_discovery()
        elif stage == "observe":
            obs_eng.run_observation()
        elif stage == "metrics":
            met_eng.run_metrics_generation()
        elif stage == "signals":
            agg_eng.run_aggregation()
        elif stage == "run":
            disc_eng.run_discovery()
            obs_eng.run_observation()
            met_eng.run_metrics_generation()
            agg_eng.run_aggregation()
    except Exception as e:
        logger.error(f"Background pipeline stage '{stage}' execution failed: {e}")
    finally:
        db.close()

@router.post("/pipeline/run")
def trigger_pipeline(stage: str, background_tasks: BackgroundTasks):
    """
    Triggers a pipeline stage in the background. Valid stages: discover, observe, metrics, signals, run.
    """
    valid_stages = ["discover", "observe", "metrics", "signals", "run"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid pipeline stage. Must be one of {valid_stages}")
        
    background_tasks.add_task(execute_pipeline_task, stage)
    return {"status": "accepted", "message": f"Pipeline stage '{stage}' triggered in background."}


@router.get("/diagnostics/raw-data")
def get_raw_data_summary(db: Session = Depends(get_db)):
    """
    Returns a summary mapping table names to their current row count in the database.
    """
    table_map = {
        "concepts": Concept,
        "channels": Channel,
        "videos": Video,
        "search_runs": SearchRun,
        "video_candidates": VideoCandidate,
        "population_runs": PopulationRun,
        "population_members": PopulationMember,
        "video_observations": VideoObservation,
        "video_metrics": VideoMetric,
        "concept_daily_signals": ConceptDailySignal,
        "api_request_logs": ApiRequestLog
    }
    
    summary = {}
    for name, model in table_map.items():
        summary[name] = db.query(model).count()
        
    return summary


@router.get("/diagnostics/raw-data/{table_name}")
def get_raw_table_data(table_name: str, limit: int = 200, db: Session = Depends(get_db)):
    """
    Returns up to `limit` rows of raw data from the specified table.
    """
    table_map = {
        "concepts": Concept,
        "channels": Channel,
        "videos": Video,
        "search_runs": SearchRun,
        "video_candidates": VideoCandidate,
        "population_runs": PopulationRun,
        "population_members": PopulationMember,
        "video_observations": VideoObservation,
        "video_metrics": VideoMetric,
        "concept_daily_signals": ConceptDailySignal,
        "api_request_logs": ApiRequestLog
    }
    
    if table_name not in table_map:
        raise HTTPException(
            status_code=404, 
            detail=f"Table '{table_name}' not found. Valid tables are: {list(table_map.keys())}"
        )
        
    model = table_map[table_name]
    rows = db.query(model).limit(limit).all()
    
    data = []
    for r in rows:
        r_dict = dict(r.__dict__)
        r_dict.pop("_sa_instance_state", None)
        data.append(r_dict)
        
    return {
        "table": table_name,
        "count": len(data),
        "limit": limit,
        "data": data
    }
