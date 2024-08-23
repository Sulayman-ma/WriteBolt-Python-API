"""YouTube transcript router"""

from typing import Any, Annotated
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

from fastapi import APIRouter, Query, Response

# Define API Router
router = APIRouter(
    prefix="/transcript",
    tags=['transcript'],
    responses={
        404: {"message": "Transcript not found"},
        400: {"message": "Please include a valid video ID"}
    }
)

"""Path Operations"""
@router.get("/", status_code=200, response_model=list[dict[str, Any]])
async def get_transcript(
    video_id: Annotated[str, Query(title="Video ID", min_length=1)]
) -> Response:
    """Takes a YouTube video's ID and retrieves the transcript from it."""

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id=video_id, 
            languages=['en', 'hi', 'ur', 'es', 'fr', 'de', 'zh-Hans', 'zh-Hant', 'ar', 'pt', 'it', 'ja', 'ko']
        )
        formatter = JSONFormatter()
        json_formatted = formatter.format_transcript(transcript)

        return transcript

    except Exception as e:
        return "[]"
