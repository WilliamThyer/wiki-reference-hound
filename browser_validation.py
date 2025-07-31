#!/usr/bin/env python3
"""
Browser-based validation for detecting false positives in dead link detection.

This module uses Selenium WebDriver to perform secondary validation of links
that appear to be dead using HTTP requests. Browser automation can help detect
false positives by:

1. Rendering JavaScript content
2. Handling complex redirects
3. Bypassing bot detection
4. Checking actual page content
"""

import time
import logging
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        WebDriverException, 
        NoSuchElementException,
        SessionNotCreatedException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium")


class BrowserValidator:
    """
    Browser-based validator for detecting false positives in dead link detection.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30, 
                 user_agent: str = None, enable_images: bool = False):
        """
        Initialize the browser validator.
        
        Args:
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in seconds
            user_agent: Custom user agent string
            enable_images: Whether to load images (faster if disabled)
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is required for browser validation. Install with: pip install selenium")
        
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.enable_images = enable_images
        self.driver = None
        
    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver."""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Performance optimizations
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        if not self.enable_images:
            options.add_argument('--disable-images')
        options.add_argument('--disable-css')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Additional stability options
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=NetworkService')
        
        # Set user agent
        options.add_argument(f'--user-agent={self.user_agent}')
        
        # Memory optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Add experimental options for better stability
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(5)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except SessionNotCreatedException as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            logger.info("Make sure Chrome/Chromium is installed and chromedriver is in PATH")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Chrome driver: {e}")
            raise
    
    def validate_url_with_browser(self, url: str) -> Tuple[str, str, Optional[int], Dict]:
        """
        Validate a URL using browser automation.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (url, status, status_code, additional_info)
            status can be: 'alive', 'dead', 'blocked', 'timeout', 'error'
        """
        if not self.driver:
            try:
                self.driver = self._create_driver()
            except Exception as e:
                logger.error(f"Failed to create browser driver: {e}")
                return url, 'error', None, {'error': str(e)}
        
        additional_info = {}
        
        try:
            logger.info(f"Browser validating: {url}")
            
            # Navigate to the URL
            self.driver.get(url)
            
            # Wait for page to load with shorter timeout
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                # If page doesn't load completely, still check what we have
                logger.warning(f"Page load timeout for {url}, checking current state")
            
            # Get current URL (after redirects)
            current_url = self.driver.current_url
            additional_info['final_url'] = current_url
            
            # Check if we were redirected
            if current_url != url:
                additional_info['redirected'] = True
                additional_info['original_url'] = url
            
            # Get page title
            try:
                title = self.driver.title
                additional_info['title'] = title
            except:
                additional_info['title'] = None
            
            # Check for common error indicators in page content
            page_source = self.driver.page_source.lower()
            
            # Only look for very specific error indicators that clearly indicate dead pages
            clear_error_indicators = [
                '404 not found', 'page not found', 'error 404',
                '500 internal server error', 'internal server error',
                '403 forbidden', 'access denied',
                '410 gone', 'resource no longer available',
                'this page cannot be displayed',
                'the requested url was not found',
                'the page you are looking for could not be found',
                'server not found', 'dns_probe_finished_nxdomain'
            ]
            
            # Check for very specific error indicators
            for indicator in clear_error_indicators:
                if indicator in page_source:
                    additional_info['error_indicator'] = indicator
                    return url, 'dead', None, additional_info
            
            # Check for bot blocking indicators
            blocking_indicators = [
                'captcha', 'challenge', 'security check',
                'bot detected', 'automated access',
                'cloudflare', 'ddos protection',
                'please verify you are human',
                'checking your browser'
            ]
            
            for indicator in blocking_indicators:
                if indicator in page_source:
                    additional_info['blocking_indicator'] = indicator
                    return url, 'blocked', None, additional_info
            
            # Check if page has meaningful content
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                additional_info['content_length'] = len(body_text.strip())
            except:
                additional_info['content_length'] = 0
            
            # If we have a meaningful title and the page loaded, consider it alive
            # This is the most conservative approach - if the page loads and has a title, it's probably alive
            if additional_info.get('title') and len(additional_info['title'].strip()) > 0:
                # Only mark as dead if the title contains very clear error indicators
                title_lower = additional_info['title'].lower()
                title_error_indicators = ['404 not found', 'error 404', 'page not found', 'forbidden', 'server error']
                if not any(indicator in title_lower for indicator in title_error_indicators):
                    return url, 'alive', 200, additional_info
            
            # If we get here, the page loaded but we're unsure - be conservative and assume it's alive
            return url, 'alive', 200, additional_info
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url}")
            return url, 'timeout', None, {'error': 'Page load timeout'}
            
        except WebDriverException as e:
            error_msg = str(e)
            logger.error(f"WebDriver error for {url}: {error_msg}")
            
            # Check for specific error types
            if any(err in error_msg.lower() for err in [
                'err_connection_closed', 'err_name_not_resolved', 'err_connection_refused',
                'err_connection_timed_out', 'err_connection_reset', 'err_network_changed',
                'err_internet_disconnected', 'err_network_access_denied'
            ]):
                return url, 'dead', None, {'error': error_msg}
            else:
                return url, 'error', None, {'error': error_msg}
            
        except Exception as e:
            logger.error(f"Unexpected error validating {url}: {e}")
            return url, 'error', None, {'error': str(e)}
    
    def validate_multiple_urls(self, urls: List[str], 
                              progress_callback=None) -> List[Tuple[str, str, Optional[int], Dict]]:
        """
        Validate multiple URLs using browser automation.
        
        Args:
            urls: List of URLs to validate
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of validation results
        """
        results = []
        
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(i + 1, len(urls))
            
            result = self.validate_url_with_browser(url)
            results.append(result)
            
            # Small delay between requests
            time.sleep(1)
        
        return results
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def validate_dead_links_with_browser(dead_links: List[Tuple[str, str, Optional[int]]], 
                                   headless: bool = True,
                                   timeout: int = 30) -> List[Tuple[str, str, Optional[int], Dict]]:
    """
    Validate a list of dead links using browser automation.
    
    Args:
        dead_links: List of (url, status, status_code) tuples that were marked as dead
        headless: Whether to run browser in headless mode
        timeout: Page load timeout in seconds
        
    Returns:
        List of validation results with additional browser info
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not available. Cannot perform browser validation.")
        return [(url, status, code, {'error': 'Selenium not available'}) for url, status, code in dead_links]
    
    # Handle different tuple formats
    urls = []
    for item in dead_links:
        if len(item) == 2:
            # Format: (url, status_code)
            url, status_code = item
            urls.append(url)
        elif len(item) == 3:
            # Format: (url, status, status_code)
            url, status, status_code = item
            urls.append(url)
        else:
            # Fallback: assume first element is URL
            urls.append(item[0])
    
    with BrowserValidator(headless=headless, timeout=timeout) as validator:
        return validator.validate_multiple_urls(urls)


