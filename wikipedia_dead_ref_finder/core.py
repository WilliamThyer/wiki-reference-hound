"""
Core API for Wikipedia Dead Link Finder

This module provides a high-level interface for finding dead links in Wikipedia articles.
"""

import time
import gc
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .fetch_top_articles import get_top_articles, get_all_time_top_articles
from .fetch_article_html import get_article_html_batch
from .extract_references import get_references_with_archives, filter_links_for_checking
from .check_links import check_all_links_with_archives, check_all_links_with_archives_parallel
from .browser_validation import validate_dead_links_with_browser
from .utils import clean_article_title, format_duration


@dataclass
class LinkResult:
    """Result of checking a single link."""
    url: str
    status: str  # 'alive', 'dead', 'blocked', 'archived'
    status_code: Optional[int]
    archive_urls: List[str] = None
    
    def __post_init__(self):
        if self.archive_urls is None:
            self.archive_urls = []


@dataclass
class ArticleResult:
    """Result of processing a single article."""
    title: str
    total_links: int
    dead_links: List[LinkResult]
    blocked_links: List[LinkResult]
    archived_links: List[LinkResult]
    alive_links: List[LinkResult]
    browser_validation_results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.browser_validation_results is None:
            self.browser_validation_results = {}


@dataclass
class ProcessingConfig:
    """Configuration for the dead link finding process."""
    limit: int = 25
    all_time: bool = True
    timeout: float = 5.0
    delay: float = 0.1
    parallel: bool = True
    max_workers: int = 50
    chunk_size: int = 100
    browser_validation: bool = True
    browser_timeout: int = 30
    max_browser_links: int = 50
    headless: bool = True
    references_only: bool = True
    use_html_structure: bool = True
    verbose: bool = False


@dataclass
class ProcessingSummary:
    """Summary of the entire processing run."""
    total_articles: int
    total_links_checked: int
    total_dead_links: int
    total_blocked_links: int
    total_archived_links: int
    total_alive_links: int
    processing_time: float
    memory_usage_mb: float
    timestamp: datetime


