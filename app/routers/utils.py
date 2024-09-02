import requests
from bs4 import BeautifulSoup
from googlesearch import search
from collections import deque, Counter
from urllib.parse import urljoin, urlsplit
from requests.exceptions import HTTPError, ConnectionError



def remove_keys(search_results: list[dict[str, str]], remove_list: list[str]) -> None:
    """Filters the properties in the remove list form the search results in each dict in the search results list"""

    for dictionary in search_results:
        for key in list(dictionary.keys()):
            if key in remove_list:
                dictionary.pop(key)


def reorder(search_results: list[dict]):
    """Reorders the search results to ensure that no more than 2 same sites appear in every 10 blocks"""

    # Add search results to a deque
    temp_results = deque()
    temp_results.extend(search_results)

    display_links = {result['displayLink'] for result in temp_results}

    # Counter object
    counter = Counter(display_links)

    def reset_counters():
        for key in counter:
            counter[key] = 0

    # New list and block tracker
    new_results = []
    block_tracker = 0

    while temp_results:
        # Get next result and add to new reordered list
        result = temp_results.pop()

        # Reset trackers to 0 after every block of 10
        if block_tracker % 10 == 0:
            reset_counters()
        
        # Put back into queue if up to 2 of the same site are in block already
        if counter.get(result['displayLink']) == 2:
            temp_results.append(result)
            block_tracker += 1
            continue

        # Add result to new list and increase tracker count
        new_results.append(result)
        counter[result['displayLink']] += 1
        
        # Increment block count
        block_tracker += 1

    new_results.reverse()
    return new_results


def crawl_with_addons(url: str) -> str | None:
    """Appends common sitemap URL strings to a URL in an attempt to locate the sitemap URL."""
    
    addons = [
        'sitemap',
        'sitemap.xml',
        'sitemap_index.xml',
        'wp-sitemap.xml',
        'sitemap/index.xml',
    ]
    
    # print(f"-> Crawling {url} with addons")
    for addon in addons:
        try:
            # Form URL with added string
            addon_url = urljoin(url, addon)
            
            # Test next endpoint to find root sitemap URL
            response = requests.get(
                url=addon_url,
                # allow_redirects=redirects,
                headers={'User-Agent': 'ResearchEngine'}
            )
            
            code = response.status_code
            response_url = response.url
            
            # OK response and sitemap in the response URL (not redirected)
            if code == 200:
                if 'sitemap' in response_url.casefold():
                    return response_url
                else:
                    continue

            # Handle redirection
            elif code == 301:
                continue
            
            # If neither 200 nor 301, break and move to the next addon
            else:
                # print(f'{addon}: {code}')
                continue
        
        # Retry with redirect enabled if the test endpoint fails
        except requests.ConnectionError as e:
            # print(f'{addon}: failed')
            continue
    
    return None


def crawl_robots(url: str) -> list[str] | None:
    """Crawls a website's robots.txt file if one exists to get the all sitemap URLs listed on it.
    
    :param url: Website root URL
    
    Returns a list of the sitemap URLs or None."""

    url = urljoin(url, 'robots.txt')

    try:
        response = requests.get(
            url=url,
            headers={
                # Refer to notes for why you did this
                'User-Agent': 'ResearchEngine'
            }
        )
        response.raise_for_status()

    except HTTPError as e:
        return None
    
    except ConnectionError:
        return None

    # Split robots.txt lines
    robots_file = response.text
    lines = robots_file.split('\n')

    # Parse sitemaps from file lines
    sitemaps = [line for line in lines if 'Sitemap:' in line]
    sitemaps = [sitemap.split('Sitemap:')[-1].strip() for sitemap in sitemaps]

    # Remove compressed sitemap URL files
    sitemaps = [sitemap for sitemap in sitemaps if not sitemap.endswith('gz')]

    # Convert to set and back to remove duplicate links
    sitemaps = list(set(sitemaps))

    # TODO: For single link return, that's the sitemap index, return it alone

    return sitemaps or None


def crawl_google(url: str) -> str | None:
    """Performs a Google search for the site URL, filetype XML as such:

    site:url filetype:xml inurl:sitemap.
    
    Returns the link of the first result of the Google search."""
    
    term = f"site:{url} filetype:xml inurl:sitemap"
    try:
        results = search(
            term=term, 
            num_results=1,
            sleep_interval=3,
        )
        if not results:
            return None
        
    except HTTPError as e:
        return None
    
    # Get link from results and return as sitemap URL
    return list(results) or None


