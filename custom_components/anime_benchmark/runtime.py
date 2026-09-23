from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable

from .anilist import AniListClient, AniListResult
from .model import ModelBundle
from .scorer import score
from .taxonomy import from_anilist


@dataclass(slots=True)
class BenchmarkRuntime:
    client: AniListClient
    bundle: ModelBundle
    query: str = ""
    result: dict | None = None
    candidates: list[dict] = field(default_factory=list)
    _candidate_raw: dict[int, AniListResult] = field(default_factory=dict)
    error: str | None = None
    busy: bool = False
    phase: str = "idle"
    status: str = "Připraveno"
    elapsed_ms: int | None = None
    activity_log: list[str] = field(default_factory=lambda: ["Připraveno"])
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

    def _set_status(self, phase: str, message: str, *, log: bool = True) -> None:
        self.phase = phase
        self.status = message
        if log and (not self.activity_log or self.activity_log[-1] != message):
            self.activity_log.append(message)
            self.activity_log = self.activity_log[-6:]
        self._notify()

    def _finish_timing(self, started: float) -> None:
        self.elapsed_ms = round((monotonic() - started) * 1000)

    async def _score_result(self, found: AniListResult, started: float) -> None:
        self.candidates = []
        self._candidate_raw = {}
        self._set_status("scoring", f"Počítám rating: {found.title}")
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
        self._finish_timing(started)
        self._set_status("done", f"Hotovo za {self.elapsed_ms / 1000:.2f} s")

    async def search(self, query: str, anilist_id: int | None = None) -> None:
        query = query.strip()
        if not query:
            self.error = "Zadej název anime"
            self._set_status("error", self.error)
            return

        started = monotonic()
        self.query = query
        self.error = None
        self.busy = True
        self.elapsed_ms = None
        self.activity_log = []
        self._set_status("starting", f'Odesílám: "{query}"')

        try:
            if anilist_id is not None:
                self._set_status("selected", f"Vybrán AniList #{anilist_id}")
                found = self._candidate_raw.get(int(anilist_id))
                if found is None:
                    self._set_status("anilist", "Načítám vybraný titul z AniList")
                    found = await self.client.get_by_id(int(anilist_id))
                await self._score_result(found, started)
                return

            self.result = None
            self.candidates = []
            self._candidate_raw = {}
            self._set_status("anilist", "Hledám na AniList…")
            found = await self.client.search_candidates(query)
            if not found:
                raise LookupError(f'AniList nic nenašel pro "{query}"')

            exact = [item for item in found if item.match_score(query)[0] == 1.0]
            if exact:
                self._set_status("matched", f"Přesná shoda: {exact[0].title}")
                await self._score_result(exact[0], started)
                return

            self._candidate_raw = {
                int(item.raw["id"]): item for item in found if item.raw.get("id") is not None
            }
            self.candidates = [item.summary(query) for item in found]
            self._finish_timing(started)
            count = len(self.candidates)
            self._set_status(
                "awaiting_selection",
                f"Nalezeno {count} kandidátů za {self.elapsed_ms / 1000:.2f} s – vyber správný titul",
            )
        except Exception as exc:
            self.result = None
            self.candidates = []
            self._candidate_raw = {}
            self.error = str(exc) or exc.__class__.__name__
            self._finish_timing(started)
            self._set_status("error", f"Chyba po {self.elapsed_ms / 1000:.2f} s: {self.error}")
        finally:
            self.busy = False
            self._notify()

    async def calculate(self) -> None:
        await self.search(self.query)
