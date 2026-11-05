#!/usr/bin/env python3
"""Prepare the default-off COMP-REQ-508/509/510 owner-review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
VALIDATION_DIR = (
    "docs/validation/companion-browser-owner-review-ready-comp-req-508"
)
RUNNER = (
    "tools/faraday_upper_art/"
    "run_companion_browser_owner_review_comp_req_510.ps1"
)
RUNNER_SHA256 = (
    "4E4588AB3402F2CF3F0F9EB5A9F0FC547EA55E4467C8C0A7278DB023C5F8C2FC"
)
CHECKONLY_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_510.ps1 -CheckOnly"
)
EXECUTE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_510.ps1 "
    "-Execute -OwnerStartAcknowledged"
)
BINDINGS = {
    "page": (
        "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
        "candidate/wb55-browser-parity-attempt-01/index.html",
        "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7",
    ),
    "machine_ready": (
        f"{VALIDATION_DIR}/MACHINE_READY.json",
        "94962CA64121D0BBE9BF69D45BAA6D20D4EEE4B54C8C7F6CB8868C69DB6BA911",
    ),
    "negative_matrix": (
        f"{VALIDATION_DIR}/source-bound-negative-result.json",
        "0656B0362536C1B029D1BB3154E0C5A567B08ABF8C61F3BBC1F5B3FD4680469F",
    ),
    "replay": (
        f"{VALIDATION_DIR}/browser-replay-result.json",
        "8FCAD0AC4C5370EFBBBC6C3785B6E115AA1E77C69EA81C0E137207AC1D33721C",
    ),
    "pixel_dom_route": (
        f"{VALIDATION_DIR}/pixel-dom-route-artifact.json",
        "91E6793F01B8368933E61115E93AD7280B435A9A1429D4B2DE743B61878BD1F3",
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/screenshot-manifest.json",
        "1886C6193AE846C11116462A20A1DCDC093DB4BD65BED36C9B19CB762965460A",
    ),
    "determinism": (
        f"{VALIDATION_DIR}/clean-replay-determinism.json",
        "EAE756749EDC2030D18CB349137598F2C33642BB381DD64F6CD12C4DE73A51DB",
    ),
    "runner": (RUNNER, RUNNER_SHA256),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--checkonly-output", required=True)
    parser.add_argument("--packet-output", required=True)
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    validation = (root / VALIDATION_DIR).resolve()
    checkonly_path = (root / args.checkonly_output).resolve()
    packet_path = (root / args.packet_output).resolve()
    checkonly_path.relative_to(validation)
    packet_path.relative_to(validation)

    identities = []
    for binding_id, (relative_path, expected) in sorted(BINDINGS.items()):
        path = root / relative_path
        require(path.is_file(), f"missing binding: {binding_id}")
        observed = sha256(path.read_bytes())
        require(observed == expected, f"binding drift: {binding_id}")
        identities.append(
            {
                "bytes": path.stat().st_size,
                "id": binding_id,
                "path": relative_path,
                "sha256": observed,
            }
        )

    machine = read_json(root / BINDINGS["machine_ready"][0])
    negative = read_json(root / BINDINGS["negative_matrix"][0])
    replay = read_json(root / BINDINGS["replay"][0])
    determinism = read_json(root / BINDINGS["determinism"][0])
    require(
        machine.get("status") == "BROWSER_OWNER_REVIEW_READY_SUCCESSOR"
        and machine.get("failed_checks") == [],
        "MACHINE_READY is not a clean successor PASS",
    )
    require(
        negative.get("status") == "PASS"
        and negative.get("negative_count") == 27
        and negative.get("rejected_count") == 27,
        "negative matrix is incomplete",
    )
    require(
        determinism.get("status")
        == "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL"
        and determinism.get("byte_identical") is True
        and determinism.get("run_a") == determinism.get("run_b"),
        "clean replay is not byte stable",
    )
    require(
        replay.get("totals", {}).get("scenario_count") == 42
        and replay.get("totals", {}).get("recording_negative_checks") == 54
        and replay.get("totals", {}).get("mic_glyph_pixel_count") == 0,
        "replay semantic totals drifted",
    )

    runner_source = (root / RUNNER).read_text(encoding="utf-8")
    require(
        runner_source.count(
            "& pwsh -NoProfile -File $aiwPath operator-prompt"
        ) == 1,
        "runner does not contain exactly one canonical operator-prompt call",
    )
    for token in (
        'title = "Companion 浏览器总体体验验收"',
        'buttons = @("通过", "失败")',
        "PASS_CHECKONLY_NO_EXECUTE",
        "route_recording_entries",
        "route_recording_exits",
        "owner-review.json",
        ".owner-review.prompt-active.lock",
    ):
        require(token in runner_source, f"runner contract token missing: {token}")

    lifecycle_paths = {
        "owner_result": f"{VALIDATION_DIR}/owner-review.json",
        "raw_result": f"{VALIDATION_DIR}/owner-review.raw.json",
        "optional_note": f"{VALIDATION_DIR}/owner-review.note.txt",
        "fault": f"{VALIDATION_DIR}/owner-review-fault.json",
        "prompt_lock": f"{VALIDATION_DIR}/.owner-review.prompt-active.lock",
    }
    for label in ("owner_result", "raw_result", "optional_note", "prompt_lock"):
        require(
            not (root / lifecycle_paths[label]).exists(),
            f"owner lifecycle file already exists: {label}",
        )

    checkonly = {
        "schema": "companion.browser-owner-review-checkonly.v2",
        "requirements": ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
        "status": "PASS_CHECKONLY_NO_EXECUTE",
        "default_off": True,
        "execute_performed": False,
        "command": CHECKONLY_COMMAND,
        "filesystem_diff_count": 0,
        "identities": identities,
        "owner_result_exists": False,
        "prompt_contract": {
            "instance_count": 1,
            "title": "Companion 浏览器总体体验验收",
            "buttons": ["通过", "失败"],
            "note_allowed": True,
        },
        "side_effect_counters": {
            "process": 0,
            "browser": 0,
            "popup": 0,
            "hardware": 0,
            "write": 0,
            "microphone_permission_request": 0,
            "server_start": 0,
            "owner_prompt": 0,
        },
    }
    checkonly_path.write_bytes(canonical_bytes(checkonly))
    checkonly_sha = sha256(checkonly_path.read_bytes())

    packet = {
        "schema": "companion.browser-owner-review-packet.v2",
        "requirements": ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
        "status": "READY_FOR_ONE_FUTURE_OWNER_REVIEW_NOT_OWNER_PASS",
        "default_off": True,
        "execute_performed": False,
        "owner_pass_claimed": False,
        "url": URL,
        "source_commit": "6e6e521fddcdb9a99af0608fa86714df199e6c9c",
        "evidence_commit": "1874859d769925696ca46aa158fa71fdb70b3500",
        "gate_commit": "258f6864c487fd07a1583e690a5e0e97aadf77be",
        "machine_artifact_bindings": identities,
        "checkonly": {
            "path": checkonly_path.relative_to(root).as_posix(),
            "sha256": checkonly_sha,
            "command": CHECKONLY_COMMAND,
            "status": checkonly["status"],
        },
        "future_execute": {
            "authorized_now": False,
            "command": EXECUTE_COMMAND,
            "operator_prompt_instance_count": 1,
            "canonical_aiw_subcommand": "operator-prompt",
            "title": "Companion 浏览器总体体验验收",
            "buttons": ["通过", "失败"],
            "note_allowed": True,
            "result_paths": lifecycle_paths,
        },
        "human_visible_checks": [
            "center orientation and accepted single-face identity",
            "tap response and continuous drag gaze replacement without stale pupils",
            "double-tap recording enter and fresh double-tap exact restore",
            "inward waves with listening then thoughtful-listening face",
            "stationary hold progress and menu entry",
            "four menu roots, Device > UI assets, Calm/Curious/Warm and return",
            "one 200x200 screen, one face, one gaze/highlight, no debug or mic glyph",
        ],
        "owner_boundary": {
            "owner_result_exists": False,
            "owner_prompt_invoked": False,
            "remaining_gate": (
                "Main agent must explicitly authorize the one future Execute."
            ),
        },
    }
    packet_path.write_bytes(canonical_bytes(packet))
    print(
        json.dumps(
            {
                "checkonly_sha256": checkonly_sha,
                "packet_sha256": sha256(packet_path.read_bytes()),
                "status": packet["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
