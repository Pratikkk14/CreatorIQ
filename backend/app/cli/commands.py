import click
import sys
from datetime import datetime, date, timezone
try:
    from tabulate import tabulate
except ImportError:
    tabulate = None
from app.core.config import settings, get_concepts_config
from app.core.database import check_db_health, SessionLocal
from app.core.logging import logger
from app.models.models import Concept
from app.services import (
    YouTubeService, SemanticService, SelectorService, 
    DiscoveryEngine, ObservationEngine, MetricsEngine, AggregationEngine
)

def get_services(mock: bool = False):
    yt = YouTubeService(use_mock=mock)
    sem = SemanticService()
    sel = SelectorService()
    
    disc = DiscoveryEngine(yt, sem, sel)
    obs = ObservationEngine(yt)
    met = MetricsEngine()
    agg = AggregationEngine()
    
    return disc, obs, met, agg

@click.group()
def cli():
    """YouTube Trend Prediction System Pipeline Tool"""
    pass

@cli.command("diagnostics")
@click.option("--mock", is_flag=True, help="Run diagnostics using YouTube Mock API")
def diagnostics(mock):
    """Check system settings, database, and database row tallies."""
    click.echo("Running system diagnostics...")
    db_ok = check_db_health()
    yt_ok = bool(settings.youtube_api_key)
    
    click.echo(f"Database Connectivity: {'OK' if db_ok else 'ERROR'}")
    click.echo(f"YouTube Configuration: {'OK' if yt_ok else 'MISSING_API_KEY'}")
    
    db = SessionLocal()
    try:
        concepts = db.query(Concept).count()
        click.echo(f"Active Concepts: {concepts}")
        
        # Query summaries
        from app.models.models import Video, VideoCandidate, PopulationMember, VideoObservation, ConceptDailySignal, ApiRequestLog
        click.echo(f"Registered Videos: {db.query(Video).count()}")
        click.echo(f"Candidates Tracked: {db.query(VideoCandidate).count()}")
        click.echo(f"Population Members: {db.query(PopulationMember).count()}")
        click.echo(f"Video Observations: {db.query(VideoObservation).count()}")
        click.echo(f"Concept Signals Generated: {db.query(ConceptDailySignal).count()}")
        click.echo(f"API Failed Requests: {db.query(ApiRequestLog).filter(ApiRequestLog.success == False).count()}")
        
        latest_obs = db.query(VideoObservation.observed_at).order_by(VideoObservation.observed_at.desc()).first()
        click.echo(f"Latest Observation: {latest_obs[0] if latest_obs else 'None'}")
        
        latest_sig = db.query(ConceptDailySignal.signal_date).order_by(ConceptDailySignal.signal_date.desc()).first()
        click.echo(f"Latest Concept Signal: {latest_sig[0] if latest_sig else 'None'}")
    except Exception as e:
        click.echo(f"Diagnostics Error querying database: {e}", err=True)
    finally:
        db.close()

@click.group(name="pipeline")
def pipeline_group():
    """Pipeline Stage Commands"""
    pass

@pipeline_group.command("validate")
def validate_config():
    """Validates env variables and YAML config files."""
    click.echo("Validating environment settings and concepts configurations...")
    try:
        # Load settings
        db_url = settings.get_db_url()
        click.echo("√ Environment configurations parsed.")
        
        # Load concepts config
        concepts = get_concepts_config()
        click.echo(f"√ Concepts YAML loaded. Found {len(concepts)} concepts:")
        for idx, c in enumerate(concepts):
            click.echo(f"  {idx+1}. {c['name']} (queries: {c['search_queries']})")
            
        # Check DB
        if check_db_health():
            click.echo("√ Database connection established successfully.")
        else:
            click.echo("X Database connection failed.", err=True)
            sys.exit(1)
            
        click.echo("All configurations validated successfully.")
    except Exception as e:
        click.echo(f"Validation FAILED: {e}", err=True)
        sys.exit(1)

@pipeline_group.command("discover")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--lookback-days", type=int, help="Override lookback window in days")
def discover(mock, lookback_days):
    """Run candidate discovery and population selection."""
    click.echo("Running candidate discovery and population selection...")
    disc, _, _, _ = get_services(mock)
    res = disc.run_discovery(lookback_days=lookback_days)
    click.echo(f"Discovery Result: {res}")

@pipeline_group.command("observe")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--date", "obs_date", type=str, help="Override observation timestamp (ISO format)")
def observe(mock, obs_date):
    """Run statistics observation loop for active population."""
    click.echo("Running video statistics observations...")
    _, obs, _, _ = get_services(mock)
    
    o_time = None
    if obs_date:
        o_time = datetime.fromisoformat(obs_date)
        if o_time.tzinfo is None:
            o_time = o_time.replace(tzinfo=timezone.utc)
            
    res = obs.run_observation(observation_time=o_time)
    click.echo(f"Observation Result: {res}")

@pipeline_group.command("metrics")
def metrics():
    """Generate derived features/metrics from raw observations."""
    click.echo("Generating derived features...")
    _, _, met, _ = get_services()
    res = met.run_metrics_generation()
    click.echo(f"Metrics Generation Result: {res}")

@pipeline_group.command("signals")
@click.option("--date", "sig_date", type=str, help="Target date for aggregation (YYYY-MM-DD)")
def signals(sig_date):
    """Aggregate video metrics into concept daily signals."""
    click.echo("Generating concept daily signals...")
    _, _, _, agg = get_services()
    
    t_date = None
    if sig_date:
        t_date = date.fromisoformat(sig_date)
        
    res = agg.run_aggregation(target_date=t_date)
    click.echo(f"Aggregation Result: {res}")

@pipeline_group.command("run")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--lookback-days", type=int, help="Override lookback window in days")
@click.option("--date", "target_date_str", type=str, help="Target date for the run (YYYY-MM-DD)")
def run_all(mock, lookback_days, target_date_str):
    """Execute all pipeline stages sequentially."""
    click.echo("=== EXECUTION: Pipeline Run Starting ===")
    disc, obs, met, agg = get_services(mock)
    
    # 1. Discover
    click.echo("\n--- STAGE 1: Discover ---")
    d_res = disc.run_discovery(lookback_days=lookback_days)
    click.echo(f"Discovery: {d_res}")
    if d_res.get("status") == "failed":
        click.echo("Pipeline aborted due to Discovery failure.")
        sys.exit(1)
        
    # 2. Observe
    click.echo("\n--- STAGE 2: Observe ---")
    o_time = None
    if target_date_str:
        # If running for a specific date, align observations with that date's midday
        target_d = date.fromisoformat(target_date_str)
        o_time = datetime.combine(target_d, datetime.now(timezone.utc).time(), tzinfo=timezone.utc)
    o_res = obs.run_observation(observation_time=o_time)
    click.echo(f"Observation: {o_res}")
    
    # 3. Metrics
    click.echo("\n--- STAGE 3: Derived Metrics ---")
    m_res = met.run_metrics_generation()
    click.echo(f"Metrics: {m_res}")
    
    # 4. Signals
    click.echo("\n--- STAGE 4: Concept Signals ---")
    t_date = None
    if target_date_str:
        t_date = date.fromisoformat(target_date_str)
    a_res = agg.run_aggregation(target_date=t_date)
    click.echo(f"Aggregation: {a_res}")
    
    click.echo("\n=== EXECUTION: Pipeline Run Complete ===")

cli.add_command(diagnostics)
cli.add_command(pipeline_group)

if __name__ == "__main__":
    cli()
