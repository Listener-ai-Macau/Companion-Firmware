#!/usr/bin/env python3
"""Prove a WBA UI generation update changes only About-screen pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-profile", type=Path, required=True)
    parser.add_argument("--before-image", type=Path, required=True)
    parser.add_argument("--after-profile", type=Path, required=True)
    parser.add_argument("--after-image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    before = json.loads(args.before_profile.read_text(encoding="utf-8-sig"))
    after = json.loads(args.after_profile.read_text(encoding="utf-8-sig"))
    before_states = before.get("states", {})
    after_states = after.get("states", {})
    changed = sorted(
        name
        for name in before_states.keys() | after_states.keys()
        if before_states.get(name, {}).get("sha256")
        != after_states.get(name, {}).get("sha256")
    )
    unexpected = [name for name in changed if not name.startswith(("menu_ui_en_s7_", "menu_ui_zh_cn_s7_", "menu_ui_zh_tw_s7_"))]
    checks = {
        "generationAdvancedByOne": after.get("generation") == before.get("generation", -1) + 1,
        "profileRevisionAdvanced": after.get("profileRevision", 0) > before.get("profileRevision", 0),
        "stateNamesUnchanged": set(before_states) == set(after_states),
        "aboutPixelsChanged": bool(changed),
        "allPixelChangesRestrictedToAbout": not unexpected,
        "nonAboutPixelsPreserved": len(changed) < len(after_states) and not unexpected,
        "partitionChanged": sha256(args.before_image) != sha256(args.after_image),
    }
    result = {
        "schema": "companion.wba.ui-identity-delta.v1",
        "result": "PASS_UI_IDENTITY_ONLY" if all(checks.values()) else "FAIL_UI_IDENTITY_DELTA",
        "checks": checks,
        "before": {
            "generation": before.get("generation"),
            "profileRevision": before.get("profileRevision"),
            "uiPartitionSha256": sha256(args.before_image),
        },
        "after": {
            "generation": after.get("generation"),
            "profileRevision": after.get("profileRevision"),
            "uiPartitionSha256": sha256(args.after_image),
        },
        "stateCount": len(after_states),
        "changedStateCount": len(changed),
        "changedStates": changed,
        "unexpectedChangedStates": unexpected,
        "hardwareAcceptance": "NOT_RUN",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["result"])
    return 0 if result["result"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
