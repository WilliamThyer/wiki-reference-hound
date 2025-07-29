import re
from typing import List, Optional
from urllib.parse import urlparse


def clean_article_title(title: str) -> str:
    """
    Clean and normalize a Wikipedia article title.
    
    Args:
        title: Raw article title
        
    Returns:
        Cleaned title
    """
    # Replace underscores with spaces
    title = title.replace('_', ' ')
    
    # Remove any extra whitespace
    title = ' '.join(title.split())
    
    return title


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: URL to validate
        
    Returns:
        True if the URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing common tracking parameters and fragments.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    if not url:
        return url
    
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'campaign'
    ]
    
    parsed = urlparse(url)
    query_params = parsed.query.split('&') if parsed.query else []
    
    # Filter out tracking parameters
    filtered_params = []
    for param in query_params:
        if '=' in param:
            key = param.split('=')[0]
            if key not in tracking_params:
                filtered_params.append(param)
    
    # Reconstruct URL without tracking parameters
    new_query = '&'.join(filtered_params) if filtered_params else ''
    
    # Remove fragment
    new_parsed = parsed._replace(query=new_query, fragment='')
    
    return new_parsed.geturl()


def extract_domain(url: str) -> Optional[str]:
    """
    Extract the domain from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name or None if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return None


def is_likely_dead_link(url: str, status_code: Optional[int]) -> bool:
    """
    Determine if a link is likely dead based on status code and URL patterns.
    
    Args:
        url: The URL
        status_code: HTTP status code
        
    Returns:
        True if the link is likely dead
    """
    # If we have a status code, use it
    if status_code is not None:
        return status_code >= 400
    
    # If no status code (connection error), it's likely dead
    return True


def group_links_by_domain(links: List[str]) -> dict:
    """
    Group links by their domain.
    
    Args:
        links: List of URLs
        
    Returns:
        Dictionary mapping domains to lists of URLs
    """
    domain_groups = {}
    
    for url in links:
        domain = extract_domain(url)
        if domain:
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(url)
    
    return domain_groups


def print_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """
    Print a simple progress indicator.
    
    Args:
        current: Current item number
        total: Total number of items
        prefix: Prefix text for the progress message
    """
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"\r{prefix}: {current}/{total} ({percentage:.1f}%)", end='', flush=True)
    
    if current == total:
        print()  # New line when complete


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


if __name__ == "__main__":
    # Test utility functions
    test_urls = [
        "https://example.com/page?utm_source=test&param=value#section",
        "https://test.com/",
        "invalid_url",
        "https://google.com/search?q=test&gclid=123"
    ]
    
    print("Testing URL utilities:")
    for url in test_urls:
        print(f"  Original: {url}")
        print(f"  Normalized: {normalize_url(url)}")
        print(f"  Domain: {extract_domain(url)}")
        print(f"  Valid: {is_valid_url(url)}")
        print() 