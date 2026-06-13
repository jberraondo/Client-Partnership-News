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
    {"section": "Tennis", "name": "Sky Sports", "kind": "gnews",  "query": "site:skysports.com/tennis"},

    # ---- Golf ----
    {"section": "Golf", "name": "BBC Sport", "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/golf/rss.xml"},
    {"section": "Golf", "name": "Golf.com",  "kind": "direct", "url": "https://golf.com/feed/"},
    {"section": "Golf", "name": "LIV Golf",  "kind": "gnews",  "query": "site:livgolf.com"},

    # ---- Badminton ----
    {"section": "Badminton", "name": "Olympics",         "kind": "gnews", "query": "site:olympics.com badminton"},
    {"section": "Badminton", "name": "Badminton Europe", "kind": "gnews", "query": "site:badmintoneurope.com"},

    # ---- Safety-net searches across ALL of Google News -------------------------
    # These catch HSBC-property stories that appear in less obvious outlets, so we
    # never miss a relevant angle. Kept tight to HSBC's actual properties to avoid
    # flooding the page; capped lower with "max". Toggle them off on the page if noisy.
    {"section": "Wider Sports News", "name": "HSBC watch", "kind": "gnews", "max": 8,
     "query": 'HSBC (sport OR sponsorship OR partnership OR rugby OR tennis OR golf OR badminton OR arts OR SVNS OR "Queen\'s Club" OR "Abu Dhabi")'},

    {"section": "Rugby", "name": "SVNS watch", "kind": "gnews", "max": 6,
     "query": '"HSBC SVNS" OR "rugby sevens" OR "SVNS Series" OR "World Rugby Sevens"'},
    {"section": "Tennis", "name": "HSBC tennis watch", "kind": "gnews", "max": 6,
     "query": '"Emma Raducanu" OR "Jack Draper" OR "HSBC Championships" OR "Queen\'s Club"'},
    {"section": "Golf", "name": "HSBC golf watch", "kind": "gnews", "max": 6,
     "query": '"Bryson DeChambeau" OR "LIV Golf" OR "Abu Dhabi HSBC" OR "Abu Dhabi Championship"'},
    {"section": "Badminton", "name": "BWF watch", "kind": "gnews", "max": 6,
     "query": '"BWF World Tour" OR "BWF" OR "Badminton World Federation"'},

]

# ---- Competitor News (the banks 160/90 tracks, strictly in a sport/arts context) ----
# Only the brands below, and only when tied to sponsorship/partnership in sport or arts.
# Split across a few searches because Google News is unreliable with one huge query;
# they all feed the "Competitor News" section and are de-duplicated automatically.
_SPONSOR = '(sponsorship OR partnership OR sponsor OR "official partner" OR deal)'
_SPORT_ARTS = ('(sport OR sports OR arts OR football OR tennis OR golf OR rugby OR '
               'cricket OR Olympics OR athletics OR stadium OR theatre OR music OR festival)')
_COMPETITOR_GROUPS = [
    '(Barclays OR "Lloyds Bank" OR NatWest OR "Santander" OR Nationwide)',
    # Halifax/RBS group — exclude the Halifax sports clubs (town, not the bank).
    '(Halifax OR "Royal Bank of Scotland" OR RBS OR TSB OR "Virgin Money" OR "Metro Bank") '
    '-"Halifax Town" -"Halifax Panthers" -"Halifax Wanderers" -"FC Halifax"',
    '(Monzo OR "Starling Bank" OR Revolut OR "Chase UK" OR "Standard Chartered")',
    '(Citi OR "J.P. Morgan" OR "JP Morgan" OR "BNP Paribas" OR "Deutsche Bank")',
]
for _grp in _COMPETITOR_GROUPS:
    SOURCES.append({
        "section": "Competitor News",
        "name": "Google News",
        "kind": "gnews",
        "query": f"{_grp} {_SPONSOR} {_SPORT_ARTS}",
    })
