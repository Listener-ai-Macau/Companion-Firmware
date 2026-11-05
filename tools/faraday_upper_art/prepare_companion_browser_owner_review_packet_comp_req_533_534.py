#!/usr/bin/env python3
"""Prepare CheckOnly evidence and the default-off COMP-REQ-533/534 packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-three-wave-state-view-successor-comp-req-533-534"
)
RUNNER = (
    "tools/faraday_upper_art/"
    "run_companion_browser_owner_review_comp_req_533_534.ps1"
)
URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
CHECKONLY_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_533_534.ps1 -CheckOnly"
)
EXECUTE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "run_companion_browser_owner_review_comp_req_533_534.ps1 "
    "-Execute -OwnerStartAcknowledged"
)
BINDINGS = {
    "page": (
        "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
        "candidate/wb55-browser-parity-attempt-01/index.html",
        "8F8FC05C5DAA3A95C7A2E80D677B56A831CF620A752EABB1DCB535F01705AB9D",
    ),
    "machine_ready": (
        f"{VALIDATION_DIR}/MACHINE_READY.json",
        "F35D392C68AB660014E6DFAC861DE013090BBA02BAE8B2ADF2895478D68A9D6F",
    ),
    "negative_matrix": (
        f"{VALIDATION_DIR}/source-bound-negatives.json",
        "4FF9EAB610BFEB10757D30D6BAC2F8B9D51EE30A641686E3FDB992467E5E159B",
    ),
    "replay": (
        f"{VALIDATION_DIR}/determinism-run/browser-replay-result.json",
        "842073FF357B7ADF03775B432E87C67B45824F6EC271FE59D5B7CE46A05CF94C",
    ),
    "pixel": (
        f"{VALIDATION_DIR}/determinism-run/pixel-dom-route-artifact.json",
        "21CA3E864CE8523C497F38ABC758B1ADE34BB92EF755F63D9DFA2FC7A4F5B4F6",
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/determinism-run/screenshot-manifest.json",
        "4806A36D7E0BA0C456CA588888E237911D8D5B46B55F0B9E1B6DA238976A8BC5",
    ),
    "determinism": (
        f"{VALIDATION_DIR}/deterministic-replay-receipt.json",
        "7A65317B4FF4296543AF94D0D16662C6D4464726328BB9F172BE0ACFEA3674A7",
    ),
    "focused": (
        f"{VALIDATION_DIR}/after-fix/geometry-temporal-state-oracle.json",
        "9FC4A390A71A431029A3B50E6DC117D441D832694E7BDEA5E53A11A306DE7626",
    ),
    "runner": (
        RUNNER,
        "94FDD088BB8EFC18228EC2118D5CA65056C5954E6A69779073E3BD03628D5B9F",
    ),
    "source_gate": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_three_wave_state_view_source_bound_comp_req_533_534.py",
        "BC547A8C13B6BCF2AB411DB5D8847D36D9006E38F2A5928B0520810D65BC0D27",
    ),
    "negative_gate": (
        "tools/faraday_upper_art/"
        "test_companion_browser_three_wave_state_view_source_bound_negatives_comp_req_533_534.py",
        "71F7788E81865E292C023678793264DF371BB05DDC7FD59151581037469C92F4",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_lf_bytes(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise RuntimeError("text identity contains a bare carriage return")
    return normalized


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--checkonly-output", required=True)
    parser.add_argument("--packet-output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    validation = root / VALIDATION_DIR
    checkonly_path = (root / args.checkonly_output).resolve()
    packet_path = (root / args.packet_output).resolve()
    checkonly_path.relative_to(validation)
    packet_path.relative_to(validation)

    identities = []
    for binding_id, (relative, expected_sha) in sorted(BINDINGS.items()):
        path = root / relative
        require(path.is_file(), f"missing binding: {binding_id}")
        checkout_bytes = path.read_bytes()
        canonical = canonical_lf_bytes(checkout_bytes)
        observed = sha256(canonical)
        require(observed == expected_sha, f"binding drift: {binding_id}")
        row: dict[str, Any] = {
            "canonical_bytes": len(canonical),
            "checkout_bytes": len(checkout_bytes),
            "id": binding_id,
            "identity_basis": "git_blob_plus_canonical_lf_sha256",
            "path": relative,
            "canonical_sha256": observed,
        }
        index_blob = git_text(root, "rev-parse", f":{relative}")
        worktree_blob = git_text(
            root, "hash-object", "--path", relative, relative
        )
        require(index_blob == worktree_blob, f"uncommitted drift: {binding_id}")
        row["git_blob"] = index_blob
        identities.append(row)

    for name in (
        "owner-review.json",
        "owner-review.raw.json",
        "owner-review.note.txt",
        ".owner-review.prompt-active.lock",
    ):
        require(not (validation / name).exists(), f"owner lifecycle exists: {name}")

    runner_source = (root / RUNNER).read_text(encoding="utf-8")
    require(
        runner_source.count("$promptOutput = & pwsh") == 1,
        "runner must contain exactly one canonical prompt call",
    )
    for token in (
        'title = "Companion 浏览器总体体验验收"',
        'buttons = @("通过", "失败")',
        "PASS_CHECKONLY_NO_EXECUTE",
        "contractStepMs",
        "owner-review.json",
        ".owner-review.prompt-active.lock",
    ):
        require(token in runner_source, f"runner contract missing: {token}")

    files_before = sum(1 for path in validation.rglob("*") if path.is_file())
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
    files_after = sum(1 for path in validation.rglob("*") if path.is_file())
    require(files_before == files_after, "CheckOnly changed validation files")
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
        "requirements": ["COMP-REQ-521", "COMP-REQ-533", "COMP-REQ-534"],
        "status": "PASS_CHECKONLY_NO_EXECUTE",
        "command": CHECKONLY_COMMAND,
        "readiness": readiness,
        "file_count_before": files_before,
        "file_count_after": files_after,
        "identities": identities,
        "counters": readiness["counters"],
    }
    checkonly_path.write_bytes(canonical_bytes(checkonly))
    checkonly_sha = sha256(canonical_lf_bytes(checkonly_path.read_bytes()))

    packet = {
        "schema": "companion.browser-owner-review-packet.v4",
        "requirements": ["COMP-REQ-521", "COMP-REQ-533", "COMP-REQ-534"],
        "status": "READY_FOR_SINGLE_OWNER_PROMPT",
        "default_off": True,
        "execute_performed": False,
        "url": URL,
        "checkonly_command": CHECKONLY_COMMAND,
        "execute_command": EXECUTE_COMMAND,
        "checkonly_artifact": {
            "path": checkonly_path.relative_to(root).as_posix(),
            "canonical_sha256": checkonly_sha,
        },
        "identity_basis": "git_blob_plus_canonical_lf_sha256",
        "machine_ready_canonical_sha256": BINDINGS["machine_ready"][1],
        "page_canonical_sha256": BINDINGS["page"][1],
        "identities": identities,
        "prompt": readiness["prompt_contract"],
        "owner_result_path": f"{VALIDATION_DIR}/owner-review.json",
        "owner_raw_path": f"{VALIDATION_DIR}/owner-review.raw.json",
        "owner_note_path": f"{VALIDATION_DIR}/owner-review.note.txt",
        "owner_gate": {
            "status": "PENDING",
            "may_claim_owner_pass": False,
            "selection_required": ["通过", "失败"],
            "prompt_count": 1,
        },
        "counters": {
            "execute": 0,
            "process": 0,
            "browser": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "server_start": 0,
        },
    }
    packet_path.write_bytes(canonical_bytes(packet))
    print(json.dumps({
        "status": packet["status"],
        "checkonly_canonical_sha256": checkonly_sha,
        "packet_canonical_sha256": sha256(
            canonical_lf_bytes(packet_path.read_bytes())
        ),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
