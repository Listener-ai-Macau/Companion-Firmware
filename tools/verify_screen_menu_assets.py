#!/usr/bin/env python3
"""Verify single-language menu packs remain external-first and gesture-ready."""

from __future__ import annotations

import json
import pathlib
import re
import struct
import sys
import zlib

from PIL import Image

import build_emote_asset_pack


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
ASSET_DIR = ROOT / "docs/validation/epaper"
BILINGUAL_MENU_EVIDENCE = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
TOUCH_WB55_EVIDENCE = ROOT / "docs/validation/companion-screen-touch-ft6336-wb55.json"
STYLE_SNAPSHOT = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
STYLE_SNAPSHOT_MD = ROOT / "docs/validation/companion-screen-generated-art-style-contract.snapshot.md"
GENERATED_IMPORT_REPORT = ROOT / "docs/validation/companion-screen-generated-expression-sheet-import.json"
CEMP_BUILD_ARTIFACT = (
    ROOT /
    "cubeide/Companion_Nucleo_WB55RG_Bringup/build_screen_asset_provision/generated/"
    "emote_matrix_white_200x200.cemp"
)
HOME_PET_PANEL_HEIGHT = 48
HOME_ITEM_STEP = 34
DETAIL_BADGE_TOP_Y = {
    "record": 39,
    "status": 39,
    "phone": 45,
    "device": 43,
    "preferences": 35,
    "about": 45,
}


def has_black(image: Image.Image, box: tuple[int, int, int, int]) -> bool:
    return any(pixel == 0 for pixel in image.crop(box).getdata())


def read_cemp_metadata(path: pathlib.Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 80 or data[:4] != b"CEMP":
        raise ValueError(f"{path.relative_to(ROOT)} is not a CEMP v1 pack")
    total, revision, _priority, _reserved = struct.unpack_from("<IIHH", data, 8)
    _width, _height, _stride, _pixel, _encoding, clips, frames = struct.unpack_from(
        "<HHHBBHH", data, 20
    )
    _clip_offset, _frame_offset, _string_offset, _string_length, _payload_offset, payload_bytes, _payload_crc, _index_crc = struct.unpack_from(
        "<IIIIIIII", data, 32
    )
    return {
        "revision": revision,
        "clips": clips,
        "frames": frames,
        "payload_bytes": payload_bytes,
        "total_bytes": total,
        "pack_crc32": f"0x{zlib.crc32(data):08X}",
        "file_bytes": len(data),
    }


def metadata_from_pack_builder() -> dict[str, object]:
    pack, metadata = build_emote_asset_pack.build_pack(MANIFEST)
    return {
        "revision": metadata["revision"],
        "clips": metadata["clip_count"],
        "frames": metadata["frame_count"],
        "payload_bytes": metadata["payload_bytes"],
        "total_bytes": metadata["total_bytes"],
        "pack_crc32": f"0x{metadata['pack_crc32']:08X}",
        "file_bytes": len(pack),
    }


def generated_import_outputs() -> set[str]:
    report = json.loads(GENERATED_IMPORT_REPORT.read_text(encoding="utf-8"))
    outputs: set[str] = set()
    for item in report.get("outputs", []):
        for path in item.get("files", []):
            outputs.add(pathlib.Path(path).name)
    return outputs


def manifest_expression_sources(manifest: dict[str, object]) -> set[str]:
    sources: set[str] = set()
    for clip in manifest.get("clips", []):
        for frame in clip.get("frames", []):
            source = pathlib.Path(str(frame.get("source", ""))).name
            if source.startswith("expression_") and source.endswith(".pbm"):
                sources.add(source)
    return sources


def compare_pack_metadata(
    errors: list[str],
    label: str,
    recorded_pack: dict[str, object],
    actual_pack: dict[str, object],
) -> None:
    for key in ("revision", "clips", "frames", "payload_bytes", "total_bytes", "pack_crc32"):
        if recorded_pack.get(key) != actual_pack[key]:
            errors.append(
                f"resource_pack.{key}={recorded_pack.get(key)!r} does not match "
                f"{label} {actual_pack[key]!r}"
            )
    if actual_pack["file_bytes"] != actual_pack["total_bytes"]:
        errors.append(f"{label} total_bytes does not match the pack length")


def check_generated_import_covers_manifest(errors: list[str], manifest: dict[str, object]) -> None:
    generated = generated_import_outputs()
    used = manifest_expression_sources(manifest)
    missing = sorted(used - generated)
    if missing:
        errors.append(
            "normal CEMP expression sources must all come from generated-sheet import; "
            f"missing from import report: {missing}"
        )
    if len(generated) < len(used):
        errors.append("generated-sheet import report has fewer expression outputs than normal CEMP uses")


def check_runtime_evidence(errors: list[str], runtime: dict[str, object]) -> None:
    status = runtime.get("status")
    pending = bool(re.fullmatch(r"REVISION_[1-9][0-9]*_RUNTIME_RECHECK_PENDING", str(status)))
    proven = bool(re.fullmatch(
        r"REVISION_[1-9][0-9]*_(?:PROVISION_AND_NORMAL_)?RUNTIME_PASS_HUMAN_VISUAL_PENDING",
        str(status),
    ))
    if not pending and not proven:
        errors.append("runtime_evidence must record a revisioned runtime pending or human-visual-pending status")
        return
    if pending:
        observation = str(runtime.get("machine_observation", ""))
        if "pending" not in observation.lower():
            errors.append("pending runtime_evidence must explain that runtime logs are pending")
        return

    log_keys = (
        "provision_capture_summary",
        "provision_raw_log",
        "normal_capture_summary",
        "normal_raw_log",
    )
    texts: list[str] = []
    for key in log_keys:
        value = runtime.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"runtime_evidence.{key} missing")
            continue
        path = ROOT / value
        if not path.exists():
            errors.append(f"runtime evidence path missing: {value}")
            continue
        if path.suffix == ".json":
            try:
                summary = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                errors.append(f"runtime summary {value} is not valid JSON: {exc}")
                continue
            if summary.get("status") != "PASS":
                errors.append(f"runtime summary {value} is not PASS")
        else:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))

    combined_logs = "\n".join(texts)
    for marker in runtime.get("required_runtime_markers", []):
        if not isinstance(marker, str) or marker not in combined_logs:
            errors.append(f"runtime marker missing from runtime logs: {marker}")


