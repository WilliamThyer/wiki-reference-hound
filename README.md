# Wikipedia Dead Link Checker

A Python tool that automatically checks for dead external links in the top 25 most-viewed English Wikipedia articles from the previous day.

## 🎯 Features

- **Fetches top articles**: Gets the most-viewed Wikipedia articles from yesterday using the Wikimedia REST API
- **Extracts external links**: Parses HTML content to find external links in references and citations
- **Checks link status**: Uses HTTP HEAD/GET requests to verify if links are alive
- **Generates reports**: Creates CSV and text reports of dead links found
- **Progress tracking**: Shows real-time progress with progress bars
- **Rate limiting**: Respectful to servers with configurable delays

## 📁 Project Structure

```
wikipedia-dead-ref-finder/
├── main.py                 # Main orchestration script
├── fetch_top_articles.py   # Fetches top Wikipedia articles
├── fetch_article_html.py   # Retrieves article HTML content
├── extract_references.py   # Extracts external links from HTML
├── check_links.py         # Checks if links are alive
├── generate_report.py     # Generates CSV and summary reports
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── output/              # Generated reports (created automatically)
    ├── dead_links_report_YYYYMMDD_HHMMSS.csv
    └── dead_links_summary_YYYYMMDD_HHMMSS.txt
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Tool

```bash
python main.py
```

This will:
- Fetch the top 25 most-viewed Wikipedia articles from yesterday
- Extract external links from each article
- Check if each link is alive
- Generate reports in the `output/` directory

### 3. View Results

Check the `output/` directory for:
- `dead_links_report_YYYYMMDD_HHMMSS.csv` - Detailed CSV report
- `dead_links_summary_YYYYMMDD_HHMMSS.txt` - Human-readable summary

## ⚙️ Configuration Options

### Command Line Arguments

```bash
python main.py [OPTIONS]

Options:
  --limit N              Number of articles to check (default: 25)
  --timeout SECONDS      Request timeout in seconds (default: 5.0)
  --delay SECONDS        Delay between link checks (default: 0.1)
  --output-dir DIR       Output directory (default: output)
  --parallel             Enable parallel processing for faster checking
  --max-workers N        Number of concurrent workers (default: 20)
  --chunk-size N         Links per batch for parallel processing (default: 100)
  --browser-validation   Enable browser validation for false positive detection
  --browser-timeout N    Browser page load timeout in seconds (default: 30)
  --no-headless          Run browser in visible mode (default: headless)
  --max-browser-links N  Max dead links to validate with browser (default: 50)
```

### Examples

```bash
# Check only top 10 articles
python main.py --limit 10

# Use longer timeout for slow servers
python main.py --timeout 10.0

# Be more respectful with longer delays
python main.py --delay 0.5

# Save reports to custom directory
python main.py --output-dir my_reports

# Enable parallel processing for faster checking
python main.py --parallel --max-workers 30

# Enable browser validation for false positive detection
python main.py --browser-validation --browser-timeout 20
```

## 📊 Output Format

### CSV Report

The CSV file contains the following columns:
- `article_title`: Name of the Wikipedia article
- `url`: The dead external link
- `status_code`: HTTP status code (or "CONNECTION_ERROR")
- `timestamp`: When the check was performed

### Summary Report

The text summary includes:
- Total statistics (articles processed, links checked, dead links found)
- Status code breakdown
- List of articles with dead links and their URLs

## 🧪 Testing

Test individual components:

```bash
python main.py --test
```

This will test each module separately to help with debugging.

## 🔧 How It Works

### 1. Fetch Top Articles
Uses the Wikimedia REST API to get the most-viewed articles from yesterday:
```
https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/YYYY/MM/DD
```

### 2. Get Article Content
Retrieves the full HTML content of each article using the MediaWiki API:
```
https://en.wikipedia.org/w/api.php?action=parse&page={title}&prop=text&formatversion=2&format=json
```

### 3. Extract External Links
Uses BeautifulSoup to parse HTML and find external links in:
- `<ref>` tags
- References sections
- Other external links (filtered to exclude navigation)

### 4. Check Link Status
For each external link:
- First tries HTTP HEAD request (faster)
- Falls back to HTTP GET if HEAD fails
- Records status code and connection errors

### 5. Generate Reports
Creates timestamped reports with all dead links found.

## 🔍 Browser Validation (False Positive Detection)

The tool includes optional browser validation to detect false positives in dead link detection. This is useful for:

- **JavaScript-heavy sites**: Some sites require JavaScript to load content
- **Complex redirects**: Multi-step redirects that HTTP libraries miss
- **Bot detection**: Sites that block automated requests but work in browsers
- **Content verification**: Ensuring pages actually load meaningful content

### Setup Browser Validation

1. **Install dependencies**:
```bash
python setup_browser_validation.py
```

2. **Install Chrome/Chromium** (if not already installed):
   - macOS: Download from https://www.google.com/chrome/
   - Linux: `sudo apt-get install google-chrome-stable`
   - Windows: Download from https://www.google.com/chrome/

3. **Test browser validation**:
```bash
python test_browser_validation.py --test-urls
```

### Using Browser Validation

```bash
# Enable browser validation
python main.py --browser-validation

# Customize browser settings
python main.py --browser-validation --browser-timeout 20 --no-headless

# Limit browser validation to first 20 dead links (for safety)
python main.py --browser-validation --max-browser-links 20
```

### Browser Validation Features

- **Headless mode**: Runs browser in background (default)
- **Visible mode**: Run with `--no-headless` for debugging
- **Configurable timeout**: Set with `--browser-timeout`
- **Safety limits**: Limit validation with `--max-browser-links`
- **False positive detection**: Identifies links that work in browsers but fail HTTP checks

### Browser Validation Output

When browser validation is enabled, you'll see additional output:
```
🔍 Browser Validation Summary
========================================
Total links checked: 15
✅ Confirmed alive (false positives): 3
❌ Confirmed dead: 10
🚫 Blocked (bot protection): 2
⏱️  Timeout: 0
🔌 Error: 0

🎉 False Positives Found:
   - https://example.com/page
     → Redirected to: https://example.com/new-page
     → Title: Example Page
```

## 📦 Dependencies

- **requests**: HTTP requests for APIs and link checking
- **beautifulsoup4**: HTML parsing for link extraction
- **tqdm**: Progress bars for better UX
- **selenium**: Browser automation for false positive detection (optional)
- **webdriver-manager**: Automatic ChromeDriver management (optional)

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Important Notes

- **Rate Limiting**: The tool includes delays between requests to be respectful to servers
- **Timeouts**: Default 5-second timeout per request to avoid hanging
- **API Limits**: Wikimedia APIs have rate limits, but the tool is designed to work within them
- **False Positives**: Some links might appear dead due to temporary issues or anti-bot measures

## 🔍 Troubleshooting

### Common Issues

1. **No articles found**: Check your internet connection and the Wikimedia API status
2. **No external links found**: Some articles may not have external references
3. **Many connection errors**: Try increasing the timeout with `--timeout 10.0`
4. **Slow performance**: Increase delay with `--delay 0.5` to be more respectful to servers

### Debug Mode

Use the test mode to debug individual components:

```bash
python main.py --test
```

This will test each module separately and show detailed output. 