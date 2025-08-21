#!/usr/bin/env python3
"""
Wikipedia Dead Link Checker

Checks for dead external links in top Wikipedia articles.
"""

import argparse
import time
import os
import json
from typing import Dict, List, Tuple, Optional

from fetch_top_articles import get_top_articles, get_all_time_top_articles
from fetch_article_html import get_article_html, get_article_html_batch
from extract_references import extract_external_links, extract_external_links_from_references, filter_links_for_checking, get_references_with_archives
from check_links import check_all_links_with_archives, check_all_links_with_archives_parallel, print_link_summary
from generate_report import create_all_references_csv_report, print_report_summary
from utils import clean_article_title, format_duration


def load_popular_articles_from_json(filepath: str, limit: int, verbose: bool = False) -> List[str]:
    """
    Load popular articles from a JSON file.
    
    Args:
        filepath: Path to the JSON file containing popular articles
        limit: Maximum number of articles to return
        verbose: Whether to print verbose output
        
    Returns:
        List of article titles
    """
    try:
        if verbose:
            print(f"📁 Loading popular articles from: {filepath}")
        
        if not os.path.exists(filepath):
            if verbose:
                print(f"❌ File not found: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            if verbose:
                print(f"❌ Invalid JSON format: expected list, got {type(data).__name__}")
            return []
        
        # Extract article titles from the JSON data
        articles = []
        for item in data:
            if isinstance(item, dict) and 'title' in item:
                articles.append(item['title'])
            elif isinstance(item, str):
                # Handle case where items are just strings
                articles.append(item)
        
        if verbose:
            print(f"📊 Loaded {len(articles)} articles from JSON file")
        
        # Limit the number of articles
        if limit > 0:
            articles = articles[:limit]
            if verbose:
                print(f"📏 Limited to {len(articles)} articles as requested")
        
        return articles
        
    except json.JSONDecodeError as e:
        if verbose:
            print(f"❌ JSON parsing error: {e}")
        return []
    except Exception as e:
        if verbose:
            print(f"❌ Error loading popular articles: {e}")
        return []


def main():
    """Main function to orchestrate the dead link checking process."""
    
    parser = argparse.ArgumentParser(description='Check for dead links in top Wikipedia articles')
    parser.add_argument('--limit', type=int, default=25, 
                       help='Number of articles to check (default: 25)')
    parser.add_argument('--all-time', action='store_true', default=True,
                       help='Fetch top articles of all time instead of yesterday\'s top articles (default: True)')
    parser.add_argument('--daily', action='store_false', dest='all_time',
                       help='Fetch yesterday\'s top articles instead of all-time (default: all-time)')
    parser.add_argument('--use-popular-articles', type=str, default=None,
                       help='Use articles from specified JSON file instead of fetching from API (e.g., output/popular_articles.json)')
    parser.add_argument('--timeout', type=float, default=5.0,
                       help='Request timeout in seconds (default: 5.0)')
    parser.add_argument('--delay', type=float, default=0.2,
                       help='Delay between link checks in seconds (default: 0.2)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for reports (default: output)')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Enable parallel processing for faster link checking (default: True)')
    parser.add_argument('--no-parallel', action='store_false', dest='parallel',
                       help='Disable parallel processing (default: parallel enabled)')
    parser.add_argument('--max-workers', type=int, default=3,
                       help='Maximum number of concurrent workers for parallel processing (default: 3)')
    parser.add_argument('--chunk-size', type=int, default=100,
                       help='Number of links to process in each batch for parallel processing (default: 100)')
    # Browser validation arguments
    parser.add_argument('--browser-validation', action='store_true', default=True,
                       help='Enable browser validation for false positive detection (default: True)')
    parser.add_argument('--no-browser-validation', action='store_false', dest='browser_validation',
                       help='Disable browser validation (default: browser validation enabled)')
    parser.add_argument('--browser-timeout', type=int, default=30,
                       help='Browser page load timeout in seconds (default: 30)')
    parser.add_argument('--max-browser-links', type=int, default=50,
                       help='Maximum number of dead links to validate with browser (default: 50)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser in visible mode (default: headless)')
    parser.add_argument('--references-only', action='store_true', default=True,
                       help='Only extract external links from the references section (default: True)')
    parser.add_argument('--all-links', action='store_false', dest='references_only',
                       help='Extract all external links, not just references (default: references only)')
    parser.add_argument('--use-html-structure', action='store_true', default=True,
                       help='Use HTML structure analysis to associate archives with their originals (default: True)')
    parser.add_argument('--no-html-structure', action='store_false', dest='use_html_structure',
                       help='Disable HTML structure analysis (default: HTML structure analysis enabled)')
    parser.add_argument('--verbose', action='store_true', default=False,
                       help='Enable verbose output (default: False)')
    
    args = parser.parse_args()
    
    if args.verbose:
        print("🔍 Wikipedia Dead Link Checker")
        print("=" * 40)
        if args.use_popular_articles:
            print(f"📊 Using articles from: {args.use_popular_articles}")
            print(f"📏 Will check up to {args.limit} articles")
        elif args.all_time:
            print(f"📊 Checking top {args.limit} articles of all time (default)")
        else:
            print(f"📊 Checking top {args.limit} articles from yesterday")
        print(f"⏱️  Timeout: {args.timeout}s, Delay: {args.delay}s")
        if args.parallel:
            print(f"🚀 Parallel processing enabled: {args.max_workers} workers, chunk size: {args.chunk_size} (default)")
        else:
            print(f"🐌 Sequential processing enabled (parallel disabled)")
        
        if args.browser_validation:
            if args.verbose:
                print(f"🔍 Browser validation enabled: {args.browser_timeout}s timeout, headless: {not args.no_headless} (default)")
                print(f"   Max browser validation links: {args.max_browser_links}")
        else:
            if args.verbose:
                print(f"🔍 Browser validation disabled")
        if args.references_only:
            print(f"🎯 References-only mode enabled: Only extracting links from references section (default)")
        else:
            print(f"🔍 Comprehensive mode enabled: Extracting all external links")
        if args.use_html_structure:
            print(f"🔗 HTML structure analysis enabled: Using HTML proximity to associate archives with originals (default)")
        else:
            print(f"🔗 Basic archive detection enabled")
        print()
    
    start_time = time.time()
    
    # Step 1: Fetch top articles
    if args.verbose:
        print("📰 Fetching articles...")
    
    if args.use_popular_articles:
        # Load articles from JSON file
        articles = load_popular_articles_from_json(args.use_popular_articles, args.limit, args.verbose)
    elif args.all_time:
        articles = get_all_time_top_articles(limit=args.limit, verbose=args.verbose)
    else:
        articles = get_top_articles(limit=args.limit, verbose=args.verbose)
    
    if not articles:
        print("❌ Failed to fetch articles. Exiting.")
        return
    
    if args.verbose:
        print(f"✅ Found {len(articles)} articles to check")
        print()
    
    # Step 2: Process articles in efficient batches
    if args.verbose:
        print("🔍 Processing articles in batches...")
    
    # Process articles in chunks to manage memory
    chunk_size = 50  # Process 50 articles at a time
    dead_links = {}
    total_links_checked = 0
    total_dead_links = 0
    total_archived_links = 0
    
    # Track progress and memory usage
    import gc
    import psutil
    import os
    
    def get_memory_usage():
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0
    
    if args.verbose:
        print(f"💾 Initial memory usage: {get_memory_usage():.1f} MB")
    
    for chunk_start in range(0, len(articles), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(articles))
        chunk_articles = articles[chunk_start:chunk_end]
        
        if args.verbose:
            print(f"\n📦 Processing batch {chunk_start//chunk_size + 1}/{(len(articles)-1)//chunk_size + 1}: {len(chunk_articles)} articles")
            print(f"   📊 Progress: {chunk_start}/{len(articles)} articles ({chunk_start/len(articles)*100:.1f}%)")
            print(f"   💾 Memory before batch: {get_memory_usage():.1f} MB")
        
        # Fetch all articles in this chunk in a single API call
        if args.verbose:
            print(f"   📥 Fetching HTML content for {len(chunk_articles)} articles...")
        html_batch = get_article_html_batch(chunk_articles, delay=args.delay, verbose=args.verbose)
        
        if not html_batch:
            if args.verbose:
                print(f"   ❌ Failed to fetch any articles in this batch")
            continue
        
        if args.verbose:
            print(f"   ✅ Successfully fetched {len(html_batch)} articles")
        
        # Process each article in the chunk
        chunk_dead_links = {}
        chunk_all_links = {}
        chunk_archive_groups = {}
        chunk_link_results = {}
        chunk_browser_results = {}
        
        for i, title in enumerate(chunk_articles, 1):
            clean_title = clean_article_title(title)
            if args.verbose:
                print(f"   🔍 Processing ({i}/{len(chunk_articles)}): {clean_title}")
            
            # Get HTML for this article from the batch
            html = html_batch.get(title, "")
            if not html:
                if args.verbose:
                    print(f"      ⚠️  No HTML content for '{clean_title}'")
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
                
                if args.verbose:
                    print(f"      🔗 Using HTML structure analysis method")
            elif args.references_only:
                article_links = extract_external_links_from_references(html)
                if args.verbose:
                    print(f"      🎯 Using references-only extraction method")
                
                # Filter links for checking (remove archives, group with originals)
                links_to_check, archive_groups = filter_links_for_checking(article_links)
            else:
                article_links = extract_external_links(html)
                if args.verbose:
                    print(f"      🔍 Using comprehensive extraction method")
                
                # Filter links for checking (remove archives, group with originals)
                links_to_check, archive_groups = filter_links_for_checking(article_links)
            
            if not article_links:
                if args.verbose:
                    print(f"      ℹ️  No external links found in '{clean_title}'")
                continue
            
            # For HTML structure method, we already have the archive groups
            if not args.use_html_structure:
                # Filter links for checking (remove archives, group with originals)
                links_to_check, archive_groups = filter_links_for_checking(article_links)
            else:
                # For HTML structure method, links_to_check is all original links
                links_to_check = article_links
            
            # Store all links and archive groups for this article
            chunk_all_links[clean_title] = article_links
            chunk_archive_groups[clean_title] = archive_groups
            
            # Count links that actually have archives
            links_with_archives = sum(1 for archives in archive_groups.values() if archives)
            
            if args.verbose:
                print(f"      📎 Found {len(article_links)} total links ({len(links_to_check)} to check, {links_with_archives} with archives)")
            
            total_links_checked += len(links_to_check)
            
            # Check link status
            if args.parallel:
                if args.verbose:
                    print(f"      🔗 Checking link status in parallel...")
                results = check_all_links_with_archives_parallel(links_to_check, archive_groups, timeout=args.timeout, max_workers=args.max_workers)
            else:
                if args.verbose:
                    print(f"      🔗 Checking link status...")
                results = check_all_links_with_archives(links_to_check, archive_groups, timeout=args.timeout, delay=args.delay)
            
            # Store complete link checking results for this article
            chunk_link_results[clean_title] = results
            
            # Browser validation if enabled
            if args.browser_validation:
                from browser_validation import validate_dead_links_with_browser
                
                # Get dead links for browser validation
                dead_for_browser = [(url, status, code) for url, status, code in results if status == 'dead']
                
                if dead_for_browser:
                    if args.verbose:
                        print(f"      🔍 Browser validating {len(dead_for_browser)} dead links...")
                    browser_results = validate_dead_links_with_browser(
                        dead_for_browser,
                        headless=not args.no_headless,
                        timeout=args.browser_timeout,
                        verbose=args.verbose
                    )
                    
                    # Store browser validation results for this article
                    article_browser_results = {}
                    for browser_result in browser_results:
                        url, status, code, info = browser_result
                        article_browser_results[url] = browser_result
                    chunk_browser_results[clean_title] = article_browser_results
                else:
                    chunk_browser_results[clean_title] = {}
            else:
                chunk_browser_results[clean_title] = {}
            
            # Filter dead links (only truly dead, not archived or blocked)
            dead = [(url, code) for url, status, code in results if status == 'dead']
            blocked = [(url, status, code) for url, status, code in results if status == 'blocked']
            archived = [(url, code) for url, status, code in results if status == 'archived']
            
            if dead:
                chunk_dead_links[clean_title] = dead
                total_dead_links += len(dead)
                if args.verbose:
                    print(f"      ❌ Found {len(dead)} dead links")
            else:
                if args.verbose:
                    print(f"      ✅ All links are alive, archived, or blocked")
            
            if blocked:
                if args.verbose:
                    print(f"      🚫 Found {len(blocked)} blocked links (likely bot protection)")
            
            if archived:
                if args.verbose:
                    print(f"      📦 Found {len(archived)} archived links (skipped during checking)")
                total_archived_links += len(archived)
        
        # Generate report for this chunk immediately
        if args.verbose:
            print(f"   📋 Generating report for batch {chunk_start//chunk_size + 1}...")
        
        # Create the comprehensive CSV for this chunk
        chunk_csv_filepath = create_all_references_csv_report(
            chunk_all_links, 
            chunk_archive_groups, 
            chunk_link_results,
            chunk_browser_results, 
            args.output_dir,
            batch_number=chunk_start//chunk_size + 1,
            verbose=args.verbose
        )
        
        if args.verbose:
            print(f"   📄 Batch {chunk_start//chunk_size + 1} CSV report saved to: {chunk_csv_filepath}")
        
        # Merge chunk results into main results
        dead_links.update(chunk_dead_links)
        
        # Clear chunk data to free memory
        del chunk_all_links, chunk_archive_groups, chunk_link_results, chunk_browser_results
        del html_batch  # Clear the HTML batch data too
        
        # Force garbage collection
        gc.collect()
        
        if args.verbose:
            print(f"   ✅ Batch {chunk_start//chunk_size + 1} completed. Memory cleared.")
            print(f"   💾 Memory after cleanup: {get_memory_usage():.1f} MB")
        
        # Add delay between chunks to be respectful to the API
        if chunk_end < len(articles):
            if args.verbose:
                print(f"   ⏳ Waiting {args.delay}s before next batch...")
            time.sleep(args.delay)
    
    if args.verbose:
        print(f"\n✅ All {len(articles)} articles processed in batches!")
        print(f"💾 Final memory usage: {get_memory_usage():.1f} MB")
    
    # Step 3: Generate final summary report (optional)
    if args.verbose:
        print("📋 Generating final summary report...")
    
    # Create a final summary CSV combining all batches if needed
    if args.output_dir and os.path.exists(args.output_dir):
        batch_files = [f for f in os.listdir(args.output_dir) if f.startswith('all_references_batch_') and f.endswith('.csv')]
        if batch_files:
            if args.verbose:
                print(f"📄 Generated {len(batch_files)} batch reports in {args.output_dir}")
                print(f"   Each batch contains up to {chunk_size} articles")
                print(f"   Combine them manually or use a data analysis tool to merge")
    
    # Step 4: Print final summary
    end_time = time.time()
    duration = end_time - start_time
    
    if args.verbose:
        print()
        print("🎯 Final Summary")
        print("=" * 20)
        print(f"📰 Articles processed: {len(articles)}")
        print(f"🔗 Total links checked: {total_links_checked}")
        print(f"❌ Total dead links: {total_dead_links}")
    
    if total_archived_links > 0:
        if args.verbose:
            print(f"📦 Total archive URLs found: {total_archived_links}")
    
    if args.verbose:
        print(f"⏱️  Total time: {format_duration(duration)}")
    
    # Optional: show quick dead-link summary in console for awareness
    if dead_links:
        print_report_summary(dead_links, verbose=args.verbose)
    
    # Print browser validation summary if used
    if args.browser_validation and hasattr(args, 'browser_reports') and args.browser_reports:
        if args.verbose:
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
        
        if args.verbose:
            print(f"Total false positives detected: {total_false_positives}")
            print(f"Total confirmed dead: {total_confirmed_dead}")
            print(f"Total blocked by bot protection: {total_blocked}")
            print(f"Total timeout errors: {total_timeout}")
            print(f"Total other errors: {total_error}")
        
        if total_false_positives > 0:
            if args.verbose:
                print(f"🎉 Browser validation helped detect {total_false_positives} false positives!")
                print(f"💡 Detailed results are captured in the all-references CSV report")
        
    if args.verbose:
        print("\n✅ Done!")


def test_individual_components(verbose=False):
    """Test individual components for debugging."""
    if verbose:
        print("🧪 Testing individual components...")
    
    # Test fetching top articles
    if verbose:
        print("\n1. Testing fetch_top_articles (daily)...")
    daily_articles = get_top_articles(limit=3)
    if verbose:
        print(f"   Found {len(daily_articles)} daily articles: {daily_articles}")
    
    if verbose:
        print("\n2. Testing fetch_top_articles (all-time)...")
    all_time_articles = get_all_time_top_articles(limit=3)
    if verbose:
        print(f"   Found {len(all_time_articles)} all-time articles: {all_time_articles}")
    
    # Use the first available articles for further testing
    articles = daily_articles if daily_articles else all_time_articles
    
    if articles:
        # Test fetching article HTML
        if verbose:
            print("\n2. Testing fetch_article_html...")
        test_title = articles[0]
        html = get_article_html(test_title)
        if verbose:
            print(f"   HTML length for '{test_title}': {len(html)} characters")
        
        if html:
            # Test extracting links
            if verbose:
                print("\n3. Testing extract_references...")
                print("   Testing comprehensive method:")
            links = extract_external_links(html)
            if verbose:
                print(f"   Found {len(links)} external links")
                for i, link in enumerate(links[:3], 1):
                    print(f"   {i}. {link}")
            
            if verbose:
                print("   Testing references-only method:")
            ref_links = extract_external_links_from_references(html)
            if verbose:
                print(f"   Found {len(ref_links)} external links from references only")
                for i, link in enumerate(ref_links[:3], 1):
                    print(f"   {i}. {link}")
            
            if links:
                # Test checking links
                if verbose:
                    print("\n4. Testing check_links...")
                results = check_all_links_with_archives(links[:2], {}, timeout=3.0, delay=0.5)
                if verbose:
                    print_link_summary(results, verbose=verbose)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Parse args to get verbose flag for testing
        parser = argparse.ArgumentParser(description='Test individual components')
        parser.add_argument('--test', action='store_true', help='Run tests')
        parser.add_argument('--verbose', action='store_true', default=False, help='Enable verbose output')
        test_args = parser.parse_args()
        test_individual_components(verbose=test_args.verbose)
    else:
        main() 