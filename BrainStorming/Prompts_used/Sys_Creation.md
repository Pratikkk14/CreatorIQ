# Antigravity Master Implementation Prompt

## YouTube Trend Prediction System — Phase 0 through Phase 4

You are working inside an existing YouTube Trend Prediction project.

Your task is to inspect the existing repository, understand what has already been implemented, preserve useful existing work, and then implement the complete **Phase 0 → Phase 4 data foundation and operational pipeline in one coherent implementation**.

Do NOT treat this as a skeleton-generation task.

I do not want a result where files/classes/endpoints merely exist.

I want the system to **actually execute the intended data-engineering workflow correctly**, with realistic database state, correct YouTube API behavior, reproducible selection, immutable observations, derived metrics, concept-level signals, proper error handling, and automated behavioral validation.

The final system must be capable of running the pipeline end-to-end against either the real YouTube API or a deterministic mock/test provider.

---

# 1. Core objective

Build a reliable longitudinal YouTube observation system that follows this lifecycle:

```text
Concept Configuration
        ↓
Search Discovery
        ↓
Candidate Registry
        ↓
Candidate Filtering
        ↓
Semantic Relevance Scoring
        ↓
Creator-Size Classification
        ↓
Population Selection
        ↓
Video Registry
        ↓
Repeated Video Observation
        ↓
Immutable Video Time Series
        ↓
Video-Level Derived Metrics
        ↓
Concept-Level Aggregation
        ↓
Concept Daily Time Series
```

The system is intended to become the data foundation for future PreWHether / PreWHen-style forecasting.

Do NOT prematurely implement the forecasting model.

The objective of Phases 0–4 is to produce a **research-ready, reproducible, longitudinal dataset**.

---

# 2. Fundamental data-model rule

The most important architectural rule is:

> A video discovered today does NOT contain historical public statistics.

Do not attempt to reconstruct historical views/likes/comments from the current YouTube API response.

If a video is discovered on August 13 and observed:

```text
Aug 13 → 1,000 views
Aug 14 → 3,000 views
Aug 15 → 7,000 views
Aug 16 → 15,000 views
```

then those observations constitute the actual observed trajectory.

The system must therefore:

1. Discover videos early.
2. Register them immediately.
3. Start observation immediately.
4. Re-observe them on subsequent scheduled runs.
5. Store every observation immutably.
6. Derive temporal metrics from those observations.

Never overwrite historical observations.

---
# 3:First action inspect the repo
As currently we are going to make the project from stracth u can safely assume that we have not created anything I have my old system here in this 
> location: D:\Projects\Desktop\agy2-projects\CreatorIQ\Old_System

but the prblm was it was faulty so i dont want u to go and read through those files just to halluicate urself and confuse in implementation plan  

# 4. Environment requirements

Create/update `.env.example` and configuration loading.
NOTE: Here all these secrets may be required or not we dont know but for the time being i have these env present with me
```Current env
Environment = Developer

POSTGRES_DB=<Neon_DB_Link_For_Postgres>

Youtube_API_KEY=<Google_console_API_Service_activated_then_key_generated>
YOUTUBE_API_BASE_URL=https://www.googleapis.com/youtube/v3
YOUTUBE_API_TIMEOUT_SECONDS=30 
YOUTUBE_API_MAX_RETRIES=3 
YOUTUBE_API_RETRY_BACKOFF_SECONDS=2

Youtube_OAUTH_CLIENT_ID=<Client_ID_from_OAuth>
Youtbe_OAUTH_CLIENT_SECRET=<Client_Secret_from_OAuth>
YOUTUBE_OAUTH_ENABLED=true 

PUBLIC_APP_URL = https://localhost:9009
GOOGLE_REDIRECT_URI = https://localhost:9009/api/oauth2callback
```
Ideal environment variables:

