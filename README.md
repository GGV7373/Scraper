# skraper

## Overview

**skraper** is a graphical Python application for discovering and scraping the main content from websites based on a base domain name (e.g., `nrk`). It automatically checks which top-level domains (TLDs) are active for the base (like `.no`, `.com`, etc.), pings them in parallel, and scrapes the most important content from each reachable site.

## Features

- **Automatic TLD Discovery:** Checks all known TLDs for a given base domain.
- **Parallel Pinging:** Fast domain reachability checks using threading.
- **Content Extraction:** Extracts and saves only important elements: `<title>`, meta descriptions, Open Graph descriptions, and all `<h1>`-`<h6>`, `<p>` tags.
- **Graphical Interface:** Simple GUI for input and progress/log viewing.
- **Reporting:** Generates a summary report after scraping, including statistics on pinged, saved, failed, and non-useful scrapes.
- **Per-domain Output:** Saves results for each domain in a separate `.txt` file inside a folder named after the base.

## Usage

1. **Install requirements:**
   ```
   pip install requests beautifulsoup4
   ```

2. **Run the app:**
   ```
   python main.py
   ```

3. **In the GUI:**
   - Enter a base domain name (e.g., `nrk`).
   - Click "Run Scraper".
   - View progress and logs in the app.
   - Results and a scrape report will be saved in a folder named after your base domain.

## Output

- For each reachable domain, a file like `nrk-no.txt` will be created in the `nrk` folder.
- A summary report `nrk-scrape-report.txt` will be saved in the same folder.

## Example

If you enter `nrk` as the base, the app will try domains like `nrk.no`, `nrk.com`, etc., and save the results for each reachable site.

---

**Note:**  
- The app uses a public TLD list and may take some time depending on your network and the number of TLDs.
- Only non-empty, meaningful content is saved for each domain.

