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
            'User-Agent': 'Wikipedia-Dead-Link-Checker/1.0 (https://github.com/your-repo; your-email@example.com)'
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

def get_article_html_batch(titles: List[str], delay: float = 0.1) -> dict:
    """
    Fetch HTML content for multiple Wikipedia articles in a single API call.
    This is much more efficient than individual calls and respects API guidelines.
    
    Args:
        titles: List of Wikipedia article titles
        delay: Delay between API calls in seconds
        
    Returns:
        Dictionary mapping title to HTML content
    """
    if not titles:
        return {}
    
    session = get_session()
    results = {}
    
    # Process titles in batches of 50 (Wikipedia API limit)
    batch_size = 50
    
    for i in range(0, len(titles), batch_size):
        batch_titles = titles[i:i + batch_size]
        
        # MediaWiki API endpoint
        url = "https://en.wikipedia.org/w/api.php"
        
        # Use pipe separator to request multiple articles in one call
        params = {
            'action': 'parse',
            'page': '|'.join(batch_titles),
            'prop': 'text',
            'formatversion': '2',
            'format': 'json'
        }
        
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'error' in data:
                if data['error'].get('code') == 'ratelimited':
                    # Implement exponential backoff for rate limits
                    wait_time = delay * 2
                    print(f"⚠️  Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    delay = min(delay * 2, 10.0)  # Exponential backoff, max 10s
                    continue
                else:
                    print(f"API Error: {data['error']['info']}")
                    continue
            
            # Extract HTML content for each article
            if 'parse' in data:
                # Handle single article response
                if isinstance(data['parse'], dict):
                    title = data['parse'].get('title', '')
                    if 'text' in data['parse']:
                        results[title] = data['parse']['text']
                # Handle multiple articles response
                elif isinstance(data['parse'], list):
                    for article in data['parse']:
                        title = article.get('title', '')
                        if 'text' in article:
                            results[title] = article['text']
            
            # Add delay between batches to be respectful
            if i + batch_size < len(titles):
                time.sleep(delay)
                
        except requests.RequestException as e:
            print(f"Error fetching batch of articles: {e}")
            # Continue with next batch instead of failing completely
            continue
        except (KeyError, ValueError) as e:
            print(f"Error parsing response: {e}")
            continue
    
    return results

def get_article_html(title: str) -> str:
    """
    Fetch the HTML content of a single Wikipedia article.
    For multiple articles, use get_article_html_batch() instead.
    
    Args:
        title: The title of the Wikipedia article
        
    Returns:
        Raw HTML content of the article
    """
    # Use the batch function with a single title for backward compatibility
    results = get_article_html_batch([title])
    return results.get(title, "")


def get_article_text(title: str) -> Optional[str]:
    """
    Fetch the plain text content of a Wikipedia article (alternative method).
    
    Args:
        title: The title of the Wikipedia article
        
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
            print(f"API Error for '{title}': {data['error']['info']}")
            return None
        
        pages = data['query']['pages']
        page_id = list(pages.keys())[0]
        
        if page_id != '-1' and 'extract' in pages[page_id]:
            return pages[page_id]['extract']
        else:
            print(f"Article '{title}' not found or has no content")
            return None
            
    except requests.RequestException as e:
        print(f"Error fetching article '{title}': {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing response for '{title}': {e}")
        return None


if __name__ == "__main__":
    # Test the function
    test_title = "Python_(programming_language)"
    html_content = get_article_html(test_title)
    print(f"HTML content length for '{test_title}': {len(html_content)} characters")
    
    if html_content:
        print("First 200 characters:")
        print(html_content[:200]) 