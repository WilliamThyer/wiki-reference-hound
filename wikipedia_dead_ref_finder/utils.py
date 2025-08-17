import re
from typing import List, Optional
from urllib.parse import urlparse


def clean_article_title(title: str) -> str:
    """
    Clean and normalize a Wikipedia article title.
    
    Args:
        title: Raw article title
        
    Returns:
        Cleaned title
    """
    # Replace underscores with spaces
    title = title.replace('_', ' ')
    
    # Remove any extra whitespace
    title = ' '.join(title.split())
    
    return title


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


if __name__ == "__main__":
    # Test utility functions
    test_title = "Example_Article_Title_With_Underscores"
    print("Testing utility functions:")
    print(f"  Original title: {test_title}")
    print(f"  Cleaned title: {clean_article_title(test_title)}")
    print(f"  Duration 45.5s: {format_duration(45.5)}")
    print(f"  Duration 125.0s: {format_duration(125.0)}")
    print(f"  Duration 7325.0s: {format_duration(7325.0)}") 