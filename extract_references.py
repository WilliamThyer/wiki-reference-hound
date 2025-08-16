from bs4 import BeautifulSoup
from typing import List, Set, Dict, Tuple, Optional
import re
from fetch_article_html import get_article_html


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


def filter_links_for_checking(links: List[str]) -> Tuple[List[str], Dict[str, List[str]], Dict[str, str]]:
    """
    Filter links for checking, separating original links with and without archives.
    Also finds fuzzy archive matches for links without exact matches.
    
    Args:
        links: List of all URLs found (mixture of original and archive links)
        
    Returns:
        Tuple of (links_to_check, links_with_archives, fuzzy_archive_matches)
        - links_to_check: original links with no matching archive link
        - links_with_archives: original links that have archives, with key=original link and value=list of archives
        - fuzzy_archive_matches: original links with fuzzy archive matches, with key=original link and value=best fuzzy archive
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
    
    # Find fuzzy archive matches for links without exact matches
    fuzzy_archive_matches = find_fuzzy_archive_matches(links_to_check, archive_links, similarity_threshold=0.7)
    
    return links_to_check, links_with_archives, fuzzy_archive_matches


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
    
    soup = BeautifulSoup(html, 'html.parser')
    external_links = set()
    
    # Find all reference list containers (ol with class="references")
    references_ol = soup.find_all("ol", class_="references")
    
    for ol in references_ol:
        # Extract all <li> elements from each reference list
        for li in ol.find_all("li", recursive=False):
            # Find all <a> tags within each reference
            links = li.find_all('a', href=True)
            for link in links:
                href = link['href']
                if is_external_url(href):
                    external_links.add(href)
    
    # Also look for <ref> tags that might contain external links
    ref_tags = soup.find_all('ref')
    for ref in ref_tags:
        links = ref.find_all('a', href=True)
        for link in links:
            href = link['href']
            if is_external_url(href):
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


def fuzzy_match_archive_url(original_url: str, all_archive_urls: List[str], similarity_threshold: float = 0.7) -> Optional[str]:
    """
    Find the best fuzzy match for an archive URL when exact matching fails.
    
    Args:
        original_url: The original URL to find an archive for
        all_archive_urls: List of all available archive URLs
        similarity_threshold: Minimum similarity score to consider a match (0.0 to 1.0)
        
    Returns:
        Best matching archive URL if found, None otherwise
    """
    if not original_url or not all_archive_urls:
        return None
    
    best_match = None
    best_score = 0.0
    
    # Normalize the original URL for comparison
    normalized_original = normalize_url_for_comparison(original_url)
    
    for archive_url in all_archive_urls:
        # Extract the original URL from the archive
        extracted_original = extract_original_url_from_archive(archive_url)
        if not extracted_original:
            continue
        
        # Normalize the extracted URL
        normalized_extracted = normalize_url_for_comparison(extracted_original)
        
        # Calculate similarity score
        similarity = calculate_url_similarity(normalized_original, normalized_extracted)
        
        if similarity > best_score and similarity >= similarity_threshold:
            best_score = similarity
            best_match = archive_url
    
    return best_match


def calculate_url_similarity(url1: str, url2: str) -> float:
    """
    Calculate similarity between two URLs using multiple metrics.
    
    Args:
        url1: First normalized URL
        url2: Second normalized URL
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not url1 or not url2:
        return 0.0
    
    # Exact match gets highest score
    if url1 == url2:
        return 1.0
    
    # Split URLs into components
    parts1 = url1.split('/')
    parts2 = url2.split('/')
    
    # Domain similarity (most important)
    domain1 = parts1[0] if parts1 else ""
    domain2 = parts2[0] if parts2 else ""
    
    if domain1 == domain2:
        domain_score = 1.0
    elif domain1 and domain2:
        # Check for subdomain variations
        if domain1.endswith(domain2) or domain2.endswith(domain1):
            domain_score = 0.9
        else:
            # Calculate domain similarity using character overlap
            domain_score = calculate_string_similarity(domain1, domain2)
    else:
        domain_score = 0.0
    
    # Path similarity
    path1 = '/'.join(parts1[1:]) if len(parts1) > 1 else ""
    path2 = '/'.join(parts2[1:]) if len(parts2) > 1 else ""
    
    if path1 == path2:
        path_score = 1.0
    elif path1 and path2:
        # Check if one path contains the other
        if path1 in path2 or path2 in path1:
            path_score = 0.8
        else:
            # Calculate path similarity
            path_score = calculate_string_similarity(path1, path2)
    else:
        path_score = 0.5 if not path1 and not path2 else 0.0
    
    # Weighted combination (domain is more important than path)
    final_score = (domain_score * 0.7) + (path_score * 0.3)
    
    return final_score


def calculate_string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using character overlap.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not str1 or not str2:
        return 0.0
    
    if str1 == str2:
        return 1.0
    
    # Convert to sets of characters for overlap calculation
    chars1 = set(str1.lower())
    chars2 = set(str2.lower())
    
    if not chars1 or not chars2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(chars1.intersection(chars2))
    union = len(chars1.union(chars2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


def find_fuzzy_archive_matches(original_urls: List[str], all_archive_urls: List[str], 
                              similarity_threshold: float = 0.7) -> Dict[str, str]:
    """
    Find fuzzy archive matches for a list of original URLs.
    
    Args:
        original_urls: List of original URLs to find archives for
        all_archive_urls: List of all available archive URLs
        similarity_threshold: Minimum similarity score to consider a match
        
    Returns:
        Dictionary mapping original URLs to their best fuzzy archive match
    """
    fuzzy_matches = {}
    
    for original_url in original_urls:
        # Skip if this URL already has an exact archive match
        if is_archive_url(original_url):
            continue
            
        # Try to find a fuzzy match
        fuzzy_archive = fuzzy_match_archive_url(original_url, all_archive_urls, similarity_threshold)
        if fuzzy_archive:
            fuzzy_matches[original_url] = fuzzy_archive
    
    return fuzzy_matches


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