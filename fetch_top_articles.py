import requests
import urllib3
import warnings
from datetime import datetime, timedelta
from typing import List

# Suppress SSL/TLS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


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
    
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{year}/{month_str}/{day_str}"
    
    headers = {
        'User-Agent': 'Wikipedia-Dead-Link-Checker/1.0 (https://github.com/your-repo; your-email@example.com)'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
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


def get_all_time_top_articles(limit: int = 25) -> List[str]:
    """
    Fetch articles that represent the most consistently popular English Wikipedia articles.
    Since the Wikimedia API doesn't provide true all-time data, this function aggregates
    data from multiple representative days to identify consistently popular articles.
    
    Args:
        limit: Number of articles to fetch (default: 25)
        
    Returns:
        List of article titles representing consistently popular articles
    """
    # Define representative dates to sample from (different months/years)
    sample_dates = [
        (2024, 1, 1),   # New Year's Day
        (2023, 12, 25), # Christmas
        (2023, 7, 4),   # Independence Day
        (2023, 3, 15),  # Random spring day
        (2022, 12, 31), # New Year's Eve
        (2022, 6, 15),  # Random summer day
        (2022, 1, 15),  # Random winter day
        (2021, 12, 25), # Christmas previous year
        (2021, 7, 4),   # Independence Day previous year
        (2021, 3, 15),  # Random spring day previous year
    ]
    
    article_scores = {}  # Track articles and their cumulative scores
    
    print(f"📊 Sampling data from {len(sample_dates)} representative dates...")
    
    for year, month, day in sample_dates:
        try:
            # Format month and day with leading zeros
            month_str = f"{month:02d}"
            day_str = f"{day:02d}"
            
            url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{year}/{month_str}/{day_str}"
            
            headers = {
                'User-Agent': 'Wikipedia-Dead-Link-Checker/1.0 (https://github.com/your-repo; your-email@example.com)'
            }
            
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                articles = data['items'][0].get('articles', [])
                
                # Score articles based on their rank (lower rank = higher score)
                for article in articles:
                    title = article.get('article', '')
                    rank = article.get('rank', 1000)
                    views = article.get('views', 0)
                    
                    # Skip special pages and main page
                    if title.startswith('Special:') or title == 'Main_Page':
                        continue
                    
                    # Calculate score: higher views and lower rank = higher score
                    score = views / (rank ** 0.5)  # Weight by rank
                    
                    if title in article_scores:
                        article_scores[title]['total_score'] += score
                        article_scores[title]['appearances'] += 1
                        article_scores[title]['total_views'] += views
                    else:
                        article_scores[title] = {
                            'total_score': score,
                            'appearances': 1,
                            'total_views': views
                        }
                
                print(f"   ✅ {year}-{month_str}-{day_str}: {len(articles)} articles")
                
            else:
                print(f"   ⚠️  {year}-{month_str}-{day_str}: No data available")
                
        except Exception as e:
            print(f"   ❌ {year}-{month_str}-{day_str}: Error - {str(e)}")
            continue
    
    # Sort articles by their cumulative score and appearance frequency
    sorted_articles = []
    for title, data in article_scores.items():
        # Calculate final score: combine total score with appearance frequency
        final_score = data['total_score'] * (1 + data['appearances'] * 0.1)
        sorted_articles.append({
            'title': title,
            'score': final_score,
            'appearances': data['appearances'],
            'total_views': data['total_views']
        })
    
    # Sort by final score (descending)
    sorted_articles.sort(key=lambda x: x['score'], reverse=True)
    
    # Extract titles up to the limit
    result = [article['title'] for article in sorted_articles[:limit]]
    
    print(f"📈 Found {len(result)} consistently popular articles from {len(article_scores)} unique articles")
    
    return result


if __name__ == "__main__":
    # Test both functions
    print("Testing daily top articles:")
    daily_articles = get_top_articles(5)
    print(f"Top 5 articles from yesterday: {len(daily_articles)} found")
    for i, article in enumerate(daily_articles, 1):
        print(f"  {i}. {article}")
    
    print("\nTesting all-time top articles:")
    all_time_articles = get_all_time_top_articles(5)
    print(f"Top 5 articles of all time: {len(all_time_articles)} found")
    for i, article in enumerate(all_time_articles, 1):
        print(f"  {i}. {article}") 