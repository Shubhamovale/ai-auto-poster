import json
import os
import random
import re
from html import unescape
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests


NEWS_QUERIES = [
    ("AI", "latest AI tools OR ChatGPT OR OpenAI OR Google AI when:1d"),
    ("Tech", "technology trend OR viral app OR startup when:1d"),
    ("Entertainment", "movie trailer OR netflix OR marvel OR gaming OR playstation OR xbox when:1d"),
    ("Business", "stock market OR business trend OR company launch when:1d"),
]

WEAK_PATTERNS = [
    r"^\d+\s",
    r"\blive updates?\b",
    r"\blive score\b",
    r"\bopinion\b",
    r"\breview\b",
    r"\bhow to\b",
    r"\bexplained\b",
    r"\brecap\b",
    r"\bresults\b",
    r"\bobituary\b",
    r"\bweather\b",
    r"\bhoroscope\b",
]


def clean_headline(text):
    headline = unescape(text or "").strip()
    headline = re.sub(r"\s*-\s*[^-]+$", "", headline)
    headline = re.sub(r"\s+", " ", headline)
    return headline.strip()


def is_strong_headline(headline):
    if not headline:
        return False
    if len(headline) < 18:
        return False
    normalized = headline.lower()
    for pattern in WEAK_PATTERNS:
        if re.search(pattern, normalized):
            return False
    # Prefer entertainment-style trigger words for the default poster format.
    strong_terms = [
        "trailer",
        "marvel",
        "netflix",
        "movie",
        "game",
        "gaming",
        "playstation",
        "xbox",
        "studio",
        "streaming",
        "season",
        "box office",
    ]
    return any(term in normalized for term in strong_terms)


def parse_rss_items(xml_text):
    root = ElementTree.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        title = clean_headline(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published_at": pub_date,
                }
            )
    return items


def fetch_news_items(query, hl="en-US", gl="US", ceid="US:en"):
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"
    )
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return parse_rss_items(response.text)


def load_fallback_topics():
    with open("topics.json", encoding="utf-8") as f:
        return json.load(f)["topics"]


def select_query():
    requested = os.environ.get("TREND_CATEGORY", "").strip().lower()
    if requested:
        for query_name, query in NEWS_QUERIES:
            if query_name.lower() == requested:
                return query_name, query
    for query_name, query in NEWS_QUERIES:
        if query_name == "Entertainment":
            return query_name, query
    return random.choice(NEWS_QUERIES)


def get_random_topic():
    query_name, query = select_query()
    try:
        items = fetch_news_items(query)
        strong_items = [item for item in items if is_strong_headline(item["title"])]
        candidates = strong_items or items
        if candidates:
            picked = random.choice(candidates[:15])
            return {
                "topic": picked["title"],
                "source_name": "Google News",
                "source_link": picked["link"],
                "source_query": query_name,
                "published_at": picked["published_at"],
                "is_live_trend": True,
            }
    except Exception as e:
        print(f"Trending topic fetch failed: {e}")

    fallback_topic = random.choice(load_fallback_topics())
    return {
        "topic": fallback_topic,
        "source_name": "Static topics fallback",
        "source_link": "",
        "source_query": "Fallback",
        "published_at": "",
        "is_live_trend": False,
    }
