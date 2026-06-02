from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from deepdiff import DeepDiff


@dataclass
class DiffResult:
    field_changes: list[dict]
    text_unified: str


def compute_diff(old: dict, new: dict) -> DiffResult:
    dd = DeepDiff(old, new, ignore_order=True, verbose_level=2)
    changes = []

    for path, vals in dd.get("values_changed", {}).items():
        changes.append({
            "path": str(path),
            "change_type": "changed",
            "old_value": str(vals["old_value"])[:300],
            "new_value": str(vals["new_value"])[:300],
        })
    for path in dd.get("dictionary_item_added", set()):
        changes.append({"path": str(path), "change_type": "added", "old_value": None, "new_value": None})
    for path in dd.get("dictionary_item_removed", set()):
        changes.append({"path": str(path), "change_type": "removed", "old_value": None, "new_value": None})
    for path, vals in dd.get("iterable_item_added", {}).items():
        changes.append({"path": str(path), "change_type": "added", "old_value": None, "new_value": str(vals)[:300]})
    for path, vals in dd.get("iterable_item_removed", {}).items():
        changes.append({"path": str(path), "change_type": "removed", "old_value": str(vals)[:300], "new_value": None})

    old_text = json.dumps(old, indent=2).splitlines(keepends=True)
    new_text = json.dumps(new, indent=2).splitlines(keepends=True)
    unified = "".join(difflib.unified_diff(old_text, new_text, fromfile="version_a", tofile="version_b", n=3))

    return DiffResult(field_changes=changes, text_unified=unified)
