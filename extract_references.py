from bs4 import BeautifulSoup
from typing import List, Set, Dict, Tuple
import re


def normalize_url_for_comparison(url: str) -> str:
    """
    Normalize a URL for comparison purposes.
    Treats HTTP and HTTPS versions of the same domain as equivalent.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL string
    """
    # Remove protocol for comparison
    if url.startswith('https://'):
        return url[8:]  # Remove 'https://'
    elif url.startswith('http://'):
        return url[7:]   # Remove 'http://'
    return url


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs point to the same domain, ignoring protocol.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if URLs point to the same domain
    """
    normalized1 = normalize_url_for_comparison(url1)
    normalized2 = normalize_url_for_comparison(url2)
    
    # Extract domain part (everything before the first slash)
    domain1 = normalized1.split('/')[0] if '/' in normalized1 else normalized1
    domain2 = normalized2.split('/')[0] if '/' in normalized2 else normalized2
    
    return domain1 == domain2


def find_best_original_url(urls: List[str], preferred_protocol: str = 'https') -> str:
    """
    Find the best original URL from a list of URLs, preferring HTTPS over HTTP.
    
    Args:
        urls: List of URLs to choose from
        preferred_protocol: Preferred protocol ('https' or 'http')
        
    Returns:
        Best URL to use as the original
    """
    if not urls:
        return ""
    
    # Filter out archive URLs
    original_urls = [url for url in urls if not is_archive_url(url)]
    
    if not original_urls:
        return ""
    
    # If only one original URL, return it
    if len(original_urls) == 1:
        return original_urls[0]
    
    # Prefer HTTPS over HTTP
    https_urls = [url for url in original_urls if url.startswith('https://')]
    http_urls = [url for url in original_urls if url.startswith('http://')]
    
    if preferred_protocol == 'https' and https_urls:
        return https_urls[0]
    elif http_urls:
        return http_urls[0]
    elif https_urls:
        return https_urls[0]
    
    # Fallback to first URL
    return original_urls[0]


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
    
    # Handle archive.today URLs (these are more complex and may require page scraping)
    elif 'archive.today' in archive_url or 'archive.is' in archive_url or 'archive.fo' in archive_url:
        # These services often have the original URL in the path or as a parameter
        # For now, we'll try to extract from common patterns
        # Pattern: https://archive.today/ORIGINAL_URL or https://archive.today/ORIGINAL_URL
        # Note: This is a simplified approach and may not work for all cases
        
        # Try to extract from path
        parsed = archive_url.split('/', 3)  # Split into max 4 parts
        if len(parsed) >= 4:
            potential_original = parsed[3]
            # Check if it looks like a valid URL
            if potential_original and '.' in potential_original:
                return potential_original
        
        # For now, return empty string as these are complex to parse reliably
        return ""
    
    # Handle archive.md, archive.ph, archive.li, archive.vn
    elif any(domain in archive_url for domain in ['archive.md', 'archive.ph', 'archive.li', 'archive.vn']):
        # These services have similar patterns to archive.today
        # For now, return empty string as they require more complex parsing
        return ""
    
    # Handle webcitation.org
    elif 'webcitation.org' in archive_url:
        # Pattern: https://webcitation.org/QUERY_ID/ORIGINAL_URL
        match = re.search(r'https://webcitation\.org/[^/]+/(.+)', archive_url)
        if match:
            return match.group(1)
    
    # Handle wayback.archive.org (alternative web.archive.org domain)
    elif 'wayback.archive.org' in archive_url:
        # Pattern: https://wayback.archive.org/web/TIMESTAMP/ORIGINAL_URL
        match = re.search(r'https://wayback\.archive\.org/web/\d+/(.+)', archive_url)
        if match:
            return match.group(1)
    
    return ""


def is_valid_archive_match(original_url: str, archive_url: str) -> bool:
    """
    Validate that an archive URL is actually an archive of the given original URL.
    
    Args:
        original_url: The original URL
        archive_url: The archive URL to validate
        
    Returns:
        True if the archive URL appears to be a valid archive of the original
    """
    if not original_url or not archive_url:
        return False
    
    # Extract original URL from archive
    extracted_original = extract_original_url_from_archive(archive_url)
    if not extracted_original:
        return False
    
    # Normalize both URLs for comparison
    normalized_original = normalize_url_for_comparison(original_url)
    normalized_extracted = normalize_url_for_comparison(extracted_original)
    
    # Check if they match
    return normalized_original == normalized_extracted


def group_links_with_archives(links: List[str]) -> Dict[str, List[str]]:
    """
    Group links by their normalized URL, identifying archive versions.
    
    Args:
        links: List of URLs
        
    Returns:
        Dictionary mapping normalized original URLs to list of archive URLs
    """
    link_groups = {}
    
    for link in links:
        if is_archive_url(link):
            original = extract_original_url_from_archive(link)
            if original:
                # Normalize the original URL for grouping
                normalized_original = normalize_url_for_comparison(original)
                if normalized_original not in link_groups:
                    link_groups[normalized_original] = []
                link_groups[normalized_original].append(link)
        else:
            # This is an original link - normalize it for grouping
            normalized = normalize_url_for_comparison(link)
            if normalized not in link_groups:
                link_groups[normalized] = []
    
    # Validate archive matches and clean up any invalid ones
    validated_groups = {}
    for normalized_url, archives in link_groups.items():
        # Find the original URL that corresponds to this normalized version
        original_urls = [url for url in links if not is_archive_url(url) and normalize_url_for_comparison(url) == normalized_url]
        
        if original_urls:
            # Validate each archive against the original URLs
            valid_archives = []
            for archive in archives:
                for original in original_urls:
                    if is_valid_archive_match(original, archive):
                        valid_archives.append(archive)
                        break
            
            if valid_archives:
                validated_groups[normalized_url] = valid_archives
    
    return validated_groups


def filter_links_for_checking(links: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Filter links for checking, removing archive links and grouping with originals.
    
    Args:
        links: List of all URLs found
        
    Returns:
        Tuple of (links_to_check, archive_groups)
    """
    # Group links by normalized original URL
    link_groups = group_links_with_archives(links)
    
    # For each normalized group, choose the best original URL to check
    links_to_check = []
    final_archive_groups = {}
    
    for normalized_url, archives in link_groups.items():
        # Find all URLs that match this normalized version
        matching_urls = []
        for link in links:
            if not is_archive_url(link):
                normalized_link = normalize_url_for_comparison(link)
                if normalized_link == normalized_url:
                    matching_urls.append(link)
        
        # Find the best original URL to represent this group
        best_original = find_best_original_url(matching_urls, preferred_protocol='https')
        
        if best_original:
            links_to_check.append(best_original)
            final_archive_groups[best_original] = archives
    
    return links_to_check, final_archive_groups


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