import requests
from typing import List, Tuple, Optional, Dict
from tqdm import tqdm
import time
from extract_references import is_archive_url, group_links_with_archives
import re
from urllib.parse import urlparse, urljoin
import socket


def is_likely_bot_blocked(response: requests.Response) -> bool:
    """
    Check if a 403 response is likely due to bot blocking.
    
    Args:
        response: The HTTP response object
        
    Returns:
        True if the response suggests bot blocking
    """
    # Check for common bot-blocking indicators in response headers
    bot_indicators = [
        'cloudflare',
        'captcha',
        'challenge',
        'bot',
        'automated',
        'rate limit',
        'access denied',
        'security',
        'blocked'
    ]
    
    # Check response headers
    for header_name, header_value in response.headers.items():
        header_lower = f"{header_name}: {header_value}".lower()
        for indicator in bot_indicators:
            if indicator in header_lower:
                return True
    
    # For HEAD requests, we can't read content, so rely on headers
    # For GET requests, check response content for bot-blocking messages
    if response.request.method == 'GET':
        try:
            content = response.text.lower()
            blocking_phrases = [
                'access denied',
                'forbidden',
                'blocked',
                'bot detected',
                'automated access',
                'rate limit',
                'captcha',
                'challenge',
                'security check',
                'cloudflare',
                'ddos protection'
            ]
            
            for phrase in blocking_phrases:
                if phrase in content:
                    return True
        except:
            pass
    
    # Bot blocking detection is now based purely on response headers and content
    # rather than hardcoded domain lists
    
    # For 403 responses, be more conservative - only assume bot blocking
    # if we have strong evidence from headers or content
    return False


def check_dns_resolution(url: str) -> bool:
    """
    Check if a URL's domain can be resolved via DNS.
    
    Args:
        url: URL to check
        
    Returns:
        True if DNS resolution succeeds
    """
    try:
        parsed = urlparse(url)
        socket.gethostbyname(parsed.netloc)
        return True
    except (socket.gaierror, socket.herror, ValueError):
        return False


def check_with_alternative_methods(url: str, timeout: float = 5.0) -> Tuple[str, str, Optional[int]]:
    """
    Use alternative methods to check if a URL is actually accessible.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (url, status, status_code)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Method 1: Try with different User-Agent and session for redirects
    try:
        alt_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        session = requests.Session()
        session.headers.update(alt_headers)
        session.max_redirects = 5
        
        response = session.head(url, timeout=timeout, allow_redirects=True)
        # Only consider it alive if the final status code after redirects is < 400
        if response.status_code < 400:
            return url, 'alive', response.status_code
    except:
        pass
    
    # Method 2: Try GET request with session and minimal content download
    try:
        session = requests.Session()
        session.headers.update(headers)
        session.max_redirects = 5
        
        response = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
        # Read only first 1024 bytes to check if content is accessible
        response.raw.read(1024)
        response.close()
        # Only consider it alive if the final status code after redirects is < 400
        if response.status_code < 400:
            return url, 'alive', response.status_code
    except:
        pass
    
    # Method 3: Try without SSL verification (for some problematic sites)
    try:
        session = requests.Session()
        session.headers.update(headers)
        session.max_redirects = 5
        
        response = session.head(url, timeout=timeout, verify=False, allow_redirects=True)
        if response.status_code < 400:
            return url, 'alive', response.status_code
    except:
        pass
    
    # Method 4: Try with more browser-like headers
    try:
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        session = requests.Session()
        session.headers.update(browser_headers)
        session.max_redirects = 5
        
        response = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
        response.close()
        if response.status_code < 400:
            return url, 'alive', response.status_code
    except:
        pass
    
    return url, 'connection_error', None


def validate_redirect_chain(url: str, timeout: float = 5.0) -> Tuple[str, str, Optional[int]]:
    """
    Follow redirect chains and validate the final destination.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (url, status, status_code)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Use session to follow redirects and track the chain
        session = requests.Session()
        session.headers.update(headers)
        
        # First, try HEAD request
        response = session.head(url, timeout=timeout, allow_redirects=True)
        
        # If HEAD works, return success
        if response.status_code < 400:
            return url, 'alive', response.status_code
        
        # If HEAD fails with redirect-related status, try GET
        if response.status_code in [301, 302, 303, 307, 308]:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            response.close()
            if response.status_code < 400:
                return url, 'alive', response.status_code
        
        # Check if it's a bot blocking case
        if response.status_code == 403:
            if is_likely_bot_blocked(response):
                return url, 'blocked', response.status_code
            else:
                return url, 'dead', response.status_code
        
        return url, 'dead', response.status_code
        
    except requests.RequestException as e:
        return url, 'connection_error', None


