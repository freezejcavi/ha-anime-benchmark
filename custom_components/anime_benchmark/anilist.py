from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from aiohttp import ClientSession

from .const import ANILIST_URL

QUERY = """
query ($search: String!) {
  Page(page: 1, perPage: 5) {
    media(search: $search, type: ANIME, isAdult: false) {
      id
      siteUrl
      title { romaji english native }
      format
      status
      episodes
      duration
      countryOfOrigin
      source(version: 3)
      genres
      description(asHtml: false)
      startDate { year }
      coverImage { large }
      tags { name rank isGeneralSpoiler isMediaSpoiler isAdult }
    }
  }
}
"""


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _candidate_score(query: str, media: dict) -> tuple[float, float]:
    q = _normalize(query)
    titles = media.get("title") or {}
    variants = [_normalize(v) for v in titles.values() if v]
    if not variants:
        return (0.0, 0.0)
    exact = 1.0 if q in variants else 0.0
    fuzzy = max(SequenceMatcher(None, q, value).ratio() for value in variants)
    return (exact, fuzzy)


@dataclass(slots=True)
class AniListResult:
    raw: dict[str, Any]

    @property
    def title(self) -> str:
        title = self.raw.get("title") or {}
        return title.get("english") or title.get("romaji") or title.get("native") or "Unknown"


class AniListClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def search(self, title: str) -> AniListResult:
        async with self._session.post(
            ANILIST_URL,
            json={"query": QUERY, "variables": {"search": title}},
            timeout=15,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        if payload.get("errors"):
            raise LookupError(payload["errors"][0].get("message", "AniList query failed"))
        media = (((payload.get("data") or {}).get("Page") or {}).get("media") or [])
        if not media:
            raise LookupError(f"AniList title not found: {title}")
        best = max(media, key=lambda item: _candidate_score(title, item))
        return AniListResult(best)
