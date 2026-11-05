#!/usr/bin/env python3
"""Export current V45 event ornaments without redrawing or activating them.

The exporter is intentionally strict: only component IDs registered by the
current V45 two-track layout are copied. Historical heart/star/moon assets are
reported as unavailable, never silently promoted into the WBA candidate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate"
TRACK_PATH = SOURCE_DIR / "two-track-layout.json"
LAYOUT_PATH = SOURCE_DIR / "v45-special-component-layout.json"
PROFILE_PATH = SOURCE_DIR / "target-score-attempt-01/v45-wb55-target-profile-plan.json"
OUT = ROOT / "docs/art/iterations/companion-wba-expression-v1/events"

SELECTED_IDS = {
    512, 513, 514, 521, 522, 523, 545, 546, 547,
    563, 564, 565, 566, 567, 568, 572, 573, 574,
    594, 595, 596, 605, 606, 607, 608,
}

# Suggested independent upper-zone anchors. They move registered masks only;
# the mask bytes and dimensions never change. The error masks are 41 px high,
# so their y=25 anchor ends at y=65, still clear of the face but one row beyond
# the preferred y25..64 band. This exception is recorded in the manifest.
ANCHORS = {
    512: (148, 38), 513: (145, 34), 514: (142, 29),
    521: (99, 42), 522: (96, 35), 523: (94, 25),
    545: (85, 30), 546: (86, 30), 547: (86, 30),
    563: (92, 25), 564: (92, 25), 565: (92, 25),
    566: (86, 25), 567: (86, 25), 568: (86, 25),
    572: (86, 45), 573: (86, 45), 574: (86, 45),
    594: (94, 27), 595: (116, 42), 596: (134, 54),
    605: (170, 33), 606: (160, 38), 607: (157, 38), 608: (154, 36),
}

EVENTS = [
    {
        "name": "recording_input",
        "kind": "functional",
        "meaning": "真实麦克风采集正在进行；麦克风固定，输入波纹独立变化。",
        "triggerContract": "capture_active=true from the recording service; never infer from pet emotion",
        "sequence": [[605, 606], [605, 607], [605, 608], [605, 607], [605, 606]],
        "durationsMs": [260, 240, 520, 240, 680],
        "stages": {"entered": ([0], [605, 606]), "hold": ([1, 2, 3], [605, 608]), "exit": ([4], [605, 606])},
    },
    {
        "name": "upgrade_progress",
        "kind": "functional",
        "meaning": "固件或资源更新确实处于安装/验证流程。",
        "triggerContract": "verified update-service state only",
        "sequence": [[563], [564], [565], [564], [565]],
        "durationsMs": [420, 280, 520, 280, 680],
        "stages": {"entered": ([0], [563]), "hold": ([1, 2], [565]), "exit": ([3, 4], [565])},
    },
    {
        "name": "error_caution",
        "kind": "functional",
        "meaning": "真实功能错误或需要用户注意的恢复状态。",
        "triggerContract": "nonzero product error/result state only",
        "sequence": [[566], [567], [568], [567], [568]],
        "durationsMs": [220, 220, 620, 220, 820],
        "stages": {"entered": ([0], [566]), "hold": ([1, 2], [568]), "exit": ([3, 4], [568])},
    },
    {
        "name": "bottom_connector_charging",
        "kind": "functional",
        "meaning": "检测到真实充电/底座供电状态。",
        "triggerContract": "measured charging state only; battery estimate is insufficient",
        "sequence": [[572], [573], [574], [573], [574]],
        "durationsMs": [300, 260, 520, 260, 680],
        "stages": {"entered": ([0], [572]), "hold": ([1, 2], [574]), "exit": ([3, 4], [574])},
    },
    {
        "name": "menu_entry_notice",
        "kind": "functional",
        "meaning": "进入菜单前的短提示；结束后所有角色与功能层撤出。",
        "triggerContract": "accepted menu-entry gesture only",
        "sequence": [[545], [546], [547]],
        "durationsMs": [140, 140, 180],
        "stages": {"entered": ([0], [545]), "hold": ([1], [546]), "exit": ([2], [547])},
        "afterLastCue": "withdraw_expression_and_functional_tracks_then_show_menu_ui",
    },
    {
        "name": "curious_question",
        "kind": "emotion",
        "meaning": "宠物自身的好奇/提问装饰，不表示任何设备功能。",
        "triggerContract": "curious expression choreography only",
        "sequence": [[], [512], [513], [514], []],
        "durationsMs": [180, 180, 260, 760, 360],
        "stages": {"entered": ([1], [512]), "hold": ([3], [514]), "exit": ([4], [])},
    },
    {
        "name": "alert_exclamation",
        "kind": "emotion",
        "meaning": "宠物自身的警觉/惊讶装饰；功能错误仍使用 error_caution。",
        "triggerContract": "alert expression choreography only",
        "sequence": [[], [521], [522], [523], []],
        "durationsMs": [180, 180, 260, 760, 360],
        "stages": {"entered": ([1], [521]), "hold": ([3], [523]), "exit": ([4], [])},
    },
    {
        "name": "sleep_zzz",
        "kind": "emotion",
        "meaning": "困倦情绪的 ZZZ 装饰；当前 V45 明确不使用月亮或云。",
        "triggerContract": "sleepy expression choreography only",
        "sequence": [[], [], [594], [594, 595], [594, 595, 596]],
        "durationsMs": [420, 360, 320, 420, 1400],
        "stages": {"entered": ([2], [594]), "hold": ([3, 4], [594, 595, 596]), "exit": ([], [])},
        "exitNote": "no registered exit mask; withdraw layer at the expression boundary",
    },
]

COMPONENT_KIND = {
    **{component_id: "functional" for component_id in range(545, 575)},
    **{component_id: "functional" for component_id in range(605, 609)},
    **{component_id: "emotion" for component_id in (512, 513, 514, 521, 522, 523, 594, 595, 596)},
}

SEMANTICS = {
    512: "curious question entered", 513: "curious question grows", 514: "curious question hold",
    521: "alert exclamation entered", 522: "alert exclamation grows", 523: "alert exclamation hold",
    545: "menu entry entered", 546: "menu entry hold", 547: "menu entry exit",
    563: "update progress entered", 564: "update progress intermediate", 565: "update progress hold",
    566: "error caution entered", 567: "error caution intermediate", 568: "error caution hold",
    572: "charging entered", 573: "charging intermediate", 574: "charging hold",
    594: "sleep Z large", 595: "sleep Z medium", 596: "sleep Z small",
    605: "recording microphone static", 606: "recording wave quiet", 607: "recording wave medium", 608: "recording wave peak",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def event_rel(path: Path) -> str:
    """Return a path consumers can resolve from the events/ manifest root."""
    return path.relative_to(OUT).as_posix()


def load_binary_mask(path: Path, expected_size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("1")
    if image.size != expected_size or not set(image.getdata()).issubset({0, 255}):
        raise ValueError(f"invalid binary mask geometry: {rel(path)}")
    return image


def make_layer(mask: Image.Image, anchor: tuple[int, int]) -> Image.Image:
    x, y = anchor
    if x < 0 or y < 0 or x + mask.width > 200 or y + mask.height > 200:
        raise ValueError(f"mask does not fit 200x200 at {anchor}")
    layer = Image.new("1", (200, 200), 1)
    layer.paste(mask, anchor)
    return layer


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def historical_missing() -> list[dict]:
    base = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
    manifest = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json"
    rows = [
        ("sync_progress", None, "No independent sync component is registered in V45; retain the current product status-rail sync icon."),
        ("save_progress_or_complete", None, "No independent save component is registered in V45; retain the current product status-rail save/saved icons."),
        ("heart", base / "charm_heart.pbm", "Historical V9 charm is not a current V45 registered component."),
        ("star", base / "charm_star.pbm", "Historical V9 charm is not a current V45 registered component."),
        ("moon", base / "charm_sleep_moon_z.pbm", "Historical V9 charm is excluded; current V45 explicitly forbids moon/crescent/cloud for sleep."),
    ]
    result = []
    for name, path, reason in rows:
        item = {"name": name, "currentV45Registered": False, "exported": False, "reason": reason}
        if path and path.exists():
            item.update(historicalSourcePbm=rel(path), historicalSourceSha256=sha256(path))
        elif name.startswith(("sync", "save")) and manifest.exists():
            item.update(historicalFullFrameManifest=rel(manifest), historicalManifestSha256=sha256(manifest))
        result.append(item)
    return result


def main() -> int:
    track = json.loads(TRACK_PATH.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if layout.get("revision") != 45 or len(layout.get("components", [])) != 60:
        raise ValueError("current V45 registry identity mismatch")
    if track["source_authority"]["v45_special_layout"]["sha256"].lower() != sha256(LAYOUT_PATH):
        raise ValueError("two-track layout does not identify the current V45 special layout")
    by_id = {item["component_id"]: item for item in layout["components"]}
    if not SELECTED_IDS.issubset(by_id):
        raise ValueError(f"missing selected V45 component IDs: {sorted(SELECTED_IDS - by_id.keys())}")

    if OUT.exists():
        shutil.rmtree(OUT)
    for name in ("pbm", "small", "layers", "stages"):
        (OUT / name).mkdir(parents=True, exist_ok=True)

    components = []
    layer_by_id: dict[int, Image.Image] = {}
    for component_id in sorted(SELECTED_IDS):
        item = by_id[component_id]
        source = ROOT / item["mask"]
        size = tuple(item["mask_size"])
        if sha256(source).lower() != item["mask_sha256"].lower():
            raise ValueError(f"registered PBM hash drift: {item['name']}")
        mask = load_binary_mask(source, size)
        anchor = ANCHORS[component_id]
        stem = f"{component_id}-{item['name']}"
        output_pbm = OUT / "pbm" / f"{stem}.pbm"
        output_small = OUT / "small" / f"{stem}.png"
        output_layer = OUT / "layers" / f"{stem}.png"
        shutil.copyfile(source, output_pbm)
        mask.save(output_small, optimize=False)
        layer = make_layer(mask, anchor)
        layer.save(output_layer, optimize=False)
        layer_by_id[component_id] = layer
        source_bottom = item["base_position"][1] + size[1] - 1
        suggested_bottom = anchor[1] + size[1] - 1
        components.append({
            "componentId": component_id,
            "name": item["name"],
            "kind": COMPONENT_KIND[component_id],
            "semantic": SEMANTICS[component_id],
            "compositeOp": item["composite_op"],
            "sourcePbm": rel(source),
            "sourceSha256": sha256(source),
            "sourceAnchor": item["base_position"],
            "sourceBottom": source_bottom,
            "maskSize": list(size),
            "suggestedAnchor": list(anchor),
            "suggestedBottom": suggested_bottom,
            "preferredUpperZoneFit": anchor[1] >= 25 and suggested_bottom <= 64,
            "anchorNote": "one-row y65 exception; 41px registered error mask cannot fit y25..64 without forbidden rescaling"
                if component_id in (567, 568) else "registered bytes unchanged; clear of status y0..15 and face y72..143",
            "outputPbm": event_rel(output_pbm),
            "outputPbmSha256": sha256(output_pbm),
            "outputSmallPng": event_rel(output_small),
            "outputSmallPngSha256": sha256(output_small),
            "outputLayerPng": event_rel(output_layer),
            "outputLayerPngSha256": sha256(output_layer),
        })

    event_rows = []
    contact_rows = []
    for event in EVENTS:
        stages = []
        for stage_name in ("entered", "hold", "exit"):
            frame_indices, ids = event["stages"][stage_name]
            layer = Image.new("1", (200, 200), 1)
            for component_id in ids:
                layer = ImageChops.darker(layer, layer_by_id[component_id])
            output = OUT / "stages" / f"{event['name']}-{stage_name}.png"
            layer.save(output, optimize=False)
            stages.append({
                "stage": stage_name,
                "sourceFrameIndices": frame_indices,
                "representativeComponentIds": ids,
                "withdraw": not ids,
                "outputLayerPng": event_rel(output),
                "outputLayerPngSha256": sha256(output),
            })
            contact_rows.append((event["name"], stage_name, layer.convert("RGB")))
        row = {key: value for key, value in event.items() if key != "stages"}
        row["stages"] = stages
        event_rows.append(row)

    label_width = 190
    sheet = Image.new("RGB", (label_width + 3 * 202 + 4, 90 + len(EVENTS) * 230), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 14), "V45 registered event ornaments · entered / hold / exit", font=font(22), fill="black")
    draw.text((20, 48), "200x200 ink-only layers; runtime inactive; no generation-21 claim", font=font(14), fill="black")
    for row_index, event in enumerate(EVENTS):
        y = 86 + row_index * 230
        draw.text((8, y + 84), event["name"], font=font(12), fill="black")
        for column, stage_name in enumerate(("entered", "hold", "exit")):
            image = next(image for name, stage, image in contact_rows if name == event["name"] and stage == stage_name)
            x = label_width + column * 202
            sheet.paste(image, (x, y))
            draw.text((x + 4, y + 202), stage_name, font=font(12), fill="black")
    contact = OUT / "contact-sheet.png"
    sheet.save(contact, optimize=False)

    event_mapping = [
        {"runtimeEvent": "recording.capture_active", "ornament": "recording_input", "requiredTruth": "recorder reports capture_active=true"},
        {"runtimeEvent": "update.install_or_verify", "ornament": "upgrade_progress", "requiredTruth": "update service reports active nonterminal state"},
        {"runtimeEvent": "product.error_recovery", "ornament": "error_caution", "requiredTruth": "nonzero product error/result"},
        {"runtimeEvent": "power.charging", "ornament": "bottom_connector_charging", "requiredTruth": "measured charging input"},
        {"runtimeEvent": "menu.accepted_entry", "ornament": "menu_entry_notice", "requiredTruth": "accepted menu-entry gesture"},
        {"runtimeEvent": "emotion.curious", "ornament": "curious_question", "requiredTruth": "emotion track only"},
        {"runtimeEvent": "emotion.alert", "ornament": "alert_exclamation", "requiredTruth": "emotion track only; never substitute for error_caution"},
        {"runtimeEvent": "emotion.sleepy", "ornament": "sleep_zzz", "requiredTruth": "emotion track only"},
        {"runtimeEvent": "recording.saving", "ornament": None, "requiredTruth": "use existing status rail; no current V45 PBM"},
        {"runtimeEvent": "recording.saved", "ornament": None, "requiredTruth": "use existing status rail; no current V45 PBM"},
        {"runtimeEvent": "transfer.sync", "ornament": None, "requiredTruth": "use existing status rail; no current V45 PBM"},
    ]

    manifest = {
        "schema": "companion.wba.event_art.v1",
        "status": "CANDIDATE_REUSE_EXPORT_RUNTIME_INACTIVE",
        "sourceLayouts": {
            "twoTrack": {"path": rel(TRACK_PATH), "sha256": sha256(TRACK_PATH), "revision": track["revision"]},
            "specialComponents": {"path": rel(LAYOUT_PATH), "sha256": sha256(LAYOUT_PATH), "revision": layout["revision"], "registeredCount": len(by_id)},
            "targetProfile": {"path": rel(PROFILE_PATH), "sha256": sha256(PROFILE_PATH), "status": profile["status"]},
        },
        "exporter": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "canvas": {"width": 200, "height": 200, "pixelFormat": "1bpp black/white", "composite": "black ink union on white"},
        "preferredAnchorZone": {"x": [0, 199], "y": [25, 64], "reservedStatusY": [0, 15], "reservedFaceY": [72, 143]},
        "separationContract": {
            "functional": "driven only by measured/accepted product state; never selects or mutates emotion",
            "emotion": "driven only by pet expression choreography; never claims recording, save, sync, update or charging state",
        },
        "components": components,
        "events": event_rows,
        "eventToOrnamentMapping": event_mapping,
        "missingCurrentRegistry": historical_missing(),
        "outputs": {"contactSheet": event_rel(contact), "contactSheetSha256": sha256(contact)},
        "nonClaims": [
            "no generation-21 resource claim",
            "no runtime activation or firmware binding",
            "no new or redrawn ornament pixels",
            "no physical panel acceptance",
            "historical heart/star/moon are not current V45 assets",
        ],
    }
    manifest_path = OUT / "event-art.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Final self-checks cover byte identity, semantic separation and output geometry.
    if any((OUT / row["outputPbm"]).read_bytes() != (ROOT / row["sourcePbm"]).read_bytes() for row in components):
        raise ValueError("exported PBM bytes differ from their registered source")
    if any(row["kind"] not in ("functional", "emotion") for row in components):
        raise ValueError("unclassified event component")
    stage_paths = [OUT / stage["outputLayerPng"] for event in event_rows for stage in event["stages"]]
    if any(Image.open(path).size != (200, 200) or Image.open(path).mode != "1" for path in stage_paths):
        raise ValueError("stage layer geometry mismatch")
    if any(row["suggestedAnchor"][1] <= 15 or row["suggestedBottom"] >= 72 for row in components):
        raise ValueError("suggested event anchor overlaps reserved status or face rows")
    print(f"PASS_EVENT_ART_EXPORT: {len(components)} registered components, {len(event_rows)} events; runtime inactive")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
