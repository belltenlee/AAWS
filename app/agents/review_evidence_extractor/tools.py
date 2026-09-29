from app.tools.common import file_read, file_writer, web_fetch, web_search
from app.tools.navigator import browse_web
from app.tools.youtube_video_analysis import analyze_public_youtube_video

tools_review_evidence_extractor = [
    file_read,
    file_writer,
    web_search,
    web_fetch,
    browse_web,
    analyze_public_youtube_video,
]

__all__ = ["tools_review_evidence_extractor"]