#!/usr/bin/env python3
"""Verify the SCR-17 generation release ledger for the current screen candidate."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-generation-release-ledger.json"
SCHEMA_ID = "companion.pendant.screen_generation_release_ledger.v1"
PENDING_RUNTIME_RECHECK = "PENDING_RUNTIME_RECHECK"
RUNTIME_LOGS_PASS_PROMOTION_PENDING = "RUNTIME_LOGS_PASS_PROMOTION_PENDING"
RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING = "RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING"

PLAN = ROOT / "docs/companion_screen_project_plan.md"
RESEARCH = ROOT / "docs/validation/companion-screen-generation-swap-research.md"
MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
STYLE = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
IMPORT = ROOT / "docs/validation/companion-screen-generated-expression-sheet-import.json"
CONTACT = ROOT / "docs/validation/companion-screen-generated-expression-normal-pack-contact-sheet.json"
QUEUE = ROOT / "docs/validation/companion-screen-display-queue-generation-hygiene.json"
REFRESH = ROOT / "docs/validation/companion-screen-refresh-feel-contract.json"
RUNTIME_LOGS = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
RUNTIME_PROMOTION = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
WBA_PORT = ROOT / "docs/validation/companion-screen-wba-port-contract.json"
WBA_REAL = ROOT / "docs/validation/companion-screen-wba-real-parity-gate.json"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def build_ledger() -> dict[str, Any]:
    menu = load(MENU)
    style = load(STYLE)
    import_report = load(IMPORT)
    contact = load(CONTACT)
    queue = load(QUEUE)
    refresh = load(REFRESH)
    runtime_logs = load(RUNTIME_LOGS)
    promotion = load(RUNTIME_PROMOTION)
    wba_port = load(WBA_PORT)
    wba_real = load(WBA_REAL)

    resource_pack = menu.get("resource_pack", {})
    runtime = menu.get("runtime_evidence", {})
    queue_expectation = queue.get("scenario", {}).get("display_result_expectation", {})
    after_switch = queue.get("scenario", {}).get("after_switch", {})
    contact_coverage = contact.get("generated_coverage", {})

    candidate_revision = int(resource_pack.get("revision", 0))
    logs_pass = runtime_logs.get("status") == "PASS"
    promotion_applied = promotion.get("status") == "APPLIED"
    expected_resource_runtime_status = f"REVISION_{candidate_revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING"
    resource_runtime_promoted = (
        promotion_applied
        and runtime.get("status") == expected_resource_runtime_status
    )
    if resource_runtime_promoted:
        missing_hardware = ["human visual classification of any old marks"]
        if not logs_pass:
            missing_hardware.insert(0, "current quiet interaction-profile normal capture")
        ledger_status = RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING
        external_flash_activation = f"runtime_verified_rev{candidate_revision}_external_flash"
    elif logs_pass:
        missing_hardware = ["human visual classification of any old marks"]
        ledger_status = RUNTIME_LOGS_PASS_PROMOTION_PENDING
        external_flash_activation = f"runtime_verified_rev{candidate_revision}_external_flash"
    else:
        missing_hardware = [
            f"rev{candidate_revision} ScreenAssetProvision flash/capture",
            f"rev{candidate_revision} normal firmware restore/capture",
            "real display_result coherent_generation=1 log",
            "human visual classification of any old marks",
        ]
        ledger_status = PENDING_RUNTIME_RECHECK
        external_flash_activation = f"pending_rev{candidate_revision}_runtime_recheck"

    return {
        "schema_id": SCHEMA_ID,
        "status": ledger_status,
        "purpose": "SCR-17 release ledger proving the current screen-art candidate has a single product generation before human visual review.",
        "candidate": {
            "product": "Companion screen",
            "target_profile": "GDEY0154D67-T03 200x200 1-bit",
            "target_family": "STM32WB55 baseline; WBA55/WBA65 inherit generation hygiene",
            "cemp_revision": resource_pack.get("revision"),
            "cemp_crc32": resource_pack.get("pack_crc32"),
            "clips": resource_pack.get("clips"),
            "frames": resource_pack.get("frames"),
            "pack_bytes": resource_pack.get("total_bytes"),
            "storage": resource_pack.get("storage"),
            "runtime_status": runtime.get("status"),
        },
        "source_art_identity": {
            "style_name": style.get("style_name"),
            "expression_sheet": import_report.get("source"),
            "style_source_of_truth": import_report.get("style_source_of_truth"),
            "import_preview": import_report.get("preview"),
            "review_preview": import_report.get("review_preview"),
            "normal_pack_contact_sheet": contact.get("contact_sheet"),
            "visual_review_required": import_report.get("visual_review_required"),
            "machine_review_status": import_report.get("machine_review", {}).get("status"),
        },
        "normal_pack_generation": {
            "manifest_expression_sources": contact_coverage.get("used_by_manifest"),
            "covered_by_import": contact_coverage.get("covered_by_import"),
            "old_procedural_normal_frames_allowed": False,
            "rescue_or_maintenance_fallback_only": True,
            "contact_report": rel(CONTACT),
        },
        "activation_evidence": {
            "manifest_verified_static": True,
            "external_flash_activation": external_flash_activation,
            "active_revision_field": queue.get("contract", {}).get("active_revision_field"),
            "request_revision_field": queue.get("contract", {}).get("request_revision_field"),
            "old_queue_action": "drain_or_discard",
            "stale_queued_frames_discarded_in_model": after_switch.get("last_stale_discarded"),
            "wba_inherits_contract": queue.get("contract", {}).get("wba_inherits_contract"),
        },
        "first_frame_evidence": {
            "expected_marker": "coherent_generation=1",
            "model_active_revision": queue_expectation.get("active_revision"),
            "model_resource_revision": queue_expectation.get("resource_revision"),
            "model_coherent_generation": queue_expectation.get("coherent_generation"),
            "model_generation_switches": queue_expectation.get("generation_switches"),
            "model_last_stale_discarded": queue_expectation.get("last_stale_discarded"),
            "real_runtime_status": "PASS" if resource_runtime_promoted else runtime_logs.get("status"),
            "real_marker_present": (
                runtime_logs.get("provision", {}).get("markers", {}).get("coherent_generation=1")
                if resource_runtime_promoted
                else logs_pass
            ),
            "quiet_interaction_profile_runtime_status": runtime_logs.get("status"),
            "quiet_interaction_profile_passed": logs_pass,
        },
        "refresh_classification": {
            "interactive": refresh.get("product_rules", {}).get("interactive"),
            "maintenance": refresh.get("product_rules", {}).get("maintenance"),
            "full_refresh": refresh.get("product_rules", {}).get("full_refresh"),
            "visual_triage_classes": [
                "physical afterimage",
                "stale queued frame",
                "stale asset revision",
                "rescue/procedural fallback leakage",
                "stale_generation_content",
            ],
            "physical_afterimage_route": "panel profile, one quiet maintenance refresh, or full baseline/fault recovery",
            "software_generation_route": "product P0: resource/queue/render path fix before human acceptance",
            "product_backlog_rule": "SCR-17 stays listed as a product backlog/release item for every candidate; recognizable old art or layout is stale_generation_content until proven physical afterimage only.",
        },
        "ota_transaction_rule": {
            "ui_assets_ota_in_scope": True,
            "required_transaction_fields": [
                "resource manifest",
                "payload",
                "CRC/signature",
                "active revision",
                "display queue generation",
                "first coherent frame",
            ],
            "failure_policy": "keep previous active resource; never display a half-new/half-old generation",
        },
        "wba_portability": {
            "wba_port_contract": wba_port.get("status"),
            "wba_real_parity": wba_real.get("status"),
            "front_stable_back_compose_atomic_commit_required": True,
            "tile_compose_allowed_if_sram_limited": True,
        },
        "missing_hardware_facts": missing_hardware,
        "sources": {
            "project_plan": rel(PLAN),
            "generation_research": rel(RESEARCH),
            "menu_resource_candidate": rel(MENU),
            "generated_art_style": rel(STYLE),
            "sheet_import": rel(IMPORT),
            "normal_pack_contact": rel(CONTACT),
            "display_queue_generation_hygiene": rel(QUEUE),
            "refresh_feel_contract": rel(REFRESH),
            "runtime_recheck_logs": rel(RUNTIME_LOGS),
            "runtime_promotion": rel(RUNTIME_PROMOTION),
            "wba_port_contract": rel(WBA_PORT),
            "wba_real_parity_gate": rel(WBA_REAL),
        },
        "validation_commands": [
            "python .\\tools\\verify_screen_generation_release_ledger.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\render_generated_art_style_contract.py",
            "python .\\tools\\render_generated_expression_normal_pack_contact_sheet.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_wba_real_parity_gate.py",
        ],
    }


def check_ledger(ledger: dict[str, Any], errors: list[str]) -> None:
    if ledger.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    runtime_logs = load(RUNTIME_LOGS)
    promotion = load(RUNTIME_PROMOTION)
    logs_pass = runtime_logs.get("status") == "PASS"
    promotion_applied = promotion.get("status") == "APPLIED"
    candidate = ledger.get("candidate", {})
    menu = load(MENU)
    resource_pack = menu.get("resource_pack", {})
    runtime = menu.get("runtime_evidence", {})
    revision = resource_pack.get("revision")
    crc32 = resource_pack.get("pack_crc32")
    expected_resource_runtime_status = f"REVISION_{revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING"
    resource_runtime_promoted = (
        promotion_applied
        and runtime.get("status") == expected_resource_runtime_status
    )
    expected_ledger_status = (
        RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING
        if resource_runtime_promoted
        else RUNTIME_LOGS_PASS_PROMOTION_PENDING
        if logs_pass
        else PENDING_RUNTIME_RECHECK
    )
    if ledger.get("status") != expected_ledger_status:
        errors.append(f"ledger status must be {expected_ledger_status}")
    if candidate.get("cemp_revision") != revision:
        errors.append("candidate CEMP revision must match the active menu resource")
    if candidate.get("cemp_crc32") != crc32:
        errors.append("candidate CEMP CRC must match the active menu resource")
    if candidate.get("storage") != "external ui_assets at 0x00200000":
        errors.append("candidate storage must remain external ui_assets")
    expected_runtime_status = (
        expected_resource_runtime_status
        if promotion_applied
        else f"REVISION_{revision}_RUNTIME_RECHECK_PENDING"
    )
    if candidate.get("runtime_status") != expected_runtime_status:
        errors.append(f"candidate runtime status must be {expected_runtime_status}")

    source_art = ledger.get("source_art_identity", {})
    if source_art.get("style_name") != "genref_sheet_12_inner_faces_v5":
        errors.append("source art style name drifted")
    if source_art.get("expression_sheet") != "docs/art/generated_pet_expression_sheet_v5.png":
        errors.append("ledger must reference generated_pet_expression_sheet_v5.png")
    if source_art.get("visual_review_required") is not True:
        errors.append("ledger must require visual review of imported art")
    if source_art.get("machine_review_status") != "PASS":
        errors.append("import machine review must be PASS")

    normal_pack = ledger.get("normal_pack_generation", {})
    if normal_pack.get("manifest_expression_sources") != 39:
        errors.append("normal pack must keep 39 manifest expression sources")
    if normal_pack.get("covered_by_import") != 39:
        errors.append("normal pack must keep 39 generated-import-covered sources")
    if normal_pack.get("old_procedural_normal_frames_allowed") is not False:
        errors.append("old procedural normal product frames must not be allowed")
    if normal_pack.get("rescue_or_maintenance_fallback_only") is not True:
        errors.append("fallback must be rescue/maintenance only")

    activation = ledger.get("activation_evidence", {})
    expected_activation = (
        f"runtime_verified_rev{revision}_external_flash"
        if resource_runtime_promoted or logs_pass
        else f"pending_rev{revision}_runtime_recheck"
    )
    if activation.get("external_flash_activation") != expected_activation:
        errors.append(f"candidate external flash activation must be {expected_activation}")
    if activation.get("old_queue_action") != "drain_or_discard":
        errors.append("old queue action must be drain_or_discard")
    if activation.get("stale_queued_frames_discarded_in_model") != 3:
        errors.append("model must prove three stale queued frames discarded")
    if activation.get("wba_inherits_contract") is not True:
        errors.append("WBA must inherit the generation hygiene contract")

    first = ledger.get("first_frame_evidence", {})
    if first.get("expected_marker") != "coherent_generation=1":
        errors.append("first-frame marker must be coherent_generation=1")
    model_active_revision = first.get("model_active_revision")
    model_resource_revision = first.get("model_resource_revision")
    if not isinstance(model_active_revision, int) or model_active_revision <= 0:
        errors.append("model active revision must be positive")
    if model_resource_revision != model_active_revision:
        errors.append("model resource revision must match the simulated active revision")
    if first.get("model_coherent_generation") != 1:
        errors.append("model first frame must be coherent")
    expected_first_runtime_status = "PASS" if resource_runtime_promoted else runtime_logs.get("status")
    if first.get("real_runtime_status") != expected_first_runtime_status:
        errors.append("real coherent marker runtime status must preserve the resource-runtime evidence")
    expected_real_marker = (
        runtime_logs.get("provision", {}).get("markers", {}).get("coherent_generation=1")
        if resource_runtime_promoted
        else logs_pass
    )
    if first.get("real_marker_present") is not expected_real_marker:
        errors.append("real coherent marker must match the resource-runtime evidence")
    if first.get("quiet_interaction_profile_runtime_status") != runtime_logs.get("status"):
        errors.append("quiet interaction-profile status must match the runtime log verifier")
    if first.get("quiet_interaction_profile_passed") is not logs_pass:
        errors.append("quiet interaction-profile pass result must match the runtime log verifier")

    refresh = ledger.get("refresh_classification", {})
    classes = set(refresh.get("visual_triage_classes", []))
    for item in (
        "physical afterimage",
        "stale queued frame",
        "stale asset revision",
        "rescue/procedural fallback leakage",
        "stale_generation_content",
    ):
        if item not in classes:
            errors.append(f"missing visual triage class {item}")
    if "product backlog/release item" not in str(refresh.get("product_backlog_rule", "")):
        errors.append("refresh classification must carry SCR-17 product backlog rule")

    ota = ledger.get("ota_transaction_rule", {})
    if ota.get("ui_assets_ota_in_scope") is not True:
        errors.append("ui_assets OTA must be in SCR-17 transaction scope")
    for item in ("resource manifest", "payload", "CRC/signature", "active revision", "display queue generation", "first coherent frame"):
        if item not in ota.get("required_transaction_fields", []):
            errors.append(f"OTA transaction rule missing {item}")
    if "never display a half-new/half-old generation" not in str(ota.get("failure_policy", "")):
        errors.append("OTA failure policy must forbid half-new/half-old display")

    wba = ledger.get("wba_portability", {})
    if wba.get("front_stable_back_compose_atomic_commit_required") is not True:
        errors.append("WBA portability must require front-stable/back-compose/atomic-commit semantics")
    if wba.get("tile_compose_allowed_if_sram_limited") is not True:
        errors.append("WBA portability must allow tile composition under SRAM limits")

    missing = set(ledger.get("missing_hardware_facts", []))
    required_missing = ["human visual classification of any old marks"]
    if resource_runtime_promoted and not logs_pass:
        required_missing.insert(0, "current quiet interaction-profile normal capture")
    elif not logs_pass:
        required_missing = [
            f"rev{revision} ScreenAssetProvision flash/capture",
            f"rev{revision} normal firmware restore/capture",
            "real display_result coherent_generation=1 log",
            *required_missing,
        ]
    for item in required_missing:
        if item not in missing:
            errors.append(f"missing hardware fact not tracked: {item}")

    plan = read(PLAN)
    research = read(RESEARCH)
    for token in ("release ledger", "新旧画面交织防回退", "coherent_generation=1", "资源 manifest", "产品 backlog/release item", "stale_generation_content"):
        if token not in plan:
            errors.append(f"project plan missing token {token}")
    for token in ("Release ledger entry required", "Source art identity", "First-frame evidence", "Human/visual note", "product backlog item", "stale_generation_content"):
        if token not in research:
            errors.append(f"generation research missing token {token}")

    sources = ledger.get("sources", {})
    for path in (PLAN, RESEARCH, MENU, STYLE, IMPORT, CONTACT, QUEUE, REFRESH, RUNTIME_LOGS, RUNTIME_PROMOTION, WBA_PORT, WBA_REAL):
        if rel(path) not in sources.values():
            errors.append(f"ledger sources must include {rel(path)}")

    commands = set(ledger.get("validation_commands", []))
    for command in (
        "python .\\tools\\verify_screen_generation_release_ledger.py",
        "python .\\tools\\verify_display_queue_generation_hygiene.py",
        "python .\\tools\\verify_screen_refresh_feel_contract.py",
        "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
    ):
        if command not in commands:
            errors.append(f"ledger validation commands missing {command}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    output = args.json if args.json.is_absolute() else ROOT / args.json
    ledger = build_ledger()
    errors: list[str] = []
    check_ledger(ledger, errors)

    rendered = json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not output.exists():
            errors.append(f"missing {rel(output)}")
        elif output.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(output)}; rerun with --write")

    if errors:
        print("FAIL: screen generation release ledger checks failed", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: screen generation release ledger verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