class WikipediaDeadLinkFinder:
    """
    High-level API for finding dead links in Wikipedia articles.
    
    This class orchestrates the entire workflow of fetching articles,
    extracting links, checking their status, and optionally validating
    with browser automation.
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize the dead link finder.
        
        Args:
            config: Configuration object. If None, uses default settings.
        """
        self.config = config or ProcessingConfig()
        self.results: Dict[str, ArticleResult] = {}
        self.summary: Optional[ProcessingSummary] = None
        
    def find_dead_links(self, article_titles: Optional[List[str]] = None) -> Dict[str, ArticleResult]:
        """
        Find dead links in Wikipedia articles.
        
        Args:
            article_titles: List of article titles to check. If None, fetches top articles.
            
        Returns:
            Dictionary mapping article titles to ArticleResult objects.
        """
        start_time = time.time()
        
        # Step 1: Get articles to process
        if article_titles is None:
            if self.config.all_time:
                articles = get_all_time_top_articles(limit=self.config.limit, verbose=self.config.verbose)
            else:
                articles = get_top_articles(limit=self.config.limit, verbose=self.config.verbose)
        else:
            articles = article_titles[:self.config.limit]
            
        if not articles:
            if self.config.verbose:
                print("❌ No articles to process.")
            return {}
            
        if self.config.verbose:
            print(f"📰 Processing {len(articles)} articles...")
            
        # Step 2: Process articles in batches
        self._process_articles_in_batches(articles)
        
        # Step 3: Generate summary
        end_time = time.time()
        processing_time = end_time - start_time
        
        self.summary = self._create_summary(processing_time)
        
        if self.config.verbose:
            self._print_summary()
            
        return self.results
    
    def _process_articles_in_batches(self, articles: List[str]):
        """Process articles in memory-efficient batches."""
        chunk_size = 50  # Process 50 articles at a time
        
        for chunk_start in range(0, len(articles), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(articles))
            chunk_articles = articles[chunk_start:chunk_end]
            
            if self.config.verbose:
                print(f"📦 Processing batch {chunk_start//chunk_size + 1}/{(len(articles)-1)//chunk_size + 1}")
            
            # Fetch HTML for this chunk
            html_batch = get_article_html_batch(
                chunk_articles, 
                delay=self.config.delay, 
                verbose=self.config.verbose
            )
            
            if not html_batch:
                continue
                
            # Process each article in the chunk
            for title in chunk_articles:
                html = html_batch.get(title, "")
                if not html:
                    continue
                    
                self._process_single_article(title, html)
            
            # Clear chunk data to free memory
            del html_batch
            gc.collect()
            
            # Add delay between chunks
            if chunk_end < len(articles):
                time.sleep(self.config.delay)
    
    def _process_single_article(self, title: str, html: str):
        """Process a single article and store results."""
        clean_title = clean_article_title(title)
        
        if self.config.verbose:
            print(f"   🔍 Processing: {clean_title}")
        
        # Extract references with archives
        if self.config.use_html_structure:
            references_with_archives = get_references_with_archives(html)
            
            # Convert to the format expected by link checking
            article_links = []
            archive_groups = {}
            
            for ref in references_with_archives:
                if ref['original_url']:
                    article_links.append(ref['original_url'])
                    if ref['archive_url']:
                        if ref['original_url'] not in archive_groups:
                            archive_groups[ref['original_url']] = []
                        archive_groups[ref['original_url']].append(ref['archive_url'])
        else:
            # Use traditional method
            if self.config.references_only:
                from .extract_references import extract_external_links_from_references
                article_links = extract_external_links_from_references(html)
            else:
                from .extract_references import extract_external_links
                article_links = extract_external_links(html)
            
            # Filter links for checking
            links_to_check, archive_groups = filter_links_for_checking(article_links)
            article_links = links_to_check
        
        if not article_links:
            if self.config.verbose:
                print(f"      ℹ️  No external links found")
            return
        
        # Check link status
        if self.config.parallel:
            link_results = check_all_links_with_archives_parallel(
                article_links, 
                archive_groups, 
                timeout=self.config.timeout, 
                max_workers=self.config.max_workers
            )
        else:
            link_results = check_all_links_with_archives(
                article_links, 
                archive_groups, 
                timeout=self.config.timeout, 
                delay=self.config.delay
            )
        
        # Browser validation if enabled
        browser_results = {}
        if self.config.browser_validation:
            dead_for_browser = [(url, status, code) for url, status, code in link_results if status == 'dead']
            
            if dead_for_browser and len(dead_for_browser) <= self.config.max_browser_links:
                if self.config.verbose:
                    print(f"      🔍 Browser validating {len(dead_for_browser)} dead links...")
                
                browser_results_raw = validate_dead_links_with_browser(
                    dead_for_browser,
                    headless=self.config.headless,
                    timeout=self.config.browser_timeout
                )
                
                # Convert to dictionary format
                for result in browser_results_raw:
                    url, status, code, info = result
                    browser_results[url] = {
                        'status': status,
                        'code': code,
                        'info': info
                    }
        
        # Organize results by status
        dead_links = []
        blocked_links = []
        archived_links = []
        alive_links = []
        
        for url, status, code in link_results:
            archive_urls = archive_groups.get(url, [])
            link_result = LinkResult(url=url, status=status, status_code=code, archive_urls=archive_urls)
            
            if status == 'dead':
                dead_links.append(link_result)
            elif status == 'blocked':
                blocked_links.append(link_result)
            elif status == 'archived':
                archived_links.append(link_result)
            else:  # alive
                alive_links.append(link_result)
        
        # Create article result
        article_result = ArticleResult(
            title=clean_title,
            total_links=len(article_links),
            dead_links=dead_links,
            blocked_links=blocked_links,
            archived_links=archived_links,
            alive_links=alive_links,
            browser_validation_results=browser_results
        )
        
        self.results[clean_title] = article_result
        
        if self.config.verbose:
            print(f"      📎 Found {len(article_links)} total links")
            print(f"      ❌ {len(dead_links)} dead, 🚫 {len(blocked_links)} blocked")
            print(f"      📦 {len(archived_links)} archived, ✅ {len(alive_links)} alive")
    
    def _create_summary(self, processing_time: float) -> ProcessingSummary:
        """Create a summary of the processing run."""
        total_articles = len(self.results)
        total_links_checked = sum(result.total_links for result in self.results.values())
        total_dead_links = sum(len(result.dead_links) for result in self.results.values())
        total_blocked_links = sum(len(result.blocked_links) for result in self.results.values())
        total_archived_links = sum(len(result.archived_links) for result in self.results.values())
        total_alive_links = sum(len(result.alive_links) for result in self.results.values())
        
        # Get memory usage
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024
        except:
            memory_usage = 0
        
        return ProcessingSummary(
            total_articles=total_articles,
            total_links_checked=total_links_checked,
            total_dead_links=total_dead_links,
            total_blocked_links=total_blocked_links,
            total_archived_links=total_archived_links,
            total_alive_links=total_alive_links,
            processing_time=processing_time,
            memory_usage_mb=memory_usage,
            timestamp=datetime.now()
        )
    
    def _print_summary(self):
        """Print a summary of the processing run."""
        if not self.summary:
            return
            
        print("\n🎯 Processing Summary")
        print("=" * 30)
        print(f"📰 Articles processed: {self.summary.total_articles}")
        print(f"🔗 Total links checked: {self.summary.total_links_checked}")
        print(f"❌ Total dead links: {self.summary.total_dead_links}")
        print(f"🚫 Total blocked links: {self.summary.total_blocked_links}")
        print(f"📦 Total archived links: {self.summary.total_archived_links}")
        print(f"✅ Total alive links: {self.summary.total_alive_links}")
        print(f"⏱️  Processing time: {format_duration(self.summary.processing_time)}")
        print(f"💾 Memory usage: {self.summary.memory_usage_mb:.1f} MB")
    
    def get_dead_links_only(self) -> Dict[str, List[LinkResult]]:
        """Get only articles that have dead links."""
        return {
            title: result.dead_links 
            for title, result in self.results.items() 
            if result.dead_links
        }
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics as a dictionary."""
        if not self.summary:
            return {}
            
        return {
            'total_articles': self.summary.total_articles,
            'total_links_checked': self.summary.total_links_checked,
            'total_dead_links': self.summary.total_dead_links,
            'total_blocked_links': self.summary.total_blocked_links,
            'total_archived_links': self.summary.total_archived_links,
            'total_alive_links': self.summary.total_alive_links,
            'processing_time_seconds': self.summary.processing_time,
            'memory_usage_mb': self.summary.memory_usage_mb,
            'timestamp': self.summary.timestamp.isoformat()
        }
    
    def export_to_csv(self, output_dir: str = "output") -> str:
        """
        Export results to CSV format.
        
        Args:
            output_dir: Directory to save the CSV file
            
        Returns:
            Path to the generated CSV file
        """
        from .generate_report import create_all_references_csv_report
        
        # Convert our results to the format expected by the CSV generator
        all_links = {title: [link.url for link in result.dead_links + result.blocked_links + result.alive_links] 
                    for title, result in self.results.items()}
        
        archive_groups = {}
        for title, result in self.results.items():
            archive_groups[title] = {}
            for link in result.dead_links + result.blocked_links + result.alive_links:
                if link.archive_urls:
                    archive_groups[title][link.url] = link.archive_urls
        
        # Convert link results to the expected format
        all_link_results = {}
        for title, result in self.results.items():
            all_link_results[title] = [(link.url, link.status, link.status_code) 
                                     for link in result.dead_links + result.blocked_links + result.alive_links]
        
        # Convert browser results to the expected format
        browser_results = {}
        for title, result in self.results.items():
            browser_results[title] = {}
            for url, info in result.browser_validation_results.items():
                browser_results[title][url] = (url, info['status'], info['code'], info['info'])
        
        return create_all_references_csv_report(
            all_links,
            archive_groups,
            all_link_results,
            browser_results,
            output_dir,
            verbose=self.config.verbose
        )