def crawl_sitemap_index(
        sitemap_url: str | list[str], 
        single: bool = True
) -> dict[str, list[str]] | None:
    """Crawls the XML sitemap index of the site to find the pages, blogs and products sitemap indexes"""

    result_urls = {
        ('pages', 'page'): [],
        ('products', 'product'): [],
        ('blogs', 'blog', 'post', 'posts'): [],
    }
    final_dict = {}

    # print(f'-> Collecting sitemap URLs')
    try:
        # If more than one link was found on the sitemap index, just classify by blogs and add the rest to pages
        if not single:
            final_dict = {
                'pages': [],
                'blogs': [],
            }
            for key in result_urls.keys():
                for url in sitemap_url:
                    path = urlsplit(url).path
                    if 'blog' in path.casefold():
                        final_dict['blogs'].append(url)
                    else:
                        final_dict['pages'].append(url)
            # Remove duplicates
            for key, value in final_dict.items():
                final_dict[key] = list(set(value))
            return final_dict

        response = requests.get(
            url=sitemap_url,
            headers={
                # Refer to notes for why you did this
                'User-Agent': 'ResearchEngine'
            }
        )
        response.raise_for_status()

        # Parse for both HTML and XML sitemaps
        if sitemap_url.endswith('xml'):
            soup = BeautifulSoup(response.content, 'xml')
            tags = soup.find_all('loc')
            links = [tag.text for tag in tags]
        else:
            soup = BeautifulSoup(response.content, 'html.parser')
            tags = soup.find_all('a')
            tags = [tag for tag in tags if tag.get('href') is not None]
            links = [tag.get('href') for tag in tags]
            # Form full URLs
            links = [urljoin(sitemap_url, link) for link in links]
            # Remove sitemap URL if it is repeated in links
            try:
                links.remove(sitemap_url)
            except ValueError:
                pass

        # Get pages, blogs and products
        for key in result_urls.keys():
            for link in links:
                # print(f"Checking {link}")
                path = urlsplit(link).path
                # If any of the key search words exists in the link path, add it
                if any(k in path.casefold() for k in key):
                    # add = links.pop(links.index(link))
                    result_urls[key].append(link)

        # Strip keys back to single words
        for key, value in result_urls.items():
            key = key[0]
            final_dict[key] = value

        # FALLBACK FOR BLOGS AND PAGES
        if not final_dict['blogs'] and not final_dict['pages']:
            for link in links:
                path = urlsplit(link).path
                if 'blog' in path.casefold():
                    final_dict['blogs'].append(link)
                else:
                    final_dict['pages'].append(link)

        # Remove duplicates
        for key, value in final_dict.items():
            final_dict[key] = list(set(value))

        return final_dict

    except HTTPError as e:
        # print(f"HTTP Error: {e.response.status_code}")
        return None
    
    except Exception as e:
        # print(f"Exception: {e}")
        return None


async def locate_sitemap_urls(url: str) -> tuple[str, dict[str, list[str]]] | None:
    """Full function

    1. Locates a website's sitemap URL starting with the addons method. If that fails, it moves on to parse the robots.txt file
    2. If both fail, it essentially returns None.
    
    Returns a dictionary of all the sitemap classifications needed."""

    sitemap_urls = None
    sitemap_index = None

    # Try with addons
    results = crawl_with_addons(url)
    if not results:
        # Try with robots.txt
        results = crawl_robots(url)
        if results:
            if len(results) == 1:
                sitemap_index = results[0]
                sitemap_urls = crawl_sitemap_index(results[0])
            else:
                # Select the index sitemap
                for result in results:
                    path = urlsplit(result).path.casefold()
                    if 'index.xml' in path or \
                    'sitemap_index.xml' in path or \
                    'sitemap-index.xml' in path or \
                    'sitemap-index-0.xml' in path or \
                    'sitemap/index.xml' in path :
                        sitemap_index = result
                        break
                sitemap_urls = crawl_sitemap_index(results, single=False)
        else:
            # Try Google search
            results = crawl_google(url)
            if results:
                sitemap_index = results
                sitemap_urls = crawl_sitemap_index(results)
            else:
                pass
    else:
        sitemap_index = results
        # If URL was found with addons, crawl and get page, blog and products
        sitemap_urls = crawl_sitemap_index(results)

    return_tuple = (sitemap_index, sitemap_urls)
    return return_tuple if any(return_tuple) else None
