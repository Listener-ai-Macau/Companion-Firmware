#!/usr/bin/env python3
"""Render a machine-readable generated-art style contract snapshot."""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
STYLE_HEADER = ROOT / "app/companion_pendant/epaper/pet_visual_style.h"
MENU_GENERATOR = ROOT / "tools/generate_screen_menu_assets.py"
SHEET_IMPORTER = ROOT / "tools/import_generated_expression_sheet.py"
NORMAL_PACK_CONTACT_SHEET = ROOT / "tools/render_generated_expression_normal_pack_contact_sheet.py"
SHEET_SOURCE = ROOT / "docs/art/generated_pet_expression_sheet_v5.png"
SHEET_IMPORT_REPORT = ROOT / "docs/validation/companion-screen-generated-expression-sheet-import.json"
NORMAL_PACK_CONTACT_REPORT = ROOT / "docs/validation/companion-screen-generated-expression-normal-pack-contact-sheet.json"
STYLE_DOC = ROOT / "docs/validation/companion-screen-generated-art-style-contract.md"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-generated-art-style-contract.snapshot.md"


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def parse_macros(text: str) -> dict[str, int | str]:
    macros: dict[str, int | str] = {}
    for match in re.finditer(r"^#define\s+(COMP_PET_STYLE_[A-Z0-9_]+)\s+(.+)$", text, re.MULTILINE):
        name, raw_value = match.groups()
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            macros[name] = value.strip('"')
            continue
        try:
            macros[name] = int(value, 0)
        except ValueError:
            macros[name] = value
    return macros


def parse_menu_style(text: str) -> dict[str, object]:
    tree = ast.parse(text, filename=rel(MENU_GENERATOR))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MENU_STYLE":
                    value = ast.literal_eval(node.value)
                    if not isinstance(value, dict):
                        raise ValueError("MENU_STYLE must be a dict literal")
                    return value
    raise ValueError("MENU_STYLE was not found")


