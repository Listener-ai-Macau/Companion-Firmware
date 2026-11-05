#!/usr/bin/env python3
"""Verify the real-panel hardware session scaffold for Companion screen work."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-hardware-session.json")
SCHEMA_ID = "companion.pendant.screen_panel_hardware_session.v1"
TARGETS = ("WB55", "WBA55", "WBA65")
GATE_ID = "wb55_real_panel_refresh"

SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs" / "bringup_steps.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
HARDWARE_PLAN = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-acceptance-plan.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
PANEL_RECOVERY_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-wb55-hardware-recovery-gate.json"
PANEL_EVIDENCE_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-record-scaffold.json"
PANEL_EVIDENCE_VALIDATOR = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-record-validator.json"
PANEL_WIRING_PREFLIGHT = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-wiring-preflight.json"
WBA_PORT_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read_text(path, errors)
    if not text:
        return {}
    return json.loads(text)


def session_root(target: str) -> str:
    return f".cache/validation/companion-real-panel-{target.lower()}-<timestamp>"


def session_path(target: str, leaf: str) -> str:
    return f"{session_root(target)}/{leaf}"


def target_resources(target: str) -> str:
    if target == "WB55":
        return "Companion-WB55,BLE-Companion"
    return f"Companion-{target},BLE-Companion"


def target_resource_arg(target: str) -> str:
    return f"'{target_resources(target)}'"


def adapter_pattern(target: str) -> str:
    if target == "WB55":
        return "*_stm32wb.*"
    return "*_stm32wba.*"


def target_static_preflight(target: str) -> list[str]:
    commands = [
        "python .\\tools\\verify_expression_panel_hardware_session.py",
        "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
        "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
    ]
    if target == "WB55":
        commands.extend(
            [
                "python .\\tools\\verify_expression_panel_wiring_preflight.py",
                "python .\\tools\\verify_expression_panel_target_stm32wb.py",
            ]
        )
    else:
        commands.extend(
            [
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            ]
        )
    return commands


def build_target_session(target: str) -> dict[str, Any]:
    root = session_root(target)
    record_path = session_path(target, "panel-evidence-record.json")
    facts_path = session_path(target, "panel-hardware-facts.todo.json")
    bench_path = session_path(target, "companion-ble-real-bench.json")
    diagnostics_path = session_path(target, "diagnostics/summary.json")
    resources = target_resources(target)
    return {
        "target": target,
        "session_root_pattern": root,
        "hardware_lock_resources": resources,
        "adapter_file_pattern": adapter_pattern(target),
        "required_artifacts": [
            {
                "id": "panel_evidence_record",
                "path": record_path,
                "created_by": (
                    "python .\\tools\\init_expression_panel_evidence_record.py "
                    f"--target {target} --session-root {root} --write-session"
                ),
                "validated_by": f"python .\\tools\\verify_expression_panel_evidence_record.py --record {record_path}",
            },
            {
                "id": "hardware_facts_draft",
                "path": facts_path,
                "created_by": (
                    "python .\\tools\\init_expression_panel_evidence_record.py "
                    f"--target {target} --session-root {root} --write-session"
                ),
                "validated_by": f"python .\\tools\\verify_expression_panel_hardware_facts.py --facts {facts_path}",
                "must_start_as": "DRAFT_UNFILLED",
            },
            {
                "id": "real_ble_bench_artifact",
                "path": bench_path,
                "must_include": [
                    "--expect-real-panel",
                    "real_panel_refresh_claimed=true",
                    "screen_expression_status",
                    "card_write",
                    "settings_sleepy_screen_status",
                    "final_card_status=rendered/ok",
                ],
                "failure_must_preserve": [
                    "operations",
                    "partial_operation_count",
                ],
            },
            {
                "id": "diagnostics_bundle_summary",
                "path": diagnostics_path,
                "must_include": [
                    "epaper.runtime_snapshot_decoded",
                    "panel_error_count=0",
                    "display_queue.pending_count=0",
                    "display_queue.dropped_count=0",
                ],
            },
            {
                "id": "visual_before",
                "path": session_path(target, "visual/before_photo.jpg"),
                "record_field": "visual_evidence.before_photo",
            },
            {
                "id": "visual_during",
                "path": session_path(target, "visual/during_refresh_photo_or_video"),
                "record_field": "visual_evidence.during_refresh_photo_or_video",
            },
            {
                "id": "visual_after",
                "path": session_path(target, "visual/after_photo.jpg"),
                "record_field": "visual_evidence.after_photo",
                "record_hash_field": "visual_evidence.evidence_sha256",
            },
            {
                "id": "operator_notes",
                "path": session_path(target, "operator-notes.md"),
                "must_record": [
                    "operator action",
                    "observed refresh result",
                    "panel/controller labels",
                    "deviations from scaffold",
                ],
            },
        ],
        "bootstrap_commands": [
            *target_static_preflight(target),
            (
                "python .\\tools\\init_expression_panel_evidence_record.py "
                f"--target {target} --session-root {root} --write-session"
            ),
            f"python .\\tools\\verify_expression_panel_hardware_facts.py --facts {facts_path}",
            (
                "pwsh -NoProfile -File <ai-collaboration-workflow>\\scripts\\aiw.ps1 "
                f"with-lock -Resource {target_resource_arg(target)} -Purpose \"Companion {target} real e-paper panel session\" "
                "-Run python .\\tools\\companion_ble_real_bench.py --name companion --timeout 20 "
                "--notify-timeout 10 --screen-final-timeout 30 --expect-real-panel "
                f"--output {bench_path} --json"
            ),
            (
                "pwsh -NoProfile -File .\\tools\\collect_companion_diagnostics.ps1 "
                f"-OutputDir {root}\\diagnostics"
            ),
            f"python .\\tools\\verify_expression_panel_evidence_record.py --record {record_path}",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
        "promotion_rule": (
            "Only a filled record that passes verify_expression_panel_evidence_record.py "
            "can move wb55_real_panel_refresh out of DEFERRED_HARDWARE."
        ),
    }


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Defines one hardware-session directory and command scaffold per target so "
            "WB55 real-panel evidence and later WBA55/WBA65 evidence are collected with "
            "the same contract."
        ),
        "gate_id": GATE_ID,
        "current_gate_status": "DEFERRED_HARDWARE",
        "no_hardware_action_required_to_verify_scaffold": True,
        "sources": {
            "hardware_acceptance_plan": rel(HARDWARE_PLAN),
            "panel_hardware_gate": rel(PANEL_GATE),
            "panel_hardware_recovery_gate": rel(PANEL_RECOVERY_GATE),
            "panel_evidence_record_scaffold": rel(PANEL_EVIDENCE_SCAFFOLD),
            "panel_evidence_record_validator": rel(PANEL_EVIDENCE_VALIDATOR),
            "panel_wiring_preflight": rel(PANEL_WIRING_PREFLIGHT),
            "wba_port_contract": rel(WBA_PORT_CONTRACT),
            "wba55_port_scaffold": rel(WBA55_SCAFFOLD),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            "session_verifier": "tools/verify_expression_panel_hardware_session.py",
        },
        "session_contract": {
            "uses_workflow_hardware_lock": True,
            "session_record_starts_from_scaffold": True,
            "hardware_facts_draft_required": True,
            "real_ble_and_diagnostics_artifacts_are_distinct": True,
            "visual_before_during_after_required": True,
            "operator_notes_required": True,
            "target_adapter_pattern_required": True,
            "third_party_cube_dirs_must_remain_clean": True,
            "wba_targets_do_not_inherit_wb55_pin_map": True,
            "failed_live_ble_runs_preserve_partial_operations": True,
        },
        "target_sessions": [build_target_session(target) for target in TARGETS],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_hardware_session.py",
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
            "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel hardware session schema", errors)
    require(data.get("status") == "PASS", "panel hardware session scaffold must be PASS", errors)
    require(data.get("gate_id") == GATE_ID, "panel hardware session scaffold points at the wrong gate", errors)
    require(
        data.get("current_gate_status") == "DEFERRED_HARDWARE",
        "panel hardware session scaffold must preserve the deferred gate",
        errors,
    )
    require(
        data.get("no_hardware_action_required_to_verify_scaffold") is True,
        "panel hardware session verifier must remain a no-hardware check",
        errors,
    )
    contract = data.get("session_contract", {})
    for token in [
        "uses_workflow_hardware_lock",
        "session_record_starts_from_scaffold",
        "hardware_facts_draft_required",
        "real_ble_and_diagnostics_artifacts_are_distinct",
        "visual_before_during_after_required",
        "operator_notes_required",
        "target_adapter_pattern_required",
        "third_party_cube_dirs_must_remain_clean",
        "wba_targets_do_not_inherit_wb55_pin_map",
        "failed_live_ble_runs_preserve_partial_operations",
    ]:
        require(contract.get(token) is True, f"session contract missing {token}", errors)

    source_paths = [value for value in data.get("sources", {}).values() if isinstance(value, str)]
    for source in source_paths:
        require((REPO_ROOT / source).exists(), f"panel hardware session source missing {source}", errors)

    targets = {entry.get("target"): entry for entry in data.get("target_sessions", []) if isinstance(entry, dict)}
    require(set(targets) == set(TARGETS), "panel hardware sessions must cover WB55, WBA55, and WBA65", errors)
    roots: set[str] = set()
    for target in TARGETS:
        entry = targets.get(target, {})
        root = str(entry.get("session_root_pattern", ""))
        roots.add(root)
        require(root == session_root(target), f"{target} session root pattern drifted", errors)
        require(entry.get("hardware_lock_resources") == target_resources(target), f"{target} lock resources drifted", errors)
        require(entry.get("adapter_file_pattern") == adapter_pattern(target), f"{target} adapter pattern drifted", errors)

        artifacts = {artifact.get("id"): artifact for artifact in entry.get("required_artifacts", []) if isinstance(artifact, dict)}
        for artifact_id in [
            "panel_evidence_record",
            "hardware_facts_draft",
            "real_ble_bench_artifact",
            "diagnostics_bundle_summary",
            "visual_before",
            "visual_during",
            "visual_after",
            "operator_notes",
        ]:
            require(artifact_id in artifacts, f"{target} session missing artifact {artifact_id}", errors)
        artifact_paths = [str(artifact.get("path", "")) for artifact in artifacts.values()]
        require(len(artifact_paths) == len(set(artifact_paths)), f"{target} session artifact paths must be distinct", errors)
        for path in artifact_paths:
            require(path.startswith(root), f"{target} artifact path does not stay under session root: {path}", errors)

        serialized = json.dumps(entry, sort_keys=True)
        normalized = serialized.replace("\\\\", "\\")
        for token in [
            f"--target {target}",
            "--expect-real-panel",
            "with-lock",
            f"-Resource {target_resource_arg(target)}",
            target_resources(target),
            "companion_ble_real_bench.py",
            "partial_operation_count",
            "panel-hardware-facts.todo.json",
            "verify_expression_panel_hardware_facts.py --facts",
            "collect_companion_diagnostics.ps1",
            "verify_expression_panel_evidence_record.py --record",
            "screen_expression_status",
            "settings_sleepy_screen_status",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ]:
            require(token in normalized, f"{target} session missing anchor {token}", errors)
        if target == "WB55":
            require("*_stm32wb.*" in normalized, "WB55 session missing *_stm32wb.* adapter rule", errors)
            require("verify_expression_panel_wiring_preflight.py" in normalized, "WB55 session missing wiring preflight", errors)
        else:
            require("*_stm32wba.*" in normalized, f"{target} session missing *_stm32wba.* adapter rule", errors)
            require("verify_expression_wba_portability.py" in normalized, f"{target} session missing WBA portability preflight", errors)
            for wb55_pin in ["PA9", "PC1", "PC2", "PA6", "SPI2_CS"]:
                require(wb55_pin not in normalized, f"{target} session leaked WB55 pin fact {wb55_pin}", errors)
    require(len(roots) == len(TARGETS), "target session roots must be unique", errors)


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    bringup_doc = read_text(BRINGUP_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    plan = read_json(HARDWARE_PLAN, errors)
    gate = read_json(PANEL_GATE, errors)
    recovery = read_json(PANEL_RECOVERY_GATE, errors)
    require(
        gate.get("status") == "PASS"
        and gate.get("evidence_scope") == "historical_refresh_evidence_integrity"
        and gate.get("current_real_refresh_claimed") is False,
        "WB55 historical panel gate must not claim current acceptance",
        errors,
    )
    require(
        recovery.get("status") == "DEFERRED_HARDWARE_FTS02_BOOST"
        and recovery.get("claim_scope") == "current_hardware_recovery_gate_no_panel_acceptance",
        "WB55 current panel recovery gate must remain hardware-deferred",
        errors,
    )

    for text, name in [
        (screen_doc, "screen doc"),
        (bringup_doc, "bringup doc"),
        (wba_rules, "WBA rules"),
        (readme, "epaper README"),
    ]:
        for token in [
            "panel_hardware_session_scaffold",
            "companion-screen-panel-hardware-session.json",
            "verify_expression_panel_hardware_session.py",
            "companion-real-panel-wb55-<timestamp>",
            "operator-notes.md",
            "panel-hardware-facts.todo.json",
            "visual/before_photo.jpg",
            "visual/after_photo.jpg",
            "collect_companion_diagnostics.ps1",
            "--expect-real-panel",
            "verify_expression_panel_evidence_record.py --record",
        ]:
            require(token in text, f"{name} missing hardware session anchor {token}", errors)

    if not allow_stale_index:
        serialized_plan = json.dumps(plan, sort_keys=True)
        for token in [
            "companion-screen-panel-hardware-session.json",
            "verify_expression_panel_hardware_session.py",
            "companion-real-panel-wb55-<timestamp>",
        ]:
            require(token in serialized_plan, f"hardware acceptance plan missing session anchor {token}", errors)

    index_text = read_text(ACCEPTANCE_INDEX, errors)
    if not index_text:
        return
    index = json.loads(index_text)
    items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_hardware_session_scaffold"]
    if allow_stale_index and not items:
        return
    require(len(items) == 1, "acceptance index must contain one panel_hardware_session_scaffold item", errors)
    if items:
        item = items[0]
        require(item.get("status") == "PASS", "panel_hardware_session_scaffold item must be PASS", errors)
        require(
            "docs/validation/companion-screen-panel-hardware-session.json" in item.get("evidence_paths", []),
            "panel_hardware_session_scaffold item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_panel_hardware_session.py" in item.get("validation_commands", []),
            "panel_hardware_session_scaffold item must run its verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel hardware session fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic hardware session JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen panel hardware session checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen panel hardware session verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
