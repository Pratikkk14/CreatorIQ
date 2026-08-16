# Deployment Instructions & Architecture Critique

This document reviews how the previous deployment architecture functioned, rates the VM + Docker approach, and details how to execute a temporary deployment of the current system to **Vercel** (frontend) and **Render** (backend).

---

## 🔍 1. How the Previous Azure VM + Docker Deployment Worked

The old deployment pipeline was automated via local scripting and CI/CD pipelines:
1. **GitHub Actions Workflow** (`.github/workflows/backend-deploy.yml`):
   * Triggered on pushes to the `main` branch when files in the `backend/` directory changed.
   * Leveraged SSH connections via `appleboy/ssh-action` to connect to an Azure VM.
   * Read environment secrets (`ENV_FILE`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`) stored inside GitHub Secrets.
2. **PowerShell script** (`deploy.ps1`):
   * An alternative manual script for developers to deploy straight from their local terminals.
   * Copied production secret configurations (`.env.production`) and JWT keys (`jwt_private.pem`, `jwt_public.pem`) directly to the VM directory `~/CreatorIQ/backend/` using `scp` (Secure Copy Protocol).
3. **Execution Steps on the Azure VM**:
   * **Code Pulling**: Cleaned the directory, fetched remote changes, and performed a hard reset (`git reset --hard origin/main`) to match production code.
   * **Secrets Writing**: Injected the env vars file to `backend/.env` and wrote PEM keys to `backend/secrets/`.
   * **Docker Orchestration**: Executed `docker compose down` and `docker compose up -d --build` to build images and spin up containers in the background (API Gateway, Auth, Trend, Strategy, etc., along with Postgres and Redis).
   * **Database Inits**: Ran one-shot Docker containers using the `db-push` profile to directly sync SQLAlchemy models into the Postgres database.
   * **Priming the Trend Engine**: Extracted the service token from the running container and sent an internal HTTP POST to the Trend service (`/internal/trends/collect`) to scrape Google Trends and YouTube API for first-run concepts.

---

## 📈 2. Critique of the Old VM Deployment

### Ratings: 
* **Reliability**: 6/10
* **Scalability**: 4/10
* **Development Convenience**: 8/10
* **Operational Complexity**: 7/10

### Why is this more complex than standard Vercel/Render deploys?
In simple React/Node apps, developers build static files (`npm run build`) and host them directly on a CDN (like Vercel). The backend is usually a single API service connected to one database. 
The old CreatorIQ system is a **microservices ecosystem**. It does not run as one program; it runs as **8 separate web apps**, plus a SQL database (Postgres), an in-memory cache (Redis), and a vector search engine (Qdrant). To keep them running together, the previous developer used Docker Compose on a single Azure Virtual Machine (VM) to act as a local cloud.

### Pros (Why the developer chose this):
* **Cost Efficiency**: Running 8 separate services on managed cloud platforms (like AWS ECS or Render) is very expensive. A single Azure VM hosting all containers in Docker is extremely cheap ($10-$20/month).
* **Isolation**: If the ML service crashes or runs out of memory, it does not bring down the Auth or Gateway services.
* **Database control**: Running Postgres, Redis, and Qdrant in containers on the same VM avoids expensive managed database subscriptions.

### Cons (The risks and problems):
* **Single Point of Failure (SPOF)**: If the single Azure VM goes down or gets network throttled, the entire application (Gateway, databases, and APIs) crashes.
* **Resource Contention**: The VM has fixed CPU/RAM. If building new Docker images during deployment consumes all CPU, active users will experience API timeouts.
* **State Management Issues**: If the VM hard drive fills up (common with Docker images prune failure), Postgres databases can corrupt.
* **Git Hard Reset on Prod**: Pulling code and running `git reset --hard` on production environments is risky. Network disconnects mid-pull leave the server in a broken state.

---

## 🚀 3. Temporary Deployments (Vercel + Render)

To bypass the complex Azure VM + Docker configuration while recovering access and planning upgrades, follow this guide to set up a temporary deployment.

```
┌──────────────────┐               ┌──────────────────┐
│ Frontend (React) │  ──────────▶  │  Backend API     │
│ Hosted on Vercel │               │ Hosted on Render │
└──────────────────┘               └──────────────────┘
                                     │         │
                                     ▼         ▼
                                 [Postgres] [Redis]
                                  (Render)   (Render)
```

### 1. Frontend: Deploying to Vercel

Vite/React apps are static and deploy easily to Vercel:

1. **Prerequisites**:
   * Ensure `vercel.json` exists in the `frontend` folder with SPA routing support:
     ```json
     {
       "rewrites": [
         { "source": "/(.*)", "destination": "/index.html" }
       ]
     }
     ```
2. **Steps**:
   * Log into [Vercel](https://vercel.com/) and click **Add New** → **Project**.
   * Connect your Git repository.
   * Set **Root Directory** to `frontend`.
   * **Framework Preset**: Vite.
   * **Build Settings**:
     * Build Command: `npm run build`
     * Output Directory: `dist`
   * **Environment Variables**:
     * Add `VITE_API_URL` pointing to your deployed Render gateway (e.g., `https://creatoriq-gateway.onrender.com/v1`).
   * Click **Deploy**.

---

### 2. Backend: Deploying to Render

Since Render charged per service, running 8 separate microservices will exceed free limits and become costly. We recommend **Option A** (Collapsing into a Monolith) for the temporary deploy.

#### Option A: The Monolithic Collapse (Recommended for Temporary/Free Tiers)
Combine the routes of all microservices into a single backend service.
1. Create a unified entry point file in your backend (e.g., `backend/main.py`):
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   from app.services.auth.app.api.v1.endpoints import auth_router
   from app.services.trend.app.api.v1.endpoints import trend_router
   # Import other service routes...

   app = FastAPI(title="CreatorIQ Monolith API")

   # Crucial CORS configuration
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-vercel-app.vercel.app"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   # Mount all microservice routes onto the same API instance
   app.include_router(auth_router, prefix="/v1/auth")
   app.include_router(trend_router, prefix="/v1/trends")
   # Mount channel, strategy, planner, etc.
   ```
2. Deploy this single Python Web Service on Render:
   * **Build Command**: `pip install -r requirements.txt` (Consolidate all microservice libraries).
   * **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Option B: Deploying the Microservices Individually
If you want to keep the microservices architecture, you will need to create:
1. **Render Managed PostgreSQL**:
   * Spin up a database instance.
   * Copy the connection string (`postgres://...`).
2. **Render Managed Redis**:
   * Spin up a Redis instance.
   * Copy the Redis URL.
3. **Deploy Microservices**:
   * Create separate Render Web Services for:
     * `Auth Service`
     * `Trend Service`
     * `Strategy Service`
     * `Planner Service`
     * `Analytics Service`
   * Set their respective ports and environment variables (`DATABASE_URL`, `REDIS_URL`, `INTERNAL_SERVICE_TOKEN`).
4. **Deploy the API Gateway**:
   * Create a final Render Web Service pointing to the `backend/services/api-gateway` folder.
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   * **Environment Variables**: Provide URLs for other Render microservices:
     * `AUTH_SERVICE_URL`: `https://creatoriq-auth.onrender.com`
     * `TREND_SERVICE_URL`: `https://creatoriq-trend.onrender.com`
     * (and so on)
   * This Gateway will route inbound requests to respective microservices over public HTTPS.

#### CORS and Base URL Configurations (Required for both Options)
To ensure the Vercel Frontend can read the Render Backend without browser security blocking:
1. **Backend CORS**: Configure `CORSMiddleware` in your Gateway (or collapsed Monolith) main app file:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-vercel-domain.vercel.app", "http://localhost:5173"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. **Frontend Base URL**: In React Axios configurations (typically `src/lib/api.ts`), read the VITE env value:
   ```typescript
   const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/v1';
   ```
