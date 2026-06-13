#!/usr/bin/env python3
"""
HSBC Partnership News scraper.

Pulls recent stories from every source in sources.py, filters to the recency
window, tries to extract two clean paragraphs of copy for each story, and writes
everything to data/news.json grouped by section.

Run it with:   python3 scrape.py
Options (environment variables):
   WINDOW_HOURS   how many hours back to keep (default 48)
   MAX_PER_SOURCE max stories kept per source (default 12)
   FETCH_BODIES   "1" to fetch article bodies for fuller copy (default 1)
"""

from __future__ import annotations  # allow modern type hints on Python 3.9

import os
import re
import json
import html
import time
import urllib.parse
import warnings
from datetime import datetime, timezone, timedelta

warnings.filterwarnings("ignore")

import requests
import feedparser
from bs4 import BeautifulSoup

try:
    import trafilatura
    HAVE_TRAFILATURA = True
except Exception:
    HAVE_TRAFILATURA = False

from sources import SOURCES, SECTION_ORDER, DEFAULT_WINDOW_HOURS

# ---- settings ----
WINDOW_HOURS = int(os.environ.get("WINDOW_HOURS", DEFAULT_WINDOW_HOURS))
# How many days of stories to keep in the file. The scraper ADDS new stories to
# this rolling archive each run; the page then filters to 24/48/72h on top of it.
KEEP_DAYS = int(os.environ.get("KEEP_DAYS", 7))
MAX_PER_SOURCE = int(os.environ.get("MAX_PER_SOURCE", 12))
FETCH_BODIES = os.environ.get("FETCH_BODIES", "1") == "1"
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "news.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}


def gnews_url(query: str) -> str:
    """Build a Google News RSS search URL (UK edition)."""
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-GB&gl=GB&ceid=GB:en"


def clean_text(s: str) -> str:
    """Strip HTML tags and tidy whitespace."""
    if not s:
        return ""
    text = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_date(entry) -> datetime | None:
    """Get a timezone-aware datetime from a feed entry, if present."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def strip_publisher_suffix(title: str, source_name: str) -> str:
    """Google News titles end with ' - Publisher'; drop that tail."""
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip() if " - " in title else title


def extract_body(url: str) -> str:
    """
    Best-effort: fetch the article and return its first two real paragraphs.
    Returns "" on any failure (blocked, paywalled, timeout, etc.).
    """
    if not (FETCH_BODIES and HAVE_TRAFILATURA and url):
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(
            downloaded, include_comments=False, include_tables=False,
            favor_precision=True,
        ) or ""
    except Exception:
        return ""

    return top_paragraphs(text)


def top_paragraphs(text: str, bullets: int = 2, target: int = 175) -> str:
    """
    Turn extracted article text into exactly `bullets` substantial bullets, each a
    solid 2-3 lines, to match the example bulletins. News articles often open with
    one-sentence paragraphs, so we combine consecutive paragraphs into each bullet
    until it reaches `target` characters (≈ 2-3 lines) before starting the next.
    """
    # Keep proper sentence-like paragraphs; skip headings, stat lines, captions.
    good = [line.strip() for line in (text or "").split("\n")
            if len(line.strip()) >= 40 and any(p in line for p in ".!?")]

    out, i = [], 0
    for _ in range(bullets):
        chunk = ""
        while i < len(good) and len(chunk) < target:
            chunk = (chunk + " " + good[i]).strip()
            i += 1
        if chunk:
            out.append(chunk)

    result = "\n\n".join(out)
    # Reject thin extractions (homepages, "official site" blurbs, cookie notices)
    # so they fall back to a clean manual write-up rather than junk copy.
    return result if len(result) >= 250 else ""


# Sources we don't bother browser-fetching: Sportcal & Olympics hard-block
# data-centre servers (403); the FT is paywalled. These stay click-to-read.
SKIP_BROWSER_SOURCES = {"Sportcal", "Olympics", "Financial Times"}
FETCH_BROWSER = os.environ.get("FETCH_BROWSER", "1") == "1"
# Cookie that skips Google's EU consent wall so redirects resolve cleanly.
_GOOGLE_CONSENT = {"name": "SOCS", "value": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg",
                   "domain": ".google.com", "path": "/"}


def _browser_body(page, url: str) -> str:
    """Follow a Google News link through to the real article and read its body."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception:
        pass
    # Wait for the redirect to leave google.com and land on the real article.
    for _ in range(16):
        if "google.com" not in page.url and "chrome-error" not in page.url:
            break
        try:
            page.wait_for_timeout(500)
        except Exception:
            break
    if "google.com" in page.url or "chrome-error" in page.url:
        return ""
    try:
        page.wait_for_timeout(2500)  # let the article render
        html = page.content()
    except Exception:
        return ""
    if not HAVE_TRAFILATURA:
        return ""
    body = trafilatura.extract(html, include_comments=False,
                               include_tables=False, favor_precision=True) or ""
    return top_paragraphs(body)


def browser_enrich(stories: list) -> None:
    """Read article bodies for blocked (Google News) sources using a headless browser."""
    targets = [s for s in stories
               if s["kind"] == "gnews" and not s["body"]
               and s["source"] not in SKIP_BROWSER_SOURCES]
    if not (FETCH_BROWSER and targets):
        return
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("   (playwright not installed — skipping browser fetch; those stay manual)")
        return

    print(f"\nBrowser-fetching copy for {len(targets)} blocked-source stories...")
    ua = HEADERS["User-Agent"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=ua, locale="en-GB")
        ctx.add_cookies([_GOOGLE_CONSENT])
        page = ctx.new_page()
        for s in targets:
            s["body"] = _browser_body(page, s["link"])
        browser.close()
    done = sum(1 for s in targets if s["body"])
    print(f"   got full copy for {done}/{len(targets)}")


