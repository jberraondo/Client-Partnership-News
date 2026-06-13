"""
Source definitions for the HSBC Partnership News scraper.

Each source has:
  section : which bulletin section it feeds
  name    : the publisher name shown in the bulletin (e.g. "BBC Sport")
  kind    : "direct"  -> a normal RSS feed (we get the real article link + can fetch body text)
            "gnews"   -> Google News RSS (used for sites that block scrapers; gives headline + snippet + link)
  url      : (direct) the RSS feed URL
  query    : (gnews)  the Google News search query

Sections are listed in SECTION_ORDER, which is the fixed order they appear in the bulletin.
"""

# Fixed order the sections appear in the bulletin.
SECTION_ORDER = [
    "Wider Sports News",
    "Rugby",
    "Tennis",
    "Golf",
    "Badminton",
    "Competitor News",
]

# How many hours back to keep stories. Jacob's rule: strict 24h (48h only when asked).
# We fetch a slightly wider window so nothing is lost to timezone edges; the page
# lets you toggle between 24h and 48h.
DEFAULT_WINDOW_HOURS = 48

SOURCES = [
    # ---- Wider Sports News ----
    # Sportcal leads the agenda. It blocks scrapers, so we reach it via Google News.
    {"section": "Wider Sports News", "name": "Sportcal",       "kind": "gnews",  "query": "site:sportcal.com"},
    {"section": "Wider Sports News", "name": "SportsPro",      "kind": "direct", "url": "https://www.sportspro.com/feed/"},
    {"section": "Wider Sports News", "name": "Sport Industry", "kind": "direct", "url": "https://sportindustry.co.uk/feed/"},
    {"section": "Wider Sports News", "name": "SportBusiness",  "kind": "direct", "url": "https://www.sportbusiness.com/feed/"},
    {"section": "Wider Sports News", "name": "Financial Times","kind": "gnews",  "query": 'site:ft.com (sport OR sponsorship OR "broadcast rights" OR Olympics OR "Premier League" OR Formula)'},

    # ---- Rugby ----
    {"section": "Rugby", "name": "BBC Sport",  "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml"},
    {"section": "Rugby", "name": "Rugby Pass", "kind": "direct", "url": "https://www.rugbypass.com/feeds/rss/"},

    # ---- Tennis ----
    {"section": "Tennis", "name": "BBC Sport",  "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml"},
    {"section": "Tennis", "name": "Sky Sports", "kind": "gnews",  "query": "site:skysports.com tennis"},

    # ---- Golf ----
    {"section": "Golf", "name": "BBC Sport", "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/golf/rss.xml"},
    {"section": "Golf", "name": "Golf.com",  "kind": "direct", "url": "https://golf.com/feed/"},
    {"section": "Golf", "name": "LIV Golf",  "kind": "gnews",  "query": "site:livgolf.com"},

    # ---- Badminton ----
    {"section": "Badminton", "name": "Olympics",         "kind": "gnews", "query": "site:olympics.com badminton"},
    {"section": "Badminton", "name": "Badminton Europe", "kind": "gnews", "query": "site:badmintoneurope.com"},

    # ---- Competitor News (banking / financial brands in sport & arts) ----
    # Only surfaces when there are genuine finance-brand-in-sport stories.
    {"section": "Competitor News", "name": "Google News", "kind": "gnews",
     "query": '(Barclays OR "Standard Chartered" OR "JP Morgan" OR Santander OR NatWest OR Monzo OR Revolut OR "Bank of America" OR Mastercard OR Visa OR "BNP Paribas") (sponsorship OR partnership OR sport)'},
]
