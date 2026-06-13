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

    paras = []
    for line in text.split("\n"):
        line = line.strip()
        # Keep proper sentence-like paragraphs; skip headings, stat lines, captions.
        if len(line) >= 80 and ("." in line or "!" in line or "?" in line):
            paras.append(line)
        if len(paras) >= 2:
            break
    return "\n\n".join(paras)


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
        if len(stories) >= MAX_PER_SOURCE:
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

    # Group by section in fixed order.
    grouped = {sec: [] for sec in SECTION_ORDER}
    for s in all_stories:
        grouped.setdefault(s["section"], []).append(s)

    # Sort each section newest-first.
    for sec in grouped:
        grouped[sec].sort(key=lambda x: x["published"] or "", reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_label": datetime.now(timezone.utc).strftime("%A %d %B %Y, %H:%M UTC"),
        "window_hours": WINDOW_HOURS,
        "section_order": SECTION_ORDER,
        "sections": grouped,
        "total": len(all_stories),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(all_stories)} stories to {OUT_PATH}")


if __name__ == "__main__":
    main()
