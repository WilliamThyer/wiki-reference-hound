# Bot Detection Improvements for Wikipedia Dead Link Checker

## Problem Statement

The original Wikipedia dead link checker was treating all 4xx and 5xx HTTP status codes as "dead" links. However, many 403 (Forbidden) responses are actually due to websites blocking automated access (bots) rather than the links being truly dead. This was causing false positives in the dead link reports.

## Solution Overview

We've implemented a sophisticated bot detection system that:

1. **Categorizes 403 responses** as either "blocked" (bot protection) or "dead" (truly forbidden)
2. **Analyzes response headers and content** for bot-blocking indicators
3. **Uses domain-specific knowledge** of sites that commonly block bots
4. **Excludes blocked links** from dead link reports
5. **Provides detailed reporting** on blocked vs. truly dead links

## Key Improvements

### 1. New Status Categories

The link checker now recognizes these status categories:
- `alive`: Links that return 2xx status codes
- `dead`: Links that return 4xx/5xx status codes (except 403)
- `blocked`: Links that return 403 due to bot protection
- `archived`: Links that have working archive versions
- `connection_error`: Links that can't be reached due to network issues

### 2. Bot Detection Logic

The `is_likely_bot_blocked()` function analyzes:

**Response Headers:**
- Cloudflare protection headers
- Captcha/challenge headers
- Bot detection headers
- Rate limiting headers
- Security headers

**Response Content:**
- Bot-blocking messages
- Captcha pages
- Security challenge pages
- Access denied messages

**Domain Knowledge:**
- Known bot-blocking domains (Twitter, Facebook, LinkedIn, etc.)
- News sites that commonly block automated access
- CDN and security service domains

### 3. Improved User-Agent

Changed from a custom bot user-agent to a standard browser user-agent to reduce bot detection:
```python
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
```

### 4. Enhanced Reporting

**Console Output:**
- Separate counts for dead vs. blocked links
- Clear indication of bot protection
- Detailed status breakdown

**CSV Reports:**
- Only truly dead links are included
- Blocked links are excluded from dead link counts
- Status codes are preserved for analysis

**Summary Reports:**
- Notes about 403 responses being likely bot blocking
- Status code breakdown with bot-blocking indicators
- Clear distinction between different types of failures

## Example Output

Before improvements:
```
📊 Link Check Summary:
   Total links: 100
   ✅ Alive: 80
   ❌ Dead: 20  # Included 403 responses as "dead"
```

After improvements:
```
📊 Link Check Summary:
   Total links: 100
   ✅ Alive: 80
   ❌ Dead: 15  # Only truly dead links
   🚫 Blocked (403): 5  # Bot-blocked links
```

## Usage

The improvements are automatically applied when running the main script:

```bash
python main.py --limit 25
```

You can also test the bot detection specifically:

```bash
python test_bot_detection.py
```

## Benefits

1. **More Accurate Reports**: Dead link reports now only contain truly dead links
2. **Better Analysis**: Clear distinction between bot blocking and actual link death
3. **Reduced False Positives**: 403 responses are properly categorized
4. **Improved User Experience**: Users can focus on links that actually need attention
5. **Better Resource Allocation**: Organizations can prioritize fixing truly dead links over dealing with bot-blocking sites

## Technical Details

### Bot Detection Algorithm

1. **Header Analysis**: Check response headers for bot-blocking indicators
2. **Content Analysis**: For GET requests, analyze response content for blocking messages
3. **Domain Matching**: Check against known bot-blocking domains
4. **Fallback Logic**: For 403 responses, default to "blocked" unless strong evidence suggests otherwise

### Known Bot-Blocking Domains

- Social media: `twitter.com`, `x.com`, `facebook.com`, `instagram.com`, `linkedin.com`
- News sites: `blackfilm.com`, `essence.com`, `people.com`, `tvline.com`
- Security services: `cloudflare.com`, `akamai.com`
- Academic databases: `isni.org`, `worldcat.org`

### Performance Impact

- Minimal performance impact (additional GET request only for 403 responses)
- Improved accuracy justifies the small overhead
- Better user experience with more accurate results

## Future Enhancements

1. **Machine Learning**: Train models to better distinguish bot blocking from true forbidden responses
2. **Dynamic Domain Lists**: Automatically update known bot-blocking domains
3. **Retry Logic**: Implement exponential backoff for rate-limited requests
4. **Proxy Support**: Add support for rotating proxies to avoid IP-based blocking
5. **Browser Simulation**: Use tools like Selenium for sites with advanced bot protection

## Conclusion

These improvements significantly enhance the accuracy of the Wikipedia dead link checker by properly distinguishing between truly dead links and those that are simply blocking automated access. This leads to more actionable reports and better resource allocation for link maintenance. 