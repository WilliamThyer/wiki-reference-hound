from bs4 import BeautifulSoup
from typing import List, Set, Dict, Tuple, Optional
import re
from .fetch_article_html import get_article_html


def normalize_url_for_comparison(url: str) -> str:
    """
    Normalize a URL for comparison purposes.
    Treats HTTP and HTTPS versions of the same domain as equivalent.
    Also treats www and non-www versions of the same domain as equivalent.
    Handles common domain variations like .com/.co.uk/.org variations.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL string
    """
    # Remove protocol for comparison
    if url.startswith('https://'):
        url = url[8:]  # Remove 'https://'
    elif url.startswith('http://'):
        url = url[7:]   # Remove 'http://'
    
    # Remove 'www.' prefix for comparison (treats www.domain.com and domain.com as equivalent)
    if url.startswith('www.'):
        url = url[4:]  # Remove 'www.'
    
    # Handle common domain variations
    # Extract domain part (everything before the first slash)
    domain_part = url.split('/')[0] if '/' in url else url
    
    # Common domain variations mapping
    domain_variations = {
        '.co.uk': '.com',      # UK sites often have .com equivalents
        '.co.za': '.com',      # South African sites
        '.co.au': '.com',      # Australian sites
        '.co.nz': '.com',      # New Zealand sites
        '.co.in': '.com',      # Indian sites
        '.co.jp': '.com',      # Japanese sites
        '.co.kr': '.com',      # Korean sites
        '.co.il': '.com',      # Israeli sites
        '.com.au': '.com',     # Australian sites
        '.com.br': '.com',     # Brazilian sites
        '.com.mx': '.com',     # Mexican sites
        '.com.sg': '.com',     # Singapore sites
        '.com.hk': '.com',     # Hong Kong sites
        '.com.tw': '.com',     # Taiwanese sites
        '.com.my': '.com',     # Malaysian sites
        '.com.ph': '.com',     # Philippine sites
        '.com.vn': '.com',     # Vietnamese sites
        '.com.th': '.com',     # Thai sites
        '.com.id': '.com',     # Indonesian sites
    }
    
    # Apply domain variations
    for old_suffix, new_suffix in domain_variations.items():
        if domain_part.endswith(old_suffix):
            domain_part = domain_part[:-len(old_suffix)] + new_suffix
            # Reconstruct the URL with the modified domain
            if '/' in url:
                url = domain_part + '/' + '/'.join(url.split('/')[1:])
            else:
                url = domain_part
            break
    
    return url


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs point to the same domain, ignoring protocol and common variations.
    
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


def is_url_equivalent(url1: str, url2: str) -> bool:
    """
    Check if two URLs are equivalent, considering domain variations and path similarities.
    """
    if not url1 or not url2:
        return False

    # Normalize protocol differences and strip trailing slashes for robust comparison
    def _basic_normalize(u: str) -> str:
        u = u.strip()
        if u.startswith("https://"):
            u = u[8:]
        elif u.startswith("http://"):
            u = u[7:]
        u = u.lower().rstrip("/")
        return u

    if _basic_normalize(url1) == _basic_normalize(url2):
        return True

    # Original logic for more complex path/domain matching
    if normalize_url_for_comparison(url1) == normalize_url_for_comparison(url2):
        return True
    
    if is_same_domain(url1, url2):
        path1 = url1.split('/', 3)[-1] if len(url1.split('/', 3)) > 3 else ""
        path2 = url2.split('/', 3)[-1] if len(url2.split('/', 3)) > 3 else ""
        if path1 == path2:
            return True
        if path1 and path2 and (path1 in path2 or path2 in path1):
            return True

    return False


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
        'webcitation.org',
        'wayback.archive.org',
        'ghostarchive.org'  # Added missing archive service
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
        # Handle both HTTP and HTTPS protocols
        match = re.search(r'https?://web\.archive\.org/web/\d+/(.+)', archive_url)
        if match:
            return match.group(1)
    
    # Handle ghostarchive.org URLs
    elif 'ghostarchive.org' in archive_url:
        # Pattern: https://ghostarchive.org/archive/TIMESTAMP/ORIGINAL_URL
        match = re.search(r'https://ghostarchive\.org/archive/\d+/(.+)', archive_url)
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
    
    # Use the new URL equivalence function for better matching
    return is_url_equivalent(original_url, extracted_original)


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
                # Find the best matching original link from our list
                best_original = None
                for orig_link in links:
                    if not is_archive_url(orig_link) and is_url_equivalent(orig_link, original):
                        best_original = orig_link
                        break
                
                if best_original:
                    # Use the actual original URL as the key
                    if best_original not in link_groups:
                        link_groups[best_original] = []
                    link_groups[best_original].append(link)
        else:
            # This is an original link - ensure it's in the groups
            if link not in link_groups:
                link_groups[link] = []
    
    # Validate archive matches and clean up any invalid ones
    validated_groups = {}
    for original_url, archives in link_groups.items():
        # Validate each archive against the original URL
        valid_archives = []
        for archive in archives:
            if is_valid_archive_match(original_url, archive):
                valid_archives.append(archive)
        
        if valid_archives:
            validated_groups[original_url] = valid_archives
    
    return validated_groups


