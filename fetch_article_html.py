import requests
from typing import Optional


def get_article_html(title: str) -> str:
    """
    Fetch the HTML content of a Wikipedia article.
    
    Args:
        title: The title of the Wikipedia article
        
    Returns:
        Raw HTML content of the article
    """
    # MediaWiki API endpoint
    url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        'action': 'parse',
        'page': title,
        'prop': 'text',
        'formatversion': '2',
        'format': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if 'error' in data:
            print(f"API Error for '{title}': {data['error']['info']}")
            return ""
        
        # Extract the HTML content
        if 'parse' in data and 'text' in data['parse']:
            return data['parse']['text']
        else:
            print(f"No content found for article: {title}")
            return ""
            
    except requests.RequestException as e:
        print(f"Error fetching article '{title}': {e}")
        return ""
    except (KeyError, ValueError) as e:
        print(f"Error parsing response for '{title}': {e}")
        return ""


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