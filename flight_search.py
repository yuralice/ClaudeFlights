#!/usr/bin/env python3
"""
Flight Price Comparison — IAH → Asia (December 2026)
2 Adults + 1 Infant | Premium Economy & Business Class

Setup:
    pip install -r requirements.txt
    cp .env.example .env   # add your Kiwi API key
    python flight_search.py

Get a free Kiwi API key at: https://tequila.kiwi.com/
(Sign up → My Apps → Create new app → copy the API key)
"""

import os
import sys
import json
import requests
import webbrowser
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ─── SEARCH PARAMETERS ────────────────────────────────────────────────────────

KIWI_API_KEY = os.getenv("KIWI_API_KEY", "")
KIWI_BASE    = "https://api.tequila.kiwi.com/v2/search"

ORIGIN      = "IAH"
DATE_FROM   = "18/12/2026"
DATE_TO     = "21/12/2026"
CURRENCY    = "USD"
MAX_RESULTS = 5

DESTINATIONS = [
    {"code": "NRT", "name": "Tokyo Narita",   "country": "Japan",             "flag": "🇯🇵"},
    {"code": "HND", "name": "Tokyo Haneda",   "country": "Japan",             "flag": "🇯🇵"},
    {"code": "KIX", "name": "Osaka",          "country": "Japan",             "flag": "🇯🇵"},
    {"code": "TPE", "name": "Taipei",         "country": "Taiwan",            "flag": "🇹🇼"},
    {"code": "ICN", "name": "Seoul Incheon",  "country": "South Korea (hub)", "flag": "🇰🇷"},
    {"code": "HKG", "name": "Hong Kong",      "country": "Hub / Gateway",     "flag": "🇭🇰"},
]

# Cabin code → Kiwi code, display name, passenger config, infant note
CABINS = [
    {
        "code": "W",
        "name": "Premium Economy",
        "pax": {"adults": 2, "children": 1},
        "infant_note": "Daughter needs own seat — booked as child fare",
    },
    {
        "code": "C",
        "name": "Business Class",
        "pax": {"adults": 2, "infants": 1},
        "infant_note": "Daughter as lap infant — typically 10% of adult fare",
    },
]


# ─── POINTS & AWARD DATA ──────────────────────────────────────────────────────

POINTS_CURRENCIES = {
    "Amex Membership Rewards": {"cpp": 1.8, "color": "#016FD0"},
    "Chase Ultimate Rewards":  {"cpp": 1.9, "color": "#117ACA"},
    "Capital One Miles":       {"cpp": 1.7, "color": "#D03027"},
}