def filter_links_for_checking(links: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Filter links for checking, separating original links with and without archives.
    
    Args:
        links: List of all URLs found (mixture of original and archive links)
        
    Returns:
        Tuple of (links_to_check, links_with_archives)
        - links_to_check: original links with no matching archive link
        - links_with_archives: original links that have archives, with key=original link and value=list of archives
    """
    # Separate original links and archive links
    original_links = [link for link in links if not is_archive_url(link)]
    archive_links = [link for link in links if is_archive_url(link)]
    
    # Group archives by their original URL
    archives_by_original = {}
    for archive_url in archive_links:
        original_url = extract_original_url_from_archive(archive_url)
        if original_url:
            # Find the best matching original link from our list
            best_original = None
            for orig_link in original_links:
                if is_url_equivalent(orig_link, original_url):
                    best_original = orig_link
                    break
            
            if best_original:
                if best_original not in archives_by_original:
                    archives_by_original[best_original] = []
                archives_by_original[best_original].append(archive_url)
    
    # Separate links into two categories
    links_with_archives = {}
    links_to_check = []
    
    for link in original_links:
        if link in archives_by_original:
            # This link has archives
            links_with_archives[link] = archives_by_original[link]
        else:
            # This link has no archives, so it needs to be checked
            links_to_check.append(link)
    
    return links_to_check, links_with_archives


def get_wikipedia_references(title: str) -> List[str]:
    """
    Fetch the references (citations) from a Wikipedia article.

    Args:
        title: The title of the Wikipedia article

    Returns:
        A list of HTML strings, each representing one reference
    """
    html = get_article_html(title)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Find all reference list containers
    references_ol = soup.find_all("ol", class_="references")

    all_refs = []
    for ol in references_ol:
        for li in ol.find_all("li", recursive=False):
            all_refs.append(str(li))

    return all_refs


def get_wikipedia_references_from_html(html: str) -> List[str]:
    """
    Extract the references (citations) from Wikipedia article HTML content.
    This function specifically targets only the references section.

    Args:
        html: Raw HTML content of the Wikipedia article

    Returns:
        A list of HTML strings, each representing one reference
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    all_refs = []

    # Find all reference list containers
    references_ol = soup.find_all("ol", class_="references")

    for ol in references_ol:
        for li in ol.find_all("li", recursive=False):
            all_refs.append(str(li))

    return all_refs


def extract_external_links(html: str) -> List[str]:
    """
    Extract external links from Wikipedia article HTML content.
    This function now specifically targets only the references section for more accurate results.
    
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


def extract_external_links_from_references(html: str) -> List[str]:
    """
    Extract external links ONLY from the references section of a Wikipedia article.
    This provides a more focused approach than extract_external_links.
    
    Args:
        html: Raw HTML content of the Wikipedia article
        
    Returns:
        List of external URLs found only in the references section
    """
    if not html:
        return []
    
    # Use the new HTML structure-based approach
    references_with_archives = extract_references_with_archives(html)
    
    # Extract all unique URLs (both original and archive)
    external_links = set()
    for ref in references_with_archives:
        if ref['original_url']:
            external_links.add(ref['original_url'])
        if ref['archive_url']:
            external_links.add(ref['archive_url'])
    
    return list(external_links)


def get_references_with_archives(html: str) -> List[Dict[str, str]]:
    """
    Get references with their archives using HTML structure analysis.
    This is the main function to use when you want to preserve the relationship
    between original URLs and their archive URLs.
    
    Args:
        html: Raw HTML content of the Wikipedia article
        
    Returns:
        List of dictionaries, each containing:
        - 'original_url': The original external URL
        - 'archive_url': The archive URL if found, empty string otherwise
        - 'reference_html': The full HTML of the reference for debugging
    """
    return extract_references_with_archives(html)


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


def extract_references_with_archives(html: str) -> List[Dict[str, str]]:
    """
    Extract references with their archives using HTML structure.
    This function analyzes the HTML structure of each reference to properly associate
    original URLs with their archive URLs that appear in the same reference.
    
    Args:
        html: Raw HTML content of the Wikipedia article
        
    Returns:
        List of dictionaries, each containing:
        - 'original_url': The original external URL
        - 'archive_url': The archive URL if found, empty string otherwise
        - 'reference_html': The full HTML of the reference for debugging
    """
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    references_with_archives = []
    
    # Find all reference list containers (ol with class="references")
    references_ol = soup.find_all("ol", class_="references")
    
    for ol in references_ol:
        # Extract all <li> elements from each reference list
        for li in ol.find_all("li", recursive=False):
            reference_data = extract_single_reference_with_archives(li)
            if reference_data:
                references_with_archives.extend(reference_data)
    
    # Also look for <ref> tags that might contain external links
    ref_tags = soup.find_all('ref')
    for ref in ref_tags:
        ref_data = extract_single_reference_with_archives(ref)
        if ref_data:
            references_with_archives.extend(ref_data)
    
    return references_with_archives


def extract_single_reference_with_archives(reference_element) -> List[Dict[str, str]]:
    """
    Extract original URLs and their archives from a single reference element.
    
    Args:
        reference_element: BeautifulSoup element representing one reference
        
    Returns:
        List of dictionaries with original_url, archive_url, and reference_html
    """
    references = []
    
    # Find all <a> tags within this reference
    links = reference_element.find_all('a', href=True)
    
    # Group links by their position and context
    original_links = []
    archive_links = []
    
    for link in links:
        href = link['href']
        if not is_external_url(href):
            continue
            
        if is_archive_url(href):
            archive_links.append(link)
        else:
            original_links.append(link)
    
    # If we have both original and archive links, try to associate them
    if original_links and archive_links:
        # Look for archives that are close to their originals in the HTML structure
        for original_link in original_links:
            best_archive = find_best_archive_for_original(original_link, archive_links)
            
            references.append({
                'original_url': original_link['href'],
                'archive_url': best_archive['href'] if best_archive else '',
                'reference_html': str(reference_element)
            })
            
            # Remove the used archive from consideration
            if best_archive:
                archive_links.remove(best_archive)
    
    # Add any remaining original links without archives
    for original_link in original_links:
        # Check if we already added this URL
        if not any(ref['original_url'] == original_link['href'] for ref in references):
            references.append({
                'original_url': original_link['href'],
                'archive_url': '',
                'reference_html': str(reference_element)
            })
    
    # Add any remaining archive links that couldn't be matched
    for archive_link in archive_links:
        # Try to extract the original URL from the archive
        original_url = extract_original_url_from_archive(archive_link['href'])
        if original_url:
            references.append({
                'original_url': original_url,
                'archive_url': archive_link['href'],
                'reference_html': str(reference_element)
            })
        else:
            # If we can't extract the original, add it as an unmatched archive
            references.append({
                'original_url': '',
                'archive_url': archive_link['href'],
                'reference_html': str(reference_element)
            })
    
    return references


def find_best_archive_for_original(original_link, archive_links) -> Optional:
    """
    Find the best archive link for a given original link based on HTML proximity.
    
    Args:
        original_link: The original link element
        archive_links: List of archive link elements
        
    Returns:
        The best matching archive link element, or None if no good match
    """
    if not archive_links:
        return None
    
    # Strategy 1: Look for archives that are direct siblings or very close to the original
    original_parent = original_link.parent
    original_text = original_link.get_text().strip()
    
    # Look for archives in the same parent element or very close
    for archive_link in archive_links:
        archive_parent = archive_link.parent
        
        # Check if they're in the same parent element
        if archive_parent == original_parent:
            return archive_link
        
        # Check if they're in sibling elements
        if archive_parent.parent == original_parent.parent:
            return archive_link
        
        # Check if they're close in the document order
        if is_elements_close_in_document(original_link, archive_link):
            return archive_link
    
    # Strategy 2: Look for archives that contain the original URL in their extracted original
    for archive_link in archive_links:
        extracted_original = extract_original_url_from_archive(archive_link['href'])
        if extracted_original and is_url_equivalent(original_link['href'], extracted_original):
            return archive_link
    
    # Strategy 3: Look for archives that appear right after the original link
    # This is common in Wikipedia references
    original_next = original_link.find_next_sibling()
    if original_next:
        # Check if the next sibling contains an archive link
        archive_in_next = original_next.find('a', href=True)
        if archive_in_next and is_archive_url(archive_in_next['href']):
            return archive_in_next
    
    # Strategy 4: Look for archives that appear right before the original link
    original_prev = original_link.find_previous_sibling()
    if original_prev:
        # Check if the previous sibling contains an archive link
        archive_in_prev = original_prev.find('a', href=True)
        if archive_in_prev and is_archive_url(archive_in_prev['href']):
            return archive_in_prev
    
    # If no good match found, return the first archive (fallback)
    return archive_links[0] if archive_links else None


def is_elements_close_in_document(elem1, elem2, max_distance: int = 3) -> bool:
    """
    Check if two elements are close to each other in the document order.
    
    Args:
        elem1: First element
        elem2: Second element
        max_distance: Maximum number of elements between them
        
    Returns:
        True if elements are close in document order
    """
    # Count elements between elem1 and elem2
    distance = 0
    current = elem1.next_sibling
    
    while current and current != elem2:
        if hasattr(current, 'name') and current.name:  # Only count actual elements
            distance += 1
        if distance > max_distance:
            return False
        current = current.next_sibling
    
    return current == elem2


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