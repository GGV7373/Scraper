
# Skraper

## Overview

**Skraper** is a graphical Python application for discovering and scraping the main content from websites based on a base domain name (e.g., `nrk`). It automatically checks which top-level domains (TLDs) are active for the base (like `.no`, `.com`, etc.), pings them in parallel, and scrapes the most important content from each reachable site.

## Features

- **Automatic TLD Discovery:** Checks all known TLDs for a given base domain, or lets you specify a custom list.
- **Parallel Pinging:** Fast domain reachability checks using configurable threading (choose number of threads in GUI).
- **Content Extraction:** Extracts and saves only important elements: `<title>`, meta descriptions, Open Graph descriptions, and all `<h1>`-`<h6>`, `<p>` tags.
- **Graphical Interface:** Simple GUI for input, thread count, TLD selection, and progress/log viewing.
- **Reporting:** Generates a summary report after scraping, including statistics on pinged, saved, failed, and non-useful scrapes. Reports can be saved as `.txt`, `.csv`, and `.json`.
- **Per-domain Output:** Saves results for each domain in a separate `.txt` file inside a folder named after the base.
- **Image-only scraper:** Optional CLI tool to pull images from specific URLs, deduplicate by content hash, and sort into per-domain folders under `output/images`.


## Requirements File

The `requirements.txt` has the following content:

```
requests
beautifulsoup4
aiohttp
pillow
textblob
numpy
jsonschema
```

Quick install:

```sh
pip install -r requirements.txt
```

2. **Run the app:**
   ```sh
   python main.py
   ```

3. **In the GUI:**
   - Enter a base domain name (e.g., `nrk`).
   - (Optional) Set the number of threads (default: 20, range: 1-100).
   - (Optional) Enter a comma-separated list of TLDs to check (e.g., `.no,.com,.org`). Leave blank to check all known TLDs.
   - Click **Run Scraper**.
   - View progress and logs in the app.
   - Results and a scrape report will be saved in a folder named after your base domain.

## Output

- For each reachable domain, a file like `nrk-no.txt` will be created in the `nrk` folder.
- A summary report (e.g., `nrk-report.txt`, `nrk-report.csv`, `nrk-report.json`) will be saved in the same folder.
- For image-only scraping, all images are saved under `output/images/<domain>/` with a persistent `.hash_index.json` to avoid duplicates across runs.

## Image-only scraper (CLI)

Use this if you only want pictures from specific pages.

```sh
python image_scraper.py https://example.com https://example.com/gallery
# or from a file
python image_scraper.py --url-file urls.txt --output output/images --concurrency 8
# include subdomains and same-domain links (recursive crawl up to 100 pages per seed)
python image_scraper.py https://example.com --recursive --max-pages 100
```

- Images are grouped by domain and path under the chosen output folder (default `output/images`).
  - Example: `https://example.com/meat/special` → images saved under `output/images/example.com/meat/special/`
  - Example: `https://example.com/` → images saved under `output/images/example.com/index/`
- Deduplication uses SHA-256 content hashes stored in `.hash_index.json` in the output root, so reruns skip already downloaded images.
- Only `http/https` URLs are accepted. Provide one URL per line when using `--url-file`.
- `--recursive` follows links on the same domain and its subdomains; limit crawl breadth/depth with `--max-pages` (per seed URL).

## Example

If you enter `nrk` as the base, the app will try domains like `nrk.no`, `nrk.com`, etc., and save the results for each reachable site. You can limit the TLDs or increase threads for faster scanning.

---

**Notes:**
- The app uses a public TLD list and may take some time depending on your network and the number of TLDs.
- Only non-empty, meaningful content is saved for each domain.
- Reports are saved in multiple formats for convenience.

