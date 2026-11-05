#!/usr/bin/env python3
"""Prepare the default-off COMP-REQ-508/518/520/521 owner-review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-natural-expression-successor-comp-req-518-520-521"
)
RUNNER = (
    "tools/faraday_upper_art/"
    "run_companion_browser_owner_review_comp_req_521.ps1"
)
CHECKONLY_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_521.ps1 -CheckOnly"
)
EXECUTE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_521.ps1 "
    "-Execute -OwnerStartAcknowledged"
)
BINDINGS = {
    "page": (
        "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
        "candidate/wb55-browser-parity-attempt-01/index.html",
        "24B5720F14B6793B201C4E74AD8BDB2219EE4F8CC941454983876979DA9ADAB1",
    ),
    "machine_ready": (
        f"{VALIDATION_DIR}/MACHINE_READY.json",
        "16973DD68F45E0897AA7C0F7D5003A51EE9C095C599C55820E82625445B1DCC4",
    ),
    "negative_matrix": (
        f"{VALIDATION_DIR}/source-bound-negatives.json",
        "1161156D89BEC5CB12B4AB4928E699214B0A80C915A41FD0AB13EB0CC543ECAF",
    ),
    "replay": (
        f"{VALIDATION_DIR}/determinism-run/browser-replay-result.json",
        "50027010EC4923ADD5B73B71F56DFBEA48DF0268427955F34D48C1B368913B37",
    ),
    "pixel_dom_route": (
        f"{VALIDATION_DIR}/determinism-run/pixel-dom-route-artifact.json",
        "1688A1FF837A9F771E6950967F5891F5922D432180392863CAA431EAC8116382",
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/determinism-run/screenshot-manifest.json",
        "4E577A7C4E65A5C349B88C887CC59BE7446B10B62EC06CE255D4F17BF5500651",
    ),
    "determinism": (
        f"{VALIDATION_DIR}/deterministic-replay-receipt.json",
        "FC290AAFB6CEB203F885B81992DE63895AD026A8F0B2BC6FCA6B6B41FF383330",
    ),
    "focused_recording": (
        f"{VALIDATION_DIR}/focused-recording-temporal.json",
        "60EF928EE104035F1DE7756A0600A499A6B9A84D28869BDB8AB9A1A1290C526E",
    ),
    "focused_natural": (
        f"{VALIDATION_DIR}/focused-natural-expression.json",
        "93A1D3BF6D701A74007CCE5E5F9C1556630D3AAA7BCD5DD16C63718593BD5A4A",
    ),
    "runner": (
        RUNNER,
        "91BCA9CE1B4391BAAFF41880531F4D4E3AC477618C9820D8C42C7EEB309A6E15",
    ),
    "source_bound_verifier": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_combined_source_bound_comp_req_521.py",
        "8A8216AC64D368AD2BFBC9FB3F2352DADE860B4E4CDB973E6540D173356DAEEC",
    ),
    "negative_verifier": (
        "tools/faraday_upper_art/"
        "test_companion_browser_combined_source_bound_negatives_comp_req_521.py",
        "679D513B28D6A7B9C73B40E9D88042501531BA5ACEE6F0C7A7C7B4929782CA99",
    ),
}
TOOL_BINDINGS = {"runner", "source_bound_verifier", "negative_verifier"}


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


def git_text(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def tool_provenance(root: Path, relative_path: str) -> dict[str, str]:
    commit = git_text(root, "log", "-1", "--format=%H", "--", relative_path)
    require(len(commit) == 40, f"tool has no committed provenance: {relative_path}")
    committed_blob = git_text(root, "rev-parse", f"{commit}:{relative_path}")
    worktree_blob = git_text(
        root, "hash-object", "--path", relative_path, relative_path
    )
    require(
        committed_blob == worktree_blob,
        f"tool differs from committed provenance: {relative_path}",
    )
    return {"commit": commit, "git_blob": committed_blob}


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
        row: dict[str, Any] = {
            "bytes": path.stat().st_size,
            "id": binding_id,
            "path": relative_path,
            "sha256": observed,
        }
        if binding_id in TOOL_BINDINGS:
            row["provenance"] = tool_provenance(root, relative_path)
        identities.append(row)

    machine = read_json(root / BINDINGS["machine_ready"][0])
    negative = read_json(root / BINDINGS["negative_matrix"][0])
    replay = read_json(root / BINDINGS["replay"][0])
    determinism = read_json(root / BINDINGS["determinism"][0])
    require(
        machine.get("status") == "MACHINE_READY"
        and machine.get("failed_checks") == [],
        "MACHINE_READY is not a clean source-bound PASS",
    )
    require(
        negative.get("status") == "PASS"
        and negative.get("negative_case_count") == 19
        and negative.get("rejected_negative_count") == 19,
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
        and replay.get("totals", {}).get("snapshot_count") == 258
        and replay.get("totals", {}).get("recording_negative_checks") == 54
        and replay.get("totals", {}).get("stale_pupil_pixel_count") == 0
        and replay.get("totals", {}).get("microphone_requests") == 0,
        "replay semantic totals drifted",
    )

    runner_source = (root / RUNNER).read_text(encoding="utf-8")
    require(
        runner_source.count(
            "& pwsh -NoProfile -File $aiwPath operator-prompt"
        )
        == 1,
        "runner does not contain exactly one canonical operator-prompt call",
    )
    for token in (
        'title = "Companion 浏览器总体体验验收"',
        'buttons = @("通过", "失败")',
        "PASS_CHECKONLY_NO_EXECUTE",
        "recording_negative_checks",
        "stale_pupil_pixel_count",
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
        "schema": "companion.browser-owner-review-checkonly.v3",
        "requirements": [
            "COMP-REQ-508",
            "COMP-REQ-518",
            "COMP-REQ-520",
            "COMP-REQ-521",
        ],
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
        "schema": "companion.browser-owner-review-packet.v3",
        "requirements": [
            "COMP-REQ-508",
            "COMP-REQ-518",
            "COMP-REQ-520",
            "COMP-REQ-521",
        ],
        "status": "READY_FOR_ONE_FUTURE_OWNER_REVIEW_NOT_OWNER_PASS",
        "default_off": True,
        "execute_performed": False,
        "owner_pass_claimed": False,
        "url": URL,
        "source_commit": "119c0b8c873d7817c64edec31391b393e00b09ac",
        "replay_tool_commit": "a9753faab76048f3a350292cb61cbbff762ae32c",
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
            "center, orientation and accepted single-face identity",
            "single release orient then one natural expression transition after the 650 ms discriminator",
            "continuous drag gaze replacement and center return without stale pupils",
            "strict double-tap recording entry and fresh double-tap exact restore",
            "one stable listening face, inward absorbed waves and one compact recording-status icon",
            "stationary hold progress, four menu roots, Device > UI assets and return",
            "one 200x200 screen, one face, one gaze/highlight, no debug, mic request or mic glyph",
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
