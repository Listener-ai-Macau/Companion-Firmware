#!/usr/bin/env python3
"""Prepare deterministic CheckOnly evidence and a default-off owner packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-epaper-parity-successor-comp-req-536-538"
)
RUNNER = (
    "tools/faraday_upper_art/"
    "run_companion_browser_owner_review_comp_req_536_538.ps1"
)
PAGE = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
URL = f"http://127.0.0.1:4173/{PAGE}"
CHECKONLY_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_536_538.ps1 -CheckOnly"
)
EXECUTE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_536_538.ps1 "
    "-Execute -OwnerStartAcknowledged"
)
BINDINGS = {
    "page": (PAGE, "6176B9B3A7948291F430B5C47EBB5CDB2DA339BEEA86FBD1C72920D74438DD10"),
    "machine": (
        f"{VALIDATION_DIR}/MACHINE_READY.json",
        "988FBD722F28CFFCCCB425A5C4D0F63B5ABF34589C2F90327ED66BB986DB7676",
    ),
    "negatives": (
        f"{VALIDATION_DIR}/source-bound-negatives.json",
        "03594FBCFB115E4DC069EC87CF7B11C190A57D413F6902018CCEED6192A4BFA5",
    ),
    "focused": (
        f"{VALIDATION_DIR}/focused-oracle.json",
        "6F3E806C4703E677DE9E2D108F8D3241546D87D41D05D099731A89BCD1603271",
    ),
    "replay": (
        f"{VALIDATION_DIR}/replay-run/browser-replay-result.json",
        "4108424DA67141EA31F7755CF3974CA982093B1D7B1FEE8A8263B25B9CDD5B26",
    ),
    "pixel": (
        f"{VALIDATION_DIR}/replay-run/pixel-dom-route-artifact.json",
        "C44BB53F2D07BE61D5EE27521E9237412EC1CFADCFEE57D6C9ED3636BEBBBE2F",
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/replay-run/screenshot-manifest.json",
        "81C10D5E17A633AC8F2411C82658C3A05F60963BDDBB36D592DADE19C901512C",
    ),
    "parity": (
        f"{VALIDATION_DIR}/parity-verifier.json",
        "D8CDA1082AC334FB4CEABB097D52EF8D6EFB9374455A8369A6720A848DC2EACB",
    ),
    "manifest": (
        "docs/art/exports/companion-browser-epaper-parity-comp-req-536-538/"
        "visual-frame-manifest.json",
        "198ED5AFBA59F06BE507E0BC6C1778363DB1E401AF17A8859A2A3D0665DB36DB",
    ),
    "runner": (
        RUNNER,
        "85886DFB978F8235AC97C7F57BDCA6F713E0EA5AA95F2FFC65923E74CEF700D2",
    ),
    "source_gate": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_epaper_source_bound_comp_req_536_538.py",
        "76077D1153265CDCAABC2B857268D2A8B3B8AE2C2A0AD29379C24D1FB71E2B1A",
    ),
    "negative_gate": (
        "tools/faraday_upper_art/"
        "test_companion_browser_epaper_source_bound_negatives_comp_req_536_538.py",
        "C0656F1B797D870C6CBE3704D3D5D0F5FD877F717E6326A9D0E9C47531B33021",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_lf(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise RuntimeError("text identity contains a bare carriage return")
    return normalized


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validation_snapshot(root: Path, excluded: set[Path]) -> dict[str, str]:
    base = root / VALIDATION_DIR
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes())
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.resolve() not in excluded
    }


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
    excluded = {checkonly_path, packet_path}

    identities = []
    for binding_id, (relative, expected_sha) in sorted(BINDINGS.items()):
        path = root / relative
        require(path.is_file(), f"missing binding: {binding_id}")
        checkout = path.read_bytes()
        observed = sha256(canonical_lf(checkout))
        require(observed == expected_sha, f"binding drift: {binding_id}")
        index_blob = git_text(root, "rev-parse", f":{relative}")
        worktree_blob = git_text(root, "hash-object", "--path", relative, relative)
        require(index_blob == worktree_blob, f"uncommitted drift: {binding_id}")
        identities.append(
            {
                "canonical_lf_sha256": observed,
                "git_blob": index_blob,
                "id": binding_id,
                "path": relative,
            }
        )

    for name in (
        "owner-review.json",
        "owner-review.raw.json",
        "owner-review.note.txt",
        "owner-review-fault.json",
        ".owner-review.prompt-active.lock",
    ):
        require(not (validation / name).exists(), f"owner lifecycle exists: {name}")

    runner_source = (root / RUNNER).read_text(encoding="utf-8")
    require(
        runner_source.count("$promptOutput = & pwsh") == 1,
        "runner must contain one canonical prompt call",
    )
    for token in (
        'title = "Companion 浏览器总体体验验收"',
        'buttons = @("通过", "失败")',
        "PASS_CHECKONLY_NO_EXECUTE",
        "owner-review.json",
        ".owner-review.prompt-active.lock",
    ):
        require(token in runner_source, f"runner contract missing: {token}")

    before = validation_snapshot(root, excluded)
    check = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(root / RUNNER),
            "-CheckOnly",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    require(check.returncode == 0, f"CheckOnly failed: {check.stderr.strip()}")
    readiness = json.loads(check.stdout)
    after = validation_snapshot(root, excluded)
    require(before == after, "CheckOnly changed validation evidence")
    require(
        readiness.get("status") == "PASS_CHECKONLY_NO_EXECUTE",
        "CheckOnly did not pass",
    )
    require(
        all(value == 0 for value in readiness.get("counters", {}).values()),
        "CheckOnly side-effect counter is nonzero",
    )

    checkonly = {
        "schema": "companion.browser-owner-review-checkonly-artifact.v1",
        "requirements": ["COMP-REQ-521", "COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538"],
        "status": "PASS_CHECKONLY_NO_EXECUTE",
        "command": CHECKONLY_COMMAND,
        "readiness": readiness,
        "snapshot_before": before,
        "snapshot_after": after,
        "identities": identities,
        "counters": {
            "process": 0,
            "browser": 0,
            "popup": 0,
            "hardware": 0,
            "write": 0,
            "server": 0,
            "owner_prompt": 0,
        },
    }
    checkonly_path.write_bytes(canonical_json(checkonly))
    checkonly_sha = sha256(checkonly_path.read_bytes())

    packet = {
        "schema": "companion.browser-owner-review-packet.v1",
        "requirements": ["COMP-REQ-521", "COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538"],
        "status": "READY_FOR_OWNER_REVIEW_PENDING",
        "default_off": True,
        "owner_result_exists": False,
        "owner_pass_claimed": False,
        "url": URL,
        "source_commit": "985c91d12c0210952fd4ede5812a65328157048d",
        "implementation_commit": "41677c9f96b44c9d45a28f29ea576ff30aef1f88",
        "evidence_commit": "c919bfe5198067e60d0b6cbf5fd38d82853e23a1",
        "machine_ready_sha256": BINDINGS["machine"][1],
        "checkonly": {
            "command": CHECKONLY_COMMAND,
            "path": checkonly_path.relative_to(root).as_posix(),
            "sha256": checkonly_sha,
        },
        "future_execute_command": EXECUTE_COMMAND,
        "prompt_lifecycle": {
            "canonical_operator_prompt_calls": 1,
            "title": "Companion 浏览器总体体验验收",
            "buttons": ["通过", "失败"],
            "note_allowed": True,
            "result_path": f"{VALIDATION_DIR}/owner-review.json",
            "raw_path": f"{VALIDATION_DIR}/owner-review.raw.json",
            "note_path": f"{VALIDATION_DIR}/owner-review.note.txt",
        },
        "identities": identities,
        "remaining_gate": "one canonical Chinese owner prompt; not executed",
    }
    packet_path.write_bytes(canonical_json(packet))
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
