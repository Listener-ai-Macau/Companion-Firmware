#!/usr/bin/env python3
"""Archive the sealed R8-R2 runtime, including all selector response hashes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from verify_wb55_ssd1681_ram_command_target_r8_log import READ_RE, STAGES


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / ".cache/validation/wb55-ram-command-target-r8-r2-execute-20260721-r1"
RAW = RUN_ROOT / "candidate-capture/nucleo-serial-raw.log"
CONTROLLER = RUN_ROOT / "controller-state.json"
PRECLEAN = RUN_ROOT / "preclean-white.json"
POSTCLEAN = RUN_ROOT / "postclean-white.json"
RESTORE = RUN_ROOT / "restore-gate.json"
NORMAL = RUN_ROOT / "normal-resume.json"
STAGE = RUN_ROOT / "stage-run.json"
LAUNCH = RUN_ROOT / "persistent-launch.json"
STDOUT = RUN_ROOT / "runner.stdout.log"
STDERR = RUN_ROOT / "runner.stderr.log"
OUTPUT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json"

EXPECTED_STATUS = {
    CONTROLLER: "PASS_MACHINE_R8_COMMAND_TARGET_MAPPING",
    PRECLEAN: "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE",
    POSTCLEAN: "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE",
    RESTORE: "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES",
    NORMAL: "PASS_APPLICATION_RESUMED_AFTER_BACKUP",
    STAGE: "PASS_MACHINE_RAM_COMMAND_TARGET_R8_RESTORED",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def main() -> int:
    errors: list[str] = []
    required = (RAW, CONTROLLER, PRECLEAN, POSTCLEAN, RESTORE, NORMAL, STAGE, LAUNCH, STDOUT, STDERR)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        errors.append(f"missing runtime inputs: {missing}")

    documents: dict[Path, dict] = {}
    if not errors:
        for path in (*EXPECTED_STATUS.keys(), LAUNCH):
            try:
                documents[path] = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"cannot load {path}: {exc}")

    for path, expected in EXPECTED_STATUS.items():
        if documents.get(path, {}).get("status") != expected:
            errors.append(f"status differs: {path}")

    raw_text = RAW.read_text(encoding="utf-8", errors="replace") if RAW.is_file() else ""
    start = raw_text.find("[epaper] ram_command_target_r8 start ")
    end = raw_text.find("[epaper] ram_command_target_r8 result=", max(start, 0))
    if start < 0 or end < 0:
        errors.append("R8 raw scope markers are missing")
        scoped = raw_text
    else:
        scoped = raw_text[start:]

    responses: list[dict[str, object]] = []
    seen: dict[tuple[str, int, int], bytes] = {}
    for match in READ_RE.finditer(scoped):
        stage, selector_s, repeat_s, length_s, read_ok, repeat_ok, raw_hex, gpio = match.groups()
        selector = int(selector_s)
        repeat = int(repeat_s)
        key = (stage, selector, repeat)
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError:
            errors.append(f"non-hex selector response: {key}")
            continue
        if key in seen:
            errors.append(f"duplicate selector response: {key}")
            continue
        seen[key] = raw
        responses.append({
            "stage": stage,
            "selector": selector,
            "repeat": repeat,
            "reported_length": int(length_s),
            "read_ok": read_ok == "1",
            "repeat_ok": repeat_ok == "1",
            "gpio_restore": gpio == "1",
            "response_bytes": len(raw),
            "response_sha256": sha_bytes(raw),
            "dummy_hex": raw[:1].hex().upper(),
            "payload_bytes": max(0, len(raw) - 1),
            "payload_sha256": sha_bytes(raw[1:]),
        })

    expected_keys = {
        (stage_name, selector, repeat)
        for stage_name in STAGES
        for selector in (0, 1)
        for repeat in (1, 2)
    }
    if set(seen) != expected_keys:
        errors.append("selector response key set differs")
    if len(responses) != 28:
        errors.append(f"selector response count differs: {len(responses)}")
    for key, raw in seen.items():
        if len(raw) != 5001:
            errors.append(f"selector response length differs: {key}")
    for stage_name in STAGES:
        for selector in (0, 1):
            first = seen.get((stage_name, selector, 1))
            second = seen.get((stage_name, selector, 2))
            if first is None or second is None or first[1:] != second[1:]:
                errors.append(f"selector repeats differ: {stage_name}/{selector}")

    controller = documents.get(CONTROLLER, {})
    observed = controller.get("observed", {})
    if observed.get("read_count") != 28:
        errors.append("controller parser read count differs")
    if observed.get("selected_mapping") != "fixed_bank":
        errors.append("controller parser mapping is not fixed_bank")
    if observed.get("target_selector") != {"0x24": 0, "0x26": 1}:
        errors.append("controller parser target selector mapping differs")
    if observed.get("target_role") != {"0x24": "base_role_after_swap", "0x26": "current_role_after_swap"}:
        errors.append("controller parser role mapping differs")
    if observed.get("known_swap_busy_elapsed_ms") != 447:
        errors.append("known swap BUSY duration differs")

    stage = documents.get(STAGE, {})
    counters = stage.get("counters", {})
    expected_counters = {
        "candidate_write_calls": 1,
        "preclean_write_calls": 1,
        "postclean_write_calls": 1,
        "restore_write_calls": 1,
        "automatic_retries": 0,
        "panel_writes": 5,
        "panel_refresh_commands": 1,
        "panel_hard_resets": 1,
    }
    for name, expected in expected_counters.items():
        if counters.get(name) != expected:
            errors.append(f"stage counter differs: {name}")
    if stage.get("popup_policy", {}).get("machine_only_r8_total") != 0:
        errors.append("R8 popup count differs")
    if stage.get("pre_execute_prompt", {}).get("invoked") is not False or stage.get("operator_prompt", {}).get("invoked") is not False:
        errors.append("R8 claims a popup invocation")
    if documents.get(RESTORE, {}).get("restore_sha256") != "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C":
        errors.append("exact raw restore hash differs")
    if len(STDERR.read_bytes()) != 0:
        errors.append("durable runner stderr is nonempty")

    artifact_paths = (LAUNCH, RAW, CONTROLLER, PRECLEAN, POSTCLEAN, RESTORE, NORMAL, STAGE, STDOUT, STDERR)
    result = {
        "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.r2_runtime.v1",
        "status": "PASS_MACHINE_R8_R2_FIXED_BANK_MAPPING_CLEANED_RESTORED" if not errors else "NO_GO_R8_R2_RUNTIME",
        "requirements": ["COMP-REQ-305", "COMP-REQ-306"],
        "errors": errors,
        "hardware_contact": 1,
        "execute_count": 1,
        "automatic_retries": 0,
        "popup_count": 0,
        "classification": {
            "selected_mapping": observed.get("selected_mapping"),
            "target_selector": observed.get("target_selector"),
            "target_role_after_swap": observed.get("target_role"),
            "known_swap_busy_elapsed_ms": observed.get("known_swap_busy_elapsed_ms"),
            "selector_reads": observed.get("read_count"),
            "swap_activations": controller.get("contract", {}).get("swap_activations"),
            "post_tag_activations": controller.get("contract", {}).get("post_tag_activations"),
        },
        "selector_responses": responses,
        "cleanup_restore": {
            "preclean_status": documents.get(PRECLEAN, {}).get("status"),
            "postclean_status": documents.get(POSTCLEAN, {}).get("status"),
            "restore_status": documents.get(RESTORE, {}).get("status"),
            "restore_bytes": documents.get(RESTORE, {}).get("length_bytes"),
            "restore_sha256": documents.get(RESTORE, {}).get("restore_sha256"),
            "normal_resume_status": documents.get(NORMAL, {}).get("status"),
        },
        "artifact_hashes": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
            for path in artifact_paths
        },
        "claims_not_made": [
            "no optical, ghosting, motion, or visual acceptance result",
            "no production admission",
            "no LUT, waveform, temperature, voltage, Rig, CRIG, or expression claim",
        ],
        "next_boundary": "Stop after this machine disposition. No retry, visual candidate, or subsequent experiment is authorized.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
