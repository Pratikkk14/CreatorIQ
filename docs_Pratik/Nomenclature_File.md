# Unified Nomenclature & Integration Standard

This document establishes the official naming conventions, variable dictionaries, and API structures for CreatorIQ. Because the frontend and backend are developed independently by two separate developers, strict adherence to this standard is required to prevent integration errors during merge and deployment.

---

## 📐 1. General Naming Conventions

| Layer | Standard | Case Style | Examples |
| :--- | :--- | :--- | :--- |
| **Backend Code (Python)** | Python PEP 8 | `snake_case` | `user_id`, `get_channel_metrics` |
| **Frontend Code (React/TS)**| JavaScript Standard | `camelCase` | `userId`, `getChannelMetrics` |
| **API JSON Payloads** | REST Uniform Standard | `snake_case` | `{"trend_velocity_score": 8.7}` |
| **Database Columns** | PostgreSQL Standard | `snake_case` | `oauth_token_encrypted` |
| **API Endpoints** | RESTful Slugs | `kebab-case` | `/v1/trends/history-snapshots` |
| **HTTP Headers** | RFC Custom Header | `Train-Case` | `X-Internal-Service-Token` |

---

## 📡 2. API Contract Standards

To minimize integration mismatch, all network payloads passed over HTTP/REST must be in **`snake_case`**. 

* **Frontend Action**: When sending payloads to the backend, map React objects from `camelCase` to `snake_case`. When receiving payloads, parse them back to `camelCase` or use them directly if mapped via an API client transformer.
* **Backend Action**: Return all responses in `snake_case` directly via Pydantic model schemas.

### Standard Response Envelope
All API endpoints must return data wrapped in this structured envelope:
```json
{
  "data": {},
  "meta": {
    "request_id": "8f8c85a0-efdb-46f9-b883-8a3fb796be03",
    "timestamp": "2026-08-16T08:00:00Z"
  }
}
```

### Standard Error Envelope
When an operation fails, return the standard error structure:
```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "The provided access token has expired.",
    "details": {}
  },
  "meta": {
    "request_id": "8f8c85a0-efdb-46f9-b883-8a3fb796be03"
  }
}
```

---

## 📖 3. Shared Variable Dictionary

Use these exact variable names for both Frontend (when receiving JSON keys) and Backend. Do not introduce custom abbreviations.

### User & Authentication
* `user_id` (UUID): Primary key identifying the creator.
* `email` (string): Authenticated email address.
* `password_hash` (string, BE only): Hashed password.
* `access_token` (string): Short-lived JWT bearer token.
* `refresh_token` (string): Long-lived rotation token.
* `plan_tier` (enum): Gated features; values must be: `free`, `pro`, `enterprise`.

### Channel & Creator Profiles
* `channel_id` (string): The YouTube Channel ID.
* `channel_title` (string): Display name of the YouTube Channel.
* `niche` (string): Main content category (e.g. `tech`, `finance`, `gaming`).
* `target_geo` (string): 2-letter ISO country code for target audience (e.g., `US`, `GB`, `IN`).
* `content_format` (enum): `shorts`, `longform`, `hybrid`.
* `tone_voice` (string): Creator's style (e.g., `energetic`, `sarcastic`, `educational`).

### Trends Engine
* `concept_id` (UUID): Unique identifier of a trend topic.
* `concept_title` (string): Canonical title of the trend concept.
* `trend_velocity_score` / `tvs` (float): Speed/growth rate of the trend.
* `raw_momentum` (float): Google Trends search growth indicator.
* `is_saved` (boolean): Whether the user saved this trend.
* `feed_id` (UUID): Identifier of a creator's historical trend feed snapshot.

### Strategy Briefs
* `brief_id` (UUID): Unique ID for the generated strategy brief.
* `hook_structure` (string): Script hook ideas.
* `retention_points` (array): Retention optimization points.
* `call_to_action` (string): Script CTA.
* `suggested_titles` (array of strings): AI generated title options.

---

## 🔑 4. Environment & Production Placeholders

This section outlines variables that will be used for future production setups. Codebases must support these placeholders out of the box.

### Frontend (.env)
* `VITE_API_URL`: Path to the API Gateway.
  * *Dev*: `http://localhost:8000/v1`
  * *Prod (Vercel)*: `https://api.creatoriq.com/v1` (Placeholder target)
* `VITE_GOOGLE_CLIENT_ID`: Google Client ID for frontend button initialization.

### Backend (.env)
* `ENVIRONMENT`: Running mode. Must be either `development` or `production`.
* `DATABASE_URL`: Asynchronous DB connection string.
  * *Format*: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>`
* `REDIS_URL`: Cache database link.
  * *Format*: `redis://<host>:<port>/<db_index>`
* `QDRANT_URL`: Vector search endpoint.
  * *Format*: `http://<host>:6333`
* `INTERNAL_SERVICE_TOKEN`: Shared secret to authorize microservice requests.
* `AES_ENCRYPTION_KEY`: Fernet symmetric key to encrypt Google OAuth tokens at rest.
* `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Credentials to query YouTube OAuth.
* `YOUTUBE_API_KEY`: API key to fetch YouTube trends statistics.
* `SERPAPI_API_KEY`: API key to fetch Google Trends data.
* `OPENROUTER_API_KEY`: Access token to open Router for LLM strategy briefing.
* `MODEL_NAME`: OpenRouter model slug (e.g., `openai/gpt-4o-mini`).

---

## 💻 5. Integration Code Patterns

### Frontend (TypeScript / Axios Client)
To ensure smooth integration, use an Axios interceptor or explicit payload transformers to handle `camelCase` (JS) to `snake_case` (API) translation.

```typescript
import axios from 'axios';
import snakeCaseKeys from 'snakecase-keys';
import camelcaseKeys from 'camelcase-keys';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Interceptor to convert outbound requests to snake_case
api.interceptors.request.use((config) => {
  if (config.data) {
    config.data = snakeCaseKeys(config.data, { deep: true });
  }
  return config;
});

// Interceptor to convert inbound responses to camelCase
api.interceptors.response.use((response) => {
  if (response.data) {
    response.data = camelcaseKeys(response.data, { deep: true });
  }
  return response;
});

export default api;
```

### Backend (FastAPI / Pydantic v2)
In FastAPI, configure Pydantic models to accept incoming requests in either `snake_case` or automatically handle aliases. Returning payloads in `snake_case` is default behavior.

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake

class UserProfileSchema(BaseModel):
    # Setting model configuration for clean serialization
    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,
        from_attributes=True
    )
    
    user_id: str
    channel_id: str
    trend_velocity_score: float
```
