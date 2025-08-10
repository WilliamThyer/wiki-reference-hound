import csv
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime


def write_report(dead_links: Dict[str, List[Tuple[str, Optional[int]]]], output_dir: str = "output") -> str:
    """
    Generate a CSV report of dead links found in Wikipedia articles.
    
    Args:
        dead_links: Dictionary mapping article titles to lists of (url, status_code) tuples
        output_dir: Directory to save the report (default: "output")
        
    Returns:
        Path to the generated CSV file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dead_links_report_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Write CSV report
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['article_title', 'url', 'status_code', 'timestamp'])
        
        # Write data
        for article_title, links in dead_links.items():
            for url, status_code in links:
                writer.writerow([
                    article_title,
                    url,
                    status_code if status_code is not None else 'CONNECTION_ERROR',
                    timestamp
                ])
    
    return filepath


def create_incremental_csv_writer(output_dir: str = "output") -> Tuple[str, csv.writer]:
    """
    Create a CSV file and writer for incremental writing of dead links.
    
    Args:
        output_dir: Directory to save the report (default: "output")
        
    Returns:
        Tuple of (filepath, csv_writer)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dead_links_report_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Create file and writer
    csvfile = open(filepath, 'w', newline='', encoding='utf-8')
    writer = csv.writer(csvfile)
    
    # Write header with separate browser validation columns
    writer.writerow(['article_title', 'url', 'error_code', 'timestamp', 'browser_validation_check', 'browser_validation_check_detail'])
    
    return filepath, writer, csvfile


def write_article_results_to_csv(writer: csv.writer, article_title: str, 
                                dead_links: List[Tuple[str, Optional[int]]], 
                                browser_validation_results: Dict[str, Tuple[str, str, Optional[int], Dict]] = None,
                                timestamp: str = None) -> None:
    """
    Write results for a single article to the CSV file.
    
    Args:
        writer: CSV writer object
        article_title: Title of the article
        dead_links: List of (url, status_code) tuples for dead links
        browser_validation_results: Dictionary mapping URLs to browser validation results
        timestamp: Timestamp to use (defaults to current time)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for url, status_code in dead_links:
        # Get browser validation result for this URL if available
        browser_result = "Not checked"
        browser_detail = ""
        if browser_validation_results and url in browser_validation_results:
            browser_status, browser_code, browser_info = browser_validation_results[url][1:4]
            browser_result = browser_status
            browser_detail = ""
            
            if browser_info:
                details = []
                if browser_info.get('error_indicator'):
                    details.append(f"Error: {browser_info['error_indicator']}")
                if browser_info.get('blocking_indicator'):
                    details.append(f"Blocked: {browser_info['blocking_indicator']}")
                if browser_info.get('final_url') and browser_info.get('final_url') != url:
                    details.append(f"Redirected to: {browser_info['final_url']}")
                if browser_info.get('title'):
                    details.append(f"Title: {browser_info['title']}")
                
                browser_detail = "; ".join(details)
        
        writer.writerow([
            article_title,
            url,
            status_code if status_code is not None else 'CONNECTION_ERROR',
            timestamp,
            browser_result,
            browser_detail
        ])


def create_comprehensive_csv_report(dead_links: Dict[str, List[Tuple[str, Optional[int]]]], 
                                   browser_validation_results: Dict[str, Dict[str, Tuple[str, str, Optional[int], Dict]]] = None,
                                   output_dir: str = "output") -> str:
    """
    Create a comprehensive CSV report with browser validation results.
    
    Args:
        dead_links: Dictionary mapping article titles to lists of (url, status_code) tuples
        browser_validation_results: Dictionary mapping article titles to browser validation results
        output_dir: Directory to save the report (default: "output")
        
    Returns:
        Path to the generated CSV file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dead_links_comprehensive_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header with separate browser validation columns
        writer.writerow(['article_title', 'url', 'error_code', 'timestamp', 'browser_validation_check', 'browser_validation_check_detail'])
        
        # Write data for each article
        for article_title, links in dead_links.items():
            article_browser_results = browser_validation_results.get(article_title, {}) if browser_validation_results else {}
            
            for url, status_code in links:
                # Get browser validation result for this URL if available
                browser_result = "Not checked"
                browser_detail = ""
                if url in article_browser_results:
                    browser_status, browser_code, browser_info = article_browser_results[url][1:4]
                    browser_result = browser_status
                    browser_detail = ""
                    
                    if browser_info:
                        details = []
                        if browser_info.get('error_indicator'):
                            details.append(f"Error: {browser_info['error_indicator']}")
                        if browser_info.get('blocking_indicator'):
                            details.append(f"Blocked: {browser_info['blocking_indicator']}")
                        if browser_info.get('final_url') and browser_info.get('final_url') != url:
                            details.append(f"Redirected to: {browser_info['final_url']}")
                        if browser_info.get('title'):
                            details.append(f"Title: {browser_info['title']}")
                        
                        browser_detail = "; ".join(details)
                
                writer.writerow([
                    article_title,
                    url,
                    status_code if status_code is not None else 'CONNECTION_ERROR',
                    timestamp,
                    browser_result,
                    browser_detail
                ])
    
    return filepath