def main() -> int:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = json.loads(BILINGUAL_MENU_EVIDENCE.read_text(encoding="utf-8"))
    touch_evidence = json.loads(TOUCH_WB55_EVIDENCE.read_text(encoding="utf-8"))
    style_snapshot = json.loads(STYLE_SNAPSHOT.read_text(encoding="utf-8"))
    resource_pack = evidence.get("resource_pack", {})
    current_revision_text = f"revision {resource_pack.get('revision')}"
    current_crc = str(resource_pack.get("pack_crc32"))
    clips = {clip["name"]: clip for clip in manifest["clips"]}
    check_generated_import_covers_manifest(errors, manifest)

    for language in ("en", "zh"):
        stale_home_frames: list[str] = []
        pattern = re.compile(rf"menu_home(\d+)_{language}_1_54in\.pbm$")
        for path in ASSET_DIR.glob(f"menu_home*_{language}_1_54in.pbm"):
            match = pattern.match(path.name)
            if match is not None and int(match.group(1)) >= 43:
                stale_home_frames.append(path.name)
        if stale_home_frames:
            errors.append(
                f"{language} home menu still has stale 85-frame artifacts: "
                f"{', '.join(sorted(stale_home_frames)[:6])}"
            )
        home_name = f"menu.home.{language}"
        if home_name not in clips or len(clips[home_name]["frames"]) != 43:
            errors.append(f"manifest {home_name} must contain 43 two-pixel free-scroll frames")
        header_rasters: list[bytes] = []
        for selection in range(43):
            suffix = "" if selection == 0 else str(selection)
            path = ASSET_DIR / f"menu_home{suffix}_{language}_1_54in.pbm"
            if not path.exists():
                errors.append(f"missing {path.relative_to(ROOT)}")
                continue
            data = path.read_bytes()
            if not data.startswith(b"P4\n200 200\n") or len(data) != 5011:
                errors.append(f"invalid 200x200 P4 asset {path.name}")
                continue
            with Image.open(path) as image:
                header_rasters.append(image.crop((0, 0, 200, 38)).tobytes())
                gutter = image.crop((0, 32, 200, 38)).tobytes()
                if any(byte != 0xFF for byte in gutter):
                    errors.append(f"{path.name} must preserve the white fixed-header gutter")
        if len(header_rasters) == 43 and len(set(header_rasters)) != 1:
            errors.append(f"{language} home menu must keep its 38px fixed header across scrolling frames")
        for view in ("record", "status", "phone", "device", "preferences", "about"):
            name = f"menu.{view}.{language}"
            path = ASSET_DIR / f"menu_{view}_{language}_1_54in.pbm"
            if name not in clips:
                errors.append(f"manifest missing {name}")
            if not path.exists():
                errors.append(f"missing {path.relative_to(ROOT)}")
                continue
            data = path.read_bytes()
            if not data.startswith(b"P4\n200 200\n") or len(data) != 5011:
                errors.append(f"invalid 200x200 P4 asset {path.name}")
            raster = data[11:]
            if not raster or all(byte == 0x00 for byte in raster) or all(byte == 0xFF for byte in raster):
                errors.append(f"blank menu asset {path.name}")
            with Image.open(path) as image:
                badge_top = DETAIL_BADGE_TOP_Y[view]
                outline_guard = (82, badge_top, 120, badge_top + 12)
                inner_face_zone = (82, badge_top + 13, 120, badge_top + 36)
                if has_black(image, outline_guard):
                    errors.append(
                        f"{path.name} draws cat-outline pixels in the shell-owned badge guard zone"
                    )
                if not has_black(image, inner_face_zone):
                    errors.append(
                        f"{path.name} lost its inner-face mood mark"
                    )

        icon_rasters: list[bytes] = []
        for item in range(6):
            frame = min(42, round(item * HOME_ITEM_STEP / 2))
            offset = min(frame * 2, 84)
            suffix = "" if frame == 0 else str(frame)
            path = ASSET_DIR / f"menu_home{suffix}_{language}_1_54in.pbm"
            if not path.exists():
                continue
            icon_y = 38 + HOME_PET_PANEL_HEIGHT + item * HOME_ITEM_STEP - offset + 5
            with Image.open(path) as image:
                icon_rasters.append(image.crop((17, icon_y, 48, icon_y + 31)).tobytes())
        if len(icon_rasters) == 6 and len(set(icon_rasters)) != 6:
            errors.append(f"{language} home menu must use six distinct icons")

    menu_header = (ROOT / "app/companion_pendant/epaper/screen_menu.h").read_text(encoding="utf-8")
    menu_source = (ROOT / "app/companion_pendant/epaper/screen_menu.c").read_text(encoding="utf-8")
    panel = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c").read_text(encoding="utf-8")
    app = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8")
    main_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    makefile = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile").read_text(encoding="utf-8")
    flash_script = (ROOT / "tools/flash_nucleo_bringup.ps1").read_text(encoding="utf-8")
    plan = (ROOT / "docs/companion_screen_project_plan.md").read_text(encoding="utf-8")
    readme = (ROOT / "app/companion_pendant/epaper/README.md").read_text(encoding="utf-8")
    bringup_readme = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/README.md").read_text(encoding="utf-8")
    memory_policy = (ROOT / "docs/companion_resource_memory_policy.md").read_text(encoding="utf-8")
    expression_doc = (ROOT / "docs/companion_screen_expression_system.md").read_text(encoding="utf-8")
    style_snapshot_md = STYLE_SNAPSHOT_MD.read_text(encoding="utf-8")
    if manifest.get("revision", 0) < 32:
        errors.append("manifest must be at least revision 32 for the product menu")
    recorded_pack = evidence.get("resource_pack", {})
    runtime_evidence = evidence.get("runtime_evidence", {})
    if isinstance(runtime_evidence, dict):
        check_runtime_evidence(errors, runtime_evidence)
    else:
        errors.append("runtime_evidence must be an object")
    try:
        compare_pack_metadata(errors, "generated CEMP", recorded_pack, metadata_from_pack_builder())
    except Exception as exc:
        errors.append(f"failed to build CEMP metadata from manifest: {exc}")
    if CEMP_BUILD_ARTIFACT.exists():
        try:
            cemp = read_cemp_metadata(CEMP_BUILD_ARTIFACT)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            compare_pack_metadata(errors, "built CEMP artifact", recorded_pack, cemp)
    required = {
        "menu_generator": (
            (ROOT / "tools/generate_screen_menu_assets.py").read_text(encoding="utf-8"),
            "MENU_STYLE",
            "genref_sheet_12_inner_faces_v5",
            '"inner_face_only": True',
            '"detail_badge_x": 84',
            "header_pet_chip",
            'MENU_STYLE["home_card"]',
            'MENU_STYLE["home_key_spark"]',
            'MENU_STYLE["detail_badge_x"]',
            "Only inner face marks are drawn",
        ),
        "screen_menu.h": (
            menu_header,
            "COMP_SCREEN_MENU_LANGUAGE_ZH",
            "COMP_SCREEN_MENU_VIEW_ABOUT",
            "COMP_SCREEN_MENU_VIEW_PHONE",
            "COMP_SCREEN_MENU_VIEW_PREFERENCES",
            "comp_screen_menu_gesture",
            "COMP_SCREEN_MENU_SCROLL_QUANTUM_PX 2u",
            "COMP_SCREEN_MENU_SCROLL_MAX_PX 84u",
            "COMP_SCREEN_MENU_HOME_CONTENT_TOP_PX 38u",
        ),
        "screen_menu.c": (
            menu_source,
            '"menu.%s.%s"',
            "COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED",
            "COMP_TOUCH_GESTURE_SWIPE_RIGHT",
            "COMP_SCREEN_MENU_BACK_EDGE_MAX_X",
            "comp_screen_menu_drag",
            "comp_screen_menu_drag_to",
            "COMP_SCREEN_MENU_SCROLL_QUANTUM_PX",
            "MENU_HOME_CONTENT_TOP",
            "COMP_SCREEN_MENU_SCROLL_FRAME_COUNT",
            "framebuffer_fingerprint",
            "COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE",
            "COMP_TOUCH_GESTURE_LONG_PRESS",
            "COMP_TOUCH_GESTURE_SWIPE_UP",
            "COMP_TOUCH_GESTURE_SWIPE_DOWN",
            '"phone", "device",',
            '"preferences", "about",',
            "draw_header_pet_chip",
            "draw_corner_spark",
            "physical shell owns the cat outline",
            "three-second hold anywhere",
        ),
        "panel": (panel, "comp_epaper_expression_asset_source_copy_clip", "source=external_flash"),
        "app": (
            app,
            "COMPANION_SCREEN_ASSET_CLIP_CAPACITY 48u",
            "COMPANION_SCREEN_ASSET_FRAME_CAPACITY 256u",
            "COMPANION_SCREEN_ASSET_STRING_CAPACITY 1024u",
            "Companion_Screen_ShowDaily",
            "Companion_Screen_DailyTap",
            "Companion_Screen_DailyTapAt",
            "pet_attention_selftest",
            "core_selftest menu=%s gesture=%s",
        ),
        "main": (
            main_source,
            "menu_drag anchor_y=",
            "s_menu_vertical_drag_anchor_y",
            "comp_screen_menu_drag_to",
            "comp_touch_gesture_is_vertical_drag",
            "daily_hold_tease",
            "any_long_press",
        ),
        "makefile": (makefile, "menu_*_1_54in.pbm",),
        "flash_script": (
            flash_script,
            "[switch]$ScreenAssetProvision",
            "[switch]$CheckOnly",
            "Companion_Nucleo_WB55RG_ScreenAssetProvision.hex",
            "Use either -ScreenAssetProvision or -ImagePath, not both.",
        ),
        "build_evidence": (
            json.dumps(evidence.get("build_evidence", {}), ensure_ascii=False),
            "tools/flash_nucleo_bringup.ps1 -ScreenAssetProvision -CheckOnly",
            "tools/flash_nucleo_bringup.ps1 -ScreenAssetProvision",
            "tools/flash_nucleo_bringup.ps1 -CheckOnly",
            "tools/flash_nucleo_bringup.ps1",
        ),
        "bringup_readme": (
            bringup_readme,
            "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -ScreenAssetProvision -CheckOnly",
            "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -ScreenAssetProvision",
            "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -CheckOnly",
        ),
        "memory_policy": (
            memory_policy,
            "tools/flash_nucleo_bringup.ps1 -ScreenAssetProvision",
            "Companion_Nucleo_WB55RG_ScreenAssetProvision.hex",
            "Companion_Nucleo_WB55RG_Bringup.hex",
        ),
        "project_plan": (
            plan,
            current_revision_text,
            "录音、状态、手机、设备、偏好、关于",
            "650 ms",
            "3 s",
            "任意位置近似静止长按",
            "43 张 2 px",
        ),
        "epaper_readme": (
            readme,
            current_revision_text,
            "159 timeline frames",
            "43 external",
            "six product",
            "3 s hold",
            "physical shell owns the",
            f"CRC32 `{current_crc}`",
        ),
        "expression_system": (
            expression_doc + "\n" + json.dumps(style_snapshot, ensure_ascii=False) + "\n" + style_snapshot_md,
            current_revision_text,
            "650 ms pet tease",
            "3 s long press",
            "43 external two-pixel",
            "press-cue partial refresh",
            "target-arrival partial refresh",
            "genref_sheet_12_inner_faces_v5",
            "pet_visual_style.h",
            "MENU_STYLE",
            "companion.screen.generated_art_style_contract.v1",
            "style_names_match",
            "quick_adjustment_workflow_recorded",
        ),
    }
    for label, values in required.items():
        content, *tokens = values
        for token in tokens:
            if token not in content:
                errors.append(f"{label} missing {token}")

    stale_rules = (
        ("project_plan", plan, "主页目录依次为\r\n记录、状态、表情、设置、同步、存储、设备、关于"),
        ("project_plan", plan, "只有从右侧边缘开始的左划进入目录"),
        ("project_plan", plan, "保留“右侧边缘向左”进入菜单"),
        ("project_plan", plan, "只有屏幕中央近似静止长按才进入目录"),
        ("project_plan", plan, "偏离中央或明显移动不得进入菜单"),
        ("project_plan", plan, "中央长按入口"),
        ("project_plan", plan, "屏幕中央近似\r\n静止 3 s 长按"),
        ("project_plan", plan, "屏幕中央近似\n静止 3 s 长按"),
        ("touch_fixture", json.dumps(touch_evidence, ensure_ascii=False), "right-edge swipe_left enters the settings drawer"),
        ("touch_fixture", json.dumps(touch_evidence, ensure_ascii=False), "only the completed centered long press can preempt a pet interaction"),
        ("touch_fixture", json.dumps(touch_evidence, ensure_ascii=False), "centered_menu_long_press_ms"),
        ("project_plan", plan, "主菜单八项分别使用"),
        ("project_plan", plan, "每种语言 85 external"),
        ("epaper_readme", readme, "85 external two-pixel"),
        ("epaper_readme", readme, "eight first-level menu items"),
        ("epaper_readme", readme, "revision 22 pack expands"),
        ("expression_system", expression_doc, "A swipe left on the daily face enters the menu"),
        ("expression_system", expression_doc, "from 0 through 167"),
        ("menu_generator", required["menu_generator"][0], "small face gives each practical page"),
        ("screen_menu.c", menu_source, "x + 8, y + 2, x + 15, y + 9"),
        ("screen_menu.c", menu_source, "x + 31, y + 2"),
    )
    for label, content, token in stale_rules:
        if token in content:
            errors.append(f"{label} still contains stale menu rule: {token}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: product-focused Companion menu assets provide 43 external two-pixel positions per language.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
