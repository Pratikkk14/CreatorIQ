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
from app.models.models import Concept, ConceptDailySignal, ApiRequestLog
from app.services.youtube_api import YouTubeService
from app.services.semantic import SemanticService
from app.services.pipeline_engine import PipelineEngine

@click.group()
def cli():
    """YouTube Trend Prediction System Pipeline Tool"""
    pass

@cli.command("diagnostics")
def diagnostics():
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
        click.echo(f"Concept Signals Generated: {db.query(ConceptDailySignal).count()}")
        click.echo(f"API Failed Requests: {db.query(ApiRequestLog).filter(ApiRequestLog.success == False).count()}")
        
        latest_sig = db.query(ConceptDailySignal.video_date).order_by(ConceptDailySignal.video_date.desc()).first()
        click.echo(f"Latest Concept Signal Date: {latest_sig[0] if latest_sig else 'None'}")
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
        click.echo("[OK] Environment configurations parsed.")
        
        # Load concepts config
        concepts = get_concepts_config()
        click.echo(f"[OK] Concepts YAML loaded. Found {len(concepts)} concepts:")
        for idx, c in enumerate(concepts):
            click.echo(f"  {idx+1}. {c['name']} (includes: {c.get('include_terms', [])}, excludes: {c.get('exclude_terms', [])})")
            
        # Check DB
        if check_db_health():
            click.echo("[OK] Database connection established successfully.")
        else:
            click.echo("X Database connection failed.", err=True)
            sys.exit(1)
            
        click.echo("All configurations validated successfully.")
    except Exception as e:
        click.echo(f"Validation FAILED: {e}", err=True)
        sys.exit(1)

@pipeline_group.command("run")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--date", "target_date_str", type=str, help="Target execution date (YYYY-MM-DD)")
def run_all(mock, target_date_str):
    """Execute the daily ingestion pipeline (unified single-run)."""
    click.echo("=== EXECUTION: Consolidated Ingestion Pipeline Starting ===")
    
    t_date = None
    if target_date_str:
        try:
            t_date = date.fromisoformat(target_date_str)
        except ValueError:
            click.echo(f"Invalid date format: {target_date_str}. Use YYYY-MM-DD.", err=True)
            sys.exit(1)
    else:
        t_date = datetime.now(timezone.utc).date()
        
    db = SessionLocal()
    try:
        yt = YouTubeService(use_mock=mock)
        sem = SemanticService()
        engine = PipelineEngine(yt, sem)
        
        active_concepts = db.query(Concept).filter(Concept.active == True).all()
        if not active_concepts:
            click.echo("No active concepts found in the database. Run seed-db first.")
            sys.exit(1)
            
        for concept in active_concepts:
            click.echo(f"\nProcessing concept '{concept.name}' (ID: {concept.id})...")
            res = engine.execute_concept_run(db, concept_id=concept.id, execution_date=t_date)
            click.echo(f"Run Outcome: {res}")
            
        click.echo("\n=== EXECUTION: Ingestion Pipeline Complete ===")
    except Exception as e:
        click.echo(f"X Pipeline run failed: {e}", err=True)
        sys.exit(1)
    finally:
        db.close()

# Backward compatible alias commands pointing to consolidated pipeline run
@pipeline_group.command("discover")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--date", "target_date_str", type=str, help="Target execution date (YYYY-MM-DD)")
@click.pass_context
def discover(ctx, mock, target_date_str):
    """Run discover stage (Alias to consolidated pipeline run)."""
    ctx.invoke(run_all, mock=mock, target_date_str=target_date_str)

@pipeline_group.command("observe")
@click.option("--mock", is_flag=True, help="Use mock YouTube client")
@click.option("--date", "target_date_str", type=str, help="Target execution date (YYYY-MM-DD)")
@click.pass_context
def observe(ctx, mock, target_date_str):
    """Run observe stage (Alias to consolidated pipeline run)."""
    ctx.invoke(run_all, mock=mock, target_date_str=target_date_str)

@pipeline_group.command("metrics")
@click.option("--date", "target_date_str", type=str, help="Target execution date (YYYY-MM-DD)")
@click.pass_context
def metrics(ctx, target_date_str):
    """Run metrics stage (Alias to consolidated pipeline run)."""
    ctx.invoke(run_all, mock=False, target_date_str=target_date_str)

