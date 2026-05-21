"""
Dorking Engine — executes dorks via SearXNG public instances.
Falls back to next instance if one fails.
Rate limited to avoid bans.
"""
from __future__ import annotations

import time
import requests
from app.logging_setup import logger
from app.dork_library import get_dorks

# Public SearXNG instances (fallback list)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _search_one(instance: str, query: str) -> list[dict]:
    """Execute one dork via DuckDuckGo HTML."""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._current = {}
                self._in_title = False
                self._in_snippet = False

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                cls = attrs.get("class", "")
                if tag == "a" and "result__a" in cls:
                    self._current = {"title": "", "url": attrs.get("href", ""), "snippet": ""}
                    self._in_title = True
                elif tag == "a" and "result__snippet" in cls:
                    self._in_snippet = True

            def handle_endtag(self, tag):
                if tag == "a":
                    if self._in_title and self._current.get("title"):
                        self.results.append(self._current)
                        self._current = {}
                    self._in_title = False
                    self._in_snippet = False

            def handle_data(self, data):
                if self._in_title:
                    self._current["title"] = self._current.get("title", "") + data
                elif self._in_snippet:
                    self._current["snippet"] = self._current.get("snippet", "") + data

        parser = DDGParser()
        parser.feed(resp.text)
        return parser.results[:5]

    except Exception as e:
        logger.debug("DDG search failed: %s", e)
        return []


def run_dorks(category: str, target: str) -> dict:
    """
    Run all dorks for a category against a target.
    Returns structured results per dork.
    """
    dorks = get_dorks(category, target)
    if not dorks:
        return {"ok": False, "error": "Unknown category"}

    all_results = []

    for dork in dorks:
        logger.info("Running dork: %s", dork)
        results = _search_one("", dork)

        all_results.append({
            "dork":    dork,
            "results": results,
            "count":   len(results),
        })
        time.sleep(2)  # rate limit

    total = sum(r["count"] for r in all_results)
    return {
        "ok":       True,
        "target":   target,
        "category": category,
        "total":    total,
        "dorks":    all_results,
    }
