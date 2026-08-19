# YouTube Trend Prediction System Walkthrough

I have successfully finalized the development, debugging, and verification of the YouTube Trend Prediction Ingestion System. The codebase includes a FastAPI REST API server, a Click CLI terminal tool, a Vite React dashboard interface, and a robust test suite.

---

## 1. System Components Delivered

### 🐍 FastAPI Backend (`backend/`)
- **API Endpoints (`app/api/endpoints.py`)**: Endpoints for trend concepts listing, historical signal trajectories, system metrics, manual backfill triggers, and request log tracing.
- **ORM Models (`app/models/models.py`)**: 11 fully mapped tables supporting cascading deletes, constraints, indexes, and full chronological logging.
- **Service Layer (`app/services/`)**:
  - `YouTubeService`: Integrates with YouTube Data API v3 with quota tracking, timeouts, retries, and a deterministic offline Mock mode.
  - `SemanticService`: Calculates cosine similarities using Ollama (local) or Gemini (remote `models/embedding-001`) with automatic pseudo-embedding fallback.
  - `SelectorService`: Implements Creator classification by subscriber percentiles and deterministically selects the population with soft-borrow recovery.
  - `DiscoveryEngine`, `ObservationEngine`, `MetricsEngine`, `AggregationEngine`: Run longitudinal trend tracking, capture views/likes/comments daily, calculate velocities/growth/acceleration, and generate daily aggregated signals.

### 💻 click CLI Interface
- Unified command line utility in `backend/app/cli/commands.py` supporting `diagnostics`, database health checks, and mock pipeline runs.

### ⚛️ Vite React Frontend (`frontend/`)
- A modern UI dashboard featuring trend analysis graphs, active video details panels, and a comprehensive diagnostics view to display database sizes and API query logs.

---

## 2. Issues & Bug Fixes Resolved

During the verification phase, several crucial bugs were diagnosed and corrected:

1. **SQLite Autoincrement Primary Key Crash**:
   - *Problem*: SQLite does not autoincrement `BigInteger` primary keys without manual sequencing, causing `NOT NULL constraint failed: video_observations.id` and `api_request_logs.id` integrity errors.
   - *Fix*: Modified primary keys and matching foreign keys in [models.py](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/backend/app/models/models.py) to `Integer` (SERIAL), which works perfectly with auto-increment across both SQLite and PostgreSQL.
2. **SQLAlchemy Detached Instance Error**:
   - *Problem*: Accessing properties on ORM records after closing database sessions threw `DetachedInstanceError`.
   - *Fix*: Configured both the core `SessionLocal` in [database.py](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/backend/app/core/database.py) and test `TestingSessionLocal` in [conftest.py](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/backend/tests/conftest.py) with `expire_on_commit=False`.
3. **Substring Mismatch in Mock Similarity Filtering**:
   - *Problem*: The mock semantic similarity selector used simple substring searches (`v in t2`), leading to `mock_vid_1` matching against `mock_vid_10`, `mock_vid_11`, and `mock_vid_12`. This selected unrelated videos and distorted the creator-size percentiles.
   - *Fix*: Updated similarity lambdas in tests to use regex word boundaries (`rf"\b{v}\b"`).
4. **Missing CLI Dependencies**:
   - *Problem*: Click CLI crashed when `tabulate` was missing.
   - *Fix*: Added a graceful try-except import fallback in `commands.py`.
5. **Deprecated FastAPI Event Hooks**:
   - *Problem*: FastAPI failed to start due to the deprecated `@api_app.on_startup` decorator.
   - *Fix*: Updated to the standard `@api_app.on_event("startup")` hook in [main.py](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/backend/app/main.py).

---

## 3. Test Verification Results

All 3 automated test suites in the `backend/tests/` folder run and pass successfully in the local environment:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Projects\Desktop\agy2-projects\CreatorIQ
plugins: anyio-4.14.2, mock-3.15.1
collected 3 items

backend\tests\test_e2e.py .                                              [ 33%]
backend\tests\test_idempotency.py .                                      [ 66%]
backend\tests\test_youtube_mock.py .                                     [100%]

======================== 3 passed, 1 warning in 7.47s =========================
```

- **`test_e2e.py`**: Asserts 3 days of simulation with correct medians, percentiles, velocities, and daily aggregations.
- **`test_idempotency.py`**: Ensures re-running pipeline stages does not duplicate canonical videos, observations, or daily signals.
- **`test_youtube_mock.py`**: Verifies partial observation failures (missing/private videos) complete without crashing.

---

## 4. How to Run and Verify the System

### 🧪 Run the Test Suite
From the workspace root, execute:
```bash
backend/myvenv/Scripts/pytest backend/tests -v
```

### 📊 Run the CLI Diagnostics
From the `backend` folder, execute:
```bash
myvenv/Scripts/python -m app.main diagnostics --mock
```

### ⚡ Start the Backend Server
From the `backend` folder, execute:
```bash
myvenv/Scripts/uvicorn app.main:api_app --host 127.0.0.1 --port 8000
```
*Note: The server automatically seeds the "AI Agents" concept upon startup if database tables are empty.*

### 🖥️ Start the Frontend Dashboard
From the `frontend` folder, run:
```bash
npm install
npm run dev
```
And navigate to `http://localhost:5173`.