def check_link_status(url: str, timeout: float = 5.0) -> Tuple[str, str, Optional[int]]:
    """
    Check if a URL is alive using multiple validation methods.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (url, status, status_code)
        status can be: 'alive', 'dead', 'blocked', 'archived', 'connection_error'
    """
    # Skip archive links entirely
    if is_archive_url(url):
        return url, 'archived', None
    
    # Step 1: Check DNS resolution first (fastest check)
    if not check_dns_resolution(url):
        return url, 'connection_error', None
    
    # Step 2: Try standard HEAD request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        # Success case
        if response.status_code < 400:
            return url, 'alive', response.status_code
        
        # Handle 403 (Forbidden) - check if it's bot blocking
        elif response.status_code == 403:
            # Try GET request to get better bot detection
            try:
                get_response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
                get_response.close()
                if is_likely_bot_blocked(get_response):
                    return url, 'blocked', response.status_code
                else:
                    # If not bot blocking, try alternative methods
                    alt_result = check_with_alternative_methods(url, timeout)
                    if alt_result[1] == 'alive':
                        return alt_result
                    else:
                        return url, 'dead', response.status_code
            except:
                # If GET fails, use HEAD response for bot detection
                if is_likely_bot_blocked(response):
                    return url, 'blocked', response.status_code
                else:
                    return url, 'dead', response.status_code
        
        # Handle redirect status codes - these should be followed to final destination
        elif response.status_code in [301, 302, 303, 307, 308]:
            # Use session to properly follow redirects
            try:
                session = requests.Session()
                session.headers.update(headers)
                session.max_redirects = 5  # Allow up to 5 redirects
                
                get_response = session.get(url, timeout=timeout, stream=True)
                get_response.close()
                
                if get_response.status_code < 400:
                    return url, 'alive', get_response.status_code
                else:
                    return url, 'dead', get_response.status_code
            except:
                # If session approach fails, try simple GET
                try:
                    get_response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
                    get_response.close()
                    if get_response.status_code < 400:
                        return url, 'alive', get_response.status_code
                    else:
                        return url, 'dead', get_response.status_code
                except:
                    return url, 'dead', response.status_code
        
        # Other error status codes - try GET request as fallback for 404s
        else:
            # For 404 status codes, try GET request as some servers don't support HEAD
            if response.status_code == 404:
                try:
                    get_response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
                    get_response.close()
                    if get_response.status_code < 400:
                        return url, 'alive', get_response.status_code
                    else:
                        return url, 'dead', get_response.status_code
                except:
                    return url, 'dead', response.status_code
            else:
                return url, 'dead', response.status_code
        
    except requests.RequestException as e:
        # Step 3: If HEAD fails, try GET request
        try:
            response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
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
            
        except requests.RequestException as e2:
            # Step 4: Try alternative methods as last resort
            alt_result = check_with_alternative_methods(url, timeout)
            if alt_result[1] == 'alive':
                return alt_result
            
            # Step 5: Try redirect chain validation
            redirect_result = validate_redirect_chain(url, timeout)
            if redirect_result[1] == 'alive':
                return redirect_result
            
            # All methods failed
            return url, 'connection_error', None


def check_all_links_with_archives(links: List[str], archive_groups: Dict[str, List[str]], 
                                 timeout: float = 5.0, delay: float = 0.1, 
                                 use_secondary_validation: bool = True) -> List[Tuple[str, str, Optional[int]]]:
    """
    Check the status of all links with archive awareness and secondary validation.
    
    Args:
        links: List of URLs to check (should be original URLs only)
        archive_groups: Dictionary mapping original URLs to archive URLs
        timeout: Request timeout in seconds
        delay: Delay between requests to be respectful to servers
        use_secondary_validation: Whether to use secondary validation for potential false positives
        
    Returns:
        List of tuples (url, status, status_code)
    """
    if not links:
        return []
    
    results = []
    
    # Use tqdm for progress bar
    for link in tqdm(links, desc="Checking links", unit="link"):
        # Skip checking links that have associated archives
        if link in archive_groups and archive_groups[link]:
            results.append((link, 'archived', None))
            continue
        
        # Initial check with retry logic
        result = check_link_with_retry(link, timeout, max_retries=1)
        url, status, status_code = result
        
        # Secondary validation for potential false positives
        if use_secondary_validation and status == 'dead':
            result = validate_link_with_secondary_check(link, result, timeout)
            url, status, status_code = result
        
        results.append((url, status, status_code))
        
        # Small delay to be respectful to servers
        if delay > 0:
            time.sleep(delay)
    
    return results


