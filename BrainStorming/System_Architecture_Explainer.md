# YouTube Trend Prediction Ingestion System: HLD Architectural Explainer

This document serves as a complete technical guide to help developers and collaborators understand **why** the YouTube Ingestion System was built, **how** it functions step-by-step using the High-Level Design (HLD) architecture, and the **reasoned engineering decisions** behind its core mechanisms.

---

## 1. The "Why" - Core Problem Statement

Traditional social listening tools fail to predict emerging video trends because they suffer from:
1.  **Creator-Size Bias**: Heavy algorithms skew towards massive channels (e.g., millions of subscribers), missing early signals originating from small/mid-sized creators.
2.  **Lack of Trajectory Context**: Traditional databases only record *totals* (e.g., total views). They do not track the **velocity** (first derivative) or **acceleration** (second derivative) of growth over consecutive days.
3.  **API Rate Limiting**: The YouTube Data API v3 enforces a strict daily limit of 10,000 quota units, meaning the system must be highly efficient.
4.  **Relevancy Noise**: Generic keyword search results include off-topic videos that distort statistical averages.

To solve this, we built a **longitudinal cohort tracking system** that selects a representative sample of creators (stratified by size), tracks their video metrics over time, and computes trend acceleration.

---

## 2. The "How" - Pipeline Architecture (Referencing the HLD)

The system works as a 4-stage pipeline that runs sequentially:

```text
        [ config/concepts.yaml ]
                   │
                   ▼
      Stage 1: Candidate Discovery
                   │
                   ▼
     Gemini / Local Ollama Filter
                   │
                   ▼
      Creator-Size Stratification
                   │
                   ▼
      Cohort Selection & Borrowing
                   │
                   ▼
     Stage 2: Statistics Observation
                   │
                   ▼
      Stage 3: Derived Metrics Engine
                   │
                   ▼
     Stage 4: Aggregation & Ingestion
                   │
                   ▼
          [ Neon PostgreSQL DB ]
```

### Stage 1: Candidate Discovery & Cohort Selection
*   **Search**: The system reads topics from `config/concepts.yaml` (e.g., "AI Agents"). It queries the YouTube Search API to retrieve candidates.
*   **Relevance Filtering**: It calculates the cosine similarity between the concept description and the video metadata (title + description) using **Ollama** or **Gemini**. Videos scoring below `0.5` are rejected.
*   **Stratification**: Eligible creators are classified into three percentile-based buckets:
    *   **Small** (bottom 33.3% of subscriber counts)
    *   **Medium** (middle 33.3%)
    *   **Big** (top 33.3%)
*   **Cohort Selection**: It builds a cohort representing a balanced ratios of creator sizes (e.g., 30% Big, 40% Medium, 30% Small).

### Stage 2: Statistics Observation
*   Every day, the system queries the YouTube API to record views, likes, and comments for the active cohort of videos.
*   It logs these metrics chronologically in `video_observations`.

### Stage 3: Derived Metrics Engine
*   The system compares today's statistics with yesterday's statistics for each video.
*   It calculates:
    *   **Velocity**: Change in views per day.
    *   **Acceleration**: Change in velocity day-over-day.
    *   **Engagement Rate**: Likes and comments relative to view counts.

### Stage 4: Ingestion & Aggregation
*   Individual video velocities and accelerations are rolled up into daily concept-level trend scores (`concept_daily_signals`).
*   Data is written atomically to the **Neon PostgreSQL** database.

---

## 3. Key Design Decisions & Reasoned Arguments

### Decision A: Stratified Cohort Selection
*   **Why**: If we only tracked the most-viewed videos, we would only see creators who are *already* viral. 
*   **Argument**: By forcing a selection ratio (e.g., 30% Big, 40% Medium, 30% Small), we ensure the system monitors smaller channels. When a small creator's video shows high velocity, it is detected as an early trend *before* it reaches the mainstream.

### Decision B: The "Soft Borrowing" Mechanism
*   **Why**: In real-world API queries, a specific creator class might have a shortage of qualified videos (e.g., we want 3 "Big" creators, but only 1 matches our search terms).
*   **Argument**: Standard algorithms might fail or leave slots empty. **Soft borrowing** collects all leftovers, sorts them by semantic score, and "borrows" them to fill the empty slots. This guarantees we always reach our target cohort size with the most relevant videos available.

