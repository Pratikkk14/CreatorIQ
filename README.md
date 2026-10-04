# CreatorIQ — Real-Time Trend Intelligence Pipeline

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg)](https://vitejs.dev)

> 💡 **Project Context**: This repository is a specialized real-time ingestion pipeline component within the larger **CreatorIQ** AI SaaS platform. It handles real-time YouTube search candidate discovery, multi-stage semantic filtering, relative channel percentiles, composite **Trend Scoring**, and outlier tracking across monitored niche concepts.

---

## 🎯 Goal-Oriented Project Overview

The objective of this project is to provide a robust, automated **Real-Time YouTube Trend Intelligence Engine** that operates continuously (scheduled 3 times daily at 00:00, 08:00, 16:00 UTC) to identify rising video concepts, quantify creator performance, and produce normalized daily trend signals.

Rather than relying on static creator lists, this pipeline dynamically evaluates real-time YouTube candidate populations for **10 tracked Fitness concepts**:

| # | Concept Name | Focus Area |
| :--- | :--- | :--- |
| 1 | **Diet** | Nutrition, meal plans, calorie deficit/surplus, gym meal prep |
| 2 | **Muscle training** | Hypertrophy routines, resistance training, weight lifting, muscle growth |
| 3 | **Calisthenics** | Bodyweight workouts, gymnastics strength, muscle-ups, pull-up tutorials |
| 4 | **Gym Entertainment** | Gym humor, fitness challenges, PR reactions, workout memes |
| 5 | **Gym time management** | Workout efficiency, busy gym routines, quick 30-min sessions |
| 6 | **Protein intake strategies** | Whey protein timing, daily protein requirements, recovery nutrition |
| 7 | **Bodybuilding** | Competitive physique, posing routines, muscle symmetry, stage prep |
| 8 | **Gym reviews** | Commercial gym tours, equipment reviews, supplement reviews, lifting gear |
| 9 | **How to do exercises** | Bench press form tutorials, squat technique, deadlift form guides |
| 10 | **How to improve yourself** | Fitness mindset, physical transformation guides, workout discipline |

---

## 🗺️ High-Level System Architecture & Ingestion Flow

```mermaid
graph TD
    A[Cron Scheduler / API Trigger] -->|3x Daily: 00:00, 08:00, 16:00 UTC| B[1. Concept Ingestion Window]
    B -->|Search Query Generation| C[2. YouTube Data API v3]
    
    C -->|Up to 40 Candidates| D[3. Batch Metadata Fetch]
    D -->|Views, Likes, Subs, Duration| E{4. Multi-Stage Filter Gate}
    
    E -->|Stage 1: Hard Gate| F[Views >= 50, Subs >= 100, Desc >= 30]
    E -->|Stage 2: Language Gate| G[English Language Validation]
    E -->|Stage 3: Semantic Identity Gate| H[SentenceTransformer MiniLM Similarity]
    
    H -->|Match Score > Threshold| I[5. Fit Population Selection]
    I --> J[6. Relative Percentile Bucketing Q25/Q75]
    J -->|Small / Medium / Big Tiers| K[Population Composition Counts]
    
    I --> L[7. Metric & Trend Score Engine]
    L -->|Reach Ratio = views/subs / 100| M[Composite Trend Score 0-100]
    L -->|Interaction Density = likes+comments/views| M
    
    I --> N[8. Statistical Outliers μ + 2σ]
    N -->|Max Reach Ratio Outlier| O[Top Outlier & Streak Counter]
    
    M --> P[(9. ConceptDailySignal Database Record)]
    K --> P
    O --> P
```

---

## 📂 Repository Directory Documentation

The codebase is organized into clean, decoupled directories with detailed internal documentation:

- 📖 [**Backend Documentation (`backend/README.md`)**](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/backend/README.md)
  - Full details on FastAPI REST endpoints (`/api/diagnostics`, `/api/concepts`, `/api/signals`, `/api/latest-entries`, `/api/provenance`).
  - Mathematical metric formulas (Reach Ratio, Interaction Density, Composite Trend Score, Outlier $\mu+2\sigma$).
  - Multi-stage pipeline logic, SQLAlchemy ORM models (`Concept`, `ConceptDailySignal`), and CLI command reference.

- 📖 [**Frontend Documentation (`frontend/README.md`)**](file:///d:/Projects/Desktop/agy2-projects/CreatorIQ/frontend/README.md)
  - Single-page Vite + React UI dashboard setup.
  - Real-Time 3x/Day status panel, **Top Populated Entries Leaderboard** with Trend Score progress gauges, and raw database inspection tools.

---

## 🚀 Quickstart & Setup Guide

### 1. Backend Setup & Data Seeding

```bash
cd backend

# 1. Create and activate Python virtual environment
python -m venv myvenv
myvenv\Scripts\activate      # Windows
source myvenv/bin/activate   # macOS/Linux

# 2. Install backend dependencies
pip install -r requirements.txt

# 3. Create .env from template and add Youtube_API_KEY
cp ../.env-samples ../.env

# 4. Recreate database tables with new schema
myvenv\Scripts\python -m app.main recreate-db --yes

# 5. Seed the 10 Fitness concepts into the database
myvenv\Scripts\python -m app.main seed-db

# 6. Start the FastAPI backend server
myvenv\Scripts\uvicorn app.main:api_app --host 127.0.0.1 --port 8000
```

*Backend API Docs*: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Frontend Setup

In a new terminal window:

```bash
cd frontend

# Install frontend dependencies
npm install

# Start Vite React development server
npm run dev
```

*Frontend Dashboard*: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing & Verification

Run the automated test suite to verify pipeline calculations, semantic similarity filtering, and idempotency:

```bash
cd backend
myvenv\Scripts\pytest tests -v
```

---

## 📄 License & Ecosystem Context

Part of the **CreatorIQ** AI SaaS ecosystem. Proprietary — All rights reserved.
