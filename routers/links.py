import re
from fastapi import Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException
import requests.compat

# Define API Router
router = APIRouter(
    prefix="/blog-index",
    tags=['blog_index'],
    responses={
        404: {"message": "Endpoint not found"},
    }
)

"""Path Operations"""
@router.get("/", status_code=200)
async def blog_index(url: str) -> Response:
    """Does a bunch of stuff which I will be absolutely sure to document later before pushing to production."""

    # URL response object
    response = await requests.get(
        url=url,
        headers={
            'User-Agent': "WriteBolt-API"
        }
    )

    # Raise HTTP exception if site cannot be reached
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, 
            detail="Unable to fetch webpage"
        )

    # Get the main article content
    soup = BeautifulSoup(response.content, "html.parser")
    main = soup.select_one("div#main") or soup.select_one("div#content")
    main_pattern = r'(main)|(content)'
    main = soup.find(
        lambda tag: (
            (
                tag.name == 'div' and 
                re.search(main_pattern, tag.get('id', ''), re.IGNORECASE) or
                re.search(main_pattern, ' '.join(tag.get('class', [])), re.IGNORECASE)
            ) 
            or
            tag.name == 'main'
        )
    )

    # TODO: use first column in case where blog content is split into sidebar and main content

    links = [
        a.get('href') 
        for a in main.find_all("a")
    ]

    # Count links per 1k words
    word_count = len(main.text.split())
    links_per_1k_words = (len(links) / word_count) * 1000

    # Equal to 5-6 links per 1k words
    if 5 <= links_per_1k_words <= 6:
        return {'code': 550}

    else:
        # Get first 10 links in header and footer
        header = soup.find(
            lambda tag: (
                tag.name == 'header' or

                tag.name == 'div' and 
                re.search(r'header', tag.get('id', ''), re.IGNORECASE) or
                re.search(r'header', ' '.join(tag.get('class', [])), re.IGNORECASE)
            )
        )
        footer = soup.find(
            lambda tag: (
                tag.name == 'footer' or

                tag.name == 'div' and 
                re.search(r'footer', tag.get('id', ''), re.IGNORECASE) or
                re.search(r'footer', ' '.join(tag.get('class', [])), re.IGNORECASE)
            )
        )
        if header:  
            header_links = header.select("a")[:15]
        if footer:
            footer_links = footer.select("a")[:15]

        # Blog link and list of blog releases
        blog_index = []
        blog_url = ''
        blog_reached = True

        # Search for blog page link in links from header and footer's first 10 links
        if header_links or footer_links:
            for batch in zip(header_links, footer_links):
                for link in batch:
                    try:
                        if 'blog/' in link.get('href'):
                            blog_url = link.get('href')
                            break
                    except AttributeError:
                        pass
                if blog_url:
                    break

        # Form blog URL if not found in header and footer
        if not blog_url:
            blog_url = urljoin(url, 'blog')

        # Parse blog page for the 5 most recent blog posts
        blog_res = await requests.get(
            url=blog_url,
            headers={
                'User-Agent': "WriteBolt-API"
            }
        )

        # Blog URL cannot be retrived
        if blog_res.status_code != 200:
            blog_reached = False
        else:
            """Fetch 5 most recent blog posts"""
            blog_soup = BeautifulSoup(blog_res.content, "html.parser")

            # Get blog titles and parse for the links
            title_pattern = r'(entry)|(title)'
            headers = blog_soup.find_all(
                lambda tag: (
                    tag.name == 'h3' or
                    tag.name == 'h6' or
                    # Other header tags with entry or title in the class name
                    (
                        tag.name == 'h2' or
                        tag.name == 'h4' or 
                        tag.name == 'h5' 
                    ) and
                    re.search(
                        pattern=title_pattern, 
                        string=' '.join(tag.get('class', [])), 
                        flags=re.IGNORECASE
                    )
                )
            )
            if headers:
                for header in headers:
                    anchor = header.select_one('a')
                    if anchor:
                        link = anchor.get('href')
                        blog_index.append(link)

            # Return top 5
            blog_index = blog_index[:5]

        # Less than 5-6 (in which case less than 5 is reasonable)
        if links_per_1k_words < 5:
            return {
                'code': 501,
                'numLinks': int(links_per_1k_words),
                'blogURL': blog_url,
                'blogReached': blog_reached,
                'blogIndex': blog_index
            }

        # More than 5-6, (essentially more than 6)
        else:
            return {
                'code': 502,
                'numLinks': int(links_per_1k_words),
                'blogURL': blog_url,
                'blogReached': blog_reached,
                'blogIndex': blog_index
            }
