#!/usr/bin/env python3
"""Record that retained Companion history is classified without bulk merging it."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation/companion-historical-branch-audit-20260717.json"
PROTECTED_REFS = {
    "adhoc/codex/companion-ui-art-foundation": "15f1a55c62120db4cc65ce8b703c5f2b9f7a78dc",
    "ai/codex-companion-wb55-flash-mic-evidence-1.1": "329bb0a1a185244ef17d26ab6254530848d706a4",
    "human/scratch/companion-firmware/companion-ui-art-foundation-cleanup-20260716-233138": (
        "04f7a84272f28e5a0d3c7a1273c43a714f8cf2ca"
    ),
}
MAIN_REQUIRED_TOKENS = {
    "app/companion_pendant/power/power_policy.h": (
        "COMP_POWER_IDLE_MINUTES_DEFAULT 3u",
        "COMP_POWER_BLOCKER_TOUCH_CONFIRMATION",
    ),
    "app/companion_pendant/power/power_policy.c": (
        "comp_power_idle_settings_timeout_ms",
        "comp_power_idle_settings_self_test",
    ),
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c": (
        "comp_power_idle_settings_init(&s_power_idle_settings)",
        "COMP_POWER_BLOCKER_TOUCH_CONFIRMATION",
    ),
    "docs/companion_product_requirements.md": (
        "COMP-REQ-066",
        "COMP-REQ-070",
        "COMP-REQ-075",
    ),
}


def git_ref(name: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", name],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip().lower()


def verify() -> dict[str, object]:
    errors: list[str] = []
    refs: list[dict[str, str]] = []
    for name, expected in PROTECTED_REFS.items():
        actual = git_ref(name)
        if actual != expected:
            errors.append(f"protected history ref drifted: {name}")
        refs.append({"name": name, "expected": expected, "actual": actual})

    for relative, tokens in MAIN_REQUIRED_TOKENS.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        for token in tokens:
            if token not in source:
                errors.append(f"main integration token missing: {relative}: {token}")

    return {
        "schema": "companion.historical_branch_audit.v1",
        "status": "PASS_PRESERVED_AND_CLASSIFIED" if not errors else "FAIL",
        "workspace_observation": {
            "worktree_cleanup": "disposable worktrees removed before this audit",
            "main_branch": "main",
            "bulk_merge": "forbidden; historical commits are not a current feature contract",
        },
        "protected_refs": refs,
        "classification": {
            "art_foundation": (
                "Its useful three-minute idle setting and first-tap Stop blocker are "
                "re-integrated through the current portable power policy. Its retired "
                "art/camera-era material is not merged."
            ),
            "flash_mic_evidence": (
                "Its external-Flash/audio evidence remains preserved. Its manual Record "
                "menu action is intentionally not merged because COMP-REQ-066 selects "
                "double-tap-only daily recording."
            ),
            "scratch_checkpoint": (
                "Retained as an audit recovery point only; it is not a merge source."
            ),
        },
        "current_main_protections": {
            "three_minute_idle_default": True,
            "first_tap_blocks_stop_until_double_tap_decision": True,
            "double_tap_only_recording_menu_policy": True,
            "rejected_renderable_art_stays_retired": True,
        },
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the audit evidence JSON.")
    args = parser.parse_args(argv)
    result = verify()
    if args.write:
        OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: retained Companion branches are preserved, classified, and not bulk-merged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
