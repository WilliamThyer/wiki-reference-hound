import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from extract_references import is_archive_url
import polars as pl


def print_report_summary(dead_links: Dict[str, List[Tuple[str, Optional[int]]]]) -> None:
    """
    Print a summary of the dead links report to console.
    
    Args:
        dead_links: Dictionary mapping article titles to lists of (url, status_code) tuples
    """
    if not dead_links:
        print("✅ No dead links found!")
        return
    
    total_articles = len(dead_links)
    total_dead_links = sum(len(links) for links in dead_links.values())
    
    print(f"\n📋 Report Summary:")
    print(f"   Articles with dead links: {total_articles}")
    print(f"   Total dead links: {total_dead_links}")
    
    # Show top articles with most dead links
    sorted_articles = sorted(dead_links.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\n🔝 Top articles with dead links:")
    for i, (article_title, links) in enumerate(sorted_articles[:5], 1):
        print(f"   {i}. {article_title} ({len(links)} dead links)")
    
    if len(sorted_articles) > 5:
        print(f"   ... and {len(sorted_articles) - 5} more articles")


def build_all_references_table(all_links: Dict[str, List[str]], 
                               archive_groups: Dict[str, Dict[str, List[str]]],
                               all_link_results: Dict[str, List[Tuple[str, str, Optional[int]]]] = None,
                               browser_validation_results: Dict[str, Dict[str, Tuple[str, str, Optional[int], Dict]]] = None,
                               generation_timestamp: Optional[str] = None) -> pl.DataFrame:
    """Construct the ALL references Polars DataFrame that serves as the project's primary output."""
    if generation_timestamp is None:
        generation_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    records: List[dict] = []

    for article_title, links in all_links.items():
        article_archives = archive_groups.get(article_title, {})
        article_link_results = all_link_results.get(article_title, []) if all_link_results else []
        article_browser_results = browser_validation_results.get(article_title, {}) if browser_validation_results else {}

        link_results_lookup = {url: (status, code) for url, status, code in article_link_results}

        # Get only original links (non-archive URLs)
        original_links = [url for url in links if not is_archive_url(url)]
        
        for original_url in original_links:
            # Check if this original link has any archive links
            archive_urls = article_archives.get(original_url, [])
            # Use the first archive URL if available, otherwise None
            archive_url = archive_urls[0] if archive_urls else None
            
            # Determine error code and browser validation info for the original URL
            error_code: str
            browser_validation_check = "Not checked"
            browser_validation_check_detail = ""

            if archive_url:
                # If there's an archive, mark as not needing checking
                error_code = 'None'
                browser_validation_check = 'Browser validation not performed.'
            else:
                # No archive, so check the original link status
                if original_url in link_results_lookup:
                    status, status_code = link_results_lookup[original_url]
                    if status == 'dead':
                        error_code = status_code if status_code is not None else 'CONNECTION_ERROR'
                    elif status == 'blocked':
                        error_code = status_code if status_code is not None else 'BLOCKED'
                    elif status == 'alive':
                        error_code = 'None'
                    else:
                        error_code = status_code if status_code is not None else 'ERROR'
                else:
                    error_code = 'Not checked'

                # Get browser validation results if available
                if original_url in article_browser_results:
                    browser_status, browser_code, browser_info = article_browser_results[original_url][1:4]
                    browser_validation_check = browser_status
                    details = []
                    if browser_info:
                        if browser_info.get('error_indicator'):
                            details.append(f"Error: {browser_info['error_indicator']}")
                        if browser_info.get('blocking_indicator'):
                            details.append(f"Blocked: {browser_info['blocking_indicator']}")
                        if browser_info.get('final_url') and browser_info.get('final_url') != original_url:
                            details.append(f"Redirected to: {browser_info['final_url']}")
                        if browser_info.get('title'):
                            details.append(f"Title: {browser_info['title']}")
                    browser_validation_check_detail = "; ".join(details) if details else ''
                else:
                    if original_url in link_results_lookup:
                        status, _ = link_results_lookup[original_url]
                        if status in ('alive', 'blocked', 'dead'):
                            browser_validation_check = status
                        else:
                            browser_validation_check = str(status)

            records.append({
                'article_title': article_title,
                'original_url': original_url,
                'archive_url': archive_url,
                'has_archive': bool(archive_url),
                'error_code': error_code,
                'timestamp': generation_timestamp,
                'browser_validation_check': browser_validation_check,
                'browser_validation_check_detail': browser_validation_check_detail
            })

    df = pl.DataFrame(records, schema={
        'article_title': pl.Utf8,
        'original_url': pl.Utf8,
        'archive_url': pl.Utf8,
        'has_archive': pl.Boolean,
        'error_code': pl.Utf8,
        'timestamp': pl.Utf8,
        'browser_validation_check': pl.Utf8,
        'browser_validation_check_detail': pl.Utf8,
    })

    return df.select([
        'article_title',
        'original_url',
        'archive_url',
        'has_archive',
        'error_code',
        'timestamp',
        'browser_validation_check',
        'browser_validation_check_detail'
    ])


def create_all_references_csv_report(all_links: Dict[str, List[str]], 
                                     archive_groups: Dict[str, Dict[str, List[str]]],
                                     all_link_results: Dict[str, List[Tuple[str, str, Optional[int]]]] = None,
                                     browser_validation_results: Dict[str, Dict[str, Tuple[str, str, Optional[int], Dict]]] = None,
                                     output_dir: str = 'output',
                                     batch_number: Optional[int] = None) -> str:
    """
    Create a comprehensive CSV report of all references with their status.
    
    Args:
        all_links: Dictionary mapping article titles to lists of URLs
        archive_groups: Dictionary mapping article titles to archive groups
        all_link_results: Dictionary mapping article titles to link checking results
        browser_validation_results: Dictionary mapping article titles to browser validation results
        output_dir: Directory to save the report
        batch_number: Optional batch number for batch processing
        
    Returns:
        Filepath of the created CSV report
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp and filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if batch_number is not None:
        filename = f"all_references_batch_{batch_number:03d}_{timestamp}.csv"
    else:
        filename = f"all_references_{timestamp}.csv"
    
    filepath = os.path.join(output_dir, filename)
    
    # Build the comprehensive table
    df = build_all_references_table(
        all_links, 
        archive_groups, 
        all_link_results, 
        browser_validation_results, 
        timestamp
    )
    
    # Save to CSV
    df.write_csv(filepath)
    
    print(f"📊 CSV report saved: {filepath}")
    print(f"   📋 Total records: {len(df)}")
    print(f"   📰 Articles: {len(all_links)}")
    
    return filepath
