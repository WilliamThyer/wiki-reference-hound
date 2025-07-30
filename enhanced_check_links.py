#!/usr/bin/env python3
"""
Enhanced link checking with browser validation for false positive detection.
"""

import time
from typing import List, Tuple, Optional, Dict
from check_links import (
    check_all_links_with_archives_parallel,
    categorize_links,
    print_link_summary
)
from browser_validation import (
    validate_dead_links_with_browser,
    create_browser_validation_report,
    print_browser_validation_summary,
    is_likely_false_positive_browser
)


def check_links_with_browser_validation(
    links: List[str],
    archive_groups: Dict[str, List[str]],
    timeout: float = 5.0,
    max_workers: int = 20,
    chunk_size: int = 100,
    browser_timeout: int = 30,
    browser_headless: bool = True,
    enable_browser_validation: bool = True
) -> Tuple[List[Tuple[str, str, Optional[int]]], Dict]:
    """
    Check links with HTTP requests and validate dead links using browser automation.
    
    Args:
        links: List of URLs to check
        archive_groups: Dictionary mapping original URLs to archive URLs
        timeout: HTTP request timeout in seconds
        max_workers: Maximum number of concurrent workers for HTTP requests
        chunk_size: Number of links to process in each batch
        browser_timeout: Browser page load timeout in seconds
        browser_headless: Whether to run browser in headless mode
        enable_browser_validation: Whether to enable browser validation
        
    Returns:
        Tuple of (link_results, browser_validation_report)
    """
    print("🔍 Step 1: Checking links with HTTP requests...")
    
    # First, check all links with HTTP requests
    results = check_all_links_with_archives_parallel(
        links, 
        archive_groups, 
        timeout=timeout, 
        max_workers=max_workers,
        chunk_size=chunk_size
    )
    
    # Categorize results
    categories = categorize_links(results)
    dead_links = categories['dead']
    
    print(f"✅ HTTP checking complete: {len(dead_links)} dead links found")
    
    browser_report = None
    
    if enable_browser_validation and dead_links:
        print(f"\n🔍 Step 2: Validating {len(dead_links)} dead links with browser...")
        print(f"⏱️  Browser timeout: {browser_timeout}s, Headless: {browser_headless}")
        
        # Validate dead links with browser
        browser_results = validate_dead_links_with_browser(
            dead_links,
            headless=browser_headless,
            timeout=browser_timeout
        )
        
        # Create browser validation report
        browser_report = create_browser_validation_report(dead_links, browser_results)
        print_browser_validation_summary(browser_report)
        
        # Update results based on browser validation
        results = update_results_with_browser_validation(results, dead_links, browser_results)
    
    return results, browser_report


def update_results_with_browser_validation(
    original_results: List[Tuple[str, str, Optional[int]]],
    dead_links: List[Tuple[str, str, Optional[int]]],
    browser_results: List[Tuple[str, str, Optional[int], Dict]]
) -> List[Tuple[str, str, Optional[int]]]:
    """
    Update original results based on browser validation.
    
    Args:
        original_results: Original HTTP check results
        dead_links: List of dead links that were browser validated
        browser_results: Browser validation results
        
    Returns:
        Updated results list
    """
    # Create a mapping of dead links to their browser results
    dead_urls = set()
    browser_map = {}
    
    for i, item in enumerate(dead_links):
        # Extract URL from different tuple formats
        if len(item) == 2:
            url, status_code = item
        elif len(item) == 3:
            url, status, status_code = item
        else:
            url = item[0]
        
        dead_urls.add(url)
        
        if i < len(browser_results):
            browser_map[url] = browser_results[i]
    
    # Update original results
    updated_results = []
    
    for url, status, code in original_results:
        if url in browser_map:
            browser_url, browser_status, browser_code, browser_info = browser_map[url]
            
            # If browser says it's alive, update the status
            if browser_status == 'alive':
                updated_results.append((url, 'alive', 200))
            else:
                # Keep original result but add browser info as comment
                updated_results.append((url, status, code))
        else:
            updated_results.append((url, status, code))
    
    return updated_results


def print_enhanced_summary(results: List[Tuple[str, str, Optional[int]]], 
                          browser_report: Dict = None):
    """
    Print an enhanced summary including browser validation results.
    
    Args:
        results: Link checking results
        browser_report: Browser validation report
    """
    print_link_summary(results)
    
    if browser_report:
        print(f"\n🔍 Browser Validation Impact:")
        print(f"   False positives detected: {browser_report['false_positives']}")
        print(f"   Confirmed dead: {browser_report['confirmed_dead']}")
        print(f"   Blocked by bot protection: {browser_report['blocked']}")
        
        if browser_report['false_positives'] > 0:
            accuracy_improvement = (browser_report['false_positives'] / browser_report['total_checked']) * 100
            print(f"   Accuracy improvement: {accuracy_improvement:.1f}%")


def validate_dead_links_safely(dead_links: List[Tuple[str, str, Optional[int]]], 
                              browser_timeout: int = 30,
                              browser_headless: bool = True,
                              max_links: int = 50) -> List[Tuple[str, str, Optional[int]]]:
    """
    Safely validate dead links using browser automation with limits.
    
    Args:
        dead_links: List of dead links to validate
        browser_timeout: Browser page load timeout in seconds
        browser_headless: Whether to run browser in headless mode
        max_links: Maximum number of links to validate (for safety)
        
    Returns:
        Updated results list
    """
    if not dead_links:
        return []
    
    # Limit the number of links to validate for safety
    if len(dead_links) > max_links:
        print(f"⚠️  Limiting browser validation to {max_links} links for safety")
        dead_links = dead_links[:max_links]
    
    print(f"🔍 Browser validating {len(dead_links)} dead links...")
    
    browser_results = validate_dead_links_with_browser(
        dead_links,
        headless=browser_headless,
        timeout=browser_timeout
    )
    
    # Update results based on browser validation
    updated_results = []
    
    for i, (url, status, code) in enumerate(dead_links):
        if i < len(browser_results):
            browser_url, browser_status, browser_code, browser_info = browser_results[i]
            
            # If browser says it's alive, update the status
            if browser_status == 'alive':
                updated_results.append((url, 'alive', 200))
            else:
                # Keep original result
                updated_results.append((url, status, code))
        else:
            updated_results.append((url, status, code))
    
    return updated_results


if __name__ == "__main__":
    # Test the enhanced link checking
    test_links = [
        "https://httpstat.us/200",
        "https://httpstat.us/404",
        "https://httpstat.us/403",
        "https://google.com",
        "https://nonexistentdomain12345.com"
    ]
    
    print("Testing enhanced link checking with browser validation...")
    
    results, browser_report = check_links_with_browser_validation(
        test_links,
        {},
        timeout=5.0,
        max_workers=5,
        browser_timeout=10,
        browser_headless=True,
        enable_browser_validation=True
    )
    
    print_enhanced_summary(results, browser_report) 