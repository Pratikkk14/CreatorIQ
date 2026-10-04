# TODO: Fitness Category Pipeline Implementation & Integration Checklist

This document details the completed codebase updates for the 10 Fitness Concepts real-time pipeline and outlines remaining tasks for testing, verification, and microservices system merging (`Yash_creatorIQ`).

---

## 📅 Status Overview
- **Phase**: Implementation & Feature Enhancement Completed (100% Passing Tests)
- **Category**: Fitness
- **Tracked Concepts Count**: 10 Concepts
- **Schedule**: Real-Time 3x Daily (00:00, 08:00, 16:00 UTC)
- **D-3 Window**: Removed (`LAG_DAYS=0` for real-time candidate search)

---

## ✅ Completed Codebase & Feature Enhancements

1. **Composite Video Trend Scoring Engine**:
   - Each video in the candidate population is assigned a calculated `trend_score` (0–100 scale):
     $$\text{trend\_score} = 0.45 \cdot \text{norm\_reach} + 0.35 \cdot \text{norm\_interaction} + 0.20 \cdot \text{norm\_semantic}$$
   - Daily signals calculate and store `trend_score_median` across all fit population videos.

2. **Real-Time Data Ingestion & 3x/Day Schedule**:
   - Removed the forced $D-3$ window by setting default `lag_days: int = 0` in `backend/app/core/config.py`.
   - Reconfigured `BackgroundScheduler` in `backend/app/core/scheduler.py` to trigger 3 times per day automatically at `00:00`, `08:00`, and `16:00` UTC.

3. **10 Tracked Fitness Concepts (`backend/config/concepts.yaml`)**:
   - Registered all 10 Fitness concepts with UUID strings:
     1. `Diet` (`10000000-0000-0000-0000-000000000001`)
     2. `Muscle training` (`10000000-0000-0000-0000-000000000002`)
     3. `Calisthenics` (`10000000-0000-0000-0000-000000000003`)
     4. `Gym Entertainment` (`10000000-0000-0000-0000-000000000004`)
     5. `Gym time management` (`10000000-0000-0000-0000-000000000005`)
     6. `Protein intake strategies` (`10000000-0000-0000-0000-000000000006`)
     7. `Bodybuilding` (`10000000-0000-0000-0000-000000000007`)
     8. `Gym reviews` (`10000000-0000-0000-0000-000000000008`)
     9. `How to do exercises` (`10000000-0000-0000-0000-000000000009`)
     10. `How to improve yourself` (`10000000-0000-0000-0000-000000000010`)

4. **Decoupled Standalone Backend REST API**:
   - Implemented `/api/latest-entries` endpoint returning top populated video entries ordered by composite `trend_score` descending.
   - Restructured `/api/diagnostics`, `/api/signals`, `/api/provenance`, and `/api/concepts` to serve clean JSON. Enables separate backend hosting on Render/AWS and easy merging into `Yash_creatorIQ`.

5. **Enhanced React Dashboard (`frontend/src/`)**:
   - Added **Top Populated Entries Leaderboard** showing real-time video titles, concept badges, channel tiers, reach ratios, and Trend Score gauges.
   - Added real-time database status & 3x daily scheduler indicators.

---

## 📋 Remaining TODOs for System Integration

### Phase 1: Local System Run
- [ ] Run database recreate & seed:
  ```bash
  backend/myvenv/Scripts/python -m app.main recreate-db --yes
  backend/myvenv/Scripts/python -m app.main seed-db
  ```
- [ ] Run real-time ingestion pipeline:
  ```bash
  backend/myvenv/Scripts/python -m app.main pipeline run --mock
  ```
- [ ] Start FastAPI backend server:
  ```bash
  backend/myvenv/Scripts/uvicorn app.main:api_app --host 127.0.0.1 --port 8000
  ```
- [ ] Start Vite React frontend:
  ```bash
  cd frontend && npm run dev
  ```

### Phase 2: Integration & Merging into `Yash_creatorIQ`
- [ ] Map `ConceptDailySignal` and `trend_score_median` outputs to `Yash_creatorIQ`'s `TrendConcept` and `ConceptSignal` repositories in `backend/services/trend/`.
- [ ] Connect `top_outlier_video_id` and `outlier_streak` signals to `Yash_creatorIQ` Strategy Brief generation (`strategy_service.py`).
