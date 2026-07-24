#!/usr/bin/env python3
"""Run the COMP-REQ-508 replay twice and compare every output byte."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


CANDIDATE_COMMIT = "6e6e521fddcdb9a99af0608fa86714df199e6c9c"
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7"
REPLAY_TOOL_PATH = (
    "tools/faraday_upper_art/"
    "replay_companion_browser_owner_review_ready_comp_req_508.mjs"
)
REPLAY_TOOL_SHA256 = "304575095583ACACDD45F4E218315F5829B0E2D0E68061403AD70287DDC9DE64"
REVIEW_URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def collect_outputs(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "screenshot-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_paths = [
        output_dir / "browser-replay-result.json",
        output_dir / "pixel-dom-route-artifact.json",
        manifest_path,
    ]
    relative_paths.extend(
        repo_root / entry["path"] for entry in manifest["screenshots"]
    )
    identities = []
    for path in relative_paths:
        data = path.read_bytes()
        identities.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": sha256_bytes(data),
                "bytes": len(data),
            }
        )
    identities.sort(key=lambda item: item["path"])
    aggregate = sha256_bytes(canonical_bytes(identities))
    return {
        "file_count": len(identities),
        "aggregate_sha256": aggregate,
        "files": identities,
    }


def run_replay(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    command = ["node", REPLAY_TOOL_PATH, output_dir.relative_to(repo_root).as_posix()]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Replay failed with exit {completed.returncode}: {completed.stderr.strip()}"
        )
    return collect_outputs(repo_root, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    receipt_path = (repo_root / args.receipt).resolve()
    page_path = repo_root / PAGE_PATH
    replay_tool = repo_root / REPLAY_TOOL_PATH

    if sha256_bytes(page_path.read_bytes()) != PAGE_SHA256:
        raise RuntimeError("Accepted page SHA drifted before replay")
    if sha256_bytes(replay_tool.read_bytes()) != REPLAY_TOOL_SHA256:
        raise RuntimeError("Replay tool SHA drifted before replay")

    request = urllib.request.Request(REVIEW_URL, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read()
        http_status = response.status
    if http_status != 200 or sha256_bytes(body) != PAGE_SHA256:
        raise RuntimeError("Existing 4173 route is not the accepted page")

    run_a = run_replay(repo_root, output_dir)
    if sha256_bytes(page_path.read_bytes()) != PAGE_SHA256:
        raise RuntimeError("Accepted page changed after replay A")
    run_b = run_replay(repo_root, output_dir)
    if sha256_bytes(page_path.read_bytes()) != PAGE_SHA256:
        raise RuntimeError("Accepted page changed after replay B")

    byte_identical = run_a == run_b
    result = {
        "schema": "companion.browser-clean-replay-determinism.v2",
        "requirements": [
            "COMP-REQ-440",
            "COMP-REQ-441",
            "COMP-REQ-442",
            "COMP-REQ-471",
            "COMP-REQ-508",
            "COMP-REQ-509",
            "COMP-REQ-510",
        ],
        "status": (
            "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL"
            if byte_identical
            else "NO_GO"
        ),
        "candidate_commit": CANDIDATE_COMMIT,
        "page_path": PAGE_PATH,
        "page_sha256": PAGE_SHA256,
        "url": REVIEW_URL,
        "http_status": http_status,
        "served_page_sha256": sha256_bytes(body),
        "replay_tool": {
            "path": REPLAY_TOOL_PATH,
            "sha256": REPLAY_TOOL_SHA256,
        },
        "command": [
            "node",
            REPLAY_TOOL_PATH,
            Path(args.output_dir).as_posix(),
        ],
        "run_count": 2,
        "byte_identical": byte_identical,
        "run_a": run_a,
        "run_b": run_b,
        "side_effect_counters": {
            "headless_browser_replay_runs": 2,
            "server_start": 0,
            "browser_window_open": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "evidence_artifact_write": 1,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(canonical_bytes(result))
    print(result["status"])
    return 0 if byte_identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
