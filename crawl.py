import asyncio
import argparse
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
START_URL = "https://www.bracu.ac.bd/"
OUTPUT_DIR = "university_docs"
STATE_FILE = "crawl_state.json"       # for resume support
MAX_RETRIES = 2
POLITENESS_DELAY = 1.0                # seconds between requests

# Priority seed paths – these are appended to the base URL so the
# crawler does not have to *discover* them through link-following.
SEED_PATHS = [
    "/",
    "/about",
    "/about/overview",
    "/about/mission-vision",
    "/about/history",
    "/about/governance",
    "/about/accreditation",
    "/academics",
    "/academics/programs",
    "/academics/undergraduate-programs",
    "/academics/graduate-programs",
    "/academics/departments",
    "/admissions",
    "/admissions/undergraduate",
    "/admissions/graduate",
    "/admissions/international-students",
    "/admissions/tuition-fees",
    "/admissions/scholarships-and-financial-aid",
    "/research",
    "/research/centers",
    "/research/publications",
    "/student-life",
    "/student-life/clubs",
    "/student-life/residential-life",
    "/student-life/career-services",
    "/campus",
    "/faculty",
    "/contact",
]

# Domains we are allowed to crawl (main site + known sub-domains)
ALLOWED_DOMAINS = {
    "www.bracu.ac.bd",
    "bracu.ac.bd",
}

# File extensions to skip
SKIP_EXTENSIONS = frozenset([
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".zip", ".rar", ".7z",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".css", ".js", ".json", ".xml",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv",
])


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def is_valid_url(url: str) -> bool:
    """Return True if the URL belongs to an allowed BRAC domain and
    is not a binary file or junk link."""
    parsed = urlparse(url)
    if parsed.netloc not in ALLOWED_DOMAINS:
        return False
    if any(url.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    if "#" in url or "javascript:" in url or "mailto:" in url or "tel:" in url:
        return False
    return True


def clean_filename(url: str) -> str:
    """Create a filesystem-safe filename from a URL."""
    name = url.replace("https://", "").replace("http://", "").replace("/", "_")
    name = "".join(c if c.isalnum() or c in "_-" else "" for c in name)
    return name[:80] + ".txt"


def extract_page_title(html: str) -> str:
    """Pull the <title> tag content."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def extract_clean_content(html: str) -> str:
    """
    Extract meaningful text from raw HTML, stripping navigation,
    footer, sidebar, and other boilerplate elements.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove structural noise
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript", "svg",
                     "button", "select", "option"]):
        tag.decompose()

    # 2. Remove class/id-based noise
    noise_pattern = re.compile(
        r"(menu|nav|sidebar|breadcrumb|search|social|footer|widget|"
        r"cookie|popup|modal|banner|advertisement|ad-|slick|carousel)",
        re.I,
    )
    for el in soup.find_all(["div", "section", "ul", "aside"],
                            class_=noise_pattern):
        el.decompose()
    for el in soup.find_all(["div", "section", "ul", "aside"],
                            id=noise_pattern):
        el.decompose()

    # 3. Extract text, preserving some structure
    text = soup.get_text(separator="\n")

    # 4. Line-by-line filtering
    clean_lines = []
    seen = set()  # simple dedup for repeated lines (menus echoed)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in seen:
            continue
        # Skip very short junk-like lines
        if len(line) < 10:
            continue
        # Skip common UI labels
        junk_labels = [
            "Apply Now", "Read More", "Learn More", "Click Here",
            "Skip to main", "Search form", "Toggle navigation",
            "Back to top", "Follow us", "Share this",
        ]
        if any(line.lower() == label.lower() for label in junk_labels):
            continue
        # Skip lines that are only punctuation / symbols
        if re.match(r"^[\W_]+$", line):
            continue

        seen.add(line)
        clean_lines.append(line)

    return "\n".join(clean_lines)


