#!/usr/bin/env python3
"""
HSBC Partnership News scraper.

Pulls recent stories from every source in sources.py, turns Google News links
back into the real article links, reads the article text for any NEW story, and
writes everything to data/news.json grouped by section.

Stories that still need their two summary bullets are listed (with their
article text) in data/pending.json. summarise.py then asks Claude to write the
bullets and folds them back into data/news.json.

Run it with:   python3 scrape.py
Options (environment variables):
   WINDOW_HOURS   how many hours back to collect (default 48)
   KEEP_DAYS      how many days of stories to keep in the archive (default 7)
   MAX_PER_SOURCE max stories kept per source (default 12)
   FETCH_BODIES   "1" to read article text (default 1)
   FETCH_BROWSER  "1" to use a headless browser for sites that block us (default 1)
"""

from __future__ import annotations  # allow modern type hints on Python 3.9

import os
import re
import json
import html
import time
import hashlib
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
FETCH_BROWSER = os.environ.get("FETCH_BROWSER", "1") == "1"
# Only stories this fresh get sent for AI summaries (saves your Claude allowance).
SUMMARY_WINDOW_HOURS = int(os.environ.get("SUMMARY_WINDOW_HOURS", 30))
ARTICLE_MAX_WORDS = 900   # plenty for two bullets; keeps the AI step light

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_PATH = os.path.join(DATA_DIR, "news.json")
PENDING_PATH = os.path.join(DATA_DIR, "pending.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}
# Cookie that skips Google's EU consent wall.
GOOGLE_CONSENT = {"name": "SOCS", "value": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg",
                  "domain": ".google.com", "path": "/"}

# Sources we don't bother browser-fetching: Olympics hard-blocks data-centre
# servers; the FT is paywalled. The AI step can still try these itself.
SKIP_BROWSER_SOURCES = {"Olympics", "Financial Times"}

# Pages that aren't written articles (video clips, galleries, live blogs).
NOT_AN_ARTICLE = re.compile(r"/(video|videos|watch|gallery|galleries|live|podcast)s?/", re.I)


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


def strip_publisher_suffix(title: str) -> str:
    """Google News titles end with ' - Publisher'; drop that tail."""
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip() if " - " in title else title


def story_id(link: str) -> str:
    """Short, stable ID for a story (used to match up AI summaries)."""
    return hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Google News links
# ---------------------------------------------------------------------------
# Google News RSS gives a scrambled news.google.com link rather than the real
# article address. Google's own page swaps it for the real one with two quick
# requests; we do the same so we can actually read the article.
_gsession = requests.Session()
_gsession.headers.update(HEADERS)
_gsession.cookies.set(GOOGLE_CONSENT["name"], GOOGLE_CONSENT["value"], domain=GOOGLE_CONSENT["domain"])


def decode_gnews_link(link: str) -> str:
    """Return the real article URL behind a Google News link ("" if it fails)."""
    try:
        art_id = urllib.parse.urlparse(link).path.rstrip("/").split("/")[-1]
        page = _gsession.get(f"https://news.google.com/articles/{art_id}", timeout=15)
        div = BeautifulSoup(page.text, "html.parser").select_one("c-wiz > div[jscontroller]")
        if not div:
            return ""
        sig, ts = div.get("data-n-a-sg"), div.get("data-n-a-ts")
        inner = ('["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,'
                 'null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
                 f'"{art_id}",{ts},"{sig}"]')
        body = "f.req=" + urllib.parse.quote(json.dumps([[["Fbv4je", inner]]]))
        res = _gsession.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data=body, timeout=15)
        data = json.loads(res.text.split("\n\n")[1])[:-2]
        url = json.loads(data[0][2])[1]
        return url if url.startswith("http") else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Article text
# ---------------------------------------------------------------------------
def tidy_article(text: str) -> str:
    """Keep proper sentence-like paragraphs (skip captions, stat lines), capped in length."""
    paras = [line.strip() for line in (text or "").split("\n")
             if len(line.strip()) >= 40 and any(p in line for p in ".!?")]
    out, words = [], 0
    for p in paras:
        out.append(p)
        words += len(p.split())
        if words >= ARTICLE_MAX_WORDS:
            break
    result = "\n\n".join(out)
    # Reject thin extractions (homepages, cookie notices) — the AI step will
    # try the link itself instead.
    return result if len(result) >= 250 else ""


def fetch_article(url: str) -> str:
    """Best-effort: fetch the article and return its main text. "" on any failure."""
    if not (FETCH_BODIES and HAVE_TRAFILATURA and url):
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(downloaded, include_comments=False,
                                   include_tables=False, favor_precision=True) or ""
    except Exception:
        return ""
    return tidy_article(text)


def browser_fetch(stories: list) -> None:
    """Read articles that blocked the simple fetch, using a headless browser."""
    targets = [s for s in stories if not s["article_text"] and s["source"] not in SKIP_BROWSER_SOURCES]
    if not (FETCH_BROWSER and HAVE_TRAFILATURA and targets):
        return
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("   (playwright not installed — skipping browser fetch)")
        return

    print(f"\nBrowser-fetching {len(targets)} articles that blocked the simple fetch...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"], locale="en-GB")
        ctx.add_cookies([GOOGLE_CONSENT])
        page = ctx.new_page()
        for s in targets:
            try:
                page.goto(s["link"], wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2500)  # let the article render
                text = trafilatura.extract(page.content(), include_comments=False,
                                           include_tables=False, favor_precision=True) or ""
                s["article_text"] = tidy_article(text)
            except Exception:
                pass
        browser.close()
    print(f"   read {sum(1 for s in targets if s['article_text'])}/{len(targets)}")