def is_likely_false_positive_browser(url: str, initial_status: str, 
                                   browser_result: Tuple[str, str, Optional[int], Dict]) -> bool:
    """
    Determine if a link is likely a false positive based on browser validation.
    
    Args:
        url: The URL that was checked
        initial_status: The initial status from HTTP requests
        browser_result: The browser validation result
        
    Returns:
        True if this appears to be a false positive
    """
    browser_url, browser_status, browser_code, browser_info = browser_result
    
    # If browser says it's alive but HTTP said it was dead, it's likely a false positive
    if browser_status == 'alive' and initial_status == 'dead':
        return True
    
    # If browser was redirected to a different URL, it might be a false positive
    if browser_info.get('redirected') and browser_status == 'alive':
        return True
    
    # If browser found blocking indicators, it's not a false positive
    if browser_status == 'blocked':
        return False
    
    # If browser timed out or had errors, we can't determine
    if browser_status in ['timeout', 'error']:
        return False
    
    return False


def create_browser_validation_report(dead_links: List[Tuple[str, str, Optional[int]]],
                                   browser_results: List[Tuple[str, str, Optional[int], Dict]]) -> Dict:
    """
    Create a report of browser validation results.
    
    Args:
        dead_links: Original dead link results
        browser_results: Browser validation results
        
    Returns:
        Dictionary with validation summary
    """
    report = {
        'total_checked': len(dead_links),
        'confirmed_dead': 0,
        'false_positives': 0,
        'blocked': 0,
        'timeout': 0,
        'error': 0,
        'false_positive_urls': [],
        'confirmed_dead_urls': [],
        'blocked_urls': []
    }
    
    for i, item in enumerate(dead_links):
        if i < len(browser_results):
            browser_result = browser_results[i]
            browser_url, browser_status, browser_code, browser_info = browser_result
            
            # Extract URL and initial info
            if len(item) == 2:
                url, initial_code = item
                initial_status = 'dead'
            elif len(item) == 3:
                url, initial_status, initial_code = item
            else:
                url = item[0]
                initial_status = 'dead'
                initial_code = None
            
            if browser_status == 'alive':
                report['false_positives'] += 1
                report['false_positive_urls'].append({
                    'url': url,
                    'initial_status': initial_status,
                    'initial_code': initial_code,
                    'browser_info': browser_info
                })
            elif browser_status == 'blocked':
                report['blocked'] += 1
                report['blocked_urls'].append({
                    'url': url,
                    'browser_info': browser_info
                })
            elif browser_status == 'timeout':
                report['timeout'] += 1
            elif browser_status == 'error':
                report['error'] += 1
            else:
                report['confirmed_dead'] += 1
                report['confirmed_dead_urls'].append({
                    'url': url,
                    'browser_info': browser_info
                })
    
    return report


