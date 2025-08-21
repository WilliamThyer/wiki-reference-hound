#!/usr/bin/env python3
"""
Wikipedia Popular Articles Extractor

Extracts article names from the Wikipedia:Popular_pages page using the REST API.
This script parses the page content to find article links and extracts their titles.
"""

import requests
import re
import json
from typing import List, Dict, Optional
from urllib.parse import unquote, urlparse
import time


def get_page_content(page_title: str, verbose: bool = False) -> Optional[str]:
    """
    Fetch the HTML content of a Wikipedia page using the REST API.
    
    Args:
        page_title: The title of the page to fetch
        verbose: Enable verbose output
        
    Returns:
        HTML content as string, or None if failed
    """
    # Use the REST API endpoint for HTML content
    url = f"https://en.wikipedia.org/api/rest_v1/page/html/{page_title}"
    
    headers = {
        'User-Agent': 'Wikipedia-Popular-Articles-Extractor/1.0 (https://github.com/thyer/wikipedia-dead-ref-finder; thyer@example.com)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }
    
    try:
        if verbose:
            print(f"📥 Fetching content for: {page_title}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        if verbose:
            print(f"✅ Successfully fetched {len(content)} characters")
        
        return content
        
    except requests.RequestException as e:
        if verbose:
            print(f"❌ Error fetching page: {e}")
        return None


def extract_article_links(html_content: str, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Extract article links from HTML content.
    
    Args:
        html_content: HTML content from Wikipedia page
        verbose: Enable verbose output
        
    Returns:
        List of dictionaries with article information
    """
    articles = []
    
    # Pattern to match Wikipedia article links
    # The REST API returns relative URLs like ./Article_Name or ./Category:Name
    link_pattern = r'<a[^>]*href="\./([^"#]+)(?:#[^"]*)?"[^>]*>([^<]+)</a>'
    
    # Find all matches
    matches = re.findall(link_pattern, html_content)
    
    if verbose:
        print(f"🔍 Found {len(matches)} potential article links")
    
    # Process matches
    seen_articles = set()
    for href, link_text in matches:
        # Skip special pages, user pages, and other non-article content
        if (href.startswith('Special:') or 
            href.startswith('User:') or 
            href.startswith('Talk:') or 
            href.startswith('Wikipedia:') or
            href.startswith('File:') or
            href.startswith('Category:') or
            href.startswith('Template:') or
            href.startswith('Help:') or
            href.startswith('Portal:') or
            href.startswith('MediaWiki:') or
            href.startswith('Module:') or
            href.startswith('Project:') or
            href.startswith('Media:') or
            href.startswith('Talk:') or
            href.startswith('User_talk:') or
            href.startswith('Wikipedia_talk:') or
            href.startswith('File_talk:') or
            href.startswith('Category_talk:') or
            href.startswith('Template_talk:') or
            href.startswith('Help_talk:') or
            href.startswith('Portal_talk:') or
            href.startswith('MediaWiki_talk:') or
            href.startswith('Module_talk:') or
            href.startswith('Project_talk:') or
            href.startswith('Media_talk:') or
            href == 'Main_Page'):
            continue
        
        # Decode URL-encoded characters
        clean_title = unquote(href)
        
        # Skip if we've already seen this article
        if clean_title in seen_articles:
            continue
        
        seen_articles.add(clean_title)
        
        # Clean up the link text (remove HTML entities, extra whitespace)
        clean_text = re.sub(r'&[^;]+;', '', link_text).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        if clean_text and len(clean_text) > 1:
            articles.append({
                'title': clean_title,
                'display_text': clean_text,
                'url': f"https://en.wikipedia.org/wiki/{clean_title}"
            })
    
    if verbose:
        print(f"✅ Extracted {len(articles)} unique article links")
    
    return articles


def save_results(articles: List[Dict[str, str]], filename: str = 'popular_articles.json', verbose: bool = False):
    """
    Save extracted articles to a JSON file.
    
    Args:
        articles: List of article dictionaries
        filename: Output filename
        verbose: Enable verbose output
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"💾 Saved {len(articles)} articles to {filename}")
    
    except Exception as e:
        if verbose:
            print(f"❌ Error saving file: {e}")


def main():
    """Main function to extract popular articles."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract article names from Wikipedia:Popular_pages')
    parser.add_argument('--output', '-o', type=str, default='popular_articles.json',
                       help='Output JSON file (default: popular_articles.json)')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Maximum number of articles to extract (0 = no limit, default: 0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        print("🔍 Wikipedia Popular Articles Extractor")
        print("=" * 40)
        print(f"📄 Source: Wikipedia:Popular_pages")
        print(f"📁 Output: {args.output}")
        if args.limit > 0:
            print(f"🔢 Limit: {args.limit}")
        else:
            print(f"🔢 Limit: No limit (extract all)")
        print()
    
    # Fetch the Popular Pages content
    page_title = "Wikipedia:Popular_pages"
    html_content = get_page_content(page_title, verbose=args.verbose)
    
    if not html_content:
        print("❌ Failed to fetch page content. Exiting.")
        return
    
    # Extract article links
    articles = extract_article_links(html_content, verbose=args.verbose)
    
    if not articles:
        print("❌ No articles found. Exiting.")
        return
    
    # Apply limit if specified
    if args.limit > 0:
        articles = articles[:args.limit]
        if args.verbose:
            print(f"📊 Limited to {len(articles)} articles")
    
    if args.verbose:
        print(f"\n📋 Final Results:")
        print(f"   Total articles extracted: {len(articles)}")
    
    # Save results
    save_results(articles, args.output, verbose=args.verbose)
    
    # Print sample of results
    if args.verbose:
        print(f"\n📚 Sample Articles:")
        for i, article in enumerate(articles[:10], 1):
            print(f"   {i:2d}. {article['title']}")
            print(f"       Display: {article['display_text']}")
            print(f"       URL: {article['url']}")
            print()
    
    print(f"✅ Extraction complete! Found {len(articles)} articles.")
    print(f"📁 Results saved to: {args.output}")


if __name__ == "__main__":
    main()
