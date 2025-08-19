#!/usr/bin/env python3
"""
Browser-based validation for detecting false positives in dead link detection.
"""

import time
import logging
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse

# Configure logging - will be updated based on verbose flag
logging.basicConfig(level=logging.WARNING)  # Default to WARNING to suppress INFO messages
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, WebDriverException, NoSuchElementException, SessionNotCreatedException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium")


def set_logging_level(verbose: bool = False):
    """Set the logging level based on verbose flag."""
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)


class BrowserValidator:
    """Browser-based validator for detecting false positives in dead link detection."""
    
    def __init__(self, headless: bool = True, timeout: int = 30, verbose: bool = False):
        """Initialize the browser validator."""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is required for browser validation. Install with: pip install selenium")
        
        self.headless = headless
        self.timeout = timeout
        self.verbose = verbose
        self.driver = None
        
        # Set logging level based on verbose flag
        set_logging_level(verbose)
        
    def _create_driver(self) -> 'webdriver.Chrome':
        """Create and configure Chrome WebDriver."""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Performance optimizations
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-images')
        options.add_argument('--disable-css')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Add experimental options for better stability
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(5)
            
            # Set ChromeDriver HTTP connection timeout to match page load timeout
            driver.command_executor._conn.timeout = self.timeout
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except SessionNotCreatedException as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            if self.verbose:
                logger.info("Make sure Chrome/Chromium is installed and chromedriver is in PATH")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Chrome driver: {e}")
            raise
    
    def validate_url_with_browser(self, url: str) -> Tuple[str, str, Optional[int], Dict]:
        """Validate a URL using browser automation."""
        if not self.driver:
            try:
                self.driver = self._create_driver()
            except Exception as e:
                logger.error(f"Failed to create browser driver: {e}")
                return url, 'error', None, {'error': str(e)}
        
        additional_info = {}
        
        try:
            if self.verbose:
                logger.info(f"Browser validating: {url}")
            
            # Navigate to the URL
            self.driver.get(url)
            
            # Wait for page to load
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                if self.verbose:
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
            
            # Check for error indicators in page content
            page_source = self.driver.page_source.lower()
            
            # Check for specific access denied pattern that indicates blocking
            if 'error: access denied' in page_source and 'title: access denied' in page_source:
                additional_info['blocking_indicator'] = 'access denied'
                return url, 'blocked', None, additional_info
            
            # Clear error indicators
            clear_error_indicators = [
                '404 not found', 'page not found', 'error 404',
                '500 internal server error', 'internal server error',
                '403 forbidden',
                '410 gone', 'resource no longer available',
                'this page cannot be displayed',
                'the requested url was not found',
                'the page you are looking for could not be found',
                'server not found', 'dns_probe_finished_nxdomain'
            ]
            
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
                'checking your browser',
                'access denied'
            ]
            
            for indicator in blocking_indicators:
                if indicator in page_source:
                    additional_info['blocking_indicator'] = indicator
                    return url, 'blocked', None, additional_info
            
            # If we have a meaningful title and the page loaded, consider it alive
            if additional_info.get('title') and len(additional_info['title'].strip()) > 0:
                title_lower = additional_info['title'].lower()
                title_error_indicators = ['404 not found', 'error 404', 'page not found', 'forbidden', 'server error']
                if not any(indicator in title_lower for indicator in title_error_indicators):
                    return url, 'alive', 200, additional_info
            
            # If we get here, the page loaded but we're unsure - be conservative and assume it's alive
            return url, 'alive', 200, additional_info
            
        except TimeoutException:
            if self.verbose:
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
    
    def validate_multiple_urls(self, urls: List[str]) -> List[Tuple[str, str, Optional[int], Dict]]:
        """Validate multiple URLs using browser automation."""
        results = []
        
        for url in urls:
            result = self.validate_url_with_browser(url)
            results.append(result)
            time.sleep(1)  # Small delay between requests
        
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
                                   timeout: int = 30,
                                   verbose: bool = False) -> List[Tuple[str, str, Optional[int], Dict]]:
    """Validate a list of dead links using browser automation."""
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not available. Cannot perform browser validation.")
        return [(url, status, code, {'error': 'Selenium not available'}) for url, status, code in dead_links]
    
    # Handle different tuple formats
    urls = []
    for item in dead_links:
        if len(item) == 2:
            url, status_code = item
            urls.append(url)
        elif len(item) == 3:
            url, status, status_code = item
            urls.append(url)
        else:
            urls.append(item[0])
    
    with BrowserValidator(headless=headless, timeout=timeout, verbose=verbose) as validator:
        return validator.validate_multiple_urls(urls)


def create_browser_validation_report(dead_links: List[Tuple[str, str, Optional[int]]],
                                   browser_results: List[Tuple[str, str, Optional[int], Dict]]) -> Dict:
    """Create a report of browser validation results."""
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


def print_browser_validation_summary(report: Dict, verbose: bool = False):
    """Print a summary of browser validation results."""
    if not verbose:
        return
        
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