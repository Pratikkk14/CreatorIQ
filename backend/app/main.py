import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, get_concepts_config
from app.core.database import check_db_health, SessionLocal
from app.core.logging import logger
from app.api.endpoints import router as api_router
from app.models.models import Concept
from app.cli.commands import cli

# 1. Initialize FastAPI Application
api_app = FastAPI(
    title="YouTube Trend Prediction System API",
    description="Backend API powering the longitudinal observation and signals dashboard",
    version="1.0.0"
)

# Configure CORS for React/Vite development server (usually running on port 5173)
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict to app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
api_app.include_router(api_router, prefix="/api")

# Startup database initialization and seeding hook
@api_app.on_event("startup")
def on_startup():
    logger.info("Starting up FastAPI application...")
    
    # Check DB connection
    if not check_db_health():
        logger.error("FastAPI startup warning: Database is unreachable.")
        return

    # Seed concepts from YAML config if concepts table is empty
    db = SessionLocal()
    try:
        existing_count = db.query(Concept).count()
        if existing_count == 0:
            logger.info("Concepts database table is empty. Seeding from concepts.yaml config...")
            concepts_list = get_concepts_config()
            for c_data in concepts_list:
                concept = Concept(
                    name=c_data["name"],
                    description=c_data.get("description", ""),
                    active=c_data.get("active", True),
                    search_queries=c_data["search_queries"]
                )
                db.add(concept)
            db.commit()
            logger.info(f"Successfully seeded {len(concepts_list)} concepts.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding concepts on startup: {e}")
    finally:
        db.close()

# 2. Command Line Entrypoint Routing
if __name__ == "__main__":
    # If file executed directly, defer to click CLI
    cli()
