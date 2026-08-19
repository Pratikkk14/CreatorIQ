from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Date, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class Concept(Base):
    __tablename__ = "concepts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    search_queries = Column(JSON, nullable=False)  # List of queries
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    search_runs = relationship("SearchRun", back_populates="concept", cascade="all, delete-orphan")
    population_runs = relationship("PopulationRun", back_populates="concept", cascade="all, delete-orphan")
    daily_signals = relationship("ConceptDailySignal", back_populates="concept", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"
    
    channel_id = Column(String(255), primary_key=True)
    title = Column(String(255), nullable=False)
    subscriber_count = Column(BigInteger, nullable=True)
    video_count = Column(Integer, nullable=True)
    country = Column(String(50), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_observed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    
    video_id = Column(String(255), primary_key=True)
    channel_id = Column(String(255), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    category_id = Column(String(50), nullable=True)
    language = Column(String(50), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    first_discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, deleted, private
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    channel = relationship("Channel", back_populates="videos")
    candidates = relationship("VideoCandidate", back_populates="video", cascade="all, delete-orphan")
    observations = relationship("VideoObservation", back_populates="video", cascade="all, delete-orphan")
    metrics = relationship("VideoMetric", back_populates="video", cascade="all, delete-orphan")
    population_memberships = relationship("PopulationMember", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_videos_channel_id", "channel_id"),
    )


class SearchRun(Base):
    __tablename__ = "search_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    published_after = Column(DateTime(timezone=True), nullable=True)
    published_before = Column(DateTime(timezone=True), nullable=True)
    query = Column(String(255), nullable=False)
    requested_limit = Column(Integer, nullable=False)
    returned_count = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)  # pending, success, failed
    error_message = Column(String, nullable=True)

    concept = relationship("Concept", back_populates="search_runs")
    candidates = relationship("VideoCandidate", back_populates="search_run", cascade="all, delete-orphan")
    population_runs = relationship("PopulationRun", back_populates="search_run", cascade="all, delete-orphan")


class VideoCandidate(Base):
    __tablename__ = "video_candidates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_run_id = Column(Integer, ForeignKey("search_runs.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(String(255), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)
    semantic_score = Column(Float, nullable=True)
    language_score = Column(Float, nullable=True)
    metadata_score = Column(Float, nullable=True)
    creator_size_bucket = Column(String(50), nullable=True)  # big, medium, small
    selection_status = Column(String(50), default="pending", nullable=False)  # pending, selected, rejected, invalid
    selection_rank = Column(Integer, nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    search_run = relationship("SearchRun", back_populates="candidates")
    video = relationship("Video", back_populates="candidates")

    __table_args__ = (
        Index("idx_video_candidates_search_run_id", "search_run_id"),
    )


class PopulationRun(Base):
    __tablename__ = "population_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    search_run_id = Column(Integer, ForeignKey("search_runs.id", ondelete="CASCADE"), nullable=False)
    target_size = Column(Integer, nullable=False)
    actual_size = Column(Integer, nullable=False)
    selection_strategy = Column(String(100), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)  # pending, success, failed

    concept = relationship("Concept", back_populates="population_runs")
    search_run = relationship("SearchRun", back_populates="population_runs")
    members = relationship("PopulationMember", back_populates="population_run", cascade="all, delete-orphan")


class PopulationMember(Base):
    __tablename__ = "population_members"
    
    population_run_id = Column(Integer, ForeignKey("population_runs.id", ondelete="CASCADE"), primary_key=True)
    video_id = Column(String(255), ForeignKey("videos.video_id", ondelete="CASCADE"), primary_key=True)
    creator_size_bucket = Column(String(50), nullable=False)
    selection_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    selected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    population_run = relationship("PopulationRun", back_populates="members")
    video = relationship("Video", back_populates="population_memberships")

    __table_args__ = (
        Index("idx_population_members_run_id", "population_run_id"),
    )


class VideoObservation(Base):
    __tablename__ = "video_observations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(255), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    view_count = Column(BigInteger, nullable=False)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(BigInteger, nullable=True)
    subscriber_count = Column(BigInteger, nullable=True)
    video_age_seconds = Column(BigInteger, nullable=True)
    api_source = Column(String(50), nullable=False)  # youtube_data_api, mock
    request_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    video = relationship("Video", back_populates="observations")
    metrics = relationship("VideoMetric", back_populates="observation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_video_obs_video_observed", "video_id", "observed_at"),
        Index("idx_video_obs_observed_at", "observed_at"),
        UniqueConstraint("video_id", "observed_at", name="uq_video_id_observed_at"),
    )


class VideoMetric(Base):
    __tablename__ = "video_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(255), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)
    observation_id = Column(Integer, ForeignKey("video_observations.id", ondelete="CASCADE"), nullable=False)
    age_days = Column(Float, nullable=True)
    views_per_day = Column(Float, nullable=True)
    view_velocity = Column(Float, nullable=True)
    view_growth = Column(Float, nullable=True)
    view_acceleration = Column(Float, nullable=True)
    views_per_subscriber = Column(Float, nullable=True)
    normalized_velocity = Column(Float, nullable=True)
    reach_ratio = Column(Float, nullable=True)
    interaction_density = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    video = relationship("Video", back_populates="metrics")
    observation = relationship("VideoObservation", back_populates="metrics")


class ConceptDailySignal(Base):
    __tablename__ = "concept_daily_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    signal_date = Column(Date, nullable=False)
    population_size = Column(Integer, nullable=False)
    observation_coverage = Column(Float, nullable=False)
    median_view_velocity = Column(Float, nullable=True)
    median_view_growth = Column(Float, nullable=True)
    median_view_acceleration = Column(Float, nullable=True)
    median_normalized_velocity = Column(Float, nullable=True)
    median_reach_ratio = Column(Float, nullable=True)
    median_interaction_density = Column(Float, nullable=True)
    p25_velocity = Column(Float, nullable=True)
    p75_velocity = Column(Float, nullable=True)
    velocity_std = Column(Float, nullable=True)
    big_creator_signal = Column(Float, nullable=True)
    medium_creator_signal = Column(Float, nullable=True)
    small_creator_signal = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    concept = relationship("Concept", back_populates="daily_signals")

    __table_args__ = (
        Index("idx_concept_signals_concept_date", "concept_id", "signal_date"),
        UniqueConstraint("concept_id", "signal_date", name="uq_concept_id_signal_date"),
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
