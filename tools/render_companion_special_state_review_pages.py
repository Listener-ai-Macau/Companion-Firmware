#!/usr/bin/env python3
"""Materialize each locked special-state source cell as one 200x200 review page.

This creates review PNGs only. It deliberately does not create PBM/CEMP assets
or change any runtime resource boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/art/iterations/companion-pet-special-states-v1"
PREFLIGHT = ROOT / "docs/validation/companion-pet-special-state-crop-preflight-20260717.json"
OUT = ART / "review-pages"
REPORT = ROOT / "docs/validation/companion-pet-special-state-one-page-review-20260717.json"
THRESHOLD = 180

STATE_MEANING = {
    "voice.speaking": ("说话回应", "语音回复正在输出"),
    "recording.error": ("温和提醒", "录音未能完成，需要恢复"),
    "power.charge_detected": ("注意到电源", "刚接入供电"),
    "power.charging": ("安心充电", "正在充电"),
    "power.charged": ("满足充满", "电量已充足"),
    "power.low_battery": ("轻微求助", "电量偏低"),
    "link.pairing": ("期待连接", "正在配对"),
    "link.connected": ("连接成功", "设备已连上"),
    "link.syncing": ("耐心同步", "正在同步"),
    "link.synced": ("同步完成", "数据已同步"),
    "link.error": ("温和提示", "连接需要恢复"),
    "system.error": ("安静求助", "系统需要处理"),
    "menu.open.entry": ("思考确认", "长按进入菜单的起始帧"),
    "menu.open.settle": ("准备切换", "进入菜单前的停留帧"),
    "menu.blocked": ("礼貌阻止", "当前状态不能进入菜单"),
    "menu.exit": ("轻松返回", "从菜单回到首页"),
    "upgrade.offer": ("好奇询问", "发现可用升级"),
    "upgrade.prepare": ("准备开始", "升级前检查"),
    "upgrade.transfer": ("耐心等待", "升级数据传输中"),
    "upgrade.verify": ("认真确认", "升级校验中"),
    "upgrade.restart": ("短暂告别", "即将重启"),
    "upgrade.success": ("开心完成", "升级已完成"),
    "upgrade.error": ("温和提醒", "升级遇到问题"),
    "upgrade.error.recovery": ("恢复信心", "升级失败后的可恢复状态"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def page_name(index: int, state: str) -> str:
    return f"{index:02d}-{state.replace('.', '-')}.png"


def render(source: Path, crop_box: list[int]) -> Image.Image:
    image = Image.open(source).convert("L")
    page = image.crop(tuple(crop_box)).resize((200, 200), Image.Resampling.LANCZOS)
    return page.point(lambda pixel: 0 if pixel < THRESHOLD else 255, "1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    sources: list[dict[str, object]] = []
    errors: list[str] = []
    for source_data in preflight.get("sources", []):
        source_path = ROOT / source_data["source"]
        identifier = source_data["id"]
        pages: list[dict[str, object]] = []
        if not source_path.is_file():
            errors.append(f"missing {source_data['source']}")
            continue
        for position, frame in enumerate(source_data.get("frames", []), start=1):
            state = frame["state"]
            if state not in STATE_MEANING:
                errors.append(f"missing semantic meaning for {state}")
                continue
            target = OUT / identifier / page_name(position, state)
            if args.write:
                target.parent.mkdir(parents=True, exist_ok=True)
                render(source_path, frame["source_crop_box"]).save(target, format="PNG")
            if not target.is_file():
                errors.append(f"missing review page {target.relative_to(ROOT).as_posix()}")
                continue
            emotion, intent = STATE_MEANING[state]
            pages.append({
                "index": position,
                "state": state,
                "emotion": emotion,
                "intent": intent,
                "source_crop_box": frame["source_crop_box"],
                "review_page": target.relative_to(ROOT).as_posix(),
                "review_page_sha256": digest(target),
                "minimum_clearance_px": frame["minimum_clearance_px"],
                "edge_ink_pixels": frame["edge_ink_pixels"],
            })
        if len(pages) != 12:
            errors.append(f"{identifier} produced {len(pages)} rather than 12 pages")
        sources.append({
            "id": identifier,
            "source": source_data["source"],
            "source_sha256": source_data["source_sha256"],
            "pages": pages,
        })

    report = {
        "schema": "companion.pet_special_state_one_page_review.v1",
        "status": "PASS_MACHINE_ONE_PAGE_PER_SPECIAL_STATE_PENDING_OWNER" if not errors else "FAIL",
        "sources": sources,
        "runtime_boundary": {
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "runtime_resource_activated": False,
        },
        "review_rule": "Open every state page alone in source order. Each page remains review-only and cannot activate a visual resource.",
        "errors": errors,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        REPORT.write_text(rendered, encoding="utf-8")
    elif not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale {REPORT.relative_to(ROOT).as_posix()}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: materialized {sum(len(source['pages']) for source in sources)} special-state single-page reviews -> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
