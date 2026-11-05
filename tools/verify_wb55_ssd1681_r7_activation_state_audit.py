#!/usr/bin/env python3
"""Reconstruct the executed SSD1681 local-update activation states for R7."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUTPUT = ROOT / "docs/validation/companion-ssd1681-r7-activation-state-audit-20260721.json"
SUPPLIER = Path(
    "C:\\Users\\Billy\\Desktop\\GDEH0154D67-20211203-P-LUT(1s) -1s\u5feb\u5237\\EPD_W21\\EPAPER.c"
)
PROTECTED_ACCEPTANCE = (
    ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
)

EVIDENCE = {
    "accepted_operator": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json",
        "DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57",
    ),
    "accepted_runtime": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-runtime-20260720.json",
        "AE50830D1DB091AD2E526A132D55A7D512EA55E09D534F66CA7E71DB81BFF814",
    ),
    "disjoint_252_operator": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-operator-r1-20260721.json",
        "67E43FBBD7546EB99E4CE8B06EE84141D0B0F4419E77C7ED1AF7D9C38D7D9C00",
    ),
    "disjoint_252_trace": (
        ".cache/validation/wb55-vendor-partial-disjoint-no-union-settle-r1-20260721/vendor-partial-disjoint-no-union-settle-trace.json",
        "8BC7D28C8D54C175525CF95D91977CCE2D649434F7746CA84F203FC1DE2A8355",
    ),
    "old_new_stage": (
        ".cache/validation/wb55-vendor-partial-old-new-ram-current-room-20260720/stage-run.json",
        "2CD19DBC5EDA70A072F632AC40504FC8853CC62B4BABCA77C5675E6C13588398",
    ),
    "old_new_trace": (
        ".cache/validation/wb55-vendor-partial-old-new-ram-current-room-20260720/vendor-partial-slow-motion-trace.json",
        "4FD8EC2970A4C5F3626ABB88C90F0F6A41016667153C1AAA0FA0CD9C6272D0BF",
    ),
    "current_stage_operator": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json",
        "13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3",
    ),
    "current_stage_trace": (
        ".cache/validation/wb55-vendor-partial-disjoint-current-stage-r6-20260721/vendor-partial-disjoint-current-stage-trace.json",
        "9EDE11E629886FADF7B3B585F7775C9CCBDD5A7B1A8703997209BFE4D7CAAB86",
    ),
    "draw_final_operator": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-draw-final-operator-20260720.json",
        "69FC1FC6A01EBDDD45A10E477270ACC4EC4F22999BB4C3B78EE474E2CAC03B1E",
    ),
    "draw_final_runtime": (
        "docs/validation/companion-gdey0154d67-t03-vendor-partial-draw-final-runtime-20260720.json",
        "FCD31FDF99BEA9DFBA2BFBA49BB1490FBA6999A926E9364EF2D51EDABE0C6F8D",
    ),
    "phase_a_fingerprint": (
        "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json",
        "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    ),
    "post_sync_machine": (
        "docs/validation/companion-ssd1681-ram-ping-pong-point-probe-machine-20260721.json",
        "C0399F525B0908A31EB0303DFD06DC569EDEE6AE042B40A0272E85C188EC7776",
    ),
    "post_sync_operator": (
        "docs/validation/companion-ssd1681-ram-ping-pong-point-probe-operator-result-20260721.json",
        "C74E48DFBE2801A92D99DD38475C10214D91DEBE2B9A8514320C29A825007AF0",
    ),
    "fast_post_sync_r1": (
        "docs/validation/companion-ssd1681-fast-point-probe-round1-disposition-20260721.json",
        "47903C0E23FAE98E3106666D20DDC301ED5C1E5E607E3572A832405A1D18A167",
    ),
    "fast_post_sync_r2": (
        "docs/validation/companion-ssd1681-fast-point-probe-inverse-seed-round2-disposition-20260721.json",
        "DFF623032CE01355DCAF12A1FAEA0BCDC27A1A0FF777C86CCED0B7ACF7BB7BBB",
    ),
    "prior_mechanism_research": (
        "docs/validation/companion-ssd1681-mechanism-lut-research-disposition-20260721.json",
        "478EECD541623713C665D2FCFCCF17743B9F3489A934097978033C1893E20F93",
    ),
    "tp16_failure": (
        "docs/validation/companion-ssd1681-custom-mode2-observable-r6-failure-diagnosis-20260721.json",
        "CD58E1AFF90339A2A3528C9C86B22F641DD010A4D275AF75410E16F812552289",
    ),
    "prior_cutoff_research": (
        "docs/validation/companion-ssd1681-two-stage-cutoff-research-disposition-20260721.json",
        "AF36FEC2A768A113798F5980303EEF3CE7D92B9CB6E5F1636D853B3A8DA3C823",
    ),
}

RAW_EVIDENCE = {
    "post_sync_point_probe_raw": (
        ".cache/validation/wb55-ram-ping-pong-point-probe-execute-20260721-r1/candidate-capture/nucleo-serial-raw.log",
        "55D247D7A0D936D50AAFD540CD294E87BC71DD17053332E79D1194434E373815",
    ),
    "post_sync_fast_r1_raw": (
        ".cache/validation/wb55-fast-point-probe-execute-20260721-r1/candidate-capture/nucleo-serial-raw.log",
        "8CD7DD3291CC139F57F24C173169F1F36B39394CC26DC96B6842EE83808A4336",
    ),
    "post_sync_fast_r2_raw": (
        ".cache/validation/wb55-fast-point-probe-inverse-seed-execute-20260721-r2/candidate-capture/nucleo-serial-raw.log",
        "6756CB1425FA3E92ECF58C1BDA334472F410499D8D895BCDB7CE653027AA9AC9",
    ),
    "old_new_raw": (
        ".cache/validation/wb55-vendor-partial-old-new-ram-current-room-20260720/capture/nucleo-serial-raw.log",
        "C37EB066E45ABD04E7E2266C5BC7F1F474C984A88500DAC7C9015017EA5B54E4",
    ),
    "current_stage_raw": (
        ".cache/validation/wb55-vendor-partial-disjoint-current-stage-r6-20260721/capture/nucleo-serial-raw.log",
        "B46B87AF3442797BABD43C555A499F82489A40EEF714F5E34F5F5F8580E56947",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row(
    topology: str,
    phase: str,
    count: int,
    writes: list[str],
    pre_state: str,
    post_state: str,
    visible_after: str,
    observed: str,
    timing_ms: Any,
) -> dict[str, Any]:
    return {
        "topology": topology,
        "phase": phase,
        "activation_count": count,
        "pre_activation_state": pre_state,
        "ordered_panel_commands": writes + ["0x22=0xFF", "0x20", "BUSY"],
        "post_activation_state": post_state,
        "ideal_visible_after": visible_after,
        "physical_observation": observed,
        "busy_elapsed_ms": timing_ms,
    }


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    require("registry_exists", REGISTRY.is_file(), "product registry is missing")
    registry = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
    require(
        "registry_first_r7_contract",
        "| COMP-REQ-301 |" in registry
        and "Routine White pre/post-clean" in registry
        and "R7 is research-only" in registry,
        "COMP-REQ-301 R7/prompt boundary is missing",
    )

    loaded: dict[str, dict[str, Any]] = {}
    raw_loaded: dict[str, str] = {}
    source_manifest: dict[str, str] = {}
    for name, (relative, expected) in EVIDENCE.items():
        path = ROOT / relative
        exists = path.is_file()
        require(f"evidence_exists_{name}", exists, f"missing evidence: {relative}")
        if not exists:
            continue
        actual = sha256(path)
        require(f"evidence_hash_{name}", actual == expected, f"hash mismatch: {relative}")
        source_manifest[relative] = actual
        try:
            loaded[name] = load_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"invalid JSON {relative}: {exc}")

    for name, (relative, expected) in RAW_EVIDENCE.items():
        path = ROOT / relative
        exists = path.is_file()
        require(f"raw_evidence_exists_{name}", exists, f"missing raw evidence: {relative}")
        if not exists:
            continue
        actual = sha256(path)
        require(f"raw_evidence_hash_{name}", actual == expected, f"hash mismatch: {relative}")
        source_manifest[relative] = actual
        try:
            raw_loaded[name] = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            failures.append(f"unreadable raw evidence {relative}: {exc}")

    require(
        "supplier_source_immutable",
        SUPPLIER.is_file()
        and sha256(SUPPLIER)
        == "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
        "supplier EPAPER.c is missing or changed",
    )
    require(
        "protected_acceptance_unchanged",
        PROTECTED_ACCEPTANCE.is_file()
        and sha256(PROTECTED_ACCEPTANCE)
        == "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
        "protected owner acceptance changed",
    )

    if failures:
        result = {
            "schema_id": "companion.wb55.ssd1681_r7_activation_state_audit.v1",
            "status": "NO_GO_R7_EVIDENCE_INCOMPLETE",
            "hardware_contact": 0,
            "checks": checks,
            "failures": failures,
        }
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["status"])
        return 1

    accepted = loaded["accepted_operator"]
    accepted_runtime = loaded["accepted_runtime"]
    disjoint = loaded["disjoint_252_operator"]
    disjoint_trace = loaded["disjoint_252_trace"]
    old_new_stage = loaded["old_new_stage"]
    old_new_trace = loaded["old_new_trace"]
    current_stage = loaded["current_stage_operator"]
    current_stage_trace = loaded["current_stage_trace"]
    draw_final = loaded["draw_final_operator"]
    draw_final_runtime = loaded["draw_final_runtime"]
    phase_a = loaded["phase_a_fingerprint"]
    post_sync = loaded["post_sync_machine"]
    post_sync_operator = loaded["post_sync_operator"]
    fast_r1 = loaded["fast_post_sync_r1"]
    fast_r2 = loaded["fast_post_sync_r2"]
    tp16 = loaded["tp16_failure"]
    controlled_sync_logs = (
        raw_loaded["post_sync_point_probe_raw"],
        raw_loaded["post_sync_fast_r1_raw"],
        raw_loaded["post_sync_fast_r2_raw"],
    )
    controlled_post_0x24_count = sum(
        text.count("post_sync_command=0x24") for text in controlled_sync_logs
    )
    controlled_post_0x26_count = sum(
        text.count("post_sync_command=0x26") for text in controlled_sync_logs
    )
    global_post_0x26_logs = []
    for directory, _, filenames in os.walk(ROOT / ".cache/validation", onerror=lambda _: None):
        for filename in filenames:
            if not filename.endswith(".log"):
                continue
            log_path = Path(directory) / filename
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "post_sync_command=0x26" in text:
                global_post_0x26_logs.append(str(log_path.relative_to(ROOT)).replace("\\", "/"))

    require(
        "accepted_baseline_exact",
        accepted.get("status") == "PASS_OPERATOR_ACCEPTED_PRODUCTION_OFF_NO_UNION_SETTLE_BASELINE"
        and accepted.get("operator_review", {}).get("selection") == "\u901a\u8fc7"
        and accepted_runtime.get("observed", {}).get("partial_activation_count") == 96,
        "accepted COMP-REQ-236/237 baseline differs",
    )
    require(
        "disjoint_252_exact",
        disjoint.get("status") == "NO_GO_OPERATOR_LEADING_EDGE_CUTOFF_DISJOINT_NO_UNION_SETTLE"
        and disjoint_trace.get("controller_completions") == 96,
        "COMP-REQ-252 evidence differs",
    )
    require(
        "old_new_explicit_executed",
        old_new_trace.get("status") == "PASS_MACHINE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE"
        and old_new_stage.get("operator_review", {}).get("selected") == "\u5931\u8d25"
        and old_new_stage.get("operator_review", {}).get("residue_observed") is True,
        "explicit old/new RAM physical execution is not proven",
    )
    require(
        "current_stage_executed",
        current_stage.get("status") == "PASS_OPERATOR_WITH_RESIDUE_STEERING_PRODUCTION_OFF"
        and current_stage_trace.get("partial_steps") == 48,
        "current-only single activation control differs",
    )
    require(
        "draw_final_executed",
        draw_final.get("status") == "NO_GO_OPERATOR_VISIBLE_RESIDUE_DRAW_FINAL"
        and draw_final_runtime.get("observed", {}).get("partial_activation_count") == 96,
        "draw-final evidence differs",
    )
    require(
        "phase_a_unique_selector_mapping",
        phase_a.get("fingerprint", {}).get("unique_mapping")
        == "activation_swapped_banks_selector0_base_selector1_current"
        and phase_a.get("phase_b_admission", {}).get("motion_0x26_writes_allowed") == 0,
        "Phase-A selector mapping differs",
    )
    require(
        "post_sync_executed",
        post_sync.get("transport", {}).get("post_activation_0x24_sync_without_refresh") == 24
        and post_sync.get("transport", {}).get("refresh_0x20") == 24
        and post_sync_operator.get("human_result_blocks_visual_admission") is True,
        "post-activation 0x24 sync execution differs",
    )
    require(
        "fast_post_sync_rounds_executed",
        fast_r1.get("machine", {}).get("frames") == 120
        and fast_r2.get("machine", {}).get("frames") == 120
        and fast_r1.get("operator", {}).get("visual_pass") is False
        and fast_r2.get("operator", {}).get("visual_pass") is False,
        "fast post-sync rounds differ",
    )
    require(
        "controlled_post_sync_command_counts",
        controlled_post_0x24_count == 264 and controlled_post_0x26_count == 0,
        "controlled post-activation sync command counts differ",
    )
    require(
        "no_historical_post_sync_0x26_log",
        not global_post_0x26_logs,
        "a historical post-activation 0x26 sync log exists and must be audited",
    )
    require(
        "old_new_and_current_stage_have_no_post_sync",
        "post_sync_command=" not in raw_loaded["old_new_raw"]
        and "post_sync_command=" not in raw_loaded["current_stage_raw"],
        "old/new or current-stage raw log unexpectedly has post-sync",
    )
    require(
        "tp16_progression_retired",
        tp16.get("status") == "PASS_RESEARCH_R6_FAILURE_DIAGNOSIS_NO_NEW_HARDWARE_CANDIDATE"
        and "COMP-REQ-300" in registry
        and "must not be rerun" in registry,
        "TP16 hard-fail retirement is incomplete",
    )

    transition_truth_table = [
        {
            "class": "same_black",
            "previous_P": 0,
            "current_N": 0,
            "visible_previous": 0,
            "after_erase_first_P_or_N": 0,
            "after_draw_final_N": 0,
            "draw_union_P_and_N": 0,
        },
        {
            "class": "old_only_black_to_white",
            "previous_P": 0,
            "current_N": 1,
            "visible_previous": 0,
            "after_erase_first_P_or_N": 1,
            "after_draw_final_N": 1,
            "draw_union_P_and_N": 0,
        },
        {
            "class": "new_only_white_to_black",
            "previous_P": 1,
            "current_N": 0,
            "visible_previous": 1,
            "after_erase_first_P_or_N": 1,
            "after_draw_final_N": 0,
            "draw_union_P_and_N": 0,
        },
        {
            "class": "same_white",
            "previous_P": 1,
            "current_N": 1,
            "visible_previous": 1,
            "after_erase_first_P_or_N": 1,
            "after_draw_final_N": 1,
            "draw_union_P_and_N": 1,
        },
    ]

    activation_state_table = [
        row(
            "COMP-REQ-236/237 accepted_no_union_settle",
            "erase_old",
            48,
            ["hard_reset_10_10", "border=0x80", "window=bbox(previous black)", "0x24=current N bytes"],
            "visible=P; RAM selectors were not read in this historical run",
            "intermediate ideal=P OR N (black-set intersection)",
            "old-only is white, new-only is still white",
            "no old hatch/full-screen flash; directional leading edge is cut",
            {"minimum": 446, "maximum": 447},
        ),
        row(
            "COMP-REQ-236/237 accepted_no_union_settle",
            "draw_current",
            48,
            ["hard_reset_10_10", "border=0x80", "window=byte-aligned old/new union", "0x24=current N bytes"],
            "visible=P OR N",
            "visible=N",
            "old-only stays white and new-only becomes black",
            "cut segment is restored; bounded run accepted as current best",
            {"minimum": 446, "maximum": 447},
        ),
        row(
            "COMP-REQ-252 disjoint_no_union_settle",
            "erase_old",
            48,
            ["hard_reset_10_10", "border=0x80", "window=bbox(previous black)", "0x24=current N bytes"],
            "visible=P",
            "visible=P OR N",
            "new-only remains white",
            "same eaten leading segment remains",
            {"maximum": disjoint_trace["timing"]["single_completion_max_ms"]},
        ),
        row(
            "COMP-REQ-252 disjoint_no_union_settle",
            "draw_current_disjoint",
            48,
            ["hard_reset_10_10", "border=0x80", "windows=1..5 disjoint byte-aligned diff regions", "0x24=current N bytes"],
            "visible=P OR N",
            "visible=N",
            "new-only becomes black",
            "residue floor preserved but cutoff restored only after this activation",
            {"maximum": disjoint_trace["timing"]["single_completion_max_ms"]},
        ),
        row(
            "draw_final",
            "draw_old_or_current_union",
            48,
            ["hard_reset_10_10", "border=0x80", "window=byte-aligned old/new union", "0x24=P AND N bytes"],
            "visible=P",
            "visible=P AND N (black-set union)",
            "both old-only and new-only are black",
            "empty gap removed but a residue frame is visible",
            {"minimum": 446, "maximum": 447},
        ),
        row(
            "draw_final",
            "settle_current",
            48,
            ["hard_reset_10_10", "border=0x80", "window=byte-aligned old/new union", "0x24=current N bytes"],
            "visible=P AND N",
            "visible=N",
            "old-only is driven white",
            "operator still observed visible residue; durable NO_GO",
            {"minimum": 446, "maximum": 447},
        ),
        row(
            "explicit_old_new_ram",
            "direct_previous_to_current",
            5,
            ["hard_reset_10_10", "border=0x80", "window=byte-aligned old/new union", "0x26=full-CPU previous P bytes", "0x24=full-CPU current N bytes"],
            "within union: previous bank=P, current bank=N",
            "Mode2 bank visibility swaps after activation; intended visible=N",
            "black-to-white and white-to-black are requested in one activation",
            "machine PASS; operator FAIL: black residue followed motion",
            {"minimum": 447, "maximum": 447},
        ),
        row(
            "current_stage_r6",
            "direct_current_only",
            48,
            ["hard_reset_10_10", "border=0x80", "windows=1..5 disjoint byte-aligned diff regions", "0x24=current N bytes", "no 0x26", "no post-sync"],
            "prior bank ownership relies on preceding Mode2 state",
            "intended visible=N",
            "one activation has no erase-first gap",
            "visible movement, but direct-motion residue reported",
            {"minimum": min(current_stage_trace["refresh_elapsed_ms"]), "maximum": max(current_stage_trace["refresh_elapsed_ms"])},
        ),
        row(
            "Phase_A_fingerprint",
            "controlled_mapping_probe",
            1,
            ["before activation measured selector0=N and selector1=P", "no post-activation RAM write"],
            "selector0=N, selector1=P",
            "selector0=P, selector1=N",
            "not an optical acceptance run",
            "readback uniquely proves content swap; it does not map a write command after the swap",
            {"partial": phase_a["fingerprint"]["partial_busy_elapsed_ms"]},
        ),
        row(
            "post_sync_Phase_B",
            "direct_activation",
            24,
            ["hard_reset_10_10", "window=byte-aligned old/new union", "0x24=current N bytes", "0x26 retains previous P"],
            "intended before activation: one selector contains N and the other P; no per-frame selector readback",
            "Phase-A predicts a content swap, but this runtime did not read either selector",
            "direct old-to-new with no erase-first intermediate",
            "machine transport passed; visual run reported no observed motion and dirty whole screen",
            post_sync["transport"]["busy_elapsed_ms"],
        ),
        {
            "topology": "post_sync_Phase_B",
            "phase": "post_activation_bank_sync_without_display",
            "activation_count": 0,
            "repeat_count": 24,
            "pre_activation_state": "selector0=P, selector1=N after Mode2 swap",
            "ordered_panel_commands": ["window=same byte-aligned union", "0x24=current N bytes", "no 0x22", "no 0x20", "no BUSY"],
            "post_activation_state": "UNKNOWN_NOT_READ_BACK: either selector0=N,selector1=N if 0x24 targets physical selector0, or selector0=P,selector1=N if 0x24 targets the current-role bank",
            "ideal_visible_after": "unchanged N because no activation occurs",
            "physical_observation": "the command was transported, but its post-swap physical/role target was never read back",
            "busy_elapsed_ms": None,
        },
        row(
            "fast_post_sync_round_1",
            "direct_activation_then_post_sync",
            120,
            ["hard_reset_10_10", "window=byte-aligned old/new union", "0x24=current N"],
            "CPU assumes synchronized P/P; initial seed was not optically activated",
            "intended visible=N; later no-refresh 0x24=N target is UNKNOWN_NOT_READ_BACK",
            "direct transition with no erase-first gap",
            "120 machine completions; owner saw no movement/screen change",
            {"maximum": fast_r1["machine"]["busy_max_ms"]},
        ),
        row(
            "fast_post_sync_round_2_inverse_seed",
            "direct_activation_then_post_sync",
            120,
            ["hard_reset_10_10", "window=byte-aligned old/new union", "0x24=current N"],
            "inverse local corridor seed supplied intended W->B and B->W transitions",
            "intended visible=N; later no-refresh 0x24=N target is UNKNOWN_NOT_READ_BACK",
            "direct transition with no erase-first gap",
            "120 machine completions; owner saw no screen reaction",
            {"maximum": fast_r2["machine"]["busy_max_ms"]},
        ),
    ]

    measured_command_mapping = {
        "read_selector_0x41_then_0x27": {
            "measured": True,
            "scope": "0x41 selected readback selector 0 or 1 before 0x27 returned 5000 payload bytes",
            "write_mapping_claim": "none; read-selector choice does not prove which selector a later 0x24 or 0x26 write targets",
        },
        "before_partial_activation": {
            "measured": "after 0x24=N staging, selector0=N and selector1=P",
            "supported_mapping": "0x24 targeted selector0 in this pre-activation state",
        },
        "after_partial_activation": {
            "measured": "without another RAM write, selector0=P and selector1=N",
            "supported_mapping": "activation swapped selector-visible contents",
            "unsupported_inference": "the historical selector0/0x24 and selector1/0x26 labels do not prove post-swap write-command targeting",
        },
        "post_activation_write_targets": {
            "0x24": "UNKNOWN_NOT_READ_BACK",
            "0x26": "UNKNOWN_NOT_EXECUTED_OR_READ_BACK_IN_CONTROLLED_MODE2_FF_SYNC",
            "selector_aware_dynamic_target": "UNKNOWN_NOT_EXECUTED",
        },
    }

    historical_post_activation_sync_matrix = [
        {
            "mechanism": "fixed post-activation 0x24 no-refresh sync",
            "executed_count": controlled_post_0x24_count,
            "executed_runs": 3,
            "post_write_selector_readback_count": 0,
            "target_state": "UNKNOWN_NOT_READ_BACK",
            "visual_disposition": "no visual admission; dirty/unseen or no reaction",
        },
        {
            "mechanism": "fixed post-activation 0x26 no-refresh sync",
            "executed_count": controlled_post_0x26_count,
            "executed_runs": 0,
            "post_write_selector_readback_count": 0,
            "target_state": "UNKNOWN_NOT_EXECUTED",
            "visual_disposition": "none",
        },
        {
            "mechanism": "selector-aware post-activation sync chosen from measured post-write ownership",
            "executed_count": 0,
            "executed_runs": 0,
            "post_write_selector_readback_count": 0,
            "target_state": "UNKNOWN_NOT_EXECUTED",
            "visual_disposition": "none",
        },
    ]

    exact_candidate_assessment = {
        "candidate": "OTP_0xFF_single_activation_selector_aware_dual_buffer_union",
        "requested_properties": {
            "complete_previous_current_cpu_framebuffers": True,
            "selector_aware_bank_ownership": True,
            "byte_aligned_old_new_union_window": True,
            "previous_plane": "P",
            "current_plane": "N",
            "one_activation": "0x22=0xFF -> 0x20 -> BUSY",
            "no_erase_first_gap": True,
        },
        "historical_equivalents": [
            {
                "name": "vendor_partial_old_new_ram",
                "equivalence": "explicit 0x26=P plus 0x24=N in the byte-aligned changed union before one FF/20/BUSY",
                "machine": "PASS_MACHINE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE",
                "physical": "FAIL_RESIDUE_FOLLOWS_MOTION",
            },
            {
                "name": "Phase_A_proven_post_sync_Phase_B",
                "equivalence": "not proven: Phase B used fixed 0x24 after the swap, but never read back which selector it changed",
                "machine": "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE_RESTORED",
                "physical": "NO_VISUAL_ADMISSION_DIRTY_OR_UNSEEN",
            },
        ],
        "materially_untested": False,
        "post_activation_sync_target_submechanism_untested": True,
        "unique_untested_topology_proven_to_make_next_P_equal_N": False,
        "admitted": False,
        "decision": "NO_GO_EXPLICIT_OLD_NEW_VISUAL_TOPOLOGY_FAILED_AND_POST_SYNC_TARGET_UNPROVEN",
        "reason": "The simultaneous P-to-N one-activation visual topology was already executed with explicit old/new RAM writes and physically failed on moving black residue. The cross-frame post-sync target remains unresolved: existing evidence cannot prove that an unrun 0x26 or selector-aware write would make the next previous state equal current. It is therefore an evidence gap, not an admitted visual candidate.",
    }

    result = {
        "schema_id": "companion.wb55.ssd1681_r7_activation_state_audit.v1",
        "status": "NO_GO_R7_POST_ACTIVATION_SYNC_TARGET_UNPROVEN_NO_NEW_VISUAL_CANDIDATE",
        "claim_scope": "Research-only reconstruction from executed evidence; no build, flash, panel command, production, expression, or waveform claim.",
        "hardware_contact": 0,
        "candidate_implemented": False,
        "candidate_built": False,
        "goal_action": "none_root_owned",
        "checks": checks,
        "failures": failures,
        "state_model": {
            "polarity": "1=white, 0=black",
            "symbols": {"P": "previous visible framebuffer", "N": "requested current framebuffer"},
            "transition_truth_table": transition_truth_table,
            "cutoff_proof": "For every new-only pixel P=1,N=0, erase-first produces P OR N=1 (white). Only the second activation changes it to N=0 (black). The eaten segment is therefore the real visible intermediate between two completed activations; the following restoration is the draw activation, not a missing SPI byte or an incomplete BUSY wait.",
        },
        "activation_state_table": activation_state_table,
        "measured_command_mapping": measured_command_mapping,
        "historical_post_activation_sync_matrix": historical_post_activation_sync_matrix,
        "exact_candidate_assessment": exact_candidate_assessment,
        "tp16_disposition": {
            "progression": "retired",
            "reason": "R6 hard visual failure made the intended pattern disappear; timing PASS is not optical PASS.",
            "rerun": False,
        },
        "recommendation": {
            "next_hardware_variable": None,
            "decision": "NO_GO",
            "preserve": "COMP-REQ-236/237 remains the production-off visual floor with its known two-activation leading-edge cutoff.",
            "next_evidence_mechanism": "Future separately contracted readback-only discriminator: after a known FF swap, write a tagged region through 0x24 and read both selectors; restore, repeat through 0x26, and identify the physical/role target. R7 does not implement, build, flash, or run it.",
            "evidence_mechanism_is_not_visual_candidate": True,
            "only_future_visual_unlock": "A measured mechanism that both makes the next previous state equal current and materially changes the already failed direct P-to-N optical transition, or a Good Display/FPC-bound local Mode2 waveform and rules materially different from the executed OTP 0xFF family.",
            "do_not_repeat": [
                "explicit 0x26=P plus 0x24=N one-activation FF/20",
                "fixed 0x24 post-sync without readback proof",
                "current-only one-activation FF/20",
                "erase-first or draw-first two-activation reorderings",
                "TP16 custom waveform progression",
            ],
        },
        "owner_prompt_boundary": {
            "routine_cleanup": "promptless",
            "research_and_artifact_cleanup": "promptless",
            "new_hardware_refresh_experiment": "one timely Chinese operator boundary only after machine gates",
            "final_visual_verdict": "canonical",
        },
        "source_manifest": source_manifest,
        "protected_hashes": {
            str(SUPPLIER): sha256(SUPPLIER),
            str(PROTECTED_ACCEPTANCE.relative_to(ROOT)).replace("\\", "/"): sha256(PROTECTED_ACCEPTANCE),
        },
    }

    require(
        "no_new_hardware_candidate",
        result["exact_candidate_assessment"]["materially_untested"] is False
        and result["exact_candidate_assessment"]["unique_untested_topology_proven_to_make_next_P_equal_N"] is False
        and result["recommendation"]["next_hardware_variable"] is None,
        "audit accidentally admits a repeated hardware candidate",
    )
    result["checks"] = checks
    result["failures"] = failures
    if failures:
        result["status"] = "NO_GO_R7_AUDIT_INCONSISTENT"

    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result["status"])
    print(f"activation_state_rows={len(activation_state_table)}")
    print(f"evidence_files={len(source_manifest)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
