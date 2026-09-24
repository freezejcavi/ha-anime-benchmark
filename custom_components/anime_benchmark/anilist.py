from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from aiohttp import ClientSession

from .const import ANILIST_URL

MEDIA_FIELDS = """
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
"""

SEARCH_QUERY = f"""
query ($search: String!) {{
  Page(page: 1, perPage: 5) {{
    media(search: $search, type: ANIME, isAdult: false) {{
      {MEDIA_FIELDS}
    }}
  }}
}}
"""

ID_QUERY = f"""
query ($id: Int!) {{
  Media(id: $id, type: ANIME, isAdult: false) {{
    {MEDIA_FIELDS}
  }}
}}
"""


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def candidate_score(query: str, media: dict) -> tuple[float, float]:
    q = normalize_title(query)
    titles = media.get("title") or {}
    variants = [normalize_title(v) for v in titles.values() if v]
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

    def match_score(self, query: str) -> tuple[float, float]:
        return candidate_score(query, self.raw)

    def summary(self, query: str) -> dict[str, Any]:
        exact, fuzzy = self.match_score(query)
        titles = self.raw.get("title") or {}
        return {
            "id": self.raw.get("id"),
            "title": self.title,
            "titles": [value for value in (titles.get("english"), titles.get("romaji"), titles.get("native")) if value],
            "romaji": titles.get("romaji"),
            "english": titles.get("english"),
            "year": (self.raw.get("startDate") or {}).get("year"),
            "format": self.raw.get("format"),
            "cover_url": (self.raw.get("coverImage") or {}).get("large"),
            "anilist_url": self.raw.get("siteUrl"),
            "exact": bool(exact),
            "match": round(fuzzy, 3),
        }


class AniListClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def _post(self, query: str, variables: dict) -> dict:
        async with self._session.post(
            ANILIST_URL,
            json={"query": query, "variables": variables},
            timeout=15,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        if payload.get("errors"):
            raise LookupError(payload["errors"][0].get("message", "AniList query failed"))
        return payload.get("data") or {}

    async def search_candidates(self, title: str) -> list[AniListResult]:
        data = await self._post(SEARCH_QUERY, {"search": title})
        media = ((data.get("Page") or {}).get("media") or [])
        results = [AniListResult(item) for item in media]
        results.sort(key=lambda item: item.match_score(title), reverse=True)
        return results

    async def get_by_id(self, anilist_id: int) -> AniListResult:
        data = await self._post(ID_QUERY, {"id": int(anilist_id)})
        media = data.get("Media")
        if not media:
            raise LookupError(f"AniList title not found: {anilist_id}")
        return AniListResult(media)
