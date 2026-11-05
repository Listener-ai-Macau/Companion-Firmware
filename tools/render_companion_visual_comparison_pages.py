#!/usr/bin/env python3
"""Build paired locked-art versus desktop-output pages for G2 review only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER, normalize, translate


ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "docs" / "validation"
ART = ROOT / "docs" / "art" / "iterations"
REPORT = VALIDATION / "companion-ui-visual-comparison-pages-20260717.json"
OUT = ART / "companion-visual-comparison-v1" / "review-pages"
V9 = VALIDATION / "companion-v9-home-storyboard-review-20260717.json"
V9_RENDER = ART / "companion-pet-expression-v9" / "rendered-200x200" / "v9-expression-render-report.json"
MENU = VALIDATION / "companion-menu-v7-screen-family-preview-20260717.json"
SPECIAL = VALIDATION / "companion-pet-special-state-one-page-review-20260717.json"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
CANVAS = (200, 200)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size=size)


def compare(left: Image.Image, right: Image.Image) -> int:
    left_bytes = left.convert("1").tobytes()
    right_bytes = right.convert("1").tobytes()
    return sum((left_byte ^ right_byte).bit_count() for left_byte, right_byte in zip(left_bytes, right_bytes, strict=True))


def write_comparison(
    family: str,
    index: int,
    identifier: str,
    baseline: Image.Image,
    output: Image.Image,
    relation: str,
    result: str,
) -> Path:
    scale = 2
    panel = (CANVAS[0] * scale, CANVAS[1] * scale)
    page = Image.new("RGB", (850, 500), "white")
    draw = ImageDraw.Draw(page)
    draw.text((20, 15), f"{family} · {index:02d} · {identifier}", fill="black", font=font(18))
    draw.text((20, 47), "锁定生图基线", fill="black", font=font(15))
    draw.text((435, 47), "电脑端 200×200 输出", fill="black", font=font(15))
    left = baseline.convert("RGB").resize(panel, Image.Resampling.NEAREST)
    right = output.convert("RGB").resize(panel, Image.Resampling.NEAREST)
    page.paste(left, (20, 78))
    page.paste(right, (435, 78))
    draw.rectangle((19, 77, 420, 478), outline="black", width=2)
    draw.rectangle((434, 77, 835, 478), outline="black", width=2)
    draw.text((20, 480), f"机器关系：{relation} · {result}", fill="black", font=font(12))
    output_path = OUT / family / f"{index:02d}-{identifier}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.save(output_path, format="PNG")
    return output_path


def v9_pages() -> list[dict[str, object]]:
    review = json.loads(V9.read_text(encoding="utf-8"))
    render = json.loads(V9_RENDER.read_text(encoding="utf-8"))
    render_by_key = {(frame["clip"], frame["phase"]): frame for frame in render["frames"]}
    source = Image.open(ROOT / render["source"]).convert("L")
    pages: list[dict[str, object]] = []
    index = 1
    for state in review["states"]:
        for frame in state["frames"]:
            rendered = render_by_key[(state["clip"], frame["phase"])]
            baseline = source.crop(tuple(rendered["source_crop_box"])).resize(CANVAS, Image.Resampling.LANCZOS)
            canonical, anchor = normalize(baseline, CANONICAL_CENTER)
            if rendered["anchor_policy"] != ANCHOR_POLICY:
                raise ValueError(f"v9 anchor policy drift for {state['clip']}.{frame['phase']}")
            if list(anchor.source_anchor) != rendered["source_anchor"]:
                raise ValueError(f"v9 source anchor drift for {state['clip']}.{frame['phase']}")
            if list(anchor.normalization_offset) != rendered["normalization_offset"]:
                raise ValueError(f"v9 normalization offset drift for {state['clip']}.{frame['phase']}")
            expected = translate(canonical, tuple(rendered["phase_offset"]))
            desktop = Image.open(ROOT / rendered["path"]).convert("1")
            difference = compare(expected, desktop)
            if difference:
                raise ValueError(f"v9 source-to-PBM mismatch for {state['clip']}.{frame['phase']}: {difference} pixels")
            comparison = write_comparison(
                "home-v9-daily-storyboard",
                index,
                f"{state['clip']}-{frame['phase']}",
                baseline,
                desktop,
                "锁定裁剪 + 整组中心归一化 + 已记录动效位移",
                "PASS: 0 像素偏差",
            )
            pages.append({
                "index": index,
                "id": f"{state['clip']}-{frame['phase']}",
                "baseline": {
                    "path": rendered["source"],
                    "sha256": rendered["source_sha256"],
                    "crop_box": rendered["source_crop_box"],
                },
                "desktop_output": {"path": rendered["path"], "sha256": rendered["sha256"]},
                "relation": "source_crop_threshold_whole_expression_anchor_normalization_phase_translation_to_pbm",
                "machine_result": {
                    "status": "PASS_EXACT",
                    "different_pixels": difference,
                    "anchor_policy": rendered["anchor_policy"],
                    "source_anchor": rendered["source_anchor"],
                    "canonical_center": rendered["canonical_center"],
                    "normalization_offset": rendered["normalization_offset"],
                    "phase_offset": rendered["phase_offset"],
                    "requested_center": rendered["requested_center"],
                    "final_output_bounds": rendered["final_output_bounds"],
                },
                "comparison_page": {"path": rel(comparison), "sha256": digest(comparison)},
            })
            index += 1
    if len(pages) != 39:
        raise ValueError("v9 comparison page count drifted")
    return pages


def menu_pages() -> list[dict[str, object]]:
    report = json.loads(MENU.read_text(encoding="utf-8"))
    source = Image.open(ROOT / report["source"]["path"]).convert("L")
    pages: list[dict[str, object]] = []
    index = 1
    for screen in report["pages"]:
        baseline = ImageOps.pad(source.crop(tuple(screen["source_crop"])), CANVAS, method=Image.Resampling.LANCZOS, color=255, centering=(0.5, 0.5)).convert("L")
        raw = Image.open(ROOT / screen["review_pages"]["source"]["path"]).convert("1")
        raw_difference = compare(baseline.convert("1"), raw)
        if raw_difference:
            raise ValueError(f"menu source crop mismatch for {screen['id']}: {raw_difference} pixels")
        for language in ("source", "en", "zh_cn"):
            output_data = screen["review_pages"][language]
            desktop = Image.open(ROOT / output_data["path"]).convert("1")
            relation = "locked_source_crop_to_desktop_preview" if language == "source" else "locked_source_geometry_with_localized_desktop_text_overlay"
            result = "PASS: 0 像素偏差" if language == "source" else "PASS: 锁定版式 + 明确本地化覆盖"
            comparison = write_comparison(
                "menu-v7-screen-family",
                index,
                f"{screen['id']}-{language}",
                baseline,
                desktop,
                "锁定版式" if language == "source" else "锁定版式 + 单语言文字覆盖",
                result,
            )
            pages.append({
                "index": index,
                "id": f"{screen['id']}-{language}",
                "baseline": {
                    "path": report["source"]["path"],
                    "sha256": report["source"]["sha256"],
                    "crop_box": screen["source_crop"],
                },
                "desktop_output": {"path": output_data["path"], "sha256": output_data["sha256"]},
                "relation": relation,
                "machine_result": {
                    "status": "PASS_EXACT" if language == "source" else "PASS_LOCALIZED_TARGET",
                    "different_pixels": raw_difference if language == "source" else None,
                    "language": language,
                    "labels": output_data.get("labels", []),
                },
                "comparison_page": {"path": rel(comparison), "sha256": digest(comparison)},
            })
            index += 1
    if len(pages) != 15:
        raise ValueError("menu comparison page count drifted")
    return pages


def special_pages(identifier: str) -> list[dict[str, object]]:
    report = json.loads(SPECIAL.read_text(encoding="utf-8"))
    source_data = next(item for item in report["sources"] if item["id"] == identifier)
    source = Image.open(ROOT / source_data["source"]).convert("L")
    pages: list[dict[str, object]] = []
    for page in source_data["pages"]:
        baseline = source.crop(tuple(page["source_crop_box"])).resize(CANVAS, Image.Resampling.LANCZOS)
        expected, anchor = normalize(baseline, CANONICAL_CENTER)
        if page["anchor_policy"] != ANCHOR_POLICY:
            raise ValueError(f"special anchor policy drift for {page['state']}")
        if list(anchor.source_anchor) != page["source_anchor"]:
            raise ValueError(f"special source anchor drift for {page['state']}")
        if list(anchor.normalization_offset) != page["normalization_offset"]:
            raise ValueError(f"special normalization offset drift for {page['state']}")
        desktop = Image.open(ROOT / page["review_page"]).convert("1")
        difference = compare(expected, desktop)
        if difference:
            raise ValueError(f"special source-to-preview mismatch for {page['state']}: {difference} pixels")
        comparison = write_comparison(
            identifier,
            page["index"],
            page["state"].replace(".", "-"),
            baseline,
            desktop,
            "锁定裁剪 + 整组中心归一化",
            "PASS: 0 像素偏差",
        )
        pages.append({
            "index": page["index"],
            "id": page["state"].replace(".", "-"),
            "baseline": {
                "path": source_data["source"],
                "sha256": source_data["source_sha256"],
                "crop_box": page["source_crop_box"],
            },
            "desktop_output": {"path": page["review_page"], "sha256": page["review_page_sha256"]},
            "relation": "source_crop_threshold_whole_expression_anchor_normalization_to_desktop_preview",
            "machine_result": {
                "status": "PASS_EXACT",
                "different_pixels": difference,
                "anchor_policy": page["anchor_policy"],
                "source_anchor": page["source_anchor"],
                "canonical_center": page["canonical_center"],
                "normalization_offset": page["normalization_offset"],
                "phase_offset": page["phase_offset"],
                "requested_center": page["requested_center"],
                "final_output_bounds": page["final_output_bounds"],
            },
            "comparison_page": {"path": rel(comparison), "sha256": digest(comparison)},
        })
    if len(pages) != 12:
        raise ValueError(f"{identifier} comparison page count drifted")
    return pages


def build() -> dict[str, object]:
    items = [
        {"id": "home-v9-daily-storyboard", "pages": v9_pages()},
        {"id": "menu-v7-screen-family", "pages": menu_pages()},
        {"id": "special-system-v1", "pages": special_pages("special-system-v1")},
        {"id": "special-journey-v1", "pages": special_pages("special-journey-v1")},
    ]
    return {
        "schema": "companion.ui_visual_comparison_pages.v1",
        "status": "PASS_PAIRED_ART_BASELINE_AND_DESKTOP_OUTPUT_READY",
        "review_scope": "Each G2 page shows the locked generated-art baseline beside its deterministic 200x200 desktop output. This is not a physical e-paper-panel acceptance.",
        "items": items,
        "page_total": sum(len(item["pages"]) for item in items),
        "runtime_boundary": {
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "runtime_resource_activated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        REPORT.write_text(rendered, encoding="utf-8")
    elif not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != rendered:
        print(f"FAIL: stale {rel(REPORT)}")
        return 1
    print(f"PASS: paired {report['page_total']} locked-art and desktop-output G2 pages -> {rel(REPORT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
