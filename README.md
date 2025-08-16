# Wikipedia Dead Link Checker

A Python tool that automatically checks for dead external links in the top 25 most-viewed English Wikipedia articles from the previous day.

## Features

- **Fetches top articles**: Gets the most-viewed Wikipedia articles from yesterday using the Wikimedia REST API
- **Extracts external links**: Parses HTML content to find external links in references and citations
- **Checks link status**: Uses HTTP HEAD/GET requests to verify if links are alive
- **Generates primary table**: Builds a comprehensive ALL references table (Polars DataFrame) and writes it to CSV
- **Progress tracking**: Shows real-time progress with progress bars
- **Rate limiting**: Respectful to servers with configurable delays
- **Parallel processing**: Optional parallel processing for faster checking
- **Browser validation**: Optional browser automation for false positive detection

## Quick Start

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
- Check if each link is alive (skipping ones with valid archives)
- Generate the ALL references CSV in the `output/` directory

### 3. View Results

Check the `output/` directory for:
- `all_references_report_YYYYMMDD_HHMMSS.csv` - The project’s primary artifact

## Configuration Options

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
  --references-only       Only extract external links from the references section (more focused)
```

### Examples

```bash
# Check only top 10 articles
python main.py --limit 10

# Use longer timeout for slow servers
python main.py --timeout 10.0

# Enable parallel processing for faster checking
python main.py --parallel --max-workers 30

# Enable browser validation for false positive detection
python main.py --browser-validation --browser-timeout 20

# Use references-only mode for more focused link extraction
python main.py --references-only
```

## Link Extraction Methods

The tool offers two methods for extracting external links from Wikipedia articles:

### 1. Comprehensive Extraction (Default)
Extracts external links from the entire article content, including:
- References section
- Inline citations
- External links section
- Any other external links found in the article

This method is more thorough but may include links that are not strictly citations.

### 2. References-Only Extraction
Extracts external links only from the formal references section using the `--references-only` flag. This method:
- Focuses specifically on `<ol class="references">` elements
- Extracts links from `<ref>` tags
- Provides more accurate citation-only results
- Reduces false positives from navigation or non-citation links

Use this method when you want to focus specifically on academic citations and references.

## Browser Validation

The tool includes optional browser validation to detect false positives in dead link detection. This is useful for:

- **JavaScript-heavy sites**: Some sites require JavaScript to load content
- **Complex redirects**: Multi-step redirects that HTTP libraries miss
- **Bot detection**: Sites that block automated requests but work in browsers

### Setup Browser Validation

1. **Install dependencies**:
```bash
pip install selenium webdriver-manager
```

2. **Install Chrome/Chromium** (if not already installed):
   - macOS: Download from https://www.google.com/chrome/
   - Linux: `sudo apt-get install google-chrome-stable`
   - Windows: Download from https://www.google.com/chrome/

3. **Use browser validation**:
```bash
python main.py --browser-validation
```

## Project Structure

```
wikipedia-dead-ref-finder/
├── main.py                 # Main orchestration script
├── fetch_top_articles.py   # Fetches top Wikipedia articles
├── fetch_article_html.py   # Retrieves article HTML content
├── extract_references.py   # Extracts external links from HTML
├── check_links.py         # Checks if links are alive
├── generate_report.py     # Builds the ALL references Polars table and writes CSV
├── browser_validation.py  # Browser automation for false positive detection
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── output/              # Generated reports (created automatically)
    └── all_references_report_YYYYMMDD_HHMMSS.csv
```

## Output Format

### ALL References CSV

The CSV file contains the following columns for every reference link found:
- `article_title`: Name of the Wikipedia article
- `original_url`: The original reference URL (non-archive)
- `archive_url`: The archive URL if available, otherwise None
- `has_archive`: Whether a valid archive URL exists for this reference
- `error_code`: For links that were checked (no archive available), the HTTP status code or a label such as `CONNECTION_ERROR`, `BLOCKED`, `ERROR`, or `Not checked`
- `timestamp`: When the table was generated
- `browser_validation_check`: If browser validation was used, the outcome for the URL (`alive`, `dead`, `blocked`, `timeout`, `error`, or `Not checked`)
- `browser_validation_check_detail`: Concise detail collected during validation (if any)

**Note**: Each row represents one original link. If an archive link exists, it's included in the same row as the `archive_url`. This eliminates duplicate rows and makes it easier to see which links have archives.

## Dependencies

- **requests**: HTTP requests for APIs and link checking
- **beautifulsoup4**: HTML parsing for link extraction
- **tqdm**: Progress bars for better UX
- **selenium**: Browser automation for false positive detection (optional)
- **webdriver-manager**: Automatic ChromeDriver management (optional)
- **polars**: High-performance DataFrame library used to build the primary table

## Testing

Test individual components:

```bash
python main.py --test
```

This will test each module separately to help with debugging.

## Important Notes

- **Rate Limiting**: The tool includes delays between requests to be respectful to servers
- **Timeouts**: Default 5-second timeout per request to avoid hanging
- **API Limits**: Wikimedia APIs have rate limits, but the tool is designed to work within them
- **False Positives**: Some links might appear dead due to temporary issues or anti-bot measures

## Troubleshooting

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