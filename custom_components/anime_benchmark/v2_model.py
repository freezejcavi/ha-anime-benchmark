from __future__ import annotations

"""Affinity V2 benchmark read model.

TRACKED: exact PROD franchise score (live HA queue when available; otherwise dated
snapshot). NEW: an explicit *proxy interval*, never the canonical V2 score.
The V2 Story Arc component is not available from AniList.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Only conservatively mapped AniList tags; do not guess for unknown tags.
# Targets are validated against the PROD V2 subgenre rank registry on load.
TAG_TO_V2 = {
    "Magic": "Magic systems",
    "Reincarnation": "Rebirth and reincarnation",
    "Isekai": "Other-world transfer",
    "Martial Arts": "Combat disciplines",
    "Super Power": "Character abilities and roles",
    "Survival": "Survival and vulnerability",
    "Vampire": "Monsters and nonhuman peoples",
    "Dragons": "Monsters and nonhuman peoples",
    "Ensemble Cast": "Teamwork and ensemble",
    "Found Family": "Friendship and chosen bonds",
    "Coming of Age": "Character growth and maturation",
    "Time Manipulation": "Time and parallel realities",
    "Alternate Universe": "Time and parallel realities",
    "Demons": "Mythology and divinity",
    "Robots": "Mecha and artificial beings",
    "Space": "Space opera and interstellar",
    "Kaiju": "Monsters and nonhuman peoples",
    "Military": "War and military strategy",
    "War": "War and military strategy",
    "Post-Apocalyptic": "Apocalypse and dystopia",
    "Urban Fantasy": "Urban paranormal",
    "Superhero": "Superheroes and villains",
    "Anti-Hero": "Antihero and vigilante roles",
    "Space Opera": "Space opera and interstellar",
    "Dungeon": "Dungeons and structured challenges",
    "Death Game": "Competition and tournaments",
    "Virtual World": "Game worlds and virtual reality",
    "Video Games": "Game worlds and virtual reality",
    "RPG": "RPG mechanics and leveling",
    "Leveling": "Power progression and evolution",
    "Overpowered Main Character": "Overpowered protagonists",
    "Cooking": "Cooking and food activities",
    "Alchemy": "Crafting and professional skills",
    "Politics": "Politics and institutions",
    "Kingdom Building": "Kingdom and settlement building",
    "Travel": "Exploration and travel",
    "Mystery": "Mystery and investigation",
}


def _rounded(value: float) -> float:
    return round(value + 1e-10, 2)


@dataclass(slots=True)
class AffinityV2Catalog:
    snapshot_date: str
    scores: dict[str, dict[str, Any]]
    genre_ranks: dict[str, int]
    subgenre_ranks: dict[str, int]

    @classmethod
    def load(cls, path: Path) -> "AffinityV2Catalog":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or len(data.get("items", [])) < 200:
            raise ValueError("Invalid Affinity V2 catalog snapshot")
        genres = {
            row["term"]: int(row["rank"])
            for row in data["genre_ranks"]
            if row.get("direct_fit", True)
        }
        subgenres = {row["term"]: int(row["rank"]) for row in data["subgenre_ranks"]}
        unknown_targets = set(TAG_TO_V2.values()) - subgenres.keys()
        if unknown_targets:
            raise ValueError(f"Unknown V2 tag targets: {sorted(unknown_targets)}")
        if len(genres) < 15 or len(subgenres) != 56:
            raise ValueError("Incomplete V2 ranking registries")
        scores = {row["id"]: row for row in data["items"]}
        if len(scores) != len(data["items"]):
            raise ValueError("Duplicate V2 franchise IDs")
        return cls(data["snapshot_date"], scores, genres, subgenres)

    def score_for(self, franchise_id: str | None) -> float | None:
        row = self.scores.get(franchise_id or "")
        return None if not row or row.get("score") is None else float(row["score"])

    def estimate_new(self, media: dict[str, Any]) -> dict[str, Any]:
        """Pre-watch proxy; Story Arc 0..4 contributes 10..50 points.

        This is NOT the canonical V2 calculation: input taxonomy and Story Arc
        have not passed the tracker research/acceptance process.
        """
        genres = sorted({
            term for term in (media.get("genres") or [])
            if term in self.genre_ranks
        })
        subgenres = set()
        for tag in media.get("tags") or []:
            if tag.get("isAdult") or tag.get("isGeneralSpoiler") or tag.get("isMediaSpoiler"):
                continue
            if int(tag.get("rank") or 0) < 60:
                continue
            mapped = TAG_TO_V2.get((tag.get("name") or "").strip())
            if mapped:
                subgenres.add(mapped)
        subgenres = sorted(subgenres)

        base: dict[str, Any] = {
            "score_status": "provisional" if genres and subgenres else "insufficient_taxonomy",
            "score_source": "anilist_v2_proxy",
            "model_version": "affinity-v2-prewatch-proxy",
            "story_arc": None,
            "assumed_story_arc": 2,
            "genre_terms": genres,
            "subgenre_terms": subgenres,
            "rating": None,
            "range_min": None,
            "range_max": None,
            "rating_note": (
                "Jen orientační odhad. Story Arc (50 % V2) není na AniList ověřený; "
                "po zařazení do trackeru je nutný kanonický výpočet."
            ),
        }
        if not genres or not subgenres:
            missing = []
            if not genres:
                missing.append("žánry")
            if not subgenres:
                missing.append("spolehlivě mapované subžánry")
            base["rating_note"] = (
                "Nedostatek vstupů (" + ", ".join(missing) +
                "). Žádné skóre nedopočítáváme z V1.4 ani z vymyšleného Story Arc."
            )
            return base

        genre_raw = sum(self.genre_ranks[g] * 3 for g in genres) / len(genres)
        subgenre_raw = sum(self.subgenre_ranks[s] * 4 for s in subgenres) / len(subgenres)
        known_part = genre_raw * 10 / 69 + subgenre_raw * 40 / 224

        # canonical Story Arc uses (5 + 5 * strength_0_4) * 50 / 25
        base.update({
            "rating": _rounded(known_part + 30),  # explicit neutral assumption, Arc=2
            "range_min": _rounded(known_part + 10),  # Arc=0
            "range_max": _rounded(known_part + 50),  # Arc=4
            "genre_component": _rounded(genre_raw * 10 / 69),
            "subgenre_component": _rounded(subgenre_raw * 40 / 224),
        })
        return base
