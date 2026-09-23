from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonomySignal:
    namespace: str
    term: str
    source_strength: float = 1.0


GENRE_MAP = {
    "Action": "Action", "Adventure": "Adventure", "Comedy": "Comedy", "Drama": "Drama",
    "Fantasy": "Fantasy", "Horror": "Horror", "Mystery": "Mystery", "Romance": "Romance",
    "Sci-Fi": "Sci-Fi", "Slice of Life": "Slice of life", "Supernatural": "Supernatural",
}

FORMAT_MAP = {
    "TV": "tv", "TV_SHORT": "tv_short", "MOVIE": "film", "ONA": "ona",
    "OVA": "ova", "SPECIAL": "special",
}

TAG_MAP = {
    "School": ("project.subgenre", "School", 1.0),
    "Magic": ("project.subgenre", "Magic", 1.0),
    "Super Power": ("project.subgenre", "Superpowers", 1.0),
    "Martial Arts": ("project.subgenre", "Martial arts", 1.0),
    "Reincarnation": ("project.subgenre", "Reincarnation", 1.0),
    "Isekai": ("project.subgenre", "Isekai", 1.0),
    "Survival": ("project.subgenre", "Survival", 1.0),
    "Vampire": ("project.subgenre", "Vampires", 1.0),
    "Dragons": ("project.subgenre", "Dragons", 1.0),
    "Ensemble Cast": ("project.subgenre", "Ensemble", 0.9),
    "Found Family": ("project.subgenre", "Found family", 0.9),
    "Coming of Age": ("project.subgenre", "Coming-of-age", 0.9),
    "Time Manipulation": ("project.subgenre", "Time travel", 0.8),
    "Alternate Universe": ("project.subgenre", "Multiverse", 0.7),
    "Demons": ("project.subgenre", "Demons/Angels", 0.8),
    "Robots": ("project.subgenre", "Robots", 1.0),
    "Space": ("project.subgenre", "Space", 1.0),
    "Kaiju": ("project.subgenre", "Kaiju", 1.0),
    "Full CGI": ("project.subgenre", "CGI animation", 0.8),
    "Military": ("project.subgenre", "War", 0.8),
    "War": ("project.subgenre", "War", 1.0),
    "Post-Apocalyptic": ("project.subgenre", "Post-apocalyptic", 0.9),
    "Urban Fantasy": ("project.subgenre", "Urban fantasy", 1.0),
    "Superhero": ("project.subgenre", "Superhero", 1.0),
    "Assassins": ("project.subgenre", "Assassin", 0.9),
    "Anti-Hero": ("project.subgenre", "Antihero", 0.9),
    "Space Opera": ("project.subgenre", "Space opera", 1.0),
    "Dungeon": ("project.subgenre", "Dungeon", 1.0),
    "Death Game": ("project.subgenre", "Death game", 1.0),
}


def _origin(media: dict) -> str:
    return "donghua" if media.get("countryOfOrigin") == "CN" else "anime"


def from_anilist(media: dict) -> list[TaxonomySignal]:
    signals: list[TaxonomySignal] = [
        TaxonomySignal("content.medium", "animation", 1.0),
        TaxonomySignal("content.animation_origin", _origin(media), 1.0),
    ]
    mapped_format = FORMAT_MAP.get(media.get("format"))
    if mapped_format:
        signals.append(TaxonomySignal("content.format", mapped_format, 1.0))

    for genre in media.get("genres") or []:
        mapped = GENRE_MAP.get(genre)
        if mapped:
            signals.append(TaxonomySignal("project.genre", mapped, 1.0))

    for tag in media.get("tags") or []:
        if tag.get("isAdult") or tag.get("isGeneralSpoiler") or tag.get("isMediaSpoiler"):
            continue
        rank = int(tag.get("rank") or 0)
        if rank < 60:
            continue
        rank_strength = min(1.0, max(0.6, rank / 100))
        name = (tag.get("name") or "").strip()
        if not name:
            continue
        mapped = TAG_MAP.get(name)
        if mapped:
            namespace, term, strength = mapped
            signals.append(TaxonomySignal(namespace, term, strength * rank_strength))
        else:
            signals.append(TaxonomySignal("project.subgenre", name, 0.75 * rank_strength))

    unique: dict[tuple[str, str], TaxonomySignal] = {}
    for signal in signals:
        key = (signal.namespace, signal.term.casefold())
        if key not in unique or signal.source_strength > unique[key].source_strength:
            unique[key] = signal
    return list(unique.values())
