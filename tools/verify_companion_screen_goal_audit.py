#!/usr/bin/env python3
"""Verify the current Companion screen goal completion audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-goal-audit.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-goal-audit.md"
BILINGUAL_MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
TOUCH_PACKET = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"
TOUCH_REVIEW_TEMPLATE = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.json"
TOUCH_REVIEW_RECORD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-record.json"
RUNTIME_ACTION_CARD = ROOT / "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json"
RUNTIME_FLASH_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-flash-preflight.json"
RUNTIME_SERIAL_CAPTURE_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json"
PRE_ACCEPTANCE_HEALTH = ROOT / "docs/validation/companion-screen-pre-acceptance-health.json"
ACCEPTANCE_INDEX = ROOT / "docs/validation/companion-screen-acceptance-index.json"
RUNTIME_RECHECK_RUNNER = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-runner.json"
RUNTIME_RECHECK_LOGS = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
RUNTIME_PROMOTION = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
PANEL_GATE = ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
WB55_BUILD_MATRIX = ROOT / "docs/validation/companion-screen-wb55-build-matrix.json"
WBA_PORT = ROOT / "docs/validation/companion-screen-wba-port-contract.json"
WBA_CUBE_DEPENDENCY = ROOT / "docs/validation/companion-screen-wba-cube-dependency-preflight.json"
WBA_REAL_PARITY = ROOT / "docs/validation/companion-screen-wba-real-parity-gate.json"
WBA_LSE_CLOCK = ROOT / "docs/validation/companion-screen-wba-lse-clock-contract.json"
WBA_PET_BEHAVIOR_USER_DATA = ROOT / "docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json"
RESOURCE_POLICY = ROOT / "docs/validation/companion-screen-resource-memory-policy.json"
GENERATED_STYLE = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
PREMIUM_ART = ROOT / "docs/validation/companion-screen-premium-pet-art-contract.json"
REFRESH_FEEL = ROOT / "docs/validation/companion-screen-refresh-feel-contract.json"
DISPLAY_QUEUE_GENERATION_HYGIENE = ROOT / "docs/validation/companion-screen-display-queue-generation-hygiene.json"
GENERATION_RELEASE_LEDGER = ROOT / "docs/validation/companion-screen-generation-release-ledger.json"
MENU_DRAG = ROOT / "docs/validation/companion-screen-menu-drag-continuity-contract.json"
PRESENTATION = ROOT / "docs/validation/companion-screen-presentation-wb55.json"
TOUCH_FT6336 = ROOT / "docs/validation/companion-screen-touch-ft6336-wb55.json"
INTERACTION_PROFILE_RUNTIME_GATE = ROOT / "docs/validation/companion-interaction-profile-runtime-gate-20260714.md"
SCHEMA_ID = "companion.pendant.screen_goal_audit.v1"
CANDIDATE = current_candidate()
RUNTIME_GATE_ID = f"wb55_rev{CANDIDATE.revision}_runtime_recheck"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence(path: pathlib.Path, status: str, summary: str) -> dict[str, str]:
    return {
        "path": rel(path),
        "status": status,
        "summary": summary,
    }


def build_audit() -> dict[str, Any]:
    menu = load_json(BILINGUAL_MENU)
    touch_packet = load_json(TOUCH_PACKET)
    touch_review_template = load_json(TOUCH_REVIEW_TEMPLATE)
    touch_review_record = load_json(TOUCH_REVIEW_RECORD)
    runtime_action_card = load_json(RUNTIME_ACTION_CARD)
    runtime_flash_preflight = load_json(RUNTIME_FLASH_PREFLIGHT)
    runtime_serial_capture_preflight = load_json(RUNTIME_SERIAL_CAPTURE_PREFLIGHT)
    pre_acceptance = load_json(PRE_ACCEPTANCE_HEALTH)
    acceptance_index = load_json(ACCEPTANCE_INDEX)
    runtime_recheck_runner = load_json(RUNTIME_RECHECK_RUNNER)
    runtime_recheck_logs = load_json(RUNTIME_RECHECK_LOGS)
    runtime_promotion = load_json(RUNTIME_PROMOTION)
    panel_gate = load_json(PANEL_GATE)
    wb55_build_matrix = load_json(WB55_BUILD_MATRIX)
    wba_port = load_json(WBA_PORT)
    wba_cube_dependency = load_json(WBA_CUBE_DEPENDENCY)
    wba_real_parity = load_json(WBA_REAL_PARITY)
    wba_lse_clock = load_json(WBA_LSE_CLOCK)
    wba_pet_behavior_user_data = load_json(WBA_PET_BEHAVIOR_USER_DATA)
    resource_policy = load_json(RESOURCE_POLICY)
    generated_style = load_json(GENERATED_STYLE)
    premium_art = load_json(PREMIUM_ART)
    refresh_feel = load_json(REFRESH_FEEL)
    generation_hygiene = load_json(DISPLAY_QUEUE_GENERATION_HYGIENE)
    generation_ledger = load_json(GENERATION_RELEASE_LEDGER)
    menu_drag = load_json(MENU_DRAG)
    presentation = load_json(PRESENTATION)
    touch_ft6336 = load_json(TOUCH_FT6336)

    runtime = menu.get("runtime_evidence", {})
    machine_state = touch_packet.get("machine_state", {})
    interaction_profile = machine_state.get("interaction_profile", {})
    interaction_profile_status = str(interaction_profile.get("status", ""))
    resource_pack = menu.get("resource_pack", {})
    wb55_real = resource_policy.get("wb55_real_evidence", {})
    candidate_pack = resource_policy.get("candidate_pack", {})
    runtime_status = str(runtime.get("status", ""))
    runtime_pending = runtime_status.endswith("_RUNTIME_RECHECK_PENDING")
    promotion_status = str(runtime_promotion.get("status", ""))

    requirements = [
        {
            "id": "wb55_physical_wiring_and_panel_identity",
            "status": "proved",
            "requirement": "NUCLEO-WB55RG drives the physical GDEY0154D67-T03 panel with verified SSD1681 wiring.",
            "evidence": [
                evidence(PANEL_GATE, str(panel_gate.get("status")), "controller, panel, voltage, DC/RST/BUSY, full/partial/maintenance refresh, orientation, and contact evidence are recorded"),
            ],
        },
        {
            "id": "current_external_resource_runtime",
            "status": "proved" if not runtime_pending else "pending_hardware_recheck",
            "requirement": "The normal WB55 firmware uses external ui_assets for the current expression/menu art pack.",
            "evidence": [
                evidence(BILINGUAL_MENU, str(menu.get("status")), f"revision {resource_pack.get('revision')} CEMP pack metadata is current; runtime_status={runtime_status}"),
                evidence(
                    ROOT / str(runtime.get("normal_raw_log")),
                    "PASS" if not runtime_pending else "LAST_PROVEN_PREVIOUS_REVISION",
                    (
                        f"normal boot log contains mount=ok, revision={resource_pack.get('revision')}, source=external_flash, and full refresh completion"
                        if not runtime_pending else
                        f"last proven normal boot remains revision={wb55_real.get('revision')}; current revision={resource_pack.get('revision')} awaits provision/normal runtime recheck"
                    ),
                ),
            ],
        },
        {
            "id": "generated_pet_and_menu_art_baseline",
            "status": "proved",
            "requirement": "Normal product expression/menu art follows the generated-image baseline, keeps the cat outline in the physical shell, and prevents regressions to eye-only or legacy procedural faces.",
            "evidence": [
                evidence(
                    GENERATED_STYLE,
                    str(generated_style.get("status")),
                    f"style={generated_style.get('style_name')} marks generated reference as source of truth and limits legacy procedural faces to rescue/maintenance fallback",
                ),
                evidence(
                    PREMIUM_ART,
                    str(premium_art.get("status")),
                    f"{premium_art.get('pose_count')} generated-baseline poses move multiple inner-face zones including mouth/nose with zero shell-owned outer-margin pixels",
                ),
            ],
        },
        {
            "id": "generated_art_handoff_and_refresh_feel_regression_guard",
            "status": "proved",
            "requirement": "Product rules prevent mixed old/new expression art and prevent e-paper ghosting fixes from regressing into repeated full-screen flicker during touch.",
            "evidence": [
                evidence(
                    GENERATED_STYLE,
                    str(generated_style.get("status")),
                    "normal pack contact sheet proves every normal expression source is generated-sheet-derived; old procedural art is not allowed in the normal product pack",
                ),
                evidence(
                    REFRESH_FEEL,
                    str(refresh_feel.get("status")),
                    "SCR-16 contract keeps 0xFC differential interaction, latest-frame menu coalescing, one 0xCF quiet maintenance pass after touch settles, and 0xF7 only for baseline/fault recovery",
                ),
                evidence(
                    DISPLAY_QUEUE_GENERATION_HYGIENE,
                    str(generation_hygiene.get("status")),
                    "SCR-17 separates physical e-paper afterimage from stale queued frames by atomically switching active_resource_revision, draining stale requests, and requiring coherent_generation on the first visible result",
                ),
                evidence(
                    GENERATION_RELEASE_LEDGER,
                    str(generation_ledger.get("status")),
                    f"SCR-17 release ledger records source art, CEMP revision/CRC, external Flash activation status, stale-discard model, first-frame coherent marker, refresh classification, OTA transaction rule, and pending rev{CANDIDATE.revision} runtime facts",
                ),
            ],
        },
        {
            "id": "screen_refresh_touch_machine_health",
            "status": "proved" if not runtime_pending and interaction_profile_status == "PASS" else "pending_hardware_recheck",
            "requirement": "WB55 machine logs prove refresh path, FT6336 identity/health, and the quiet interaction profile before human visual acceptance.",
            "evidence": [
                evidence(
                    ROOT / str(runtime.get("normal_raw_log")),
                    "PASS" if not runtime_pending else "LAST_PROVEN_PREVIOUS_REVISION",
                    "normal boot log includes refresh complete and touch-health identity addr=0x38 cipher=0x64 fw=0x01 chip=0x11" if not runtime_pending else f"rev{resource_pack.get('revision')} refresh/touch runtime evidence is pending; rev{wb55_real.get('revision')} remains last proven",
                ),
                evidence(
                    RUNTIME_RECHECK_LOGS,
                    str(runtime_recheck_logs.get("status")),
                    f"current rev{CANDIDATE.revision} machine health depends on provision and normal runtime logs; pending status keeps this requirement in hardware recheck instead of relying on earlier history",
                ),
                evidence(
                    INTERACTION_PROFILE_RUNTIME_GATE,
                    interaction_profile_status,
                    "the reset-bounded normal capture must contain the complete quiet interaction boot marker; older resource-only logs do not prove the latency candidate",
                ),
                evidence(TOUCH_PACKET, str(touch_packet.get("status")), "operator packet links the current resource state; it does not claim human visual acceptance"),
                evidence(REFRESH_FEEL, str(refresh_feel.get("status")), f"static refresh-feel contract is PASS; real rev{CANDIDATE.revision} touch/flicker/ghosting feel remains a pending hardware recheck"),
            ],
        },
        {
            "id": "wb55_screen_firmware_build_matrix",
            "status": "proved",
            "requirement": "WB55 screen firmware keeps default dry-run, SSD1681 real-panel, and ScreenAssetProvision external ui_assets build variants compilable before any hardware acceptance is requested.",
            "evidence": [
                evidence(
                    WB55_BUILD_MATRIX,
                    str(wb55_build_matrix.get("status")),
                    "build matrix proves the default dry-run build excludes SSD1681 transport, the explicit real-panel build includes panel_target_stm32wb_ssd1681.c and resource-generation queue diagnostics, and the ScreenAssetProvision build links the current external CEMP provision image",
                ),
            ],
        },
        {
            "id": "touch_menu_interaction_machine_contract",
            "status": "proved",
            "requirement": "Portable touch/menu logic preserves any-position 3 s menu entry, daily tap/swipe pet reactions, the menu-v3 static six-row home, row press-cue, and left-edge right-swipe back/exit before subjective human feel review.",
            "evidence": [
                evidence(
                    MENU_DRAG,
                    str(menu_drag.get("status")),
                    f"{menu_drag.get('frame_count_per_language')} source-layout home frame per language keeps six visible rows and a black selected row while excluding legacy numbered scroll frames",
                ),
                evidence(
                    PRESENTATION,
                    "PASS_STATIC_CURRENT_CODE",
                    "screen_presentation verifier proves any-position long_press entry, pet-only daily swipes, static-home row handling, row press-cue, and left-edge swipe-right navigation",
                ),
                evidence(
                    TOUCH_FT6336,
                    "PASS_STATIC_CURRENT_CODE",
                    f"gesture contract keeps {touch_ft6336.get('gesture_contract', {}).get('daily_enter_menu')} and {touch_ft6336.get('gesture_contract', {}).get('home_vertical_stroke')}",
                ),
            ],
        },
        {
            "id": "daily_pet_and_menu_human_feel",
            "status": "pending_human",
            "requirement": "Human confirms daily tap/swipe pet reactions, 3 s hold menu entry, static menu-home vertical strokes, press-cue, language switching, residual/flicker, and premium pet feel on the real panel.",
            "evidence": [
                evidence(
                    TOUCH_PACKET,
                    str(touch_packet.get("status")),
                    f"asynchronous focused packet must start only after the operator explicitly says 开始验收; machine_precondition={touch_packet.get('machine_precondition')}",
                ),
                evidence(
                    INTERACTION_PROFILE_RUNTIME_GATE,
                    interaction_profile_status,
                    "the same focused packet remains NO_GO until the reset-bounded normal capture proves the complete quiet interaction marker",
                ),
                evidence(
                    TOUCH_REVIEW_TEMPLATE,
                    str(touch_review_template.get("status")),
                    "blank structured review template mirrors all focused operator steps and defaults every record to non-publishable until triaged with evidence",
                ),
                evidence(
                    TOUCH_REVIEW_RECORD,
                    str(touch_review_record.get("status")),
                    "filled review record validator is present and stays non-publishable until all operator notes are triaged, closed, and linked to evidence",
                ),
                evidence(PRE_ACCEPTANCE_HEALTH, str(pre_acceptance.get("status")), f"machine-only pre-acceptance health gate blocks acceptance until rev{CANDIDATE.revision} runtime recheck, while retaining last-proven log, touch identity, refresh marker, flash preflight, and packet/resource consistency evidence"),
                evidence(RUNTIME_RECHECK_RUNNER, str(runtime_recheck_runner.get("status")), f"rev{CANDIDATE.revision} provision flash, provision capture, normal restore, and normal capture sequence is dry-run verified and requires the Companion-WB55 workflow hardware lock before execution"),
                evidence(
                    RUNTIME_ACTION_CARD,
                    str(runtime_action_card.get("status")),
                    f"Chinese hardware action card renders the locked rev{CANDIDATE.revision} runtime recheck steps, expected markers, promotion sequence, and human acceptance start rule",
                ),
                evidence(
                    RUNTIME_FLASH_PREFLIGHT,
                    str(runtime_flash_preflight.get("status")),
                    "normal/provision flash CheckOnly preflight proves both hex paths and STM32_Programmer_CLI are available before the locked hardware run",
                ),
                evidence(
                    RUNTIME_SERIAL_CAPTURE_PREFLIGHT,
                    str(runtime_serial_capture_preflight.get("status")),
                    "static serial-capture preflight proves capture_nucleo_serial.ps1, locked runner calls, raw/summary output names, and log-verifier expectations before opening any COM port; claim_scope=static_serial_capture_contract_no_hardware_claim",
                ),
                evidence(
                    RUNTIME_RECHECK_LOGS,
                    str(runtime_recheck_logs.get("status")),
                    f"rev{CANDIDATE.revision} provision/normal runtime logs are the first-hand machine gate; pending status means human touch/visual acceptance must not start",
                ),
                evidence(
                    RUNTIME_PROMOTION,
                    promotion_status,
                    f"promotion gate has applied rev{CANDIDATE.revision} runtime evidence; human visual/touch acceptance is still pending"
                    if promotion_status == "APPLIED" else
                    f"promotion gate refuses to update runtime evidence until both rev{CANDIDATE.revision} provision and normal serial logs verify PASS",
                ),
            ],
            "pending_steps": [item.get("id") for item in touch_packet.get("operator_steps", [])],
        },
        {
            "id": "external_flash_and_ota_resource_policy",
            "status": "proved",
            "requirement": "Large replaceable UI resources stay in external Flash and remain part of OTA/update scope; internal Flash keeps only rescue UI/code.",
            "evidence": [
                evidence(RESOURCE_POLICY, str(resource_policy.get("status")), f"normal linked full-frame static expression bytes remain zero; revision {resource_pack.get('revision')} candidate pack bytes/CRC are tracked separately from last real WB55 runtime evidence"),
            ],
        },
        {
            "id": "wba55_wba65_portability_boundary",
            "status": "pre_port_proved_real_wba_pending",
            "requirement": "Portable screen/expression/touch/resource layers preserve WBA55/WBA65 boundaries; real WBA parity remains a future hardware gate.",
            "evidence": [
                evidence(WBA_PORT, str(wba_port.get("status")), "portable contracts, target-named WBA scaffolds, and forbidden portable dependencies are recorded"),
                evidence(
                    WBA_CUBE_DEPENDENCY,
                    str(wba_cube_dependency.get("status")),
                    "CubeWBA dependency preflight records that WBA parity stays DRAFT_PRE_PORT until STM32CubeWBA, a separate CubeWBA project, and a scriptable WBA build wrapper exist",
                ),
                evidence(
                    WBA_REAL_PARITY,
                    str(wba_real_parity.get("status")),
                    "WBA promotion is blocked until target_family=STM32WBA, exact WBA55/WBA65 evidence, WBA-named paths, and real panel/touch/BLE artifacts exist; WB55 evidence is baseline only",
                ),
                evidence(
                    WBA_LSE_CLOCK,
                    str(wba_lse_clock.get("status")),
                    "WBA55/WBA65 pre-port clock contract requires assembled 32.768 kHz LSE by default and keeps real LSE startup, RTC continuity, BLE sleep, timed wake-up, or no-LSE exception evidence pending; claim_scope=wba_clock_design_contract_no_hardware_claim",
                ),
                evidence(
                    WBA_PET_BEHAVIOR_USER_DATA,
                    str(wba_pet_behavior_user_data.get("status")),
                    "WBA55/WBA65 comp_pet_behavior_memory_t stays outside ui_assets/CEMP, OTA staging, recording cache, and MCU Flash constants through callback-only logical slots, CRC records, low-frequency commits, explicit privacy erase, and Cortex-M33 ARM GCC object compilation; real WBA storage evidence remains pending",
                ),
            ],
            "blocked_until_hardware": wba_port.get("blocked_until_hardware", {}),
        },
    ]

    open_requirements = [
        item["id"] for item in requirements
        if item["status"] not in {"proved"}
    ]

    return {
        "schema_id": SCHEMA_ID,
        "status": "GOAL_ACTIVE_NOT_COMPLETE",
        "target": "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U; future STM32WBA55/WBA65",
        "generated_from": {
            "bilingual_menu": rel(BILINGUAL_MENU),
            "touch_visual_packet": rel(TOUCH_PACKET),
            "touch_visual_review_template": rel(TOUCH_REVIEW_TEMPLATE),
            "touch_visual_review_record": rel(TOUCH_REVIEW_RECORD),
            "runtime_hardware_action_card": rel(RUNTIME_ACTION_CARD),
            "runtime_flash_preflight": rel(RUNTIME_FLASH_PREFLIGHT),
            "runtime_serial_capture_preflight": rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT),
            "pre_acceptance_health": rel(PRE_ACCEPTANCE_HEALTH),
            "acceptance_index": rel(ACCEPTANCE_INDEX),
            "runtime_recheck_runner": rel(RUNTIME_RECHECK_RUNNER),
            "runtime_recheck_logs": rel(RUNTIME_RECHECK_LOGS),
            "runtime_promotion_gate": rel(RUNTIME_PROMOTION),
            "panel_gate": rel(PANEL_GATE),
            "wb55_build_matrix": rel(WB55_BUILD_MATRIX),
            "wba_port_contract": rel(WBA_PORT),
            "wba_cube_dependency_preflight": rel(WBA_CUBE_DEPENDENCY),
            "wba_real_parity_gate": rel(WBA_REAL_PARITY),
            "wba_lse_clock_contract": rel(WBA_LSE_CLOCK),
            "wba_pet_behavior_user_data": rel(WBA_PET_BEHAVIOR_USER_DATA),
            "resource_policy": rel(RESOURCE_POLICY),
            "generated_art_style_contract": rel(GENERATED_STYLE),
            "premium_pet_art_contract": rel(PREMIUM_ART),
            "refresh_feel_contract": rel(REFRESH_FEEL),
            "display_queue_generation_hygiene": rel(DISPLAY_QUEUE_GENERATION_HYGIENE),
            "generation_release_ledger": rel(GENERATION_RELEASE_LEDGER),
            "menu_drag_continuity_contract": rel(MENU_DRAG),
            "screen_presentation_contract": rel(PRESENTATION),
            "touch_ft6336_contract": rel(TOUCH_FT6336),
            "interaction_profile_runtime_gate": rel(INTERACTION_PROFILE_RUNTIME_GATE),
        },
        "current_resource": {
            "revision": resource_pack.get("revision"),
            "clips": resource_pack.get("clips"),
            "frames": resource_pack.get("frames"),
            "total_bytes": resource_pack.get("total_bytes"),
            "crc32": resource_pack.get("pack_crc32"),
            "runtime_status": runtime_status,
            "interaction_profile_status": interaction_profile_status,
            "normal_firmware_restored": (
                machine_state.get("normal_firmware_restored") if not runtime_pending else False
            ),
            "normal_log": machine_state.get("normal_log") if not runtime_pending else None,
            "provision_log": machine_state.get("provision_log") if not runtime_pending else None,
        },
        "resource_policy_crosscheck": {
            "candidate_revision": candidate_pack.get("revision"),
            "candidate_pack_bytes": candidate_pack.get("pack_bytes"),
            "candidate_crc32": candidate_pack.get("pack_crc32"),
            "wb55_real_revision": wb55_real.get("revision"),
            "wb55_real_pack_bytes": wb55_real.get("pack_bytes"),
            "wb55_real_crc32": wb55_real.get("pack_crc32"),
            "last_runtime_proven_marker": "source=external_flash",
        },
        "acceptance_sequence": {
            "acceptance_index": rel(ACCEPTANCE_INDEX),
            "schema_id": acceptance_index.get("schema_id"),
            "next_hardware_gate": acceptance_index.get("summary", {}).get("next_hardware_gate"),
            "next_human_gate": acceptance_index.get("summary", {}).get("next_human_gate"),
            "summary": acceptance_index.get("summary", {}),
            "pre_acceptance_status": pre_acceptance.get("status"),
            "runtime_logs_status": runtime_recheck_logs.get("status"),
            "runtime_promotion_status": runtime_promotion.get("status"),
            "interaction_profile_status": interaction_profile_status,
            "interaction_profile_marker_present": interaction_profile.get("marker_present"),
        },
        "requirements": requirements,
        "open_requirements": open_requirements,
        "completion_rule": (
            "Do not mark the active goal complete until every requirement is proved; "
            "pending_human requires operator acceptance evidence, and WBA real parity "
            "requires a later WBA hardware/project gate."
        ),
        "validation_commands": [
            "python .\\tools\\verify_companion_screen_goal_audit.py",
            "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
            "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "python .\\tools\\render_wb55_touch_visual_review_template.py",
            "python .\\tools\\verify_wb55_touch_visual_review_record.py",
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_wb55_screen_build_matrix.py",
            "python .\\tools\\verify_screen_menu_assets.py",
            "python .\\tools\\verify_menu_drag_continuity_contract.py",
            "python .\\tools\\verify_screen_presentation.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_screen_resource_architecture.py",
            "python .\\tools\\render_generated_art_style_contract.py",
            "python .\\tools\\verify_premium_pet_art_contract.py",
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_screen_generation_release_ledger.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
            "python .\\tools\\verify_expression_wba_real_parity_gate.py",
            "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
            "python .\\tools\\verify_pet_behavior_user_data_stm32wba.py",
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Companion Screen Goal Audit",
        "",
        "This file is generated. Update it with",
        "`python .\\tools\\verify_companion_screen_goal_audit.py --write`.",
        "",
        f"- Status: `{audit['status']}`",
        f"- Target: `{audit['target']}`",
        f"- Current resource: revision `{audit['current_resource']['revision']}`, "
        f"`{audit['current_resource']['total_bytes']}` bytes, CRC `{audit['current_resource']['crc32']}`",
        "",
        "## Requirements",
        "",
    ]
    for item in audit["requirements"]:
        lines.extend([
            f"### {item['id']}",
            "",
            f"- Status: `{item['status']}`",
            f"- Requirement: {item['requirement']}",
            "- Evidence:",
        ])
        for ev in item["evidence"]:
            lines.append(f"  - `{ev['path']}`: `{ev['status']}` - {ev['summary']}")
        if item.get("pending_steps"):
            lines.append("- Pending steps:")
            for step in item["pending_steps"]:
                lines.append(f"  - `{step}`")
        if item.get("blocked_until_hardware"):
            blocked = item["blocked_until_hardware"]
            lines.append(f"- Future gate: `{blocked.get('gate')}` - {blocked.get('reason')}")
        lines.append("")
    lines.extend([
        "## Open Requirements",
        "",
    ])
    lines.extend(f"- `{item}`" for item in audit["open_requirements"])
    lines.extend(["", f"Completion rule: {audit['completion_rule']}", ""])
    return "\n".join(lines)


def check_audit(audit: dict[str, Any], errors: list[str]) -> None:
    if audit.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if audit.get("status") != "GOAL_ACTIVE_NOT_COMPLETE":
        errors.append("goal audit must keep the active goal open")
    resource = audit.get("current_resource", {})
    menu = load_json(BILINGUAL_MENU)
    menu_pack = menu.get("resource_pack", {})
    menu_runtime = menu.get("runtime_evidence", {})
    expected_resource = {
        "revision": menu_pack.get("revision"),
        "clips": 33,
        "frames": CANDIDATE.frames,
        "total_bytes": menu_pack.get("total_bytes"),
        "crc32": menu_pack.get("pack_crc32"),
        "runtime_status": menu_runtime.get("status"),
        "interaction_profile_status": load_json(TOUCH_PACKET).get("machine_state", {}).get("interaction_profile", {}).get("status"),
        "normal_firmware_restored": (
            False
            if str(menu_runtime.get("status", "")).endswith("_RUNTIME_RECHECK_PENDING")
            else True
        ),
    }
    for key, expected in expected_resource.items():
        if resource.get(key) != expected:
            errors.append(f"current_resource.{key} drifted: {resource.get(key)!r}")
    crosscheck = audit.get("resource_policy_crosscheck", {})
    runtime_status = str(menu_runtime.get("status", ""))
    runtime_logs_pass = load_json(RUNTIME_RECHECK_LOGS).get("status") == "PASS"
    if runtime_status.endswith("_RUNTIME_RECHECK_PENDING"):
        if crosscheck.get("candidate_revision") != menu_pack.get("revision"):
            errors.append("resource policy candidate revision drifted")
        if crosscheck.get("candidate_pack_bytes") != menu_pack.get("total_bytes"):
            errors.append("resource policy candidate pack size drifted")
        if crosscheck.get("candidate_crc32") != menu_pack.get("pack_crc32"):
            errors.append("resource policy candidate CRC drifted")
    else:
        if crosscheck.get("wb55_real_revision") != menu_pack.get("revision"):
            errors.append("resource policy crosscheck revision drifted")
        if crosscheck.get("wb55_real_pack_bytes") != menu_pack.get("total_bytes"):
            errors.append("resource policy crosscheck pack size drifted")
        if crosscheck.get("wb55_real_crc32") != menu_pack.get("pack_crc32"):
            errors.append("resource policy crosscheck CRC drifted")

    requirements = {item.get("id"): item for item in audit.get("requirements", [])}
    generated_from = audit.get("generated_from", {})
    runtime_promotion = load_json(RUNTIME_PROMOTION)
    runtime_recheck_logs = load_json(RUNTIME_RECHECK_LOGS)
    touch_review_template = load_json(TOUCH_REVIEW_TEMPLATE)
    touch_review_record = load_json(TOUCH_REVIEW_RECORD)
    touch_packet = load_json(TOUCH_PACKET)
    interaction_profile = touch_packet.get("machine_state", {}).get("interaction_profile", {})
    interaction_profile_status = str(interaction_profile.get("status", ""))
    runtime_action_card = load_json(RUNTIME_ACTION_CARD)
    quiet_profile_only_recheck = runtime_action_card.get("quiet_interaction_profile_recheck_required") is True
    runtime_flash_preflight = load_json(RUNTIME_FLASH_PREFLIGHT)
    runtime_serial_capture_preflight = load_json(RUNTIME_SERIAL_CAPTURE_PREFLIGHT)
    acceptance_index = load_json(ACCEPTANCE_INDEX)
    wb55_build_matrix = load_json(WB55_BUILD_MATRIX)
    wba_cube_dependency = load_json(WBA_CUBE_DEPENDENCY)
    wba_real_parity = load_json(WBA_REAL_PARITY)
    wba_lse_clock = load_json(WBA_LSE_CLOCK)
    required_ids = {
        "wb55_physical_wiring_and_panel_identity",
        "current_external_resource_runtime",
        "generated_pet_and_menu_art_baseline",
        "generated_art_handoff_and_refresh_feel_regression_guard",
        "screen_refresh_touch_machine_health",
        "wb55_screen_firmware_build_matrix",
        "touch_menu_interaction_machine_contract",
        "daily_pet_and_menu_human_feel",
        "external_flash_and_ota_resource_policy",
        "wba55_wba65_portability_boundary",
    }
    missing = required_ids - set(requirements)
    if missing:
        errors.append(f"missing requirements: {sorted(missing)}")
    if requirements.get("daily_pet_and_menu_human_feel", {}).get("status") != "pending_human":
        errors.append("human touch/visual gate must remain pending_human")
    expected_machine_health_status = (
        "proved"
        if not runtime_status.endswith("_RUNTIME_RECHECK_PENDING") and interaction_profile_status == "PASS"
        else "pending_hardware_recheck"
    )
    if requirements.get("screen_refresh_touch_machine_health", {}).get("status") != expected_machine_health_status:
        errors.append(f"screen refresh/touch machine health must be {expected_machine_health_status}")
    if interaction_profile.get("required_marker") != "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 refresh_policy=partial_x5_then_fast_cleanup":
        errors.append("interaction profile must require the complete quiet boot marker")
    if interaction_profile.get("marker_present") != (interaction_profile_status == "PASS"):
        errors.append("interaction profile marker presence must match its status")
    if touch_packet.get("machine_state", {}).get("interaction_profile_evidence") != rel(INTERACTION_PROFILE_RUNTIME_GATE):
        errors.append("touch packet must link interaction-profile runtime gate")
    if touch_review_template.get("status") != "TEMPLATE_NOT_ACCEPTANCE_RESULT":
        errors.append("touch review template must remain a template, not an acceptance result")
    if touch_review_template.get("claim_scope") != "blank_operator_review_template":
        errors.append("touch review template claim scope drifted")
    if len(touch_review_template.get("review_records", [])) != len(requirements.get("daily_pet_and_menu_human_feel", {}).get("pending_steps", [])):
        errors.append("touch review template records must mirror pending human steps")
    allowed_review_record_statuses = {
        "NO_GO_NOT_STARTED",
        "NO_GO_OPEN_REVIEW_ITEMS",
        "PASS_READY_FOR_PUBLISHABLE_REVIEW",
    }
    if touch_review_record.get("status") not in allowed_review_record_statuses:
        errors.append("touch review record must remain a known non-publishable or publishable review state")
    if touch_review_record.get("publishable_pass_allowed") is not False:
        errors.append("touch review record must not allow publishable PASS before human review")
    if len(touch_review_record.get("review_records", [])) != len(requirements.get("daily_pet_and_menu_human_feel", {}).get("pending_steps", [])):
        errors.append("touch review record records must mirror pending human steps")
    if runtime_promotion.get("target_state", {}).get("status") != CANDIDATE.pass_status:
        errors.append("runtime promotion target status drifted")
    if generated_from.get("runtime_recheck_logs") != rel(RUNTIME_RECHECK_LOGS):
        errors.append("generated_from must include runtime_recheck_logs")
    if generated_from.get("touch_visual_review_template") != rel(TOUCH_REVIEW_TEMPLATE):
        errors.append("generated_from must include touch_visual_review_template")
    if generated_from.get("touch_visual_review_record") != rel(TOUCH_REVIEW_RECORD):
        errors.append("generated_from must include touch_visual_review_record")
    if generated_from.get("runtime_hardware_action_card") != rel(RUNTIME_ACTION_CARD):
        errors.append("generated_from must include runtime_hardware_action_card")
    if generated_from.get("runtime_flash_preflight") != rel(RUNTIME_FLASH_PREFLIGHT):
        errors.append("generated_from must include runtime_flash_preflight")
    if generated_from.get("runtime_serial_capture_preflight") != rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT):
        errors.append("generated_from must include runtime_serial_capture_preflight")
    if generated_from.get("acceptance_index") != rel(ACCEPTANCE_INDEX):
        errors.append("generated_from must include acceptance_index")
    if generated_from.get("wb55_build_matrix") != rel(WB55_BUILD_MATRIX):
        errors.append("generated_from must include wb55_build_matrix")
    if generated_from.get("wba_real_parity_gate") != rel(WBA_REAL_PARITY):
        errors.append("generated_from must include wba_real_parity_gate")
    if generated_from.get("wba_lse_clock_contract") != rel(WBA_LSE_CLOCK):
        errors.append("generated_from must include wba_lse_clock_contract")
    if generated_from.get("wba_pet_behavior_user_data") != rel(WBA_PET_BEHAVIOR_USER_DATA):
        errors.append("generated_from must include wba_pet_behavior_user_data")
    if generated_from.get("wba_cube_dependency_preflight") != rel(WBA_CUBE_DEPENDENCY):
        errors.append("generated_from must include wba_cube_dependency_preflight")
    if generated_from.get("display_queue_generation_hygiene") != rel(DISPLAY_QUEUE_GENERATION_HYGIENE):
        errors.append("generated_from must include display_queue_generation_hygiene")
    if generated_from.get("generation_release_ledger") != rel(GENERATION_RELEASE_LEDGER):
        errors.append("generated_from must include generation_release_ledger")
    if generated_from.get("interaction_profile_runtime_gate") != rel(INTERACTION_PROFILE_RUNTIME_GATE):
        errors.append("generated_from must include interaction_profile_runtime_gate")
    if runtime_status.endswith("_RUNTIME_RECHECK_PENDING"):
        if runtime_logs_pass:
            if runtime_promotion.get("status") != "READY_TO_APPLY":
                errors.append("runtime promotion gate must be READY_TO_APPLY after logs pass while runtime is pending")
            if runtime_promotion.get("blockers"):
                errors.append("READY_TO_APPLY runtime promotion must not keep blockers")
        else:
            if runtime_promotion.get("status") != "NO_GO_LOGS_NOT_PASS":
                errors.append("runtime promotion gate must remain NO_GO while active runtime is pending")
            if not runtime_promotion.get("blockers"):
                errors.append("runtime promotion gate must list blockers while active runtime is pending")
            if runtime_recheck_logs.get("status") not in {"NO_GO_MISSING_RUNTIME_LOGS", "NO_GO_INCOMPLETE_RUNTIME_MARKERS"}:
                errors.append("runtime recheck logs gate must remain NO_GO while active runtime is pending")
    else:
        if runtime_promotion.get("status") != "APPLIED":
            errors.append("runtime promotion gate must be APPLIED after active runtime evidence is promoted")
        if runtime_recheck_logs.get("status") != "PASS" and not quiet_profile_only_recheck:
            errors.append("runtime recheck logs gate may remain non-PASS after resource promotion only for the explicit quiet-profile recheck")
        if quiet_profile_only_recheck and runtime_recheck_logs.get("status") not in {"NO_GO_MISSING_RUNTIME_LOGS", "NO_GO_INCOMPLETE_RUNTIME_MARKERS"}:
            errors.append("quiet-profile recheck must keep a pending runtime log gate until the current normal capture is replaced")
    if requirements.get("wba55_wba65_portability_boundary", {}).get("status") != "pre_port_proved_real_wba_pending":
        errors.append("WBA boundary must remain pre-port with real WBA pending")
    if wba_cube_dependency.get("status") != "PASS":
        errors.append("WBA Cube dependency preflight must be PASS")
    if wba_cube_dependency.get("contract", {}).get("wba_parity_claim_allowed") is not False:
        errors.append("WBA Cube dependency preflight must not allow parity claims")
    if wba_cube_dependency.get("contract", {}).get("wba_port_status_until_dependency_lands") != "DRAFT_PRE_PORT":
        errors.append("WBA Cube dependency preflight must keep WBA status DRAFT_PRE_PORT")
    if wba_real_parity.get("status") != "PASS_PRE_PORT_PARITY_BLOCKED":
        errors.append("WBA real parity gate must remain blocked before real WBA evidence exists")
    if wba_real_parity.get("parity_claim_allowed") is not False:
        errors.append("WBA real parity gate must reject parity claims before real WBA evidence exists")
    if wba_lse_clock.get("status") != "PASS_PRE_PORT_CLOCK_CONTRACT_RECORDED":
        errors.append("WBA LSE clock contract must remain recorded before WBA port")
    if wba_lse_clock.get("claim_scope") != "wba_clock_design_contract_no_hardware_claim":
        errors.append("WBA LSE clock contract must not claim hardware completion")
    if wba_lse_clock.get("current_state", {}).get("hardware_claimed") is not False:
        errors.append("WBA LSE clock contract must keep hardware_claimed false")
    if runtime_action_card.get("status") != "NO_GO_WAITING_FOR_REAL_HARDWARE_RUN":
        errors.append("runtime hardware action card must remain waiting for real hardware run")
    if runtime_action_card.get("claim_scope") != "operator_action_card_no_hardware_claim":
        errors.append("runtime hardware action card must not claim hardware completion")
    if runtime_flash_preflight.get("status") != "PASS":
        errors.append("runtime flash preflight must be PASS")
    if runtime_serial_capture_preflight.get("status") != "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT":
        errors.append("runtime serial capture preflight must be PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT")
    if runtime_serial_capture_preflight.get("claim_scope") != "static_serial_capture_contract_no_hardware_claim":
        errors.append("runtime serial capture preflight must not claim hardware completion")
    acceptance_sequence = audit.get("acceptance_sequence", {})
    if acceptance_sequence.get("schema_id") != "companion.pendant.screen_acceptance_index.v1":
        errors.append("acceptance sequence schema drifted")
    if acceptance_sequence.get("acceptance_index") != rel(ACCEPTANCE_INDEX):
        errors.append("acceptance sequence must point at companion-screen-acceptance-index.json")
    expected_next_hardware_gate = "wba_real_panel_parity" if runtime_status == CANDIDATE.pass_status else RUNTIME_GATE_ID
    if acceptance_sequence.get("next_hardware_gate") != expected_next_hardware_gate:
        errors.append(f"acceptance sequence next_hardware_gate must be {expected_next_hardware_gate}")
    if acceptance_sequence.get("next_human_gate") != "wb55_touch_visual_acceptance":
        errors.append("acceptance sequence next_human_gate must be wb55_touch_visual_acceptance")
    expected_pre_acceptance_status = (
        "NO_GO_RUNTIME_RECHECK_PENDING"
        if runtime_status.endswith("_RUNTIME_RECHECK_PENDING")
        else "NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING"
        if not runtime_logs_pass
        else "NO_GO_OPEN_OPERATOR_REVIEW_ITEMS"
        if touch_review_record.get("status") == "NO_GO_OPEN_REVIEW_ITEMS"
        else "PASS"
    )
    if acceptance_sequence.get("pre_acceptance_status") != expected_pre_acceptance_status:
        errors.append(f"acceptance sequence pre-acceptance status must be {expected_pre_acceptance_status}")
    if acceptance_sequence.get("runtime_logs_status") != runtime_recheck_logs.get("status"):
        errors.append("acceptance sequence runtime log status drifted from runtime log gate")
    if acceptance_sequence.get("runtime_promotion_status") != runtime_promotion.get("status"):
        errors.append("acceptance sequence runtime promotion status drifted from promotion gate")
    if acceptance_sequence.get("interaction_profile_status") != interaction_profile_status:
        errors.append("acceptance sequence interaction profile status drifted from touch packet")
    if acceptance_sequence.get("interaction_profile_marker_present") != interaction_profile.get("marker_present"):
        errors.append("acceptance sequence interaction profile marker drifted from touch packet")
    if acceptance_index.get("summary", {}).get("next_hardware_gate") != acceptance_sequence.get("next_hardware_gate"):
        errors.append("acceptance sequence next hardware gate drifted from acceptance index")
    if acceptance_index.get("summary", {}).get("next_human_gate") != acceptance_sequence.get("next_human_gate"):
        errors.append("acceptance sequence next human gate drifted from acceptance index")
    expected_deferred_count = 0 if runtime_status == CANDIDATE.pass_status else 1
    if acceptance_sequence.get("summary", {}).get("deferred_count") != expected_deferred_count:
        errors.append(f"acceptance sequence deferred_count must be {expected_deferred_count}")
    wba_evidence_paths = {
        ev.get("path")
        for ev in requirements.get("wba55_wba65_portability_boundary", {}).get("evidence", [])
    }
    if rel(WBA_REAL_PARITY) not in wba_evidence_paths:
        errors.append("WBA boundary evidence must include the real parity gate")
    if rel(WBA_CUBE_DEPENDENCY) not in wba_evidence_paths:
        errors.append("WBA boundary evidence must include the CubeWBA dependency preflight")
    if rel(WBA_LSE_CLOCK) not in wba_evidence_paths:
        errors.append("WBA boundary evidence must include the LSE clock contract")
    if rel(WBA_PET_BEHAVIOR_USER_DATA) not in wba_evidence_paths:
        errors.append("WBA boundary evidence must include the pet behavior user-data contract")
    build_req = requirements.get("wb55_screen_firmware_build_matrix", {})
    if build_req.get("status") != "proved":
        errors.append("WB55 screen firmware build matrix requirement must be proved")
    build_evidence_paths = {ev.get("path") for ev in build_req.get("evidence", [])}
    if rel(WB55_BUILD_MATRIX) not in build_evidence_paths:
        errors.append("WB55 build matrix requirement evidence must include the build matrix")
    if wb55_build_matrix.get("status") != "PASS":
        errors.append("WB55 build matrix must be PASS")
    build_variants = wb55_build_matrix.get("build_variants", {})
    if "dry_run_default" not in build_variants:
        errors.append("WB55 build matrix must include dry_run_default")
    if "ssd1681_real_panel" not in build_variants:
        errors.append("WB55 build matrix must include ssd1681_real_panel")
    if "screen_asset_provision" not in build_variants:
        errors.append("WB55 build matrix must include screen_asset_provision")
    build_contracts = wb55_build_matrix.get("contracts", {})
    for key in (
        "build_logs_prove_all_variants",
        "queue_generation_compiles_in_all_variants",
        "screen_asset_provision_builds_current_external_assets",
        "build_logs_prove_both_variants",
        "queue_generation_compiles_in_both_variants",
        "build_wrapper_serializes_shared_build_dir",
        "pre_acceptance_status_remains_runtime_pending_until_logs",
    ):
        if build_contracts.get(key) is not True:
            errors.append(f"WB55 build matrix contract {key} must be true")
    generated_req = requirements.get("generated_pet_and_menu_art_baseline", {})
    if generated_req.get("status") != "proved":
        errors.append("generated pet/menu art baseline must be proved")
    generated_style = load_json(GENERATED_STYLE)
    premium_art = load_json(PREMIUM_ART)
    refresh_feel = load_json(REFRESH_FEEL)
    generation_hygiene = load_json(DISPLAY_QUEUE_GENERATION_HYGIENE)
    generation_ledger = load_json(GENERATION_RELEASE_LEDGER)
    menu_drag = load_json(MENU_DRAG)
    touch_ft6336 = load_json(TOUCH_FT6336)
    acceptance = generated_style.get("acceptance", {})
    for key in (
        "generated_reference_is_source_of_truth",
        "legacy_procedural_not_normal_product",
        "inner_face_only",
        "shell_owns_outline",
    ):
        if acceptance.get(key) is not True:
            errors.append(f"generated style acceptance.{key} must be true")
    if premium_art.get("pose_count") != 12:
        errors.append("premium pet art contract must retain the 12-pose generated reference sheet")
    handoff_refresh_req = requirements.get("generated_art_handoff_and_refresh_feel_regression_guard", {})
    if handoff_refresh_req.get("status") != "proved":
        errors.append("generated art handoff and refresh feel regression guard must be proved")
    if acceptance.get("normal_pack_no_old_new_handoff") is not True:
        errors.append("generated style must prevent normal-pack old/new handoff")
    if acceptance.get("screen_feel_policy_recorded") is not True:
        errors.append("generated style must record the screen feel policy")
    if refresh_feel.get("status") != "PASS":
        errors.append("refresh feel contract must be PASS")
    if generation_hygiene.get("status") != "PASS":
        errors.append("display queue generation hygiene must be PASS")
    expected_ledger_status = (
        "RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING"
        if runtime_promotion.get("status") == "APPLIED" else
        "RUNTIME_LOGS_PASS_PROMOTION_PENDING"
        if runtime_logs_pass else
        "PENDING_RUNTIME_RECHECK"
    )
    if generation_ledger.get("status") != expected_ledger_status:
        errors.append(f"generation release ledger must be {expected_ledger_status}")
    if generation_ledger.get("candidate", {}).get("cemp_revision") != menu_pack.get("revision"):
        errors.append("generation release ledger candidate revision drifted from menu resource pack")
    if generation_ledger.get("candidate", {}).get("cemp_crc32") != menu_pack.get("pack_crc32"):
        errors.append("generation release ledger candidate CRC drifted from menu resource pack")
    if generation_ledger.get("first_frame_evidence", {}).get("model_coherent_generation") != 1:
        errors.append("generation release ledger must require coherent first frame")
    if generation_ledger.get("activation_evidence", {}).get("stale_queued_frames_discarded_in_model") != 3:
        errors.append("generation release ledger must keep stale discard model evidence")
    if generation_ledger.get("normal_pack_generation", {}).get("old_procedural_normal_frames_allowed") is not False:
        errors.append("generation release ledger must forbid old procedural normal product frames")
    if generation_ledger.get("ota_transaction_rule", {}).get("ui_assets_ota_in_scope") is not True:
        errors.append("generation release ledger must include ui_assets OTA transaction scope")
    handoff_paths = {ev.get("path") for ev in handoff_refresh_req.get("evidence", [])}
    if rel(GENERATION_RELEASE_LEDGER) not in handoff_paths:
        errors.append("generation handoff requirement evidence must include release ledger")
    generation_scenario = generation_hygiene.get("scenario", {})
    generation_expectation = generation_scenario.get("display_result_expectation", {})
    if generation_expectation.get("coherent_generation") != 1:
        errors.append("display queue generation hygiene must require coherent_generation")
    if generation_expectation.get("last_stale_discarded") != 3:
        errors.append("display queue generation hygiene must keep stale discard expectation")
    refresh_checks = refresh_feel.get("checks", {})
    for key in (
        "vendor_ghosting_research_recorded",
        "interactive_uses_differential_waveform",
        "maintenance_uses_single_low_flicker_waveform",
        "full_refresh_reserved_for_baseline_or_fault",
        "menu_drag_coalesces_to_latest_frame",
        "art_and_refresh_axes_separate",
    ):
        if refresh_checks.get(key) is not True:
            errors.append(f"refresh feel check {key} drifted")
    touch_menu_req = requirements.get("touch_menu_interaction_machine_contract", {})
    if touch_menu_req.get("status") != "proved":
        errors.append("touch/menu machine interaction contract must be proved")
    if menu_drag.get("schema_id") != "companion.screen.menu_v3_static_home_contract.v1":
        errors.append("menu contract must use the menu-v3 static-home schema")
    if menu_drag.get("frame_count_per_language") != 1:
        errors.append("menu-v3 contract must keep one home frame per language")
    if menu_drag.get("home_rows") != 6:
        errors.append("menu-v3 contract must keep six visible home rows")
    gesture_contract = touch_ft6336.get("gesture_contract", {})
    expected_gestures = {
        "daily_enter_menu": "3000 ms any-position long_press with 46 px wobble tolerance",
        "home_vertical_stroke": "menu-v3 home tracks the current pressed row but never synthesizes legacy scroll frames",
        "daily_stroke": "all non-menu-entry swipes react as directional pet strokes",
    }
    for key, expected in expected_gestures.items():
        if gesture_contract.get(key) != expected:
            errors.append(f"touch gesture contract {key} drifted")
    open_requirements = set(audit.get("open_requirements", []))
    daily_evidence_paths = {
        ev.get("path")
        for ev in requirements.get("daily_pet_and_menu_human_feel", {}).get("evidence", [])
    }
    machine_health_evidence_paths = {
        ev.get("path")
        for ev in requirements.get("screen_refresh_touch_machine_health", {}).get("evidence", [])
    }
    if rel(RUNTIME_RECHECK_LOGS) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include runtime recheck logs")
    if rel(RUNTIME_ACTION_CARD) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include runtime hardware action card")
    if rel(RUNTIME_FLASH_PREFLIGHT) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include runtime flash preflight")
    if rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include runtime serial capture preflight")
    if rel(TOUCH_REVIEW_TEMPLATE) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include touch review template")
    if rel(TOUCH_REVIEW_RECORD) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include touch review record")
    if rel(RUNTIME_RECHECK_LOGS) not in machine_health_evidence_paths:
        errors.append("screen refresh/touch machine health evidence must include runtime recheck logs")
    if rel(INTERACTION_PROFILE_RUNTIME_GATE) not in daily_evidence_paths:
        errors.append("daily human gate evidence must include interaction-profile runtime gate")
    if rel(INTERACTION_PROFILE_RUNTIME_GATE) not in machine_health_evidence_paths:
        errors.append("screen refresh/touch machine health evidence must include interaction-profile runtime gate")
    validation_commands = set(audit.get("validation_commands", []))
    if "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py" not in validation_commands:
        errors.append("validation_commands must include runtime recheck logs verifier")
    if "python .\\tools\\render_wb55_touch_visual_review_template.py" not in validation_commands:
        errors.append("validation_commands must include touch review template renderer")
    if "python .\\tools\\render_wb55_runtime_hardware_action_card.py" not in validation_commands:
        errors.append("validation_commands must include runtime hardware action card renderer")
    if "python .\\tools\\verify_wb55_runtime_flash_preflight.py" not in validation_commands:
        errors.append("validation_commands must include runtime flash preflight verifier")
    if "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py" not in validation_commands:
        errors.append("validation_commands must include runtime serial capture preflight verifier")
    if "python .\\tools\\verify_wb55_touch_visual_review_record.py" not in validation_commands:
        errors.append("validation_commands must include touch review record verifier")
    if "python .\\tools\\verify_expression_wba_real_parity_gate.py" not in validation_commands:
        errors.append("validation_commands must include WBA real parity gate verifier")
    if "python .\\tools\\verify_expression_wba_lse_clock_contract.py" not in validation_commands:
        errors.append("validation_commands must include WBA LSE clock contract verifier")
    if "python .\\tools\\verify_expression_acceptance_index.py" not in validation_commands:
        errors.append("validation_commands must include acceptance index verifier")
    if "python .\\tools\\verify_display_queue_generation_hygiene.py" not in validation_commands:
        errors.append("validation_commands must include display queue generation hygiene verifier")
    if "python .\\tools\\verify_screen_generation_release_ledger.py" not in validation_commands:
        errors.append("validation_commands must include generation release ledger verifier")
    if "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py" not in validation_commands:
        errors.append("validation_commands must include WBA Cube dependency preflight verifier")
    if "python .\\tools\\verify_pet_behavior_user_data_stm32wba.py" not in validation_commands:
        errors.append("validation_commands must include WBA pet behavior user-data verifier")
    if "python .\\tools\\verify_wb55_screen_build_matrix.py" not in validation_commands:
        errors.append("validation_commands must include WB55 screen build matrix verifier")
    for required_open in ("daily_pet_and_menu_human_feel", "wba55_wba65_portability_boundary"):
        if required_open not in open_requirements:
            errors.append(f"open_requirements missing {required_open}")
    if runtime_status.endswith("_RUNTIME_RECHECK_PENDING") or interaction_profile_status != "PASS":
        for required_open in ("current_external_resource_runtime", "screen_refresh_touch_machine_health"):
            if required_open == "current_external_resource_runtime" and not runtime_status.endswith("_RUNTIME_RECHECK_PENDING"):
                continue
            if required_open not in open_requirements:
                errors.append(f"open_requirements missing runtime/profile recheck item {required_open}")

    serialized = json.dumps(audit, ensure_ascii=False)
    for token in (
        str(menu_runtime.get("status")),
        "开 始验收".replace(" ", ""),
        str(menu_pack.get("pack_crc32")),
        str(menu_pack.get("total_bytes")),
        f"revision={menu_pack.get('revision')}",
        "source=external_flash",
        "verify_premium_pet_art_contract.py",
        "verify_screen_refresh_feel_contract.py",
        "verify_display_queue_generation_hygiene.py",
        "verify_screen_generation_release_ledger.py",
        "companion-screen-generation-release-ledger.json",
        expected_ledger_status,
        "first-frame coherent marker",
        "OTA transaction",
        "verify_wb55_screen_runtime_recheck_logs.py",
        "render_wb55_touch_visual_review_template.py",
        "render_wb55_runtime_hardware_action_card.py",
        "verify_wb55_runtime_flash_preflight.py",
        "verify_wb55_runtime_serial_capture_preflight.py",
        "verify_wb55_touch_visual_review_record.py",
        "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT",
        "static_serial_capture_contract_no_hardware_claim",
        "TEMPLATE_NOT_ACCEPTANCE_RESULT",
        str(touch_review_record.get("status")),
        "NO_GO_WAITING_FOR_REAL_HARDWARE_RUN",
        "blank structured review template",
        "filled review record validator",
        "verify_expression_wba_real_parity_gate.py",
        "verify_expression_wba_lse_clock_contract.py",
        "verify_expression_wba_cube_dependency_preflight.py",
        "verify_wb55_screen_build_matrix.py",
        "companion-screen-wb55-build-matrix.json",
        "default dry-run",
        "real-panel build",
        "resource-generation queue diagnostics",
        "companion-screen-wba-cube-dependency-preflight.json",
        "DRAFT_PRE_PORT",
        "STM32CubeWBA",
        "promote_wb55_screen_runtime_recheck.py",
        "verify_companion_screen_pre_acceptance_health.py",
        "verify_expression_acceptance_index.py",
        "companion-screen-acceptance-index.json",
        "companion-interaction-profile-runtime-gate-20260714.md",
        "PENDING_HARDWARE_RUNTIME_MARKER",
        "NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING",
        "complete quiet interaction boot marker",
        "acceptance_sequence",
        expected_next_hardware_gate,
        "wb55_touch_visual_acceptance",
        "render_generated_art_style_contract.py",
        "verify_menu_drag_continuity_contract.py",
        "verify_screen_presentation.py",
        "verify_touch_ft6336.py",
        "3000 ms any-position long_press",
        "menu-v3 home tracks the current pressed row",
        "generated reference as source of truth",
        "old/new expression art",
        "coherent_generation",
        "stale queued frames",
        "one 0xCF quiet maintenance",
        "WBA real parity requires",
        "32.768 kHz LSE",
        "wba_clock_design_contract_no_hardware_claim",
        "target_family=STM32WBA",
        "companion-screen-pet-behavior-user-data-stm32wba.json",
        "verify_pet_behavior_user_data_stm32wba.py",
        "privacy erase",
        "comp_pet_behavior_memory_t",
    ):
        if token not in serialized:
            errors.append(f"audit missing token: {token}")


def write_outputs(json_path: pathlib.Path, md_path: pathlib.Path, audit: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(audit), encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)

    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    md_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    audit = build_audit()
    errors: list[str] = []
    check_audit(audit, errors)

    rendered_json = json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    rendered_md = render_markdown(audit)
    if args.write:
        json_path.write_text(rendered_json, encoding="utf-8")
        md_path.write_text(rendered_md, encoding="utf-8")
    else:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json_path.read_text(encoding="utf-8") != rendered_json:
            errors.append(f"stale {rel(json_path)}")
        if not md_path.exists():
            errors.append(f"missing {rel(md_path)}")
        elif md_path.read_text(encoding="utf-8") != rendered_md:
            errors.append(f"stale {rel(md_path)}")

    if errors:
        print("FAIL: Companion screen goal audit checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen goal audit verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
