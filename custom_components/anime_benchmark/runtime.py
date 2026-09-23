from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .anilist import AniListClient
from .model import ModelBundle
from .scorer import score
from .taxonomy import from_anilist


@dataclass(slots=True)
class BenchmarkRuntime:
    client: AniListClient
    bundle: ModelBundle
    query: str = ""
    result: dict | None = None
    error: str | None = None
    busy: bool = False
    listeners: list[Callable[[], None]] = field(default_factory=list)

    def set_query(self, value: str) -> None:
        self.query = value.strip()
        self._notify()

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(callback)
        return lambda: self.listeners.remove(callback) if callback in self.listeners else None

    def _notify(self) -> None:
        for callback in tuple(self.listeners):
            callback()

    async def calculate(self) -> None:
        if not self.query:
            self.error = "Enter an anime title"
            self._notify()
            return
        self.busy = True
        self.error = None
        self._notify()
        try:
            found = await self.client.search(self.query)
            signals = from_anilist(found.raw)
            scored = score(signals, self.bundle)
            self.result = {
                "title": found.title,
                "rating": scored.rating,
                "confidence": scored.confidence,
                "evidence_coverage": scored.evidence_coverage,
                "affinity_index": scored.affinity_index,
                "base_affinity_index": scored.base_affinity_index,
                "anilist_id": found.raw.get("id"),
                "anilist_url": found.raw.get("siteUrl"),
                "cover_url": (found.raw.get("coverImage") or {}).get("large"),
                "format": found.raw.get("format"),
                "year": (found.raw.get("startDate") or {}).get("year"),
                "status": found.raw.get("status"),
                "source": found.raw.get("source"),
                "country": found.raw.get("countryOfOrigin"),
                "episodes": found.raw.get("episodes"),
                "duration": found.raw.get("duration"),
                "genres": found.raw.get("genres") or [],
                "matched_taxonomy": [f"{s.namespace}:{s.term}" for s in signals],
                "component_scores": scored.component_scores,
                "model_version": self.bundle.data["model_version"],
                "taxonomy_mapping_version": self.bundle.data.get("taxonomy_mapping_version"),
            }
        except Exception as exc:
            self.result = None
            self.error = str(exc)
        finally:
            self.busy = False
            self._notify()
