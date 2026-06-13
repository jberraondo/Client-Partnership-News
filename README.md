# HSBC Partnership News — Morning Brief

A small tool that automatically collects each morning's sports-business news from
your usual sources, groups it into the bulletin sections, and lets you tick the
stories you want and copy a ready-formatted bulletin into your email.

## How it works (plain English)

1. **`scrape.py`** visits every source (using RSS feeds, plus Google News for sites
   that block scrapers like Sportcal), keeps the last 24–48 hours of stories, and —
   for sources we're allowed to read — pulls two clean paragraphs of copy. It saves
   everything into **`data/news.json`**.
2. **`index.html`** is the web page. It reads `news.json`, shows the stories grouped
   by section, and gives you checkboxes, source filters, a 24h/48h toggle, and a
   **Copy bulletin** button.
3. A **GitHub Action** (`.github/workflows/scrape.yml`) runs `scrape.py` automatically
   every morning so the page is fresh when you arrive.

## Using it each morning

1. Open the page (your GitHub Pages link).
2. Tick the stories you want. Sources that block auto-copy show a **READ & WRITE**
   badge — click the headline, read the article, and type the two paragraphs into the
   box (it's editable). Full-copy stories are ready to go.
3. Click **Copy bulletin** and paste into your email. Links and bold formatting carry over.

## Running it yourself (optional)

```bash
pip install -r requirements.txt
python3 scrape.py          # writes data/news.json
python3 -m http.server     # then open http://localhost:8000
```

## Editing your sources

All sources live in **`sources.py`** — add, remove, or re-order them there. Each is
either a direct RSS feed (`"kind": "direct"`) or a Google News search
(`"kind": "gnews"`) for sites that block scrapers.
