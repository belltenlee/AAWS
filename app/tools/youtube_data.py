"""Small async wrappers for the public YouTube Data API v3 endpoints."""

import json
import os
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, Field
from langchain_core.tools import tool

_API_BASE = "https://www.googleapis.com/youtube/v3"


def _configured_channel_id() -> Optional[str]:
    return os.getenv("YOUTUBE_GOMM_CHANNEL_ID") or os.getenv("YOUTUBE_CHANNEL_ID")


async def _youtube_get(resource: str, params: dict) -> dict:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "YOUTUBE_API_KEY is not configured in the server environment.",
        }

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"X-Goog-Api-Key": api_key},
        ) as client:
            response = await client.get(f"{_API_BASE}/{resource}", params=params)
        if response.is_error:
            try:
                error_data = response.json().get("error", {})
                message = error_data.get("message", "YouTube Data API request failed.")
            except (ValueError, AttributeError):
                message = "YouTube Data API request failed."
            return {
                "status": "error",
                "http_status": response.status_code,
                "message": message.replace(api_key, "[redacted]"),
            }
        return response.json()
    except httpx.TimeoutException:
        return {"status": "error", "message": "YouTube Data API request timed out."}
    except httpx.RequestError as exc:
        return {
            "status": "error",
            "message": f"YouTube Data API connection failed ({type(exc).__name__}).",
        }
    except ValueError:
        return {"status": "error", "message": "YouTube Data API returned invalid JSON."}


class YouTubeChannelSearchInput(BaseModel):
    query: str = Field(default="귀곰", description="Channel name or identifying search phrase.")
    max_results: int = Field(default=10, ge=1, le=50)


@tool(args_schema=YouTubeChannelSearchInput)
async def youtube_search_channels(query: str = "귀곰", max_results: int = 10) -> str:
    """Searches YouTube channels and returns channel IDs, handles, and upload playlist IDs."""
    result = await _youtube_get(
        "search",
        {"part": "snippet", "type": "channel", "q": query, "maxResults": max_results},
    )
    if result.get("status") == "error":
        return json.dumps(result, ensure_ascii=False)

    channel_ids = [
        item.get("id", {}).get("channelId")
        for item in result.get("items", [])
        if item.get("id", {}).get("channelId")
    ]
    if not channel_ids:
        return json.dumps({"status": "success", "query": query, "channels": []}, ensure_ascii=False)

    details = await _youtube_get(
        "channels",
        {"part": "snippet,statistics,contentDetails", "id": ",".join(channel_ids)},
    )
    if details.get("status") == "error":
        return json.dumps(details, ensure_ascii=False)

    channels = []
    for item in details.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        channels.append({
            "channel_id": item.get("id"),
            "title": snippet.get("title"),
            "custom_url": snippet.get("customUrl"),
            "description": snippet.get("description"),
            "published_at": snippet.get("publishedAt"),
            "video_count": stats.get("videoCount"),
            "uploads_playlist_id": uploads,
        })

    return json.dumps({"status": "success", "query": query, "channels": channels}, ensure_ascii=False)


class YouTubeVideoSearchInput(BaseModel):
    query: str = Field(description="Product category or phrase to search in video titles and descriptions.")
    channel_id: Optional[str] = Field(
        default=None,
        description="Verified channel ID. Uses YOUTUBE_GOMM_CHANNEL_ID (or legacy YOUTUBE_CHANNEL_ID) when omitted.",
    )
    max_results: int = Field(default=25, ge=1, le=50)
    page_token: Optional[str] = None
    order: Literal["date", "relevance"] = "date"
    published_after: Optional[str] = Field(
        default=None,
        description="Optional RFC 3339 timestamp, e.g. 2025-01-01T00:00:00Z.",
    )


