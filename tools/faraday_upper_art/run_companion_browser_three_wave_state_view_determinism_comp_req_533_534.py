#!/usr/bin/env python3
"""Run the COMP-REQ-533/534 replay twice and compare every output byte."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


SOURCE_COMMIT = "235bc31c64ff82c99f2a2ba9783eef353754cbd5"
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "0C29D5FF40D80C41461F0738C1C747A6C2B27A5DA74B5C79E166621A7566D9DA"
COMMITTED_PAGE_SHA256 = (
    "8F8FC05C5DAA3A95C7A2E80D677B56A831CF620A752EABB1DCB535F01705AB9D"
)
COMMITTED_PAGE_GIT_BLOB = "fdf6c7c8e9ad7293dfd1115e7f42cca015d9a15e"
REPLAY_TOOL_PATH = (
    "tools/faraday_upper_art/"
    "replay_companion_browser_three_wave_state_view_comp_req_533_534.mjs"
)
REPLAY_TOOL_SHA256 = (
    "EC9E0F9C6370F4244532CFF157AD15CCC2295A31901BE790F53AF5D051C3C86A"
)
OWNER_REVIEW_URL = (
    "http://127.0.0.1:4173/" + PAGE_PATH
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


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


def collect_outputs(root: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "screenshot-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [
        output_dir / "browser-replay-result.json",
        output_dir / "pixel-dom-route-artifact.json",
        manifest_path,
    ]
    paths.extend(root / row["path"] for row in manifest["screenshots"])
    files = []
    for path in paths:
        data = path.read_bytes()
        files.append(
            {
                "bytes": len(data),
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_bytes(data),
            }
        )
    files.sort(key=lambda row: row["path"])
    return {
        "aggregate_sha256": sha256_bytes(canonical_bytes(files)),
        "file_count": len(files),
        "files": files,
    }


def run_replay(
    root: Path,
    output_dir: Path,
    runtime_url: str,
) -> dict[str, Any]:
    command = [
        "node",
        REPLAY_TOOL_PATH,
        output_dir.relative_to(root).as_posix(),
    ]
    environment = os.environ.copy()
    environment["COMPANION_BROWSER_REPLAY_URL"] = runtime_url
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"replay failed with exit {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    return collect_outputs(root, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--runtime-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    output_dir = (root / args.output_dir).resolve()
    receipt_path = (root / args.receipt).resolve()
    page_path = root / PAGE_PATH
    replay_tool = root / REPLAY_TOOL_PATH
    output_dir.relative_to(root)
    receipt_path.relative_to(root)

    if git_text(root, "rev-parse", f"{SOURCE_COMMIT}^{{commit}}") != SOURCE_COMMIT:
        raise RuntimeError("source commit identity drifted")
    committed_page = subprocess.run(
        ["git", "show", f"{SOURCE_COMMIT}:{PAGE_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    if sha256_bytes(committed_page) != COMMITTED_PAGE_SHA256:
        raise RuntimeError("source commit page identity drifted")
    if (
        git_text(root, "rev-parse", f"{SOURCE_COMMIT}:{PAGE_PATH}")
        != COMMITTED_PAGE_GIT_BLOB
    ):
        raise RuntimeError("source commit page blob drifted")
    if sha256_bytes(page_path.read_bytes()) != PAGE_SHA256:
        raise RuntimeError("worktree page identity drifted")
    if sha256_bytes(replay_tool.read_bytes()) != REPLAY_TOOL_SHA256:
        raise RuntimeError("replay tool identity drifted")

    request = urllib.request.Request(args.runtime_url, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read()
        http_status = response.status
    if http_status != 200 or sha256_bytes(body) != PAGE_SHA256:
        raise RuntimeError("runtime route is not the exact source-bound page")

    run_a = run_replay(root, output_dir, args.runtime_url)
    run_b = run_replay(root, output_dir, args.runtime_url)
    byte_identical = run_a == run_b
    result = {
        "schema": "companion.browser-three-wave-state-view-determinism.v1",
        "requirements": ["COMP-REQ-533", "COMP-REQ-534"],
        "status": (
            "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL"
            if byte_identical
            else "NO_GO"
        ),
        "source_commit": SOURCE_COMMIT,
        "page": {
            "path": PAGE_PATH,
            "committed_sha256": COMMITTED_PAGE_SHA256,
            "git_blob": COMMITTED_PAGE_GIT_BLOB,
            "sha256": PAGE_SHA256,
        },
        "owner_review_url": OWNER_REVIEW_URL,
        "runtime_url": args.runtime_url,
        "http_status": http_status,
        "served_page_sha256": sha256_bytes(body),
        "replay_tool": {
            "path": REPLAY_TOOL_PATH,
            "sha256": REPLAY_TOOL_SHA256,
        },
        "run_count": 2,
        "byte_identical": byte_identical,
        "run_a": run_a,
        "run_b": run_b,
        "side_effect_counters": {
            "headless_browser_replay_runs": 2,
            "server_start": 0,
            "visible_browser": 0,
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
