import os, time, requests
from typing import List, Dict
from bs4 import BeautifulSoup

NEWSAPI = "https://newsapi.org/v2/top-headlines"
GDELT  = "https://api.gdeltproject.org/api/v2/doc/doc"
USER_AGENT = {"User-Agent": "NewsAggregator/0.1 (+noncommercial)"}

def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script","style","noscript"]): t.extract()
    return soup.get_text("\n")

def newsapi_fetch(country="us", page_size=50) -> List[Dict]:
    key = os.getenv("NEWSAPI_KEY")
    if not key: return []
    r = requests.get(NEWSAPI, params={"apiKey": key, "country": country, "pageSize": page_size}, timeout=20, headers=USER_AGENT)
    r.raise_for_status()
    data = r.json()
    out = []
    for a in data.get("articles", []):
        out.append({
            "url": a.get("url",""),
            "title": a.get("title",""),
            "source": (a.get("source") or {}).get("name",""),
            "author": a.get("author") or "",
            "published_at": a.get("publishedAt") or "",
            "description": a.get("description") or "",
            "content": a.get("content") or "",
        })
    return out

def gdelt_fetch(query="technology", maxrecords=50) -> List[Dict]:
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": maxrecords,
        "format": "JSON",
    }
    r = requests.get(GDELT, params=params, timeout=20, headers=USER_AGENT)
    r.raise_for_status()
    data = r.json()
    out = []
    for a in data.get("articles", []):
        out.append({
            "url": a.get("url",""),
            "title": a.get("title",""),
            "source": a.get("domain",""),
            "author": "",
            "published_at": a.get("seendate",""),
            "description": a.get("title",""),
            "content": a.get("snippet",""),
        })
    return out