```Ideal env
DATABASE_URL=
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_ECHO=false

YOUTUBE_API_KEY=
YOUTUBE_API_BASE_URL=https://www.googleapis.com/youtube/v3
YOUTUBE_API_TIMEOUT_SECONDS=30
YOUTUBE_API_MAX_RETRIES=3
YOUTUBE_API_RETRY_BACKOFF_SECONDS=2

YOUTUBE_OAUTH_ENABLED=true
YOUTUBE_OAUTH_CLIENT_SECRET_FILE=
YOUTUBE_OAUTH_TOKEN_FILE=

SCHEDULER_ENABLED=true
DISCOVERY_CRON=
OBSERVATION_CRON=
SIGNAL_CRON=
TIMEZONE=Asia/Kolkata

APP_ENV=development
LOG_LEVEL=INFO
LOG_FORMAT=json

OLLAMA_BASE_URL=
OLLAMA_EMBEDDING_MODEL=

ENABLE_API_REQUEST_LOGGING=true
ENABLE_METRICS=true
DRY_RUN=false
```

Do not put research parameters such as candidate limits, semantic thresholds, population sizes, or creator-stratification percentages into `.env`.

Those belong in application configuration such as:

```text
config/
    concepts.yaml
    pipeline.yaml
    selection.yaml
```

The application must fail clearly when mandatory secrets/configuration are missing.

Never hard-code API keys, passwords, tokens, or database credentials.

So when we are creating the system if u feel we need to add these into env or remove something from the env tell me i will do so and always refer the env.sample file as it will always carry the updated snapshot of the env without credentials

---

# 5. Database

Use PostgreSQL with SQLAlchemy unless the existing project already has a working equivalent that should be preserved.

Do not introduce unnecessary infrastructure.

Use TimeScaleDB for time series data

Use migrations.

Do not rely on `Base.metadata.create_all()` as the primary production schema-management mechanism.

---

# 6. Required database schema

Implement approximately the following schema.

## `concepts`

```text
id                  PK
name
description
active
search_queries      JSON/JSONB
created_at
updated_at
```

Purpose:

Represents a monitored concept/topic.

---

## `channels`

```text
channel_id           PK
title
subscriber_count
video_count
country
published_at
first_seen_at
last_observed_at
created_at
updated_at
```

Purpose:

Canonical registry of YouTube channels.

Do not store daily channel statistics here.

---

## `videos`

```text
video_id             PK
channel_id           FK
title
description
published_at
duration_seconds
category_id
language
thumbnail_url
first_discovered_at
last_seen_at
status
created_at
updated_at
```

Purpose:

Canonical video registry.

Do NOT put mutable daily view counts here.

---

## `search_runs`

```text
id                   PK
concept_id           FK
started_at
completed_at
published_after
published_before
query
requested_limit
returned_count
status
error_message
```

Purpose:

Records each discovery operation and preserves provenance.

---

## `video_candidates`

```text
id                   PK
search_run_id        FK
video_id             FK
semantic_score
language_score
metadata_score
creator_size_bucket
selection_status
selection_rank
rejection_reason
evaluated_at
```

Purpose:

Store ALL discovered candidates, not only selected videos.

A candidate rejected by the population selector must remain in this table.

---

## `population_runs`

```text
id                   PK
concept_id           FK
search_run_id        FK
target_size
actual_size
selection_strategy
started_at
completed_at
status
```

Purpose:

Represents one population-selection execution.

---

## `population_members`

```text
population_run_id    FK
video_id             FK
creator_size_bucket
selection_score
rank
selected_at

PRIMARY KEY(population_run_id, video_id)
```

Purpose:

Represents which videos were selected for a specific monitoring population.

Do NOT add a permanent `selected=true` field to `videos`.

The same video may participate in different experiments/populations.

---

## `video_observations`

This is the most important table.

```text
id
video_id
observed_at

view_count
like_count
comment_count

subscriber_count
video_age_seconds

api_source
request_id
created_at
```

Enforce uniqueness appropriate to the observation frequency, e.g.:

```text
UNIQUE(video_id, observed_at)
```

or the normalized observation bucket used by the scheduler.

Every successful observation creates a new record.

Never overwrite an old observation.

---

## `video_metrics`

