from app.tools.common import file_read, file_writer, web_fetch, web_search
from app.tools.youtube_data import youtube_search_channels, youtube_search_videos

tools_review_video_discovery = [
	youtube_search_channels,
	youtube_search_videos,
	file_read,
	file_writer,
	web_search,
	web_fetch,
]

__all__ = ["tools_review_video_discovery"]