@pipeline_group.command("signals")
@click.option("--date", "target_date_str", type=str, help="Target execution date (YYYY-MM-DD)")
@click.pass_context
def signals(ctx, target_date_str):
    """Run signals stage (Alias to consolidated pipeline run)."""
    ctx.invoke(run_all, mock=False, target_date_str=target_date_str)

@cli.command("reset-db")
@click.option("--yes", is_flag=True, help="Confirm database reset without confirmation prompt")
def reset_db(yes):
    """Delete all records from all tables in the database (Clean Slate)."""
    if not yes:
        if not click.confirm("Are you sure you want to delete all historical observations, signals, runs, channels, videos, and logs?"):
            click.echo("Reset aborted.")
            return
            
    click.echo("Resetting database tables...")
    db = SessionLocal()
    try:
        from app.models.models import (
            ApiRequestLog, ConceptDailySignal, VideoMetric, VideoObservation,
            PopulationMember, PopulationRun, VideoCandidate, SearchRun, Video, Channel, Concept
        )
        
        click.echo("Clearing api logs and signals...")
        db.query(ApiRequestLog).delete()
        db.query(ConceptDailySignal).delete()
        
        click.echo("Clearing video statistics and cohorts...")
        db.query(VideoMetric).delete()
        db.query(VideoObservation).delete()
        db.query(PopulationMember).delete()
        db.query(PopulationRun).delete()
        db.query(VideoCandidate).delete()
        db.query(SearchRun).delete()
        db.query(Video).delete()
        db.query(Channel).delete()
        
        click.echo("Clearing concepts...")
        db.query(Concept).delete()
        
        db.commit()
        click.echo("[OK] Database successfully cleared. All tables are now empty.")
    except Exception as e:
        db.rollback()
        click.echo(f"X Failed to clear database: {e}", err=True)
    finally:
        db.close()

@cli.command("seed-db")
def seed_db():
    """Seed default trend concepts from concepts.yaml config."""
    click.echo("Seeding database concepts from concepts.yaml...")
    db = SessionLocal()
    try:
        existing = db.query(Concept).count()
        if existing > 0:
            click.echo(f"Concepts table already has {existing} entries. Skipping seeding.")
            return
            
        concepts_list = get_concepts_config()
        for c_data in concepts_list:
            concept = Concept(
                name=c_data["name"],
                description=c_data.get("description", ""),
                active=c_data.get("active", True),
                include_terms=c_data["include_terms"],
                exclude_terms=c_data.get("exclude_terms", [])
            )
            db.add(concept)
        db.commit()
        click.echo(f"[OK] Successfully seeded {len(concepts_list)} concepts.")
    except Exception as e:
        db.rollback()
        click.echo(f"X Seeding failed: {e}", err=True)
    finally:
        db.close()

@cli.command("recreate-db")
@click.option("--yes", is_flag=True, help="Confirm database drop and recreation without prompt")
def recreate_db(yes):
    """Drop all tables and recreate them with the new schema."""
    if not yes:
        if not click.confirm("WARNING: This will drop ALL database tables and recreate them. Are you sure?"):
            click.echo("Aborted.")
            return
            
    click.echo("Dropping all tables...")
    from app.models.base import Base
    from app.core.database import engine
    from sqlalchemy import text
    try:
        # Execute DROP CASCADE on any old/obsolete tables first to clear legacy foreign keys
        with engine.begin() as conn:
            conn.execute(text("""
                DROP TABLE IF EXISTS channels, videos, search_runs, video_candidates, 
                population_runs, population_members, video_observations, video_metrics CASCADE;
            """))
            
        from app.models.models import (
            ApiRequestLog, ConceptDailySignal, Concept
        )
        Base.metadata.drop_all(bind=engine)
        click.echo("[OK] Tables dropped.")
        
        click.echo("Creating tables with new schema...")
        Base.metadata.create_all(bind=engine)
        click.echo("[OK] Tables recreated successfully.")
    except Exception as e:
        click.echo(f"X Failed to recreate database: {e}", err=True)


cli.add_command(diagnostics)
cli.add_command(pipeline_group)
cli.add_command(reset_db)
cli.add_command(seed_db)
cli.add_command(recreate_db)

if __name__ == "__main__":
    cli()

