import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.tools.youtube_data import (
    youtube_list_channel_videos,
    youtube_search_channels,
    youtube_search_videos,
)
from app.tools.youtube_video_analysis import analyze_public_youtube_video


class YouTubeDataToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_channel_search_returns_uploads_playlist(self):
        api_responses = [
            {"items": [{"id": {"channelId": "UC_test"}}]},
            {
                "items": [{
                    "id": "UC_test",
                    "snippet": {"title": "귀곰", "customUrl": "@gwigom"},
                    "statistics": {"videoCount": "42"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}},
                }]
            },
        ]
        with patch(
            "app.tools.youtube_data._youtube_get",
            new=AsyncMock(side_effect=api_responses),
        ):
            result = json.loads(await youtube_search_channels.ainvoke({"query": "귀곰"}))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["channels"][0]["channel_id"], "UC_test")
        self.assertEqual(result["channels"][0]["uploads_playlist_id"], "UU_test")

    async def test_upload_list_preserves_dates_and_next_page_token(self):
        api_responses = [
            {
                "items": [{
                    "id": "UC_test",
                    "snippet": {"title": "귀곰", "customUrl": "@gwigom"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}},
                }]
            },
            {
                "items": [{
                    "snippet": {
                        "title": "로봇청소기 비교",
                        "channelId": "UC_test",
                        "channelTitle": "귀곰",
                    },
                    "contentDetails": {
                        "videoId": "video_1",
                        "videoPublishedAt": "2026-01-02T03:04:05Z",
                    },
                }],
                "nextPageToken": "next_page",
                "pageInfo": {"totalResults": 42},
            },
        ]
        with patch(
            "app.tools.youtube_data._youtube_get",
            new=AsyncMock(side_effect=api_responses),
        ):
            result = json.loads(
                await youtube_list_channel_videos.ainvoke({"channel_id": "UC_test"})
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["videos"][0]["video_id"], "video_1")
        self.assertEqual(result["videos"][0]["published_at"], "2026-01-02T03:04:05Z")
        self.assertEqual(result["next_page_token"], "next_page")

    async def test_uses_gomm_channel_id_from_environment(self):
        api_responses = [
            {
                "items": [{
                    "id": "UC_gomm",
                    "snippet": {"title": "귀곰"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU_gomm"}},
                }]
            },
            {"items": [], "pageInfo": {"totalResults": 0}},
        ]
        api_get = AsyncMock(side_effect=api_responses)
        with patch.dict(os.environ, {"YOUTUBE_GOMM_CHANNEL_ID": "UC_gomm", "YOUTUBE_CHANNEL_ID": ""}):
            with patch("app.tools.youtube_data._youtube_get", new=api_get):
                result = json.loads(await youtube_list_channel_videos.ainvoke({}))

        self.assertEqual(result["status"], "success")
        self.assertEqual(api_get.await_args_list[0].args[1]["id"], "UC_gomm")

    async def test_video_search_returns_title_description_and_date(self):
        api_response = {
            "items": [{
                "id": {"videoId": "video_2"},
                "snippet": {
                    "title": "로봇청소기 비교 리뷰",
                    "description": "제품별 청소 성능과 추천 순위를 비교합니다.",
                    "channelId": "UC_gomm",
                    "channelTitle": "귀곰",
                    "publishedAt": "2026-09-01T00:00:00Z",
                },
            }],
            "nextPageToken": "next_page",
        }
        api_get = AsyncMock(return_value=api_response)
        with patch.dict(os.environ, {"YOUTUBE_GOMM_CHANNEL_ID": "UC_gomm"}):
            with patch("app.tools.youtube_data._youtube_get", new=api_get):
                result = json.loads(await youtube_search_videos.ainvoke({
                    "query": "로봇청소기",
                    "order": "relevance",
                }))

        self.assertEqual(result["videos"][0]["title"], "로봇청소기 비교 리뷰")
        self.assertIn("성능", result["videos"][0]["description"])
        self.assertEqual(result["videos"][0]["published_at"], "2026-09-01T00:00:00Z")
        self.assertEqual(api_get.await_args.args[1]["order"], "relevance")

    async def test_gemini_video_analysis_forwards_public_youtube_uri(self):
        class FakeInteractions:
            async def create(self, **kwargs):
                self.request = kwargs
                return type("Result", (), {"output_text": '{"recommendation_groups":[]}'})()

        class FakeAsyncClient:
            def __init__(self):
                self.interactions = FakeInteractions()
                self.closed = False

            async def aclose(self):
                self.closed = True

        fake_client = FakeAsyncClient()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("app.tools.youtube_video_analysis.genai.Client", return_value=type(
                "FakeClient", (), {"aio": fake_client}
            )()):
                result = await analyze_public_youtube_video.ainvoke({
                    "video_url": "https://www.youtube.com/watch?v=video_1",
                    "category": "로봇청소기",
                })

        analysis = json.loads(result)
        self.assertIn("recommendation_groups", analysis)
        self.assertEqual(analysis["video_url"], "https://www.youtube.com/watch?v=video_1")
        self.assertEqual(analysis["category"], "로봇청소기")
        self.assertEqual(
            fake_client.interactions.request["input"][1]["uri"],
            "https://www.youtube.com/watch?v=video_1",
        )
        self.assertTrue(fake_client.closed)

    async def test_gemini_video_analysis_rejects_mismatched_video_url(self):
        class FakeInteractions:
            async def create(self, **kwargs):
                return type("Result", (), {"output_text": '{"video_url":"https://www.youtube.com/watch?v=placeholder","category":"로봇청소기","recommendation_groups":[]}'} )()

        class FakeAsyncClient:
            interactions = FakeInteractions()

            async def aclose(self):
                pass

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("app.tools.youtube_video_analysis.genai.Client", return_value=type(
                "FakeClient", (), {"aio": FakeAsyncClient()}
            )()):
                result = await analyze_public_youtube_video.ainvoke({
                    "video_url": "https://www.youtube.com/watch?v=video_1",
                    "category": "로봇청소기",
                })

        self.assertIn("different video URL", result)

    async def test_gemini_video_analysis_rejects_non_youtube_url(self):
        with patch("app.tools.youtube_video_analysis.genai.Client") as client_factory:
            result = await analyze_public_youtube_video.ainvoke({
                "video_url": "https://example.com/video",
                "category": "로봇청소기",
            })

        self.assertIn("valid HTTPS YouTube video URL", result)
        client_factory.assert_not_called()

    async def test_missing_api_key_fails_without_network_request(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}):
            result = json.loads(await youtube_search_channels.ainvoke({"query": "귀곰"}))

        self.assertEqual(result["status"], "error")
        self.assertIn("YOUTUBE_API_KEY", result["message"])


if __name__ == "__main__":
    unittest.main()