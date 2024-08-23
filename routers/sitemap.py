"""Sitemaps router."""
from fastapi import APIRouter, Query

from typing import Any, Annotated

from ..dependencies import locate_sitemap_urls

router = APIRouter(
    prefix="/sitemap",
    tags=['sitemap'],
    responses={
        404: {"message": "Endpoint not found"},
        500: {
            "message": "Sitemap retrieval failed",
            "status": "Failed"
        }
    }
)


@router.get("/")
async def get_sitemap(
    url: Annotated[str, Query(title="Website URL", min_length=1)]
):
    """Retrieves the sitemap URLs of any given website in the query parameter. These include; main sitemap, blog sitemap, product sitemap and page sitemap"""

    try:
        if url == '' or 'http' not in url.casefold():
            return {
                'status': 'bad request',
                'message': 'please include a valid url in your request',
                'code': 400
            }
    except AttributeError:
        return {
            'status': 'bad request',
            'message': 'please include a valid url in your request',
            'code': 400
        }

    try:
        # Get sitemap results
        sitemap_result = locate_sitemap_urls(url)

        if sitemap_result:
            # Get sitemap URL and other URLs
            sitemap_url = sitemap_result[0]
            other_urls = sitemap_result[1]

            # Return JSONified response
            return {
                'status': 'success',
                'message': 'sitemap urls retrieved',
                'sitemap': sitemap_url,
                'otherUrls': other_urls,
                'code': 200
            }
        else:
            return {
                'status': 'empty',
                'message': 'no sitemap urls found',
                'code': 404
            }
    except Exception as e:
        return {
            'status': 'failed',
            'message': 'a server error has occured',
            'code': 500,
            'error': e
        }
