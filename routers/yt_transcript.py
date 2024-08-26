"""YouTube transcript router"""

from typing import Any, Annotated
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable

from fastapi import APIRouter, Query, Response

# Define API Router
router = APIRouter(
    prefix="/transcript",
    tags=['transcript'],
    responses={
        400: {"message": "Please include a valid video ID"}
    }
)

"""Path Operations"""
@router.get(path="/", status_code=200)
async def get_transcript(
    video_id: Annotated[str, Query(title="Video ID", min_length=1)]
) -> Response:
    """Takes a YouTube video's ID and retrieves the transcript from it."""

    try:
        transcript = await YouTubeTranscriptApi.get_transcript(
            video_id=video_id, 
            languages=['en', 'hi', 'ur', 'es', 'fr', 'de', 'zh-Hans', 'zh-Hant', 'ar', 'pt', 'it', 'ja', 'ko']
        )
        # formatter = JSONFormatter()
        # json_formatted = formatter.format_transcript(transcript)

        return transcript

    except TranscriptsDisabled as e:
        return {
            "status": "failed",
            "message": "Transcript disabled",
            "error": e
        }

    except NoTranscriptAvailable as e:
        return {
            "status": "failed",
            "message": "Transcript unavailable",
            "error": e
        }

    except Exception as e:
        return {
            "status": "failed",
            "message": "Server exception",
            "error": e
        }