def write_summary_report(dead_links: Dict[str, List[Tuple[str, Optional[int]]]], 
                        browser_validation_results: Dict[str, Dict[str, Tuple[str, str, Optional[int], Dict]]] = None,
                        output_dir: str = "output") -> str:
    """
    Generate a summary report with statistics including browser validation results.
    
    Args:
        dead_links: Dictionary mapping article titles to lists of (url, status_code) tuples
        browser_validation_results: Dictionary mapping article titles to browser validation results
        output_dir: Directory to save the report (default: "output")
        
    Returns:
        Path to the generated summary file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dead_links_summary_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    # Calculate statistics
    total_articles = len(dead_links)
    total_dead_links = sum(len(links) for links in dead_links.values())
    
    # Count status codes
    status_counts = {}
    for links in dead_links.values():
        for _, status_code in links:
            status = status_code if status_code is not None else 'CONNECTION_ERROR'
            status_counts[status] = status_counts.get(status, 0) + 1
    
    # Add note about 403 status codes
    if 403 in status_counts:
        status_counts['403 (Bot Blocked)'] = status_counts.pop(403)
    
    # Calculate browser validation statistics if available
    browser_stats = {
        'total_checked': 0,
        'false_positives': 0,
        'confirmed_dead': 0,
        'blocked': 0,
        'timeout': 0,
        'error': 0
    }
    
    if browser_validation_results:
        for article_results in browser_validation_results.values():
            for browser_result in article_results.values():
                browser_status = browser_result[1]
                browser_stats['total_checked'] += 1
                if browser_status == 'alive':
                    browser_stats['false_positives'] += 1
                elif browser_status == 'blocked':
                    browser_stats['blocked'] += 1
                elif browser_status == 'timeout':
                    browser_stats['timeout'] += 1
                elif browser_status == 'error':
                    browser_stats['error'] += 1
                else:
                    browser_stats['confirmed_dead'] += 1
    
    # Write summary report
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("Wikipedia Dead Links Report Summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total articles with dead links: {total_articles}\n")
        f.write(f"Total dead links found: {total_dead_links}\n")
        
        # Count blocked links (403 status codes)
        blocked_count = sum(1 for links in dead_links.values() 
                           for _, status_code in links if status_code == 403)
        if blocked_count > 0:
            f.write(f"Note: {blocked_count} links returned 403 (likely blocking bots)\n")
        
        # Add browser validation summary if available
        if browser_validation_results and browser_stats['total_checked'] > 0:
            f.write(f"\nBrowser Validation Summary:\n")
            f.write(f"-" * 25 + "\n")
            f.write(f"Total links browser validated: {browser_stats['total_checked']}\n")
            f.write(f"False positives detected: {browser_stats['false_positives']}\n")
            f.write(f"Confirmed dead: {browser_stats['confirmed_dead']}\n")
            f.write(f"Blocked by bot protection: {browser_stats['blocked']}\n")
            f.write(f"Timeout errors: {browser_stats['timeout']}\n")
            f.write(f"Other errors: {browser_stats['error']}\n")
        
        f.write("\n")
        
        f.write("Status Code Breakdown:\n")
        f.write("-" * 20 + "\n")
        # Sort by count (descending) and then by status
        sorted_items = sorted(status_counts.items(), key=lambda x: (-x[1], str(x[0])))
        for status, count in sorted_items:
            f.write(f"{status}: {count}\n")
        
        f.write("\nArticles with Dead Links:\n")
        f.write("-" * 25 + "\n")
        for article_title, links in dead_links.items():
            f.write(f"\n{article_title} ({len(links)} dead links):\n")
            for url, status_code in links:
                status = status_code if status_code is not None else 'CONNECTION_ERROR'
                f.write(f"  - {url} (Status: {status})")
                
                # Add browser validation result if available
                if (browser_validation_results and article_title in browser_validation_results and 
                    url in browser_validation_results[article_title]):
                    browser_result = browser_validation_results[article_title][url]
                    browser_status = browser_result[1]
                    if browser_status == 'alive':
                        f.write(" [BROWSER: ALIVE - False Positive!]")
                    elif browser_status == 'blocked':
                        f.write(" [BROWSER: BLOCKED]")
                    elif browser_status == 'timeout':
                        f.write(" [BROWSER: TIMEOUT]")
                    elif browser_status == 'error':
                        f.write(" [BROWSER: ERROR]")
                    else:
                        f.write(" [BROWSER: CONFIRMED DEAD]")
                
                f.write("\n")
    
    return filepath


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


if __name__ == "__main__":
    # Test the function with sample data
    test_dead_links = {
        "Python_(programming_language)": [
            ("https://example.com/dead1", 404),
            ("https://example.com/dead2", 500)
        ],
        "JavaScript": [
            ("https://example.com/dead3", None),  # Connection error
            ("https://example.com/dead4", 403)
        ]
    }
    
    csv_file = write_report(test_dead_links)
    summary_file = write_summary_report(test_dead_links)
    
    print(f"CSV report saved to: {csv_file}")
    print(f"Summary report saved to: {summary_file}")
    
    print_report_summary(test_dead_links) 