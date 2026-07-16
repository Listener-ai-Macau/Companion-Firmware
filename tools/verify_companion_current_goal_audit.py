#!/usr/bin/env python3
"""Keep the active Companion Goal boundary auditable without hardware access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
DEFAULT_MD = ROOT / "docs/validation/companion-current-goal-audit-20260717.md"

ARTIFACTS = {
    "historical": ROOT / "docs/validation/companion-historical-branch-audit-20260717.json",
    "low_power": ROOT / "docs/validation/companion-low-power-requirements.json",
    "wb55_build_receipt": ROOT / "docs/validation/companion-wb55-current-build-receipt-20260717.json",
    "wba_m33_compile": ROOT / "docs/validation/companion-screen-wba-adapter-m33-compile.json",
    "wba_spi_nor": ROOT / "docs/validation/companion-wba-spi-nor-adapter.json",
    "v9_baseline": ROOT / "docs/art/iterations/companion-pet-expression-v9/baseline-lock.json",
    "v9_cemp": ROOT / "docs/validation/companion-v9-expression-cemp-20260716.json",
    "v9_coverage": ROOT / "docs/validation/companion-v9-scene-coverage-20260716.json",
    "v9_binding": ROOT / "docs/validation/companion-v9-candidate-resource-binding-20260717.json",
    "menu_source": ROOT / "docs/validation/companion-menu-v6-source-review-20260717.json",
    "menu_localization": ROOT / "docs/validation/companion-menu-v6-localization-preview-20260717.json",
    "special_system": ROOT / "docs/validation/companion-pet-special-system-source-review-20260717.json",
    "special_journey": ROOT / "docs/validation/companion-pet-special-journey-source-review-20260717.json",
    "special_mapping": ROOT / "docs/validation/companion-pending-special-source-mapping-20260717.json",
    "visual_readiness": ROOT / "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json",
    "wba_boundary": ROOT / "docs/validation/companion-v9-wba-visual-boundary-20260717.json",
    "waveform_freeze": ROOT / "docs/companion_ssd1681_vendor_waveform_freeze.md",
}

V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
MENU_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
SYSTEM_SHA256 = "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82"
JOURNEY_SHA256 = "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(name: str) -> dict[str, Any]:
    path = ARTIFACTS[name]
    return json.loads(path.read_text(encoding="utf-8"))


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def evidence(name: str, status: str, detail: str) -> dict[str, str]:
    return {"path": rel(ARTIFACTS[name]), "status": status, "detail": detail}


def build_audit() -> dict[str, Any]:
    errors: list[str] = []
    historical = load_json("historical")
    low_power = load_json("low_power")
    wb55_build_receipt = load_json("wb55_build_receipt")
    wba_m33_compile = load_json("wba_m33_compile")
    wba_spi_nor = load_json("wba_spi_nor")
    baseline = load_json("v9_baseline")
    cemp = load_json("v9_cemp")
    coverage = load_json("v9_coverage")
    binding = load_json("v9_binding")
    menu_source = load_json("menu_source")
    menu_localization = load_json("menu_localization")
    special_system = load_json("special_system")
    special_journey = load_json("special_journey")
    special_mapping = load_json("special_mapping")
    visual_readiness = load_json("visual_readiness")
    wba_boundary = load_json("wba_boundary")
    waveform_freeze = ARTIFACTS["waveform_freeze"].read_text(encoding="utf-8")
    waveform_freeze_normalized = waveform_freeze.lower()

    check(errors, historical.get("status") == "PASS_PRESERVED_AND_CLASSIFIED", "historical branches are not classified")
    protections = historical.get("current_main_protections", {})
    for key in (
        "double_tap_only_recording_menu_policy",
        "first_tap_blocks_stop_until_double_tap_decision",
        "rejected_renderable_art_stays_retired",
        "three_minute_idle_default",
    ):
        check(errors, protections.get(key) is True, f"historical protection missing: {key}")

    check(errors, low_power.get("status") == "PASS", "low-power static contract is not PASS")
    check(errors, low_power.get("target") == "final product-board LP-01 standby average <= 1 mA over >= 60 s", "low-power target drifted")
    check(errors, "3-minute" in str(low_power.get("low_power_visual")), "three-minute sleepy policy drifted")

    check(errors, wb55_build_receipt.get("status") == "PASS_CURRENT_SOURCE_BUILD_NO_HARDWARE", "current WB55 build receipt is not PASS")
    build_commit = wb55_build_receipt.get("source_commit", "")
    check(errors, isinstance(build_commit, str) and len(build_commit) == 40, "current WB55 build receipt has no full source commit")
    for name in ("dry_run_default", "ssd1681_real_panel", "screen_asset_provision"):
        variant = wb55_build_receipt.get("variants", {}).get(name, {})
        check(errors, variant.get("returncode") == 0, f"current WB55 build variant failed: {name}")
        check(errors, isinstance(variant.get("size", {}).get("dec"), int), f"current WB55 build variant has no size: {name}")
    check(errors, wba_m33_compile.get("status") == "PASS_STATIC_M33_COMPILE_CONTRACT", "WBA Cortex-M33 adapter compile is not PASS")
    wba_claims = wba_m33_compile.get("claims", {})
    check(errors, wba_claims.get("cube_wba_project_claimed") is False and wba_claims.get("wba_hardware_parity_claimed") is False, "WBA compile evidence overclaims target parity")
    check(errors, wba_spi_nor.get("status") == "PASS_NATIVE_BEHAVIOR_AND_PORTABLE_CONTRACT", "WBA SPI-NOR contract is not PASS")
    wba_targets = wba_spi_nor.get("targets", {})
    check(errors, wba_targets.get("transport") == "spi_nor_1_1_1" and wba_targets.get("hardware_parity_claimed") is False, "WBA SPI-NOR transport boundary drifted")

    accepted_source = baseline.get("accepted_source", {})
    check(errors, baseline.get("status") == "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED", "v9 baseline is not owner locked")
    check(errors, accepted_source.get("sha256") == V9_SHA256, "v9 source hash drifted")
    check(errors, baseline.get("machine_candidate_scope", {}).get("forbidden") is not None, "v9 machine-only boundary missing")

    check(errors, cemp.get("status") == "PASS_MACHINE_ONLY_CEMP_NOT_ACTIVATED", "v9 CEMP evidence is not machine-only PASS")
    check(errors, cemp.get("frame_count") == 39 and cemp.get("clip_count") == 13, "v9 CEMP frame coverage drifted")
    for key in ("runtime_resource_activated", "external_flash_provisioned", "firmware_flashed", "physical_or_owner_visual_pass"):
        check(errors, cemp.get(key) is False, f"v9 CEMP boundary drifted: {key}")

    check(errors, coverage.get("status") == "PASS_MACHINE_ONLY_NO_LEGACY_FALLBACK", "v9 no-fallback coverage is not PASS")
    check(errors, coverage.get("portable_resource_family_count") == 40, "scene family count drifted")
    check(errors, coverage.get("candidate_mapping_count") == 18 and coverage.get("pending_no_fallback_count") == 22, "scene mapping boundary drifted")
    check(errors, binding.get("status") == "PASS_MACHINE_ONLY_INACTIVE", "v9 selector is not inactive machine-only PASS")
    check(errors, binding.get("candidate_pack", {}).get("runtime_resource_activated") is False, "v9 selector permits runtime activation")

    for name, data, expected_sha in (
        ("menu_source", menu_source, MENU_SHA256),
        ("menu_localization", menu_localization, MENU_SHA256),
        ("special_system", special_system, SYSTEM_SHA256),
        ("special_journey", special_journey, JOURNEY_SHA256),
    ):
        check(errors, data.get("status") == "PASS_MACHINE_PREVIEW_PENDING_OWNER" or name == "menu_localization" and data.get("status") == "PASS_MACHINE_LOCALIZATION_PREVIEW_PENDING_OWNER", f"{name} preview status drifted")
        source_sha = json.dumps(data, sort_keys=True)
        check(errors, expected_sha in source_sha, f"{name} source hash missing")

    check(errors, special_mapping.get("status") == "PASS_EXACT_PENDING_SOURCE_MAPPING_NO_RUNTIME", "special scene mapping is not pending/no-runtime PASS")
    check(errors, special_mapping.get("mapped_family_count") == 22 and special_mapping.get("pending_family_count") == 22, "special scene mapping count drifted")
    mapping_boundary = special_mapping.get("runtime_boundary", {})
    for key in ("cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass", "pbm_imported"):
        check(errors, mapping_boundary.get(key) is False, f"special scene activation boundary drifted: {key}")

    check(errors, visual_readiness.get("status") == "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW", "visual review readiness is not PASS")
    readiness_items = visual_readiness.get("items", [])
    check(errors, len(readiness_items) == 3, "visual review must retain exactly three sequential items")
    check(errors, {item.get("source_sha256") for item in readiness_items} == {MENU_SHA256, SYSTEM_SHA256, JOURNEY_SHA256}, "visual review source hashes drifted")

    check(errors, wba_boundary.get("status") == "PASS_V9_WBA_VISUAL_BOUNDARY_PENDING_OWNER", "WBA visual boundary is not PASS")
    wba_resource = wba_boundary.get("wba_resource_boundary", {})
    check(errors, wba_resource.get("runtime_activation_allowed") is False, "WBA resource activation is enabled")
    check(errors, wba_resource.get("storage") == "external CEMP through callback-only external NOR adapter", "WBA external resource boundary drifted")
    check(errors, wba_resource.get("transport") == "ordinary 1-1-1 SPI NOR", "WBA SPI-NOR boundary drifted")

    for token in ("frozen", "cwf1", "gdey0154d67-t03", "do not use generic", "no panel command"):
        check(errors, token in waveform_freeze_normalized, f"vendor waveform freeze document missing: {token}")

    requirements = [
        {
            "id": "historical_behavior_protection",
            "status": "proved_machine",
            "requirement": "Historical branches remain protected and only their classified double-tap, first-tap Stop blocker, three-minute idle and external-resource evidence are current behavior inputs.",
            "evidence": [evidence("historical", str(historical.get("status")), "No bulk merge; protected branch tips and useful behavior classification are verified.")],
        },
        {
            "id": "touch_low_power_policy",
            "status": "proved_machine_hardware_current_pending",
            "requirement": "Daily double tap is the only manual recording start/stop; first tap blocks Stop, and the visible sleepy transition defaults to three minutes.",
            "evidence": [evidence("low_power", str(low_power.get("status")), "HAL-free policy passes; Stop wake and <=1 mA physical measurement remain hardware gates.")],
        },
        {
            "id": "current_wb55_build_and_wba_adapter",
            "status": "proved_machine_real_wba_pending",
            "requirement": "The current WB55 source builds in dry-run, real SSD1681 and asset-provision variants; WBA55/WBA65 callback adapters compile as Cortex-M33 and preserve ordinary SPI-NOR behavior without claiming a real WBA board.",
            "evidence": [
                evidence("wb55_build_receipt", str(wb55_build_receipt.get("status")), f"Three WB55 variants built from source commit {build_commit}; the receipt invalidates when listed build inputs change."),
                evidence("wba_m33_compile", str(wba_m33_compile.get("status")), "Eight callback-only target adapters compile with strict Cortex-M33 flags."),
                evidence("wba_spi_nor", str(wba_spi_nor.get("status")), "Ordinary 1-1-1 SPI NOR behavior passes without WBA hardware parity claim."),
            ],
        },
        {
            "id": "v9_expression_renderer",
            "status": "proved_machine_inactive",
            "requirement": "Only the owner-approved v9 inner-face sheet supplies the 39-frame, 13-clip renderer-first candidate; no retired or procedural visual fallback is allowed.",
            "evidence": [
                evidence("v9_baseline", str(baseline.get("status")), "Locked v9 source hash is the sole current inner-face baseline."),
                evidence("v9_cemp", str(cemp.get("status")), "39/39 PBM-to-CEMP decode comparison passes without activation."),
                evidence("v9_coverage", str(coverage.get("status")), "40 scene families are explicit: 18 available candidates and 22 no-fallback pending sources."),
                evidence("v9_binding", str(binding.get("status")), "Portable selector remains AVAILABLE_NOT_ACTIVE."),
            ],
        },
        {
            "id": "four_root_menu_and_special_scene_sources",
            "status": "machine_previews_pass_owner_decision_pending",
            "requirement": "The four-root bilingual menu and both special-scene sheets have deterministic previews only; source approval must precede PBM/CEMP import or runtime activation.",
            "evidence": [
                evidence("menu_source", str(menu_source.get("status")), "Four-root layout source is pending owner decision."),
                evidence("menu_localization", str(menu_localization.get("status")), "English and zh-CN overlays are deterministic previews."),
                evidence("special_system", str(special_system.get("status")), "System sheet is pending owner decision."),
                evidence("special_journey", str(special_journey.get("status")), "Journey sheet is pending owner decision."),
                evidence("special_mapping", str(special_mapping.get("status")), "All 22 uncovered families map to exact pending sources with no fallback."),
                evidence("visual_readiness", str(visual_readiness.get("status")), "Three sequential Chinese owner-review items are prepared but not opened."),
            ],
        },
        {
            "id": "wba_resource_portability",
            "status": "pre_port_proved_real_wba_pending",
            "requirement": "WBA55/WBA65 adapters accept only v9-era external CEMP over callback-only ordinary SPI NOR; no WBA visual or panel parity is claimed.",
            "evidence": [evidence("wba_boundary", str(wba_boundary.get("status")), "WBA target boundary forbids retired visual inputs and runtime activation.")],
        },
        {
            "id": "ssd1681_waveform_freeze",
            "status": "frozen_waiting_vendor_evidence",
            "requirement": "No generic, adjacent-panel or guessed SSD1681 LUT may be tried. A candidate requires a matching CWF1 vendor package before a bounded hardware session.",
            "evidence": [evidence("waveform_freeze", "FROZEN", "Vendor package requirements and fail-closed parser boundary are recorded; no panel command is authorized.")],
        },
    ]

    return {
        "schema": "companion.current_goal_audit.v1",
        "status": "GOAL_ACTIVE_MACHINE_BOUNDARY_PROVED_OWNER_AND_HARDWARE_PENDING" if not errors else "GOAL_AUDIT_INVALID",
        "active_goal_boundary": "Only current v9/companion-menu-v6-four-root sources may be considered; historical v5/v6/v7/v8/v10+ art and six-root menus are not active inputs.",
        "daily_visual_validation": "deterministic source/PBM/CEMP/render evidence; camera is final physical preflight only, never daily art development",
        "requirements": requirements,
        "open_gates": [
            "three sequential owner visual decisions: menu-v6-four-root, special-system-v1, special-journey-v1",
            "separate approved-source PBM/CEMP import and runtime activation proposal",
            "WB55 FTS02/panel recovery, real touch/Stop/current and physical visual acceptance",
            "real WBA project, board and panel/resource parity",
            "matching vendor CWF1 waveform package before any new waveform candidate",
        ],
        "errors": errors,
        "validation_commands": [
            "python .\\tools\\verify_companion_current_goal_audit.py",
            "pwsh .\\tools\\test_companion_v9_expression_render_pipeline.ps1",
            "python .\\tools\\verify_companion_v9_wba_visual_boundary.py",
            "python .\\tools\\verify_companion_historical_branch_audit.py",
            "python .\\tools\\verify_companion_low_power_requirements.py",
            "pwsh .\\tools\\test_power_policy_host.ps1",
            "python .\\tools\\capture_wb55_current_build_receipt.py",
            "python .\\tools\\verify_wba_adapter_m33_compile.py --self-test",
            "python .\\tools\\verify_wba_spi_nor_adapter.py --self-test",
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Companion Current Goal Audit",
        "",
        "Generated by `python .\\tools\\verify_companion_current_goal_audit.py --write`.",
        "",
        f"- Status: `{audit['status']}`",
        f"- Current visual boundary: {audit['active_goal_boundary']}",
        f"- Daily visual validation: {audit['daily_visual_validation']}",
        "",
        "## Current Requirements",
        "",
    ]
    for requirement in audit["requirements"]:
        lines.extend((
            f"### {requirement['id']}",
            "",
            f"- Status: `{requirement['status']}`",
            f"- Requirement: {requirement['requirement']}",
            "- Evidence:",
        ))
        for item in requirement["evidence"]:
            lines.append(f"  - `{item['path']}`: `{item['status']}` - {item['detail']}")
        lines.append("")
    lines.extend(("## Open Gates", ""))
    lines.extend(f"- {item}" for item in audit["open_gates"])
    lines.extend(("", "## Validation Commands", ""))
    lines.extend(f"- `{command}`" for command in audit["validation_commands"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    rendered_json = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_md = render_markdown(audit)
    errors = list(audit["errors"])

    if args.write:
        DEFAULT_JSON.write_text(rendered_json, encoding="utf-8")
        DEFAULT_MD.write_text(rendered_md, encoding="utf-8")
    else:
        for path, expected in ((DEFAULT_JSON, rendered_json), (DEFAULT_MD, rendered_md)):
            if not path.exists():
                errors.append(f"missing {rel(path)}")
            elif path.read_text(encoding="utf-8") != expected:
                errors.append(f"stale {rel(path)}")

    if errors:
        print("FAIL: current Companion Goal audit checks failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PASS: current Companion Goal audit -> {rel(DEFAULT_JSON)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
