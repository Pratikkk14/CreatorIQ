from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from app.core.logging import logger

# Connection pooling configurations (typically loaded from env via settings, but we fall back to defaults)
POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 10)) if "os" in globals() else 10
MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", 20)) if "os" in globals() else 20

# We need to import os here
import os

try:
    engine = create_engine(
        settings.get_db_url(),
        pool_size=int(os.environ.get("DB_POOL_SIZE", 10)),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        pool_pre_ping=True
    )
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    engine = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_health() -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
