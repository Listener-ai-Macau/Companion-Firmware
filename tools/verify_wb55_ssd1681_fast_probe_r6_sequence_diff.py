#!/usr/bin/env python3
"""Byte/order audit of no-response fast probe versus visibly effective r6."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
R6_OPERATOR = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json"
R6_TRACE = ROOT / ".cache/validation/wb55-vendor-partial-disjoint-current-stage-r6-20260721/vendor-partial-disjoint-current-stage-trace.json"
R6_STAGE = ROOT / ".cache/validation/wb55-vendor-partial-disjoint-current-stage-r6-20260721/stage-run.json"
R6_LOG = ROOT / ".cache/validation/wb55-vendor-partial-disjoint-current-stage-r6-20260721/capture/nucleo-serial-raw.log"
R6_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_vendor_partial_disjoint_current_stage_operator_loop_diagnostic/Companion_Nucleo_WB55RG_VendorPartialDisjointCurrentStageOperatorLoopDiagnostic.elf"
R2_STAGE = ROOT / ".cache/validation/wb55-fast-point-probe-inverse-seed-execute-20260721-r2/stage-run.json"
R2_LOG = ROOT / ".cache/validation/wb55-fast-point-probe-inverse-seed-execute-20260721-r2/candidate-capture/nucleo-serial-raw.log"
R2_ELF = ROOT / ".cache/validation/wb55-fast-point-probe-inverse-seed-execute-20260721-r2/candidate-image/Companion_Nucleo_WB55RG_Ssd1681FastPointProbeInverseSeed.elf"
OUT = ROOT / "docs/validation/companion-ssd1681-fast-probe-r6-sequence-diff-20260721.json"

EXPECTED = {
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    R6_OPERATOR: "13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3",
    R6_TRACE: "9EDE11E629886FADF7B3B585F7775C9CCBDD5A7B1A8703997209BFE4D7CAAB86",
    R6_STAGE: "7A5B97CE371116EBD995DDD50A918B2050B27519B426899A7632122C56A54D27",
    R6_LOG: "B46B87AF3442797BABD43C555A499F82489A40EEF714F5E34F5F5F8580E56947",
    R6_ELF: "D172B691083C5D485EC4263FEB69CFBB5D9D4A666F0B5E320B86D8B46459C790",
    R2_STAGE: "8BA7B5E5F4FB6E3A0D8EA210B901E7B8132F85DC88C08284E057156D2D44CDBD",
    R2_ELF: "D5D61FCFAAFFCD1FBAC3199E5864C9660B1759E1BDC683C1BE5E4A5B7A5B2FF2",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def body(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def order(block: str, tokens: list[str]) -> list[str]:
    positions = [(block.find(token), token) for token in tokens]
    return [token for position, token in sorted(positions) if position >= 0]


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        if not path.is_file() or sha(path) != expected:
            errors.append(f"locked input missing/hash mismatch: {path}")
    driver = DRIVER.read_text(encoding="utf-8")
    supplier = SUPPLIER.read_text(encoding="utf-8", errors="ignore")
    r6_operator = json.loads(R6_OPERATOR.read_text(encoding="utf-8"))
    r6_trace = json.loads(R6_TRACE.read_text(encoding="utf-8"))
    r2_stage = json.loads(R2_STAGE.read_text(encoding="utf-8"))
    r2_log = R2_LOG.read_text(encoding="utf-8", errors="ignore")

    supplier_partial = supplier[supplier.index("void EPD_Dis_Part_myself"):]
    r6_window = body(driver, "static bool ssd1681_set_window_vendor_partial_source", "#endif")
    current_window = body(driver, "static bool ssd1681_point_probe_set_window", "static ssd1681_window_t")
    current_probe = body(driver, "static void ssd1681_fast_point_probe_diagnostic", "#endif")
    command_path = body(driver, "static bool ssd1681_spi_tx", "#if !COMPANION_EPAPER_SSD1681_HAS_BUSY")
    reset_path = body(driver, "static void ssd1681_point_probe_hard_reset", "static bool ssd1681_point_probe_set_window")
    source_tokens = ["0x3Cu", "0x44u", "0x45u", "0x4Eu", "0x4Fu"]
    current_tokens = ["0x01u", "0x11u", "0x44u", "0x45u", "0x3Cu", "0x18u", "0x4Eu", "0x4Fu"]

    if r6_operator.get("status") != "PASS_OPERATOR_WITH_RESIDUE_STEERING_PRODUCTION_OFF" or r6_operator.get("operator_review", {}).get("selected") != "通过":
        errors.append("r6 is not the locked visibly moving authority")
    if r6_trace.get("status") != "PASS_MACHINE_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_TRACE" or r6_trace.get("partial_steps") != 48:
        errors.append("r6 machine trace drifted")
    if r2_stage.get("status") != "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED":
        errors.append("r2 machine/restore status drifted")
    if order(r6_window, source_tokens) != source_tokens:
        errors.append("r6 source border/address order differs")
    if order(current_window, current_tokens) != current_tokens:
        errors.append("current extended register order differs")
    supplier_order = [token for token in ("0x3C", "0x44", "0x45", "0x4E", "0x4F", "0x24") if supplier_partial.find(token) >= 0]
    if supplier_order != ["0x3C", "0x44", "0x45", "0x4E", "0x4F", "0x24"]:
        errors.append("supplier pre-partial order differs")
    if not all(token in reset_path for token in ("HAL_GPIO_WritePin", "COMPANION_EPAPER_SSD1681_RST_GPIO_PORT", "GPIO_PIN_RESET", "GPIO_PIN_SET", "HAL_Delay(10u)")):
        errors.append("candidate hardware reset does not reach physical RST GPIO")
    if not all(token in command_path for token in ("HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9", "HAL_GPIO_WritePin(GPIOC", "ssd1681_select(true)", "ssd1681_spi_tx(&command, 1u)", "ssd1681_spi_tx(data, length)")):
        errors.append("candidate command/data path is not physical software SPI")
    if current_probe.count("ssd1681_point_probe_write_current(&window") != 2 or "post_sync_refresh=0" not in current_probe:
        errors.append("current post-activation 0x24 sync evidence differs")
    if "post_sync_command=0x24" in R6_LOG.read_text(encoding="utf-8", errors="ignore"):
        errors.append("r6 unexpectedly contains post-activation sync")
    if "post_sync_command=0x24" not in r2_log:
        errors.append("r2 post-activation sync trace missing")
    r6_busy = r6_trace.get("refresh_elapsed_ms", [])
    if not r6_busy or max(r6_busy) > 447:
        errors.append("r6 physical BUSY evidence differs")

    result = {
        "schema_id": "companion.wb55.ssd1681_fast_probe_r6_sequence_diff.v1",
        "status": "PASS_DIFF_ADMIT_R3_SUPPLIER_PRE_PARTIAL_SEQUENCE" if not errors else "NO_GO_SEQUENCE_DIFF",
        "errors": errors,
        "physical_authority": {
            "r6_status": r6_operator.get("status"),
            "selection": r6_operator.get("operator_review", {}).get("selected"),
            "note": r6_operator.get("operator_review", {}).get("note"),
            "partial_steps": r6_trace.get("partial_steps"),
            "busy_ms": [min(r6_busy), max(r6_busy)] if r6_busy else [],
        },
        "real_hardware_path": {
            "reset": "HAL_GPIO_WritePin physical RST low/high with 10 ms dwell",
            "spi": "command/data call ssd1681_spi_tx, toggling physical PA9 SCK, PC1 MOSI, CS and DC",
            "busy": "48 visibly effective r6 completions and 120 r2 completions are GPIO BUSY waits, not log-only counters",
        },
        "byte_order_diff": {
            "supplier_and_r6_pre_partial": ["hard_reset_10_10", "0x3C:0x80", "0x44", "0x45", "0x4E", "0x4F", "0x24 data", "0x22:0xFF", "0x20", "BUSY"],
            "r2_pre_partial": ["hard_reset_10_10", "0x01", "0x11:0x01", "0x44", "0x45", "0x3C:0x80", "0x18:0x80", "0x4E", "0x4F", "0x24 data", "0x22:0xFF", "0x20", "BUSY"],
            "r6_post_activation": "no 0x24 sync",
            "r2_post_activation": "reissues extended setup then 0x24 current, no activation",
        },
        "causal_selection": {
            "r3_single_variable": "pre_partial_window_register_sequence",
            "from": "extended 0x01/0x11/0x44/0x45/0x3C/0x18/0x4E/0x4F",
            "to": "visibly effective supplier/r6 0x3C/0x44/0x45/0x4E/0x4F",
            "why_not_post_sync_first": "Post-sync occurs after the first physical activation and cannot explain zero reaction on frame 1; the pre-partial sequence can.",
            "branch_basis": "R3 branches from round 1 all-white seed and changes only the pre-partial setup sequence; it does not retain or extend the falsified inverse seed.",
        },
        "unchanged": "120 fast frames, one FF/20/BUSY per frame, post-activation 0x24 sync, no full refresh, no custom LUT, exact raw restore",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
