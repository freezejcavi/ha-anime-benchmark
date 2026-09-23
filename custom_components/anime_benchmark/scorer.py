from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext

from .model import ModelBundle
from .taxonomy import TaxonomySignal


@dataclass(slots=True)
class ScoreResult:
    rating: float
    affinity_index: float
    base_affinity_index: float
    raw_fit: float
    evidence_coverage: float
    confidence: str
    component_scores: dict[str, float | None]


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _matches(rule: dict, signal: TaxonomySignal) -> bool:
    if rule["namespace"] != signal.namespace:
        return False
    if rule["match_mode"] == "exact":
        return signal.term.casefold() == rule["term_pattern"].casefold()
    return re.search(rule["term_pattern"], signal.term, flags=re.I) is not None


def _round(value: Decimal, digits: int) -> Decimal:
    quantum = Decimal(1).scaleb(-digits)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def score(signals: list[TaxonomySignal], bundle: ModelBundle) -> ScoreResult:
    """Reproduce tracker.refresh_profile_affinity_v14 for one hypothetical title."""
    data = bundle.data
    weights = data["component_weights"]
    priors = data["component_priors"]
    rules = data["rules"]
    by_component: dict[str, list[dict]] = {component: [] for component in weights}

    for signal in signals:
        matching = [r for r in rules if _matches(r, signal)]
        grouped: dict[str, list[dict]] = {}
        for rule in matching:
            grouped.setdefault(rule["component"], []).append(rule)
        for component, candidates in grouped.items():
            best = sorted(
                candidates,
                key=lambda r: (
                    -float(r.get("evidence_strength", 1.0)) * signal.source_strength,
                    -float(r["fit_score"]),
                    -float(r["rule_weight"]),
                    str(r.get("rule_id", "")),
                ),
            )[0]
            by_component[component].append(
                {
                    **best,
                    "term": signal.term,
                    "effective_evidence": float(best.get("evidence_strength", 1.0))
                    * signal.source_strength,
                }
            )

    component_scores: dict[str, Decimal | None] = {}
    component_evidence: dict[str, Decimal] = {}
    for component in weights:
        hits = sorted(
            by_component.get(component, []),
            key=lambda h: (
                -float(h["fit_score"]),
                -float(h["effective_evidence"]),
                -float(h["rule_weight"]),
                h["namespace"],
                h["term"],
            ),
        )[:3]
        if not hits:
            component_scores[component] = None
            component_evidence[component] = Decimal("0")
            continue

        numerator = sum(
            (_d(h["fit_score"]) * _d(h["rule_weight"]) * _d(h["effective_evidence"]) for h in hits),
            Decimal("0"),
        )
        denominator = sum(
            (_d(h["rule_weight"]) * _d(h["effective_evidence"]) for h in hits),
            Decimal("0"),
        )
        strongest = max(_d(h["fit_score"]) for h in hits)
        component_scores[component] = Decimal("0.75") * strongest + Decimal("0.25") * (
            numerator / denominator
        )
        component_evidence[component] = max(_d(h["effective_evidence"]) for h in hits)

    total_weight = sum((_d(v) for v in weights.values()), Decimal("0"))
    raw_fit = sum(
        (
            (component_scores[c] if component_scores[c] is not None else _d(priors[c]))
            * _d(weights[c])
            for c in weights
        ),
        Decimal("0"),
    ) / total_weight
    evidence = sum(
        (component_evidence[c] * _d(weights[c]) for c in weights), Decimal("0")
    ) / total_weight

    base_affinity = raw_fit / _d(data["baseline_median_raw_fit"])
    affinity = base_affinity / _d(data["franchise_pre_rating_median"])
    display = data["display"]
    with localcontext() as ctx:
        ctx.prec = 40
        exponent = _d(display["slope"]) * (affinity - _d(display["anchor"]))
        rating_raw = exponent.exp()
    rating = _round(max(_d(display["minimum"]), rating_raw), int(display.get("round_digits", 2)))

    confidence = "high" if evidence >= Decimal("0.70") else "medium" if evidence >= Decimal("0.45") else "low"
    return ScoreResult(
        rating=float(rating),
        affinity_index=float(_round(affinity, 6)),
        base_affinity_index=float(_round(base_affinity, 6)),
        raw_fit=float(_round(raw_fit, 8)),
        evidence_coverage=float(_round(evidence, 6)),
        confidence=confidence,
        component_scores={
            k: None if v is None else float(_round(v, 4)) for k, v in component_scores.items()
        },
    )
