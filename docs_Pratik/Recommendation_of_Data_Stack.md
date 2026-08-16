# Recommendation of Data Stack (CreatorIQ)

To evolve CreatorIQ from an AI wrapper into a robust, scalable, and predictable **Data Engineering** platform, we must structure how we ingest, store, clean, and process trend signals from YouTube, Google Trends, and future integrations. 

Below is the assessment and recommendation of technologies from the proposed stack tiers, tailored to the current and future requirements of the system.

---

## 🏗️ Architecture Design: Bronze, Silver, and Gold

We recommend organizing your data lake storage (S3 or Google Cloud Storage) into a standard **Medallion Architecture**. This prevents data loss, enables tracing data errors (lineage), and allows reprocessing raw signals when scoring algorithms change.

```
┌─────────────────┐       ┌───────────────┐       ┌─────────────────┐
│   Bronze Tier   │ ───▶  │  Silver Tier  │ ───▶  │    Gold Tier    │
│  (Raw Ingestion)│       │  (Cleaned/Dedu) │       │ (Business/ML)   │
└─────────────────┘       └───────────────┘       └─────────────────┘
  • YouTube JSON            • Iceberg Tables        • Scored Concepts
  • SerpApi JSON            • Schema-enforced       • Vector Embeddings
  • Raw API limits          • Deduplicated          • Creator Feeds
```

---

## 🛠️ Data Stack Recommendations by Tier

### Tier 1 — Critical Foundations (Implement Immediately)

| Technology | Role in CreatorIQ | Recommendation & Implementation Strategy |
| :--- | :--- | :--- |
| **Python** | Core Language | Remain as the primary language for ingestion scripts, API endpoints, and scoring systems (already in use). |
| **SQL** | Transformation & Querying | The foundational querying language for PostgreSQL storage and analytical computations. |
| **Docker / Git** | Containerization & Versioning | Standardize local environment orchestration using Docker Compose. Use Git for codebase version control (separate from configuration variables). |
| **GCS / AWS S3** | Cloud Object Storage | **Highly Recommended**. Raw JSON API responses from YouTube and SerpApi should be dumped directly into S3/GCS buckets rather than storing raw text blobs in PostgreSQL. This separates data ingestion from transactional database usage. |
| **JSON** | Raw Payload Format | The native response format from all external social APIs (YouTube, SerpApi, TikTok, Instagram). Stored inside the **Bronze Tier**. |
| **Parquet** | Analytical File Format | **Highly Recommended**. Convert raw JSON signals into Parquet format for the **Silver Tier**. Parquet offers columnar compression, which dramatically reduces storage space and speeds up analytical queries over time-series data. |
| **Apache Iceberg** | Open Table Format | **Highly Recommended**. Use Iceberg on top of Parquet files in S3. Iceberg supports schema evolution (crucial when YouTube modifies their API keys), ACID transactions, and **time-travel queries** (allowing you to audit what a creator's trend feed looked like on a specific day in the past). |
| **Apache Airflow** | Orchestration & Scheduling | **Highly Recommended**. The current system relies on basic cron/schedulers to run collection tasks. Replace this with Airflow. Airflow schedules scraping runs, manages retries, ensures API quotas aren't exceeded simultaneously, and tracks task dependencies (e.g., don't run scoring until data collection succeeds). |
| **Great Expectations** | Data Quality & Validation | **Highly Recommended**. Since external API data is volatile, use Great Expectations to validate data at the gate between Bronze and Silver. Example checks: Assert that the YouTube channel ID is not null, verify that view counts are positive numbers, and confirm that API payloads contain expected structural fields. |
| **Spark / PySpark** | Batch Processing | **Optional for MVP; Recommended for Scale**. If you are processing millions of trending videos daily across hundreds of niches, use PySpark. If you are starting with small local feeds, standard Python dataframes (e.g. Polars or Pandas) are sufficient for early-stage CPU limits, transitioning to Spark as volume increases. |
| **Trino** | Distributed SQL Query Engine | **Deferred**. Trino is useful for running SQL queries across disparate data sources (like S3 Iceberg + PostgreSQL + MongoDB). Keep this in mind for the future but rely on direct PostgreSQL and S3 query clients for now. |

---

### Tier 2 — Operational Value (Build in Phase 2)

