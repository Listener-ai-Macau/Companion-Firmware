#!/usr/bin/env python3
"""Render a one-by-one Companion screen feature acceptance checklist."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = pathlib.Path("docs/validation/companion-screen-feature-checklist.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-feature-checklist.md")
SCHEMA_ID = "companion.pendant.screen_feature_checklist.v1"

ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
FEATURE_ROADMAP = REPO_ROOT / "docs/validation/companion-screen-feature-roadmap.json"
DRIVER_READINESS = REPO_ROOT / "docs/validation/companion-screen-panel-driver-readiness.json"
TOUCH_VISUAL_PACKET = REPO_ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"
TOUCH_VISUAL_PACKET_MD = REPO_ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.md"
PRE_ACCEPTANCE_HEALTH = REPO_ROOT / "docs/validation/companion-screen-pre-acceptance-health.json"
PANEL_RECOVERY_GATE = REPO_ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def build_checklist() -> dict[str, Any]:
    index = load_json(ACCEPTANCE_INDEX)
    roadmap = load_json(FEATURE_ROADMAP)
    acceptance_by_id = {
        str(item.get("id")): item for item in index.get("items", []) if isinstance(item, dict)
    }
    capabilities = [item for item in roadmap.get("capabilities", []) if isinstance(item, dict)]
    gate_id = str(roadmap.get("current_next_gate", ""))
    current_focus = next(
        (
            item
            for item in capabilities
            if gate_id in item.get("acceptance_item_ids", [])
        ),
        next((item for item in capabilities if item.get("status") != "PASS"), capabilities[-1]),
    )
    gate = acceptance_by_id.get(gate_id, {})
    missing_fields = [str(fact) for fact in gate.get("missing_hardware_facts", [])]

    checklist: list[dict[str, Any]] = []
    for order, capability in enumerate(capabilities, start=1):
        acceptance_items = []
        for item_id in capability.get("acceptance_item_ids", []):
            acceptance = acceptance_by_id.get(str(item_id), {})
            acceptance_items.append(
                {
                    "id": str(item_id),
                    "title": acceptance.get("title"),
                    "status": acceptance.get("status", "MISSING"),
                }
            )
        checklist.append(
            {
                "order": order,
                "id": capability.get("id"),
                "title": capability.get("title"),
                "status": capability.get("status"),
                "user_value": capability.get("user_value"),
                "next_acceptance": capability.get("next_acceptance"),
                "acceptance_items": acceptance_items,
            }
        )

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "A compact one-by-one acceptance checklist derived from the screen feature roadmap.",
        "sources": {
            "acceptance_index": rel(ACCEPTANCE_INDEX),
            "feature_roadmap": rel(FEATURE_ROADMAP),
            "panel_driver_readiness": rel(DRIVER_READINESS),
            "touch_visual_acceptance_packet": rel(TOUCH_VISUAL_PACKET),
            "touch_visual_acceptance_packet_markdown": rel(TOUCH_VISUAL_PACKET_MD),
            "screen_doc": rel(SCREEN_DOC),
            "epaper_readme": rel(EPAPER_README),
            "checklist_tool": "tools/render_expression_feature_checklist.py",
        },
        "overall_status": roadmap.get("status"),
        "current_next_gate": roadmap.get("current_next_gate"),
        "current_focus": {
            "capability_id": current_focus.get("id"),
            "capability_status": current_focus.get("status"),
            "next_acceptance": current_focus.get("next_acceptance"),
            "gate_id": gate_id,
            "gate_status": gate.get("status"),
            "missing_ready_field_count": len(missing_fields),
            "operator_packet_label": "touch visual acceptance packet",
            "operator_packet": rel(TOUCH_VISUAL_PACKET),
            "pre_acceptance_health": rel(PRE_ACCEPTANCE_HEALTH),
            "panel_recovery_gate": rel(PANEL_RECOVERY_GATE),
        },
        "checklist": checklist,
        "current_missing_panel_facts": missing_fields,
        "validation_commands": [
            "python .\\tools\\render_expression_feature_checklist.py",
            "python .\\tools\\verify_expression_feature_roadmap.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\verify_expression_panel_driver_readiness.py",
        ],
    }


def build_markdown(data: dict[str, Any]) -> str:
    focus = data.get("current_focus", {})
    lines = [
        "# Companion Screen Feature Checklist",
        "",
        "This checklist is generated. Update it with `python .\\tools\\render_expression_feature_checklist.py --write`.",
        "",
        "## Current Focus",
        "",
        f"- Overall status: `{clean_md(data.get('overall_status'))}`",
        f"- Next gate: `{clean_md(data.get('current_next_gate'))}`",
        f"- Capability: `{clean_md(focus.get('capability_id'))}`",
        f"- Focused gate: `{clean_md(focus.get('gate_id'))}` (`{clean_md(focus.get('gate_status'))}`)",
        f"- Touch visual acceptance packet: `{clean_md(focus.get('operator_packet'))}`",
        f"- Pre-acceptance health: `{clean_md(focus.get('pre_acceptance_health'))}`",
        f"- Current recovery evidence: `{clean_md(focus.get('panel_recovery_gate'))}`",
        f"- Missing panel facts: `{clean_md(focus.get('missing_ready_field_count'))}`",
        f"- Next acceptance: {clean_md(focus.get('next_acceptance'))}",
        "",
        "## Capability Checklist",
        "",
        "| # | Status | Capability | Next acceptance |",
        "|---:|---|---|---|",
    ]
    for item in data.get("checklist", []):
        lines.append(
            "| "
            f"{item.get('order')} | `{clean_md(item.get('status'))}` | "
            f"`{clean_md(item.get('id'))}` | {clean_md(item.get('next_acceptance'))} |"
        )

    lines.extend(["", "## Current Missing Panel Facts", ""])
    missing = data.get("current_missing_panel_facts", [])
    if not missing:
        lines.append("- None")
    else:
        for item in missing:
            lines.append(f"- {clean_md(item)}")
    lines.append("")
    return "\n".join(lines)


def validate_checklist(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, f"checklist schema_id must be {SCHEMA_ID}", errors)
    require(data.get("status") == "PASS", "feature checklist fixture must be PASS", errors)
    require(data.get("overall_status") == "DEFERRED_HARDWARE", "overall checklist should reflect the current hardware recovery gate", errors)
    require(data.get("current_next_gate") == "wb55_real_panel_refresh", "checklist next gate must be wb55_real_panel_refresh", errors)
    focus = data.get("current_focus", {})
    require(focus.get("capability_id") == "panel_driver_readiness", "current focus must be panel_driver_readiness", errors)
    require(
        focus.get("gate_status") == "DEFERRED_HARDWARE",
        "current focus should show the WB55 panel recovery hardware gate",
        errors,
    )
    require(focus.get("gate_id") == "wb55_real_panel_refresh", "focused gate id drifted", errors)
    require(focus.get("panel_recovery_gate") == rel(PANEL_RECOVERY_GATE), "focused gate must link current recovery evidence", errors)
    require(
        focus.get("operator_packet") == rel(TOUCH_VISUAL_PACKET),
        "focused gate must link the touch visual acceptance packet",
        errors,
    )
    require(
        focus.get("pre_acceptance_health") == rel(PRE_ACCEPTANCE_HEALTH),
        "focused gate must link the pre-acceptance health fixture",
        errors,
    )
    require(PRE_ACCEPTANCE_HEALTH.exists(), "missing pre-acceptance health fixture", errors)
    require(int(focus.get("missing_ready_field_count", -1)) == 4, "current panel recovery must list four missing facts", errors)
    checklist = data.get("checklist", [])
    require(isinstance(checklist, list) and len(checklist) >= 8, "checklist must cover the roadmap capabilities", errors)
    ids = [item.get("id") for item in checklist if isinstance(item, dict)]
    for required in [
        "expression_artwork_and_copy",
        "portable_expression_model",
        "screen_demo_acceptance_flow",
        "product_status_hooks",
        "wb55_queue_and_host_status",
        "runtime_diagnostics_and_evidence",
        "panel_driver_readiness",
        "wba_migration_readiness",
    ]:
        require(required in ids, f"checklist missing capability {required}", errors)
    missing_fields = data.get("current_missing_panel_facts", [])
    require(len(missing_fields) == 4, "checklist must expose the four current hardware recovery facts", errors)


def check_project_links(errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (EPAPER_README, "epaper README")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "screen_feature_checklist",
            "companion-screen-feature-checklist.json",
            "companion-screen-feature-checklist.md",
            "render_expression_feature_checklist.py",
        ]:
            require(token in text, f"{name} missing feature checklist anchor {token}", errors)


def write_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, data: dict[str, Any], markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")


def check_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, data: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(json_path.exists(), f"missing feature checklist fixture: {rel(json_path)}", errors)
    if json_path.exists():
        actual = load_json(json_path)
        require(actual == data, f"{rel(json_path)} is stale; rerun with --write", errors)
    require(markdown_path.exists(), f"missing feature checklist Markdown: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write", action="store_true", help="Write the deterministic JSON and Markdown checklist.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    errors: list[str] = []
    data = build_checklist()
    markdown = build_markdown(data)
    validate_checklist(data, errors)
    check_project_links(errors)
    if args.write and not errors:
        write_outputs(json_path, markdown_path, data, markdown)
    if not args.write:
        check_outputs(json_path, markdown_path, data, markdown, errors)
    if errors:
        print("FAIL: Companion screen feature checklist checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen feature checklist verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
