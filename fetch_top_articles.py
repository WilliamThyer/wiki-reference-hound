import requests
from datetime import datetime, timedelta
from typing import List


def get_top_articles(limit: int = 25) -> List[str]:
    """
    Fetch the top most-viewed English Wikipedia articles from yesterday.
    
    Args:
        limit: Number of articles to fetch (default: 25)
        
    Returns:
        List of article titles (excluding Special: and Main Page)
    """
    # Get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    year = yesterday.year
    month = yesterday.month
    day = yesterday.day
    
    # Format month and day with leading zeros
    month_str = f"{month:02d}"
    day_str = f"{day:02d}"
    
    # Wikimedia REST API endpoint
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{year}/{month_str}/{day_str}"
    
    headers = {
        'User-Agent': 'Wikipedia-Dead-Link-Checker/1.0 (https://github.com/your-repo; your-email@example.com)'
    }
    
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        # Extract article titles from the response
        for item in data.get('items', []):
            if 'articles' in item:
                for article in item['articles']:
                    title = article.get('article', '')
                    
                    # Skip Special: pages and Main Page
                    if not title.startswith('Special:') and title != 'Main_Page':
                        articles.append(title)
                        
                        # Stop when we reach the limit
                        if len(articles) >= limit:
                            break
                if len(articles) >= limit:
                    break
        
        return articles[:limit]
        
    except requests.RequestException as e:
        print(f"Error fetching top articles: {e}")
        return []
    except (KeyError, ValueError) as e:
        print(f"Error parsing response: {e}")
        return []


if __name__ == "__main__":
    # Test the function
    articles = get_top_articles(5)
    print("Top 5 articles from yesterday:")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article}") 