| Technology | Role in CreatorIQ | Recommendation & Implementation Strategy |
| :--- | :--- | :--- |
| **dbt (data build tool)** | SQL Transformation & Lineage | **Highly Recommended**. Use dbt to manage the transformation SQL scripts that aggregate raw signals into Trend Velocity Scores (TVS). dbt automatically documents data lineage (so developers can audit how a specific score was generated) and tests relationships. |
| **Schema Evolution** | Data Contract Flexibility | **Highly Recommended**. Managed automatically by Iceberg. This allows your backend developers to safely alter table schemas without breaking ongoing pipelines. |
| **Idempotent Ingestion** | Ingestion Reliability | **Critical**. Ensure that running a scraping task multiple times does not insert duplicate rows or alter existing metrics. Every signal must be uniquely identifiable (e.g. `video_id` + `timestamp` as a unique hash). |
| **Incremental Processing** | Ingestion Optimization | **Critical**. Instead of pulling entire channel histories, only pull metrics since the last successful execution. Reduces API query volumes and controls cost. |
| **Data Quarantine** | Error Mitigation | **Recommended**. If a YouTube API response fails schema checks in Great Expectations, push the payload to a quarantine zone rather than letting it crash the script. Send alerts to developers while healthy data flows proceed. |
| **CI / CD** | Deployment Automation | Automate build compilation and schema validations using GitHub Actions or Gitlab CI to ensure code quality before pushing. |
| **Terraform** | Infrastructure as Code | Define resources (S3 buckets, RDS PostgreSQL databases, Redis nodes, Render/Vercel resources) in code to easily spin up staging and production environments. |
| **Entity Resolution** | Creator Profile Linking | **Critical for Multi-Platform expansion**. When scraping YouTube and other future platforms, you will need to link accounts belonging to the same creator (e.g., identifying that `@creator_name` on TikTok is the same user as `@creator_name` on YouTube). |
| **Data Lineage / Provenance** | Auditing & Visibility | Crucial for explaining to creators *why* a particular concept was recommended to them. |

---

### Tier 3 — Advanced Scale (Use Only When Required)

| Technology | Role in CreatorIQ | Recommendation & Implementation Strategy |
| :--- | :--- | :--- |
| **Apache Kafka** | Real-time Stream Processing | **Keep but defer**. The current codebase references Kafka for async tasks, but real-time message streams are not required for scheduled hourly/daily video updates. A robust task runner/orchestrator like Celery, Airflow, or Redis queues is easier to deploy on Render. Transition to Kafka only if you build real-time creator alert systems. |
| **ChromaDB** | Unstructured Vector DB | **Avoid**. The current system uses **Qdrant** which is significantly more robust and production-ready for vector storage. Keep Qdrant (or use pgvector inside PostgreSQL) instead of switching to Chroma. |
| **Feast** | Feature Store | **Use when scaling ML**. Feast is useful when you have multiple machine learning models (scoring, CTR, categorization) reading identical features. It ensures consistent features are served to training pipelines and online inference endpoints. |
| **MLflow** | Model Lifecycle Management | **Use when models become complex**. If you are training custom trend trajectory models, use MLflow to track parameters, versions, and deployment artifacts. |
| **CDC (Change Data Capture)** | DB Replication / Audit | **Deferred**. Captures insert/update/delete events directly from your transactional databases. Only needed if syncing databases in real-time with search engines or external caches. |

---

## 📈 Integration Checklist for New Platforms (Instagram, TikTok, Twitch)

To generate more diverse and predictable trend feeds as requested, use this standardized pipeline outline:

1. **Extraction (Airflow + API Client)**: Pull daily regional trending lists from TikTok/Instagram APIs, dump raw JSON to S3 (`s3://creatoriq-bronze/raw-signals/{platform}/`).
2. **Validation (Great Expectations)**: Verify columns (e.g. `video_id`, `view_count`, `post_url`). Quarantine corrupt payloads.
3. **Transformation (dbt + Iceberg)**: Normalize keys (e.g., map TikTok `likeCount` and YouTube `like_count` to a standard schema variable `likes_count`). Append to `s3://creatoriq-silver/signals/`.
4. **Scoring Engine (Python / SQL)**: Compute the Trend Velocity Score using normalized cross-platform weights.
5. **Vector Update (Qdrant)**: Embed the concept name and tag details for similarity search and deduplication.
6. **Delivery (FastAPI Gateways)**: Serve the final snapshot to the creator dashboard.