```text
id
video_id
observation_id

age_days

views_per_day
view_velocity
view_growth
view_acceleration

views_per_subscriber
normalized_velocity

reach_ratio
interaction_density

created_at
```

These are DERIVED metrics.

Do not mix them into raw observations.

---

## `concept_daily_signals`

```text
id
concept_id
signal_date

population_size
observation_coverage

median_view_velocity
median_view_growth
median_view_acceleration

median_normalized_velocity
median_reach_ratio
median_interaction_density

p25_velocity
p75_velocity
velocity_std

big_creator_signal
medium_creator_signal
small_creator_signal

created_at
```

This is the concept-level longitudinal dataset that will eventually become model input.

---

## `api_request_logs`

```text
id
requested_at
api_name
endpoint
operation
http_status
quota_cost
duration_ms
attempt
success
error_code
error_message
request_metadata JSONB
```

Every external YouTube API operation must be observable.

This table is important for quota analysis and operational debugging.

---

# 7. Database integrity requirements

Implement:

* primary keys
* foreign keys
* appropriate indexes
* unique constraints
* check constraints where useful
* timestamps with timezone
* cascading behavior deliberately
* indexes on frequently queried temporal fields

At minimum, index:

```text
video_observations(video_id, observed_at)
video_observations(observed_at)
videos(channel_id)
video_candidates(search_run_id)
population_members(population_run_id)
concept_daily_signals(concept_id, signal_date)
api_request_logs(requested_at)
```

Do not create indexes indiscriminately.

---

# 8. Phase 0 — Configuration and data foundation

Implement:

1. Environment configuration.
2. Typed application configuration.
3. PostgreSQL connection.
4. SQLAlchemy models.
5. Alembic migrations. (I have no data in any DB i am creating from stracth and idk what is alembic migration)
6. Database initialization.
7. Configuration validation.
8. Logging.
9. Health checks.
10. Repository/service boundaries.

The application should be able to run:

```text
config validation
        ↓
database connection
        ↓
migration validation
        ↓
health check
```

and fail with useful errors if configuration/database requirements are invalid.

---

# 9. Phase 1 — Concept and discovery system
I am also providing gemini api key so u can use it for any requirements there
Implement concept-driven discovery.

A concept should define:

```yaml
name: AI Agents

search_queries:
  - "AI agents"
  - "agentic AI"
  - "AI automation"
```

The discovery system must:

1. Read active concepts.
2. Determine the discovery window.
3. Execute YouTube Search API queries.
4. Retrieve video candidates.
5. Record a `search_run`.
6. Register videos/channels.
7. Store every candidate.
8. Associate each candidate with its search run.
9. Preserve query provenance.

The discovery window should be explicit:

```text
publishedAfter
publishedBefore
```

Do not silently use "whatever YouTube returns today."

---

# 10. Discovery must be idempotent

Running the same discovery job twice must NOT create duplicate canonical videos.

For example:

```text
video_id = abc123
```

must remain one row in `videos`.

However, the discovery operation itself should still be represented by its own `search_run`.

The candidate relationship must preserve the fact that a video appeared in multiple searches/runs if that occurs.

---

# 11. Search API quota awareness

Treat `search.list` as the expensive/bottleneck discovery operation.

Do not:

* call search unnecessarily
* search repeatedly for the same window
* retrieve additional pages without an explicit reason
* perform search once per video
* use search to monitor existing videos

Existing videos must be monitored through batched video-statistics retrieval.

The current YouTube API documentation gives `search.list` a separate default quota allocation and allows up to 50 results per request, while `videos.list` and `channels.list` have much lower per-call costs. Design accordingly.

---

# 12. Candidate pipeline

Implement:

```text
Search
  ↓
Raw candidates
  ↓
Language filtering
  ↓
Metadata validation
  ↓
Semantic relevance
  ↓
Creator-size classification
  ↓
Population selection
```

Do not discard rejected candidates.

Every candidate must have an explicit outcome.

Valid statuses may include:

```text
pending
selected
rejected
invalid
```

Every rejection should have a reason where possible.

Examples:

