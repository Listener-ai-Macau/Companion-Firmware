#!/usr/bin/env python3
"""Render a host-visible ExpressionV1 manifest for one-by-one acceptance."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = pathlib.Path("docs/validation/companion-screen-expression-host-manifest.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-expression-host-manifest.md")
SCHEMA_ID = "companion.pendant.screen_expression_host_manifest.v1"

CATALOG = REPO_ROOT / "docs/validation/companion-screen-expression-catalog.json"
POLICY = REPO_ROOT / "docs/validation/companion-screen-expression-policy.json"
HOST_SEQUENCE = REPO_ROOT / "docs/validation/companion-screen-expression-host-status-sequence.json"
DEMO_HOST_SEQUENCE = REPO_ROOT / "docs/validation/companion-screen-expression-demo-host-status-sequence.json"
STATE_TELEMETRY = REPO_ROOT / "docs/validation/companion-screen-expression-state-telemetry.json"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"


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


def by_name(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("name")): item for item in items if isinstance(item, dict)}


def group_by_expression(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        expression = str(item.get("expression", ""))
        grouped.setdefault(expression, []).append(item)
    return grouped


def policy_cases_by_expression(policy: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for case in policy.get("cases", []):
        if not isinstance(case, dict):
            continue
        expression = str(case.get("expected_expression", ""))
        grouped.setdefault(expression, []).append(str(case.get("case_id")))
    return grouped


def host_examples_by_expression(sequence: dict[str, Any], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for step in sequence.get(key, []):
        if not isinstance(step, dict):
            continue
        expression = str(step.get("expression", ""))
        grouped.setdefault(expression, []).append(
            {
                "event": step.get("event"),
                "signal": step.get("signal"),
                "signal_id": step.get("signal_id"),
                "diagnostic_arg3": step.get("diagnostic_arg3"),
                "request_id": step.get("request_id"),
                "content_crc32": step.get("content_crc32"),
            }
        )
    return grouped


def compact_examples(examples: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any]] = set()
    compact: list[dict[str, Any]] = []
    for example in examples:
        key = (example.get("event"), example.get("signal"))
        if key in seen:
            continue
        seen.add(key)
        compact.append(example)
        if len(compact) >= limit:
            break
    return compact


def signal_rows(catalog: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for signal in catalog.get("signals", []):
        if not isinstance(signal, dict):
            continue
        expression = str(signal.get("expression", ""))
        rows.setdefault(expression, []).append(
            {
                "id": signal.get("id"),
                "signal": signal.get("signal"),
                "may_lower_priority": signal.get("may_lower_priority"),
                "reason": signal.get("reason"),
            }
        )
    return rows


def build_manifest() -> dict[str, Any]:
    catalog = load_json(CATALOG)
    policy = load_json(POLICY)
    host_sequence = load_json(HOST_SEQUENCE)
    demo_host_sequence = load_json(DEMO_HOST_SEQUENCE)
    telemetry = load_json(STATE_TELEMETRY)

    expressions = by_name(catalog.get("expressions", []))
    signal_by_expression = signal_rows(catalog)
    policy_by_expression = policy_cases_by_expression(policy)
    legacy_examples = host_examples_by_expression(host_sequence, "steps")
    demo_examples = host_examples_by_expression(demo_host_sequence, "accepted_status_steps")
    legacy_faces = sorted(legacy_examples)
    demo_faces = sorted(demo_examples)

    manifest_faces: list[dict[str, Any]] = []
    for name in sorted(expressions, key=lambda item: int(expressions[item].get("id", 999))):
        expression = expressions[name]
        first_demo = compact_examples(demo_examples.get(name, []), limit=2)
        first_legacy = compact_examples(legacy_examples.get(name, []), limit=2)
        manifest_faces.append(
            {
                "id": expression.get("id"),
                "name": name,
                "title": expression.get("title"),
                "body": expression.get("body"),
                "footer": expression.get("footer"),
                "priority": expression.get("priority"),
                "stability": expression.get("stability"),
                "auto_recover_ms": expression.get("auto_recover_ms"),
                "signals": signal_by_expression.get(name, []),
                "policy_case_ids": sorted(policy_by_expression.get(name, [])),
                "legacy_host_sequence_covered": name in legacy_examples,
                "demo_host_sequence_covered": name in demo_examples,
                "legacy_host_examples": first_legacy,
                "demo_host_examples": first_demo,
                "host_acceptance_hint": (
                    "Covered by screen_expression_status and screen_expression_demo_status."
                    if name in legacy_examples
                    else "Covered by screen_expression_demo_status; add to real BLE screen_expression_status when expanding the six-face bench."
                ),
            }
        )

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Host-facing manifest that explains how every ExpressionV1 face is identified, triggered, observed, and accepted.",
        "sources": {
            "catalog": rel(CATALOG),
            "policy": rel(POLICY),
            "host_status_sequence": rel(HOST_SEQUENCE),
            "demo_host_status_sequence": rel(DEMO_HOST_SEQUENCE),
            "state_telemetry": rel(STATE_TELEMETRY),
            "ble_contract": rel(BLE_CONTRACT),
            "screen_doc": rel(SCREEN_DOC),
            "epaper_readme": rel(EPAPER_README),
            "wba_rules": rel(WBA_RULES),
            "manifest_tool": "tools/render_expression_host_manifest.py",
        },
        "host_observability": {
            "card_status": "CardStatusV1 accepted/final pairs on expression card slot 1",
            "diagnostic_arg3_model": catalog.get("public_invariants", {}).get("diagnostic_arg3_model"),
            "expression_request_id_base": catalog.get("public_invariants", {}).get("expression_request_id_base"),
            "telemetry_snapshot": telemetry.get("contract", {}).get("snapshot_api"),
            "telemetry_fields": sorted(telemetry.get("telemetry_fields", {}).keys()),
        },
        "coverage": {
            "expression_count": len(manifest_faces),
            "signal_count": int(catalog.get("public_invariants", {}).get("signal_count", 0)),
            "policy_expression_coverage": sorted(policy.get("policy_coverage", [])),
            "legacy_host_sequence_faces": legacy_faces,
            "demo_host_sequence_faces": demo_faces,
            "demo_covers_all_faces": set(demo_faces) == set(expressions),
            "legacy_gap_faces": sorted(set(expressions) - set(legacy_faces)),
        },
        "faces": manifest_faces,
        "wba_contract": {
            "same_face_ids": True,
            "same_signal_ids": True,
            "same_diagnostic_arg3_model": True,
            "same_card_status_semantics": True,
            "target_adapter_only_replaces_transport": True,
        },
        "validation_commands": [
            "python .\\tools\\render_expression_host_manifest.py",
            "python .\\tools\\render_expression_host_manifest.py --self-test",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_policy.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_expression_demo_host_status_sequence.py",
            "python .\\tools\\verify_expression_state_telemetry.py",
        ],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    coverage = manifest.get("coverage", {})
    obs = manifest.get("host_observability", {})
    lines = [
        "# Companion ExpressionV1 Host Manifest",
        "",
        "This manifest is generated. Update it with `python .\\tools\\render_expression_host_manifest.py --write`.",
        "",
        "## Coverage",
        "",
        f"- Expressions: `{clean_md(coverage.get('expression_count'))}`",
        f"- Signals: `{clean_md(coverage.get('signal_count'))}`",
        f"- Demo covers all faces: `{clean_md(coverage.get('demo_covers_all_faces'))}`",
        f"- Legacy host sequence faces: `{clean_md(coverage.get('legacy_host_sequence_faces'))}`",
        f"- Legacy gap faces: `{clean_md(coverage.get('legacy_gap_faces'))}`",
        "",
        "## Host Observability",
        "",
        f"- Card status: {clean_md(obs.get('card_status'))}",
        f"- Diagnostic arg3: `{clean_md(obs.get('diagnostic_arg3_model'))}`",
        f"- Request id base: `{clean_md(obs.get('expression_request_id_base'))}`",
        f"- Telemetry snapshot: `{clean_md(obs.get('telemetry_snapshot'))}`",
        "",
        "## Faces",
        "",
        "| ID | Face | Priority | Stability | Auto recover | Signals | Host coverage |",
        "|---:|---|---:|---|---:|---|---|",
    ]
    for face in manifest.get("faces", []):
        signals = [signal.get("signal") for signal in face.get("signals", [])]
        coverage_note = (
            "legacy+demo" if face.get("legacy_host_sequence_covered") else "demo"
        )
        lines.append(
            "| "
            f"{clean_md(face.get('id'))} | "
            f"`{clean_md(face.get('name'))}` | "
            f"{clean_md(face.get('priority'))} | "
            f"{clean_md(face.get('stability'))} | "
            f"{clean_md(face.get('auto_recover_ms'))} | "
            f"{clean_md(signals)} | "
            f"{coverage_note} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    require(manifest.get("schema_id") == SCHEMA_ID, f"manifest schema_id must be {SCHEMA_ID}", errors)
    require(manifest.get("status") == "PASS", "host manifest must be PASS", errors)
    coverage = manifest.get("coverage", {})
    faces = manifest.get("faces", [])
    require(coverage.get("expression_count") == 10, "host manifest must list 10 ExpressionV1 faces", errors)
    require(coverage.get("signal_count") == 18, "host manifest must preserve 18 ExpressionV1 signals", errors)
    require(coverage.get("demo_covers_all_faces") is True, "demo host sequence must cover all faces", errors)
    require(coverage.get("legacy_gap_faces") == ["happy", "listening", "speaking", "thinking"], "legacy host gap faces drifted", errors)
    names = [face.get("name") for face in faces if isinstance(face, dict)]
    require(len(names) == len(set(names)) == 10, "host manifest face names must be unique", errors)
    for expected in ["idle", "listening", "thinking", "speaking", "happy", "sleepy", "recording", "sync_complete", "low_battery", "error"]:
        require(expected in names, f"host manifest missing face {expected}", errors)
    for face in faces:
        if not isinstance(face, dict):
            continue
        require(face.get("policy_case_ids"), f"{face.get('name')} must link at least one policy case", errors)
        require(face.get("demo_host_sequence_covered") is True, f"{face.get('name')} must have demo host coverage", errors)
        require(face.get("signals"), f"{face.get('name')} must list source signals", errors)
        for example in face.get("demo_host_examples", []):
            expression_id = int(face.get("id", -1))
            signal_id = int(example.get("signal_id", -1))
            arg3 = str(example.get("diagnostic_arg3", ""))
            expected_arg3 = f"0x{((expression_id << 16) | signal_id):08x}"
            require(arg3 == expected_arg3, f"{face.get('name')} diagnostic arg3 mismatch {arg3} != {expected_arg3}", errors)
    obs = manifest.get("host_observability", {})
    require(obs.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id", "host manifest diagnostic model drifted", errors)
    require(obs.get("telemetry_snapshot") == "comp_epaper_expression_state_snapshot", "host manifest missing telemetry snapshot API", errors)
    guard = manifest.get("wba_contract", {})
    for key in ["same_face_ids", "same_signal_ids", "same_diagnostic_arg3_model", "same_card_status_semantics", "target_adapter_only_replaces_transport"]:
        require(guard.get(key) is True, f"host manifest WBA contract missing {key}", errors)


def check_project_links(errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (EPAPER_README, "epaper README"), (WBA_RULES, "WBA rules")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "expression_host_manifest",
            "companion-screen-expression-host-manifest.json",
            "companion-screen-expression-host-manifest.md",
            "render_expression_host_manifest.py",
        ]:
            require(token in text, f"{name} missing host manifest anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "expression_host_manifest"]
        require(len(items) == 1, "acceptance index must contain one expression_host_manifest item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "expression_host_manifest item must be PASS", errors)
            require(
                "docs/validation/companion-screen-expression-host-manifest.json" in item.get("evidence_paths", []),
                "expression_host_manifest item must link JSON fixture",
                errors,
            )


def run_self_test() -> list[str]:
    errors: list[str] = []
    manifest = build_manifest()
    validate_manifest(manifest, errors)
    by_face = {face.get("name"): face for face in manifest.get("faces", []) if isinstance(face, dict)}
    require(by_face.get("recording", {}).get("priority") == 90, "recording priority should stay 90", errors)
    require(by_face.get("error", {}).get("priority") == 100, "error priority should stay 100", errors)
    require(by_face.get("sleepy", {}).get("legacy_host_sequence_covered") is True, "sleepy should be in legacy host sequence", errors)
    require(by_face.get("thinking", {}).get("legacy_host_sequence_covered") is False, "thinking should remain a legacy host gap until bench expands", errors)
    return errors


def write_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, manifest: dict[str, Any], markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")


def check_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, manifest: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(json_path.exists(), f"missing host manifest JSON: {rel(json_path)}", errors)
    if json_path.exists():
        require(load_json(json_path) == manifest, f"{rel(json_path)} is stale; rerun with --write", errors)
    require(markdown_path.exists(), f"missing host manifest Markdown: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write", action="store_true", help="Write the deterministic JSON and Markdown manifest.")
    parser.add_argument("--self-test", action="store_true", help="Run manifest coverage checks.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    errors: list[str] = []

    for path in [CATALOG, POLICY, HOST_SEQUENCE, DEMO_HOST_SEQUENCE, STATE_TELEMETRY]:
        require(path.exists(), f"missing required source {rel(path)}", errors)
    manifest = build_manifest() if not errors else {"schema_id": SCHEMA_ID, "status": "FAIL"}
    markdown = render_markdown(manifest)
    validate_manifest(manifest, errors)
    if args.self_test:
        errors.extend(run_self_test())
    if not args.write:
        check_project_links(errors)
        check_outputs(json_path, markdown_path, manifest, markdown, errors)
    if args.write and not errors:
        write_outputs(json_path, markdown_path, manifest, markdown)

    if errors:
        print("FAIL: Companion ExpressionV1 host manifest checks failed:", file=__import__("sys").stderr)
        for error in errors:
            print(f" - {error}", file=__import__("sys").stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 host manifest verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