AWARD_OPTIONS = [
    {
        "rank": 1,
        "badge": "Best for Japan",
        "program": "United MileagePlus",
        "currency": "Chase Ultimate Rewards",
        "airline": "ANA (All Nippon Airways)",
        "cabin": "Business",
        "miles_per_person": 85_000,
        "route": "IAH → NRT / TYO",
        "note": (
            "IAH is United's biggest hub — often has great nonstop or 1-stop options via "
            "West Coast to NRT. ANA business (NH) is world-class. Book at united.com under "
            "Award Travel. Chase UR transfers to United at 1:1."
        ),
        "availability": "Limited",
        "avail_class": "avail-limit",
        "avail_icon": "🔴",
    },
    {
        "rank": 2,
        "badge": "Best Value",
        "program": "Aeroplan (Air Canada)",
        "currency": "Chase UR or Capital One",
        "airline": "ANA / Air Canada (Star Alliance)",
        "cabin": "Business",
        "miles_per_person": 75_000,
        "route": "IAH → NRT / TYO",
        "note": (
            "Often fewer miles than United for the same ANA metal. No fuel surcharges on ANA. "
            "Aeroplan uses dynamic pricing so rates can vary — check aircanada.com/aeroplan. "
            "Both Chase UR and Capital One transfer at 1:1."
        ),
        "availability": "Moderate",
        "avail_class": "avail-warn",
        "avail_icon": "⚠️",
    },
    {
        "rank": 3,
        "badge": "Best Product",
        "program": "Singapore KrisFlyer",
        "currency": "Amex, Chase UR, or Capital One",
        "airline": "Singapore Airlines",
        "cabin": "Business",
        "miles_per_person": 98_000,
        "route": "IAH → SIN → NRT / TPE",
        "note": (
            "Singapore Airlines business class is consistently rated the world's best. "
            "Layover in Singapore adds a stop but the product is worth it. All three of your "
            "points currencies transfer to KrisFlyer at 1:1."
        ),
        "availability": "Good",
        "avail_class": "avail-ok",
        "avail_icon": "✅",
    },
    {
        "rank": 4,
        "badge": "Solid Backup",
        "program": "United MileagePlus",
        "currency": "Chase Ultimate Rewards",
        "airline": "United / ANA",
        "cabin": "Premium Economy",
        "miles_per_person": 60_000,
        "route": "IAH → NRT / TYO",
        "note": (
            "More saver availability than business class. Good option if business awards are "
            "sold out around the holidays. Your daughter would need a separate child booking "
            "(usually ~75% of adult rate) or you book infants as a separate ticket."
        ),
        "availability": "Good",
        "avail_class": "avail-ok",
        "avail_icon": "✅",
    },
    {
        "rank": 5,
        "badge": "Best for Taiwan",
        "program": "Cathay Pacific Asia Miles",
        "currency": "Amex Membership Rewards",
        "airline": "Cathay Pacific",
        "cabin": "Business",
        "miles_per_person": 100_000,
        "route": "IAH → HKG → TPE / NRT",
        "note": (
            "Great routing for Taiwan via Hong Kong. Cathay business class is excellent. "
            "Note: Cathay charges fuel surcharges which add $200–500 per ticket. "
            "Amex MR transfers to Asia Miles at 1:1."
        ),
        "availability": "Moderate",
        "avail_class": "avail-warn",
        "avail_icon": "⚠️",
    },
]


# ─── FLIGHT SEARCH ────────────────────────────────────────────────────────────

