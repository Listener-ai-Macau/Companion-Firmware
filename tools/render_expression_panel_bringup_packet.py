#!/usr/bin/env python3
"""Render a real-panel bring-up operator packet for Companion screen work."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import init_expression_panel_evidence_record as init_record  # noqa: E402
import render_expression_panel_facts_worksheet as facts_worksheet  # noqa: E402
import verify_expression_panel_driver_readiness as readiness  # noqa: E402
import verify_expression_panel_hardware_facts as hardware_facts  # noqa: E402


DEFAULT_JSON = pathlib.Path("docs/validation/companion-screen-panel-bringup-operator-packet.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-panel-bringup-operator-packet.md")
SCHEMA_ID = "companion.pendant.screen_panel_bringup_operator_packet.v1"
GATE_ID = "wb55_real_panel_refresh"

ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
ACCEPTANCE_PLAN = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-acceptance-plan.json"
HARDWARE_SESSION = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-session.json"
FACTS_WORKSHEET = REPO_ROOT / "docs/validation/companion-screen-panel-facts-worksheet.json"
DRIVER_READINESS = REPO_ROOT / "docs/validation/companion-screen-panel-driver-readiness.json"
DEMO_HANDOFF = REPO_ROOT / "docs/validation/companion-screen-expression-demo-panel-handoff.json"
PANEL_TEMPLATE = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-template.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"


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
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def path_text(path: pathlib.Path) -> str:
    return rel(path).replace("\\", "/")


def join_path(root: str, suffix: str) -> str:
    clean_root = root.replace("\\", "/").rstrip("/")
    clean_suffix = suffix.replace("\\", "/").lstrip("/")
    return f"{clean_root}/{clean_suffix}"


def target_resources(target: str) -> str:
    if target == "WB55":
        return "Companion-WB55,BLE-Companion"
    return f"Companion-{target},BLE-Companion"


def target_resource_arg(target: str) -> str:
    return f"'{target_resources(target)}'"


def adapter_file(target: str) -> str:
    if target == "WB55":
        return "app/companion_pendant/epaper/panel_target_stm32wb.c"
    return "app/companion_pendant/epaper/panel_target_stm32wba.c"


def session_root_pattern(target: str) -> str:
    return f".cache/validation/companion-real-panel-{target.lower()}-<timestamp>"


def facts_path_from_args(args: argparse.Namespace) -> pathlib.Path | None:
    if args.session_root is not None:
        root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
        return root / init_record.SESSION_FACTS_FILENAME
    if args.facts is not None:
        return args.facts if args.facts.is_absolute() else REPO_ROOT / args.facts
    return None


def worksheet_from_args(args: argparse.Namespace) -> dict[str, Any]:
    facts_path = facts_path_from_args(args)
    if facts_path is None:
        return facts_worksheet.build_fixture()
    return facts_worksheet.build_worksheet(load_json(facts_path), facts_path)


def missing_rows(worksheet: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "field": row.get("field"),
            "current_value": row.get("current_value"),
            "accepted_values": row.get("accepted_values"),
            "prompt": row.get("prompt"),
        }
        for row in worksheet.get("worksheet_rows", [])
        if isinstance(row, dict) and row.get("status") == "missing"
    ]


def session_root_text(target: str, args: argparse.Namespace) -> str:
    if args.session_root is None:
        return session_root_pattern(target)
    root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
    return path_text(root)


def build_commands(target: str, session_root: str) -> dict[str, Any]:
    facts_path = join_path(session_root, init_record.SESSION_FACTS_FILENAME)
    record_path = join_path(session_root, init_record.SESSION_RECORD_FILENAME)
    worksheet_json = join_path(session_root, "panel-facts-worksheet.json")
    worksheet_md = join_path(session_root, "panel-facts-worksheet.md")
    readiness_json = join_path(session_root, "panel-driver-readiness.json")
    ble_json = join_path(session_root, "companion-ble-real-bench.json")
    diagnostics_dir = join_path(session_root, "diagnostics")
    return {
        "session_setup": [
            f"python .\\tools\\init_expression_panel_evidence_record.py --target {target} --session-root {session_root} --write-session",
            f"python .\\tools\\verify_expression_panel_session_directory.py --session-root {session_root} --target {target}",
            f"python .\\tools\\verify_expression_panel_hardware_facts.py --facts {facts_path}",
        ],
        "facts_worksheet": [
            f"python .\\tools\\render_expression_panel_facts_worksheet.py --session-root {session_root} --write --json {worksheet_json} --markdown {worksheet_md}",
            f"python .\\tools\\verify_expression_panel_driver_readiness.py --session-root {session_root} --output {readiness_json}",
        ],
        "pre_driver_gate": [
            f"python .\\tools\\verify_expression_panel_driver_readiness.py --session-root {session_root} --require-ready",
        ],
        "evidence_record_bridge": [
            f"python .\\tools\\apply_expression_panel_hardware_facts.py --facts {facts_path} --record {record_path} --write",
        ],
        "driver_and_static_checks": [
            f"edit {adapter_file(target)}",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1" if target == "WB55" else "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_telemetry.py",
        ],
        "real_panel_evidence": [
            (
                "pwsh -NoProfile -File <ai-collaboration-workflow>\\scripts\\aiw.ps1 "
                f"with-lock -Resource {target_resource_arg(target)} -Purpose \"Companion {target} real e-paper panel operator packet\" "
                "-Run python .\\tools\\companion_ble_real_bench.py --name companion --timeout 20 "
                "--notify-timeout 10 --screen-final-timeout 30 --expect-real-panel "
                f"--output {ble_json} --json"
            ),
            f"pwsh -NoProfile -File .\\tools\\collect_companion_diagnostics.ps1 -OutputDir {diagnostics_dir}",
            f"python .\\tools\\verify_expression_panel_evidence_record.py --record {record_path}",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
    }


def build_session_artifacts(session_root: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "panel_evidence_record",
            "path": join_path(session_root, init_record.SESSION_RECORD_FILENAME),
            "purpose": "Final real-panel evidence record; starts DRAFT_UNFILLED and must remain draft until all evidence is present.",
        },
        {
            "id": "hardware_facts",
            "path": join_path(session_root, init_record.SESSION_FACTS_FILENAME),
            "purpose": "Fill controller, wiring, power, voltage, and timing facts before target driver implementation.",
        },
        {
            "id": "facts_worksheet",
            "path": join_path(session_root, "panel-facts-worksheet.md"),
            "purpose": "Operator-facing table of missing driver-readiness fields.",
        },
        {
            "id": "driver_readiness",
            "path": join_path(session_root, "panel-driver-readiness.json"),
            "purpose": "Machine-readable BLOCKED_ON_HARDWARE_FACTS or READY_FOR_DRIVER_IMPLEMENTATION report.",
        },
        {
            "id": "operator_notes",
            "path": join_path(session_root, "operator-notes.md"),
            "purpose": "Record operator action, panel labels, observed refresh result, and deviations.",
        },
        {
            "id": "visual_before",
            "path": join_path(session_root, "visual/before_photo.jpg"),
            "purpose": "Photo before the refresh attempt.",
        },
        {
            "id": "visual_during",
            "path": join_path(session_root, "visual/during_refresh_photo_or_video"),
            "purpose": "Photo or video during the refresh attempt.",
        },
        {
            "id": "visual_after",
            "path": join_path(session_root, "visual/after_photo.jpg"),
            "purpose": "Photo after the refresh attempt; hash goes into panel-evidence-record.json.",
        },
        {
            "id": "real_ble_bench",
            "path": join_path(session_root, "companion-ble-real-bench.json"),
            "purpose": "BLE artifact created with --expect-real-panel and final rendered/ok status; failed runs must preserve operations and partial_operation_count.",
        },
        {
            "id": "diagnostics_summary",
            "path": join_path(session_root, "diagnostics/summary.json"),
            "purpose": "Diagnostics bundle summary with epaper.runtime_snapshot_decoded health, panel_error_count=0, pending display work=0, and dropped display work=0.",
        },
    ]


def build_operator_steps(commands: dict[str, list[str]], missing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identity_fields = [row["field"] for row in missing if str(row.get("field", "")).startswith("panel_identity.")]
    wiring_fields = [row["field"] for row in missing if str(row.get("field", "")).startswith("target_pin_map.")]
    timing_fields = [row["field"] for row in missing if str(row.get("field", "")).startswith("driver_timing.")]
    return [
        {
            "id": "create_session",
            "title": "Create the target session directory",
            "commands": commands["session_setup"],
            "completion_check": "Session contains panel-evidence-record.json, panel-hardware-facts.todo.json, visual/, diagnostics/, and operator-notes.md.",
        },
        {
            "id": "fill_panel_identity",
            "title": "Fill panel identity facts",
            "fields": identity_fields,
            "completion_check": "Controller, module label, datasheet revision, and LUT source are non-placeholder values.",
        },
        {
            "id": "fill_wiring_and_power",
            "title": "Fill wiring, power, and voltage facts",
            "fields": wiring_fields,
            "completion_check": "DC/RST/BUSY/power-enable/logic-voltage facts are target-specific and do not copy another board.",
        },
        {
            "id": "fill_driver_timing",
            "title": "Fill reset, BUSY, refresh, partial-refresh, and sleep timing facts",
            "fields": timing_fields,
            "completion_check": "Timing and command sequence facts are traceable to the controller datasheet or module vendor notes.",
        },
        {
            "id": "prove_driver_readiness",
            "title": "Run the concrete pre-driver readiness gate",
            "commands": commands["facts_worksheet"] + commands["pre_driver_gate"],
            "completion_check": "Readiness reports READY_FOR_DRIVER_IMPLEMENTATION for this session only.",
        },
        {
            "id": "bridge_facts_into_evidence_record",
            "title": "Copy ready facts into the session evidence record",
            "commands": commands["evidence_record_bridge"],
            "completion_check": "panel-evidence-record.json remains DRAFT_UNFILLED and still does not claim real refresh.",
        },
        {
            "id": "implement_target_driver",
            "title": "Implement the target-owned panel driver entrypoint",
            "commands": commands["driver_and_static_checks"],
            "completion_check": "Target driver builds and portable expression/display queue files remain free of SPI/GPIO/BUSY code.",
        },
        {
            "id": "collect_real_panel_evidence",
            "title": "Collect BLE, diagnostics, visual evidence, and final record validation",
            "commands": commands["real_panel_evidence"],
            "completion_check": "Final record passes verify_expression_panel_evidence_record.py with rendered/ok, zero runtime errors, and before/during/after visual evidence.",
        },
    ]


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    worksheet = worksheet_from_args(args)
    target = str(worksheet.get("target") or args.target)
    session_root = session_root_text(target, args)
    missing = missing_rows(worksheet)
    commands = build_commands(target, session_root)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Operator packet for the next real e-paper panel bring-up step without claiming real refresh.",
        "claim_scope": "operator_packet_no_hardware_claim",
        "target": target,
        "session_root": session_root,
        "gate_id": GATE_ID,
        "current_gate_status": "DEFERRED_HARDWARE",
        "real_refresh_claimed": False,
        "facts_status": worksheet.get("facts_status"),
        "readiness_status": worksheet.get("readiness_status"),
        "missing_ready_field_count": worksheet.get("missing_ready_field_count"),
        "known_transport": worksheet.get("known_transport"),
        "missing_ready_fields": missing,
        "sources": {
            "packet_tool": "tools/render_expression_panel_bringup_packet.py",
            "facts_worksheet": rel(FACTS_WORKSHEET),
            "driver_readiness": rel(DRIVER_READINESS),
            "hardware_acceptance_plan": rel(ACCEPTANCE_PLAN),
            "hardware_session": rel(HARDWARE_SESSION),
            "demo_panel_handoff": rel(DEMO_HANDOFF),
            "panel_evidence_template": rel(PANEL_TEMPLATE),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "epaper_readme": rel(EPAPER_README),
            "wba_rules": rel(WBA_RULES),
        },
        "session_artifacts": build_session_artifacts(session_root),
        "operator_steps": build_operator_steps(commands, missing),
        "command_groups": commands,
        "promotion_rule": (
            "This packet can only move work to driver implementation after --require-ready passes "
            "for the concrete session; it cannot move wb55_real_panel_refresh to PASS."
        ),
        "real_ble_failure_evidence": {
            "failed_runs_preserve_operations": True,
            "required_fields": ["operations", "partial_operation_count"],
            "reason": "Distinguish BLE or board reachability loss from screen contract drift while keeping partial CardStatusV1 evidence.",
        },
        "wba_migration_guard": {
            "wba55_wba65_need_separate_packets": True,
            "do_not_reuse_wb55_pin_map_as_wba_evidence": True,
            "portable_files_remain_hal_free": True,
        },
        "validation_commands": [
            "python .\\tools\\render_expression_panel_bringup_packet.py",
            "python .\\tools\\render_expression_panel_bringup_packet.py --self-test",
            "python .\\tools\\render_expression_panel_facts_worksheet.py --self-test",
            "python .\\tools\\verify_expression_panel_driver_readiness.py --self-test",
            "python .\\tools\\verify_expression_panel_hardware_session.py",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    transport = packet.get("known_transport", {})
    lines = [
        "# Companion Panel Bring-up Operator Packet",
        "",
        "This packet is generated. Update it with `python .\\tools\\render_expression_panel_bringup_packet.py --write`.",
        "",
        "## Status",
        "",
        f"- Target: `{clean_md(packet.get('target'))}`",
        f"- Session root: `{clean_md(packet.get('session_root'))}`",
        f"- Gate: `{clean_md(packet.get('gate_id'))}` remains `{clean_md(packet.get('current_gate_status'))}`",
        f"- Facts status: `{clean_md(packet.get('facts_status'))}`",
        f"- Driver readiness: `{clean_md(packet.get('readiness_status'))}`",
        f"- Missing fields: `{clean_md(packet.get('missing_ready_field_count'))}`",
        f"- Known transport: `{clean_md(transport.get('spi_instance_or_bus'))} SCK={clean_md(transport.get('sck_pin'))} MOSI={clean_md(transport.get('mosi_pin'))} MISO={clean_md(transport.get('miso_pin'))} CS={clean_md(transport.get('cs_pin'))}`",
        "",
        "## Operator Steps",
        "",
        "| # | Step | Completion check |",
        "|---:|---|---|",
    ]
    for index, step in enumerate(packet.get("operator_steps", []), start=1):
        lines.append(
            f"| {index} | `{clean_md(step.get('id'))}` | {clean_md(step.get('completion_check'))} |"
        )
    lines.extend(["", "## Missing Facts", "", "| Field | Current value | Accepted values |", "|---|---|---|"])
    for row in packet.get("missing_ready_fields", []):
        lines.append(
            f"| `{clean_md(row.get('field'))}` | `{clean_md(row.get('current_value'))}` | {clean_md(row.get('accepted_values'))} |"
        )
    lines.extend(["", "## Session Artifacts", "", "| Artifact | Path | Purpose |", "|---|---|---|"])
    for artifact in packet.get("session_artifacts", []):
        lines.append(
            f"| `{clean_md(artifact.get('id'))}` | `{clean_md(artifact.get('path'))}` | {clean_md(artifact.get('purpose'))} |"
        )
    lines.extend(["", "## Command Groups", ""])
    for group, commands in packet.get("command_groups", {}).items():
        lines.extend([f"### {clean_md(group)}", ""])
        for command in commands:
            lines.append(f"- `{clean_md(command)}`")
        lines.append("")
    return "\n".join(lines)


def validate_packet(packet: dict[str, Any], errors: list[str], deterministic: bool = True) -> None:
    require(packet.get("schema_id") == SCHEMA_ID, f"packet schema_id must be {SCHEMA_ID}", errors)
    require(packet.get("status") == "PASS", "operator packet status must be PASS", errors)
    require(packet.get("claim_scope") == "operator_packet_no_hardware_claim", "packet must not claim hardware refresh", errors)
    require(packet.get("gate_id") == GATE_ID, "packet must target the real-panel gate", errors)
    require(packet.get("current_gate_status") == "DEFERRED_HARDWARE", "packet must preserve deferred hardware gate", errors)
    require(packet.get("real_refresh_claimed") is False, "packet must not claim real refresh", errors)
    require(packet.get("readiness_status") in {readiness.BLOCKED_STATUS, readiness.READY_STATUS}, "packet readiness must be blocked or ready", errors)
    if deterministic:
        require(packet.get("target") == "WB55", "deterministic operator packet must target WB55", errors)
        require(packet.get("readiness_status") == readiness.BLOCKED_STATUS, "deterministic packet must show current facts blocker", errors)
        require(packet.get("missing_ready_field_count") == 15, "deterministic packet must list 15 missing fields", errors)
        transport = packet.get("known_transport", {})
        require(transport.get("spi_instance_or_bus") == "SPI2", "deterministic packet must keep WB55 SPI2 transport", errors)
        require(transport.get("sck_pin") == "PA9", "deterministic packet must keep WB55 SCK pin", errors)

    missing_fields = [row.get("field") for row in packet.get("missing_ready_fields", []) if isinstance(row, dict)]
    for required in [
        "panel_identity.controller_model",
        "target_pin_map.dc_pin",
        "target_pin_map.rst_pin",
        "target_pin_map.busy_pin",
        "driver_timing.full_refresh_sequence",
    ]:
        if deterministic:
            require(required in missing_fields, f"packet missing required field {required}", errors)

    serialized = json.dumps(packet, sort_keys=True)
    for token in [
        "init_expression_panel_evidence_record.py",
        "verify_expression_panel_session_directory.py",
        "render_expression_panel_facts_worksheet.py",
        "verify_expression_panel_driver_readiness.py --session-root",
        "--require-ready",
        "apply_expression_panel_hardware_facts.py",
        "--expect-real-panel",
        "collect_companion_diagnostics.ps1",
        "verify_expression_panel_evidence_record.py --record",
        "partial_operation_count",
        "visual/before_photo.jpg",
        "visual/during_refresh_photo_or_video",
        "visual/after_photo.jpg",
        "diagnostics/summary.json",
        "panel_error_count",
    ]:
        require(token in serialized, f"operator packet missing token {token}", errors)

    step_ids = [step.get("id") for step in packet.get("operator_steps", []) if isinstance(step, dict)]
    for step_id in [
        "create_session",
        "fill_panel_identity",
        "fill_wiring_and_power",
        "fill_driver_timing",
        "prove_driver_readiness",
        "bridge_facts_into_evidence_record",
        "implement_target_driver",
        "collect_real_panel_evidence",
    ]:
        require(step_id in step_ids, f"operator packet missing step {step_id}", errors)

    guard = packet.get("wba_migration_guard", {})
    require(guard.get("wba55_wba65_need_separate_packets") is True, "packet must require separate WBA packets", errors)
    require(guard.get("do_not_reuse_wb55_pin_map_as_wba_evidence") is True, "packet must prevent WBA pin reuse", errors)
    require(guard.get("portable_files_remain_hal_free") is True, "packet must keep portable files HAL-free", errors)


def run_self_test() -> list[str]:
    errors: list[str] = []
    parser = parse_args([])
    draft = build_packet(parser)
    validate_packet(draft, errors)

    ready_args = parse_args([])
    ready_worksheet = facts_worksheet.build_worksheet(hardware_facts.build_ready_self_test_facts("WB55"))
    original = worksheet_from_args
    try:
        globals()["worksheet_from_args"] = lambda _args: ready_worksheet
        ready_packet = build_packet(ready_args)
    finally:
        globals()["worksheet_from_args"] = original
    validate_packet(ready_packet, errors, deterministic=False)
    require(ready_packet.get("readiness_status") == readiness.READY_STATUS, "ready packet should reach READY_FOR_DRIVER_IMPLEMENTATION", errors)
    require(ready_packet.get("missing_ready_field_count") == 0, "ready packet should have no missing fields", errors)
    require(not ready_packet.get("missing_ready_fields"), "ready packet should not list missing fields", errors)
    return errors


def check_project_links(errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (BRINGUP_DOC, "bringup doc"), (EPAPER_README, "epaper README"), (WBA_RULES, "WBA rules")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_bringup_operator_packet",
            "companion-screen-panel-bringup-operator-packet.json",
            "companion-screen-panel-bringup-operator-packet.md",
            "render_expression_panel_bringup_packet.py",
        ]:
            require(token in text, f"{name} missing operator packet anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_bringup_operator_packet"]
        require(len(items) == 1, "acceptance index must contain one panel_bringup_operator_packet item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_bringup_operator_packet item must be PASS", errors)
            require(
                "docs/validation/companion-screen-panel-bringup-operator-packet.json" in item.get("evidence_paths", []),
                "panel_bringup_operator_packet item must link JSON fixture",
                errors,
            )


def write_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, packet: dict[str, Any], markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")


def check_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, packet: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(json_path.exists(), f"missing panel bring-up operator packet JSON: {rel(json_path)}", errors)
    if json_path.exists():
        require(load_json(json_path) == packet, f"{rel(json_path)} is stale; rerun with --write", errors)
    require(markdown_path.exists(), f"missing panel bring-up operator packet Markdown: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--facts", type=pathlib.Path, default=None)
    parser.add_argument("--session-root", type=pathlib.Path, default=None)
    parser.add_argument("--target", choices=init_record.TARGETS, default="WB55")
    parser.add_argument("--write", action="store_true", help="Write the deterministic or requested operator packet outputs.")
    parser.add_argument("--self-test", action="store_true", help="Run draft and ready packet checks.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    deterministic = args.facts is None and args.session_root is None
    errors: list[str] = []

    facts_path = facts_path_from_args(args)
    if facts_path is not None and not facts_path.exists():
        errors.append(f"facts file missing: {rel(facts_path)}")
        packet = build_packet(parse_args([]))
    else:
        packet = build_packet(args)
    markdown = render_markdown(packet)
    validate_packet(packet, errors, deterministic=deterministic)
    if args.self_test:
        errors.extend(run_self_test())
    if deterministic and not args.write:
        check_project_links(errors)
    if args.write and not errors:
        write_outputs(json_path, markdown_path, packet, markdown)
    if deterministic and not args.write:
        check_outputs(json_path, markdown_path, packet, markdown, errors)

    if errors:
        print("FAIL: Companion panel bring-up operator packet checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel bring-up operator packet verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
