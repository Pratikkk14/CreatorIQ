# CreatorIQ — Real-Time Trend Intelligence Frontend

This directory contains the Vite + React single-page application (SPA) dashboard for monitoring real-time trend ingestion pipelines, inspecting concept signals, and tracking populated video entries for **CreatorIQ**.

---

## 🖥️ Dashboard Overview & Features

The frontend provides an interactive workspace built with modern UI design principles, glassmorphism card surfaces, and dynamic charts:

1. **Real-Time 3x/Day Ingestion Controls**:
   - Status indicators displaying DB connectivity, active tracked concepts, and generated daily signals.
   - One-click triggers to execute manual background ingestion runs.

2. **Top Populated Entries Leaderboard**:
   - Real-time leaderboard table displaying top video entries populated in recent pipeline runs.
   - Shows video titles with direct YouTube links, concept category badges, channel tiers (`BIG`, `MEDIUM`, `SMALL`), reach ratios, and visual **Trend Score progress gauges** (0–100 scale).

3. **Concept Details & Lineage Provenance**:
   - Interactive trend signal graphs (Reach Ratio, Interaction Density, Semantic Relevance).
   - Video-level lineage drilldown showing exact contributor rankings and per-video metrics.

4. **Diagnostics & Raw Data Inspector**:
   - View database table row counts and raw JSON payloads (`concepts`, `concept_daily_signals`, `api_request_logs`).

---

## 📁 Project Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx       # Real-time leaderboard, stats, and concept creation
│   │   ├── ConceptDetail.jsx   # Interactive trend charts and provenance table
│   │   ├── Diagnostics.jsx     # System health and pipeline execution controls
│   │   └── ViewData.jsx        # Raw database table payload inspector
│   ├── services/
│   │   └── api.js              # API client connecting to FastAPI backend
│   ├── App.jsx                 # Sidebar navigation & tab router
│   ├── App.css                 # Dark theme design system & tokens
│   └── main.jsx                # React app entry point
├── package.json
└── vite.config.js
```

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Backend API URL
By default, `src/services/api.js` points to `http://localhost:8000/api`. If hosting the backend remotely, update `API_BASE_URL` in `src/services/api.js`.

### 3. Run Development Server
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.
