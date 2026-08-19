# YouTube Trend Prediction Ingestion System

A high-performance, resilient, and longitudinal data ingestion system designed to track YouTube video metrics, classify creators dynamically, calculate derivative trend metrics (velocity, growth, acceleration), and output aggregate concept signals.

Built using the **MERN-adjacent stack** (Python FastAPI Backend + SQLite/PostgreSQL Database + Vite React Frontend).

---

## 🗺️ System Architecture

The following flow chart details the longitudinal ingestion pipeline from configuration loading to frontend visualization:
![Here we are showing the FlowChart of current system](BrainStorming\HLD.png)
---

## 🚀 Key Features

* **Dynamic Creator Size Bucketing**: Rather than using hardcoded subscriber counts, the system calculates relative percentiles (Small `<=33.3%`, Medium `<=66.6%`, Big `>66.6%`) dynamically across all candidates discovered.
* **Resilient Soft-Borrow Selector**: Implements stratified sampling logic to select target population sizes. If a creator bucket runs dry, the selector borrows valid candidates from adjacent buckets based on semantic scores.
* **Longitudinal Tracking & Provenance**: Observes the active population over time, preserving historical immutability. If a video is deleted or private, observations log partial failures without breaking the pipeline.
* **Derived Trend Metrics**: Computes daily changes in view counts, likes, and comments to calculate velocities, acceleration (change in velocity), and creator-bucket-specific trends.
* **Graceful API Resilience**: Auto-logs all external API requests (Gemini, YouTube) to track quota costs and errors, with exponential backoffs and offline mock fallbacks.

---

## 📁 Repository Structure

```text
CreatorIQ/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints
│   │   ├── cli/             # Click command-line interface commands
│   │   ├── core/            # Configuration, DB connection, and logger setup
│   │   ├── models/          # Declarative SQLAlchemy models (11 tables)
│   │   ├── services/        # YouTube, Semantic, Selector, and Engine services
│   │   └── main.py          # Application entrypoint
│   ├── alembic/             # Database migration configuration and revisions
│   ├── tests/               # Pytest suite (E2E simulation, Idempotency, etc.)
│   └── requirements.txt     # Python requirements
├── frontend/
│   ├── src/                 # React component layouts, graphs, and styling
│   └── package.json         # Frontend package manifests
├── hardcoded_values_todo.md # List of defaults to move to .env in production
└── README.md                # System documentation
```

---

## 🛠️ Installation & Setup

### 1. Prerequisite Setup
Initialize a virtual environment and load dependencies inside `backend/`:
```bash
cd backend
python -m venv myvenv
myvenv/Scripts/activate     # Windows
source myvenv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the workspace root directory:
```env
POSTGRES_DB="your_postgresql_or_neon_connection_string"
Youtube_API_KEY="your_youtube_api_v3_key"
Gemini_API_Key="your_gemini_api_key"
OLLAMA_BASE_URL="http://localhost:11434"
```

### 3. Run Database Migrations
Deploy schema migrations to your database:
```bash
cd backend
myvenv/Scripts/alembic upgrade head
```

---

## 🏃 Run the Application

### Running System Diagnostics (Mock Mode)
Execute the Click CLI tool to verify connectivity and retrieve system diagnostics:
```bash
cd backend
myvenv/Scripts/python -m app.main diagnostics --mock
```

### Starting the Backend Web Server
Launch the FastAPI development server:
```bash
cd backend
myvenv/Scripts/uvicorn app.main:api_app --host 127.0.0.1 --port 8000
```
The server will boot and automatically seed default trend concepts from `config/concepts.yaml` if the database is empty. You can access the interactive API docs at `http://127.0.0.1:8000/docs`.

### Starting the Frontend Dashboard
Navigate to the `frontend` folder and boot up the Vite server:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser to view active trends, channel lists, and ingestion metrics.

---

## 📟 CLI Command Reference

All CLI commands must be executed from the `backend/` folder using the virtual environment python interpreter:

### 1. General Utility Commands

*   **Diagnostics**: Check database connectivity, YouTube configuration parameters, and row counts across all 11 tables.
    ```bash
    myvenv/Scripts/python -m app.main diagnostics
    ```
    *Add `--mock` flag to run diagnostics using YouTube Mock API.*
*   **Reset Database**: Terminate and clear all database tables (Clean slate). Safe deletion sequence respects foreign key constraints.
    ```bash
    myvenv/Scripts/python -m app.main reset-db
    ```
    *Add `--yes` flag to confirm deletion without prompts.*
*   **Seed Database**: Load default trend concepts from `concepts.yaml` into the `concepts` table.
    ```bash
    myvenv/Scripts/python -m app.main seed-db
    ```

### 2. Ingestion Pipeline Commands

Pipeline commands are nested under the `pipeline` group:

*   **Validate Configurations**: Verify environment settings and validate YAML configuration files.
    ```bash
    myvenv/Scripts/python -m app.main pipeline validate
    ```
*   **Discover Candidates**: Execute search queries on YouTube, filter results by semantic similarity, bucketing, and select active population.
    ```bash
    myvenv/Scripts/python -m app.main pipeline discover
    ```
    *Options: Add `--mock` to use mock client; `--lookback-days <int>` to override discovery window.*
*   **Observe Statistics**: Run daily metric logs (views, likes, comments, subscriber count) for the active population.
    ```bash
    myvenv/Scripts/python -m app.main pipeline observe
    ```
    *Options: Add `--mock` for mock statistics; `--date <ISO-Timestamp>` to override observation timestamp.*
*   **Calculate Metrics**: Generate derived longitudinal features (velocities, growth, acceleration) from raw observations.
    ```bash
    myvenv/Scripts/python -m app.main pipeline metrics
    ```
*   **Aggregate Signals**: Roll up individual video metrics into concept daily aggregates.
    ```bash
    myvenv/Scripts/python -m app.main pipeline signals
    ```
    *Options: Add `--date YYYY-MM-DD` to target specific dates.*
*   **Execute Full Pipeline Run**: Run discovery, observation, metric generation, and aggregation sequentially in a single execution.
    ```bash
    myvenv/Scripts/python -m app.main pipeline run
    ```
    *Options: Add `--mock` for mock execution; `--lookback-days <int>` to override search window; `--date YYYY-MM-DD` to execute for specific dates.*

---

## 🧪 Testing

The codebase includes an integration and unit test suite verifying mathematical derivations, retry/failure injection boundaries, and system idempotency.

Run the tests using:
```bash
cd backend
myvenv/Scripts/pytest tests -v
```