@tool(args_schema=YouTubeVideoSearchInput)
async def youtube_search_videos(
    query: str,
    channel_id: Optional[str] = None,
    max_results: int = 25,
    page_token: Optional[str] = None,
    order: Literal["date", "relevance"] = "date",
    published_after: Optional[str] = None,
) -> str:
    """Searches videos, optionally restricted to a verified channel ID."""
    verified_channel_id = channel_id or _configured_channel_id()
    if not verified_channel_id:
        return json.dumps({
            "status": "error",
            "message": "Provide a verified channel_id or configure YOUTUBE_GOMM_CHANNEL_ID.",
        }, ensure_ascii=False)

    params = {
        "part": "snippet",
        "type": "video",
        "channelId": verified_channel_id,
        "q": query,
        "maxResults": max_results,
        "order": order,
    }
    if page_token:
        params["pageToken"] = page_token
    if published_after:
        params["publishedAfter"] = published_after

    result = await _youtube_get("search", params)
    if result.get("status") == "error":
        return json.dumps(result, ensure_ascii=False)

    videos = []
    for item in result.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            videos.append({
                "video_id": video_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    return json.dumps({
        "status": "success",
        "channel_id": verified_channel_id,
        "query": query,
        "videos": videos,
        "next_page_token": result.get("nextPageToken"),
        "total_results": result.get("pageInfo", {}).get("totalResults"),
    }, ensure_ascii=False)


class YouTubeChannelVideosInput(BaseModel):
    channel_id: Optional[str] = Field(
        default=None,
        description="Verified channel ID. Uses YOUTUBE_GOMM_CHANNEL_ID (or legacy YOUTUBE_CHANNEL_ID) when omitted.",
    )
    max_results: int = Field(default=50, ge=1, le=50)
    page_token: Optional[str] = None


@tool(args_schema=YouTubeChannelVideosInput)
async def youtube_list_channel_videos(
    channel_id: Optional[str] = None,
    max_results: int = 50,
    page_token: Optional[str] = None,
) -> str:
    """Lists one page of a channel's upload playlist for incremental catalog building."""
    verified_channel_id = channel_id or _configured_channel_id()
    if not verified_channel_id:
        return json.dumps({
            "status": "error",
            "message": "Provide a verified channel_id or configure YOUTUBE_GOMM_CHANNEL_ID.",
        }, ensure_ascii=False)

    channel_result = await _youtube_get(
        "channels",
        {"part": "snippet,contentDetails", "id": verified_channel_id},
    )
    if channel_result.get("status") == "error":
        return json.dumps(channel_result, ensure_ascii=False)
    channel = next(
        (item for item in channel_result.get("items", []) if item.get("id") == verified_channel_id),
        None,
    )
    if not channel:
        return json.dumps({"status": "error", "message": "Channel ID was not found."}, ensure_ascii=False)

    uploads_playlist_id = (
        channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    )
    if not uploads_playlist_id:
        return json.dumps({"status": "error", "message": "Channel uploads playlist was unavailable."}, ensure_ascii=False)

    params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": max_results,
    }
    if page_token:
        params["pageToken"] = page_token
    playlist_result = await _youtube_get("playlistItems", params)
    if playlist_result.get("status") == "error":
        return json.dumps(playlist_result, ensure_ascii=False)

    videos = []
    for item in playlist_result.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("contentDetails", {}).get("videoId")
        if video_id:
            videos.append({
                "video_id": video_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": item.get("contentDetails", {}).get("videoPublishedAt"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    return json.dumps({
        "status": "success",
        "channel": {
            "channel_id": channel.get("id"),
            "title": channel.get("snippet", {}).get("title"),
            "custom_url": channel.get("snippet", {}).get("customUrl"),
            "uploads_playlist_id": uploads_playlist_id,
        },
        "videos": videos,
        "next_page_token": playlist_result.get("nextPageToken"),
        "total_results": playlist_result.get("pageInfo", {}).get("totalResults"),
    }, ensure_ascii=False)


__all__ = [
    "youtube_search_channels",
    "youtube_search_videos",
    "youtube_list_channel_videos",
]