# YouTube Trend Intelligence Pipeline Ingestion System

A high-performance, resilient, and longitudinal data ingestion system designed to track YouTube video trends, filter search results dynamically, classify creators, calculate daily engagement metrics, and store flat aggregated trend signals with full video-level lineage.

Built using the **Python FastAPI Backend** and a **Vite React Frontend**.

---

## 🗺️ System Architecture & Ingestion Flow

The system runs a **consolidated, search-derived ingestion pipeline** in a single pass daily. The execution flow is as follows:

```text
    Concept Config (Inclusions & Exclusions)
                       │
                       ▼
         Calculate target window (D - 3)
                       │
                       ▼
      YouTube Search (Dimension: 2d, Max: 40)
                       │
                       ▼
    Fetch Videos and Channel Details in Batches
                       │
                       ▼
     Stage 1: Hard Filters (Views, Subs, Dur, Desc)
                       │
                       ▼
     Stage 2: Language Filter (English validation)
                       │
                       ▼
    Stage 3: Semantic Relevance (all-MiniLM-L6-v2)
                       │
                       ▼
    Creator Bucketing via Relative Percentiles (Q25/Q75)
                       │
                       ▼
    Calculate Engagement (Reach Ratio & Interaction Density)
                       │
                       ▼
         Flag Outliers (mean + 2 * std)
                       │
                       ▼
         Increment/Reset Outlier Streak
                       │
                       ▼
    Persist Daily Signal & Population Audit Logs to DB
```

---

## 🚀 Key Architectural Principles

1. **Daily Search-Derived Populations**: The system does **not** permanently track a fixed pool of creator channels. Instead, for each concept and extraction date, it dynamically fetches a fresh set of candidates published exactly on target publication date `D - 3 days` (lag configurable).
2. **Relative Creator Bucketing**: Rather than using hardcoded subscriber count limits, the system dynamically calculates the 25th percentile (Q25) and 75th percentile (Q75) of the subscriber counts of the *final surviving population* on that day, categorizing them into `small` (< Q25), `medium` (Q25 <= sub < Q75), and `big` (>= Q75).
3. **Flat Daily Ingestion Signal Table**: Obsolete relational tables (`videos`, `channels`, `video_observations`, `video_candidates`, `population_runs`, `population_members`, `search_runs`) are inactive. The pipeline writes **exclusively** to `concept_daily_signals` and `api_request_logs`. Per-video audits, outliers, and filter rejection counts are stored directly inside flat JSON fields (`population`, `high_variance_flags`, `filter_audit`) in the daily signals table.
4. **Strict Local Semantic Model**: Uses the local offline `all-MiniLM-L6-v2` SentenceTransformer model to calculate cosine similarity between the concept name and video text. If model loading or encoding fails, the pipeline fails explicitly to prevent silent fallbacks.

---

## 📁 Repository Structure

```text
CreatorIQ/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints
│   │   ├── cli/             # Click command-line interface commands
│   │   ├── core/            # Configuration, database connection, scheduler
│   │   ├── models/          # Declarative SQLAlchemy models (concepts, daily signals, api logs)
│   │   ├── services/        # YouTube API wrapper, semantic model service, pipeline engine
│   │   └── main.py          # Application entrypoint (CLI & FastAPI server setup)
│   ├── config/              # YAML config files (concepts.yaml, pipeline.yaml, selection.yaml)
│   ├── myvenv/              # Python virtual environment (Windows/Linux/macOS)
│   └── requirements.txt     # Python requirements (including torch, sentence-transformers, langdetect)
├── frontend/
│   ├── src/                 # React component layouts, graphs, and styling
│   └── package.json         # Frontend package manifests
├── .env-samples             # Environment variables template file
└── README.md                # System documentation
```

---

## 🛠️ Developer Setup & Installation

All backend python commands **MUST** be run inside the virtual environment (`myvenv`) inside the `backend/` directory.

### 1. Backend Setup
Initialize the virtual environment and install packages:
```bash
cd backend
python -m venv myvenv
myvenv\Scripts\activate      # Windows PowerShell/CMD
source myvenv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the template file `.env-samples` to a new file named `.env` in the workspace root:
```bash
cp ../.env-samples ../.env
```
Open `.env` and fill in your connection string and credentials:
* `DATABASE_URL` / `POSTGRES_DB` (PostgreSQL connection URL)
* `Youtube_API_KEY` (Google Cloud Console YouTube Data API v3 key)

### 3. Recreate and Seed Database Tables
To drop any old database schemas and build/seed the new tables instantly, run:
```bash
# Drops all tables and recreates them with updated schema columns
myvenv\Scripts\python -m app.main recreate-db

# Seeds active concepts defined in config/concepts.yaml
myvenv\Scripts\python -m app.main seed-db
```

---

## 🏃 Running the Application

### 1. Manual Ingestion Run (Mock Mode)
To run a full, unified extraction pipeline on mock data for development:
```bash
myvenv\Scripts\python -m app.main pipeline run --mock
```
*Add option `--date YYYY-MM-DD` to target specific execution dates (defaults to today).*

### 2. Manual Ingestion Run (Real API)
To run the extraction pipeline querying real live YouTube endpoints:
```bash
myvenv\Scripts\python -m app.main pipeline run
```

### 3. Start the Backend Web Server
Launch the FastAPI server on port 8000:
```bash
myvenv\Scripts\uvicorn app.main:api_app --host 127.0.0.1 --port 8000
```
This automatically boots the daily background cron scheduler (running at configured timezone/cron hour). View API documentation at `http://127.0.0.1:8000/docs`.

### 4. Start the Frontend React App
In a separate terminal, install dependencies and boot the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. The frontend graphs will automatically display the daily trend signals and allow you to trace provenance lineages.

---

## 📟 CLI Command Reference

All commands must be executed from the `backend/` folder:

*   **Diagnostics**: Check database connectivity, YouTube configuration parameters, and daily signals generated:
    ```bash
    myvenv\Scripts\python -m app.main diagnostics
    ```
*   **Reset Database**: Truncate all records from all database tables:
    ```bash
    myvenv\Scripts\python -m app.main reset-db --yes
    ```
*   **Recreate Database**: Drop all tables and rebuild schemas:
    ```bash
    myvenv\Scripts\python -m app.main recreate-db --yes
    ```
*   **Seed Database**: Seed default concepts:
    ```bash
    myvenv\Scripts\python -m app.main seed-db
    ```
*   **Run Pipeline**: Trigger the ingestion job:
    ```bash
    myvenv\Scripts\python -m app.main pipeline run [--mock] [--date YYYY-MM-DD]
    ```

---

## 🧪 Testing

Execute the test suite to assert calculations and E2E simulation correctness:
```bash
cd backend
myvenv\Scripts\pytest tests -v
```
