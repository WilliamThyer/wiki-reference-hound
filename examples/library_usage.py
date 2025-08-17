#!/usr/bin/env python3
"""
Example: Using Wikipedia Dead Link Finder as a Python Library

This script demonstrates how to use the tool programmatically instead of via CLI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wikipedia_dead_ref_finder import (
    WikipediaDeadLinkFinder, 
    ProcessingConfig,
    get_top_articles,
    get_all_time_top_articles
)


def example_basic_usage():
    """Basic usage with default configuration."""
    print("🔍 Example 1: Basic Usage with Default Settings")
    print("=" * 50)
    
    # Create a finder with default settings
    finder = WikipediaDeadLinkFinder()
    
    # Find dead links in top articles
    results = finder.find_dead_links()
    
    # Print summary
    print(f"Processed {len(results)} articles")
    
    # Get only articles with dead links
    dead_links = finder.get_dead_links_only()
    print(f"Found {len(dead_links)} articles with dead links")
    
    # Print summary statistics
    stats = finder.get_summary_stats()
    print(f"Total links checked: {stats['total_links_checked']}")
    print(f"Total dead links: {stats['total_dead_links']}")
    print(f"Processing time: {stats['processing_time_seconds']:.2f} seconds")
    
    return finder


def example_custom_configuration():
    """Example with custom configuration."""
    print("\n🔍 Example 2: Custom Configuration")
    print("=" * 50)
    
    # Create custom configuration
    config = ProcessingConfig(
        limit=5,  # Only check 5 articles
        all_time=False,  # Use daily top articles
        timeout=10.0,  # Longer timeout
        parallel=False,  # Disable parallel processing
        browser_validation=False,  # Disable browser validation
        verbose=True  # Enable verbose output
    )
    
    # Create finder with custom config
    finder = WikipediaDeadLinkFinder(config)
    
    # Find dead links
    results = finder.find_dead_links()
    
    print(f"Processed {len(results)} articles with custom settings")
    return finder


def example_specific_articles():
    """Example with specific article titles."""
    print("\n🔍 Example 3: Specific Articles")
    print("=" * 50)
    
    # Create finder
    finder = WikipediaDeadLinkFinder()
    
    # Define specific articles to check
    specific_articles = [
        "Python_(programming_language)",
        "JavaScript",
        "HTML"
    ]
    
    # Process specific articles
    results = finder.find_dead_links(specific_articles)
    
    print(f"Processed {len(results)} specific articles")
    
    # Show results for each article
    for title, result in results.items():
        print(f"\n📰 {title}:")
        print(f"   Total links: {result.total_links}")
        print(f"   Dead links: {len(result.dead_links)}")
        print(f"   Alive links: {len(result.alive_links)}")
        
        # Show some dead links
        if result.dead_links:
            print("   Dead links:")
            for link in result.dead_links[:3]:  # Show first 3
                print(f"     - {link.url} (Status: {link.status_code})")
    
    return finder


def example_data_analysis():
    """Example of analyzing the results data."""
    print("\n🔍 Example 4: Data Analysis")
    print("=" * 50)
    
    # Get some articles first
    finder = WikipediaDeadLinkFinder(ProcessingConfig(limit=10, verbose=False))
    results = finder.find_dead_links()
    
    if not results:
        print("No results to analyze")
        return
    
    # Analyze the data
    total_dead_links = 0
    total_alive_links = 0
    articles_with_dead_links = 0
    
    for title, result in results.items():
        total_dead_links += len(result.dead_links)
        total_alive_links += len(result.alive_links)
        if result.dead_links:
            articles_with_dead_links += 1
    
    # Calculate statistics
    total_articles = len(results)
    dead_link_percentage = (total_dead_links / (total_dead_links + total_alive_links)) * 100 if (total_dead_links + total_alive_links) > 0 else 0
    articles_with_dead_links_percentage = (articles_with_dead_links / total_articles) * 100
    
    print(f"📊 Analysis Results:")
    print(f"   Total articles: {total_articles}")
    print(f"   Articles with dead links: {articles_with_dead_links} ({articles_with_dead_links_percentage:.1f}%)")
    print(f"   Total dead links: {total_dead_links}")
    print(f"   Total alive links: {total_alive_links}")
    print(f"   Dead link rate: {dead_link_percentage:.1f}%")
    
    # Find articles with most dead links
    articles_by_dead_links = sorted(
        results.items(), 
        key=lambda x: len(x[1].dead_links), 
        reverse=True
    )
    
    print(f"\n🔝 Top articles with dead links:")
    for i, (title, result) in enumerate(articles_by_dead_links[:5], 1):
        if result.dead_links:
            print(f"   {i}. {title}: {len(result.dead_links)} dead links")
    
    return finder


def example_export_results():
    """Example of exporting results to CSV."""
    print("\n🔍 Example 5: Export Results")
    print("=" * 50)
    
    # Create finder and get results
    finder = WikipediaDeadLinkFinder(ProcessingConfig(limit=5, verbose=False))
    results = finder.find_dead_links()
    
    if not results:
        print("No results to export")
        return
    
    # Export to CSV
    try:
        csv_filepath = finder.export_to_csv(
            output_dir="output",
            filename_prefix="example_export"
        )
        print(f"✅ Results exported to: {csv_filepath}")
    except Exception as e:
        print(f"❌ Failed to export: {e}")
    
    return finder


def example_individual_functions():
    """Example of using individual functions directly."""
    print("\n🔍 Example 6: Individual Functions")
    print("=" * 50)
    
    # Get top articles
    print("Fetching top articles...")
    articles = get_top_articles(limit=3)
    print(f"Found articles: {articles}")
    
    if articles:
        # Get HTML for first article
        from wikipedia_dead_ref_finder import get_article_html
        html = get_article_html(articles[0])
        print(f"HTML length for '{articles[0]}': {len(html)} characters")
        
        if html:
            # Extract external links
            from wikipedia_dead_ref_finder import extract_external_links_from_references
            links = extract_external_links_from_references(html)
            print(f"Found {len(links)} external links in references")
            
            if links:
                # Check a few links
                from wikipedia_dead_ref_finder import check_all_links_with_archives
                results = check_all_links_with_archives(links[:2], {}, timeout=5.0)
                print(f"Link check results: {results}")


def main():
    """Run all examples."""
    print("🚀 Wikipedia Dead Link Finder - Library Usage Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_usage()
        example_custom_configuration()
        example_specific_articles()
        example_data_analysis()
        example_export_results()
        example_individual_functions()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
