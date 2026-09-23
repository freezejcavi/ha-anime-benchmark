from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "custom_components" / "anime_benchmark" / "model_bundle.json"

data = json.loads(BUNDLE.read_text(encoding="utf-8"))
assert data["rules_complete"] is True
assert data["bundle_kind"] == "production-export"
assert data["model_version"] == "profile-affinity-v1.4"
assert len(data["rules"]) == data.get("rule_count")
assert len(data["rules"]) >= 180
assert abs(sum(float(v) for v in data["component_weights"].values()) - 1.0) < 1e-9
assert set(data["component_weights"]) == set(data["component_priors"])
assert all(rule.get("rule_id") for rule in data["rules"])
print(f"OK: {data['model_version']} / {len(data['rules'])} rules / {data['taxonomy_mapping_version']}")
