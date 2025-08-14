import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
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

        for url in links:
            has_archive = bool(url in article_archives and article_archives[url])

            error_code: str
            browser_validation_check = "Not checked"
            browser_validation_check_detail = ""

            if has_archive:
                error_code = 'None'
                browser_validation_check = 'Browser validation not performed.'
            else:
                if url in link_results_lookup:
                    status, status_code = link_results_lookup[url]
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

                if url in article_browser_results:
                    browser_status, browser_code, browser_info = article_browser_results[url][1:4]
                    browser_validation_check = browser_status
                    details = []
                    if browser_info:
                        if browser_info.get('error_indicator'):
                            details.append(f"Error: {browser_info['error_indicator']}")
                        if browser_info.get('blocking_indicator'):
                            details.append(f"Blocked: {browser_info['blocking_indicator']}")
                        if browser_info.get('final_url') and browser_info.get('final_url') != url:
                            details.append(f"Redirected to: {browser_info['final_url']}")
                        if browser_info.get('title'):
                            details.append(f"Title: {browser_info['title']}")
                    browser_validation_check_detail = "; ".join(details) if details else ''
                else:
                    if url in link_results_lookup:
                        status, _ = link_results_lookup[url]
                        if status in ('alive', 'blocked', 'dead'):
                            browser_validation_check = status
                        else:
                            browser_validation_check = str(status)

            records.append({
                'article_title': article_title,
                'url': url,
                'has_archive': has_archive,
                'error_code': error_code,
                'timestamp': generation_timestamp,
                'browser_validation_check': browser_validation_check,
                'browser_validation_check_detail': browser_validation_check_detail
            })

    df = pl.DataFrame(records, schema={
        'article_title': pl.Utf8,
        'url': pl.Utf8,
        'has_archive': pl.Boolean,
        'error_code': pl.Utf8,
        'timestamp': pl.Utf8,
        'browser_validation_check': pl.Utf8,
        'browser_validation_check_detail': pl.Utf8,
    })

    return df.select([
        'article_title',
        'url',
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
                                   output_dir: str = "output") -> str:
    """Build the Polars table and persist it to CSV, returning the file path."""
    os.makedirs(output_dir, exist_ok=True)
    generation_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"all_references_report_{generation_timestamp}.csv"
    filepath = os.path.join(output_dir, filename)

    df = build_all_references_table(
        all_links=all_links,
        archive_groups=archive_groups,
        all_link_results=all_link_results,
        browser_validation_results=browser_validation_results,
        generation_timestamp=generation_timestamp,
    )
    df.write_csv(filepath)
    return filepath
