#!/usr/bin/env python3
"""Materialize every v9 home-scene keyframe as a one-page owner review artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200"
MANIFEST = V9 / "v9-expression-cemp-manifest.json"
OUT = V9 / "review-pages"
REPORT = ROOT / "docs/validation/companion-v9-home-storyboard-review-20260717.json"

SEMANTICS = {
    "idle": ("平静", "无互动时的日常首页", "主页基线；不轮播到其他情绪"),
    "touch": ("好奇", "短按释放", "看向触点后回到平静"),
    "swipe_left": ("友好回应", "向左滑", "方向化回应后回到平静"),
    "swipe_right": ("友好回应", "向右滑", "方向化回应后回到平静"),
    "swipe_up": ("惊喜", "向上滑", "轻微上扬后回到平静"),
    "swipe_down": ("亲昵", "向下滑", "爱心回应后回到平静"),
    "listening": ("专注倾听", "准备或等待语音", "由语音结果接到录音、说话或平静"),
    "recording": ("专注记录", "双击开始录音", "录音结束进入保存"),
    "saving": ("耐心等待", "录音结束并写入", "保存成功或错误"),
    "saved": ("满足", "录音保存完成", "短暂停留后回到平静"),
    "sleep": ("困倦", "三分钟无互动", "静态睡眠；不做周期刷新"),
    "menu_hold": ("思考确认", "三秒长按", "进入菜单或取消后回到平静"),
    "wake": ("醒来", "触摸或中断唤醒", "一段短过渡后回到平静"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    states: list[dict[str, object]] = []
    for order, clip in enumerate(manifest["clips"], start=1):
        name = clip["name"]
        if name not in SEMANTICS:
            raise SystemExit(f"FAIL: no semantic contract for v9 clip {name}")
        emotion, trigger, transition = SEMANTICS[name]
        frames = []
        for frame_order, frame in enumerate(clip["frames"], start=1):
            source = V9 / frame["source"]
            target = OUT / f"{order:02d}-{name}" / f"{frame_order:02d}-{source.stem}.png"
            if args.write:
                target.parent.mkdir(parents=True, exist_ok=True)
                image = Image.open(source).convert("1")
                if image.size != (200, 200):
                    raise ValueError(f"{source} is not 200x200")
                image.save(target, format="PNG")
            frames.append({
                "phase": ("entry", "sustain", "settle")[frame_order - 1],
                "duration_ms": frame["duration_ms"],
                "source": source.relative_to(ROOT).as_posix(),
                "source_sha256": digest(source),
                "review_page": target.relative_to(ROOT).as_posix(),
                "review_page_sha256": digest(target) if target.is_file() else None,
            })
        states.append({
            "order": order,
            "clip": name,
            "emotion": emotion,
            "trigger": trigger,
            "transition": transition,
            "frames": frames,
        })
    report = {
        "schema": "companion.v9_home_storyboard_review.v1",
        "status": "PASS_MACHINE_ONE_PAGE_PER_KEYFRAME_PENDING_OWNER",
        "source_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "source_sha256": digest(ROOT / manifest["provenance"]["source"]),
        "states": states,
        "runtime_boundary": {"pbm_imported": False, "cemp_packed": False, "external_flash_provisioned": False, "firmware_flashed": False, "runtime_resource_activated": False},
        "review_rule": "Review every 200x200 entry, sustain and settle page in listed state order. Runtime chooses states by trigger; it never cycles this review order randomly.",
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected = ["idle", "touch", "swipe_left", "swipe_right", "swipe_up", "swipe_down", "listening", "recording", "saving", "saved", "sleep", "menu_hold", "wake"]
    if [state["clip"] for state in states] != expected or any(frame["review_page_sha256"] is None for state in states for frame in state["frames"]):
        raise SystemExit("FAIL: v9 home storyboard review pages are incomplete")
    print(f"PASS: v9 home storyboard materialized {len(states)} states and {sum(len(state['frames']) for state in states)} single-page keyframes -> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
