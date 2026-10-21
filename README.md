# HSBC Partnership News: Morning Brief

A small tool that collects the day's sports-business news from your usual sources and
has Claude write **two summary bullets (100–150 words)** for every story. The team
then picks the stories they want and copies a ready-formatted bulletin into an email.

## How it works (plain English)

1. **`scrape.py`** visits every source in `sources.py`: fixed news feeds, broad Google
   searches for each section, and one search per competitor bank. Claude checks the
   broad-search headlines against **`EDITORIAL_GUIDE.md`** and drops noise and
   duplicates. The collector then turns Google News links back into real article links,
   reads each kept article, and saves the stories to **`data/news.json`**. Stories still
   waiting for bullets go into `data/pending.json`.
2. **`summarise.py`** sends the waiting stories to Claude, which writes the two bullets
   following **`SUMMARY_STYLE.md`**. Claude also flags off-topic stories, such as
   Competitor News that isn't really about a bank sponsorship.
3. **`index.html`** is the web page the team uses: pick stories, tweak bullets, then
   click **Copy bulletin**.
4. A **GitHub Action** (`.github/workflows/scrape.yml`) runs steps 1 and 2 at
   **08:50 and 09:45 UK time** every day, adjusting automatically for the clocks
   changing. GitHub sometimes starts scheduled runs 5–30 minutes late.

## Using it each morning

1. Open the page (your GitHub Pages link).
2. Click **+ Add** on up to two stories per section. The live preview on the right
   shows exactly what will paste.
3. Click any bullet to edit it. A story marked **Needs a write-up** couldn't be read
   automatically: open the article and type two bullets.
4. Click **Copy bulletin** and paste into your email. The links and bold formatting carry over.

Picks and edits are saved in each person's own browser and reset each day.

## One-off setup: the Claude token

The summaries run on your Claude subscription (Pro or Max) and need no separate API bill.

1. In Terminal, run `claude setup-token` and follow the sign-in steps. It prints a long token.
2. On GitHub, open the repo → **Settings → Secrets and variables → Actions →
   New repository secret**. Name: `CLAUDE_CODE_OAUTH_TOKEN`. Value: the token.

## Changing things

- **Sources:** edit `sources.py`. Each source is either a direct RSS feed
  (`"kind": "direct"`) or a Google News search (`"kind": "gnews"`).
- **Bullet style:** edit `SUMMARY_STYLE.md`.
- **What gets kept or dropped:** edit `EDITORIAL_GUIDE.md`. Pasting in past bulletins
  as examples makes the judgement better.
- **Competitor banks:** edit `COMPETITOR_BANKS` in `sources.py` and the list in `SUMMARY_STYLE.md`.
- **Which Claude model:** set `SUMMARY_MODEL` in the workflow (default `sonnet`).

## Running it yourself (optional)

```bash
pip install -r requirements.txt
python3 scrape.py          # collects stories
python3 summarise.py       # writes the bullets (needs the claude command, signed in)
python3 -m http.server     # then open http://localhost:8000
```