```text
non_english
missing_metadata
semantic_below_threshold
duplicate
invalid_channel
insufficient_information
```

---

# 13. Semantic filtering

Use the configured local embedding model.

Concept:

```text
concept embedding
```

Video:

```text
title + description
```

Compute:

```text
cosine similarity
```

Store:

```text
semantic_score
```

Do not make semantic filtering an opaque boolean.

The numerical score must be persisted.

The threshold must be configurable.

The implementation must allow later experiments with different thresholds without rewriting the pipeline.

---

# 14. Creator-size stratification

Classify creators relative to the candidate population rather than using arbitrary global subscriber thresholds.

Support:

```text
big
medium
small
```

Use the previously established idea of percentile-based relative stratification.

However, this must be a SOFT selection objective.

Do not force:

```text
2 big
5 medium
3 small
```

if the candidate population does not support it.

The selector should prioritize relevance while attempting to maintain reasonable creator-size diversity.

Store the resulting bucket on the candidate and population membership.

---

# 15. Population selector

Implement a deterministic population selector.

Input:

```text
candidate set
semantic scores
creator buckets
target population size
```

Output:

```text
population_run
population_members
```

Requirements:

1. Reproducible.
2. Deterministic when given the same input.
3. Does not silently drop candidates.
4. Does not fail merely because the exact desired creator distribution is unavailable.
5. Produces the largest valid population possible subject to configured constraints.
6. Records why candidates were rejected.
7. Stores selection rank/score.

If target size is 10 but only 7 valid candidates exist:

```text
actual_size = 7
```

Do NOT fabricate three candidates.

---

# 16. Phase 2 — Observation engine

The observation system must operate independently from discovery.

This is critical.

Discovery answers:

> What new videos should we monitor?

Observation answers:

> What has happened to videos we are already monitoring?

Implement:

```text
population_members
        ↓
active videos
        ↓
batch IDs
        ↓
videos.list
        ↓
statistics
        ↓
video_observations
```

Batch requests.

Do not call YouTube once per video.

---

# 17. Observation behavior

For every monitored video:

Retrieve and store at least:

```text
viewCount
likeCount
commentCount
```

and the relevant channel subscriber count.

Also store:

```text
observed_at
video_age
API source
request ID
```

If a video disappears or the API returns an error:

* do not invent zero statistics
* do not overwrite the previous observation
* record the failure
* continue processing other videos
* preserve enough information to retry later

---

# 18. Immutable observation invariant

This invariant MUST be tested.

Given:

```text
video_id = V1
Aug 13 → 1000
Aug 14 → 3000
```

a later observation of:

```text
Aug 15 → 7000
```

must result in:

```text
3 observation rows
```

not:

```text
1 row containing 7000
```

Historical rows must remain unchanged.

---

# 19. Missing-data invariant

If YouTube does not return a value:

DO NOT convert:

```text
missing
```

into:

```text
0
```

unless that transformation is semantically justified and explicitly documented.

Missingness must remain distinguishable from zero.

---

# 20. Observation idempotency

If the same observation job is accidentally executed twice for the same observation timestamp:

```text
video_id + observation bucket
```

must not create duplicate observations.

The operation must be safely retryable.

Use database constraints plus application logic.

---

# 21. API retry behavior

Implement bounded retries for transient failures.

Retry:

```text
429
5xx
network timeout
temporary connection errors
```

Do not blindly retry permanent errors.

Use:

```text
exponential backoff
maximum retry count
jitter where appropriate
```

Every attempt must be observable through API request logging.

Never let one failed video terminate the entire observation batch.

---

# 22. Phase 3 — Video-level feature engineering

From immutable observations, derive:

```text
video_age
views_per_day
view_velocity
view_growth
view_acceleration
views_per_subscriber
normalized_velocity
reach_ratio
interaction_density
```

The exact formulas must be implemented in one centralized metric module.

Do not duplicate formulas across services.

Document every formula.

For example:

```text
view_velocity(t)
    = views(t) - views(t-1)
```

or the chosen normalized equivalent.

