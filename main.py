#!/usr/bin/env python3
"""
Wikipedia Dead Link Checker

This script fetches the top 25 most-viewed English Wikipedia articles from yesterday,
extracts external links from their references, checks if the links are alive,
and generates a CSV report of dead links.

Usage:
    python main.py [--limit N] [--timeout SECONDS] [--delay SECONDS]
"""

import argparse
import time
from typing import Dict, List, Tuple, Optional

from fetch_top_articles import get_top_articles
from fetch_article_html import get_article_html
from extract_references import extract_external_links, filter_links_for_checking
from check_links import check_all_links_with_archives, check_all_links_with_archives_parallel, print_link_summary
from generate_report import write_report, write_summary_report, print_report_summary, create_incremental_csv_writer, write_article_results_to_csv
from utils import clean_article_title, normalize_url, format_duration


def main():
    """Main function to orchestrate the dead link checking process."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check for dead links in top Wikipedia articles')
    parser.add_argument('--limit', type=int, default=25, 
                       help='Number of articles to check (default: 25)')
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
    
    args = parser.parse_args()
    
    print("🔍 Wikipedia Dead Link Checker")
    print("=" * 40)
    print(f"📊 Checking top {args.limit} articles from yesterday")
    print(f"⏱️  Timeout: {args.timeout}s, Delay: {args.delay}s")
    if args.parallel:
        print(f"🚀 Parallel processing enabled: {args.max_workers} workers, chunk size: {args.chunk_size}")
    if args.browser_validation:
        print(f"🔍 Browser validation enabled: {args.browser_timeout}s timeout, headless: {not args.no_headless}")
        print(f"   Max browser validation links: {args.max_browser_links}")
    print()
    
    start_time = time.time()
    
    # Step 1: Fetch top articles
    print("📰 Fetching top articles...")
    articles = get_top_articles(limit=args.limit)
    
    if not articles:
        print("❌ Failed to fetch articles. Exiting.")
        return
    
    print(f"✅ Found {len(articles)} articles to check")
    print()
    
    # Step 2: Process each article
    dead_links = {}
    total_links_checked = 0
    total_dead_links = 0
    
    # Create CSV file for incremental writing
    csv_filepath, csv_writer, csv_file = create_incremental_csv_writer(args.output_dir)
    print(f"📄 CSV file created: {csv_filepath}")
    print()
    
    try:
        for i, title in enumerate(articles, 1):
            clean_title = clean_article_title(title)
            print(f"🔍 Processing ({i}/{len(articles)}): {clean_title}")
            
            # Fetch article HTML
            html = get_article_html(title)
            if not html:
                print(f"   ⚠️  Could not fetch content for '{clean_title}'")
                continue
            
            # Extract external links
            all_links = extract_external_links(html)
            if not all_links:
                print(f"   ℹ️  No external links found in '{clean_title}'")
                continue
            
            # Filter links for checking (remove archives, group with originals)
            links_to_check, archive_groups = filter_links_for_checking(all_links)
            
            # Count links that actually have archives
            links_with_archives = sum(1 for archives in archive_groups.values() if archives)
            
            print(f"   📎 Found {len(all_links)} total links ({len(links_to_check)} to check, {links_with_archives} with archives)")
            total_links_checked += len(links_to_check)
            
            # Check if links are alive
            if args.browser_validation:
                # Use enhanced link checking with browser validation
                from enhanced_check_links import check_links_with_browser_validation
                
                print(f"   🔗 Checking link status with browser validation...")
                results, browser_report = check_links_with_browser_validation(
                    links_to_check, 
                    archive_groups, 
                    timeout=args.timeout, 
                    max_workers=args.max_workers,
                    chunk_size=args.chunk_size,
                    browser_timeout=args.browser_timeout,
                    browser_headless=not args.no_headless,
                    enable_browser_validation=True
                )
                
                # Store browser report for later summary
                if hasattr(args, 'browser_reports'):
                    args.browser_reports.append(browser_report)
                else:
                    args.browser_reports = [browser_report]
            else:
                # Use standard link checking
                if args.parallel:
                    print(f"   🔗 Checking link status (parallel, {args.max_workers} workers)...")
                    results = check_all_links_with_archives_parallel(
                        links_to_check, 
                        archive_groups, 
                        timeout=args.timeout, 
                        max_workers=args.max_workers,
                        chunk_size=args.chunk_size
                    )
                else:
                    print(f"   🔗 Checking link status...")
                    results = check_all_links_with_archives(links_to_check, archive_groups, timeout=args.timeout, delay=args.delay)
            
            # Filter dead links (only truly dead, not archived or blocked)
            dead = [(url, code) for url, status, code in results if status == 'dead']
            blocked = [(url, status, code) for url, status, code in results if status == 'blocked']
            
            if dead:
                dead_links[clean_title] = dead
                total_dead_links += len(dead)
                print(f"   ❌ Found {len(dead)} dead links")
                
                # Write dead links to CSV immediately
                write_article_results_to_csv(csv_writer, clean_title, dead)
                csv_file.flush()  # Ensure data is written to disk
            else:
                print(f"   ✅ All links are alive, archived, or blocked")
            
            if blocked:
                print(f"   🚫 Found {len(blocked)} blocked links (likely bot protection)")
            
            print()
    finally:
        # Ensure CSV file is closed
        csv_file.close()
    
    # Step 3: Generate reports
    print("📋 Generating reports...")
    
    if dead_links:
        summary_file = write_summary_report(dead_links, args.output_dir)
        print(f"📄 CSV report saved to: {csv_filepath}")
        print(f"📄 Summary report saved to: {summary_file}")
    else:
        print("✅ No dead links found!")
    
    # Step 4: Print final summary
    end_time = time.time()
    duration = end_time - start_time
    
    print()
    print("🎯 Final Summary")
    print("=" * 20)
    print(f"📰 Articles processed: {len(articles)}")
    print(f"🔗 Total links checked: {total_links_checked}")
    print(f"❌ Total dead links: {total_dead_links}")
    print(f"⏱️  Total time: {format_duration(duration)}")
    
    if dead_links:
        print_report_summary(dead_links)
    
    # Print browser validation summary if used
    if args.browser_validation and hasattr(args, 'browser_reports') and args.browser_reports:
        print("\n🔍 Browser Validation Summary")
        print("=" * 40)
        
        total_false_positives = 0
        total_confirmed_dead = 0
        total_blocked = 0
        
        for i, report in enumerate(args.browser_reports):
            if report:  # Only process non-None reports
                total_false_positives += report.get('false_positives', 0)
                total_confirmed_dead += report.get('confirmed_dead', 0)
                total_blocked += report.get('blocked', 0)
        
        print(f"Total false positives detected: {total_false_positives}")
        print(f"Total confirmed dead: {total_confirmed_dead}")
        print(f"Total blocked by bot protection: {total_blocked}")
        
        if total_false_positives > 0:
            print(f"🎉 Browser validation helped detect {total_false_positives} false positives!")
    
    print("\n✅ Done!")


def test_individual_components():
    """Test individual components for debugging."""
    print("🧪 Testing individual components...")
    
    # Test fetching top articles
    print("\n1. Testing fetch_top_articles...")
    articles = get_top_articles(limit=3)
    print(f"   Found {len(articles)} articles: {articles}")
    
    if articles:
        # Test fetching article HTML
        print("\n2. Testing fetch_article_html...")
        test_title = articles[0]
        html = get_article_html(test_title)
        print(f"   HTML length for '{test_title}': {len(html)} characters")
        
        if html:
            # Test extracting links
            print("\n3. Testing extract_references...")
            links = extract_external_links(html)
            print(f"   Found {len(links)} external links")
            for i, link in enumerate(links[:3], 1):
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