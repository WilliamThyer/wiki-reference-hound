import requests
import urllib3
import warnings
from typing import List, Tuple, Optional, Dict
from tqdm import tqdm
import time
from extract_references import is_archive_url
import socket
import concurrent.futures
from threading import Lock

# Suppress SSL/TLS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Constants
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
DEFAULT_HEADERS = {
    'User-Agent': DEFAULT_USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def is_likely_bot_blocked(response: requests.Response) -> bool:
    """Check if a 403 response is likely due to bot blocking."""
    bot_indicators = [
        'cloudflare', 'captcha', 'challenge', 'bot', 'automated',
        'rate limit', 'access denied', 'security', 'blocked'
    ]
    
    # Check response headers
    for header_name, header_value in response.headers.items():
        header_lower = f"{header_name}: {header_value}".lower()
        for indicator in bot_indicators:
            if indicator in header_lower:
                return True
    
    # Check response content for GET requests
    if response.request.method == 'GET':
        try:
            content = response.text.lower()
            blocking_phrases = [
                'access denied', 'forbidden', 'blocked', 'bot detected',
                'automated access', 'rate limit', 'captcha', 'challenge',
                'security check', 'cloudflare', 'ddos protection'
            ]
            
            for phrase in blocking_phrases:
                if phrase in content:
                    return True
        except:
            pass
    
    return False


def check_dns_resolution(url: str) -> bool:
    """Check if a URL's domain can be resolved via DNS."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        socket.gethostbyname(parsed.netloc)
        return True
    except (socket.gaierror, socket.herror, ValueError):
        return False


def check_link_status(url: str, timeout: float = 5.0) -> Tuple[str, str, Optional[int]]:
    """
    Check if a URL is alive using HTTP requests.
    
    Returns:
        Tuple of (url, status, status_code)
        status can be: 'alive', 'dead', 'blocked', 'archived', 'connection_error'
    """
    # Skip archive links entirely
    if is_archive_url(url):
        return url, 'archived', None
    
    # Check DNS resolution first
    if not check_dns_resolution(url):
        return url, 'connection_error', None
    
    try:
        # Try HEAD request first
        response = requests.head(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True)
        
        # Success case
        if response.status_code < 400:
            return url, 'alive', response.status_code
        
        # Handle 403 (Forbidden) - check if it's bot blocking
        elif response.status_code == 403:
            if is_likely_bot_blocked(response):
                return url, 'blocked', response.status_code
            else:
                return url, 'dead', response.status_code
        
        # Handle redirect status codes
        elif response.status_code in [301, 302, 303, 307, 308]:
            # Try GET request to follow redirects
            try:
                get_response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True, stream=True)
                get_response.close()
                if get_response.status_code < 400:
                    return url, 'alive', get_response.status_code
                else:
                    return url, 'dead', get_response.status_code
            except:
                return url, 'dead', response.status_code
        
        # For 404 status codes, try GET request as some servers don't support HEAD
        elif response.status_code == 404:
            try:
                get_response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True, stream=True)
                get_response.close()
                if get_response.status_code < 400:
                    return url, 'alive', get_response.status_code
                else:
                    return url, 'dead', get_response.status_code
            except:
                return url, 'dead', response.status_code
        
        # Other error status codes
        else:
            return url, 'dead', response.status_code
        
    except requests.RequestException:
        # If HEAD fails, try GET request
        try:
            response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS, allow_redirects=True, stream=True)
            response.close()
            if response.status_code < 400:
                return url, 'alive', response.status_code
            elif response.status_code == 403:
                if is_likely_bot_blocked(response):
                    return url, 'blocked', response.status_code
                else:
                    return url, 'dead', response.status_code
            else:
                return url, 'dead', response.status_code
            
        except requests.RequestException:
            return url, 'connection_error', None


def check_all_links_with_archives(links: List[str], archive_groups: Dict[str, List[str]], 
                                 timeout: float = 5.0, delay: float = 0.1) -> List[Tuple[str, str, Optional[int]]]:
    """Check the status of all links with archive awareness."""
    if not links:
        return []
    
    results = []
    
    for link in tqdm(links, desc="Checking links", unit="link"):
        # Skip checking links that have associated archives
        if link in archive_groups and archive_groups[link]:
            results.append((link, 'archived', None))
            continue
        
        result = check_link_status(link, timeout)
        results.append(result)
        
        # Small delay to be respectful to servers
        if delay > 0:
            time.sleep(delay)
    
    return results


def check_all_links_with_archives_parallel(links: List[str], archive_groups: Dict[str, List[str]], 
                                          timeout: float = 5.0, max_workers: int = 20,
                                          chunk_size: int = 100) -> List[Tuple[str, str, Optional[int]]]:
    """Check links in parallel using ThreadPoolExecutor."""
    if not links:
        return []
    
    results = []
    
    # Filter out archived links first
    links_to_check = []
    for link in links:
        if link in archive_groups and archive_groups[link]:
            results.append((link, 'archived', None))
        else:
            links_to_check.append(link)
    
    if not links_to_check:
        return results
    
    def process_chunk(chunk_links: List[str]) -> List[Tuple[str, str, Optional[int]]]:
        chunk_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(check_link_status, url, timeout): url 
                for url in chunk_links
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    chunk_results.append(result)
                except Exception:
                    chunk_results.append((url, 'connection_error', None))
        
        return chunk_results
    
    # Process links in chunks
    with tqdm(total=len(links_to_check), desc=f"Checking links ({max_workers} workers)", unit="link") as pbar:
        for i in range(0, len(links_to_check), chunk_size):
            chunk = links_to_check[i:i + chunk_size]
            chunk_results = process_chunk(chunk)
            results.extend(chunk_results)
            pbar.update(len(chunk))
    
    return results


def categorize_links(links_results: List[Tuple[str, str, Optional[int]]]) -> dict:
    """Categorize links by their status."""
    categories = {
        'alive': [],
        'dead': [],
        'blocked': [],
        'archived': [],
        'connection_error': []
    }
    
    for url, status, status_code in links_results:
        if status == 'alive':
            categories['alive'].append((url, status_code))
        elif status == 'dead':
            categories['dead'].append((url, status_code))
        elif status == 'blocked':
            categories['blocked'].append((url, status_code))
        elif status == 'archived':
            categories['archived'].append((url, status_code))
        elif status == 'connection_error':
            categories['connection_error'].append((url, None))
    
    return categories


def print_link_summary(links_results: List[Tuple[str, str, Optional[int]]]) -> None:
    """Print a summary of link checking results."""
    if not links_results:
        print("No links to check.")
        return
    
    categories = categorize_links(links_results)
    
    total = len(links_results)
    alive = len(categories['alive'])
    dead = len(categories['dead'])
    blocked = len(categories['blocked'])
    archived = len(categories['archived'])
    errors = len(categories['connection_error'])
    
    print(f"\n📊 Link Check Summary:")
    print(f"   Total links: {total}")
    print(f"   ✅ Alive: {alive}")
    print(f"   ❌ Dead: {dead}")
    print(f"   🚫 Blocked (403): {blocked}")
    print(f"   📦 Archived: {archived}")
    print(f"   🔌 Connection errors: {errors}")
    
    if dead > 0:
        print(f"\n❌ Dead links found:")
        for url, status_code in categories['dead']:
            print(f"   - {url} (Status: {status_code})")
    
    if blocked > 0:
        print(f"\n🚫 Blocked links (likely bot protection):")
        for url, status_code in categories['blocked']:
            print(f"   - {url} (Status: {status_code})")


if __name__ == "__main__":
    # Test the function with some sample URLs
    test_urls = [
        "https://httpstat.us/200",
        "https://httpstat.us/404",
        "https://httpstat.us/403",
        "https://httpstat.us/500",
        "https://nonexistentdomain12345.com",
        "https://google.com"
    ]
    
    print("Testing link checker...")
    results = check_all_links_with_archives(test_urls, {}, timeout=3.0, delay=0.5)
    print_link_summary(results) 