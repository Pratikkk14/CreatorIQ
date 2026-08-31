import time
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.models import ApiRequestLog

class YouTubeService:
    @staticmethod
    def build_query(include_terms: List[str], exclude_terms: List[str]) -> str:
        inc_part = " | ".join(include_terms)
        if len(include_terms) > 1:
            inc_part = f"({inc_part})"
        
        exc_part = " ".join(f"-{t}" for t in exclude_terms)
        
        query = inc_part
        if exc_part:
            query = f"{query} {exc_part}"
        return query.strip()

    def __init__(self, use_mock: bool = False, mock_provider: Optional[Any] = None):
        self.use_mock = use_mock
        self.mock_provider = mock_provider
        self.client = None
        
        if not use_mock and settings.youtube_api_key:
            try:
                self.client = build("youtube", "v3", developerKey=settings.youtube_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize real YouTube client: {e}. Falling back to mock.")
                self.use_mock = True

    def _log_api_call(self, endpoint: str, operation: str, http_status: Optional[int], 
                      quota_cost: int, duration_ms: int, attempt: int, 
                      success: bool, error_code: Optional[str] = None, 
                      error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        db = SessionLocal()
        try:
            log_entry = ApiRequestLog(
                api_name="youtube",
                endpoint=endpoint,
                operation=operation,
                http_status=http_status,
                quota_cost=quota_cost,
                duration_ms=duration_ms,
                attempt=attempt,
                success=success,
                error_code=error_code,
                error_message=error_message,
                request_metadata=metadata or {}
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to save API request log to DB: {e}")
        finally:
            db.close()

    def search_videos(self, query: str, limit: int = 50, 
                      published_after: Optional[datetime] = None, 
                      published_before: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Executes search.list. Quota cost: 100 units.
        Returns a list of simplified video dictionaries.
        """
        if self.use_mock:
            if self.mock_provider and hasattr(self.mock_provider, "search_videos"):
                return self.mock_provider.search_videos(query, limit, published_after, published_before)
            return self._get_mock_search_videos(query, limit)

        if not self.client:
            raise ValueError("YouTube API Client not initialized and mock mode is disabled.")

        # Real API Search
        attempt = 0
        max_retries = settings.youtube_api_max_retries
        backoff = settings.youtube_api_retry_backoff
        
        # Prepare parameters
        published_after_str = published_after.isoformat() if published_after else None
        published_before_str = published_before.isoformat() if published_before else None
        
        params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": min(limit, 50),
            "relevanceLanguage": "en",
            "videoDimension": "2d"
        }
        if published_after_str:
            params["publishedAfter"] = published_after_str
        if published_before_str:
            params["publishedBefore"] = published_before_str

        while attempt < max_retries:
            attempt += 1
            start_time = time.time()
            try:
                request = self.client.search().list(**params)
                response = request.execute()
                duration = int((time.time() - start_time) * 1000)
                
                # Parse videos
                items = response.get("items", [])
                videos = []
                for item in items:
                    v_id = item.get("id", {}).get("videoId")
                    snippet = item.get("snippet", {})
                    if v_id:
                        videos.append({
                            "video_id": v_id,
                            "title": snippet.get("title"),
                            "description": snippet.get("description"),
                            "channel_id": snippet.get("channelId"),
                            "channel_title": snippet.get("channelTitle"),
                            "published_at": snippet.get("publishedAt"),
                            "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url")
                        })
                
                self._log_api_call(
                    endpoint="search.list",
                    operation="search_videos",
                    http_status=200,
                    quota_cost=100,
                    duration_ms=duration,
                    attempt=attempt,
                    success=True,
                    metadata={"query": query, "limit": limit, "returned_count": len(videos)}
                )
                return videos
                
            except HttpError as err:
                duration = int((time.time() - start_time) * 1000)
                status_code = err.resp.status
                error_msg = str(err)
                
                self._log_api_call(
                    endpoint="search.list",
                    operation="search_videos",
                    http_status=status_code,
                    quota_cost=0,
                    duration_ms=duration,
                    attempt=attempt,
                    success=False,
                    error_code=f"HTTP_{status_code}",
                    error_message=error_msg,
                    metadata={"query": query}
                )
                
                if status_code in [429, 500, 503]:
                    time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                else:
                    raise err
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                self._log_api_call(
                    endpoint="search.list",
                    operation="search_videos",
                    http_status=500,
                    quota_cost=0,
                    duration_ms=duration,
                    attempt=attempt,
                    success=False,
                    error_code="LOCAL_ERROR",
                    error_message=str(e),
                    metadata={"query": query}
                )
                time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                
        raise Exception(f"Failed search_videos query '{query}' after {max_retries} attempts.")

    def get_videos_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves statistics and content details for videos.
        Uses batching: max 50 IDs per call. Quota cost: 1 unit per batch call.
        """
        if not video_ids:
            return []

        if self.use_mock:
            if self.mock_provider and hasattr(self.mock_provider, "get_videos_details"):
                return self.mock_provider.get_videos_details(video_ids)
            return self._get_mock_videos_details(video_ids)

        if not self.client:
            raise ValueError("YouTube API Client not initialized and mock mode is disabled.")

        results = []
        # Batch into chunks of 50
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i+50]
            attempt = 0
            max_retries = settings.youtube_api_max_retries
            backoff = settings.youtube_api_retry_backoff
            
            while attempt < max_retries:
                attempt += 1
                start_time = time.time()
                try:
                    request = self.client.videos().list(
                        part="snippet,statistics,contentDetails",
                        id=",".join(chunk)
                    )
                    response = request.execute()
                    duration = int((time.time() - start_time) * 1000)
                    
                    items = response.get("items", [])
                    chunk_details = []
                    for item in items:
                        snippet = item.get("snippet", {})
                        stats = item.get("statistics", {})
                        details = item.get("contentDetails", {})
                        
                        # Parse ISO 8601 duration to seconds
                        dur_str = details.get("duration", "PT0S")
                        duration_sec = self._parse_duration(dur_str)
                        
                        # Handle fields that may not be present (e.g. hidden like count)
                        chunk_details.append({
                            "video_id": item.get("id"),
                            "title": snippet.get("title"),
                            "description": snippet.get("description"),
                            "channel_id": snippet.get("channelId"),
                            "published_at": snippet.get("publishedAt"),
                            "duration_seconds": duration_sec,
                            "category_id": snippet.get("categoryId"),
                            "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                            "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                            "view_count": int(stats.get("viewCount")) if stats.get("viewCount") else None,
                            "like_count": int(stats.get("likeCount")) if stats.get("likeCount") else None,
                            "comment_count": int(stats.get("commentCount")) if stats.get("commentCount") else None
                        })
                    
                    results.extend(chunk_details)
                    self._log_api_call(
                        endpoint="videos.list",
                        operation="get_videos_details",
                        http_status=200,
                        quota_cost=1,
                        duration_ms=duration,
                        attempt=attempt,
                        success=True,
                        metadata={"requested_count": len(chunk), "returned_count": len(chunk_details)}
                    )
                    break  # Success, exit retry loop for this chunk
                    
                except HttpError as err:
                    duration = int((time.time() - start_time) * 1000)
                    status_code = err.resp.status
                    self._log_api_call(
                        endpoint="videos.list",
                        operation="get_videos_details",
                        http_status=status_code,
                        quota_cost=0,
                        duration_ms=duration,
                        attempt=attempt,
                        success=False,
                        error_code=f"HTTP_{status_code}",
                        error_message=str(err),
                        metadata={"requested_count": len(chunk)}
                    )
                    if status_code in [429, 500, 503]:
                        time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                    else:
                        raise err
                except Exception as e:
                    duration = int((time.time() - start_time) * 1000)
                    self._log_api_call(
                        endpoint="videos.list",
                        operation="get_videos_details",
                        http_status=500,
                        quota_cost=0,
                        duration_ms=duration,
                        attempt=attempt,
                        success=False,
                        error_code="LOCAL_ERROR",
                        error_message=str(e),
                        metadata={"requested_count": len(chunk)}
                    )
                    time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                    
            if attempt == max_retries:
                # In case of persistent chunk failure, record failure but don't crash the entire list
                logger.error(f"Chunk starting at index {i} failed all {max_retries} attempts.")
                
        return results

    def get_channels_details(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves channel metadata.
        Uses batching: max 50 IDs per call. Quota cost: 1 unit per batch call.
        """
        if not channel_ids:
            return []

        if self.use_mock:
            if self.mock_provider and hasattr(self.mock_provider, "get_channels_details"):
                return self.mock_provider.get_channels_details(channel_ids)
            return self._get_mock_channels_details(channel_ids)

        if not self.client:
            raise ValueError("YouTube API Client not initialized and mock mode is disabled.")

        results = []
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i:i+50]
            attempt = 0
            max_retries = settings.youtube_api_max_retries
            backoff = settings.youtube_api_retry_backoff
            
            while attempt < max_retries:
                attempt += 1
                start_time = time.time()
                try:
                    request = self.client.channels().list(
                        part="snippet,statistics",
                        id=",".join(chunk)
                    )
                    response = request.execute()
                    duration = int((time.time() - start_time) * 1000)
                    
                    items = response.get("items", [])
                    chunk_details = []
                    for item in items:
                        snippet = item.get("snippet", {})
                        stats = item.get("statistics", {})
                        chunk_details.append({
                            "channel_id": item.get("id"),
                            "title": snippet.get("title"),
                            "subscriber_count": int(stats.get("subscriberCount")) if stats.get("subscriberCount") else 0,
                            "video_count": int(stats.get("videoCount")) if stats.get("videoCount") else 0,
                            "country": snippet.get("country"),
                            "published_at": snippet.get("publishedAt")
                        })
                    
                    results.extend(chunk_details)
                    self._log_api_call(
                        endpoint="channels.list",
                        operation="get_channels_details",
                        http_status=200,
                        quota_cost=1,
                        duration_ms=duration,
                        attempt=attempt,
                        success=True,
                        metadata={"requested_count": len(chunk), "returned_count": len(chunk_details)}
                    )
                    break
                except HttpError as err:
                    duration = int((time.time() - start_time) * 1000)
                    status_code = err.resp.status
                    self._log_api_call(
                        endpoint="channels.list",
                        operation="get_channels_details",
                        http_status=status_code,
                        quota_cost=0,
                        duration_ms=duration,
                        attempt=attempt,
                        success=False,
                        error_code=f"HTTP_{status_code}",
                        error_message=str(err),
                        metadata={"requested_count": len(chunk)}
                    )
                    if status_code in [429, 500, 503]:
                        time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                    else:
                        raise err
                except Exception as e:
                    duration = int((time.time() - start_time) * 1000)
                    self._log_api_call(
                        endpoint="channels.list",
                        operation="get_channels_details",
                        http_status=500,
                        quota_cost=0,
                        duration_ms=duration,
                        attempt=attempt,
                        success=False,
                        error_code="LOCAL_ERROR",
                        error_message=str(e),
                        metadata={"requested_count": len(chunk)}
                    )
                    time.sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5))
                    
        return results

    def _parse_duration(self, duration_str: str) -> int:
        """Parses ISO 8601 duration format e.g. PT1H30M15S -> seconds"""
        import re
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration_str)
        if not match:
            return 0
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        return hours * 3600 + minutes * 60 + seconds

    # --- MOCK PROVIDERS FOR OFFLINE DEVELOPMENT / TESTS ---

    def _get_mock_search_videos(self, query: str, limit: int) -> List[Dict[str, Any]]:
        # Generates deterministic mock search results
        logger.info(f"Using default mock search for query '{query}'")
        videos = []
        now = datetime.now(timezone.utc)
        
        # We will mock 12 candidate videos as described in Section 33 E2E test requirement
        # To make it deterministic, we'll label them mock1 to mock12
        for i in range(1, 13):
            video_id = f"mock_vid_{i}"
            # Mix titles to match AI agents concept
            title = f"Building AI agents {i} - Everything you need to know" if i <= 8 else f"Random non-related video {i}"
            desc = "This is a video description detailing agentic AI systems and LLM workflows."
            videos.append({
                "video_id": video_id,
                "title": title,
                "description": desc,
                "channel_id": f"mock_channel_{i}",
                "channel_title": f"Creator Studio {i}",
                "published_at": (now - timedelta(days=2)).isoformat(),
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/default.jpg"
            })
        self._log_api_call("search.list", "search_videos", 200, 100, 50, 1, True, metadata={"query": query, "limit": limit, "returned_count": len(videos)})
        return videos[:limit]

    def _get_mock_videos_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        logger.info(f"Using default mock video details for IDs: {video_ids}")
        now = datetime.now(timezone.utc)
        results = []
        for vid in video_ids:
            results.append({
                "video_id": vid,
                "title": f"Mock Video Title for {vid}",
                "description": "Mock Description detailing agentic AI systems.",
                "channel_id": f"channel_{vid}",
                "published_at": (now - timedelta(days=2)).isoformat(),
                "duration_seconds": 360,
                "category_id": "27",
                "language": "en",
                "thumbnail_url": f"https://img.youtube.com/vi/{vid}/default.jpg",
                "view_count": 1000,
                "like_count": 50,
                "comment_count": 10
            })
        self._log_api_call("videos.list", "get_videos_details", 200, 1, 20, 1, True, metadata={"requested_count": len(video_ids)})
        return results

    def _get_mock_channels_details(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        logger.info(f"Using default mock channel details for IDs: {channel_ids}")
        now = datetime.now(timezone.utc)
        results = []
        for index, cid in enumerate(channel_ids):
            # Create sub counts that spread across buckets (big, medium, small)
            # e.g. 500, 50000, 1000000
            sub_count = 500 if index % 3 == 0 else (50000 if index % 3 == 1 else 1000000)
            results.append({
                "channel_id": cid,
                "title": f"Channel Title for {cid}",
                "subscriber_count": sub_count,
                "video_count": 42,
                "country": "US",
                "published_at": (now - timedelta(days=100)).isoformat()
            })
        self._log_api_call("channels.list", "get_channels_details", 200, 1, 20, 1, True, metadata={"requested_count": len(channel_ids)})
        return results
