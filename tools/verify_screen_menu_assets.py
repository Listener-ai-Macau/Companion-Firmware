#!/usr/bin/env python3
"""Guard the owner-accepted menu-v3 external-Flash resource path."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import pathlib
import struct
import sys
import zlib

from PIL import Image

import build_emote_asset_pack


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
ASSET_DIR = ROOT / "docs/validation/epaper"
MENU_IMPORT = ROOT / "docs/validation/companion-screen-menu-v3-import.json"
MENU_LEDGER = ROOT / "docs/art/iterations/companion-menu-v2/iteration-ledger.json"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
STYLE_SNAPSHOT = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
EVIDENCE = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
CEMP_BUILD_ARTIFACT = (
    ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_screen_asset_provision/generated/"
    "emote_matrix_white_200x200.cemp"
)
MENU_GENERATOR = ROOT / "tools/generate_screen_menu_assets.py"
MENU_VIEWS = ("home", "record", "status", "phone", "device", "preferences", "about")


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_generator():
    spec = importlib.util.spec_from_file_location("companion_menu_v3_import", MENU_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load menu-v3 resource generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata_from_bytes(data: bytes) -> dict[str, object]:
    if len(data) < 80 or data[:4] != b"CEMP":
        raise ValueError("not a CEMP v1 pack")
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


def metadata_from_builder() -> dict[str, object]:
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


def compare_metadata(errors: list[str], label: str,
                     expected: dict[str, object], actual: dict[str, object]) -> None:
    for key in ("revision", "clips", "frames", "payload_bytes", "total_bytes", "pack_crc32"):
        if expected.get(key) != actual.get(key):
            errors.append(f"{label}.{key}={actual.get(key)!r} != {expected.get(key)!r}")
    if actual["file_bytes"] != actual["total_bytes"]:
        errors.append(f"{label} file length differs from its CEMP total_bytes")


def expected_menu_sources() -> set[str]:
    return {f"menu_{view}_{language}_1_54in.pbm"
            for language in ("en", "zh") for view in MENU_VIEWS}


def check_menu_import(errors: list[str], manifest: dict[str, object]) -> None:
    generator = load_generator()
    report = json.loads(MENU_IMPORT.read_text(encoding="utf-8"))
    if report.get("schema_id") != "companion.screen.menu_v3_import.v1":
        errors.append("menu import report has the wrong schema")
    if report.get("status") != "PASS_STATIC_IMPORT_PENDING_HARDWARE":
        errors.append("menu import report must remain a static-import pending-hardware result")
    if report.get("source") != "docs/art/generated_companion_menu_reference_v3.png":
        errors.append("menu import report source drifted")
    if report.get("source_sha256") != generator.SOURCE_SHA256:
        errors.append("menu import report source SHA-256 drifted")
    if report.get("crop_boxes") != {name: list(box) for name, box in generator.SCREEN_CROPS.items()}:
        errors.append("menu import report crop map drifted")
    if report.get("asset_revision") != manifest.get("revision"):
        errors.append("menu import report revision does not match CEMP manifest")
    outputs = report.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != len(expected_menu_sources()):
        errors.append("menu import report must record exactly fourteen bilingual outputs")

    source = None
    if generator.SOURCE.exists():
        try:
            with Image.open(generator.SOURCE) as opened:
                source = opened.convert("L")
        except Exception as exc:
            errors.append(f"could not open accepted menu source: {exc}")
    if source is not None and source.size != generator.SOURCE_SIZE:
        errors.append("accepted menu source dimensions drifted")
    pinned_outputs = {
        pathlib.Path(str(item.get("path", ""))).name: item.get("sha256")
        for item in report.get("outputs", [])
        if isinstance(item, dict)
    }

    output_paths = set()
    for language in ("en", "zh"):
        for view in MENU_VIEWS:
            name = f"menu_{view}_{language}_1_54in.pbm"
            path = ASSET_DIR / name
            output_paths.add(name)
            if not path.exists():
                errors.append(f"missing menu-v3 resource {rel(path)}")
                continue
            data = path.read_bytes()
            if not data.startswith(b"P4\n200 200\n") or len(data) != 5011:
                errors.append(f"invalid 200x200 P4 resource {name}")
                continue
            if source is not None:
                try:
                    actual = Image.open(path).convert("1")
                    expected = generator.make_view(source, view, language, manifest["revision"])
                except Exception as exc:
                    errors.append(f"could not reproduce {name}: {exc}")
                    continue
                if actual.tobytes() != expected.tobytes():
                    errors.append(f"{name} is not the deterministic menu-v3 import output")
            elif hashlib.sha256(data).hexdigest().upper() != pinned_outputs.get(name):
                errors.append(f"{name} differs from the accepted import receipt SHA-256")
    if output_paths != expected_menu_sources():
        errors.append("internal expected menu source set is incomplete")
    for view in MENU_VIEWS:
        en = Image.open(ASSET_DIR / f"menu_{view}_en_1_54in.pbm").convert("1")
        zh = Image.open(ASSET_DIR / f"menu_{view}_zh_1_54in.pbm").convert("1")
        if en.tobytes() == zh.tobytes():
            errors.append(f"{view} must retain separate Chinese and English resources")

    clips = {clip["name"]: clip for clip in manifest.get("clips", [])}
    for language in ("en", "zh"):
        for view in MENU_VIEWS:
            name = f"menu.{view}.{language}"
            clip = clips.get(name)
            expected_source = "../../../../docs/validation/epaper/" + f"menu_{view}_{language}_1_54in.pbm"
            if clip is None:
                errors.append(f"manifest missing {name}")
                continue
            if clip.get("loop_start") != 0 or clip.get("loop_end") != 1 or len(clip.get("frames", [])) != 1:
                errors.append(f"manifest {name} must be one static menu-v3 frame")
            elif clip["frames"][0].get("source") != expected_source:
                errors.append(f"manifest {name} points away from its menu-v3 PBM")
    for clip in manifest.get("clips", []):
        if str(clip.get("name", "")).startswith("menu.home") and len(clip.get("frames", [])) != 1:
            errors.append("legacy multi-frame home scrolling remains in the normal CEMP manifest")
        for frame in clip.get("frames", []):
            if "menu_home" in str(frame.get("source", "")) and "menu_home_" not in str(frame.get("source", "")):
                errors.append("legacy numbered menu home frame remains referenced")


def check_source_contract(errors: list[str]) -> None:
    # The bulky iteration gallery was intentionally removed during workspace
    # cleanup. When it is present, still validate it; the durable acceptance
    # identity is the requirement-registry tuple checked below (requirement,
    # iteration id and accepted source SHA-256).
    if MENU_LEDGER.exists():
        ledger = json.loads(MENU_LEDGER.read_text(encoding="utf-8"))
        candidate = next((item for item in ledger.get("iterations", [])
                          if item.get("iteration_id") == "menu-v3-2026-07-13"), None)
        if candidate is None or candidate.get("review", {}).get("outcome") != "accepted_owner_2026-07-13":
            errors.append("menu-v3 ledger acceptance is missing")
        elif candidate.get("implementation", {}).get("status") != "external_flash_resources_generated_build_pass_hardware_pending":
            errors.append("menu-v3 ledger implementation status drifted")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    for token in ("COMP-REQ-015", "menu-v3-2026-07-13", "D87E45A49AA623552B867C9EDAADB906CA282DF2C2C062D3A127A277920F9F81"):
        if token not in requirements:
            errors.append(f"requirement registry missing {token}")
    snapshot = json.loads(STYLE_SNAPSHOT.read_text(encoding="utf-8"))
    acceptance = snapshot.get("acceptance", {})
    for key in ("style_names_match", "inner_face_only", "menu_reference_hash_pinned",
                "menu_external_flash_resource_import"):
        if acceptance.get(key) is not True:
            errors.append(f"generated-art style snapshot {key} is not true")


def check_runtime_contract(errors: list[str], built: dict[str, object]) -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    recorded = evidence.get("resource_pack", {})
    compare_metadata(errors, "evidence.resource_pack", recorded, built)
    revision = built["revision"]
    runtime = evidence.get("runtime_evidence", {})
    pending_status = f"REVISION_{revision}_RUNTIME_RECHECK_PENDING"
    promoted_status = f"REVISION_{revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING"
    status = runtime.get("status")
    observation = str(runtime.get("machine_observation", "")).lower()
    if status == pending_status:
        if "pending" not in observation:
            errors.append("pending runtime evidence must explain that the runtime recheck is pending")
    elif status == promoted_status:
        if "passed" not in observation or "pending" not in observation:
            errors.append("promoted runtime evidence must distinguish machine pass from pending human review")

        # A promoted revision remains valid only when both captured boots still
        # prove the exact markers required by the active CEMP manifest.
        captured_logs: list[str] = []
        for key in ("provision_capture_summary", "normal_capture_summary",
                    "provision_raw_log", "normal_raw_log"):
            value = runtime.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"promoted runtime evidence is missing {key}")
                continue
            path = ROOT / value
            if not path.is_file():
                errors.append(f"promoted runtime evidence path is missing: {value}")
                continue
            if path.suffix == ".json":
                try:
                    if json.loads(path.read_text(encoding="utf-8-sig")).get("status") != "PASS":
                        errors.append(f"promoted runtime summary is not PASS: {value}")
                except Exception as exc:
                    errors.append(f"could not read promoted runtime summary {value}: {exc}")
            else:
                captured_logs.append(path.read_text(encoding="utf-8", errors="replace"))
        combined_logs = "\n".join(captured_logs)
        for marker in runtime.get("required_runtime_markers", []):
            if not isinstance(marker, str) or marker not in combined_logs:
                errors.append(f"promoted runtime logs are missing marker: {marker}")
    else:
        errors.append(
            "runtime evidence must be this revision's recheck-pending or "
            "machine-pass/human-visual-pending status"
        )
    menu_contract = evidence.get("menu_contract", {})
    if menu_contract.get("external_menu_frames") != 14:
        errors.append("menu contract must record fourteen normal external menu frames")
    gesture = menu_contract.get("gesture_contract", {})
    if gesture.get("home_rendering") != "one owner-approved static external home frame per language":
        errors.append("menu contract must record the one-frame menu-v3 home policy")
    if gesture.get("home_scroll") != "retired by the six-row menu-v3 home reference":
        errors.append("menu contract must record that legacy home scrolling is retired")


def main() -> int:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check_menu_import(errors, manifest)
    check_source_contract(errors)
    try:
        built = metadata_from_builder()
    except Exception as exc:
        errors.append(f"could not build current CEMP: {exc}")
        built = None
    if built is not None:
        check_runtime_contract(errors, built)
        if CEMP_BUILD_ARTIFACT.exists():
            try:
                compare_metadata(errors, "built CEMP artifact", built,
                                 metadata_from_bytes(CEMP_BUILD_ARTIFACT.read_bytes()))
            except Exception as exc:
                errors.append(f"could not read built CEMP artifact: {exc}")
    source = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c").read_text(encoding="utf-8")
    header = (ROOT / "app/companion_pendant/epaper/screen_menu.h").read_text(encoding="utf-8")
    menu = (ROOT / "app/companion_pendant/epaper/screen_menu.c").read_text(encoding="utf-8")
    for token in ("source=external_flash", "menu_asset_name", "0u,\n                   s_frame"):
        if token not in source:
            errors.append(f"panel target missing menu-v3 external resource anchor {token!r}")
    for token in ("COMP_SCREEN_MENU_VISIBLE_ITEMS 6u", "COMP_SCREEN_MENU_SCROLL_FRAME_COUNT 1u"):
        if token not in header:
            errors.append(f"screen menu header missing {token}")
    for token in ("comp_screen_menu_v2_self_test", "comp_screen_menu_self_test", "MENU_HOME_CONTENT_TOP",
                  "COMP_SCREEN_MENU_SCROLL_MAX_PX", "COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE"):
        if token not in menu:
            errors.append(f"screen menu source missing migration guard {token}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: menu-v3 assets are deterministic owner-approved external-Flash resources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