def opening_copy(text: str, target: int = 175) -> str:
    """Stop-gap copy (the article's opening, as two chunks) shown until the AI bullets arrive."""
    paras = [p for p in (text or "").split("\n\n") if p.strip()]
    out, i = [], 0
    for _ in range(2):
        chunk = ""
        while i < len(paras) and len(chunk) < target:
            chunk = (chunk + " " + paras[i]).strip()
            i += 1
        if chunk:
            out.append(chunk)
    return "\n\n".join(out)


# ---------------------------------------------------------------------------
# Feeds
# ---------------------------------------------------------------------------
def collect_from_source(src: dict) -> list[dict]:
    """Fetch and normalise stories from a single source."""
    feed_url = gnews_url(src["query"]) if src["kind"] == "gnews" else src["url"]
    try:
        feed = feedparser.parse(feed_url, request_headers=HEADERS)
    except Exception as e:
        print(f"   ! {src['name']}: feed error {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    stories = []
    for entry in feed.entries:
        published = parse_date(entry)
        if published and published < cutoff:
            continue

        title = strip_publisher_suffix(clean_text(entry.get("title", "")))
        link = entry.get("link", "")
        if not title or not link:
            continue

        stories.append({
            "section": src["section"],
            "source": src["name"],
            "kind": src["kind"],
            "title": title,
            "feed_link": link,     # as given by the feed (Google News links are scrambled)
            "link": link,          # the real article link (fixed up later for Google News)
            "published": published.isoformat() if published else None,
            "published_label": published.strftime("%a %d %b, %H:%M") if published else "",
            "summary": clean_text(entry.get("summary", "")),  # short feed snippet
        })
        if len(stories) >= src.get("max", MAX_PER_SOURCE):
            break
    return stories


def main():
    print(f"Scraping {len(SOURCES)} sources, last {WINDOW_HOURS}h\n")
    now = datetime.now(timezone.utc)

    # ---- Load the archive so we only do the slow work for NEW stories ----
    archive = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                prev = json.load(f)
            for sec_items in prev.get("sections", {}).values():
                for s in sec_items:
                    archive[s.get("feed_link") or s.get("link")] = s
        except Exception:
            pass

    # ---- Collect from every feed ----
    fresh, seen_titles = [], set()
    for src in SOURCES:
        unique = []
        for s in collect_from_source(src):
            key = re.sub(r"[^a-z0-9]", "", s["title"].lower())[:60]
            if key and key not in seen_titles:
                seen_titles.add(key)
                unique.append(s)
        print(f"   {src['section']:18s} {src['name']:18s} {len(unique):2d} stories")
        fresh.extend(unique)

    new = [s for s in fresh if s["feed_link"] not in archive]
    print(f"\n{len(new)} new stories (of {len(fresh)} collected)")

    # ---- New stories: real links, then article text ----
    gnews = [s for s in new if s["kind"] == "gnews"]
    if gnews:
        print(f"Unscrambling {len(gnews)} Google News links...")
        for s in gnews:
            s["link"] = decode_gnews_link(s["feed_link"]) or s["feed_link"]
            time.sleep(0.5)  # be polite to Google
        print(f"   resolved {sum(1 for s in gnews if s['link'] != s['feed_link'])}/{len(gnews)}")

    for s in new:
        s["id"] = story_id(s["feed_link"])
        s["bullets"] = []
        s["is_article"] = not NOT_AN_ARTICLE.search(s["link"])
        s["article_text"] = ""

    readable = [s for s in new if s["is_article"] and "news.google.com" not in s["link"]]
    if FETCH_BODIES and HAVE_TRAFILATURA and readable:
        print(f"Reading {len(readable)} articles...")
        for s in readable:
            s["article_text"] = fetch_article(s["link"])
            time.sleep(0.3)  # be polite
        print(f"   read {sum(1 for s in readable if s['article_text'])}/{len(readable)}")
        browser_fetch(readable)

    for s in new:
        s["copy"] = opening_copy(s["article_text"])
        s["first_seen"] = now.isoformat()

    # ---- Merge into the archive (existing stories keep their bullets) ----
    merged = dict(archive)
    for s in new:
        merged[s["feed_link"]] = s

    # ---- Drop anything older than KEEP_DAYS ----
    cutoff_keep = now - timedelta(days=KEEP_DAYS)

    def when(s):
        ts = s.get("published") or s.get("first_seen")
        try:
            return datetime.fromisoformat(ts) if ts else now
        except Exception:
            return now

    kept = [s for s in merged.values() if when(s) >= cutoff_keep]

    # ---- Stories still needing AI bullets → pending.json ----
    cutoff_sum = now - timedelta(hours=SUMMARY_WINDOW_HOURS)
    pending = []
    for s in kept:
        s.setdefault("id", story_id(s.get("feed_link") or s["link"]))
        s.setdefault("bullets", [])
        if s["bullets"] or s.get("summary_status") == "skipped" or not s.get("is_article", True):
            continue
        if when(s) < cutoff_sum or s.get("summary_attempts", 0) >= 2:
            continue
        pending.append({
            "id": s["id"], "section": s["section"], "source": s["source"],
            "title": s["title"], "link": s["link"],
            "article_text": s.get("article_text", ""),
        })
    # The article text is only needed for the AI step — keep it out of news.json
    # so the web page stays quick to load.
    for s in kept:
        s.pop("article_text", None)
        s.pop("body", None)

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

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(kept)} stories to {OUT_PATH}")
    print(f"{len(pending)} stories waiting for AI bullets in {PENDING_PATH}")


if __name__ == "__main__":
    main()
