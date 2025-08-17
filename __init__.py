"""
Wikipedia Dead Link Finder

A Python library for finding dead external links in Wikipedia articles.
"""

from .core import WikipediaDeadLinkFinder, ProcessingConfig, LinkResult, ArticleResult, ProcessingSummary
from .fetch_top_articles import get_top_articles, get_all_time_top_articles
from .fetch_article_html import get_article_html, get_article_html_batch
from .extract_references import (
    extract_external_links,
    extract_external_links_from_references,
    get_references_with_archives,
    filter_links_for_checking
)
from .check_links import (
    check_all_links_with_archives,
    check_all_links_with_archives_parallel
)
from .browser_validation import validate_dead_links_with_browser
from .utils import clean_article_title, format_duration

__version__ = "1.0.0"
__author__ = "Wikipedia Dead Link Finder Contributors"

__all__ = [
    "WikipediaDeadLinkFinder",
    "ProcessingConfig",
    "LinkResult", 
    "ArticleResult",
    "ProcessingSummary",
    "get_top_articles",
    "get_all_time_top_articles", 
    "get_article_html",
    "get_article_html_batch",
    "extract_external_links",
    "extract_external_links_from_references",
    "get_references_with_archives",
    "filter_links_for_checking",
    "check_all_links_with_archives",
    "check_all_links_with_archives_parallel",
    "validate_dead_links_with_browser",
    "clean_article_title",
    "format_duration"
]