def extract_links(html: str, base_url: str) -> list[str]:
    """Return a deduplicated list of valid links found in the HTML."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    seen = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full = urljoin(base_url, href).split("#")[0].strip()
        if full.endswith("/"):
            full = full[:-1]
        if full and full not in seen and is_valid_url(full):
            seen.add(full)
            found.append(full)
    return found


# ─────────────────────────────────────────────────────────────
# STATE PERSISTENCE  (resume support)
# ─────────────────────────────────────────────────────────────
def load_state() -> tuple[set[str], list[str]]:
    """Load previously visited URLs and remaining queue."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return set(data.get("visited", [])), list(data.get("queue", []))
    return set(), []


def save_state(visited: set[str], queue: list[str]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"visited": list(visited), "queue": queue}, f, indent=2)


# ─────────────────────────────────────────────────────────────
# MAIN CRAWLER
# ─────────────────────────────────────────────────────────────
async def main(max_pages: int, resume: bool) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Build initial queue
    if resume:
        visited, queue = load_state()
        print(f"♻️  Resuming: {len(visited)} already visited, {len(queue)} in queue")
    else:
        visited: set[str] = set()
        queue: list[str] = []

    # Seed with priority URLs (skip already-visited ones)
    base = START_URL.rstrip("/")
    for path in SEED_PATHS:
        url = (base + path).rstrip("/")
        if url not in visited and url not in queue:
            queue.append(url)

    if not queue:
        print("Nothing to crawl – queue is empty.")
        return

    print(f"🚀 Starting BRAC University crawl  (max {max_pages} pages)")
    print(f"   Seeds: {len(queue)} URLs in queue\n")

    browser_cfg = BrowserConfig(
        headless=True,
        verbose=False,
    )
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30000,        # 30 s
        wait_until="domcontentloaded",
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        count = 0

        while queue and count < max_pages:
            current_url = queue.pop(0)
            if current_url.endswith("/"):
                current_url = current_url[:-1]
            if current_url in visited:
                continue

            print(f"[{count + 1}/{max_pages}]  {current_url}")

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = await crawler.arun(url=current_url, config=run_cfg)

                    if not result.success:
                        print(f"   ❌ Attempt {attempt}: page load failed")
                        await asyncio.sleep(attempt * 2)
                        continue

                    # ── Content extraction ──
                    title = extract_page_title(result.html)
                    clean_text = extract_clean_content(result.html)

                    if len(clean_text) > 150:
                        filename = clean_filename(current_url)
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"Source URL: {current_url}\n")
                            f.write(f"Page Title: {title}\n\n")
                            f.write(clean_text)
                        print(f'   ✅ Saved  ({len(clean_text):,} chars)  "{title}"')
                    else:
                        print(f"   ⚠️  Too little content after cleaning – skipped")

                    # ── Discover new links ──
                    if result.html:
                        new_links = extract_links(result.html, current_url)
                        added = 0
                        for link in new_links:
                            if link not in visited and link not in queue:
                                queue.append(link)
                                added += 1
                        if added:
                            print(f"   🔗 +{added} new links")

                    success = True
                    break  # no need to retry

                except Exception as exc:
                    print(f"   ⚠️  Attempt {attempt} error: {exc}")
                    await asyncio.sleep(attempt * 2)

            # Mark visited regardless of success (avoid infinite retries)
            visited.add(current_url)
            if success:
                count += 1

            # Save state periodically (every 10 pages)
            if count % 10 == 0:
                save_state(visited, queue)

            # Politeness delay
            await asyncio.sleep(POLITENESS_DELAY)

    # Final state save
    save_state(visited, queue)
    print(f"\n🏁 Done!  Crawled {count} pages.  Files in ./{OUTPUT_DIR}/")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl BRAC University website")
    parser.add_argument("--max-pages", type=int, default=300,
                        help="Maximum number of pages to crawl (default: 300)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous crawl state")
    args = parser.parse_args()

    asyncio.run(main(max_pages=args.max_pages, resume=args.resume))