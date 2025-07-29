#!/usr/bin/env python3
"""
Test script for improved link checking on known false positives.
"""

import sys
import time
from check_links import (
    check_link_status, 
    check_link_with_retry, 
    validate_link_with_secondary_check,
    is_likely_false_positive,
    check_dns_resolution,
    check_with_alternative_methods,
    validate_redirect_chain
)

def test_specific_urls():
    """Test the improved link checking on URLs that were incorrectly marked as broken."""
    
    # URLs that were incorrectly marked as broken in the CSV
    test_urls = [
        "https://www.blackfilm.com/read/exclusive-malcolm-jamal-warner-talks-tnt-major-crimes/",
        "http://data.bibliotheken.nl/id/thes/p073262897",
        "https://www.essence.com/news_entertainment/entertainment/articles/flashback_fridays_malcolm_jamal_warner/",
        "http://tvline.com/2015/05/13/american-crime-story-malcolm-jamal-warner-al-cowlings/",
        "https://id.worldcat.org/fast/228316",
        "http://www.people.com/people/archive/article/0,,20127316,00.html",
        "http://www.talentedteens.com/our_proud_history.htm"
    ]
    
    print("🔍 Testing Improved Link Checking")
    print("=" * 50)
    print()
    
    for i, url in enumerate(test_urls, 1):
        print(f"Testing URL {i}/{len(test_urls)}: {url}")
        print("-" * 60)
        
        # Test 1: DNS Resolution
        print(f"1. DNS Resolution: ", end="")
        if check_dns_resolution(url):
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
        
        # Test 2: Basic link check
        print(f"2. Basic Link Check: ", end="")
        start_time = time.time()
        result = check_link_status(url, timeout=10.0)
        end_time = time.time()
        print(f"{result[1].upper()} (Status: {result[2]}) - {end_time - start_time:.2f}s")
        
        # Test 3: Check if likely false positive
        print(f"3. False Positive Check: ", end="")
        if is_likely_false_positive(url, result[1], result[2]):
            print("⚠️  LIKELY FALSE POSITIVE")
        else:
            print("✅ LIKELY REAL ISSUE")
        
        # Test 4: Alternative methods
        print(f"4. Alternative Methods: ", end="")
        alt_result = check_with_alternative_methods(url, timeout=10.0)
        print(f"{alt_result[1].upper()} (Status: {alt_result[2]})")
        
        # Test 5: Redirect validation
        print(f"5. Redirect Validation: ", end="")
        redirect_result = validate_redirect_chain(url, timeout=10.0)
        print(f"{redirect_result[1].upper()} (Status: {redirect_result[2]})")
        
        # Test 6: Retry with secondary validation
        print(f"6. Retry with Secondary Validation: ", end="")
        retry_result = check_link_with_retry(url, timeout=10.0, max_retries=2)
        print(f"{retry_result[1].upper()} (Status: {retry_result[2]})")
        
        # Test 7: Secondary validation check
        print(f"7. Secondary Validation: ", end="")
        secondary_result = validate_link_with_secondary_check(url, result, timeout=10.0)
        print(f"{secondary_result[1].upper()} (Status: {secondary_result[2]})")
        
        print()
        
        # Summary
        final_status = secondary_result[1]
        if final_status == 'alive':
            print(f"🎉 FINAL RESULT: {url} is ALIVE")
        elif final_status == 'blocked':
            print(f"🚫 FINAL RESULT: {url} is BLOCKED (bot protection)")
        elif final_status == 'archived':
            print(f"📦 FINAL RESULT: {url} is ARCHIVED")
        else:
            print(f"❌ FINAL RESULT: {url} is DEAD")
        
        print("\n" + "=" * 60 + "\n")


def test_curl_comparison():
    """Compare our results with curl to verify accuracy."""
    
    test_urls = [
        "https://www.blackfilm.com/read/exclusive-malcolm-jamal-warner-talks-tnt-major-crimes/",
        "http://data.bibliotheken.nl/id/thes/p073262897",
        "http://www.people.com/people/archive/article/0,,20127316,00.html"
    ]
    
    print("🔍 Comparing with curl results")
    print("=" * 40)
    print()
    
    for url in test_urls:
        print(f"URL: {url}")
        
        # Our improved check
        result = check_link_with_retry(url, timeout=10.0, max_retries=2)
        secondary_result = validate_link_with_secondary_check(url, result, timeout=10.0)
        
        print(f"Our result: {secondary_result[1].upper()} (Status: {secondary_result[2]})")
        
        # Manual curl check
        import subprocess
        try:
            curl_result = subprocess.run(
                ['curl', '-I', '--max-time', '10', url],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if curl_result.returncode == 0:
                # Extract status code from curl output
                lines = curl_result.stdout.split('\n')
                for line in lines:
                    if line.startswith('HTTP/'):
                        status_code = line.split()[1]
                        print(f"Curl result: HTTP {status_code}")
                        break
                else:
                    print("Curl result: Success (no status code found)")
            else:
                print(f"Curl result: Failed (return code: {curl_result.returncode})")
                
        except Exception as e:
            print(f"Curl result: Error - {e}")
        
        print("-" * 40)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--curl":
        test_curl_comparison()
    else:
        test_specific_urls() 