Do not silently choose mathematically different definitions in different parts of the system.

---

# 23. Handle insufficient history correctly

A metric requiring two observations cannot be calculated from one observation.

For example:

```text
velocity
```

cannot exist for a first observation unless you explicitly define a baseline.

Do NOT manufacture:

```text
velocity = 0
```

without a documented reason.

Use:

```text
NULL
```

or an explicit insufficient-history status.

The system must distinguish:

```text
real zero
```

from:

```text
not enough data
```

---

# 24. Phase 4 — Concept-level aggregation

Aggregate video-level trajectories into a daily concept signal.

The aggregation must use the monitored population.

For each concept/date calculate:

```text
population_size
observation_coverage

median_view_velocity
median_view_growth
median_view_acceleration

median_normalized_velocity
median_reach_ratio
median_interaction_density

p25_velocity
p75_velocity
velocity_std

big_creator_signal
medium_creator_signal
small_creator_signal
```

Use robust statistics such as medians where appropriate.

Do not let one viral video completely dominate the concept signal.

---

# 25. Observation coverage

Calculate and store coverage.

Example:

```text
population = 10
expected observations = 10
received observations = 8

coverage = 0.8
```

Do not treat this as a fully observed day.

The signal should expose coverage so downstream modeling can account for missingness.

---

# 26. Concept signal idempotency

For a given:

```text
concept_id
signal_date
```

there should be one canonical signal for the current pipeline version.

Repeated execution must not produce duplicate concept signals.

If recomputation is necessary, use an explicit versioning strategy rather than silently duplicating records.

---

# 27. Provenance requirement

The system must make it possible to trace:

```text
Concept
   ↓
Search Run
   ↓
Query
   ↓
Candidate
   ↓
Semantic Score
   ↓
Population Run
   ↓
Population Member
   ↓
Video
   ↓
Observation
   ↓
Metric
   ↓
Concept Signal
```

This is a major requirement.

Do not create an opaque aggregation process where the final signal cannot be traced back to its source videos.

---

# 28. YouTube API separation

Maintain a clean distinction between:

### Public trend engine

```text
YouTube Data API
    ↓
Search
Videos
Channels
```

and future:

### Creator-owned analytics

```text
YouTube Analytics API
```

Do not build the current public trend system around private creator analytics.

OAuth support may exist as an extension point, but Phase 0–4 must work using public Data API data.

---

# 29. Scheduler architecture

Use APScheduler or the existing scheduler abstraction.

Keep jobs separate:

```text
discovery_job
observation_job
metric_job
signal_job
```

Each should be independently executable.

The system should support:

```text
run discovery now
run observation now
run metrics now
run signal generation now
```

without requiring the scheduler.

This is essential for testing and backfills.

---

# 30. Failure isolation

A failure in:

```text
one search query
```

must not necessarily terminate:

```text
all concepts
```

A failure in:

```text
one video
```

must not terminate:

```text
all video observations
```

A failure in:

```text
one concept
```

must not terminate:

```text
all concepts
```

Record failures explicitly.

---

# 31. Operational logging

Use structured logging.

Every major operation should include identifiers such as:

```text
concept_id
search_run_id
population_run_id
video_id
observation_id
request_id
```

Do not rely only on human-readable log strings.

---

# 32. Testing philosophy

Do NOT merely write tests such as:

```python
assert service is not None
```

or:

```python
assert table_exists
```

The tests must verify behavior.

Build deterministic mock YouTube responses.

The mock provider should simulate:

```text
normal successful discovery
duplicate discovery
multiple candidates
insufficient candidates
semantic rejection
creator stratification
successful observation
missing statistics
404
429
500
timeout
partial batch failure
duplicate observation run
```

---

# 33. Required end-to-end behavioral test

Create a deterministic scenario:

Concept:

```text
AI Agents
```

Discovery returns 12 videos.

After filtering:

```text
8 valid candidates
```

Population target:

```text
5
```

Selector should produce:

```text
5 population members
```

Run observation for Day 0:

```text
V1 = 100
V2 = 200
V3 = 300
V4 = 400
V5 = 500
```

