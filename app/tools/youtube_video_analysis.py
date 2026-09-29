"""Gemini video analysis for public YouTube URLs."""

import json
import os
from urllib.parse import parse_qs, urlparse

from google import genai
from langchain_core.tools import tool
from pydantic import BaseModel, Field


def _is_youtube_video_url(video_url: str) -> bool:
    parsed = urlparse(video_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        return False
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        return bool(parse_qs(parsed.query).get("v")) or parsed.path.startswith(("/shorts/", "/embed/"))
    if host == "youtu.be":
        return bool(parsed.path.strip("/"))
    return False


def _analysis_prompt(category: str) -> str:
    return f"""Analyze the complete public YouTube video for the product category: {category}.

Return JSON only, with this schema:
{{
  "recommendation_groups": [
    {{
      "category_label": "the category/price tier stated in the video, or null",
      "ranking_type": "explicit_numeric | ordered_recommendations | unordered",
      "items": [
        {{
          "product_name": "exactly identifiable product/model, or null",
          "numeric_rank": null,
          "appearance_order": 1,
          "sentiment": "recommended | not_recommended | unclear",
          "timestamp": "MM:SS or null",
          "evidence_summary": "short description of what is spoken or shown",
          "explicit_quote": null,
          "confidence": "high | medium | low"
        }}
      ]
    }}
  ],
  "limitations": []
}}

Rules:
- Review the video itself; do not infer its contents from title, description, search snippets, or outside product knowledge.
- Set numeric_rank only when a numeric rank is explicitly stated. Do not convert appearance order or category headings into numeric ranks.
- Preserve category-specific recommendation groups (for example, flagship, midrange, or entry-level).
- Set appearance_order by order of recommendation within that group; this is not a rank.
- Use an exact_quote only when the exact wording is clearly audible. Otherwise leave it null and summarize the evidence.
- If a product name, recommendation direction, timestamp, or ranking is unclear, use null/unclear and explain it under limitations.
- Do not invent missing products or claim the video is a complete ranking if it only gives examples or category picks.
"""


class YouTubeVideoAnalysisInput(BaseModel):
    video_url: str = Field(description="Public YouTube watch, Shorts, embed, or youtu.be URL.")
    category: str = Field(description="Product category to focus on, e.g. 로봇청소기.")


@tool(args_schema=YouTubeVideoAnalysisInput)
async def analyze_public_youtube_video(video_url: str, category: str) -> str:
    """Uses Gemini's YouTube URL input to extract video-grounded product picks and timestamps."""
    if not _is_youtube_video_url(video_url):
        return "VIDEO_ANALYSIS_ERROR: Provide a valid HTTPS YouTube video URL."

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "VIDEO_ANALYSIS_ERROR: GOOGLE_API_KEY is not configured for Gemini video analysis."

    client = None
    try:
        client = genai.Client(api_key=api_key)
        interaction = await client.aio.interactions.create(
            model=os.getenv("YOUTUBE_VIDEO_ANALYSIS_MODEL", "gemini-3.8-flash"),
            input=[
                {"type": "text", "text": _analysis_prompt(category)},
                {"type": "video", "uri": video_url},
            ],
        )
        output = interaction.output_text
        if not output:
            return "VIDEO_ANALYSIS_ERROR: Gemini returned no video analysis text."
        payload = output.strip()
        if payload.startswith("```"):
            lines = payload.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            payload = "\n".join(lines).strip()
        try:
            analysis = json.loads(payload)
        except json.JSONDecodeError:
            return "VIDEO_ANALYSIS_ERROR: Gemini response was not valid JSON."
        if not isinstance(analysis, dict):
            return "VIDEO_ANALYSIS_ERROR: Gemini response must be a JSON object."
        returned_video_url = analysis.get("video_url")
        if returned_video_url and returned_video_url != video_url:
            return "VIDEO_ANALYSIS_ERROR: Gemini returned a different video URL; analysis rejected."
        analysis["video_url"] = video_url
        returned_category = analysis.get("category")
        if returned_category and returned_category != category:
            return "VIDEO_ANALYSIS_ERROR: Gemini response category did not match the requested category."
        analysis["category"] = category
        if not isinstance(analysis.get("recommendation_groups"), list):
            return "VIDEO_ANALYSIS_ERROR: Gemini response omitted recommendation_groups."
        return json.dumps(analysis, ensure_ascii=False)
    except Exception as exc:
        message = str(exc).replace(api_key, "[redacted]")
        return f"VIDEO_ANALYSIS_ERROR: {message}"
    finally:
        if client is not None:
            await client.aio.aclose()


__all__ = ["analyze_public_youtube_video"]