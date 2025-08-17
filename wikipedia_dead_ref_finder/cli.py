#!/usr/bin/env python3
"""
Command-line interface for Wikipedia Dead Link Finder

This module provides the CLI functionality, separated from the core library.
"""

import argparse
import sys
import os
from typing import Optional

from .core import WikipediaDeadLinkFinder, ProcessingConfig


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description='Check for dead links in top Wikipedia articles')
    
    # Article selection
    parser.add_argument('--limit', type=int, default=25, 
                       help='Number of articles to check (default: 25)')
    parser.add_argument('--all-time', action='store_true', default=True,
                       help='Fetch top articles of all time instead of yesterday\'s top articles (default: True)')
    parser.add_argument('--daily', action='store_false', dest='all_time',
                       help='Fetch yesterday\'s top articles instead of all-time (default: all-time)')
    
    # Performance settings
    parser.add_argument('--timeout', type=float, default=5.0,
                       help='Request timeout in seconds (default: 5.0)')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='Delay between link checks in seconds (default: 0.1)')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Enable parallel processing for faster link checking (default: True)')
    parser.add_argument('--no-parallel', action='store_false', dest='parallel',
                       help='Disable parallel processing (default: parallel enabled)')
    parser.add_argument('--max-workers', type=int, default=50,
                       help='Maximum number of concurrent workers for parallel processing (default: 50)')
    parser.add_argument('--chunk-size', type=int, default=100,
                       help='Number of links to process in each batch for parallel processing (default: 100)')
    
    # Browser validation
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
    
    # Link extraction settings
    parser.add_argument('--references-only', action='store_true', default=True,
                       help='Only extract external links from the references section (default: True)')
    parser.add_argument('--all-links', action='store_false', dest='references_only',
                       help='Extract all external links, not just references (default: references only)')
    parser.add_argument('--use-html-structure', action='store_true', default=True,
                       help='Use HTML structure analysis to associate archives with their originals (default: True)')
    parser.add_argument('--no-html-structure', action='store_false', dest='use_html_structure',
                       help='Disable HTML structure analysis (default: HTML structure analysis enabled)')
    
    # Output settings
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for reports (default: output)')
    parser.add_argument('--no-csv', action='store_true',
                       help='Skip CSV report generation (default: generate CSV)')
    parser.add_argument('--verbose', action='store_true', default=False,
                       help='Enable verbose output (default: False)')
    
    # Testing
    parser.add_argument('--test', action='store_true',
                       help='Run component tests instead of main functionality')
    
    return parser


def create_config_from_args(args) -> ProcessingConfig:
    """Create a ProcessingConfig from parsed arguments."""
    return ProcessingConfig(
        limit=args.limit,
        all_time=args.all_time,
        timeout=args.timeout,
        delay=args.delay,
        parallel=args.parallel,
        max_workers=args.max_workers,
        chunk_size=args.chunk_size,
        browser_validation=args.browser_validation,
        browser_timeout=args.browser_timeout,
        max_browser_links=args.max_browser_links,
        headless=not args.no_headless,
        references_only=args.references_only,
        use_html_structure=args.use_html_structure,
        verbose=args.verbose
    )


def print_startup_info(config: ProcessingConfig):
    """Print startup information based on configuration."""
    print("🔍 Wikipedia Dead Link Checker")
    print("=" * 40)
    
    if config.all_time:
        print(f"📊 Checking top {config.limit} articles of all time (default)")
    else:
        print(f"📊 Checking top {config.limit} articles from yesterday")
    
    print(f"⏱️  Timeout: {config.timeout}s, Delay: {config.delay}s")
    
    if config.parallel:
        print(f"🚀 Parallel processing enabled: {config.max_workers} workers, chunk size: {config.chunk_size} (default)")
    else:
        print(f"🐌 Sequential processing enabled (parallel disabled)")
    
    if config.browser_validation:
        print(f"🔍 Browser validation enabled: {config.browser_timeout}s timeout, headless: {config.headless} (default)")
        print(f"   Max browser validation links: {config.max_browser_links}")
    else:
        print(f"🔍 Browser validation disabled")
    
    if config.references_only:
        print(f"🎯 References-only mode enabled: Only extracting links from references section (default)")
    else:
        print(f"🔍 Comprehensive mode enabled: Extracting all external links")
    
    if config.use_html_structure:
        print(f"🔗 HTML structure analysis enabled: Using HTML proximity to associate archives with originals (default)")
    else:
        print(f"🔗 Basic archive detection enabled")
    
    print()


def test_individual_components(verbose: bool = False):
    """Test individual components for debugging."""
    if verbose:
        print("🧪 Testing individual components...")
    
    # Test fetching top articles
    if verbose:
        print("\n1. Testing fetch_top_articles (daily)...")
    from .fetch_top_articles import get_top_articles, get_all_time_top_articles
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
            print("\n3. Testing fetch_article_html...")
        from .fetch_article_html import get_article_html
        test_title = articles[0]
        html = get_article_html(test_title)
        if verbose:
            print(f"   HTML length for '{test_title}': {len(html)} characters")
        
        if html:
            # Test extracting links
            if verbose:
                print("\n4. Testing extract_references...")
                print("   Testing comprehensive method:")
            from .extract_references import extract_external_links
            links = extract_external_links(html)
            if verbose:
                print(f"   Found {len(links)} external links")
                for i, link in enumerate(links[:3], 1):
                    print(f"   {i}. {link}")
            
            if verbose:
                print("   Testing references-only method:")
            from .extract_references import extract_external_links_from_references
            ref_links = extract_external_links_from_references(html)
            if verbose:
                print(f"   Found {len(ref_links)} external links from references only")
                for i, link in enumerate(ref_links[:3], 1):
                    print(f"   {i}. {link}")
            
            if links:
                # Test checking links
                if verbose:
                    print("\n5. Testing check_links...")
                from .check_links import check_all_links_with_archives, print_link_summary
                results = check_all_links_with_archives(links[:2], {}, timeout=3.0, delay=0.5)
                if verbose:
                    print_link_summary(results, verbose=verbose)


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle testing mode
    if args.test:
        test_individual_components(verbose=args.verbose)
        return
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Print startup information
    if config.verbose:
        print_startup_info(config)
    
    # Create and run the dead link finder
    finder = WikipediaDeadLinkFinder(config)
    
    try:
        # Run the analysis
        results = finder.find_dead_links()
        
        if not results:
            print("❌ No articles were processed successfully.")
            return
        
        # Generate CSV report if requested
        if not args.no_csv:
            if config.verbose:
                print("\n📋 Generating CSV report...")
            
            # Ensure output directory exists
            os.makedirs(args.output_dir, exist_ok=True)
            
            csv_filepath = finder.export_to_csv(
                output_dir=args.output_dir
            )
            
            if config.verbose:
                print(f"📄 CSV report saved to: {csv_filepath}")
        
        # Print final summary
        if config.verbose:
            print("\n✅ Processing completed successfully!")
        
        # Show quick dead-link summary in console
        dead_links_only = finder.get_dead_links_only()
        if dead_links_only:
            from .generate_report import print_report_summary
            
            # Convert to the format expected by print_report_summary
            dead_links_for_report = {}
            for title, links in dead_links_only.items():
                dead_links_for_report[title] = [(link.url, link.status, link.status_code) for link in links]
            
            print_report_summary(dead_links_for_report, verbose=config.verbose)
        else:
            if config.verbose:
                print("🎉 No dead links found!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        if config.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