Run observation for Day 1:

```text
V1 = 250
V2 = 350
V3 = 900
V4 = 450
V5 = 1000
```

Run observation for Day 2:

```text
V1 = 500
V2 = 700
V3 = 1800
V4 = 700
V5 = 2500
```

The database must contain:

```text
5 videos
15 observations
```

not:

```text
5 videos
5 observations
```

and not:

```text
15 videos
```

---

# 34. Verify derived metrics

Using the deterministic observations, verify that:

* video age increases correctly
* view velocity changes correctly
* growth is based on observations rather than current absolute views alone
* acceleration requires sufficient history
* normalized metrics use the correct subscriber value
* missing values remain missing
* no historical observation is modified

Do not merely test that the metric function returns a number.

Test the actual expected values.

---

# 35. Verify concept aggregation

For the deterministic dataset verify:

```text
population_size = 5
```

and verify the actual:

```text
median
p25
p75
standard deviation
creator bucket signals
coverage
```

against expected values.

The test should fail if the aggregation formula changes unexpectedly.

---

# 36. Verify idempotency

Execute:

```text
discovery()
discovery()
```

and verify:

```text
canonical videos are not duplicated
```

Then execute:

```text
observation()
observation()
```

for the same observation bucket and verify:

```text
observation rows are not duplicated
```

Then execute:

```text
signal_generation()
signal_generation()
```

and verify:

```text
concept signal is not duplicated
```

---

# 37. Verify immutability

Insert:

```text
V1 / Day 0 / 100 views
```

Then insert:

```text
V1 / Day 1 / 200 views
```

Verify the Day 0 row remains:

```text
100
```

forever.

This is a mandatory test.

---

# 38. Verify partial failures

Mock a batch:

```text
V1 success
V2 success
V3 429
V4 success
V5 timeout
```

The system must:

* preserve V1
* preserve V2
* preserve V4
* record failures for V3/V5
* retry transient failures according to policy
* not crash the entire job
* expose final coverage accurately

---

# 39. Verify quota-conscious behavior

Test that:

```text
40 candidate videos
```

do NOT result in:

```text
40 videos.list calls
```

The implementation should batch IDs.

Similarly:

```text
10 monitored videos
```

should not result in 10 separate API calls when they can be retrieved in a batch.

Search must not be used for routine monitoring.

---

# 40. Verify provenance

Given a final concept signal, the system must be able to identify:

```text
which concept produced it
which population produced it
which videos contributed
which observations contributed
```

Build repository/query methods or a diagnostic command that can demonstrate this.

Example:

```text
show_signal_provenance(
    concept="AI Agents",
    date="2026-08-19"
)
```

should return enough information to trace the signal back to contributing videos and observations.

---

# 41. Add pipeline diagnostics

Implement a diagnostic command such as:

```bash
python -m app diagnostics
```

or adapt the existing CLI.

It should report:

```text
Database: OK
YouTube configuration: OK
Scheduler: OK
Active concepts: N
Videos: N
Candidates: N
Population members: N
Observations: N
Signals: N
API failures: N
Latest observation: timestamp
Latest signal: timestamp
```

Do not make this purely cosmetic; query the actual database.

---

# 42. Add pipeline execution commands

Provide commands equivalent to:

```bash
pipeline validate
pipeline discover
pipeline observe
pipeline metrics
pipeline signals
pipeline run
```

If the existing project has a CLI, extend it instead of creating a second CLI.

`pipeline run` should execute the phases in dependency order:

```text
discover
  ↓
observe
  ↓
metrics
  ↓
signals
```

while still allowing individual stages to run independently.

---

# 43. Backfill support

Design the services so that a specific date/window can be executed explicitly.

For example:

```text
discover concept X for 2026-08-13
observe population Y for 2026-08-14
recompute metrics for video Z
recompute signal for concept X/date Y
```

Do not make the system dependent on wall-clock scheduler execution.

---

# 44. Do not implement forecasting yet

Do NOT hard-code:

