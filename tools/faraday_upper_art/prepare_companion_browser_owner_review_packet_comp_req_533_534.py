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
        "0C29D5FF40D80C41461F0738C1C747A6C2B27A5DA74B5C79E166621A7566D9DA",
    ),
    "machine_ready": (
        f"{VALIDATION_DIR}/MACHINE_READY.json",
        "97F757617A7828B61B11FEC3621861820C088C8047CD1836EC473680844BBB8A",
    ),
    "negative_matrix": (
        f"{VALIDATION_DIR}/source-bound-negatives.json",
        "49407A5D461375E1B467B787CAB6A79F760011FC6F79190D4645CD6EB8013AD6",
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
        "0CF0FA27F1227974E27451FAD634372154713DD4CDFCA00A61D673B39E84881F",
    ),
    "source_gate": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_three_wave_state_view_source_bound_comp_req_533_534.py",
        "7E3008EFADBC6FDD741FB42EAE19178B89CCAA7B9F8BE8BCEF82B1066A185B12",
    ),
    "negative_gate": (
        "tools/faraday_upper_art/"
        "test_companion_browser_three_wave_state_view_source_bound_negatives_comp_req_533_534.py",
        "176BEFAB647FB9D561C79E7B40F22D05FDD4FBCC7F82FA7A30C410842743E217",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


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
        observed = sha256(path.read_bytes())
        require(observed == expected_sha, f"binding drift: {binding_id}")
        row: dict[str, Any] = {
            "bytes": path.stat().st_size,
            "id": binding_id,
            "path": relative,
            "sha256": observed,
        }
        if relative.startswith("tools/"):
            commit = git_text(root, "log", "-1", "--format=%H", "--", relative)
            row["provenance"] = {
                "commit": commit,
                "git_blob": git_text(root, "rev-parse", f"{commit}:{relative}"),
            }
            require(
                row["provenance"]["git_blob"]
                == git_text(root, "hash-object", "--path", relative, relative),
                f"uncommitted tool drift: {binding_id}",
            )
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
    checkonly_sha = sha256(checkonly_path.read_bytes())

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
            "sha256": checkonly_sha,
        },
        "machine_ready_sha256": BINDINGS["machine_ready"][1],
        "page_sha256": BINDINGS["page"][1],
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
        "checkonly_sha256": checkonly_sha,
        "packet_sha256": sha256(packet_path.read_bytes()),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
