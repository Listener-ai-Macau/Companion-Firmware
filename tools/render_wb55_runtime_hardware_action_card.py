#!/usr/bin/env python3
"""Render the Chinese WB55 active-resource runtime hardware action card."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE = current_candidate()
RUN_REPORT = CANDIDATE.run_root / "runtime-recheck-run.json"
RUNNER_FIXTURE = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-runner.json"
RUNTIME_LOGS = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
PROMOTION = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
PRE_ACCEPTANCE = ROOT / "docs/validation/companion-screen-pre-acceptance-health.json"
FLASH_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-flash-preflight.json"
SERIAL_CAPTURE_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json"
GENERATION_RELEASE_LEDGER = ROOT / "docs/validation/companion-screen-generation-release-ledger.json"
BUILD_MATRIX = ROOT / "docs/validation/companion-screen-wb55-build-matrix.json"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-wb55-runtime-hardware-action-card.md"
SCHEMA_ID = "companion.screen.wb55_runtime_hardware_action_card.v1"
PENDING_RUNTIME_LOG_STATUSES = {
    "NO_GO_MISSING_RUNTIME_LOGS",
    "NO_GO_INCOMPLETE_RUNTIME_MARKERS",
}


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def command_line(step: dict[str, Any]) -> str:
    return " ".join([str(step.get("command", "")), *[str(arg) for arg in step.get("arguments", [])]])


def build_card() -> dict[str, Any]:
    run_report = load_json(RUN_REPORT)
    runner = load_json(RUNNER_FIXTURE)
    runtime_logs = load_json(RUNTIME_LOGS)
    promotion = load_json(PROMOTION)
    pre_acceptance = load_json(PRE_ACCEPTANCE)
    flash_preflight = load_json(FLASH_PREFLIGHT)
    serial_preflight = load_json(SERIAL_CAPTURE_PREFLIGHT)
    generation_ledger = load_json(GENERATION_RELEASE_LEDGER)
    build_matrix = load_json(BUILD_MATRIX)
    steps = run_report.get("steps", [])
    quiet_profile_recheck_required = bool(
        run_report.get("resource", {}).get("quiet_interaction_profile_recheck_required")
    )
    post_run_commands = [
        "python .\\tools\\verify_screen_generation_release_ledger.py",
        "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py --write",
    ]
    if promotion.get("status") != "APPLIED":
        post_run_commands.append("python .\\tools\\promote_wb55_screen_runtime_recheck.py --apply")
    post_run_commands.extend([
        "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
        "python .\\tools\\verify_companion_screen_goal_audit.py",
    ])
    step_cards = [
        {
            "id": step.get("id"),
            "command": command_line(step),
            "operator_meaning": {
                "flash_provision": "刷入带外部 CEMP 资源写入逻辑的 provision 固件。",
                "capture_provision": "复位并抓取 provision 启动串口日志，证明资源写入/挂载链路。",
                "flash_normal": "刷回普通运行固件，避免设备停留在 provision 镜像。",
                "capture_normal": f"复位并抓取 normal 启动串口日志，证明普通固件从外部 Flash 挂载 rev{CANDIDATE.revision}。",
            }.get(str(step.get("id")), "执行 runtime recheck 子步骤。"),
        }
        for step in steps
    ]
    return {
        "schema_id": SCHEMA_ID,
        "status": "NO_GO_WAITING_FOR_REAL_HARDWARE_RUN",
        "claim_scope": "operator_action_card_no_hardware_claim",
        "source_run_report": rel(RUN_REPORT),
        "source_runner_fixture": rel(RUNNER_FIXTURE),
        "source_flash_preflight": rel(FLASH_PREFLIGHT),
        "source_serial_capture_preflight": rel(SERIAL_CAPTURE_PREFLIGHT),
        "source_generation_release_ledger": rel(GENERATION_RELEASE_LEDGER),
        "source_build_matrix": rel(BUILD_MATRIX),
        "target": run_report.get("target"),
        "resource": run_report.get("resource", {}),
        "quiet_interaction_profile_recheck_required": quiet_profile_recheck_required,
        "build_matrix": {
            "path": rel(BUILD_MATRIX),
            "status": build_matrix.get("status"),
            "variants": sorted(build_matrix.get("build_variants", {}).keys()),
            "screen_asset_provision_size": build_matrix.get("build_log_evidence", {})
            .get("screen_asset_provision", {})
            .get("size"),
            "screen_asset_provision_log": build_matrix.get("build_variants", {})
            .get("screen_asset_provision", {})
            .get("log"),
            "validation_commands": build_matrix.get("validation_commands", []),
        },
        "generation_release_ledger": {
            "path": rel(GENERATION_RELEASE_LEDGER),
            "status": generation_ledger.get("status"),
            "purpose": "SCR-17 release ledger for new/old generation interleaving prevention",
            "cemp_revision": generation_ledger.get("candidate", {}).get("cemp_revision"),
            "cemp_crc32": generation_ledger.get("candidate", {}).get("cemp_crc32"),
            "expected_first_frame_marker": generation_ledger.get("first_frame_evidence", {}).get("expected_marker"),
            "model_last_stale_discarded": generation_ledger.get("first_frame_evidence", {}).get("model_last_stale_discarded"),
            "real_runtime_status": generation_ledger.get("first_frame_evidence", {}).get("real_runtime_status"),
            "ui_assets_ota_in_scope": generation_ledger.get("ota_transaction_rule", {}).get("ui_assets_ota_in_scope"),
        },
        "current_gates": {
            "runtime_logs": runtime_logs.get("status"),
            "runtime_promotion": promotion.get("status"),
            "pre_acceptance": pre_acceptance.get("status"),
            "pre_acceptance_blocking_reasons": pre_acceptance.get("blocking_reasons", []),
            "human_review": pre_acceptance.get("operator_review_record", {}).get("status"),
        },
        "flash_preflight": {
            "status": flash_preflight.get("status"),
            "normal_image": flash_preflight.get("normal", {}).get("image"),
            "normal_image_exists": flash_preflight.get("normal", {}).get("image_exists"),
            "normal_flash_timeout_seconds": flash_preflight.get("normal", {}).get("flash_timeout_seconds"),
            "provision_image": flash_preflight.get("screen_asset_provision", {}).get("image"),
            "provision_image_exists": flash_preflight.get("screen_asset_provision", {}).get("image_exists"),
            "provision_flash_timeout_seconds": flash_preflight.get("screen_asset_provision", {}).get("flash_timeout_seconds"),
            "timeout_contract": flash_preflight.get("flash_timeout_contract", {}),
            "programmer_exists": (
                flash_preflight.get("normal", {}).get("programmer_exists") is True
                and flash_preflight.get("screen_asset_provision", {}).get("programmer_exists") is True
            ),
        },
        "serial_capture_preflight": {
            "status": serial_preflight.get("status"),
            "claim_scope": serial_preflight.get("claim_scope"),
            "capture_script": serial_preflight.get("source_files", {}).get("capture_script"),
            "runtime_runner": serial_preflight.get("source_files", {}).get("runtime_runner"),
            "runtime_run_report": serial_preflight.get("source_files", {}).get("runtime_run_report"),
            "raw_log_filename": serial_preflight.get("capture_script_contract", {}).get("outputs", {}).get("raw_log_filename"),
            "summary_json_filename": serial_preflight.get("capture_script_contract", {}).get("outputs", {}).get("summary_json_filename"),
            "empty_capture_fails": serial_preflight.get("capture_script_contract", {}).get("outputs", {}).get("empty_capture_failure_token"),
            "summary_records_bytes_read": serial_preflight.get("capture_script_contract", {}).get("outputs", {}).get("summary_bytes_read_token"),
            "reset_timeout_seconds": serial_preflight.get("empty_capture_selftest", {}).get("reset_timeout_seconds"),
            "empty_capture_selftest": serial_preflight.get("empty_capture_selftest", {}),
            "reset_timeout_selftest": serial_preflight.get("reset_timeout_selftest", {}),
            "no_hardware_claim": serial_preflight.get("claim_scope") == "static_serial_capture_contract_no_hardware_claim",
        },
        "runner_safety": {
            "restores_normal_firmware_after_failure": runner.get("safety_contract", {}).get("restores_normal_firmware_after_failure"),
            "run_report_records_normal_firmware_restored": "normal_firmware_restored" in json.dumps(runner, ensure_ascii=False),
        },
        "selftest_recovery": {
            "command": (
                "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 "
                f"-SelfTestRecovery -OutRoot .\\.cache\\validation\\rev{CANDIDATE.revision}-runtime-recovery-selftest"
            ),
            "claim_scope": runner.get("recovery_selftest", {}).get("claim_scope"),
            "report": runner.get("recovery_selftest", {}).get("report_path"),
            "report_status": runner.get("recovery_selftest", {}).get("report_status"),
            "normal_firmware_restored": runner.get("recovery_selftest", {}).get("normal_firmware_restored"),
            "result_ids": runner.get("recovery_selftest", {}).get("result_ids", []),
            "result_statuses": runner.get("recovery_selftest", {}).get("result_statuses", {}),
        },
        "workflow_lock_command": (
            "pwsh -NoProfile -File C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow\\scripts\\aiw.ps1 "
            f"with-lock -Resource Companion-WB55 -Purpose \"Companion WB55 rev{CANDIDATE.revision} screen runtime recheck\" "
            "-Run pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -Execute -WorkflowLockHeld"
        ),
        "check_only_command": "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
        "hardware_steps": step_cards,
        "expected_runtime_markers": run_report.get("expected_runtime_markers", []),
        "expected_provision_runtime_markers": run_report.get("expected_provision_runtime_markers", []),
        "expected_normal_runtime_markers": run_report.get("expected_normal_runtime_markers", []),
        "post_run_commands": post_run_commands,
        "do_not_do": [
            f"不要手工把 {CANDIDATE.pending_status} 改成 PASS。",
            "不要跳过 normal 固件恢复；provision 只用于写资源。",
            "如果 provision 后失败，runner 会尝试 flash_normal_after_failure；若 normal_firmware_restored 不是 true，不要继续验收。",
            "不要在 runtime logs PASS 和 promotion --apply 前启动触摸/视觉人工验收。",
            "不要把 DRY-RUN report 当作真实硬件日志。",
        ],
        "human_acceptance_start_rule": (
            f"只有 rev{CANDIDATE.revision} provision/normal runtime logs 验证 PASS、当前 quiet interaction "
            "profile 在 normal log 中完整出现、resource promotion 已适用且 pre-acceptance health PASS 后，"
            "操作者明确说“开始验收”，才进入触摸/视觉人工验收。"
        ),
        "validation_commands": [
            "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
            (
                "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 "
                f"-SelfTestRecovery -OutRoot .\\.cache\\validation\\rev{CANDIDATE.revision}-runtime-recovery-selftest"
            ),
            "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
            "python .\\tools\\verify_screen_generation_release_ledger.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
        ],
    }


def render_markdown(card: dict[str, Any]) -> str:
    resource = card["resource"]
    build_matrix = card.get("build_matrix", {})
    generation_ledger = card.get("generation_release_ledger", {})
    gates = card["current_gates"]
    flash = card["flash_preflight"]
    serial = card["serial_capture_preflight"]
    runner_safety = card.get("runner_safety", {})
    selftest = card.get("selftest_recovery", {})
    empty_serial_selftest = serial.get("empty_capture_selftest", {})
    reset_timeout_selftest = serial.get("reset_timeout_selftest", {})
    lines = [
        f"# WB55 Rev{CANDIDATE.revision} Runtime 硬件执行卡",
        "",
        f"这张卡是生成文件，只用于 rev{CANDIDATE.revision} 机器 runtime recheck。它不代表人工触摸/视觉验收已开始。",
        "",
        f"- 状态: `{card['status']}`",
        f"- 目标: `{card['target']}`",
        f"- 资源: revision `{resource.get('revision')}`, bytes `{resource.get('total_bytes')}`, CRC `{resource.get('pack_crc32')}`",
        f"- build matrix: `{build_matrix.get('status')}`, variants `{', '.join(build_matrix.get('variants', []))}`",
        f"- ScreenAssetProvision size: `{build_matrix.get('screen_asset_provision_size')}`",
        f"- SCR-17 ledger: `{generation_ledger.get('status')}`, first frame `{generation_ledger.get('expected_first_frame_marker')}`, stale discard model `{generation_ledger.get('model_last_stale_discarded')}`",
        f"- runtime logs gate: `{gates.get('runtime_logs')}`",
        f"- promotion gate: `{gates.get('runtime_promotion')}`",
        f"- pre-acceptance: `{gates.get('pre_acceptance')}`",
        f"- human review record: `{gates.get('human_review')}`",
        f"- flash preflight: `{flash.get('status')}`",
        f"- serial capture preflight: `{serial.get('status')}`",
        f"- failure recovery restores normal: `{runner_safety.get('restores_normal_firmware_after_failure')}`",
        f"- no-hardware recovery self-test: `{selftest.get('report_status')}`, restored normal `{selftest.get('normal_firmware_restored')}`",
        "",
        "## 先做预演",
        "",
        f"```powershell\n{card['check_only_command']}\n```",
        "",
        "再跑失败恢复自测。这个命令不刷机、不开串口，只证明 provision 后失败会触发 normal 恢复：",
        "",
        f"```powershell\n{selftest.get('command')}\n```",
        "",
        f"- self-test report: `{selftest.get('report')}`",
        f"- expected status: `FAIL`",
        f"- expected recovery: `flash_normal_after_failure=PASS`, `normal_firmware_restored=true`",
        "",
        "空串口日志自测也必须保持 FAIL；它不打开 COM 口，只证明 0 字节日志不会被当作 runtime evidence：",
        "",
        f"```powershell\n{empty_serial_selftest.get('command')}\n```",
        "",
        f"- self-test summary: `{empty_serial_selftest.get('summary_path')}`",
        f"- expected status: `FAIL`",
        f"- expected bytes_read: `0`",
        "",
        "复位超时自测也必须保持 FAIL；它不打开真实硬件，只用 stub 进程证明 STM32 reset 不会无限挂住：",
        "",
        f"```powershell\n{reset_timeout_selftest.get('command')}\n```",
        "",
        f"- self-test summary: `{reset_timeout_selftest.get('summary_path')}`",
        f"- expected status: `FAIL`",
        f"- expected reset timeout error: `reset timed out after 5 second(s)`",
        "",
        "## 真实硬件执行",
        "",
        "刷机预检：",
        "",
        f"- provision image: `{flash.get('provision_image')}` (`exists={flash.get('provision_image_exists')}`)",
        f"- normal image: `{flash.get('normal_image')}` (`exists={flash.get('normal_image_exists')}`)",
        f"- programmer exists: `{flash.get('programmer_exists')}`",
        f"- flash timeout: provision `{flash.get('provision_flash_timeout_seconds')}` s, normal `{flash.get('normal_flash_timeout_seconds')}` s",
        f"- serial capture script: `{serial.get('capture_script')}`",
        f"- serial outputs: `{serial.get('raw_log_filename')}`, `{serial.get('summary_json_filename')}`",
        f"- reset timeout: `{serial.get('reset_timeout_seconds')}` s",
        f"- empty serial capture fails: `{serial.get('empty_capture_fails')}`",
        f"- empty serial self-test: `{empty_serial_selftest.get('summary_status')}`, bytes `{empty_serial_selftest.get('bytes_read')}`",
        f"- reset timeout self-test: `{reset_timeout_selftest.get('summary_status')}`, reset stdout `{reset_timeout_selftest.get('reset_stdout_exists')}`, reset stderr `{reset_timeout_selftest.get('reset_stderr_exists')}`",
        "",
        "必须通过 workflow hardware lock 执行：",
        "",
        f"```powershell\n{card['workflow_lock_command']}\n```",
        "",
        "该命令内部按顺序执行：",
        "",
    ]
    for index, step in enumerate(card["hardware_steps"], start=1):
        lines.extend(
            [
                f"{index}. `{step['id']}`",
                f"   - {step['operator_meaning']}",
                f"   - `{step['command']}`",
            ]
        )
    lines.extend(["", "## Provision 串口日志必须包含", ""])
    lines.extend(f"- `{marker}`" for marker in card["expected_provision_runtime_markers"])
    lines.extend(["", "## Normal 串口日志必须包含", ""])
    lines.extend(f"- `{marker}`" for marker in card["expected_normal_runtime_markers"])
    lines.extend([
        "",
        f"这些 marker 同时用于 SCR-17 release ledger：确认 rev{CANDIDATE.revision} 是唯一 active generation，旧队列已丢弃，首帧是当前 generation。",
    ])
    lines.extend(["", "## 跑完硬件后", ""])
    lines.extend(f"```powershell\n{command}\n```" for command in card["post_run_commands"])
    lines.extend(["", "## 不要做", ""])
    lines.extend(f"- {item}" for item in card["do_not_do"])
    lines.extend(["", f"人工验收入口规则：{card['human_acceptance_start_rule']}", ""])
    return "\n".join(lines)


def verify(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if card.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if card.get("status") != "NO_GO_WAITING_FOR_REAL_HARDWARE_RUN":
        errors.append("action card must not claim hardware completion")
    if card.get("claim_scope") != "operator_action_card_no_hardware_claim":
        errors.append("action card claim scope drifted")
    resource = card.get("resource", {})
    if resource.get("revision") != CANDIDATE.revision:
        errors.append("action card resource revision must match the active candidate")
    if resource.get("total_bytes") != CANDIDATE.total_bytes:
        errors.append("action card resource byte count must match the active candidate")
    if resource.get("pack_crc32") != CANDIDATE.pack_crc32:
        errors.append("action card resource CRC must match the active candidate")
    expected_common_markers = list(CANDIDATE.common_markers)
    expected_provision_markers = expected_common_markers + [
        "external_store=ready",
        "preview_started name=idle",
    ]
    quiet_marker = (
        "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 "
        "ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 "
        "refresh_policy=partial_x5_then_fast_cleanup"
    )
    expected_normal_markers = expected_common_markers + [
        quiet_marker,
        "frame rotation=180 mirror_x=1",
        "preview_started name=idle",
    ]
    if card.get("expected_runtime_markers") != expected_common_markers:
        errors.append("action card common markers must follow the active CEMP manifest")
    if card.get("expected_provision_runtime_markers") != expected_provision_markers:
        errors.append("action card provision markers drifted")
    if card.get("expected_normal_runtime_markers") != expected_normal_markers:
        errors.append("action card normal markers must require the quiet interaction profile")
    build_matrix = card.get("build_matrix", {})
    if build_matrix.get("path") != rel(BUILD_MATRIX):
        errors.append("action card must link WB55 build matrix")
    if build_matrix.get("status") != "PASS":
        errors.append("WB55 build matrix must be PASS before runtime hardware action")
    if build_matrix.get("variants") != ["dry_run_default", "screen_asset_provision", "ssd1681_real_panel"]:
        errors.append("WB55 build matrix must include dry-run, ScreenAssetProvision, and SSD1681 variants")
    provision_size = build_matrix.get("screen_asset_provision_size", {})
    if not all(isinstance(provision_size.get(key), int) and provision_size[key] >= 0 for key in ("text", "data", "bss", "dec")):
        errors.append("ScreenAssetProvision build size must remain a valid current build measurement")
    if not isinstance(provision_size.get("hex"), str) or not provision_size.get("hex"):
        errors.append("ScreenAssetProvision build size must include a hexadecimal measurement")
    if build_matrix.get("screen_asset_provision_log") != ".cache/validation/wb55-build-matrix/screen-asset-provision-build.log":
        errors.append("ScreenAssetProvision build log path drifted")
    if "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force" not in build_matrix.get("validation_commands", []):
        errors.append("WB55 build matrix must validate ScreenAssetProvision build command")
    generation_ledger = card.get("generation_release_ledger", {})
    if generation_ledger.get("path") != rel(GENERATION_RELEASE_LEDGER):
        errors.append("action card must link SCR-17 generation release ledger")
    quiet_profile_recheck_required = card.get("quiet_interaction_profile_recheck_required") is True
    if quiet_profile_recheck_required:
        if generation_ledger.get("status") != "RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING":
            errors.append("quiet-profile recheck must retain the prior promoted generation ledger")
    elif generation_ledger.get("status") != "PENDING_RUNTIME_RECHECK":
        errors.append("generation release ledger must remain pending before first runtime logs")
    if generation_ledger.get("cemp_revision") != resource.get("revision"):
        errors.append("generation release ledger revision must match action-card resource")
    if generation_ledger.get("cemp_crc32") != resource.get("pack_crc32"):
        errors.append("generation release ledger CRC must match action-card resource")
    if generation_ledger.get("expected_first_frame_marker") != "coherent_generation=1":
        errors.append("generation release ledger must require coherent_generation=1")
    if generation_ledger.get("model_last_stale_discarded") != 3:
        errors.append("generation release ledger must carry stale-discard model")
    if quiet_profile_recheck_required:
        if generation_ledger.get("real_runtime_status") != "PASS":
            errors.append("quiet-profile recheck must retain prior PASS resource runtime evidence")
    elif generation_ledger.get("real_runtime_status") not in PENDING_RUNTIME_LOG_STATUSES:
        errors.append("generation release ledger must keep a non-PASS runtime status before first promotion")
    if generation_ledger.get("ui_assets_ota_in_scope") is not True:
        errors.append("generation release ledger must keep ui_assets OTA in scope")
    gates = card.get("current_gates", {})
    if gates.get("runtime_logs") not in PENDING_RUNTIME_LOG_STATUSES:
        errors.append("current gate runtime_logs must remain a non-PASS runtime status")
    expected_gates = (
        {
            "runtime_promotion": "APPLIED",
            "pre_acceptance": "NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING",
            "human_review": "NO_GO_OPEN_REVIEW_ITEMS",
        }
        if quiet_profile_recheck_required else {
            "runtime_promotion": "NO_GO_LOGS_NOT_PASS",
            "pre_acceptance": "NO_GO_RUNTIME_RECHECK_PENDING",
            "human_review": "NO_GO_NOT_STARTED",
        }
    )
    for key, value in expected_gates.items():
        if gates.get(key) != value:
            errors.append(f"current gate {key} must remain {value}")
    if quiet_profile_recheck_required:
        for reason in ("quiet_interaction_profile_runtime_recheck", "open_operator_review_items"):
            if reason not in gates.get("pre_acceptance_blocking_reasons", []):
                errors.append(f"quiet-profile action card must retain pre-acceptance blocker {reason}")
    post_run_commands = card.get("post_run_commands", [])
    if quiet_profile_recheck_required:
        if "python .\\tools\\promote_wb55_screen_runtime_recheck.py --apply" in post_run_commands:
            errors.append("quiet-profile recheck must not re-promote an already accepted resource revision")
    elif "python .\\tools\\promote_wb55_screen_runtime_recheck.py --apply" not in post_run_commands:
        errors.append("first runtime promotion must remain in the post-run commands")
    flash = card.get("flash_preflight", {})
    if flash.get("status") != "PASS":
        errors.append("flash preflight status must be PASS")
    if flash.get("normal_image_exists") is not True:
        errors.append("normal image must exist in flash preflight")
    if flash.get("provision_image_exists") is not True:
        errors.append("provision image must exist in flash preflight")
    if flash.get("programmer_exists") is not True:
        errors.append("STM32 programmer must exist in flash preflight")
    if flash.get("normal_flash_timeout_seconds") != 120:
        errors.append("normal flash timeout must be 120 seconds")
    if flash.get("provision_flash_timeout_seconds") != 120:
        errors.append("provision flash timeout must be 120 seconds")
    for key, value in flash.get("timeout_contract", {}).items():
        if value is not True:
            errors.append(f"flash timeout contract {key} must be true")
    serial = card.get("serial_capture_preflight", {})
    if serial.get("status") != "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT":
        errors.append("serial capture preflight must be PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT")
    if serial.get("claim_scope") != "static_serial_capture_contract_no_hardware_claim":
        errors.append("serial capture preflight must not claim hardware completion")
    if serial.get("no_hardware_claim") is not True:
        errors.append("serial capture preflight no_hardware_claim must be true")
    if serial.get("raw_log_filename") != "nucleo-serial-raw.log":
        errors.append("serial capture preflight raw log filename drifted")
    if serial.get("summary_json_filename") != "nucleo-serial-summary.json":
        errors.append("serial capture preflight summary filename drifted")
    if serial.get("empty_capture_fails") is not True:
        errors.append("serial capture must reject empty runtime evidence")
    if serial.get("summary_records_bytes_read") is not True:
        errors.append("serial capture summary must record bytes_read")
    if serial.get("reset_timeout_seconds") != 15:
        errors.append("serial capture reset timeout must be 15 seconds")
    empty_serial_selftest = serial.get("empty_capture_selftest", {})
    if empty_serial_selftest.get("claim_scope") != "stubbed_empty_capture_no_hardware_claim":
        errors.append("empty serial self-test must remain no-hardware")
    if empty_serial_selftest.get("summary_status") != "FAIL":
        errors.append("empty serial self-test summary must be FAIL")
    if empty_serial_selftest.get("bytes_read") != 0:
        errors.append("empty serial self-test bytes_read must be 0")
    if empty_serial_selftest.get("summary_mode") != "selftest-empty-capture":
        errors.append("empty serial self-test mode drifted")
    reset_timeout_selftest = serial.get("reset_timeout_selftest", {})
    if reset_timeout_selftest.get("claim_scope") != "stubbed_reset_timeout_no_hardware_claim":
        errors.append("reset timeout self-test must remain no-hardware")
    if reset_timeout_selftest.get("summary_status") != "FAIL":
        errors.append("reset timeout self-test summary must be FAIL")
    if reset_timeout_selftest.get("bytes_read") != 0:
        errors.append("reset timeout self-test bytes_read must be 0")
    if reset_timeout_selftest.get("summary_mode") != "selftest-reset-timeout":
        errors.append("reset timeout self-test mode drifted")
    if reset_timeout_selftest.get("reset_timeout_seconds") != 15:
        errors.append("reset timeout self-test must keep default 15 second reset timeout")
    if reset_timeout_selftest.get("reset_stdout_exists") is not True:
        errors.append("reset timeout self-test must write reset stdout log")
    if reset_timeout_selftest.get("reset_stderr_exists") is not True:
        errors.append("reset timeout self-test must write reset stderr log")
    if not any("reset timed out after 5 second" in str(error) for error in reset_timeout_selftest.get("errors", [])):
        errors.append("reset timeout self-test must record timeout error")
    runner_safety = card.get("runner_safety", {})
    if runner_safety.get("restores_normal_firmware_after_failure") is not True:
        errors.append("runner safety must restore normal firmware after provision failure")
    if runner_safety.get("run_report_records_normal_firmware_restored") is not True:
        errors.append("runner safety must record normal_firmware_restored in the run report")
    selftest = card.get("selftest_recovery", {})
    if selftest.get("claim_scope") != "stubbed_failure_recovery_no_hardware_claim":
        errors.append("self-test recovery must stay a no-hardware claim")
    if selftest.get("report_status") != "FAIL":
        errors.append("self-test recovery report status must be FAIL")
    if selftest.get("normal_firmware_restored") is not True:
        errors.append("self-test recovery must prove normal_firmware_restored")
    if selftest.get("result_ids") != ["flash_provision", "capture_provision", "flash_normal_after_failure"]:
        errors.append("self-test recovery result ids drifted")
    if selftest.get("result_statuses", {}).get("flash_normal_after_failure") != "PASS":
        errors.append("self-test recovery must pass flash_normal_after_failure")
    step_ids = [step.get("id") for step in card.get("hardware_steps", [])]
    if step_ids != ["flash_provision", "capture_provision", "flash_normal", "capture_normal"]:
        errors.append("hardware steps must keep provision/capture/normal/capture order")
    serialized = json.dumps(card, ensure_ascii=False)
    required_tokens = [
        "Companion-WB55",
        "run_wb55_screen_runtime_recheck.ps1 -Execute -WorkflowLockHeld",
        "verify_wb55_screen_runtime_recheck_logs.py",
        "verify_screen_generation_release_ledger.py",
        "companion-screen-generation-release-ledger.json",
        "companion-screen-wb55-build-matrix.json",
        "screen_asset_provision",
        "build_screen_asset_provision",
        "SCR-17 release ledger",
        "verify_wb55_runtime_flash_preflight.py",
        "flash_timeout_seconds",
        "verify_wb55_runtime_serial_capture_preflight.py",
        "empty_capture_fails",
        "reset_timeout_seconds",
        "stubbed_empty_capture_no_hardware_claim",
        "SelfTestEmptyCapture",
        "stubbed_reset_timeout_no_hardware_claim",
        "SelfTestResetTimeout",
        "reset timed out after 5 second",
        "verify_companion_screen_pre_acceptance_health.py",
        "开始验收",
        "不要手工",
        "不要把 DRY-RUN report 当作真实硬件日志",
        "flash_normal_after_failure",
        "normal_firmware_restored",
        "SelfTestRecovery",
        "stubbed_failure_recovery_no_hardware_claim",
        f"revision={CANDIDATE.revision}",
        "source=external_flash",
        "touch-health] detected=1 identity=1 addr=0x38",
        f"queue_generation revision={CANDIDATE.revision}",
        "coherent_generation=1",
        "generation_switches=",
        "last_stale_discarded=",
        "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0",
    ]
    if not quiet_profile_recheck_required:
        required_tokens.append("promote_wb55_screen_runtime_recheck.py --apply")
    for token in required_tokens:
        if token not in serialized:
            errors.append(f"action card missing token {token}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    md_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    card = build_card()
    markdown = render_markdown(card)
    errors = verify(card)

    if args.write and not errors:
        json_path.write_text(json.dumps(card, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(markdown, encoding="utf-8")
    elif not args.write:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json.loads(json_path.read_text(encoding="utf-8")) != card:
            errors.append(f"stale {rel(json_path)}")
        if not md_path.exists():
            errors.append(f"missing {rel(md_path)}")
        elif md_path.read_text(encoding="utf-8") != markdown:
            errors.append(f"stale {rel(md_path)}")

    if errors:
        print("FAIL: WB55 runtime hardware action card checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime hardware action card verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
