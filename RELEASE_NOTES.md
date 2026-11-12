# Release notes – November 2026

## New
- **Full website crawl** – give it a start URL and it follows every internal link on the site, saving each page's HTML and metadata.
- **Image scraping** – downloads all images from the pages it visits and skips duplicates.
- **Video scraping** – finds `<video>` files, direct video links and YouTube/Vimeo/Dailymotion/Twitch embeds. Tick "Include video scraping" to download the files as well.
- **Choose an output folder** in the app. Each site gets its own subfolder, and reports can be saved as TXT, CSV, JSON or HTML.
- **Windows .exe** – run `Scraper.exe`, no Python install needed.

## Improvements
- The crawler respects `robots.txt` and waits 1 second between pages.
- Smaller window, and the app log can be shown or hidden.
- `setup.bat` / `setup.sh` set up everything when you run from source.

## Fixes
- Crawling an address with a port number (for example `localhost:8080`) no longer crashes on Windows.
- The app logo now shows in the window.
- When a page can't be fetched, the app log and the crawl report now say why (for example "HTTP 403 (the site blocks automated access)") instead of just counting an error.
