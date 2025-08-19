import requests
import urllib3
import warnings
from typing import Optional, List
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress SSL/TLS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Global session with connection pooling and GZip compression
_session = None

def get_session():
    """Get or create a global session with connection pooling and GZip compression."""
    global _session
    if _session is None:
        _session = requests.Session()
        
        # Add GZip compression header
        _session.headers.update({
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Wikipedia-Dead-Link-Checker/1.0 (https://github.com/thyer/wikipedia-dead-ref-finder; thyer@example.com)'
        })
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=100,
            max_retries=Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
    
    return _session

def get_article_html_batch(titles: List[str], delay: float = 0.2, verbose: bool = False) -> dict:
    """
    Fetch HTML content for multiple Wikipedia articles using Wikimedia REST API.
    This approach is more efficient and has higher rate limits than the Action API.
    
    Args:
        titles: List of Wikipedia article titles
        delay: Delay between API calls in seconds (default: 0.2s for REST API compliance)
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping title to HTML content
    """
    if not titles:
        return {}
    
    session = get_session()
    results = {}
    
    for i, title in enumerate(titles):
        if verbose:
            print(f"Fetching article {i+1}/{len(titles)}: {title}")
        
        # Use Wikimedia REST API endpoint for HTML content (more efficient and higher rate limits)
        url = f"https://en.wikipedia.org/api/rest_v1/page/html/{title}"
        
        # No query parameters needed for REST API
        params = {}
        
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # REST API returns HTML directly, not JSON
            html_content = response.text
            
            # Check if we got actual HTML content
            if html_content and len(html_content) > 100:  # Basic validation that we got content
                results[title] = html_content
                if verbose:
                    print(f"✅ Successfully fetched '{title}' ({len(html_content)} characters)")
            else:
                if verbose:
                    print(f"⚠️  No content found for '{title}'")
            
            # Add delay between requests to be respectful
            if i < len(titles) - 1:
                time.sleep(delay)
                
        except requests.RequestException as e:
            if verbose:
                print(f"Error fetching article '{title}': {e}")
            # Continue with next article instead of failing completely
            continue
        except (KeyError, ValueError) as e:
            if verbose:
                print(f"Error parsing response for '{title}': {e}")
            continue
    
    return results

def get_article_html(title: str, verbose: bool = False) -> str:
    """
    Fetch the HTML content of a single Wikipedia article.
    For multiple articles, use get_article_html_batch() instead.
    
    Args:
        title: The title of the Wikipedia article
        verbose: Enable verbose output
        
    Returns:
        Raw HTML content of the article
    """
    # Use the batch function with a single title for backward compatibility
    results = get_article_html_batch([title], verbose=verbose)
    return results.get(title, "")


def get_article_text(title: str, verbose: bool = False) -> Optional[str]:
    """
    Fetch the plain text content of a Wikipedia article (alternative method).
    
    Args:
        title: The title of the Wikipedia article
        verbose: Enable verbose output
        
    Returns:
        Plain text content of the article
    """
    url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts',
        'exintro': '',
        'explaintext': '',
        'format': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if 'error' in data:
            if verbose:
                print(f"API Error for '{title}': {data['error']['info']}")
            return None
        
        pages = data['query']['pages']
        page_id = list(pages.keys())[0]
        
        if page_id != '-1' and 'extract' in pages[page_id]:
            return pages[page_id]['extract']
        else:
            if verbose:
                print(f"Article '{title}' not found or has no content")
            return None
            
    except requests.RequestException as e:
        if verbose:
            print(f"Error fetching article '{title}': {e}")
        return None
    except (KeyError, ValueError) as e:
        if verbose:
            print(f"Error parsing response for '{title}': {e}")
        return None


if __name__ == "__main__":
    # Test the function
    test_title = "Python_(programming_language)"
    html_content = get_article_html(test_title, verbose=True)
    print(f"HTML content length for '{test_title}': {len(html_content)} characters")
    
    if html_content:
        print("First 200 characters:")
        print(html_content[:200]) 