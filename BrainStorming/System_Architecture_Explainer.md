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

## 4. Database Schema Relationships (11 Tables)

Understanding how the tables connect helps visualize the database:

1.  **`concepts`**: The parent topic (e.g., "AI Agents").
2.  **`channels`**: Unique YouTube creators tracked by the system.
3.  **`videos`**: Videos associated with a channel and a concept.
4.  **`search_runs`**: Records metadata when searching YouTube.
5.  **`video_candidates`**: Search results matched with their semantic scores.
6.  **`population_runs`**: Log of cohort selection trials.
7.  **`population_members`**: The videos selected to be observed.
8.  **`video_observations`**: Snapshots of views, likes, and comments.
9.  **`video_metrics`**: Velocities and accelerations calculated from observations.
10. **`concept_daily_signals`**: The final rolled-up daily signals for frontend charts.
11. **`api_request_logs`**: System audit logs monitoring API quotas and errors.
