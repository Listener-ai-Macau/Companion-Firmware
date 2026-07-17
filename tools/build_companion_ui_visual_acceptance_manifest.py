#!/usr/bin/env python3
"""Build the non-activating, one-original-image-at-a-time G2 review manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/validation/companion-ui-visual-acceptance-manifest-20260717.json"
V9 = ROOT / "docs/validation/companion-v9-home-storyboard-review-20260717.json"
MENU = ROOT / "docs/validation/companion-menu-v7-screen-family-preview-20260717.json"
SPECIAL = ROOT / "docs/validation/companion-pet-special-state-one-page-review-20260717.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def item(
    sequence: int,
    identifier: str,
    display_name: str,
    source_sha256: str,
    evidence: Path,
    images: list[dict[str, object]],
    target: str,
    action: str,
    success: list[str],
    failure: str,
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "id": identifier,
        "display_name": display_name,
        "scope": "One locked computer-side original or deterministic 200x200 page is shown per canonical Chinese prompt. It is not a physical e-paper review: direction, clipping, refresh residue and touch require later G4/G5 hardware evidence. This records a source observation only and never activates a product resource.",
        "source_sha256": source_sha256,
        "machine_evidence": evidence.relative_to(ROOT).as_posix(),
        "artifact_review": {"mode": "original_image_one_at_a_time", "images": images},
        "operator_prompt": {
            "target": target,
            "operator_action": action,
            "success_signal": success,
            "failure_rule": failure,
            "continue_condition": "选择“已执行”仅表示本张已查看且未提出修改；它不会导入 PBM/CEMP、写入 Flash、刷固件或启用运行时资源。",
            "recovery_condition": "选择“需修改”后保持当前页；备注必须说明具体状态/行号和可见问题。先 triage，再修改一个明确来源变量并重新生成、校验和逐页复查。",
            "record_fields": ["当前页状态或菜单页", "触发/功能语义", "身份或布局观察", "200x200 可读性/裁切", "选择结果", "备注"],
        },
        "owner_decision": "PENDING_OWNER_VISUAL_REVIEW",
        "runtime_boundary": "No PBM/CEMP, Flash, firmware, target-font or runtime-resource activation.",
    }


def home_images(data: dict[str, object]) -> list[dict[str, object]]:
    images: list[dict[str, object]] = []
    index = 1
    for state in data["states"]:
        for frame in state["frames"]:
            images.append({
                "index": index,
                "id": f"{state['clip']}-{frame['phase']}",
                "label": f"首页原图：{state['order']:02d} {state['clip']} · {frame['phase']}",
                "path": frame["review_page"],
                "sha256": frame["review_page_sha256"],
                "context": {
                    "state": state["clip"],
                    "emotion": state["emotion"],
                    "trigger": state["trigger"],
                    "relation": state["transition"],
                    "phase": frame["phase"],
                    "duration_ms": frame["duration_ms"],
                },
            })
            index += 1
    return images


def menu_images(data: dict[str, object]) -> list[dict[str, object]]:
    images: list[dict[str, object]] = []
    index = 1
    for page in data["pages"]:
        for language in ("source", "en", "zh_cn"):
            image = page["review_pages"][language]
            language_label = {"source": "原始版式", "en": "English", "zh_cn": "中文"}[language]
            images.append({
                "index": index,
                "id": f"{page['id']}-{language}",
                "label": f"菜单原图：{page['order']:02d} {page['title']} · {language_label}",
                "path": image["path"],
                "sha256": image["sha256"],
                "context": {
                    "screen": page["id"],
                    "screen_title": page["title"],
                    "language": language,
                    "labels": image.get("labels", []),
                    "source_crop": page["source_crop"],
                },
            })
            index += 1
    return images


def special_images(data: dict[str, object], identifier: str) -> list[dict[str, object]]:
    source = next(source for source in data["sources"] if source["id"] == identifier)
    return [
        {
            "index": page["index"],
            "id": page["state"].replace(".", "-"),
            "label": f"特殊场景原图：{page['index']:02d} {page['state']}",
            "path": page["review_page"],
            "sha256": page["review_page_sha256"],
            "context": {
                "state": page["state"],
                "emotion": page["emotion"],
                "intent": page["intent"],
                "minimum_clearance_px": page["minimum_clearance_px"],
            },
        }
        for page in source["pages"]
    ]


def build() -> dict[str, object]:
    v9 = json.loads(V9.read_text(encoding="utf-8"))
    menu = json.loads(MENU.read_text(encoding="utf-8"))
    special = json.loads(SPECIAL.read_text(encoding="utf-8"))
    for report in (v9, menu, special):
        if not str(report.get("status", "")).startswith("PASS_MACHINE"):
            raise ValueError(f"machine evidence is not ready: {report.get('status')}")
    items = [
        item(
            1, "home-v9-daily-storyboard", "首页表情序列", v9["source_sha256"], V9, home_images(v9),
            "按真实日常触发顺序检查 v9 首页 13 个状态的 entry、sustain、settle 单页关键帧。",
            "确认本页仍是同一只 Companion：眼睛、眉、嘴、脸颊身份一致；再按本页的状态、触发和相位判断情绪是否清楚。",
            ["五官是同一套 v9 身份，而不是旧工程脸或随机贴图。", "本页的触发、情绪和关键帧关系可读，200x200 内无裁切。", "它只描述事件驱动状态，不表示主页会按验收顺序随机轮播。"],
            "出现身份漂移、旧表情、情绪/触发不清、画布裁切或与本页状态不符时选择“需修改”。",
        ),
        item(
            2, "menu-v7-screen-family", "紧凑四行菜单", menu["source"]["sha256"], MENU, menu_images(menu),
            "检查 v7.3 无表情菜单家族：首页四根，以及 Voice、Device、Connection、Preferences 详情页的原始版式、English 和中文 200x200 页面。",
            "首页确认四个等高根行与图标/箭头；详情确认紧凑返回和标题、真实行项目、单一语言及无表情占位。",
            ["首页只有 Voice、Device、Connection、Preferences 四行，图标和箭头清晰。", "详情页没有宠物脸；最多四项真实内容，Connection 只有三项，未用假控制项填空。", "English/中文页面单语言、可读，文字不截断。"],
            "出现表情占位、第五行、旧六根/双页、假行或假箭头、混合语言、不可读文字或裁切时选择“需修改”。",
        ),
        item(
            3, "special-system-v1", "特殊系统场景", next(source for source in special["sources"] if source["id"] == "special-system-v1")["source_sha256"], SPECIAL, special_images(special, "special-system-v1"),
            "检查 speaking、录音错误、电源、连接和系统错误的 12 张独立 200x200 特殊场景原图。",
            "逐页确认 v9 身份、状态符号和本页语义；本机已证明画布至少保留 4 px 边缘空白，但这不取代真实面板检查。",
            ["五官身份保持 v9 一致。", "状态含义可区分且不是工程测试脸。", "画布内无可见裁切。"],
            "出现身份漂移、状态难辨、旧美术、不可爱眼神或可见裁切时选择“需修改”。",
        ),
        item(
            4, "special-journey-v1", "特殊旅程场景", next(source for source in special["sources"] if source["id"] == "special-journey-v1")["source_sha256"], SPECIAL, special_images(special, "special-journey-v1"),
            "检查菜单进入/退出和升级旅程的 12 张独立 200x200 特殊场景原图。",
            "逐页确认 v9 身份、旅程阶段和本页语义；菜单表情只承担进入/退出过渡，不替代无表情四行菜单本体。",
            ["五官身份保持 v9 一致。", "菜单与升级阶段可相互区分。", "画布内无可见裁切。"],
            "出现身份漂移、旅程语义不清、旧菜单/旧表情或可见裁切时选择“需修改”。",
        ),
    ]
    for review in items:
        for image in review["artifact_review"]["images"]:
            path = ROOT / image["path"]
            if not path.is_file() or digest(path) != image["sha256"]:
                raise ValueError(f"review image hash drifted: {image['path']}")
    return {
        "schema": "companion.ui_visual_acceptance_manifest.v2",
        "status": "READY_FOR_SEQUENTIAL_OWNER_REVIEW",
        "review_style": "canonical Chinese aiw operator-prompt; one original image at a time; button 已执行 is an observation, not a runtime or source-import pass; any note or 需修改 result becomes a triage requirement",
        "items": items,
        "final_gate": "Only a complete, triaged per-page review can be considered by a separate PBM/CEMP import proposal. No per-page observation activates a runtime resource or permits a panel flash.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = build()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        MANIFEST.write_text(rendered, encoding="utf-8")
    elif not MANIFEST.is_file() or MANIFEST.read_text(encoding="utf-8") != rendered:
        print(f"FAIL: stale {MANIFEST.relative_to(ROOT)}")
        return 1
    print(f"PASS: built {len(result['items'])} sequential visual-source families and {sum(len(item['artifact_review']['images']) for item in result['items'])} one-page reviews -> {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
