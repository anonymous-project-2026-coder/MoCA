from __future__ import annotations

import json
import os
from urllib import request
from urllib.error import HTTPError, URLError

from .schemas import SearchSnippet


def search_social_context(query: str, max_results: int = 3) -> list[SearchSnippet]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max(1, int(max_results)),
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return []

    snippets: list[SearchSnippet] = []
    for item in data.get("results", []):
        if not isinstance(item, dict):
            continue
        snippets.append(
            SearchSnippet(
                query=query,
                title=item.get("title") if isinstance(item.get("title"), str) else "",
                url=item.get("url") if isinstance(item.get("url"), str) else "",
                snippet=item.get("content") if isinstance(item.get("content"), str) else "",
            )
        )
    return snippets


def get_runtime_constraints() -> str:
    enabled = bool(os.getenv("TAVILY_API_KEY"))
    return f"external_web_search_enabled={str(enabled).lower()}"