def check_all_links(links: List[str], timeout: float = 5.0, delay: float = 0.1) -> List[Tuple[str, str, Optional[int]]]:
    """
    Check the status of all links with progress bar and rate limiting.
    This is the legacy function for backward compatibility.
    
    Args:
        links: List of URLs to check
        timeout: Request timeout in seconds
        delay: Delay between requests to be respectful to servers
        
    Returns:
        List of tuples (url, status, status_code)
    """
    if not links:
        return []
    
    results = []
    
    # Use tqdm for progress bar
    for link in tqdm(links, desc="Checking links", unit="link"):
        result = check_link_status(link, timeout)
        results.append(result)
        
        # Small delay to be respectful to servers
        if delay > 0:
            time.sleep(delay)
    
    return results


def categorize_links(links_results: List[Tuple[str, str, Optional[int]]]) -> dict:
    """
    Categorize links by their status.
    
    Args:
        links_results: List of (url, status, status_code) tuples
        
    Returns:
        Dictionary with categorized links
    """
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
    """
    Print a summary of link checking results.
    
    Args:
        links_results: List of (url, status, status_code) tuples
    """
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
    
    if archived > 0:
        print(f"\n📦 Archived links found:")
        for url, status_code in categories['archived']:
            print(f"   - {url} (Status: {status_code})")
    
    if errors > 0:
        print(f"\n🔌 Connection errors:")
        for url, _ in categories['connection_error']:
            print(f"   - {url} (Connection failed)")


def validate_with_external_services(url: str) -> Tuple[str, str, Optional[int]]:
    """
    Use external services to validate link status as a secondary check.
    
    Args:
        url: URL to check
        
    Returns:
        Tuple of (url, status, status_code)
    """
    # This is a placeholder for external service integration
    # In a real implementation, you could use:
    # - Google's Safe Browsing API
    # - VirusTotal API
    # - URLVoid API
    # - Web of Trust API
    
    # For now, we'll implement a simple check using common external services
    try:
        # Check if URL is accessible via a different method
        # This could be expanded to use actual external APIs
        
        # For demonstration, we'll just return that we can't determine
        # In practice, you would make API calls to external services
        return url, 'unknown', None
    except:
        return url, 'unknown', None


def check_link_with_retry(url: str, timeout: float = 5.0, max_retries: int = 2) -> Tuple[str, str, Optional[int]]:
    """
    Check a link with retry logic and multiple validation layers.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (url, status, status_code)
    """
    # First attempt
    result = check_link_status(url, timeout)
    
    # If first attempt says it's dead, only try retries if it looks like a false positive
    if result[1] == 'dead' and max_retries > 0 and is_likely_false_positive(url, result[1], result[2]):
        for attempt in range(max_retries):
            # Try with longer timeout
            retry_timeout = timeout * (1.5 ** (attempt + 1))
            retry_result = check_link_status(url, retry_timeout)
            
            if retry_result[1] == 'alive':
                return retry_result
            
            # Try alternative methods
            alt_result = check_with_alternative_methods(url, retry_timeout)
            if alt_result[1] == 'alive':
                return alt_result
            
            # Try redirect validation
            redirect_result = validate_redirect_chain(url, retry_timeout)
            if redirect_result[1] == 'alive':
                return redirect_result
    
    return result


def is_likely_false_positive(url: str, status: str, status_code: Optional[int]) -> bool:
    """
    Check if a link result is likely a false positive.
    
    Args:
        url: The URL that was checked
        status: The status result ('dead', 'alive', etc.)
        status_code: The HTTP status code
        
    Returns:
        True if this is likely a false positive
    """
    if status != 'dead':
        return False
    
    # Only consider redirect status codes as potential false positives
    # since they might indicate the URL is accessible via a different path
    if status_code in [301, 302, 303, 307, 308]:
        return True
    
    # For 404 and other error codes, assume they are genuinely dead
    # unless we have strong evidence to the contrary
    return False


def validate_link_with_secondary_check(url: str, initial_result: Tuple[str, str, Optional[int]], 
                                     timeout: float = 5.0) -> Tuple[str, str, Optional[int]]:
    """
    Perform a secondary validation check on links that appear to be dead.
    
    Args:
        url: The URL to validate
        initial_result: The initial check result
        timeout: Request timeout in seconds
        
    Returns:
        Updated result tuple
    """
    url, status, status_code = initial_result
    
    # If already alive, no need for secondary check
    if status == 'alive':
        return initial_result
    
    # Check if this looks like a false positive
    if is_likely_false_positive(url, status, status_code):
        # Try alternative validation methods
        alt_result = check_with_alternative_methods(url, timeout)
        if alt_result[1] == 'alive':
            return alt_result
        
        # Try redirect chain validation
        redirect_result = validate_redirect_chain(url, timeout)
        if redirect_result[1] == 'alive':
            return redirect_result
        
        # Try with different User-Agent
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
            response.close()
            if response.status_code < 400:
                return url, 'alive', response.status_code
        except:
            pass
    
    return initial_result


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
    results = check_all_links(test_urls, timeout=3.0, delay=0.5)
    
    print_link_summary(results) 