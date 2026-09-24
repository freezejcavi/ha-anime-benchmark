from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def normalize_title(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.casefold()
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


@dataclass(slots=True)
class CatalogIndex:
    items: list[dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "CatalogIndex":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items") or []
        return cls(items=items)

    def match_titles(self, titles: list[str | None]) -> dict[str, Any]:
        probes = [normalize_title(title) for title in titles if title]
        probes = [value for value in probes if value]
        if not probes:
            return {"tracked": False, "match_type": "none"}

        exact: list[tuple[int, dict[str, Any], str]] = []
        prefix: list[tuple[int, dict[str, Any], str]] = []

        for item in self.items:
            known_titles = [item.get("canonical_title"), *(item.get("aliases") or [])]
            for known in known_titles:
                normalized = normalize_title(known or "")
                if not normalized:
                    continue
                for probe in probes:
                    if probe == normalized:
                        exact.append((len(normalized), item, known))
                        continue

                    # Conservative franchise-level fallback. Avoid very short/generic prefixes.
                    if len(normalized) >= 8 and len(normalized.split()) >= 2:
                        if probe.startswith(normalized + " ") or normalized.startswith(probe + " "):
                            prefix.append((len(normalized), item, known))

        matches = exact or prefix
        if not matches:
            return {"tracked": False, "match_type": "none"}

        _, item, matched_title = sorted(matches, key=lambda row: row[0], reverse=True)[0]
        return {
            "tracked": True,
            "match_type": "exact" if exact else "franchise_prefix",
            "franchise_id": item.get("franchise_id"),
            "canonical_title": item.get("canonical_title"),
            "matched_title": matched_title,
        }

    def match_media(self, media: dict[str, Any]) -> dict[str, Any]:
        title = media.get("title") or {}
        return self.match_titles([
            title.get("english"),
            title.get("romaji"),
            title.get("native"),
        ])
