from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ModelBundleError(RuntimeError):
    pass


@dataclass(slots=True)
class ModelBundle:
    data: dict

    @classmethod
    def load(cls, path: Path) -> "ModelBundle":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("rules_complete", False):
            raise ModelBundleError("Model bundle is not production-complete")
        required = (
            "model_version",
            "component_weights",
            "component_priors",
            "baseline_median_raw_fit",
            "franchise_pre_rating_median",
            "display",
            "rules",
        )
        missing = [key for key in required if key not in data]
        if missing:
            raise ModelBundleError(f"Missing model fields: {', '.join(missing)}")
        if not data["rules"]:
            raise ModelBundleError("Model bundle contains no affinity rules")
        weight_sum = sum(float(value) for value in data["component_weights"].values())
        if abs(weight_sum - 1.0) > 1e-9:
            raise ModelBundleError(f"Component weights must sum to 1.0, got {weight_sum}")
        missing_priors = set(data["component_weights"]) - set(data["component_priors"])
        if missing_priors:
            raise ModelBundleError(f"Missing component priors: {sorted(missing_priors)}")
        return cls(data)
