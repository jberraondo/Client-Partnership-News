# HSBC Partnership News: Morning Brief

A small tool that collects the day's sports-business news from your usual sources.
The team picks the stories they want, asks Claude to summarise **just those**, and
copies a ready-formatted bulletin into an email.

## How it works (plain English)

1. **`scrape.py`** visits every source in `sources.py`: fixed news feeds, broad Google
   searches for each section, and one search per competitor brand (the 33 in
   `COMPETITOR_BANKS`). A competitor story only counts if its headline names one of
   the 33. Claude's light model (Haiku) checks headlines against
   **`EDITORIAL_GUIDE.md`** and drops noise and duplicates. The collector then turns
   Google News links back into real article links, reads each kept article, and saves
   the stories to **`data/news.json`**. Article text is kept for three days in
   `data/pending.json`, ready for summaries.
2. **No summaries are written automatically.** On the page, pick stories and click
   **Summarise my picks**. That starts **`summarise.py --ids`**, which has Claude
   (Sonnet) write two bullets for those stories only, following **`SUMMARY_STYLE.md`**.
   The bullets appear on the page about 3 minutes later.
3. **`index.html`** is the web page the team uses: pick, summarise, tweak, then
   **Copy bulletin**.
4. **When it runs:** a small Cloudflare helper (`worker/`) starts the collector at
   **07:45 UK every weekday** (72 hours on Mondays, to cover the weekend) and passes on
   the summarise button. GitHub's own schedule also runs at 08:50 and 09:45 UK daily as
   a backup, but it has been starting hours late. Setup: `worker/README.md`.

## Using it each morning

1. Open the page (your GitHub Pages link).
2. Click **+ Add** on up to two stories per section. The live preview on the right
   shows exactly what will paste.
3. Click **Summarise my picks**. The first time, it asks for the access key. Wait about
   3 minutes; the page refreshes itself when the bullets arrive.
4. Click any bullet to edit it, or type your own for any story.
5. Click **Copy bulletin** and paste into your email. The links and bold formatting carry over.

Picks and edits are saved in each person's own browser and reset each day.

## Where the Claude allowance goes

- Headline check: Haiku, the cheapest model, on new headlines only.
- Summaries: Sonnet, only for stories someone picked, using the article text the
  collector already saved, so Claude rarely has to fetch the page itself.

## One-off setup: the Claude token

The headline check and summaries run on your Claude subscription (Pro or Max) and need
no separate API bill.

1. In Terminal, run `claude setup-token` and follow the sign-in steps. It prints a long token.
2. On GitHub, open the repo → **Settings → Secrets and variables → Actions →
   New repository secret**. Name: `CLAUDE_CODE_OAUTH_TOKEN`. Value: the token.

## Changing things

- **Sources:** edit `sources.py`. Each source is either a direct RSS feed
  (`"kind": "direct"`) or a Google News search (`"kind": "gnews"`).
- **Bullet style:** edit `SUMMARY_STYLE.md`.
- **What gets kept or dropped:** edit `EDITORIAL_GUIDE.md`.
- **Competitor brands:** edit `COMPETITOR_BANKS` in `sources.py` and the list in
  `SUMMARY_STYLE.md`. Keep the two in step.
- **Which Claude model:** `SUMMARY_MODEL` (default `sonnet`) and `CHECK_MODEL`
  (default `haiku`).

## Running it yourself (optional)

```bash
pip install -r requirements.txt
python3 scrape.py                      # collects stories
python3 summarise.py --check-only      # headline check only
python3 summarise.py --ids ID1,ID2     # bullets for these stories (needs the claude command)
python3 -m http.server                 # then open http://localhost:8000
```