def build_snapshot() -> dict[str, object]:
    style_text = STYLE_HEADER.read_text(encoding="utf-8")
    menu_text = MENU_GENERATOR.read_text(encoding="utf-8")
    importer_text = SHEET_IMPORTER.read_text(encoding="utf-8")
    contact_sheet_text = NORMAL_PACK_CONTACT_SHEET.read_text(encoding="utf-8")
    doc_text = STYLE_DOC.read_text(encoding="utf-8")
    import_report = json.loads(SHEET_IMPORT_REPORT.read_text(encoding="utf-8"))
    contact_report = json.loads(NORMAL_PACK_CONTACT_REPORT.read_text(encoding="utf-8"))
    pet_style = parse_macros(style_text)
    menu_style = parse_menu_style(menu_text)
    style_name = pet_style.get("COMP_PET_STYLE_NAME")

    references = []
    for line in doc_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("`C:\\") and stripped.endswith("`"):
            references.append(stripped.strip("`"))

    return {
        "schema_id": "companion.screen.generated_art_style_contract.v1",
        "status": "PASS",
        "style_name": style_name,
        "style_sources": {
            "pet_style_header": rel(STYLE_HEADER),
            "menu_generator": rel(MENU_GENERATOR),
            "sheet_importer": rel(SHEET_IMPORTER),
            "normal_pack_contact_sheet_tool": rel(NORMAL_PACK_CONTACT_SHEET),
            "checked_in_expression_sheet": rel(SHEET_SOURCE),
            "sheet_import_report": rel(SHEET_IMPORT_REPORT),
            "normal_pack_contact_report": rel(NORMAL_PACK_CONTACT_REPORT),
            "human_contract": rel(STYLE_DOC),
        },
        "reference_images": references,
        "pet_visual_style": pet_style,
        "menu_style": menu_style,
        "acceptance": {
            "style_names_match": style_name == menu_style.get("name"),
            "inner_face_only": menu_style.get("inner_face_only") is True,
            "shell_owns_outline": "physical shell owns the cat outline" in doc_text,
            "large_assets_external": "external flash" in doc_text and "CEMP" in doc_text,
            "generated_reference_is_source_of_truth": (
                "Generated-image baseline is the source of truth for normal product art"
                in doc_text
            ),
            "human_accepted_generated_baseline_protected": (
                "Human accepted physical-art baseline:" in doc_text
                and "must not change pose semantics or restore legacy procedural faces" in doc_text
            ),
            "legacy_procedural_not_normal_product": (
                "allowed only as rescue/maintenance fallback" in doc_text
                and "must not replace the external CEMP expression/menu path" in doc_text
            ),
            "normal_pack_no_old_new_handoff": (
                "must not show a mixed old/new handoff" in doc_text
                and "Every\n`expression_*.pbm` referenced by the normal CEMP manifest" in doc_text
                and "older procedural expression PBMs fails validation" in doc_text
            ),
            "screen_feel_policy_recorded": (
                "Screen feel policy" in doc_text
                and "partial/differential refresh" in doc_text
                and "one quiet maintenance\n  pass" in doc_text
            ),
            "quick_adjustment_workflow_recorded": "Adjustment workflow" in doc_text,
            "fast_prompt_to_screen_workflow_recorded": (
                "Fast prompt-to-screen rule:" in doc_text
                and "incremented external CEMP revision" in doc_text
                and "Do not manually redraw a generated pose" in doc_text
            ),
            "profile_portability_workflow_recorded": (
                "Panel migration rule:" in doc_text
                and "200x200` / `1_54in` are the current WB55 default profile" in doc_text
                and "verify_generated_expression_sheet_profile_portability.py" in doc_text
                and "--profile" in importer_text
                and "--asset-suffix" in importer_text
            ),
            "generated_sheet_importer_recorded": (
                "import_generated_expression_sheet.py" in doc_text
                and "generated_pet_expression_sheet_v5.png" in doc_text
                and "THRESHOLD" in importer_text
                and import_report.get("status") == "PASS"
                and import_report.get("style_source_of_truth") == "generated_pet_expression_sheet_v5"
            ),
            "generated_sheet_visual_review_recorded": (
                import_report.get("visual_review_required") is True
                and bool(import_report.get("review_preview"))
                and "REF" in importer_text
                and "PBM" in importer_text
            ),
            "normal_pack_contact_sheet_recorded": (
                "render_generated_expression_normal_pack_contact_sheet.py" in doc_text
                and "normal-pack contact sheet" in doc_text
                and "generated expression normal-pack contact sheet" in contact_sheet_text
                and contact_report.get("status") == "PASS"
                and contact_report.get("generated_coverage", {}).get("used_by_manifest") == 39
                and contact_report.get("generated_coverage", {}).get("covered_by_import") == 39
            ),
            "generated_sheet_machine_review_pass": (
                import_report.get("machine_review_required") is True
                and import_report.get("machine_review", {}).get("status") == "PASS"
                and bool(import_report.get("machine_review", {}).get("pose_metrics"))
                and "label_guard_band_y" in importer_text
                and "MIN_EDGE_MARGIN" in importer_text
            ),
            "inner_face_clipping_prohibited": (
                "Inner-face clipping rule:" in doc_text
                and "must not paint a white shell guard inside the" in doc_text
                and "MIN_EDGE_MARGIN = 0" in importer_text
                and "SHELL_GUARD" not in importer_text
                and "def crop_pose(source: Image.Image, pose: Pose, profile: CanvasProfile)" in importer_text
                and "return crop_pose_reference(source, pose, profile).point" in importer_text
                and import_report.get("machine_review_thresholds", {}).get("internal_shell_mask_disabled") is True
                and import_report.get("machine_review_thresholds", {}).get("fixed_art_margin_px") == 0
            ),
        },
    }


