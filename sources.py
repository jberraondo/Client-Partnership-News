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
             and Claude checks each headline is relevant before summarising it
  title_filter : (optional) list of names; a result is kept only if its headline
             contains one of them as a whole word (case-sensitive)

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

    # ---- Wider Google searches per section ------------------------------------
    # Broad searches to catch what the fixed sources miss. They bring in noise too,
    # so Claude checks every headline against EDITORIAL_GUIDE.md before summarising.
    {"section": "Wider Sports News", "name": "Sports business search", "kind": "gnews", "max": 15, "wide": True,
     "query": '(sport OR sports) (sponsorship OR "media rights" OR "broadcast rights" OR "naming rights" '
              'OR "commercial partner" OR "title partner") when:1d'},
    # Rugby: sevens and rugby union only (covers men's and women's in both).
    {"section": "Rugby", "name": "Rugby search", "kind": "gnews", "max": 15, "wide": True,
     "query": '"rugby sevens" OR SVNS OR "rugby union" when:1d'},
    {"section": "Rugby", "name": "Rugby news search", "kind": "gnews", "max": 15, "wide": True,
     "query": '"rugby news" when:1d'},
    {"section": "Racket", "name": "Tennis news search", "kind": "gnews", "max": 15, "wide": True,
     "query": '"tennis news" when:1d'},
    {"section": "Racket", "name": "Tennis search", "kind": "gnews", "max": 15, "wide": True,
     "query": 'tennis (ATP OR WTA OR "Grand Slam") when:1d'},
    {"section": "Racket", "name": "Badminton news search", "kind": "gnews", "max": 10, "wide": True,
     "query": '"badminton news" when:1d'},
    {"section": "Racket", "name": "Badminton search", "kind": "gnews", "max": 10, "wide": True,
     "query": 'badminton (BWF OR "World Tour") when:1d'},
    {"section": "Golf", "name": "Golf news search", "kind": "gnews", "max": 15, "wide": True,
     "query": '"golf news" when:1d'},
    {"section": "Golf", "name": "Golf search", "kind": "gnews", "max": 15, "wide": True,
     "query": '"DP World Tour" OR "PGA Tour" OR "LIV Golf" OR "Ryder Cup" OR LPGA when:1d'},

]

# ---- Competitor News --------------------------------------------------------
# The banks 160/90 tracks, doing sponsorship or partnership deals in sport or the
# arts. One Google News search per bank (grouped searches missed real stories).
# Each entry: (name, Google search terms, names that must appear in the headline).
# Add, remove or edit banks here, and keep the list in SUMMARY_STYLE.md in step.
COMPETITOR_BANKS = [
    ("Barclays",              'Barclays',                                     ["Barclays"]),
    ("Lloyds Bank",           '"Lloyds Bank" OR Lloyds',                      ["Lloyds"]),
    ("NatWest",               'NatWest',                                      ["NatWest", "Natwest"]),
    ("Santander UK",          'Santander',                                    ["Santander"]),
    ("Nationwide",            '"Nationwide Building Society" OR Nationwide',  ["Nationwide"]),
    ("Royal Bank of Scotland",'"Royal Bank of Scotland" OR RBS',              ["Royal Bank of Scotland", "RBS"]),
    ("Virgin Money",          '"Virgin Money"',                               ["Virgin Money"]),
    ("Metro Bank",            '"Metro Bank"',                                 ["Metro Bank"]),
    ("Monzo",                 'Monzo',                                        ["Monzo"]),
    ("Starling Bank",         '"Starling Bank" OR Starling',                  ["Starling"]),
    ("Revolut",               'Revolut',                                      ["Revolut"]),
    ("Chase UK",              '"Chase UK" OR Chase',                          ["Chase", "JPMorganChase"]),
    ("Standard Chartered",    '"Standard Chartered"',                         ["Standard Chartered", "StanChart"]),
    ("Citi",                  'Citi OR Citibank',                             ["Citi", "Citibank", "Citigroup"]),
    ("J.P. Morgan",           '"J.P. Morgan" OR JPMorgan OR JPMorganChase',   ["J.P. Morgan", "JP Morgan", "JPMorgan", "JPMorganChase"]),
    ("BNP Paribas",           '"BNP Paribas"',                                ["BNP Paribas", "BNP"]),
    ("Deutsche Bank",         '"Deutsche Bank"',                              ["Deutsche Bank"]),
    ("UBS",                   'UBS',                                          ["UBS"]),
]
_SPORT = ('sport OR sports OR football OR soccer OR tennis OR golf OR rugby OR cricket OR NBA OR NFL OR MLS '
          'OR Olympics OR cycling OR stadium OR F1 OR "Formula 1"')
_ARTS = ('art OR arts OR exhibition OR gallery OR museum OR collection OR "Art Basel" OR Frieze OR festival '
         'OR theatre OR orchestra OR opera OR ballet OR music OR culture')
_DEAL = ('sponsorship OR sponsor OR partnership OR "official partner" OR "naming rights" OR "jersey patch" '
         'OR "presenting partner" OR "title sponsor"')
_NOISE = '-earnings -shares -stock -"price target" -dividend -"Lloyds Register" -"Chase Elliott"'
for _name, _terms, _aliases in COMPETITOR_BANKS:
    SOURCES.append({
        "section": "Competitor News",
        "name": f"{_name} search",
        "kind": "gnews",
        "wide": True,
        "max": 8,
        "title_filter": _aliases,
        "query": f"({_terms}) ({_SPORT} OR {_ARTS} OR {_DEAL}) {_NOISE} when:2d",
    })
