"""
Source definitions for the HSBC Partnership News scraper.

Each source has:
  section : which bulletin section it feeds
  name    : the publisher name shown in the bulletin (e.g. "BBC Sport")
  kind    : "direct"  -> a normal RSS feed (we get the real article link + can fetch body text)
            "gnews"   -> Google News RSS (used for sites that block scrapers; gives headline + snippet + link)
  url      : (direct) the RSS feed URL
  query    : (gnews)  the Google News search query
  wide     : (gnews)  True for searches across all publishers — each story then shows
             its real publisher (e.g. "Talksport") instead of the search's name

Sections are listed in SECTION_ORDER, which is the fixed order they appear in the bulletin.
"""

# Fixed order the sections appear in the bulletin.
SECTION_ORDER = [
    "Competitor News",
    "Wider Sports News",
    "Rugby",
    "Racket",      # tennis + badminton
    "Golf",
]

# Sections that have been renamed or merged, so older saved stories move across.
SECTION_RENAMES = {"Tennis": "Racket", "Badminton": "Racket"}

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
    {"section": "Rugby", "name": "The Independent", "kind": "direct", "url": "https://www.independent.co.uk/sport/rugby/rugby-union/rss"},

    # ---- Racket (tennis + badminton) ----
    {"section": "Racket", "name": "BBC Sport",    "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml"},
    {"section": "Racket", "name": "Sky Sports",   "kind": "gnews",  "query": "site:skysports.com/tennis/news"},
    {"section": "Racket", "name": "The Guardian", "kind": "direct", "url": "https://www.theguardian.com/sport/tennis/rss"},
    {"section": "Racket", "name": "Tennis365",    "kind": "direct", "url": "https://www.tennis365.com/feed"},
    {"section": "Racket", "name": "Olympics",         "kind": "gnews", "query": "site:olympics.com badminton"},
    {"section": "Racket", "name": "Badminton Europe", "kind": "gnews", "query": "site:badmintoneurope.com"},

    # ---- Golf ----
    {"section": "Golf", "name": "BBC Sport", "kind": "direct", "url": "https://feeds.bbci.co.uk/sport/golf/rss.xml"},
    {"section": "Golf", "name": "Golf.com",  "kind": "direct", "url": "https://golf.com/feed/"},
    {"section": "Golf", "name": "LIV Golf",  "kind": "gnews",  "query": "site:livgolf.com"},
    {"section": "Golf", "name": "Golf Monthly", "kind": "direct", "max": 8, "url": "https://www.golfmonthly.com/feeds/all"},

    # ---- Safety-net searches across ALL of Google News -------------------------
    # These catch HSBC-property stories that appear in less obvious outlets, so we
    # never miss a relevant angle. Kept tight to HSBC's actual properties to avoid
    # flooding the page; capped lower with "max". Toggle them off on the page if noisy.
    {"section": "Wider Sports News", "name": "HSBC watch", "kind": "gnews", "max": 8, "wide": True,
     "query": 'HSBC (sport OR sponsorship OR partnership OR rugby OR tennis OR golf OR badminton OR arts OR SVNS OR "Queen\'s Club" OR "Abu Dhabi")'},

    {"section": "Rugby", "name": "SVNS watch", "kind": "gnews", "max": 6, "wide": True,
     "query": '"HSBC SVNS" OR "rugby sevens" OR "SVNS Series" OR "World Rugby Sevens"'},
    {"section": "Racket", "name": "HSBC tennis watch", "kind": "gnews", "max": 6, "wide": True,
     "query": '"Emma Raducanu" OR "Jack Draper" OR "HSBC Championships" OR "Queen\'s Club"'},
    {"section": "Golf", "name": "HSBC golf watch", "kind": "gnews", "max": 6, "wide": True,
     "query": '"Bryson DeChambeau" OR "LIV Golf" OR "Abu Dhabi HSBC" OR "Abu Dhabi Championship"'},
    {"section": "Racket", "name": "BWF watch", "kind": "gnews", "max": 6, "wide": True,
     "query": '"BWF World Tour" OR "BWF" OR "Badminton World Federation"'},

]

# ---- Competitor News --------------------------------------------------------
# The banks 160/90 tracks, making sponsorship or partnership moves in sport or
# the arts. Add or remove names in COMPETITOR_BANKS (and in SUMMARY_STYLE.md).
# The names are split across several searches because Google News is unreliable
# with one huge query; results are de-duplicated automatically.
COMPETITOR_BANKS = [
    "Barclays", "Lloyds", "Santander", "NatWest", '"Metro Bank"',
    "Citi", "Citibank", "Revolut", "Monzo", "Chase", "JPMorganChase",
    '"Standard Chartered"', '"BNP Paribas"', '"JP Morgan"', '"J.P. Morgan"', "JPMorgan",
    '"Deutsche Bank"',
]
_SPONSOR = '(sponsorship OR sponsor OR partnership OR "official partner" OR "naming rights" OR "jersey patch" OR deal)'
_SPORT_ARTS = ('(sport OR sports OR football OR soccer OR tennis OR golf OR rugby OR cricket OR '
               'NBA OR NFL OR MLS OR Olympics OR cycling OR stadium OR arts OR theatre OR museum OR festival)')
_EXCLUDE = '-"Lloyds Register" -"Chase Elliott" -"Chase Field"'
_GROUP_SIZE = 6
for _i in range(0, len(COMPETITOR_BANKS), _GROUP_SIZE):
    _grp = " OR ".join(COMPETITOR_BANKS[_i:_i + _GROUP_SIZE])
    SOURCES.append({
        "section": "Competitor News",
        "name": "Bank search",
        "kind": "gnews",
        "wide": True,
        "max": 8,
        "query": f"({_grp}) {_SPONSOR} {_SPORT_ARTS} {_EXCLUDE} when:2d",
    })
