from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "custom_components" / "anime_benchmark" / "runtime.py"

tree = ast.parse(PATH.read_text(encoding="utf-8"))

for node in tree.body:
    if not isinstance(node, ast.ClassDef) or node.name != "BenchmarkRuntime":
        continue

    declared = {
        stmt.target.id
        for stmt in node.body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }
    assigned = set()

    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name)
            and child.value.id == "self"
            and isinstance(child.ctx, ast.Store)
        ):
            assigned.add(child.attr)

    undeclared = sorted(assigned - declared)
    if undeclared:
        raise SystemExit(
            "BenchmarkRuntime uses undeclared slot attributes: " + ", ".join(undeclared)
        )

    print(f"OK: BenchmarkRuntime slot assignments are declared ({len(assigned)} attrs)")
    break
else:
    raise SystemExit("BenchmarkRuntime class not found")
