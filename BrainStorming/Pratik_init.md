

> 3 category of api

| Pipeline stage                         | APIs                                                                                                                      | Quota pressure                    | strategy                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ----------------------------------------------------- |
| **1. Discovery**                       | `search.list`                                                                                                             | 🔴 **High** — 100/day             | Minimize calls; create persistent video cohorts       |
| **2. Enrichment / Monitoring**         | `videos.list`, `videos:batchGetStats`, `channels.list`                                                                    | 🟢 **Low** — general 10K/day pool | Batch aggressively; monitor already-discovered videos |
| **3. Explanation / Secondary signals** | `playlistItems.list`, `commentThreads.list`, `comments.list`, `playlists.list`, `activities.list`, `videoCategories.list` | 🟢 Generally low                  | Invoke selectively rather than on every video         |

---
---


| API                        | What we can use it for                                    | Quota / API limit                                             | Data returned / practical limit                                                                        | How we should use it                                                                            |
| -------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **`search.list`**          | Discover candidate videos for a concept/topic               | **100 calls/day**; 1 quota unit/call in its own Search bucket | Max **50 results/request**; pagination requires additional calls                                       | 🔴 **Primary discovery API** — use sparingly to create daily cohorts                            |
| **`videos.list`**          | Enrich discovered videos with metadata + current statistics | **1 unit/call**, general 10,000-unit/day pool                 | `maxResults` up to **50**; can request `snippet`, `contentDetails`, `statistics`, `topicDetails`, etc. | 🔴 **Primary enrichment API** — fetch metadata/statistics after candidate selection             |
| **`videos:batchGetStats`** | Repeatedly monitor selected videos                          | **1 unit/call**, default 10,000-unit/day pool                 | Designed for batched video statistics; introduced June 2026                                            | 🔴 **Primary monitoring API** — use for daily time-series snapshots instead of individual calls |
| **`channels.list`**        | Get creator/channel statistics and metadata                 | **1 unit/call**, general 10,000-unit/day pool                 | `maxResults` up to **50**                                                                              | 🔴 **Primary normalization API** — especially `subscriberCount` for reach normalization         |
| **`playlistItems.list`**   | Track videos uploaded by known channels / upload streams    | **1 unit/call**                                               | Max **50 items/request**; pagination required for more                                                 | 🟠 **Useful secondary discovery mechanism** after we identify important creators                |
| **`playlists.list`**       | Understand playlist structure / possible content grouping   | **1 unit/call**                                               | Max **50 playlists/request**                                                                           | 🟡 **Optional** — useful for content taxonomy, not core trend signal                            |
| **`commentThreads.list`**  | Get comments + reply counts for selected videos             | **1 unit/call**, general 10,000-unit/day pool                 | Max **100 comment threads/request**                                                                    | 🟠 **Potential** — use selectively on high-growth videos for "why is it trending?"              |
| **`comments.list`**        | Retrieve individual comments/replies                        | **1 unit/call**                                               | Max **100 comments/request**                                                                           | 🟡 **Potential** — only when doing deeper comment/NLP analysis                                  |
| **`videoCategories.list`** | Map category IDs → category names                           | **1 unit/call**                                               | Small reference dataset; cache locally                                                                 | 🟡 **Supporting** — call infrequently, not part of daily pipeline                               |
| **`activities.list`**      | Observe channel activity events                             | **1 unit/call**                                               | Max **50 activities/request**                                                                          | 🟡 **Potential but low priority** — likely redundant with upload playlists                      |

```
                         DEFAULT QUOTA
                              │
             ┌────────────────┴────────────────┐
             │                                 │
      SEARCH QUOTA                       OTHER DATA API
        100/day                           10,000/day
             │                                 │
       search.list                     videos.list = 1
       = 100/call                     channels.list = 1
                                      playlistItems = 1
                                      comments = 1
                                      etc.
```
```
                         GRAD
                          │
             ┌────────────┴────────────┐
             │                         │
       MARKET MODE               CREATOR MODE
             │                         │
             ▼                         ▼
       YouTube Data API          YouTube Analytics
             │                         │
       ┌─────┼─────┐           ┌───────┼────────┐
       │     │     │           │       │        │
    Search Videos Channels    Daily  Watch   Traffic
       │     │     │           metrics time   sources
       │     │     │
       │     │     └── subscriber count
       │     │
       │     ├── metadata
       │     └── statistics
       │
       └── candidate discovery
```
```
YouTube Analytics
       ↓
Daily views
       ↓
Watch time
       ↓
Retention
       ↓
Subscribers
       ↓
Traffic sources
       ↓
Their own content performance                                
           
            Search
            ↓
            Videos
            ↓
            Channels
            ↓
            Public statistics
            ↓
            Repeated observation
            ↓
            Trend prediction
```

