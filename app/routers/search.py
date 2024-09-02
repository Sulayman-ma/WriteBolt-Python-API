"""Programmable search engine router."""
import os
import requests
from typing import Any, Annotated

from fastapi import APIRouter, Query, Response

from .utils import (
    reorder,
    remove_keys,
)

# Define API Router
router = APIRouter(
    prefix="/search",
    tags=['search'],
    responses={
        400: {"message": "Please include a query in your search"}
    }
)

"""Path Operations"""
@router.get("/", status_code=200, response_model=dict[str, Any])
async def search(
    q: Annotated[str, Query(title="Search query", min_length=1)]
) -> Response:
    """Google custom search engine API (and others to be added later on)"""

    q = q.replace(" ", "+")

    # API key and search engine ID
    api_key = os.environ.get('GSE_KEY')
    engine_id = os.environ.get('GSE_ENGINE_ID')

    # Stores all items dicts from the search results
    complete_results = []

    # Results info to remove
    remove_list = [
        'cacheId',
        'kind',
    ]

    # Search limit
    search_limit = 30
    limit_temp = search_limit

    # Start index for page results at 10 per page
    page_index = 1

    # Page count tracker
    count = 1
    while limit_temp > 0:
        # Google API endpoint
        endpoint = f"https://customsearch.googleapis.com/customsearch/v1?key={api_key}&cx={engine_id}&q={q}&num=10&start={page_index}"

        # Query API for search results
        response = requests.get(endpoint)

        if response.status_code != 200:
            response_data = response.json()
            return {
                'status': 'failed',
                'data': response_data
            }

        search_results = dict(response.json())

        if items:=search_results.get('items'):
            # Add to complete list
            complete_results.extend(items)

            # Move to next page (next 10 results)
            page_index += 10
            limit_temp -= 10
            count += 1
            continue
        else:
            # Break search when there are no/no more results
            break

    # Return 404 and failed message if results are empty
    if not complete_results:
        return {
            'status': 'empty',
            'resultsCount': 0,
            'message': 'no search results for the query'
        }

    # Filter unneeded properties
    remove_keys(complete_results, remove_list)

    # Rearrange results to remove duplicates in every 10 blocks
    complete_results = reorder(complete_results[:search_limit])
    return {
        'status': 'success',
        'resultsCount': f'{len(complete_results)}',
        'message': 'found results for this query',
        'data': complete_results,
    }
