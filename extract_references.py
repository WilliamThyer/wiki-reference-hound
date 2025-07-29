from bs4 import BeautifulSoup
from typing import List, Set, Dict, Tuple
import re


def is_archive_url(url: str) -> bool:
    """
    Check if a URL is an archive link (web.archive.org, archive.today, etc.).
    
    Args:
        url: URL to check
        
    Returns:
        True if the URL is an archive link
    """
    archive_domains = [
        'web.archive.org',
        'archive.today',
        'archive.org',
        'archive.is',
        'archive.fo',
        'archive.md',
        'archive.ph',
        'archive.li',
        'archive.vn',
        'archive.today',
        'webcitation.org',
        'wayback.archive.org'
    ]
    
    for domain in archive_domains:
        if domain in url:
            return True
    
    return False


def extract_original_url_from_archive(archive_url: str) -> str:
    """
    Extract the original URL from an archive link.
    
    Args:
        archive_url: Archive URL
        
    Returns:
        Original URL if found, empty string otherwise
    """
    # Handle web.archive.org URLs
    if 'web.archive.org' in archive_url:
        # Pattern: https://web.archive.org/web/TIMESTAMP/ORIGINAL_URL
        match = re.search(r'https://web\.archive\.org/web/\d+/(.+)', archive_url)
        if match:
            return match.group(1)
    
    # Handle archive.today URLs
    elif 'archive.today' in archive_url or 'archive.is' in archive_url:
        # These often have the original URL as a parameter or in the path
        # This is more complex and may require actual page scraping
        # For now, return empty string
        return ""
    
    return ""


def group_links_with_archives(links: List[str]) -> Dict[str, List[str]]:
    """
    Group links by their original URL, identifying archive versions.
    
    Args:
        links: List of URLs
        
    Returns:
        Dictionary mapping original URLs to list of archive URLs
    """
    link_groups = {}
    
    for link in links:
        if is_archive_url(link):
            original = extract_original_url_from_archive(link)
            if original:
                if original not in link_groups:
                    link_groups[original] = []
                link_groups[original].append(link)
        else:
            # This is an original link
            if link not in link_groups:
                link_groups[link] = []
    
    return link_groups


def filter_links_for_checking(links: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Filter links for checking, removing archive links and grouping with originals.
    
    Args:
        links: List of all URLs found
        
    Returns:
        Tuple of (links_to_check, archive_groups)
    """
    # Group links by original URL
    link_groups = group_links_with_archives(links)
    
    # Only check original links (non-archive)
    links_to_check = [url for url in link_groups.keys() if not is_archive_url(url)]
    
    return links_to_check, link_groups


def extract_external_links(html: str) -> List[str]:
    """
    Extract external links from Wikipedia article HTML content.
    
    Args:
        html: Raw HTML content of the Wikipedia article
        
    Returns:
        List of external URLs found in references
    """
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    external_links = set()
    
    # Method 1: Look for <ref> tags and extract external links from them
    ref_tags = soup.find_all('ref')
    for ref in ref_tags:
        # Find all <a> tags within the ref
        links = ref.find_all('a', href=True)
        for link in links:
            href = link['href']
            if is_external_url(href):
                external_links.add(href)
    
    # Method 2: Look for the References section and extract links
    # Find the References section
    ref_section = None
    
    # Look for various ways the References section might be marked
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        if heading.get_text().strip().lower() in ['references', 'notes', 'external links']:
            ref_section = heading
            break
    
    if ref_section:
        # Find all <a> tags in the References section
        links = ref_section.find_next_siblings()
        for element in links:
            # Stop if we hit another heading
            if element.name in ['h2', 'h3', 'h4']:
                break
            
            # Find all <a> tags in this element
            for link in element.find_all('a', href=True):
                href = link['href']
                if is_external_url(href):
                    external_links.add(href)
    
    # Method 3: Look for external links in the entire document
    # This is a fallback to catch any external links we might have missed
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link['href']
        if is_external_url(href):
            # Only add if it looks like a reference link (not navigation, etc.)
            if is_likely_reference_link(link):
                external_links.add(href)
    
    return list(external_links)


def is_external_url(url: str) -> bool:
    """
    Check if a URL is external (starts with http or https).
    
    Args:
        url: URL to check
        
    Returns:
        True if the URL is external
    """
    return url.startswith(('http://', 'https://'))


def is_likely_reference_link(link_element) -> bool:
    """
    Check if a link element is likely to be a reference link.
    
    Args:
        link_element: BeautifulSoup link element
        
    Returns:
        True if the link is likely a reference
    """
    # Skip navigation links, edit links, etc.
    skip_classes = ['mw-editsection', 'mw-editsection-bracket', 'mw-redirect']
    skip_ids = ['mw-content-text']
    
    # Check if the link has any of the skip classes
    if link_element.get('class'):
        for skip_class in skip_classes:
            if skip_class in link_element.get('class', []):
                return False
    
    # Check if the link has any of the skip IDs
    if link_element.get('id'):
        for skip_id in skip_ids:
            if skip_id in link_element.get('id', ''):
                return False
    
    # Skip links that are clearly not references
    href = link_element.get('href', '')
    skip_patterns = [
        r'^#',  # Internal anchors
        r'^/wiki/',  # Internal Wikipedia links
        r'^/w/',  # Wikipedia internal links
        r'^/wiki/Special:',  # Special pages
        r'^/wiki/Help:',  # Help pages
        r'^/wiki/Wikipedia:',  # Wikipedia namespace
        r'^/wiki/Template:',  # Template pages
        r'^/wiki/File:',  # File pages
        r'^/wiki/Category:',  # Category pages
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, href):
            return False
    
    return True


def extract_all_links(html: str) -> List[str]:
    """
    Extract ALL external links from the HTML (for debugging purposes).
    
    Args:
        html: Raw HTML content
        
    Returns:
        List of all external URLs found
    """
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    external_links = set()
    
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link['href']
        if is_external_url(href):
            external_links.add(href)
    
    return list(external_links)


if __name__ == "__main__":
    # Test with a sample HTML
    test_html = """
    <div>
        <ref>
            <a href="https://example.com">Example</a>
        </ref>
        <h2>References</h2>
        <ul>
            <li><a href="https://test.com">Test</a></li>
            <li><a href="/wiki/Internal">Internal</a></li>
        </ul>
    </div>
    """
    
    links = extract_external_links(test_html)
    print("Extracted external links:")
    for link in links:
        print(f"  - {link}") 