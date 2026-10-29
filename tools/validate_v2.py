from __future__ import annotations

"""Offline V2 acceptance tests. No HA or PROD credential required."""

import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = root / "custom_components" / "anime_benchmark"
spec = importlib.util.spec_from_file_location("standalone_affinity_v2", package / "v2_model.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

model = module.AffinityV2Catalog.load(package / "affinity_v2_snapshot.json")
assert len(model.scores) == 253
assert len([x for x in model.scores.values() if x["score"] is not None]) == 252
assert model.score_for("missing") is None
assert model.snapshot_date == "2026-10-29"
solo = next(x for x in model.scores.values() if x["title"] == "Solo Leveling")
assert abs(model.score_for(solo["id"]) - 103.1801) < .0001
unscored = next(x for x in model.scores.values() if x["title"] == "The Apothecary Diaries")
assert model.score_for(unscored["id"]) is None

new_media = {
    "genres": ["Action", "Fantasy"],
    "tags": [
        {"name": "Magic", "rank": 90},
        {"name": "Isekai", "rank": 88},
        {"name": "Reincarnation", "rank": 75},
        {"name": "School", "rank": 95},
        {"name": "Dungeon", "rank": 45},
    ],
}
estimate = model.estimate_new(new_media)
assert estimate["score_status"] == "provisional"
assert estimate["model_version"] == "affinity-v2-prewatch-proxy"
assert len(estimate["subgenre_terms"]) == 3  # School unmapped, Dungeon below 60
assert round(estimate["rating"] - estimate["range_min"], 2) == 20
assert round(estimate["range_max"] - estimate["rating"], 2) == 20
assert estimate["range_max"] > estimate["rating"] > estimate["range_min"]
assert not any("affinity_index" in k for k in estimate)

missing = model.estimate_new({"genres": ["Action"], "tags": []})
assert missing["rating"] is None and missing["score_status"] == "insufficient_taxonomy"
blocked = model.estimate_new({
    "genres": ["Adventure"],
    "tags": [{"name": "Magic", "rank": 100, "isMediaSpoiler": True}],
})
assert blocked["rating"] is None
print("PASS V2: 253 PROD snapshots / 252 scored / 1 deferred; proxy, missing, spoilers")
