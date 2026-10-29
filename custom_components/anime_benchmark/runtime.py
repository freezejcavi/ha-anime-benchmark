from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable

from .anilist import AniListClient, AniListResult
from .catalog import CatalogIndex
from .github_writer import GitHubTransactionWriter
from .v2_model import AffinityV2Catalog
from .taxonomy import from_anilist


@dataclass(slots=True)
class BenchmarkRuntime:
    client: AniListClient
    v2: AffinityV2Catalog
    catalog: CatalogIndex
    writer: GitHubTransactionWriter
    live_score_getter: Callable[[str], float | None] | None = None
    query: str = ""
    result: dict | None = None
    candidates: list[dict] = field(default_factory=list)
    error: str | None = None
    busy: bool = False
    phase: str = "idle"
    status: str = "Připraveno"
    elapsed_ms: int | None = None
    activity_log: list[str] = field(default_factory=lambda: ["Připraveno"])
    listeners: list[Callable[[], None]] = field(default_factory=list)

    @property
    def queue_configured(self) -> bool:
        return self.writer.configured

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
        self._set_status("scoring", f"Vyhodnocuji Affinity V2: {found.title}")
        catalog = self.catalog.match_media(found.raw)
        exact_tracked = catalog.get("tracked") and catalog.get("match_type") == "exact"
        franchise_id = catalog.get("franchise_id") if exact_tracked else None

        if exact_tracked:
            live_score = self.live_score_getter(franchise_id) if self.live_score_getter else None
            snapshot_score = self.v2.score_for(franchise_id)
            value = live_score if live_score is not None else snapshot_score
            result_score = {
                "rating": value,
                "range_min": None,
                "range_max": None,
                "score_status": "tracked_v2" if value is not None else "tracked_unscored",
                "score_source": (
                    "live_ha_feed" if live_score is not None
                    else ("prod_snapshot" if snapshot_score is not None else "unavailable")
                ),
                "model_version": "affinity-v2",
                "rating_note": (
                    "Kanonické V2 skóre ze živého HA feedu." if live_score is not None
                    else (
                        f"V2 PROD snapshot z {self.v2.snapshot_date}; mezi releasy může zastarat."
                        if snapshot_score is not None else
                        "Pro tuto franšízu zatím nemáme kanonické V2 skóre."
                    )
                ),
            }
        elif catalog.get("tracked"):
            # Prefix matches intentionally do not inherit another franchise's score.
            result_score = {
                "rating": None,
                "range_min": None,
                "range_max": None,
                "score_status": "ambiguous_tracked",
                "score_source": "unavailable",
                "model_version": "affinity-v2",
                "rating_note": "Pouze přibližná shoda názvu s trackerem; skóre bez potvrzení identity neodhadujeme.",
            }
        else:
            result_score = self.v2.estimate_new(found.raw)

        self.result = {
            "title": found.title,
            **result_score,
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
            "catalog": catalog,
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
                self._set_status("anilist", "Načítám vybraný titul z AniList")
                found = await self.client.get_by_id(int(anilist_id))
                await self._score_result(found, started)
                return

            self.result = None
            self.candidates = []
            self._set_status("anilist", "Hledám na AniList…")
            found = await self.client.search_candidates(query)
            if not found:
                raise LookupError(f'AniList nic nenašel pro "{query}"')

            exact = [item for item in found if item.match_score(query)[0] == 1.0]
            if exact:
                self._set_status("matched", f"Přesná shoda: {exact[0].title}")
                await self._score_result(exact[0], started)
                return

            self.candidates = []
            for item in found:
                summary = item.summary(query)
                summary["catalog"] = self.catalog.match_titles(summary.get("titles") or [])
                self.candidates.append(summary)
            self._finish_timing(started)
            count = len(self.candidates)
            self._set_status(
                "awaiting_selection",
                f"Nalezeno {count} kandidátů za {self.elapsed_ms / 1000:.2f} s – vyber správný titul",
            )
        except Exception as exc:
            self.result = None
            self.candidates = []
            self.error = str(exc) or exc.__class__.__name__
            self._finish_timing(started)
            self._set_status("error", f"Chyba po {self.elapsed_ms / 1000:.2f} s: {self.error}")
        finally:
            self.busy = False
            self._notify()

    async def add_later(self, anilist_id: int) -> None:
        started = monotonic()
        self.error = None
        self.busy = True
        self._set_status("queueing", "Ověřuji titul před importem…")

        try:
            if not self.writer.configured:
                raise RuntimeError(
                    "Later importer není nakonfigurovaný. Otevři Configure u Anime Benchmark a vlož GitHub token."
                )

            found = await self.client.get_by_id(int(anilist_id))
            catalog_match = self.catalog.match_media(found.raw)
            if catalog_match.get("tracked"):
                raise RuntimeError(
                    f"Titul je už v trackeru jako {catalog_match.get('canonical_title') or found.title}."
                )

            self._set_status("queueing", "Připravuji bezpečný tracker transaction…")
            signals = from_anilist(found.raw)
            estimate = self.v2.estimate_new(found.raw)

            transaction = await self.writer.submit_later(
                media=found.raw,
                canonical_title=found.title,
                taxonomy=[
                    {
                        "namespace": signal.namespace,
                        "term": signal.term,
                        "weight": round(float(signal.source_strength), 4),
                    }
                    for signal in signals
                ],
                benchmark={
                    "rating": estimate["rating"],
                    "range_min": estimate["range_min"],
                    "range_max": estimate["range_max"],
                    "score_status": estimate["score_status"],
                    "model_version": "affinity-v2-prewatch-proxy",
                    "story_arc": None,
                    "taxonomy_mapping_version": "anilist-conservative-v2-20261029",
                },
            )

            if self.result is None or self.result.get("anilist_id") != int(anilist_id):
                self.result = {
                    "title": found.title,
                    "anilist_id": found.raw.get("id"),
                    "anilist_url": found.raw.get("siteUrl"),
                    "cover_url": (found.raw.get("coverImage") or {}).get("large"),
                    **estimate,
                    "catalog": catalog_match,
                }

            self.result["queue_status"] = "submitted"
            self.result["queue_transaction_id"] = transaction["transaction_id"]
            self.result["queue_commit_sha"] = transaction.get("commit_sha")
            self.result["queue_path"] = transaction["path"]
            self.result["queue_url"] = transaction.get("html_url")
            self._finish_timing(started)
            self._set_status(
                "queued",
                f"Odesláno importeru za {self.elapsed_ms / 1000:.2f} s",
            )
        except Exception as exc:
            self.error = str(exc) or exc.__class__.__name__
            if self.result is not None:
                self.result["queue_status"] = "error"
            self._finish_timing(started)
            self._set_status(
                "error",
                f"Import se nepodařil: {self.error}",
            )
        finally:
            self.busy = False
            self._notify()

    async def calculate(self) -> None:
        await self.search(self.query)