def render_markdown(snapshot: dict[str, object]) -> str:
    pet_style = snapshot["pet_visual_style"]
    menu_style = snapshot["menu_style"]
    acceptance = snapshot["acceptance"]
    lines = [
        "# Companion Generated Art Style Snapshot",
        "",
        "This file is generated. Update it with",
        "`python .\\tools\\render_generated_art_style_contract.py --write`.",
        "",
        f"- Style: `{snapshot['style_name']}`",
        f"- Pet style source: `{snapshot['style_sources']['pet_style_header']}`",
        f"- Menu style source: `{snapshot['style_sources']['menu_generator']}`",
        f"- Sheet importer: `{snapshot['style_sources']['sheet_importer']}`",
        f"- Checked-in expression sheet: `{snapshot['style_sources']['checked_in_expression_sheet']}`",
        f"- Human contract: `{snapshot['style_sources']['human_contract']}`",
        "",
        "## Key Pet Anchors",
        "",
        "| Parameter | Value |",
        "|---|---:|",
    ]
    for key in (
        "COMP_PET_STYLE_EYE_CENTER_Y",
        "COMP_PET_STYLE_EYE_HALF_SPACING",
        "COMP_PET_STYLE_EYE_BASE_RX",
        "COMP_PET_STYLE_EYE_BASE_RY",
        "COMP_PET_STYLE_NOSE_Y",
        "COMP_PET_STYLE_MOUTH_CENTER_Y",
        "COMP_PET_STYLE_CHEEK_DOT_Y",
    ):
        lines.append(f"| `{key}` | `{pet_style[key]}` |")
    lines.extend([
        "",
        "## Menu Anchors",
        "",
        "| Parameter | Value |",
        "|---|---|",
    ])
    for key in ("header_pet_chip", "home_card", "home_key_spark", "detail_badge_x", "inner_face_only"):
        lines.append(f"| `{key}` | `{menu_style[key]}` |")
    lines.extend([
        "",
        "## Acceptance",
        "",
        "| Check | Result |",
        "|---|---|",
    ])
    for key, value in acceptance.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    return "\n".join(lines)


def verify(snapshot: dict[str, object]) -> list[str]:
    errors: list[str] = []
    acceptance = snapshot.get("acceptance", {})
    for key, value in acceptance.items():
        if value is not True:
            errors.append(f"acceptance.{key} is not true")
    if snapshot.get("style_name") != "genref_sheet_12_inner_faces_v5":
        errors.append("style name drifted from genref_sheet_12_inner_faces_v5")
    if not snapshot.get("reference_images"):
        errors.append("reference image paths are missing")
    pet_style = snapshot.get("pet_visual_style", {})
    for key in (
        "COMP_PET_STYLE_EYE_CENTER_Y",
        "COMP_PET_STYLE_MOUTH_CENTER_Y",
        "COMP_PET_STYLE_CHEEK_DOT_LEFT_X",
    ):
        if key not in pet_style:
            errors.append(f"missing pet style parameter {key}")
    menu_style = snapshot.get("menu_style", {})
    for key in ("header_pet_chip", "home_card", "detail_badge_x"):
        if key not in menu_style:
            errors.append(f"missing menu style parameter {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write JSON and markdown snapshots.")
    args = parser.parse_args()

    snapshot = build_snapshot()
    errors = verify(snapshot)
    rendered_json = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    rendered_md = render_markdown(snapshot)

    if args.write:
        DEFAULT_JSON.write_text(rendered_json, encoding="utf-8")
        DEFAULT_MD.write_text(rendered_md, encoding="utf-8")
    else:
        if not DEFAULT_JSON.exists():
            errors.append(f"missing {rel(DEFAULT_JSON)}")
        elif DEFAULT_JSON.read_text(encoding="utf-8") != rendered_json:
            errors.append(f"stale {rel(DEFAULT_JSON)}")
        if not DEFAULT_MD.exists():
            errors.append(f"missing {rel(DEFAULT_MD)}")
        elif DEFAULT_MD.read_text(encoding="utf-8") != rendered_md:
            errors.append(f"stale {rel(DEFAULT_MD)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: generated-art style contract verified -> {rel(DEFAULT_JSON)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
