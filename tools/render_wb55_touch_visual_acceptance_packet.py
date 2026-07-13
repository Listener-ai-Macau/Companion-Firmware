#!/usr/bin/env python3
"""Render the focused WB55 touch/visual operator acceptance packet."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.md"
REVIEW_TEMPLATE_JSON = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.json"
REVIEW_TEMPLATE_MD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.md"
REVIEW_RECORD_JSON = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-record.json"
ACCEPTANCE_INDEX = ROOT / "docs/validation/companion-screen-acceptance-index.json"
FEATURE_CHECKLIST = ROOT / "docs/validation/companion-screen-feature-checklist.json"
SCREEN_DOC = ROOT / "docs/companion_screen_expression_system.md"
PROJECT_PLAN = ROOT / "docs/companion_screen_project_plan.md"
BILINGUAL_MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
RUNTIME_LOGS = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
RUNTIME_FLASH_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-flash-preflight.json"
RUNTIME_SERIAL_CAPTURE_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json"
RUNTIME_HARDWARE_ACTION_CARD = ROOT / "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json"
DISPLAY_QUEUE_GENERATION_HYGIENE = ROOT / "docs/validation/companion-screen-display-queue-generation-hygiene.json"
GENERATION_RELEASE_LEDGER = ROOT / "docs/validation/companion-screen-generation-release-ledger.json"
SCHEMA_ID = "companion.pendant.wb55_touch_visual_acceptance_packet.v1"
CANDIDATE = current_candidate()
PASS_RUNTIME_STATUS = CANDIDATE.pass_status


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def step(step_id: str, title: str, operator_action: str, success_signal: str,
         record: list[str], regression_guard: str) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "operator_action": operator_action,
        "success_signal": success_signal,
        "record": record,
        "regression_guard": regression_guard,
    }


def build_packet() -> dict[str, Any]:
    menu_evidence = json.loads(BILINGUAL_MENU.read_text(encoding="utf-8"))
    runtime_logs = json.loads(RUNTIME_LOGS.read_text(encoding="utf-8"))
    resource_pack = menu_evidence.get("resource_pack", {})
    runtime = menu_evidence.get("runtime_evidence", {})
    runtime_status = runtime.get("status")
    flash_preflight = json.loads(RUNTIME_FLASH_PREFLIGHT.read_text(encoding="utf-8"))
    serial_preflight = json.loads(RUNTIME_SERIAL_CAPTURE_PREFLIGHT.read_text(encoding="utf-8"))
    action_card = json.loads(RUNTIME_HARDWARE_ACTION_CARD.read_text(encoding="utf-8"))
    generation_hygiene = json.loads(DISPLAY_QUEUE_GENERATION_HYGIENE.read_text(encoding="utf-8"))
    generation_ledger = json.loads(GENERATION_RELEASE_LEDGER.read_text(encoding="utf-8"))
    generation_scenario = generation_hygiene.get("scenario", {})
    generation_expectation = generation_scenario.get("display_result_expectation", {})
    runtime_machine_ready = runtime_status == PASS_RUNTIME_STATUS and runtime_logs.get("status") == "PASS"
    machine_precondition = (
        f"PASS: rev{CANDIDATE.revision} provision and normal runtime logs are promoted; human touch/visual steps may start after the operator says 开始验收."
        if runtime_machine_ready else
        f"NO_GO_RUNTIME_RECHECK_PENDING: do not start human touch/visual steps until rev{CANDIDATE.revision} provision and normal runtime logs pass and promotion is applied."
    )
    runtime_log_note = (
        f"revision {CANDIDATE.revision} provision/normal serial logs are linked in machine_state"
        if runtime_machine_ready else
        f"machine_state currently links the last runtime-proven revision logs; rev{CANDIDATE.revision} provision/normal logs are still pending in the runtime recheck report"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PENDING_HUMAN",
        "claim_scope": "operator_packet_no_hardware_claim",
        "target": "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U",
        "gate_id": "wb55_touch_visual_acceptance",
        "purpose": (
            "Focused asynchronous operator packet for the only remaining Companion "
            "screen gate: touch feel, menu feel, language switching, pet reactions, "
            "and perceived 0xCF maintenance flicker."
        ),
        "machine_state": {
            "resource_revision": resource_pack.get("revision"),
            "resource_crc32": resource_pack.get("pack_crc32"),
            "resource_total_bytes": resource_pack.get("total_bytes"),
            "runtime_status": runtime.get("status"),
            "pet_art_style": "genref_sheet_12_inner_faces_v5",
            "normal_firmware_restored": True,
            "bilingual_menu_evidence": rel(BILINGUAL_MENU),
            "provision_log": runtime.get("provision_raw_log"),
            "normal_log": runtime.get("normal_raw_log"),
            "runtime_logs_evidence": rel(RUNTIME_LOGS),
            "runtime_flash_preflight": {
                "path": rel(RUNTIME_FLASH_PREFLIGHT),
                "status": flash_preflight.get("status"),
            },
            "runtime_serial_capture_preflight": {
                "path": rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT),
                "status": serial_preflight.get("status"),
                "claim_scope": serial_preflight.get("claim_scope"),
            },
            "runtime_hardware_action_card": {
                "path": rel(RUNTIME_HARDWARE_ACTION_CARD),
                "status": action_card.get("status"),
            },
            "display_queue_generation_hygiene": {
                "path": rel(DISPLAY_QUEUE_GENERATION_HYGIENE),
                "status": generation_hygiene.get("status"),
                "scenario": generation_scenario.get("name"),
                "coherent_generation": generation_expectation.get("coherent_generation"),
                "last_stale_discarded": generation_expectation.get("last_stale_discarded"),
            },
            "generation_release_ledger": {
                "path": rel(GENERATION_RELEASE_LEDGER),
                "status": generation_ledger.get("status"),
                "cemp_revision": generation_ledger.get("candidate", {}).get("cemp_revision"),
                "cemp_crc32": generation_ledger.get("candidate", {}).get("cemp_crc32"),
                "expected_first_frame_marker": generation_ledger.get("first_frame_evidence", {}).get("expected_marker"),
                "real_runtime_status": generation_ledger.get("first_frame_evidence", {}).get("real_runtime_status"),
                "visual_triage_classes": generation_ledger.get("refresh_classification", {}).get("visual_triage_classes", []),
            },
        },
        "start_rule": (
            f"Do not start this packet until rev{CANDIDATE.revision} runtime logs PASS, promotion is applied, pre-acceptance health PASS, and the operator explicitly says 开始验收."
        ),
        "machine_precondition": machine_precondition,
        "preflight_commands": [
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_screen_generation_release_ledger.py",
            "python .\\tools\\render_generated_art_style_contract.py",
            "python .\\tools\\verify_screen_menu_assets.py",
            "python .\\tools\\verify_screen_presentation.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_premium_pet_art_contract.py",
            "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
            "python .\\tools\\verify_epaper_differential_maintenance_runtime.py",
        ],
        "evidence_to_attach": [
            "operator notes for each step",
            f"filled copy of {rel(REVIEW_TEMPLATE_MD)} or equivalent structured records",
            f"validated filled review record from {rel(REVIEW_RECORD_JSON)}",
            f"runtime hardware action card {rel(RUNTIME_HARDWARE_ACTION_CARD)}",
            f"display queue generation hygiene {rel(DISPLAY_QUEUE_GENERATION_HYGIENE)}",
            f"SCR-17 generation release ledger {rel(GENERATION_RELEASE_LEDGER)}",
            f"runtime flash preflight {rel(RUNTIME_FLASH_PREFLIGHT)}",
            f"runtime serial capture preflight {rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT)}",
            runtime_log_note,
            "serial/runtime diagnostic tail if flashed during the session",
            "photo or short video only when the operator chooses to capture visual evidence",
            "if old marks are visible, classify them as physical afterimage, stale queued frame, stale asset revision, rescue/procedural fallback leakage, or stale_generation_content",
            "issue triage: fixed, deferred by product decision, accepted benign, or still open",
        ],
        "operator_steps": [
            step(
                "daily_tap_social_response",
                "Daily face tap keeps social mode",
                "在日常表情页轻点上/中/下几个位置，不要长按。",
                "表情看向触点并有整张内脸反应；不会误进入菜单。",
                ["tap position", "observed expression", "whether menu opened accidentally"],
                "tap must remain separate from anywhere 3 s menu entry",
            ),
            step(
                "daily_swipe_pet_response",
                "Daily swipes become pet reactions",
                "在日常表情页分别左/右/上/下滑动。",
                "四个方向都有方向化表情反应；左右滑不会进入菜单。",
                ["swipe direction", "observed response", "false menu entry yes/no"],
                "ordinary swipes must keep feeding pet_behavior instead of navigation",
            ),
            step(
                "anywhere_hold_menu_entry",
                "Anywhere hold enters menu deliberately",
                "按住屏幕任意位置约 3 秒，保持近似静止。",
                "约 650 ms 先出现逗弄反馈，约 3 s 后进入菜单。",
                ["tease visible yes/no", "menu entry time feel", "accidental entry before 3 s yes/no"],
                "menu entry remains a deliberate anywhere long press",
            ),
            step(
                "menu_drag_follow_finger",
                "Menu drag follows the finger",
                "进入菜单后按住列表区域上下拖动，不要从顶部固定系统栏开始。",
                "列表像电子书目录一样跟随手指，顶部系统栏和白色隔离带不被覆盖，松手后停在合理位置。",
                ["drag direction", "finger-follow feel", "header overlap yes/no", "snap/jump yes/no"],
                "continuous 2 px menu frames and fixed 38 px header must stay intact",
            ),
            step(
                "row_press_and_back",
                "Row press shows entry feedback",
                "点击任一菜单项，进入详情页后从左边缘右滑返回。",
                "点击项先有被选中的 press-cue，再到详情页；返回手势可用。",
                ["row", "press cue visible yes/no", "detail arrival visible yes/no", "back success yes/no"],
                "press-cue and target-arrival partial refreshes must not collapse into multi-flash full refresh",
            ),
            step(
                "language_switch_single_language",
                "Language toggle stays single-language",
                "进入偏好页切换中文/英文，再返回主页检查。",
                "每次只显示一种语言；主页和详情页语言一致。",
                ["selected language", "mixed-language text yes/no", "return path"],
                "single Chinese or single English mode must stay product-wide",
            ),
            step(
                "maintenance_single_quiet_flash",
                "Maintenance is one quiet cleanup",
                "完成一次点击或拖动后放手等待约 2 秒。",
                "只出现一次低闪维护感；没有连续多次全刷闪烁。",
                ["gesture before wait", "maintenance flash count", "residual ghosting acceptable yes/no"],
                "0xCF maintenance must stay post-contact and perceived as one quiet cleanup",
            ),
            step(
                "premium_pet_feel",
                "Pet expression feels alive enough for next art pass",
                "在轻点、滑动、菜单进入前后观察表情整体质感。",
                "眼睛、眉、嘴鼻、腮线和小标记共同变化；不像只播放固定眼睛模板。",
                ["best expression", "weakest expression", "specific art adjustment request"],
                "future art tuning must go through genref_sheet_12_inner_faces_v5 style anchors",
            ),
        ],
        "post_session_rule": (
            "Every non-empty operator note is a task input. Fix AI-solvable issues "
            "with machine evidence before asking for another focused review."
        ),
        "review_note_triage_contract": {
            "template_json": rel(REVIEW_TEMPLATE_JSON),
            "template_markdown": rel(REVIEW_TEMPLATE_MD),
            "scope": "Every non-empty operator note from this packet, even on a PASS step.",
            "required_fields": [
                "source_step_id",
                "operator_note",
                "triage_items",
                "resolution_state",
                "evidence_path",
                "next_review_scope",
                "visual_issue_classification",
            ],
            "allowed_visual_issue_classifications": [
                "none",
                "physical afterimage",
                "stale queued frame",
                "stale asset revision",
                "rescue/procedural fallback leakage",
                "stale_generation_content",
            ],
            "allowed_resolution_states": [
                "fixed_with_machine_evidence",
                "deferred_by_product_decision",
                "accepted_benign_with_evidence",
                "open_requires_fix",
            ],
            "publishable_pass_rule": (
                "The acceptance packet cannot be treated as publishable PASS while "
                "any triage item remains open_requires_fix, lacks an evidence_path, "
                "or accepts recognizable stale_generation_content as benign."
            ),
            "re_review_rule": (
                "Ask for another focused review only for the fixed item or the "
                "smallest touched behavior, not for already accepted steps unless "
                "the fix can plausibly regress them."
            ),
        },
        "validation_commands": [
            "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
            "python .\\tools\\render_wb55_touch_visual_review_template.py",
            "python .\\tools\\verify_wb55_touch_visual_review_record.py",
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_screen_generation_release_ledger.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\render_expression_feature_checklist.py",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# WB55 Touch/Visual Acceptance Packet",
        "",
        "This packet is generated. Update it with",
        "`python .\\tools\\render_wb55_touch_visual_acceptance_packet.py --write`.",
        "",
        f"- Status: `{packet['status']}`",
        f"- Gate: `{packet['gate_id']}`",
        f"- Target: `{packet['target']}`",
        f"- Start rule: {packet['start_rule']}",
        f"- Machine precondition: {packet['machine_precondition']}",
        "",
        "## Preflight Commands",
        "",
    ]
    lines.extend(f"- `{command}`" for command in packet["preflight_commands"])
    lines.extend(["", "## Machine State", ""])
    machine_state = packet["machine_state"]
    for key in (
        "resource_revision",
        "resource_crc32",
        "resource_total_bytes",
        "runtime_status",
        "normal_firmware_restored",
        "bilingual_menu_evidence",
        "provision_log",
        "normal_log",
        "runtime_logs_evidence",
    ):
        lines.append(f"- `{key}`: `{machine_state[key]}`")
    for key in (
        "runtime_flash_preflight",
        "runtime_serial_capture_preflight",
        "runtime_hardware_action_card",
        "display_queue_generation_hygiene",
        "generation_release_ledger",
    ):
        lines.append(f"- `{key}`: `{machine_state[key]}`")
    lines.extend(["", "## Operator Steps", ""])
    for index, item in enumerate(packet["operator_steps"], start=1):
        lines.extend([
            f"### {index}. {item['title']}",
            "",
            f"- ID: `{item['id']}`",
            f"- Action: {item['operator_action']}",
            f"- Success signal: {item['success_signal']}",
            f"- Regression guard: {item['regression_guard']}",
            "- Record:",
        ])
        lines.extend(f"  - {value}" for value in item["record"])
        lines.append("")
    lines.extend([
        "## Evidence To Attach",
        "",
    ])
    lines.extend(f"- {value}" for value in packet["evidence_to_attach"])
    triage = packet["review_note_triage_contract"]
    lines.extend([
        "",
        f"Post-session rule: {packet['post_session_rule']}",
        "",
        "## Review Note Triage Contract",
        "",
        f"- Scope: {triage['scope']}",
        f"- Publishable PASS rule: {triage['publishable_pass_rule']}",
        f"- Re-review rule: {triage['re_review_rule']}",
        "- Required fields:",
    ])
    lines.extend(f"  - `{value}`" for value in triage["required_fields"])
    lines.append("- Allowed visual issue classifications:")
    lines.extend(f"  - `{value}`" for value in triage["allowed_visual_issue_classifications"])
    lines.append("- Allowed resolution states:")
    lines.extend(f"  - `{value}`" for value in triage["allowed_resolution_states"])
    lines.append("")
    return "\n".join(lines)


def check_packet(packet: dict[str, Any], errors: list[str]) -> None:
    if packet.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if packet.get("status") != "PENDING_HUMAN":
        errors.append("packet must remain PENDING_HUMAN")
    if packet.get("claim_scope") != "operator_packet_no_hardware_claim":
        errors.append("packet must not claim hardware completion")
    if packet.get("gate_id") != "wb55_touch_visual_acceptance":
        errors.append("packet points at the wrong gate")
    triage = packet.get("review_note_triage_contract", {})
    required_fields = set(triage.get("required_fields", []))
    required_resolution_states = set(triage.get("allowed_resolution_states", []))
    for field in (
        "source_step_id",
        "operator_note",
        "triage_items",
        "resolution_state",
        "evidence_path",
        "next_review_scope",
        "visual_issue_classification",
    ):
        if field not in required_fields:
            errors.append(f"triage contract missing required field {field}")
    for state in (
        "fixed_with_machine_evidence",
        "deferred_by_product_decision",
        "accepted_benign_with_evidence",
        "open_requires_fix",
    ):
        if state not in required_resolution_states:
            errors.append(f"triage contract missing resolution state {state}")
    if "open_requires_fix" not in str(triage.get("publishable_pass_rule", "")):
        errors.append("triage contract must block publishable PASS while items are open")
    if "stale_generation_content" not in str(triage.get("publishable_pass_rule", "")):
        errors.append("triage contract must block benign acceptance of stale_generation_content")
    if "focused review" not in str(triage.get("re_review_rule", "")):
        errors.append("triage contract must keep re-review focused")
    visual_issue_classes = set(triage.get("allowed_visual_issue_classifications", []))
    for cls in (
        "none",
        "physical afterimage",
        "stale queued frame",
        "stale asset revision",
        "rescue/procedural fallback leakage",
        "stale_generation_content",
    ):
        if cls not in visual_issue_classes:
            errors.append(f"triage contract missing visual issue class {cls}")
    if triage.get("template_json") != rel(REVIEW_TEMPLATE_JSON):
        errors.append("triage contract template_json drifted")
    if triage.get("template_markdown") != rel(REVIEW_TEMPLATE_MD):
        errors.append("triage contract template_markdown drifted")
    if not REVIEW_TEMPLATE_JSON.exists():
        errors.append("review template JSON is missing")
    if not REVIEW_TEMPLATE_MD.exists():
        errors.append("review template Markdown is missing")
    if not REVIEW_RECORD_JSON.exists():
        errors.append("review record JSON is missing")
    if "python .\\tools\\render_wb55_touch_visual_review_template.py" not in packet.get("validation_commands", []):
        errors.append("packet validation must include review template renderer")
    if "python .\\tools\\verify_wb55_touch_visual_review_record.py" not in packet.get("validation_commands", []):
        errors.append("packet validation must include filled review record verifier")
    for command in (
        "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
        "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
        "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
        "python .\\tools\\verify_display_queue_generation_hygiene.py",
        "python .\\tools\\verify_screen_generation_release_ledger.py",
    ):
        if command not in packet.get("preflight_commands", []):
            errors.append(f"packet preflight must include {command}")
        if command not in packet.get("validation_commands", []):
            errors.append(f"packet validation must include {command}")
    generation_state = packet.get("machine_state", {}).get("display_queue_generation_hygiene", {})
    if generation_state.get("path") != rel(DISPLAY_QUEUE_GENERATION_HYGIENE):
        errors.append("packet machine_state must link display queue generation hygiene")
    if generation_state.get("status") != "PASS":
        errors.append("display queue generation hygiene must be PASS before touch/visual packet")
    if generation_state.get("coherent_generation") != 1:
        errors.append("display queue generation hygiene must require coherent_generation")
    if generation_state.get("last_stale_discarded") != 3:
        errors.append("display queue generation hygiene must record stale queued frame discard count")
    generation_ledger = packet.get("machine_state", {}).get("generation_release_ledger", {})
    if generation_ledger.get("path") != rel(GENERATION_RELEASE_LEDGER):
        errors.append("packet machine_state must link generation release ledger")
    if generation_ledger.get("status") != "PENDING_RUNTIME_RECHECK":
        errors.append("generation release ledger must remain pending before active runtime logs")
    if generation_ledger.get("cemp_revision") != packet.get("machine_state", {}).get("resource_revision"):
        errors.append("generation release ledger revision must match packet resource revision")
    if generation_ledger.get("cemp_crc32") != packet.get("machine_state", {}).get("resource_crc32"):
        errors.append("generation release ledger CRC must match packet resource CRC")
    if generation_ledger.get("expected_first_frame_marker") != "coherent_generation=1":
        errors.append("generation release ledger must require coherent_generation=1")
    if generation_ledger.get("real_runtime_status") != "NO_GO_MISSING_RUNTIME_LOGS":
        errors.append("generation release ledger must keep runtime NO_GO before logs pass")
    visual_classes = set(generation_ledger.get("visual_triage_classes", []))
    for cls in ("physical afterimage", "stale queued frame", "stale asset revision", "rescue/procedural fallback leakage", "stale_generation_content"):
        if cls not in visual_classes:
            errors.append(f"generation release ledger missing visual triage class {cls}")
    serialized = json.dumps(packet, ensure_ascii=False)
    menu_evidence = json.loads(BILINGUAL_MENU.read_text(encoding="utf-8"))
    resource_pack = menu_evidence.get("resource_pack", {})
    runtime = menu_evidence.get("runtime_evidence", {})
    for token in (
        "daily_tap_social_response",
        "daily_swipe_pet_response",
        "anywhere_hold_menu_entry",
        "menu_drag_follow_finger",
        "row_press_and_back",
        "language_switch_single_language",
        "maintenance_single_quiet_flash",
        "premium_pet_feel",
        "650 ms",
        "3 s",
        "0xCF",
        "genref_sheet_12_inner_faces_v5",
        "verify_premium_pet_art_contract.py",
        "verify_companion_screen_pre_acceptance_health.py",
        "verify_wb55_runtime_flash_preflight.py",
        "verify_wb55_runtime_serial_capture_preflight.py",
        "render_wb55_runtime_hardware_action_card.py",
        "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT",
        "static_serial_capture_contract_no_hardware_claim",
        rel(RUNTIME_FLASH_PREFLIGHT),
        rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT),
        rel(RUNTIME_HARDWARE_ACTION_CARD),
        rel(DISPLAY_QUEUE_GENERATION_HYGIENE),
        rel(GENERATION_RELEASE_LEDGER),
        "verify_display_queue_generation_hygiene.py",
        "verify_screen_generation_release_ledger.py",
        "physical afterimage",
        "stale queued frame",
        "stale asset revision",
        "rescue/procedural fallback leakage",
        "stale_generation_content",
        "coherent_generation",
        "last_stale_discarded",
        "verify_wb55_screen_runtime_recheck_logs.py",
        "promote_wb55_screen_runtime_recheck.py",
        "NO_GO_RUNTIME_RECHECK_PENDING",
        "review_note_triage_contract",
        rel(REVIEW_TEMPLATE_JSON),
        rel(REVIEW_TEMPLATE_MD),
        rel(REVIEW_RECORD_JSON),
        "render_wb55_touch_visual_review_template.py",
        "verify_wb55_touch_visual_review_record.py",
        "source_step_id",
        "triage_items",
        "visual_issue_classification",
        "fixed_with_machine_evidence",
        "deferred_by_product_decision",
        "accepted_benign_with_evidence",
        "open_requires_fix",
        "publishable PASS",
        str(runtime.get("status")),
        f'"resource_revision": {resource_pack.get("revision")}',
        str(resource_pack.get("pack_crc32")),
        str(resource_pack.get("total_bytes")),
        "顶部固定系统栏",
    ):
        if token not in serialized:
            errors.append(f"packet missing {token}")


def check_project_links(errors: list[str]) -> None:
    index = json.loads(ACCEPTANCE_INDEX.read_text(encoding="utf-8"))
    items = [item for item in index.get("items", []) if item.get("id") == "wb55_touch_visual_acceptance"]
    if len(items) != 1:
        errors.append("acceptance index must contain one wb55_touch_visual_acceptance item")
    else:
        item = items[0]
        if rel(DEFAULT_JSON) not in item.get("evidence_paths", []):
            errors.append("wb55_touch_visual_acceptance item must link the packet JSON")
        if "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py" not in item.get("validation_commands", []):
            errors.append("wb55_touch_visual_acceptance item must run the packet verifier")
    for path, label in ((FEATURE_CHECKLIST, "feature checklist"), (SCREEN_DOC, "screen doc"), (PROJECT_PLAN, "project plan")):
        text = path.read_text(encoding="utf-8")
        for token in ("wb55_touch_visual_acceptance", "touch visual acceptance packet"):
            if token not in text:
                errors.append(f"{label} missing {token}")


def write_outputs(json_path: pathlib.Path, md_path: pathlib.Path, packet: dict[str, Any], markdown: str) -> None:
    json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    md_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    packet = build_packet()
    markdown = render_markdown(packet)
    errors: list[str] = []
    check_packet(packet, errors)

    if args.write:
        write_outputs(json_path, md_path, packet, markdown)
    else:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json.loads(json_path.read_text(encoding="utf-8")) != packet:
            errors.append(f"stale {rel(json_path)}")
        if not md_path.exists():
            errors.append(f"missing {rel(md_path)}")
        elif md_path.read_text(encoding="utf-8") != markdown:
            errors.append(f"stale {rel(md_path)}")
        check_project_links(errors)

    if errors:
        print("FAIL: WB55 touch/visual acceptance packet checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 touch/visual acceptance packet verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
