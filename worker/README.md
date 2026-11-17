# Partnership News helper (Cloudflare)

A tiny Cloudflare service with two jobs:

1. **Starts the collector at 07:45 UK every weekday.** GitHub's own schedule has
   been starting runs 6 to 11 hours late. Cloudflare's timers fire on time. On
   Mondays it collects 72 hours, so Friday evening and the weekend are covered.
2. **Passes on "Summarise my picks" clicks** from the page to GitHub, which writes
   bullets for those stories only (Sonnet, on your Claude subscription).

It is free on Cloudflare's standard plan. It holds the GitHub key, so the public
page never sees it. Clicks are accepted only from the page's own address and
only with your access key.

## One-off setup (about 10 minutes)

**1. Make a GitHub key for this one repo**
- Go to github.com → your photo → Settings → Developer settings → Personal access
  tokens → Fine-grained tokens → Generate new token.
- Name: `partnership-news-helper`. Expiry: 1 year (put a reminder in your calendar).
- Repository access: **Only select repositories** → `Client-Partnership-News`.
- Permissions → Repository permissions → **Actions: Read and write**. Nothing else.
- Generate, and copy the token (it is shown once).

**2. Pick an access key**
Any long phrase you will remember, for example four random words. You type it
into the page once per browser.

**3. Put the helper on Cloudflare** (in Terminal, one line at a time)
```
cd ~/Client-Partnership-News/worker
npx wrangler login                     # opens the browser to sign in to Cloudflare
npx wrangler deploy                    # prints the helper's address, ending .workers.dev
npx wrangler secret put GITHUB_TOKEN   # paste the GitHub token from step 1
npx wrangler secret put PICK_KEY       # type the access key from step 2
```

**4. Tell the page where the helper is**
In `index.html`, `SUMMARISE_URL` must be the address `wrangler deploy` printed,
with `/summarise` on the end. It is currently
`https://partnership-news-helper.berraondo-2001.workers.dev/summarise`.

Check the secrets are saved (names only, never the values): `npx wrangler secret list`
should show `GITHUB_TOKEN` and `PICK_KEY`.

## Checking it works
- Cloudflare dashboard → Workers → `partnership-news-helper` → Logs shows each
  morning start.
- GitHub → Actions shows a "Collect morning news" run at about 07:45 on weekdays,
  and a "Summarise picked stories" run each time you press the button.

## Turning it off
`npx wrangler delete` in this folder removes the helper. GitHub's own (late)
schedule keeps collecting stories as a backup.