def collect_from_source(src: dict) -> list[dict]:
    """Fetch and normalise stories from a single source."""
    if src["kind"] == "gnews":
        feed_url = gnews_url(src["query"])
    else:
        feed_url = src["url"]

    try:
        feed = feedparser.parse(feed_url, request_headers=HEADERS)
    except Exception as e:
        print(f"   ! {src['name']}: feed error {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    stories = []
    for entry in feed.entries:
        published = parse_date(entry)
        # If no date, keep it but mark unknown (Google News always supplies one).
        if published and published < cutoff:
            continue

        title = strip_publisher_suffix(clean_text(entry.get("title", "")), src["name"])
        link = entry.get("link", "")
        if not title or not link:
            continue

        summary = clean_text(entry.get("summary", ""))

        stories.append({
            "section": src["section"],
            "source": src["name"],
            "kind": src["kind"],
            "title": title,
            "link": link,
            "published": published.isoformat() if published else None,
            "published_label": published.strftime("%a %d %b, %H:%M") if published else "",
            "summary": summary,   # short feed snippet (always available)
            "body": "",           # filled in below for direct sources
        })
        if len(stories) >= src.get("max", MAX_PER_SOURCE):
            break
    return stories


def main():
    print(f"Scraping {len(SOURCES)} sources, last {WINDOW_HOURS}h, "
          f"bodies={'on' if FETCH_BODIES and HAVE_TRAFILATURA else 'off'}\n")

    all_stories = []
    seen_titles = set()

    for src in SOURCES:
        got = collect_from_source(src)
        # Dedupe by normalised title across the whole run.
        unique = []
        for s in got:
            key = re.sub(r"[^a-z0-9]", "", s["title"].lower())[:60]
            if key and key not in seen_titles:
                seen_titles.add(key)
                unique.append(s)
        print(f"   {src['section']:18s} {src['name']:16s} {len(unique):2d} stories")
        all_stories.extend(unique)

    # Enrich direct-source stories with two paragraphs of body copy.
    if FETCH_BODIES and HAVE_TRAFILATURA:
        direct = [s for s in all_stories if s["kind"] == "direct"]
        print(f"\nFetching article copy for {len(direct)} direct-source stories...")
        for i, s in enumerate(direct, 1):
            s["body"] = extract_body(s["link"])
            time.sleep(0.3)  # be polite
        done = sum(1 for s in direct if s["body"])
        print(f"   got full copy for {done}/{len(direct)}")

    # Read blocked (Google News) sources with a real browser where we can.
    browser_enrich(all_stories)

    # For every story, settle on the best available "copy" text.
    # Google News snippets are usually just the headline echoed back (+ publisher),
    # which is useless as copy — blank those so the page prompts for a manual write-up.
    for s in all_stories:
        snippet = s["summary"]
        norm_snip = re.sub(r"[^a-z0-9]", "", snippet.lower())
        norm_title = re.sub(r"[^a-z0-9]", "", s["title"].lower())
        if norm_title and norm_title in norm_snip and len(norm_snip) < len(norm_title) + 50:
            snippet = ""
        s["copy"] = s["body"] or snippet

    # ---- Merge with previously collected stories (accumulate, don't overwrite) ----
    now = datetime.now(timezone.utc)

    def story_key(s):
        return s.get("link") or re.sub(r"[^a-z0-9]", "", s.get("title", "").lower())[:60]

    merged = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                prev = json.load(f)
            for sec_items in prev.get("sections", {}).values():
                for s in sec_items:
                    merged[story_key(s)] = s
        except Exception:
            pass
    print(f"\nMerging: {len(merged)} previously collected + {len(all_stories)} new")

    for s in all_stories:
        k = story_key(s)
        if k in merged:
            old = merged[k]
            # Keep whichever version has the richer copy; preserve original first_seen.
            if len(s.get("copy", "")) > len(old.get("copy", "")):
                s["first_seen"] = old.get("first_seen", now.isoformat())
                merged[k] = s
            else:
                merged[k].setdefault("first_seen", now.isoformat())
        else:
            s["first_seen"] = now.isoformat()
            merged[k] = s

    # ---- Drop anything older than KEEP_DAYS ----
    cutoff_keep = now - timedelta(days=KEEP_DAYS)

    def age_ok(s):
        ts = s.get("published") or s.get("first_seen")
        if not ts:
            return True
        try:
            return datetime.fromisoformat(ts) >= cutoff_keep
        except Exception:
            return True

    kept = [s for s in merged.values() if age_ok(s)]

    # Group by section in fixed order, newest first.
    grouped = {sec: [] for sec in SECTION_ORDER}
    for s in kept:
        grouped.setdefault(s["section"], []).append(s)
    for sec in grouped:
        grouped[sec].sort(key=lambda x: (x.get("published") or x.get("first_seen") or ""), reverse=True)

    output = {
        "generated_at": now.isoformat(),
        "generated_label": now.strftime("%A %d %B %Y, %H:%M UTC"),
        "keep_days": KEEP_DAYS,
        "section_order": SECTION_ORDER,
        "sections": grouped,
        "total": len(kept),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(kept)} stories (rolling {KEEP_DAYS}-day archive) to {OUT_PATH}")


if __name__ == "__main__":
    main()
