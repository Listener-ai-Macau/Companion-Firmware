#!/usr/bin/env python3
"""Promote an owner-accepted touch/emotion browser preview into a regression baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
DEFAULT_CLOSURE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-closure-20260720.json"
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-preview-20260719.json"
DEFAULT_PARITY = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-parity-20260719.json"
DEFAULT_OWNER = ROOT / "docs/validation/companion-v9-rig-touch-emotion-browser-owner-review-20260720.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-browser-accepted-baseline-20260720.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/validation/artifacts/companion-v9-rig-touch-emotion-browser-accepted-baseline-20260720"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def copy_bound(source: pathlib.Path, destination: pathlib.Path) -> dict[str, str]:
    if not source.is_file():
        raise ValueError(f"missing accepted browser artifact: {rel(source)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = sha256(source)
    archived_hash = sha256(destination)
    if source_hash != archived_hash:
        raise ValueError(f"copied browser artifact hash mismatch: {rel(source)}")
    return {"source": rel(source), "archived": rel(destination), "sha256": source_hash}


def resolve_path(value: object, label: str) -> pathlib.Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is missing")
    path = pathlib.Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=pathlib.Path, default=DEFAULT_CLOSURE)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--parity", type=pathlib.Path, default=DEFAULT_PARITY)
    parser.add_argument("--owner-review", type=pathlib.Path, default=DEFAULT_OWNER)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    closure_path = args.closure if args.closure.is_absolute() else ROOT / args.closure
    preview_path = args.preview if args.preview.is_absolute() else ROOT / args.preview
    parity_path = args.parity if args.parity.is_absolute() else ROOT / args.parity
    owner_path = args.owner_review if args.owner_review.is_absolute() else ROOT / args.owner_review
    write_path = args.write if args.write.is_absolute() else ROOT / args.write
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    closure = load(closure_path)
    preview = load(preview_path)
    parity = load(parity_path)
    owner = load(owner_path)
    if closure.get("status") != "PASS_TOUCH_EMOTION_MACHINE_CLOSURE_RUNTIME_INACTIVE":
        raise ValueError("machine closure did not pass")
    if preview.get("status") != "PASS_BROWSER_COMPONENT_PREVIEW_FROM_TARGET_TRACE" or \
            parity.get("status") != "PASS_TOUCH_EMOTION_BROWSER_TARGET_PARITY_RUNTIME_INACTIVE":
        raise ValueError("browser preview or target parity did not pass")
    if owner.get("status") != "PASS_OWNER_TOUCH_EMOTION_BROWSER_PREVIEW_ACCEPTED_RUNTIME_INACTIVE" or \
            owner.get("selected") != "通过":
        raise ValueError("owner did not accept the browser preview")
    if preview.get("source_sha256") != LOCKED_SOURCE_SHA256 or \
            preview.get("runtime_resource_activated") is not False:
        raise ValueError("preview is not bound to the locked inactive V9 source")
    player = preview.get("browser_player")
    frames = preview.get("frames")
    component_dir = resolve_path(preview.get("component_layer_dir"), "component_layer_dir")
    if not isinstance(player, dict) or not isinstance(frames, list) or not component_dir.is_dir():
        raise ValueError("preview record is incomplete")
    player_copy = copy_bound(resolve_path(player.get("path"), "browser_player.path"),
                             artifact_dir / "touch-emotion-component-player.html")
    if player.get("sha256") != player_copy["sha256"]:
        raise ValueError("browser player report hash mismatch")
    frame_copies: list[dict[str, object]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("preview frame is malformed")
        source = resolve_path(frame.get("path"), "frame.path")
        archived = copy_bound(source, artifact_dir / "frames" / source.name)
        if frame.get("sha256") != archived["sha256"]:
            raise ValueError("preview frame report hash mismatch")
        frame_copies.append({"index": frame.get("index"), "kind": frame.get("kind"), **archived})
    component_copies = [
        copy_bound(component, artifact_dir / "components" / component.name)
        for component in sorted(component_dir.glob("*.png"))
    ]
    if len(component_copies) != preview.get("component_layer_count"):
        raise ValueError("component layer count does not match preview")
    baseline = {
        "schema": "companion.v9_rig_touch_emotion_browser_accepted_baseline.v1",
        "status": "PASS_ACCEPTED_TOUCH_EMOTION_BROWSER_PREVIEW_RUNTIME_INACTIVE",
        "source_sha256": LOCKED_SOURCE_SHA256,
        "runtime_resource_activated": False,
        "claim_scope": "accepted_browser_component_choreography_regression_baseline_not_panel_acceptance",
        "owner_review": {"path": rel(owner_path), "sha256": sha256(owner_path),
                         "selected": owner.get("selected"), "operator_note": owner.get("operator_note")},
        "machine_closure": {"path": rel(closure_path), "sha256": sha256(closure_path)},
        "browser_target_parity": {"path": rel(parity_path), "sha256": sha256(parity_path)},
        "browser_player": player_copy,
        "frames": frame_copies,
        "components": component_copies,
        "component_layer_count": len(component_copies),
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: promoted accepted touch/emotion browser preview -> {rel(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
