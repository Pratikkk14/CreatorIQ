# CreatorIQ — Real-Time Trend Intelligence Backend

This directory contains the Python FastAPI backend and pipeline engine powering the real-time YouTube Trend Prediction Ingestion System for **CreatorIQ**.

---

## 🎯 Backend System Goal & Architecture Rationale

The primary objective of this backend is to ingest real-time YouTube video data across tracked niche concepts, apply strict multi-stage quality and semantic relevance filters, compute normalized engagement metrics and composite **Trend Scores**, and store flat daily signal summaries with full video-level audit trails.

### Why Decoupled Microservice Architecture?
1. **Standalone Deployment**: Built as an independent, decoupled REST API service that can be hosted on platforms like Render, AWS ECS, or Railway.
2. **Seamless Platform Integration**: Designed with standardized JSON response schemas (`/api/signals`, `/api/latest-entries`, `/api/provenance`) so that its computed trend signals can be seamlessly integrated into **CreatorIQ** main microservices (`Yash_creatorIQ`) or custom frontend dashboards.
3. **Stateless Candidate Population**: Candidate videos are dynamically searched and evaluated per run. The system does not lock into a rigid static set of creators, allowing it to discover new rising creators instantly.

---

## ⚙️ Ingestion & Signal Processing Pipeline

Each pipeline run processes active concepts through a 6-stage ingestion sequence:

```text
 ┌─────────────────────────────────────────────────────────┐
 │ 1. Concept Search Query Generation (OR & Exclude terms)  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 2. Real-Time YouTube Data API Search (search.list)      │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 3. Batch Metadata Fetch (videos.list & channels.list)   │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 4. Multi-Stage Filtering Gate                           │
 │    • Hard Filter (Min views: 50, subs: 100, desc: 30)   │
 │    • Language Gate (English validation)                 │
 │    • Semantic Concept Identity Gate (MiniLM similarity)  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 5. Relative Creator Bucketing (Q25 / Q75 percentiles)   │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 6. Metric Formulas & Composite Trend Score Calculation  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 7. Outlier Detection (μ + 2σ) & Streak Tracking         │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 8. Database Persistence (ConceptDailySignal)            │
 └─────────────────────────────────────────────────────────┘
```

---

## 📐 Mathematical Formulas & Metrics

1. **Reach Ratio**:
   $$\text{reach\_ratio} = \frac{\text{view\_count} / \text{subscriber\_count}}{100}$$

2. **Interaction Density**:
   $$\text{interaction\_density} = \frac{\text{like\_count} + \text{comment\_count}}{\text{view\_count}}$$

3. **Composite Video Trend Score (0–100 Scale)**:
   $$\text{norm\_reach} = \min(100.0, \text{reach\_ratio} \times 50.0)$$
   $$\text{norm\_interaction} = \min(100.0, \text{interaction\_density} \times 1000.0)$$
   $$\text{norm\_semantic} = \text{semantic\_score} \times 100.0$$
   $$\text{trend\_score} = 0.45 \times \text{norm\_reach} + 0.35 \times \text{norm\_interaction} + 0.20 \times \text{norm\_semantic}$$

4. **Statistical Outlier Detection**:
   A video is flagged as an outlier if:
   $$\text{reach\_ratio} > \mu_{\text{reach}} + 2\sigma_{\text{reach}} \quad \text{or} \quad \text{interaction\_density} > \mu_{\text{density}} + 2\sigma_{\text{density}}$$

---

## 🌐 REST API Endpoints Overview

All REST API endpoints are prefixed under `/api`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/diagnostics` | Operational system health, DB status, active concept counts, and latest execution timestamps. |
| `GET` | `/api/concepts` | List all monitored concepts with include/exclude search terms and categories. |
| `POST` | `/api/concepts` | Create and register a new concept with a unique string UUID. |
| `GET` | `/api/signals?concept_id={id}` | Get historical daily aggregated signals for a concept (medians, outlier metrics, creator counts). |
| `GET` | `/api/latest-entries?limit={n}` | Returns top populated video entries across recent pipeline runs sorted by `trend_score` descending. |
| `GET` | `/api/provenance?concept_id={id}&target_date={date}` | Trace the exact video-level lineage, rankings, and stats contributing to a daily signal. |
| `POST` | `/api/pipeline/run?stage={stage}` | Trigger pipeline execution in background (`discover`, `observe`, `metrics`, `signals`, `run`). |
| `GET` | `/api/diagnostics/raw-data` | Summary of table row counts. |
| `GET` | `/api/diagnostics/raw-data/{table_name}` | View raw database table contents for debugging and data audit. |

---

## 🗄️ Database Schemas & Models (`app/models/models.py`)

### 1. `concepts` Table
- `id` (`String(36)`, Primary Key): Unique UUID string (e.g. `"10000000-0000-0000-0000-000000000001"`).
- `name` (`String(255)`, Unique): Human-readable concept name.
- `category` (`String(100)`): Niche category (e.g. `"Fitness"`).
- `description` (`String`): Concept scope explanation.
- `active` (`Boolean`): Whether the concept is enabled for automated runs.
- `include_terms` (`JSON`): List of search keywords.
- `exclude_terms` (`JSON`): List of exclusion keywords.

### 2. `concept_daily_signals` Table
- `id` (`Integer`, Primary Key): Auto-incrementing signal ID.
- `concept_id` (`String(36)`, Foreign Key $\rightarrow$ `concepts.id`): Monitored concept ID.
- `concept_name` (`String(255)`): Concept name snapshot.
- `processed_at` (`DateTime UTC`): Execution timestamp.
- `video_date` (`Date`): Publication date window.
- `population_size` (`Integer`): Number of surviving videos in fit population.
- `reach_ratio_median` (`Float`): Median reach ratio across fit population.
- `interaction_density_median` (`Float`): Median interaction density.
- `semantic_score_mean` (`Float`): Mean semantic similarity score.
- `trend_score_median` (`Float`): Median composite Trend Score (0–100).
- `top_outlier_video_id` (`String(255)`): Video ID of top flagged outlier.
- `top_outlier_reach_ratio` (`Float`): Reach ratio of top outlier.
- `top_outlier_interaction_density` (`Float`): Interaction density of top outlier.
- `top_outlier_semantic_score` (`Float`): Semantic relevance score of top outlier.
- `top_outlier_channel_tier` (`String(50)`): Channel tier of top outlier (`"big"`, `"medium"`, `"small"`).
- `outlier_streak` (`Integer`): Consecutive days this video has been top outlier.
- `big_channel_count`, `medium_channel_count`, `small_channel_count` (`Integer`): Population channel tier composition.
- `keywords` (`JSON`): Titles list of all videos in the final population.
- `population` (`JSON`): Complete per-video record list for audit.
- `filter_audit` (`JSON`): Stage-by-stage rejection counts and reasons.

---

## 💻 CLI Commands Reference

Commands are executed via `app.main` CLI runner:

```bash
# System diagnostics and health check
python -m app.main diagnostics

# Recreate all database tables with updated schema
python -m app.main recreate-db --yes

# Seed 10 Fitness concepts defined in config/concepts.yaml
python -m app.main seed-db

# Run pipeline execution on mock data
python -m app.main pipeline run --mock

# Run live API ingestion pipeline
python -m app.main pipeline run
```