def search_kiwi(destination, cabin):
    params = {
        "fly_from": ORIGIN,
        "fly_to": destination["code"],
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "curr": CURRENCY,
        "sort": "price",
        "limit": MAX_RESULTS,
        "selected_cabins": cabin["code"],
        **cabin["pax"],
    }
    try:
        r = requests.get(
            KIWI_BASE,
            headers={"apikey": KIWI_API_KEY},
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"  ⚠  {destination['code']}/{cabin['name']}: {e}", file=sys.stderr)
        return []

    results = []
    for f in data.get("data", []):
        dep = f.get("local_departure", "")
        arr = f.get("local_arrival", "")
        try:
            dep_str = datetime.fromisoformat(dep.replace("Z", "")).strftime("%a %b %d, %H:%M")
        except Exception:
            dep_str = dep[:16] or "—"
        try:
            arr_str = datetime.fromisoformat(arr.replace("Z", "")).strftime("%a %b %d, %H:%M")
        except Exception:
            arr_str = arr[:16] or "—"

        secs = f.get("duration", {}).get("total", 0)
        h, m = divmod(secs // 60, 60)

        results.append({
            "price":            f.get("price", 0),
            "airline":          ", ".join(f.get("airlines", ["?"])),
            "duration":         f"{h}h {m:02d}m",
            "stops":            max(0, len(f.get("route", [])) - 1),
            "departure":        dep_str,
            "arrival":          arr_str,
            "link":             f.get("deep_link", "#"),
            "cabin":            cabin["name"],
            "infant_note":      cabin["infant_note"],
            "destination":      destination["name"],
            "destination_code": destination["code"],
            "flag":             destination["flag"],
            "country":          destination["country"],
        })
    return results


def get_demo_flights():
    return [
        {"price": 2847, "airline": "EVA Air",         "duration": "18h 30m", "stops": 1, "departure": "Fri Dec 18, 14:25", "arrival": "Sun Dec 20, 10:55", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Taipei",       "destination_code": "TPE", "flag": "🇹🇼", "country": "Taiwan"},
        {"price": 3104, "airline": "ANA",              "duration": "21h 15m", "stops": 1, "departure": "Fri Dec 18, 11:10", "arrival": "Sun Dec 20, 09:25", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Tokyo Narita", "destination_code": "NRT", "flag": "🇯🇵", "country": "Japan"},
        {"price": 3290, "airline": "Korean Air",       "duration": "20h 45m", "stops": 1, "departure": "Sat Dec 19, 09:50", "arrival": "Mon Dec 21, 07:35", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Seoul Incheon","destination_code": "ICN", "flag": "🇰🇷", "country": "South Korea (hub)"},
        {"price": 3488, "airline": "Japan Airlines",   "duration": "22h 05m", "stops": 1, "departure": "Fri Dec 18, 16:40", "arrival": "Sun Dec 20, 15:45", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Tokyo Haneda", "destination_code": "HND", "flag": "🇯🇵", "country": "Japan"},
        {"price": 3640, "airline": "Cathay Pacific",   "duration": "19h 55m", "stops": 1, "departure": "Fri Dec 18, 13:20", "arrival": "Sun Dec 20, 10:15", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Hong Kong",    "destination_code": "HKG", "flag": "🇭🇰", "country": "Hub / Gateway"},
        {"price": 3850, "airline": "Asiana",           "duration": "20h 10m", "stops": 1, "departure": "Sat Dec 19, 08:30", "arrival": "Mon Dec 21, 05:40", "link": "#", "cabin": "Premium Economy", "infant_note": "Daughter needs own seat — booked as child fare", "destination": "Osaka",        "destination_code": "KIX", "flag": "🇯🇵", "country": "Japan"},
        {"price": 4980, "airline": "EVA Air",          "duration": "18h 30m", "stops": 1, "departure": "Fri Dec 18, 14:25", "arrival": "Sun Dec 20, 09:55", "link": "#", "cabin": "Business Class",  "infant_note": "Daughter as lap infant — typically 10% of adult fare", "destination": "Taipei",       "destination_code": "TPE", "flag": "🇹🇼", "country": "Taiwan"},
        {"price": 5200, "airline": "ANA",              "duration": "21h 15m", "stops": 1, "departure": "Fri Dec 18, 11:10", "arrival": "Sun Dec 20, 09:25", "link": "#", "cabin": "Business Class",  "infant_note": "Daughter as lap infant — typically 10% of adult fare", "destination": "Tokyo Narita", "destination_code": "NRT", "flag": "🇯🇵", "country": "Japan"},
        {"price": 5450, "airline": "United",           "duration": "20h 30m", "stops": 1, "departure": "Fri Dec 18, 09:00", "arrival": "Sun Dec 20, 06:30", "link": "#", "cabin": "Business Class",  "infant_note": "Daughter as lap infant — typically 10% of adult fare", "destination": "Tokyo Narita", "destination_code": "NRT", "flag": "🇯🇵", "country": "Japan"},
        {"price": 6100, "airline": "Japan Airlines",   "duration": "22h 05m", "stops": 1, "departure": "Sat Dec 19, 16:40", "arrival": "Mon Dec 21, 14:45", "link": "#", "cabin": "Business Class",  "infant_note": "Daughter as lap infant — typically 10% of adult fare", "destination": "Tokyo Haneda", "destination_code": "HND", "flag": "🇯🇵", "country": "Japan"},
        {"price": 6800, "airline": "Singapore Airlines","duration": "24h 10m", "stops": 1, "departure": "Fri Dec 18, 22:00", "arrival": "Sun Dec 20, 23:10", "link": "#", "cabin": "Business Class",  "infant_note": "Daughter as lap infant — typically 10% of adult fare", "destination": "Tokyo Narita", "destination_code": "NRT", "flag": "🇯🇵", "country": "Japan"},
    ]


# ─── POINTS MATH ─────────────────────────────────────────────────────────────

def points_for_price(price_usd, cpp):
    return int((price_usd * 100) / cpp)


# ─── HTML GENERATION ─────────────────────────────────────────────────────────

def flight_card(f, cheapest_price):
    is_cheapest = f["price"] == cheapest_price
    cabin_code  = "C" if "Business" in f["cabin"] else "W"

    cheapest_badge = '<span class="cheapest-badge">Cheapest</span>' if is_cheapest else ""
    cheapest_class = " cheapest" if is_cheapest else ""

    pts_rows = "\n".join(
        f'<div class="pts-item"><span>{name}</span><strong>{points_for_price(f["price"], d["cpp"]):,} pts</strong></div>'
        for name, d in POINTS_CURRENCIES.items()
    )

    stops_text = "Nonstop" if f["stops"] == 0 else f'{f["stops"]} stop{"s" if f["stops"] > 1 else ""}'
    link_attr  = f'href="{f["link"]}" target="_blank"' if f["link"] != "#" else 'href="#" onclick="return false"'
    link_text  = "Book on Kiwi →" if f["link"] != "#" else "Add API key to see real results"
    link_style = "" if f["link"] != "#" else "background:#a0aec0;cursor:default;"

    return f"""
    <div class="card{cheapest_class}">
      {cheapest_badge}
      <div class="card-top">
        <div>
          <span class="cabin-badge cabin-{cabin_code}">{f["cabin"]}</span>
          <div class="dest">{f["flag"]} {f["destination"]} <span class="dest-code">({f["destination_code"]})</span></div>
          <div class="country">{f["country"]}</div>
        </div>
        <div class="price-block">
          <div class="price">${f["price"]:,}</div>
          <div class="price-sub">2 adults (est.)</div>
        </div>
      </div>
      <div class="details-grid">
        <div><div class="lbl">Airline</div>{f["airline"]}</div>
        <div><div class="lbl">Duration</div>{f["duration"]}</div>
        <div><div class="lbl">Departs</div>{f["departure"]}</div>
        <div><div class="lbl">Arrives</div>{f["arrival"]}</div>
        <div><div class="lbl">Routing</div>{stops_text}</div>
        <div><div class="lbl">Infant</div><span style="font-size:0.78rem;color:#718096">{f["infant_note"]}</span></div>
      </div>
      <div class="pts-section">
        <div class="pts-title">Points equivalent (to cover cash price):</div>
        {pts_rows}
      </div>
      <a class="book-btn" {link_attr} style="{link_style}">{link_text}</a>
    </div>"""


def award_card(a):
    return f"""
    <div class="award-card">
      <div class="award-top">
        <div class="award-program">{a["program"]}</div>
        <span class="award-badge">{a["badge"]}</span>
      </div>
      <div class="award-miles">{a["miles_per_person"]:,} <span class="award-miles-sub">miles / person</span></div>
      <div class="award-meta">✈ {a["airline"]} · {a["cabin"]} · {a["route"]}</div>
      <div class="award-currency">Transfer from: <strong>{a["currency"]}</strong> (1:1)</div>
      <div class="award-note">{a["note"]}</div>
      <div class="award-avail {a["avail_class"]}">{a["avail_icon"]} Availability: {a["availability"]}</div>
    </div>"""


def points_summary_card(cabin_name, flights):
    cabin_flights = [f for f in flights if f["cabin"] == cabin_name]
    if not cabin_flights:
        return ""
    cheapest = min(cabin_flights, key=lambda x: x["price"])
    cabin_code = "C" if "Business" in cabin_name else "W"
    rows = "\n".join(
        f'<div class="pts-item"><span>{name} ({d["cpp"]}¢/pt)</span><strong>{points_for_price(cheapest["price"], d["cpp"]):,} pts</strong></div>'
        for name, d in POINTS_CURRENCIES.items()
    )
    return f"""
    <div class="card">
      <span class="cabin-badge cabin-{cabin_code}">{cabin_name}</span>
      <div style="margin:0.5rem 0 0.75rem;font-size:0.9rem;color:#4a5568">
        Cheapest found: <strong>${cheapest["price"]:,}</strong>
        ({cheapest["flag"]} {cheapest["destination"]})
      </div>
      {rows}
      <div style="font-size:0.75rem;color:#a0aec0;margin-top:0.75rem">
        Per-person infant miles: ~10% extra in Business (lap), or child rate in Premium Eco (own seat).
      </div>
    </div>"""


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f8; color: #1a202c; }

header { background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%); color: white; padding: 2.5rem 2rem; }
header h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.25rem; }
header .subtitle { opacity: 0.8; font-size: 1rem; margin-bottom: 1rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip { background: rgba(255,255,255,0.18); padding: 0.3rem 0.85rem; border-radius: 9999px; font-size: 0.82rem; }

.demo-banner { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 1rem 2rem; font-size: 0.88rem; line-height: 1.6; }
.demo-banner code { background: #fef3c7; padding: 0.15rem 0.4rem; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.85rem; }

main { max-width: 1200px; margin: 0 auto; padding: 2rem; }
section { margin-bottom: 2.5rem; }
h2 { font-size: 1.25rem; font-weight: 700; color: #2d3748; padding-bottom: 0.6rem; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.25rem; }
.section-note { color: #718096; font-size: 0.85rem; margin-bottom: 1rem; line-height: 1.5; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1rem; }
.award-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1rem; }

.card { background: white; border-radius: 12px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; position: relative; transition: box-shadow 0.2s; }
.card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
.card.cheapest { border: 2px solid #48bb78; }
.cheapest-badge { position: absolute; top: -11px; right: 14px; background: #48bb78; color: white; font-size: 0.68rem; font-weight: 800; padding: 0.2rem 0.65rem; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.06em; }

.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.85rem; }
.cabin-badge { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; margin-bottom: 0.35rem; }
.cabin-W { background: #ebf8ff; color: #2b6cb0; }
.cabin-C { background: #faf5ff; color: #6b46c1; }
.dest { font-size: 1.05rem; font-weight: 700; }
.dest-code { font-weight: 400; color: #718096; }
.country { font-size: 0.78rem; color: #a0aec0; margin-top: 0.1rem; }
.price-block { text-align: right; flex-shrink: 0; }
.price { font-size: 1.65rem; font-weight: 800; color: #2d3748; line-height: 1; }
.price-sub { font-size: 0.72rem; color: #a0aec0; margin-top: 0.15rem; }

.details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.45rem 1rem; font-size: 0.84rem; color: #4a5568; margin-bottom: 0.85rem; }
.lbl { font-size: 0.7rem; color: #a0aec0; margin-bottom: 0.1rem; text-transform: uppercase; letter-spacing: 0.04em; }

.pts-section { border-top: 1px solid #f0f4f8; padding-top: 0.75rem; margin-top: 0.75rem; }
.pts-title { font-size: 0.75rem; color: #a0aec0; margin-bottom: 0.4rem; }
.pts-item { display: flex; justify-content: space-between; font-size: 0.83rem; color: #4a5568; padding: 0.2rem 0; }
.pts-item strong { color: #2d3748; }

.book-btn { display: block; text-align: center; margin-top: 0.85rem; padding: 0.55rem; background: #3182ce; color: white; border-radius: 8px; text-decoration: none; font-size: 0.85rem; font-weight: 600; transition: background 0.2s; }
.book-btn:hover { background: #2c5282; }

.award-card { background: white; border-radius: 12px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
.award-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.5rem; }
.award-program { font-weight: 700; font-size: 1rem; }
.award-badge { flex-shrink: 0; font-size: 0.68rem; font-weight: 800; padding: 0.2rem 0.65rem; border-radius: 9999px; background: #fef3c7; color: #92400e; text-transform: uppercase; letter-spacing: 0.04em; }
.award-miles { font-size: 1.55rem; font-weight: 800; color: #2d3748; margin-bottom: 0.35rem; }
.award-miles-sub { font-size: 0.72rem; color: #a0aec0; font-weight: 400; }
.award-meta { font-size: 0.88rem; color: #4a5568; margin-bottom: 0.25rem; }
.award-currency { font-size: 0.8rem; color: #718096; margin-bottom: 0.5rem; }
.award-currency strong { color: #4a5568; }
.award-note { font-size: 0.82rem; color: #4a5568; line-height: 1.55; border-top: 1px solid #f0f4f8; padding-top: 0.5rem; margin-top: 0.5rem; }
.award-avail { font-size: 0.8rem; margin-top: 0.5rem; font-weight: 600; }
.avail-ok    { color: #38a169; }
.avail-warn  { color: #d69e2e; }
.avail-limit { color: #e53e3e; }

footer { text-align: center; padding: 2rem; color: #a0aec0; font-size: 0.78rem; line-height: 1.7; }
footer strong { color: #718096; }
"""


def build_html(flights, is_demo):
    flights_sorted   = sorted(flights, key=lambda x: x["price"])
    cheapest_price   = flights_sorted[0]["price"] if flights_sorted else 0

    flight_cards_html = "\n".join(flight_card(f, cheapest_price) for f in flights_sorted)
    award_cards_html  = "\n".join(award_card(a) for a in AWARD_OPTIONS)
    pts_pe  = points_summary_card("Premium Economy", flights)
    pts_biz = points_summary_card("Business Class", flights)

    demo_banner = ""
    if is_demo:
        demo_banner = """
<div class="demo-banner">
  <strong>⚠ Demo Mode — Sample Prices</strong> &nbsp;&middot;&nbsp;
  Real-time results require a free Kiwi API key.
  Sign up at <strong>tequila.kiwi.com</strong>, then run:
  <code>KIWI_API_KEY=your_key_here python flight_search.py</code>
</div>"""

    source = "Demo / sample data" if is_demo else "Kiwi/Tequila API (live)"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flight Report — IAH → Asia Dec 2026</title>
<style>{CSS}</style>
</head>
<body>

<header>
  <h1>✈ Flight Report — IAH → Asia</h1>
  <div class="subtitle">December 2026 · Family trip to Japan / Taiwan</div>
  <div class="chips">
    <span class="chip">📅 Dec 18–21 departure</span>
    <span class="chip">👨‍👩‍👧 2 adults + 1 infant/child</span>
    <span class="chip">💺 Premium Economy &amp; Business</span>
    <span class="chip">💰 Budget ~$3k–$6k</span>
    <span class="chip">🏠 Houston IAH</span>
  </div>
</header>

{demo_banner}

<main>

<section>
  <h2>💵 Cash Flights — Sorted by Price</h2>
  <p class="section-note">
    Prices shown are estimates for <strong>2 adults</strong>. Infant/child seat adds cost — see each card for details.
    December flights to Japan/Taiwan book out early; prices shown reflect current availability window.
  </p>
  <div class="grid">
{flight_cards_html}
  </div>
</section>

<section>
  <h2>🏆 Award Flight Sweet Spots</h2>
  <p class="section-note">
    Your Amex MR, Chase UR, and Capital One miles all transfer to premium Asia-routing programs.
    Miles shown are <strong>per person</strong> — multiply by 2 for both adults (infant in Business is typically 10% of adult miles or free; own-seat child is typically 75% of adult miles in Premium Economy).
    Check availability at each program's website — December holiday travel books fast.
  </p>
  <div class="award-grid">
{award_cards_html}
  </div>
</section>

<section>
  <h2>📊 Points Calculator</h2>
  <p class="section-note">
    How many points you'd need to cover the cheapest cash price found in each cabin, based on typical transfer valuations.
    Actual award redemptions may be better — especially if you find saver-level availability.
  </p>
  <div class="grid">
{pts_pe}
{pts_biz}
  </div>
</section>

</main>

<footer>
  <strong>Disclaimer:</strong> Prices are estimates and change frequently. Always verify on airline or OTA websites before booking.<br>
  Infant/child fees vary by airline and booking class. For lap infants on international routes, expect ~10% of adult fare.<br>
  Generated {datetime.now().strftime("%B %d, %Y at %H:%M")} · Source: {source}
</footer>

</body>
</html>"""


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    is_demo = not bool(KIWI_API_KEY)

    if is_demo:
        print("ℹ  No KIWI_API_KEY found — running in demo mode with sample data.")
        print("   Get a free key: https://tequila.kiwi.com/")
        print("   Then: KIWI_API_KEY=your_key python flight_search.py\n")
        flights = get_demo_flights()
    else:
        print(f"🔍 Searching {len(DESTINATIONS)} destinations × {len(CABINS)} cabins from {ORIGIN} (Dec 18–21, 2026)...")
        flights = []
        for dest in DESTINATIONS:
            for cabin in CABINS:
                print(f"   {dest['flag']} {dest['code']} / {cabin['name']}...", end=" ", flush=True)
                results = search_kiwi(dest, cabin)
                flights.extend(results)
                print(f"({len(results)} results)")
        print(f"\n✓  {len(flights)} total flight options collected.\n")

    html    = build_html(flights, is_demo)
    outfile = Path(__file__).parent / "flight_report.html"
    outfile.write_text(html, encoding="utf-8")

    print(f"📄 Report saved: {outfile}")
    webbrowser.open(f"file://{outfile.resolve()}")
    print("🌐 Opening in browser...")


if __name__ == "__main__":
    main()
