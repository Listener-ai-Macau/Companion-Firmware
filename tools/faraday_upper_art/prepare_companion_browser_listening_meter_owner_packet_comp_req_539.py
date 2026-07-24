#!/usr/bin/env python3
"""Prepare the default-off COMP-REQ-539 owner review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = Path(
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
VALIDATION = Path(
    "docs/validation/"
    "companion-browser-listening-meter-successor-comp-req-539"
)
EXPORT = Path(
    "docs/art/exports/companion-browser-listening-meter-comp-req-539"
)
URL = (
    "http://127.0.0.1:4173/"
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
TEXT_SUFFIXES = {".c", ".h", ".html", ".json", ".mjs", ".py", ".ps1"}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_text(value: bytes) -> bytes:
    return value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def identity(source_commit: str, name: str, path: Path) -> dict:
    raw = (ROOT / path).read_bytes()
    value = canonical_text(raw) if path.suffix.lower() in TEXT_SUFFIXES else raw
    blob = git("rev-parse", f"{source_commit}:{path.as_posix()}").strip().decode()
    committed = git("cat-file", "blob", blob)
    committed_value = (
        canonical_text(committed)
        if path.suffix.lower() in TEXT_SUFFIXES
        else committed
    )
    if committed_value != value:
        raise ValueError(f"source drift: {path.as_posix()}")
    return {
        "git_blob": blob,
        "id": name,
        "path": path.as_posix(),
        "sha256": sha256(value),
    }


def artifact(name: str, path: Path) -> dict:
    value = (ROOT / path).read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        value = canonical_text(value)
    return {
        "id": name,
        "path": path.as_posix(),
        "sha256": sha256(value),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.relative_to(ROOT)
    machine_path = VALIDATION / "MACHINE_READY.json"
    negative_path = VALIDATION / "source-bound-negatives.json"
    machine = json.loads((ROOT / machine_path).read_text(encoding="utf-8"))
    negatives = json.loads((ROOT / negative_path).read_text(encoding="utf-8"))
    if (
        machine.get("status") != "MACHINE_READY"
        or machine.get("owner_gate") != "PENDING"
        or machine.get("source_commit") != args.source_commit
        or negatives.get("status") != "PASS"
    ):
        raise ValueError("machine or negative gate is not review-ready")
    owner_files = [
        VALIDATION / "owner-review.json",
        VALIDATION / "owner-review.raw.json",
        VALIDATION / "owner-review.note.txt",
    ]
    if any((ROOT / path).exists() for path in owner_files):
        raise ValueError("owner review lifecycle already exists")

    source_paths = {
        "page": PAGE,
        "runner": Path(
            "tools/faraday_upper_art/"
            "run_companion_browser_listening_meter_owner_review_comp_req_539.ps1"
        ),
        "source_gate": Path(
            "tools/faraday_upper_art/"
            "verify_companion_browser_listening_meter_source_bound_comp_req_539.py"
        ),
        "negative_gate": Path(
            "tools/faraday_upper_art/"
            "test_companion_browser_listening_meter_source_bound_negatives_comp_req_539.py"
        ),
        "packet_tool": Path(
            "tools/faraday_upper_art/"
            "prepare_companion_browser_listening_meter_owner_packet_comp_req_539.py"
        ),
    }
    artifacts = {
        "machine": machine_path,
        "negatives": negative_path,
        "focused": VALIDATION / "focused-oracle.json",
        "replay": VALIDATION / "replay-run/browser-replay-result.json",
        "pixel": VALIDATION / "replay-run/pixel-dom-route-artifact.json",
        "screenshots": VALIDATION / "replay-run/screenshot-manifest.json",
        "parity": VALIDATION / "parity-verifier.json",
        "manifest": EXPORT / "visual-frame-manifest.json",
        "frames": EXPORT / "frames.bin",
        "c_pack": EXPORT / "companion_browser_listening_meter_pack.c",
        "h_pack": EXPORT / "companion_browser_listening_meter_pack.h",
    }
    packet = {
        "schema": "companion.comp-req-539-owner-review-packet.v1",
        "status": "READY_DEFAULT_OFF",
        "requirements": ["COMP-REQ-539"],
        "source_commit": args.source_commit,
        "url": URL,
        "prompt_contract": {
            "title": "Companion 浏览器总体体验验收",
            "buttons": ["通过", "失败"],
            "progress_text": "1/1 浏览器总体体验",
            "scope_text": (
                "仅验收同一 4173 总体页面中的表情、菜单、"
                "录音附件与 200x200 墨水屏预览；browser-only。"
            ),
            "message": (
                "请在总体页面按正常速度实际操作：\n"
                "1. 无操作时观察确定性高光小动作：进入 eligible 后 "
                "960 ms 内出现，约每 480 ms 离散一步并精确回到基线；"
                "没有平滑插值或随机闪烁。\n"
                "2. 按住表情主屏 3000 ms 应直接进入菜单；按下、短按、"
                "提前松开、拖动和取消都不应出现进度条、进度饰品或残留像素。\n"
                "3. 严格双击开启录音附件：只增加一个小录音点和三根"
                "等宽离散竖列；每步外列写入新量化能量，旧样本逐列向脸旁"
                "听觉点移动。不得出现弧线、括号、重复图标或平滑中间帧。\n"
                "4. 录音开启时继续单点和拖动，确认底层表情、眼神、眨眼"
                "与 idle 正常演进且附件只出现一份；再次双击只移除附件，"
                "保留当前表情与眼神。\n"
                "5. 检查四根菜单、Device > UI assets、返回；始终居中、"
                "方向正确、无旧层、裁切、404、重叠、调试参数或麦克风权限请求。"
            ),
            "expected_text": (
                "选择通过表示 COMP-REQ-539 browser-only successor "
                "成为人工回归合同；选择失败会保留机器证据并返回 Faraday "
                "迭代。备注允许留空。"
            ),
        },
        "bindings": [
            identity(args.source_commit, name, path)
            for name, path in source_paths.items()
        ] + [
            artifact(name, path)
            for name, path in artifacts.items()
        ],
        "owner_result": {
            "path": (VALIDATION / "owner-review.json").as_posix(),
            "must_not_exist_before_execute": True,
        },
        "lifecycle": {
            "default_off": True,
            "execute_performed": False,
            "single_prompt": True,
            "microphone_permission_request": 0,
            "hardware": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = canonical_bytes(packet)
    output_path.write_bytes(output)
    print(json.dumps({
        "bindings": len(packet["bindings"]),
        "output": output_path.relative_to(ROOT).as_posix(),
        "sha256": sha256(output),
        "status": packet["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
