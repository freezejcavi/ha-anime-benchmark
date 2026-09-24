from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "custom_components" / "anime_benchmark" / "catalog_index.json"

data = json.loads(PATH.read_text(encoding="utf-8"))
assert data["schema_version"] == 1
items = data.get("items") or []
assert len(items) >= 50

ids = [item.get("franchise_id") for item in items]
assert all(ids)
assert len(ids) == len(set(ids))
assert all(item.get("canonical_title") for item in items)
assert all(isinstance(item.get("aliases", []), list) for item in items)

print(f"OK: tracker catalog / {len(items)} franchises")
