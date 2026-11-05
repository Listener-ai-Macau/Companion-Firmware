#!/usr/bin/env python3
"""Prepare the default-off COMP-REQ-540/541 owner review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = Path(
    "docs/validation/"
    "companion-browser-family-micro-choreography-comp-req-540"
)
PAGE = Path(
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
URL = (
    "http://127.0.0.1:4173/"
    + PAGE.as_posix()
)
TEXT_SUFFIXES = {".c", ".h", ".html", ".json", ".mjs", ".py", ".ps1"}
BINDINGS = {
    "machine": VALIDATION / "MACHINE_READY.json",
    "page": PAGE,
    "focused": VALIDATION / "focused-smoke-result.json",
    "static": VALIDATION / "ten-family-static-result.json",
    "clock": VALIDATION / "full-family-real-clock-result.json",
    "replay": VALIDATION / "replay-run/browser-replay-result.json",
    "pixel": VALIDATION / "replay-run/pixel-dom-route-artifact.json",
    "screenshots": VALIDATION / "replay-run/screenshot-manifest.json",
    "parity": VALIDATION / "parity-verifier-result.json",
    "manifest": VALIDATION / "device-pack/visual-frame-manifest.json",
    "source_negatives": VALIDATION / "source-bound-negatives.json",
    "source_gate": Path(
        "tools/faraday_upper_art/"
        "verify_companion_family_micro_source_bound_comp_req_540.py"
    ),
    "owner_runner": Path(
        "tools/faraday_upper_art/"
        "run_companion_family_micro_owner_review_comp_req_540.ps1"
    ),
}


def canonical(value: bytes, path: Path) -> bytes:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return value
    return value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=(VALIDATION / "owner-review-packet.json").as_posix(),
    )
    args = parser.parse_args()
    machine = json.loads(
        (ROOT / BINDINGS["machine"]).read_text(encoding="utf-8")
    )
    if (
        machine.get("status") != "MACHINE_READY"
        or machine.get("owner_gate") != "PENDING"
        or not all(machine.get("checks", {}).values())
    ):
        raise SystemExit("MACHINE_READY is not eligible for owner review")
    rows = []
    for identity, path in BINDINGS.items():
        data = canonical((ROOT / path).read_bytes(), path)
        rows.append(
            {
                "id": identity,
                "path": path.as_posix(),
                "sha256": sha256(data),
            }
        )
    packet = {
        "schema": "companion.comp-req-540-owner-review-packet.v1",
        "requirements": ["COMP-REQ-540", "COMP-REQ-541"],
        "status": "READY_DEFAULT_OFF",
        "url": URL,
        "bindings": rows,
        "visible_checks": [
            "十种表情的内部动作应各自有辨识度，动作细而不跳位",
            "每轮动作在三帧内回到该表情原始画面，脸始终居中且不裁切",
            "录音时左上黑点已消失，只有一组三列输入电平",
            "录音期间表情编舞、视线和手势继续工作，退出只移除电平",
            "单击、拖动、双击录音、三秒长按菜单及返回仍保持原行为",
        ],
        "prompt_contract": {
            "title": "Companion 表情精修浏览器验收",
            "buttons": ["通过", "失败"],
            "note_allowed": True,
            "progress_text": "请按正常速度体验十种表情、录音电平与既有手势。",
            "scope_text": "仅验收 200x200 浏览器表情、美术编舞与录音配件。",
            "message": (
                "请逐项观察十种表情的细微编舞，并实际操作单击、拖动、"
                "双击录音、三秒长按菜单及返回。录音态应仅有一组三列"
                "输入电平，不应出现左上黑点。"
            ),
            "expected_text": (
                "“通过”表示没有任何仍需修改的问题；仅看过候选不能选择"
                "“通过”。若备注中写有必须修改、移除、拒绝或质量缺陷，"
                "即使按钮选择“通过”，也按 NOT_ACCEPTED_OWNER_CHANGES_REQUIRED"
                " 归档。"
            ),
            "acceptance_rule": {
                "pass_means_no_remaining_required_changes": True,
                "viewed_only_is_not_pass": True,
                "blocking_note_overrides_pass_button": True,
            },
        },
        "lifecycle": {
            "default_off": True,
            "execute_performed": False,
            "single_prompt": True,
            "owner_result_exists": False,
            "browser_start": 0,
            "hardware": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
        },
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(packet)
    output.write_bytes(payload)
    print(
        json.dumps(
            {
                "bindings": len(rows),
                "output": output.relative_to(ROOT).as_posix(),
                "sha256": sha256(payload),
                "status": packet["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
