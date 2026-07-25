#!/usr/bin/env python3
"""Source-bound MACHINE_READY verifier for COMP-REQ-546."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-browser-whole-frame-choreography-comp-req-546"
PAGE = Path("docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html")
REPLAY = Path("tools/faraday_upper_art/replay_companion_browser_whole_frame_comp_req_546.mjs")
BLINK = Path("tools/faraday_upper_art/verify_companion_whole_frame_blink_comp_req_546.mjs")
PROTECTED = {
    "driver_sha256": Path("app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"),
    "frame_header_sha256": Path("app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"),
    "owner_acceptance_sha256": Path("docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"),
}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256((ROOT / path).read_bytes())


def load(name: str) -> dict:
    return json.loads((VALIDATION / name).read_text(encoding="utf-8"))


def git_blob(commit: str, path: Path) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=ROOT,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    machine = load("MACHINE_READY.json")
    review = load("visual-self-review.json")
    packet = load("owner-review-packet.json")
    manifest = load("artifact-manifest.json")
    source_commit = machine["source_commit"]

    require(machine["status"] == "MACHINE_READY", "machine status")
    require(review["status"] == "PASS_OWNER_REVIEW_READY", "visual review status")
    require(packet["status"] == "OWNER_REVIEW_READY", "packet status")
    require(manifest["status"] == "PASS", "manifest status")
    require(source_commit == review["source"]["commit"] == packet["source_commit"], "source commit mismatch")

    page_sha = sha256(git_blob(source_commit, PAGE))
    require(page_sha == machine["page"]["sha256"] == review["source"]["page_sha256"], "page blob mismatch")
    require(sha256(git_blob(source_commit, REPLAY)) == "83AC5F0A3E0D8AE3937E773E19878C4FE57DD56CD17757859148BD48265E166C", "replay blob mismatch")
    require(sha256(git_blob(source_commit, BLINK)) == "A852E10F4262B1B438A36B32A5AAA739C81C3A38453CFD62A1E521A818253B80", "blink blob mismatch")

    page_text = git_blob(source_commit, PAGE).decode("utf-8")
    require("drawImage(images[index+1]" not in page_text, "eye rectangle transplant reachable")
    require("drawImage(temp,x+dx" not in page_text, "black raster shift reachable")
    require('"transplants"' not in page_text and '"shifts"' not in page_text, "forbidden manifest field")
    require('"whole_registered_frame_plus_gaze"' in page_text, "whole-frame contract absent")

    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        require(path.is_file(), f"missing artifact {entry['path']}")
        value = path.read_bytes()
        require(len(value) == entry["bytes"], f"artifact size {entry['path']}")
        require(sha256(value) == entry["sha256"], f"artifact hash {entry['path']}")

    evidence_names = {
        "focused_ten_family_sha256": "focused-ten-family-result.json",
        "full_clock_120_sha256": "full-clock-120-result.json",
        "interaction_42_sha256": "interaction-42-result.json",
        "stale_gaze_sha256": "stale-gaze-result.json",
        "parity_sha256": "parity-verifier-result.json",
        "blink_sha256": "blink-result.json",
    }
    for field, name in evidence_names.items():
        require(sha256((VALIDATION / name).read_bytes()) == machine["evidence"][field], f"evidence {name}")

    focused = load("focused-ten-family-result.json")
    clock = load("full-clock-120-result.json")
    interaction = load("interaction-42-result.json")
    stale = load("stale-gaze-result.json")
    parity = load("parity-verifier-result.json")
    blink = load("blink-result.json")
    require(focused["status"] == "PASS" and len(focused["selected_families"]) == 10, "focused result")
    require(clock["status"] == "PASS" and clock["real_clock_cadences"] == 120, "clock result")
    require(interaction["status"] == "PASS" and not interaction["failed"], "interaction result")
    require(stale["status"] == "PASS" and stale["measurement"]["pixel"]["stale_center_mask_total"] == 0, "stale gaze")
    require(parity["status"] == "PASS" and all(parity["checks"].values()), "parity result")
    require(blink["status"] == "PASS" and blink["checks"]["whole_registered_frames_only"], "blink result")
    require(all(value == "PASS" for value in review["visual_gates"].values()), "visual gate")
    require(all(machine["checks"].values()), "machine check")
    require(all(value == 0 for value in machine["side_effects"].values()), "side effect")

    for field, path in PROTECTED.items():
        require(file_sha(path) == machine["protected"][field], f"protected hash {field}")

    require(
        sha256((VALIDATION / "visual-self-review.json").read_bytes())
        == machine["evidence"]["visual_self_review_sha256"],
        "visual review hash",
    )
    require(
        sha256((VALIDATION / "artifact-manifest.json").read_bytes())
        == machine["evidence"]["artifact_manifest_sha256"],
        "artifact manifest hash",
    )
    require(
        sha256((VALIDATION / "MACHINE_READY.json").read_bytes())
        == packet["machine_ready"]["sha256"],
        "packet machine hash",
    )

    print(json.dumps({
        "status": "PASS",
        "requirement": "COMP-REQ-546",
        "source_commit": source_commit,
        "page_sha256": page_sha,
        "artifact_files": len(manifest["files"]),
        "interaction_scenarios": len(interaction["scenarios"]),
        "physical_side_effects": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
