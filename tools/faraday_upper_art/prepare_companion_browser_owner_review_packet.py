#!/usr/bin/env python3
"""Prepare the default-off COMP-REQ-504 browser owner-review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CANDIDATE_COMMIT = "0f8fb928a726d99b4a6dacff2b59cc5f1c0caea9"
URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
SOURCE_GATE_PATH = (
    "docs/validation/companion-browser-owner-review-source-bound-comp-req-504/"
    "source-bound-tamper-gate.json"
)
SOURCE_GATE_SHA256 = "98F891667DE1223EE7E3BEBA9A448F3858B3B60BAB5A98331B3BD518EB84D2F6"
NEGATIVE_PATH = (
    "docs/validation/companion-browser-owner-review-source-bound-comp-req-504/"
    "source-bound-negative-result.json"
)
NEGATIVE_SHA256 = "79CD844B04C77E83F27428D33946A4C7851851C75192F376B4F3EDDEE7A7268B"
CLEAN_REPLAY_PATH = (
    "docs/validation/companion-browser-owner-review-source-bound-comp-req-504/"
    "clean-replay-determinism.json"
)
CLEAN_REPLAY_SHA256 = "AD6E1E39E31F68DED4FA00DFC074772994B5EED2C4E62BFC6CB80BF81FBB7A7E"
READY_DIR = "docs/validation/companion-browser-owner-review-ready-comp-req-471"
CORE_BINDINGS = {
    "replay_tool": (
        "tools/faraday_upper_art/replay_companion_browser_owner_review_ready.mjs",
        "259CB0D0D914A882634F2B37A05C6AAF5CD4413DAD766A98B997B7B7649C9E6D",
    ),
    "prior_checkonly_verifier": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_owner_review_ready_checkonly.py",
        "33581C21402DDD7591B364F8BEB32E710585CEA7C1DC8C27A615F440FF86D44D",
    ),
    "replay_result": (
        f"{READY_DIR}/browser-replay-result.json",
        "71C23ECF69CE759BAD8D328946385A82ABFA5F09D5AE14C109D3EBBB505F3B8D",
    ),
    "pixel_dom_route": (
        f"{READY_DIR}/pixel-dom-route-artifact.json",
        "670E41E6D928AD6FFAF50D580D87EC2FA19DD8507D0513375B7259BE9375C2FA",
    ),
    "screenshot_manifest": (
        f"{READY_DIR}/screenshot-manifest.json",
        "83B9EB8239D34CB772A1E85DC717DF2674C85960D63ACE81797D029CA697E823",
    ),
    "browser_owner_review_ready": (
        f"{READY_DIR}/BROWSER_OWNER_REVIEW_READY.json",
        "166FEC2E69BDF17D1EA9D398964AF146DE9EB9CC589797CE84DD03299876A7E8",
    ),
    "clean_replay_determinism": (CLEAN_REPLAY_PATH, CLEAN_REPLAY_SHA256),
    "source_bound_gate": (SOURCE_GATE_PATH, SOURCE_GATE_SHA256),
    "negative_matrix": (NEGATIVE_PATH, NEGATIVE_SHA256),
    "owner_review_scope": (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review-scope.json",
        "245B8BDB94A00A23224CF1E9A7F43CA65936CCC16518D3067D48BD98A5E61D80",
    ),
    "upper_machine_ready": (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "UPPER_MACHINE_READY.json",
        "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69",
    ),
    "protected_owner_acceptance": (
        "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json",
        "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    ),
    "canonical_runner": (
        "tools/faraday_upper_art/run_companion_browser_owner_review_comp_req_471.ps1",
        "6739E7BDF6CEB8118CC8ED9E660D5FB193F110D36E5D84F3C152753D9A424C81",
    ),
    "canonical_supervisor": (
        "tools/faraday_upper_art/"
        "supervise_companion_browser_owner_review_comp_req_471.ps1",
        "E7E599F906886030B95B47A17B0ADA88F8648A232F2A45D0C86C901AD9096F87",
    ),
}
FUTURE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "supervise_companion_browser_owner_review_comp_req_471.ps1 "
    "-Execute -OwnerStartAcknowledged"
)
MACHINE_DIR = "docs/validation/companion-browser-visual-contract-comp-req-471"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


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
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_path = (repo_root / args.output).resolve()
    require(sha256_bytes((repo_root / PAGE_PATH).read_bytes()) == PAGE_SHA256, "page drift")

    identities = []
    for binding_id, (relative_path, expected_hash) in CORE_BINDINGS.items():
        path = repo_root / relative_path
        require(path.is_file(), f"missing binding: {binding_id}")
        observed_hash = sha256_bytes(path.read_bytes())
        require(observed_hash == expected_hash, f"binding drift: {binding_id}")
        identities.append(
            {
                "id": binding_id,
                "path": relative_path,
                "sha256": observed_hash,
                "bytes": path.stat().st_size,
            }
        )

    source_gate = read_json(repo_root / SOURCE_GATE_PATH)
    require(source_gate.get("status") == "PASS_SOURCE_BOUND_TAMPER_GATE", "source gate not PASS")
    require(source_gate.get("candidate_commit", {}).get("expected") == CANDIDATE_COMMIT, "source gate candidate drift")
    require(not source_gate.get("failed_checks"), "source gate has failures")
    negative = read_json(repo_root / NEGATIVE_PATH)
    require(negative.get("status") == "PASS_ALL_TAMPERS_FAIL_CLOSED", "negative matrix not PASS")
    require(negative.get("fixture_count") == negative.get("passed_count"), "negative matrix incomplete")
    clean_replay = read_json(repo_root / CLEAN_REPLAY_PATH)
    require(
        clean_replay.get("status") == "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL",
        "clean replay is not deterministic",
    )
    require(clean_replay.get("run_a") == clean_replay.get("run_b"), "clean replay runs differ")

    ready = read_json(repo_root / CORE_BINDINGS["browser_owner_review_ready"][0])
    require(ready.get("status") == "BROWSER_OWNER_REVIEW_READY", "ready artifact not PASS")
    require(ready.get("owner_boundary", {}).get("owner_pass_claimed") is False, "ready claims owner PASS")
    require(ready.get("owner_boundary", {}).get("owner_prompt_invoked") is False, "ready claims prompt")

    screenshot_manifest = read_json(repo_root / CORE_BINDINGS["screenshot_manifest"][0])
    screenshot_identities = []
    for entry in screenshot_manifest.get("screenshots", []):
        path = repo_root / entry["path"]
        observed_hash = sha256_bytes(path.read_bytes())
        require(observed_hash == entry["sha256"], f"screenshot drift: {entry['id']}")
        screenshot_identities.append(
            {
                "id": entry["id"],
                "path": entry["path"],
                "sha256": observed_hash,
                "bytes": path.stat().st_size,
            }
        )
    require(len(screenshot_identities) == 50, "screenshot count is not 50")

    runner_path = repo_root / CORE_BINDINGS["canonical_runner"][0]
    runner_source = runner_path.read_text(encoding="utf-8")
    supervisor_source = (
        repo_root / CORE_BINDINGS["canonical_supervisor"][0]
    ).read_text(encoding="utf-8")
    require(
        runner_source.count("& pwsh -NoProfile -File $aiwPath operator-prompt") == 1,
        "canonical operator-prompt call count is not one",
    )
    for token in (
        'title = "Companion 浏览器总体体验验收"',
        'buttons = @("通过", "失败")',
        'note_allowed = $true',
        '".owner-review.prompt-active.lock"',
        '"owner-review.json"',
        '"owner-review.raw.json"',
        '"owner-review.note.txt"',
    ):
        require(token in runner_source, f"runner prompt contract token missing: {token}")
    require(
        '".owner-review.supervisor.lock"' in supervisor_source,
        "supervisor single-instance lock missing",
    )
    require(
        "-Execute -OwnerStartAcknowledged" in supervisor_source,
        "supervisor future command acknowledgement missing",
    )

    result_paths = {
        "machine_artifact": f"{MACHINE_DIR}/machine-result.json",
        "selection_result": f"{MACHINE_DIR}/owner-review.json",
        "raw_result": f"{MACHINE_DIR}/owner-review.raw.json",
        "optional_note": f"{MACHINE_DIR}/owner-review.note.txt",
        "prompt_lock": f"{MACHINE_DIR}/.owner-review.prompt-active.lock",
        "supervisor_lock": f"{MACHINE_DIR}/.owner-review.supervisor.lock",
    }
    for key in ("selection_result", "raw_result", "optional_note", "prompt_lock", "supervisor_lock"):
        require(not (repo_root / result_paths[key]).exists(), f"future lifecycle file already exists: {key}")

    packet = {
        "schema": "companion.browser-owner-review-packet.v1",
        "requirements": ["COMP-REQ-440", "COMP-REQ-441", "COMP-REQ-442", "COMP-REQ-471", "COMP-REQ-504"],
        "status": "READY_FOR_ONE_FUTURE_OWNER_REVIEW_NOT_OWNER_PASS",
        "default_off": True,
        "execute_performed": False,
        "candidate_evidence_commit": CANDIDATE_COMMIT,
        "url": URL,
        "page": {
            "path": PAGE_PATH,
            "sha256": PAGE_SHA256,
        },
        "machine_artifact_bindings": sorted(identities, key=lambda item: item["id"]),
        "screenshots": sorted(screenshot_identities, key=lambda item: item["id"]),
        "canonical_single_prompt_contract": {
            "aiw_subcommand": "operator-prompt",
            "instance_count": 1,
            "title": "Companion 浏览器总体体验验收",
            "buttons": ["通过", "失败"],
            "note_allowed": True,
            "message": (
                "请在同一总体页面实际检查：200x200 屏幕居中、方向与 V9 identity；"
                "单点响应一次；连续拖动替换 gaze 且回中无残留；双击恰好一次进入录音；"
                "原地长按饰品进度恰好一次进入菜单；四根菜单及 Device > UI assets 可用；"
                "菜单/录音返回互斥且恢复唯一 face/gaze/highlight；无 404、叠加、越界、"
                "调试参数或麦克风请求。"
            ),
            "future_execute_command": FUTURE_COMMAND,
        },
        "unique_prompt_lifecycle": {
            "supervised_only": True,
            "owner_start_acknowledgement_required": True,
            "duplicate_prompt_lock": result_paths["prompt_lock"],
            "supervisor_lock": result_paths["supervisor_lock"],
            "prompt_success_failure_timeout_cleanup_bounded_by_bound_runner": True,
            "existing_owner_result_must_not_be_overwritten": True,
            "result_paths": result_paths,
            "selection_and_note_are_adjacent_to_machine_artifact": True,
        },
        "owner_boundary": {
            "owner_prompt_invoked": False,
            "owner_result_exists": False,
            "owner_pass_claimed": False,
            "owner_pass_requires_future_existing_hash_bound_selection": "通过",
        },
        "checks": {
            "source_bound_gate_pass": True,
            "all_negative_tampers_rejected": True,
            "two_clean_replays_byte_identical": True,
            "page_and_all_artifact_hashes_recomputed": True,
            "fifty_screenshots_recomputed": True,
            "canonical_chinese_buttons_unique": True,
            "canonical_operator_prompt_call_count_one": True,
            "single_lifecycle_locks_present": True,
            "future_result_paths_absent": True,
            "owner_pass_not_claimed": True,
        },
        "side_effect_counters": {
            "server_probe": 0,
            "server_start": 0,
            "browser_start": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "owner_result_write": 0,
            "evidence_artifact_write": 1,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(packet))
    print(packet["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
