from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from app.core.database import get_db, check_db_health
from app.core.config import settings
from sqlalchemy import func
from app.models.models import (
    Concept, ConceptDailySignal, ApiRequestLog
)
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine
from app.core.database import SessionLocal
from app.core.logging import logger

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
    signals_count = db.query(ConceptDailySignal).count()
    videos_count = db.query(func.sum(ConceptDailySignal.population_size)).scalar() or 0
    
    # Failures count
    failures_count = db.query(ApiRequestLog).filter(ApiRequestLog.success == False).count()
    
    # Timestamps
    latest_sig = db.query(ConceptDailySignal.created_at).order_by(ConceptDailySignal.created_at.desc()).first()
    
    return {
        "database": "OK" if db_ok else "ERROR",
        "youtube_configuration": "OK" if yt_ok else "MISSING_KEY",
        "active_concepts": concepts_count,
        "videos": videos_count,
        "candidates": videos_count,
        "population_members": videos_count,
        "observations": videos_count,
        "signals": signals_count,
        "api_failures": failures_count,
        "latest_observation": None,  # Obsolete under new pipeline architecture
        "latest_signal": latest_sig[0].isoformat() if latest_sig else None
    }

@router.get("/concepts")
def list_concepts(db: Session = Depends(get_db)):
    return db.query(Concept).all()

@router.post("/concepts")
def create_concept(name: str, queries: List[str], description: Optional[str] = None, db: Session = Depends(get_db)):
    # Map input queries as include_terms, with exclude_terms defaulting to an empty list
    concept = Concept(name=name, include_terms=queries, exclude_terms=[], description=description, active=True)
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
        query = query.filter(ConceptDailySignal.video_date >= start)
    if end:
        query = query.filter(ConceptDailySignal.video_date <= end)
    signals = query.order_by(ConceptDailySignal.video_date.asc()).all()
    
    # Map database ConceptDailySignal columns to JSON structure expected by React chart
    results = []
    for s in signals:
        results.append({
            "id": s.id,
            "concept_id": s.concept_id,
            "signal_date": s.video_date.isoformat(),
            "population_size": s.population_size,
            "observation_coverage": 1.0 if s.population_size > 0 else 0.0,
            
            # Derived engagement metrics mapped to chart keys
            "median_view_velocity": (s.reach_ratio_median * 1000) if s.reach_ratio_median is not None else None,
            "median_view_growth": s.reach_ratio_median,
            "median_view_acceleration": s.semantic_score_mean,
            "median_normalized_velocity": s.reach_ratio_median,
            "median_reach_ratio": s.reach_ratio_median,
            "median_interaction_density": s.interaction_density_median,
            
            # Creator count ratios
            "big_creator_signal": s.big_channel_count,
            "medium_creator_signal": s.medium_channel_count,
            "small_creator_signal": s.small_channel_count
        })
    return results

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    # Legacy execution run list (returns empty lists since those pipeline tables are inactive)
    return {
        "search_runs": [],
        "population_runs": []
    }

@router.get("/provenance")
def get_provenance(concept_id: int, target_date: date, db: Session = Depends(get_db)):
    """
    Traces the lineage of a daily concept signal back to the contributing videos and observations.
    In the new architecture, contributions are loaded directly from the daily signal population JSON.
    """
    signal = db.query(ConceptDailySignal).filter(
        ConceptDailySignal.concept_id == concept_id,
        ConceptDailySignal.video_date == target_date
    ).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Daily signal not found for this concept and date.")
        
    signal_mapped = {
        "id": signal.id,
        "concept_id": signal.concept_id,
        "signal_date": signal.video_date.isoformat(),
        "population_size": signal.population_size,
        "observation_coverage": 1.0 if signal.population_size > 0 else 0.0,
        "median_view_velocity": (signal.reach_ratio_median * 1000) if signal.reach_ratio_median is not None else None,
        "median_view_growth": signal.reach_ratio_median,
        "median_view_acceleration": signal.semantic_score_mean,
        "median_normalized_velocity": signal.reach_ratio_median,
        "median_reach_ratio": signal.reach_ratio_median,
        "median_interaction_density": signal.interaction_density_median,
        "big_creator_signal": signal.big_channel_count,
        "medium_creator_signal": signal.medium_channel_count,
        "small_creator_signal": signal.small_channel_count
    }
    
    # Map pop members stored in JSON to table rows contributions structure
    contributions = []
    population_list = signal.population or []
    for idx, item in enumerate(population_list):
        contributions.append({
            "video_id": item.get("video_id"),
            "title": item.get("title", "Unknown"),
            "creator_bucket": item.get("channel_tier", "medium"),
            "selection_score": item.get("semantic_score"),
            "selection_rank": idx + 1,
            "observed": True,
            "view_count": item.get("view_count"),
            "view_velocity": item.get("reach_ratio"),
            "view_growth": item.get("interaction_density"),
            "normalized_velocity": item.get("reach_ratio"),
            "reach_ratio": item.get("reach_ratio"),
            "interaction_density": item.get("interaction_density")
        })
        
    return {
        "signal": signal_mapped,
        "population_run_id": signal.id,
        "contributions": contributions
    }

# Background pipeline execution helper
def execute_pipeline_task(stage: str):
    db = SessionLocal()
    try:
        yt = YouTubeService()
        sem = SemanticService()
        engine = PipelineEngine(yt, sem)
        
        # Consolidate all pipeline stages to run the unified daily extraction process
        active_concepts = db.query(Concept).filter(Concept.active == True).all()
        for concept in active_concepts:
            engine.execute_concept_run(db, concept.id)
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

