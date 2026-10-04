from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class Concept(Base):
    __tablename__ = "concepts"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), default="Fitness", nullable=False)
    description = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    include_terms = Column(JSON, nullable=False)  # List of inclusion terms
    exclude_terms = Column(JSON, nullable=False)  # List of exclusion terms
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    daily_signals = relationship("ConceptDailySignal", back_populates="concept", cascade="all, delete-orphan")


class ConceptDailySignal(Base):
    __tablename__ = "concept_daily_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    concept_name = Column(String(255), nullable=False)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    video_date = Column(Date, nullable=False)
    population_size = Column(Integer, nullable=False)
    
    # Core daily signals
    reach_ratio_median = Column(Float, nullable=True)
    interaction_density_median = Column(Float, nullable=True)
    semantic_score_mean = Column(Float, nullable=True)
    trend_score_median = Column(Float, nullable=True)  # Composite video trend score median (0-100)
    
    # Outlier tracking
    top_outlier_video_id = Column(String(255), nullable=True)
    top_outlier_reach_ratio = Column(Float, nullable=True)
    top_outlier_interaction_density = Column(Float, nullable=True)
    top_outlier_semantic_score = Column(Float, nullable=True)
    top_outlier_channel_tier = Column(String(50), nullable=True)  # big / medium / small
    outlier_streak = Column(Integer, default=0, nullable=False)
    
    # Population composition
    big_channel_count = Column(Integer, default=0, nullable=False)
    medium_channel_count = Column(Integer, default=0, nullable=False)
    small_channel_count = Column(Integer, default=0, nullable=False)
    
    # Full audit trail
    keywords = Column(JSON, nullable=True)  # JSON list of video titles
    population = Column(JSON, nullable=True)  # Full per-video records list
    high_variance_flags = Column(JSON, nullable=True)  # Outlier videos list
    filter_audit = Column(JSON, nullable=True)  # Filter stage counts & reasons
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    concept = relationship("Concept", back_populates="daily_signals")

    __table_args__ = (
        Index("idx_concept_signals_concept_date", "concept_id", "video_date"),
        UniqueConstraint("concept_id", "video_date", name="uq_concept_id_video_date"),
    )


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    api_name = Column(String(50), nullable=False)  # youtube, gemini, etc.
    endpoint = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    http_status = Column(Integer, nullable=True)
    quota_cost = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    attempt = Column(Integer, default=1, nullable=False)
    success = Column(Boolean, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(String, nullable=True)
    request_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_api_logs_requested_at", "requested_at"),
    )