def print_browser_validation_summary(report: Dict):
    """
    Print a summary of browser validation results.
    
    Args:
        report: Browser validation report
    """
    print(f"\n🔍 Browser Validation Summary")
    print(f"=" * 40)
    print(f"Total links checked: {report['total_checked']}")
    print(f"✅ Confirmed alive (false positives): {report['false_positives']}")
    print(f"❌ Confirmed dead: {report['confirmed_dead']}")
    print(f"🚫 Blocked (bot protection): {report['blocked']}")
    print(f"⏱️  Timeout: {report['timeout']}")
    print(f"🔌 Error: {report['error']}")
    
    if report['false_positives'] > 0:
        print(f"\n🎉 False Positives Found:")
        for item in report['false_positive_urls']:
            print(f"   - {item['url']}")
            if item['browser_info'].get('final_url'):
                print(f"     → Redirected to: {item['browser_info']['final_url']}")
            if item['browser_info'].get('title'):
                print(f"     → Title: {item['browser_info']['title']}")
    
    if report['blocked'] > 0:
        print(f"\n🚫 Blocked Links:")
        for item in report['blocked_urls']:
            print(f"   - {item['url']}")
            if item['browser_info'].get('blocking_indicator'):
                print(f"     → Blocked by: {item['browser_info']['blocking_indicator']}")


if __name__ == "__main__":
    # Test the browser validator
    test_urls = [
        "https://httpstat.us/404",
        "https://httpstat.us/200", 
        "https://google.com",
        "https://nonexistentdomain12345.com"
    ]
    
    print("Testing browser validation...")
    
    if SELENIUM_AVAILABLE:
        with BrowserValidator(headless=True, timeout=10) as validator:
            for url in test_urls:
                result = validator.validate_url_with_browser(url)
                print(f"{url}: {result[1]} (Code: {result[2]})")
    else:
        print("Selenium not available. Install with: pip install selenium") 