```text
PreWHether
PreWHen
trend labels
trend probability
time-to-trend
```

into the core ingestion pipeline.

Instead create clean interfaces/data contracts so the next phase can consume:

```text
concept_daily_signals
```

and generate its own features/labels.

The current system's responsibility is to produce reliable longitudinal data.

---

# 45. Do not create fake historical data

Tests may use synthetic/mock data.

The production system must never claim that a current YouTube statistic represents a historical observation.

If a video was discovered today:

```text
first_observed_at = today
```

unless an actual previous observation exists in the database.

Never infer missing history from current view counts.

---

# 46. Data quality rules

Implement checks for:

```text
video_id not null
channel_id not null
published_at valid
observed_at valid
view_count >= 0
like_count >= 0
comment_count >= 0
subscriber_count >= 0 where present
semantic_score between 0 and 1
coverage between 0 and 1
```

Also detect suspicious temporal anomalies such as:

```text
observed_at < previous observed_at
```

Do not automatically "fix" them without logging.

---

# 47. Performance requirements

The implementation should:

* batch YouTube API requests
* use database transactions appropriately
* avoid N+1 database queries
* avoid N+1 YouTube requests
* use bulk inserts where appropriate
* use connection pooling
* avoid loading the entire observation history into memory
* use pagination where needed

Do not optimize prematurely with complex distributed infrastructure.

---

# 48. Research reproducibility

Store enough metadata to reproduce:

```text
which query was used
which discovery window was used
which candidates were returned
which semantic score was assigned
which selector strategy was used
which candidates were selected
which observations existed
which aggregation generated the signal
```

The objective is that a researcher can inspect why a particular concept signal exists.

---

# 49. Documentation requirements

Update:

```text
README
architecture documentation
database schema documentation
configuration documentation
pipeline documentation
testing documentation
```

Include:

```text
system architecture
database ER-style description
pipeline lifecycle
configuration
scheduler jobs
API quota strategy
data lineage
metric definitions
failure handling
testing strategy
```

Do not create documentation that describes functionality which does not actually exist.

---

# 50. Final acceptance criteria

Do not consider the task complete merely because:

```text
the application starts
tables exist
API client exists
scheduler exists
tests pass superficially
```

The task is complete only when the system demonstrates:

### Discovery

```text
concept
→ search
→ candidates
→ candidate persistence
```

### Selection

```text
candidates
→ filtering
→ semantic scores
→ creator buckets
→ deterministic population
```

### Observation

```text
population
→ batched API call
→ immutable snapshots
```

### Metrics

```text
snapshots
→ temporal metrics
```

### Aggregation

```text
video metrics
→ concept daily signal
```

### Reliability

```text
retry
partial failure
idempotency
missing data
quota awareness
```

### Provenance

```text
concept
→ search run
→ candidate
→ population
→ video
→ observation
→ metric
→ signal
```

### Behavioral validation

The end-to-end deterministic test must prove that these operations actually produce the expected database state and numerical outputs.

---

# 51. Final execution instruction

After implementation:

1. Run migrations.
2. Validate configuration.
3. Run unit tests.
4. Run integration tests.
5. Run deterministic end-to-end pipeline.
6. Inspect actual database rows.
7. Run idempotency tests.
8. Run failure-injection tests.
9. Run API batching/quota behavior tests.
10. Run provenance checks.
11. Fix failures rather than merely reporting them.
12. Re-run the complete suite after fixes.
13. Produce a concise implementation report containing:

* what was reused
* what was created
* database schema
* pipeline flow
* tests executed
* behavioral results
* known limitations
* commands used to reproduce the run

Do not stop at "implementation complete."

The final state must be **operationally demonstrated**.

The primary success criterion is:

> Given a concept and a deterministic/mock YouTube API, the system must correctly discover candidates, select a population, repeatedly observe videos, preserve immutable observations, derive temporal metrics, aggregate them into concept-level daily signals, survive partial failures, remain idempotent, and preserve full provenance.

Do not implement forecasting yet.

Build the data foundation correctly enough that a future forecasting layer can trust the dataset.
