#!/usr/bin/env python3
"""Verify the generated-art internal-clipping fix is a forward-only CEMP candidate."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import build_emote_asset_pack


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app" / "companion_pendant" / "epaper" / "assets" / "emote_matrix_white_200x200.json"
IMPORT_REPORT = ROOT / "docs" / "validation" / "companion-screen-generated-expression-sheet-import.json"
STYLE_SNAPSHOT = ROOT / "docs" / "validation" / "companion-screen-generated-art-style-contract.json"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-generated-art-clipping-fix-candidate.json"
SCHEMA_ID = "companion.screen.generated_art_clipping_fix_candidate.v1"
LAST_ACCEPTED_WB55_REVISION = 51
LAST_ACCEPTED_WB55_CRC32 = "0x56B56273"
EXPECTED_REVISION = 53
EXPECTED_CRC32 = "0x2332E300"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def manifest_expression_sources(manifest: dict[str, Any]) -> set[str]:
    return {
        pathlib.Path(str(frame.get("source", ""))).name
        for clip in manifest.get("clips", [])
        for frame in clip.get("frames", [])
        if pathlib.Path(str(frame.get("source", ""))).name.startswith("expression_")
    }


def imported_outputs(report: dict[str, Any]) -> set[str]:
    return {
        pathlib.Path(path).name
        for item in report.get("outputs", [])
        for path in item.get("files", [])
    }


def build_fixture() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    import_report = json.loads(IMPORT_REPORT.read_text(encoding="utf-8"))
    style = json.loads(STYLE_SNAPSHOT.read_text(encoding="utf-8"))
    _pack, metadata = build_emote_asset_pack.build_pack(MANIFEST)
    crc32 = f"0x{metadata['pack_crc32']:08X}"
    checks = {
        "forward_revision": metadata["revision"] > LAST_ACCEPTED_WB55_REVISION,
        "expected_revision": metadata["revision"] == EXPECTED_REVISION,
        "expected_crc32": crc32 == EXPECTED_CRC32,
        "preserves_last_accepted_record": LAST_ACCEPTED_WB55_CRC32 == "0x56B56273",
        "generated_import_machine_review": import_report.get("machine_review", {}).get("status") == "PASS",
        "internal_mask_stays_disabled": (
            import_report.get("machine_review_thresholds", {}).get("internal_shell_mask_disabled") is True
            and import_report.get("machine_review_thresholds", {}).get("fixed_art_margin_px") == 0
        ),
        "normal_expression_sources_come_from_generated_sheet": (
            manifest_expression_sources(manifest).issubset(imported_outputs(import_report))
        ),
        "accepted_art_baseline_is_protected": (
            style.get("acceptance", {}).get("human_accepted_generated_baseline_protected") is True
            and style.get("acceptance", {}).get("inner_face_clipping_prohibited") is True
            and style.get("acceptance", {}).get("profile_portability_workflow_recorded") is True
        ),
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": "READY_FOR_WB55_PROVISION_RUNTIME_RECHECK" if all(checks.values()) else "FAIL",
        "purpose": (
            "Forward-only external CEMP candidate for removing the old internal "
            "white shell-mask clipping while preserving the user-approved generated art."
        ),
        "candidate": {
            "manifest": rel(MANIFEST),
            "revision": metadata["revision"],
            "clips": metadata["clip_count"],
            "frames": metadata["frame_count"],
            "total_bytes": metadata["total_bytes"],
            "pack_crc32": crc32,
            "storage": "external ui_assets",
        },
        "last_accepted_wb55_runtime": {
            "revision": LAST_ACCEPTED_WB55_REVISION,
            "pack_crc32": LAST_ACCEPTED_WB55_CRC32,
        },
        "checks": checks,
        "hardware_state": "NOT_FLASHED_BY_THIS_CANDIDATE_CHECK",
        "next_machine_action": (
            "Build ScreenAssetProvision from this manifest, then provision rev53 and "
            "collect provision/normal serial evidence under the Companion-WB55 lock."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    output = args.json if args.json.is_absolute() else ROOT / args.json
    fixture = build_fixture()
    rendered = json.dumps(fixture, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    errors: list[str] = []
    if fixture["status"] != "READY_FOR_WB55_PROVISION_RUNTIME_RECHECK":
        errors.append("clipping-fix candidate checks did not pass")
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not output.exists() or output.read_text(encoding="utf-8") != rendered:
        errors.append(f"{rel(output)} is stale; rerun with --write")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: generated-art clipping-fix candidate verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
