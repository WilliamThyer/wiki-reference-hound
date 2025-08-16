#!/usr/bin/env python3
"""
Wikipedia Dead Link Checker

Checks for dead external links in top Wikipedia articles.
"""

import argparse
import time
from typing import Dict, List, Tuple, Optional

from fetch_top_articles import get_top_articles, get_all_time_top_articles
from fetch_article_html import get_article_html
from extract_references import extract_external_links, extract_external_links_from_references, filter_links_for_checking, get_references_with_archives
from check_links import check_all_links_with_archives, check_all_links_with_archives_parallel, print_link_summary
from generate_report import create_all_references_csv_report, print_report_summary
from utils import clean_article_title, format_duration


def main():
    """Main function to orchestrate the dead link checking process."""
    
    parser = argparse.ArgumentParser(description='Check for dead links in top Wikipedia articles')
    parser.add_argument('--limit', type=int, default=25, 
                       help='Number of articles to check (default: 25)')
    parser.add_argument('--all-time', action='store_true',
                       help='Fetch top articles of all time instead of yesterday\'s top articles')
    parser.add_argument('--timeout', type=float, default=5.0,
                       help='Request timeout in seconds (default: 5.0)')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='Delay between link checks in seconds (default: 0.1)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for reports (default: output)')
    parser.add_argument('--parallel', action='store_true',
                       help='Enable parallel processing for faster link checking')
    parser.add_argument('--max-workers', type=int, default=20,
                       help='Maximum number of concurrent workers for parallel processing (default: 20)')
    parser.add_argument('--chunk-size', type=int, default=100,
                       help='Number of links to process in each batch for parallel processing (default: 100)')
    # Browser validation arguments
    parser.add_argument('--browser-validation', action='store_true',
                       help='Enable browser validation for false positive detection')
    parser.add_argument('--browser-timeout', type=int, default=30,
                       help='Browser page load timeout in seconds (default: 30)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser in visible mode (default: headless)')
    parser.add_argument('--max-browser-links', type=int, default=50,
                       help='Maximum number of dead links to validate with browser (default: 50)')
    parser.add_argument('--references-only', action='store_true',
                       help='Only extract external links from the references section (more focused)')
    parser.add_argument('--use-html-structure', action='store_true',
                       help='Use HTML structure analysis to associate archives with their originals (more accurate)')
    
    args = parser.parse_args()
    
    print("🔍 Wikipedia Dead Link Checker")
    print("=" * 40)
    if args.all_time:
        print(f"📊 Checking top {args.limit} articles of all time")
    else:
        print(f"📊 Checking top {args.limit} articles from yesterday")
    print(f"⏱️  Timeout: {args.timeout}s, Delay: {args.delay}s")
    if args.parallel:
        print(f"🚀 Parallel processing enabled: {args.max_workers} workers, chunk size: {args.chunk_size}")
    if args.browser_validation:
        print(f"🔍 Browser validation enabled: {args.browser_timeout}s timeout, headless: {not args.no_headless}")
        print(f"   Max browser validation links: {args.max_browser_links}")
    if args.references_only:
        print(f"🎯 References-only mode enabled: Only extracting links from references section")
    if args.use_html_structure:
        print(f"🔗 HTML structure analysis enabled: Using HTML proximity to associate archives with originals")
    print()
    
    start_time = time.time()
    
    # Step 1: Fetch top articles
    print("📰 Fetching top articles...")
    if args.all_time:
        articles = get_all_time_top_articles(limit=args.limit)
    else:
        articles = get_top_articles(limit=args.limit)
    
    if not articles:
        print("❌ Failed to fetch articles. Exiting.")
        return
    
    print(f"✅ Found {len(articles)} articles to check")
    print()
    
    # Step 2: Process each article
    dead_links = {}
    all_links = {}  # Store all links found for each article
    archive_groups_all = {}  # Store archive groups for all articles
    all_link_results = {}  # Store complete link checking results for all articles
    total_links_checked = 0
    total_dead_links = 0
    total_archived_links = 0  # Track total archived links
    all_browser_validation_results = {}  # Store browser validation results for all articles
    
    # Process each article and build in-memory data to create the all-references table
    for i, title in enumerate(articles, 1):
        clean_title = clean_article_title(title)
        print(f"🔍 Processing ({i}/{len(articles)}): {clean_title}")
            
        # Fetch article HTML
        html = get_article_html(title)
        if not html:
            print(f"   ⚠️  Could not fetch content for '{clean_title}'")
            continue
            
        # Extract external links
        if args.use_html_structure:
            # Use the new HTML structure-based approach
            references_with_archives = get_references_with_archives(html)
            
            # Convert to the format expected by the rest of the system
            article_links = []
            archive_groups = {}
            
            for ref in references_with_archives:
                if ref['original_url']:
                    article_links.append(ref['original_url'])
                    if ref['archive_url']:
                        if ref['original_url'] not in archive_groups:
                            archive_groups[ref['original_url']] = []
                        archive_groups[ref['original_url']].append(ref['archive_url'])
            
            print(f"   🔗 Using HTML structure analysis method")
        elif args.references_only:
            article_links = extract_external_links_from_references(html)
            print(f"   🎯 Using references-only extraction method")
            
            # Filter links for checking (remove archives, group with originals)
            links_to_check, archive_groups = filter_links_for_checking(article_links)
        else:
            article_links = extract_external_links(html)
            print(f"   🔍 Using comprehensive extraction method")
            
            # Filter links for checking (remove archives, group with originals)
            links_to_check, archive_groups = filter_links_for_checking(article_links)
            
        if not article_links:
            print(f"   ℹ️  No external links found in '{clean_title}'")
            continue
        
        # For HTML structure method, we already have the archive groups
        if not args.use_html_structure:
            # Filter links for checking (remove archives, group with originals)
            links_to_check, archive_groups = filter_links_for_checking(article_links)
        else:
            # For HTML structure method, links_to_check is all original links
            links_to_check = article_links
            
        # Store all links and archive groups for this article
        all_links[clean_title] = article_links
        archive_groups_all[clean_title] = archive_groups
            
        # Count links that actually have archives
        links_with_archives = sum(1 for archives in archive_groups.values() if archives)
            
        print(f"   📎 Found {len(article_links)} total links ({len(links_to_check)} to check, {links_with_archives} with archives)")
            
        total_links_checked += len(links_to_check)
            
        # Check link status
        if args.parallel:
            print(f"   🔗 Checking link status in parallel...")
            results = check_all_links_with_archives_parallel(links_to_check, archive_groups, timeout=args.timeout, max_workers=args.max_workers)
        else:
            print(f"   🔗 Checking link status...")
            results = check_all_links_with_archives(links_to_check, archive_groups, timeout=args.timeout, delay=args.delay)
            
        # Store complete link checking results for this article
        all_link_results[clean_title] = results
            
        # Browser validation if enabled
        if args.browser_validation:
            from browser_validation import validate_dead_links_with_browser, create_browser_validation_report, print_browser_validation_summary
            
            # Get dead links for browser validation
            dead_for_browser = [(url, status, code) for url, status, code in results if status == 'dead']
            
            if dead_for_browser:
                print(f"   🔍 Browser validating {len(dead_for_browser)} dead links...")
                browser_results = validate_dead_links_with_browser(
                    dead_for_browser,
                    headless=not args.no_headless,
                    timeout=args.browser_timeout
                )
                
                # Create browser validation report
                browser_report = create_browser_validation_report(dead_for_browser, browser_results)
                print_browser_validation_summary(browser_report)
                
                # Store browser report for later summary
                if hasattr(args, 'browser_reports'):
                    args.browser_reports.append(browser_report)
                else:
                    args.browser_reports = [browser_report]
                
                # Store browser validation results for this article
                article_browser_results = {}
                for browser_result in browser_results:
                    url, status, code, info = browser_result
                    article_browser_results[url] = browser_result
                all_browser_validation_results[clean_title] = article_browser_results
            else:
                all_browser_validation_results[clean_title] = {}
        else:
            all_browser_validation_results[clean_title] = {}
            
        # Filter dead links (only truly dead, not archived or blocked)
        dead = [(url, code) for url, status, code in results if status == 'dead']
        blocked = [(url, status, code) for url, status, code in results if status == 'blocked']
        archived = [(url, code) for url, status, code in results if status == 'archived']
        
        if dead:
            dead_links[clean_title] = dead
            total_dead_links += len(dead)
            print(f"   ❌ Found {len(dead)} dead links")
        else:
            print(f"   ✅ All links are alive, archived, or blocked")
        
        if blocked:
            print(f"   🚫 Found {len(blocked)} blocked links (likely bot protection)")
        
        if archived:
            print(f"   📦 Found {len(archived)} archived links (skipped during checking)")
            total_archived_links += len(archived)
        
        print()
    
    # Step 3: Generate comprehensive reports
    print("📋 Generating all-references report (primary artifact)...")
    
    # Generate the new comprehensive CSV with ALL reference links
    all_references_csv_filepath = create_all_references_csv_report(
        all_links, 
        archive_groups_all, 
        all_link_results,  # Pass complete link results instead of just dead_links
        all_browser_validation_results, 
        args.output_dir
    )
    
    print(f"📄 All References CSV report saved to: {all_references_csv_filepath}")
    
    # Step 4: Print final summary
    end_time = time.time()
    duration = end_time - start_time
    
    print()
    print("🎯 Final Summary")
    print("=" * 20)
    print(f"📰 Articles processed: {len(articles)}")
    print(f"🔗 Total links checked: {total_links_checked}")
    print(f"❌ Total dead links: {total_dead_links}")
    
    if total_archived_links > 0:
        print(f"📦 Total archive URLs found: {total_archived_links}")
    
    print(f"⏱️  Total time: {format_duration(duration)}")
    
    # Optional: show quick dead-link summary in console for awareness
    if dead_links:
        print_report_summary(dead_links)
    
    # Print browser validation summary if used
    if args.browser_validation and hasattr(args, 'browser_reports') and args.browser_reports:
        print("\n🔍 Browser Validation Summary")
        print("=" * 40)
        
        total_false_positives = 0
        total_confirmed_dead = 0
        total_blocked = 0
        total_timeout = 0
        total_error = 0
        
        for i, report in enumerate(args.browser_reports):
            if report:  # Only process non-None reports
                total_false_positives += report.get('false_positives', 0)
                total_confirmed_dead += report.get('confirmed_dead', 0)
                total_blocked += report.get('blocked', 0)
                total_timeout += report.get('timeout', 0)
                total_error += report.get('error', 0)
        
        print(f"Total false positives detected: {total_false_positives}")
        print(f"Total confirmed dead: {total_confirmed_dead}")
        print(f"Total blocked by bot protection: {total_blocked}")
        print(f"Total timeout errors: {total_timeout}")
        print(f"Total other errors: {total_error}")
        
        if total_false_positives > 0:
            print(f"🎉 Browser validation helped detect {total_false_positives} false positives!")
            print(f"💡 Detailed results are captured in the all-references CSV report")
        
        # We no longer generate extra artifacts; all information is in the all-references CSV
    
    print("\n✅ Done!")