### Decision C: Local Ollama Default with Remote Gemini Fallback
*   **Why**: Remote API calls (like Gemini) cost money, suffer from network latency, and can return 404 errors or hit rate limits (e.g., `models/embedding-001 is not found`).
*   **Argument**: Setting a local Ollama embedding engine (`nomic-embed-text`) as the primary default makes development and execution completely free, private, and offline-compatible. The system fallback ensures that if Ollama goes offline, it uses Gemini, and if both are unavailable, it uses a deterministic character-frequency pseudo-embedding to prevent pipeline halts.

### Decision D: Explicit API Call Auditing (`api_request_logs`)
*   **Why**: YouTube API quotas are extremely valuable. We must know exactly which processes are consuming quota.
*   **Argument**: The `api_request_logs` table logs every search, details, and channel API call along with its exact HTTP status code and estimated quota cost (e.g., search = 100 units, details = 1 unit). This allows automated diagnostics to trigger alerts if we are close to our daily 10,000-unit limit.

### Decision E: Expire on Commit Disabled (`expire_on_commit=False`)
*   **Why**: SQLAlchemy defaults to expiring model attributes after a transaction commits. Accessing `video.title` in tests or background endpoints after a commit would trigger `DetachedInstanceError` crashes.
*   **Argument**: Explicitly disabling this expiration on our session session-maker allows the FastAPI endpoints and CLI commands to read model data safely across operations without having to make redundant query calls to the database.

---

## 4. Database Schema Relationships & Detailed Column Design

The 11 tables are divided into logical layers: **Configuration**, **Discovery**, **Observation & Tracking**, **Trend Derivations**, and **Audit Logs**.

### 1. Configuration Layer
*   **`concepts`**: Stores the trend topics.
    *   *Key Columns*: `search_queries` (JSON array of strings).
    *   *Usage*: The discovery engine reads these queries to run YouTube searches.
*   **`channels`**: Tracks unique creators.
    *   *Key Columns*: `subscriber_count` (used for creator percentile stratification calculations) and `published_at` (creation date of the channel to determine channel maturity).

### 2. Discovery & Selection Layer
*   **`search_runs`** & **`video_candidates`**: Logs discovery search operations.
    *   *Key Columns*: `semantic_score` (cosine similarity score relative to concept description) and `creator_size_bucket` (`small`, `medium`, `big`).
    *   *Usage*: We audit rejected candidates using `rejection_reason` (e.g., `semantic_below_threshold`, `language_mismatch`) to troubleshoot query filtering.
*   **`population_runs`** & **`population_members`**: Logs active tracking groups.
    *   *Key Columns*: `selection_rank` (relevance rank) and `active_until` (timestamp indicating when cohort monitoring expires).

### 3. Observation Layer (Raw Data Collection)
*   **`video_observations`**: Snapshots of a video's stats at a specific point in time.
    *   *Key Columns*: `observed_at`, `view_count`, `like_count`, `comment_count`, `subscriber_count`.
    *   *Usage*: We query these raw totals over time. They act as raw inputs to compute differences.

### 4. Trend Derivation Layer (Mathematical Engine)
*   **`video_metrics`**: The mathematical outputs calculated by comparing two observations.
    *   *Key Columns*: 
        *   `time_delta_hours`: Time elapsed between current and previous observation (crucial to calculate views per day accurately even if crawls occur at irregular intervals).
        *   `view_velocity`: Difference in views divided by time delta in days. Represents growth speed.
        *   `view_acceleration`: Difference in view velocity day-over-day. Represents growth momentum.
        *   `reach_ratio_views`: Velocity divided by creator's subscriber count. Helps identify viral breakouts in smaller channels.
    *   *Usage*: Queried by the aggregation engine to calculate high-velocity indicators.
*   **`concept_daily_signals`**: Rolled up trend summary for frontend graphs.
    *   *Key Columns*:
        *   `median_view_velocity` / `average_view_velocity`: The central tendency of cohort speed.
        *   `median_view_acceleration` / `average_view_acceleration`: Growth momentum.
        *   `total_interaction_density`: Aggregated like & comment ratios.
        *   `signal_score`: A normalized composite metric representing trend strength.
    *   *Usage*: The frontend fetches these records to draw trend charts (showing signal strength over time).

### 5. Audit Layer
*   **`api_request_logs`**: Logs Google / Gemini requests.
    *   *Key Columns*: `quota_cost` (tracked per endpoint), `duration_ms` (response latency), `success` (status flag), and `error_message` (debug trace).
    *   *Usage*: Keeps track of external API health and ensures we do not hit YouTube quota limits.
