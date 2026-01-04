"""
Brave Search API client helpers.

This module provides thin wrappers around Brave's Web Search and News Search endpoints.
It returns normalized results for use by agents (deterministic sources, no LLM parsing).

Env:
- BRAVE_SEARCH_API_KEY: Brave subscription token
"""
from __future__ import annotations

from typing import Any, Dict, List
import os
import httpx


BRAVE_BASE_URL = "https://api.search.brave.com/res/v1"


class BraveSearchError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    token = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not token:
        raise BraveSearchError("BRAVE_SEARCH_API_KEY is not set")
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": token,
        "User-Agent": "Multi-Agent-Workflow-Automator/1.0",
    }


def _client(timeout_s: float = 15.0) -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(timeout_s, connect=10.0), headers=_headers())


def brave_web_search(
    query: str,
    count: int = 5,
    country: str = "us",
    search_lang: str = "en",
    *,
    timeout_s: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Brave Web Search.

    Returns list of dicts: {title, url, snippet, source}
    """
    with _client(timeout_s=timeout_s) as client:
        r = client.get(
            f"{BRAVE_BASE_URL}/web/search",
            params={"q": query, "count": count, "country": country, "search_lang": search_lang},
        )
        r.raise_for_status()
        data = r.json()

    results = (data.get("web") or {}).get("results") or []
    normalized: List[Dict[str, Any]] = []
    for x in results:
        url = (x.get("url") or "").strip()
        if not url:
            continue
        normalized.append(
            {
                "title": (x.get("title") or "").strip(),
                "url": url,
                "snippet": (x.get("description") or "").strip(),
                "source": ((x.get("profile") or {}).get("long_name") or "").strip(),
            }
        )
    return normalized


def brave_news_search(
    query: str,
    count: int = 5,
    country: str = "us",
    search_lang: str = "en",
    *,
    timeout_s: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Brave News Search.

    Returns list of dicts: {title, url, snippet, source, published}
    """
    with _client(timeout_s=timeout_s) as client:
        r = client.get(
            f"{BRAVE_BASE_URL}/news/search",
            params={"q": query, "count": count, "country": country, "search_lang": search_lang},
        )
        r.raise_for_status()
        data = r.json()

    results = (data.get("news") or {}).get("results") or []
    normalized: List[Dict[str, Any]] = []
    for x in results:
        url = (x.get("url") or "").strip()
        if not url:
            continue
        normalized.append(
            {
                "title": (x.get("title") or "").strip(),
                "url": url,
                "snippet": (x.get("description") or "").strip(),
                "source": ((x.get("publisher") or {}).get("name") or "").strip(),
                "published": (x.get("published_time") or None),
            }
        )
    return normalized