def test_individual_components():
    """Test individual components for debugging."""
    print("🧪 Testing individual components...")
    
    # Test fetching top articles
    print("\n1. Testing fetch_top_articles (daily)...")
    daily_articles = get_top_articles(limit=3)
    print(f"   Found {len(daily_articles)} daily articles: {daily_articles}")
    
    print("\n2. Testing fetch_top_articles (all-time)...")
    all_time_articles = get_all_time_top_articles(limit=3)
    print(f"   Found {len(all_time_articles)} all-time articles: {all_time_articles}")
    
    # Use the first available articles for further testing
    articles = daily_articles if daily_articles else all_time_articles
    
    if articles:
        # Test fetching article HTML
        print("\n2. Testing fetch_article_html...")
        test_title = articles[0]
        html = get_article_html(test_title)
        print(f"   HTML length for '{test_title}': {len(html)} characters")
        
        if html:
            # Test extracting links
            print("\n3. Testing extract_references...")
            print("   Testing comprehensive method:")
            links = extract_external_links(html)
            print(f"   Found {len(links)} external links")
            for i, link in enumerate(links[:3], 1):
                print(f"   {i}. {link}")
            
            print("   Testing references-only method:")
            ref_links = extract_external_links_from_references(html)
            print(f"   Found {len(ref_links)} external links from references only")
            for i, link in enumerate(ref_links[:3], 1):
                print(f"   {i}. {link}")
            
            if links:
                # Test checking links
                print("\n4. Testing check_links...")
                results = check_all_links_with_archives(links[:2], {}, timeout=3.0, delay=0.5)
                print_link_summary(results)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_individual_components()
    else:
        main() 