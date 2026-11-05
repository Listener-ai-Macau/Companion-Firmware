#!/usr/bin/env python3
"""Machine-only closure for the isolated COMP-REQ-611 lower consumer."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/comp-req-611-lower-sync"
NO_GO = OUT / "NO_GO.json"
PLAN = ROOT / ".cache/validation/comp-req-608-logical-choreography/canonical-frame-plan.json"
PAYLOAD = ROOT / ".cache/validation/comp-req-608-logical-choreography/wb55-frame-plan.bin"
PAGE = ROOT / ".cache/validation/comp-req-608-logical-choreography/index.html"
UPSTREAM_EVIDENCE = ROOT / ".cache/validation/comp-req-608-logical-choreography/verification.json"
RUNNER = ROOT / "app/companion_pendant/epaper/comp_req_611_canonical_runner.c"
RUNNER_H = ROOT / "app/companion_pendant/epaper/comp_req_611_canonical_runner.h"
GENERATOR = ROOT / "tools/generate_comp_req_611_canonical_frame_header.py"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
FRAME_HEADER = ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_611_canonical_sync"
HEX = BUILD / "Companion_Nucleo_WB55RG_Bringup.hex"
ELF = BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
BIN = BUILD / "Companion_Nucleo_WB55RG_Bringup.bin"
GENERATED_HEADER = ROOT / ".cache/validation/comp-req-611-canonical-sync/generated/comp_req_611_canonical_frames.h"
GENERATED_INPUT = ROOT / ".cache/validation/comp-req-611-canonical-sync/generated/canonical-input-evidence.json"
LAUNCHER = ROOT / "tools/run_comp_req_611_canonical_sync.ps1"
MONITOR = ROOT / "tools/monitor_comp_req_611_canonical_sync.ps1"
SUPERVISOR = ROOT / "tools/supervise_comp_req_611_canonical_sync_prompt.ps1"
LOG_PARSER = ROOT / "tools/verify_comp_req_611_canonical_sync_log.py"
CLEANUP_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_official_full_diagnostic_white/Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
CLEANUP_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_official_full_diagnostic_white/Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.elf"
EXPECTED = {
    "page": "3B9C4B2D0D16964DBD64A68B804AA6AB3404237539F44C21F3FEFD0B32A1AA22",
    "verifier": "6F400D2CD8FBB35C71A08BC038E38BBBE3CC042C423AAE7B1E36CD56E358456B",
    "plan": "2085577BAEC872AFCF7105733E48B921EDA591ADE641F19C4BC42CC77C3D592F",
    "payload": "5411FB50BC61BF3DC73EB7D0746C6C0E4DB56F7D552B6796BB3B7F6ED59AD5AD",
    "frame_header": "9571CF9F896B6C14451BAA7348CB717643B4963AE834B0A554E0C2ED2C7E8D35",
    "owner_acceptance": "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
}

PROTECTED_FUNCTIONS = {
    "ssd1681_native_cached_mode2_movement_activation": {
        "registry_normalized_sha256": "25BDB97E4E48BF976BAC4899F7338B76A81B933048029C2F5BA5FB1AFA9C1AD6",
        "current_raw_sha256": "EE83A0BA3366357C93233FEB7EBD7E581FA39B6A12379FDFCE28FF949D8954F8",
    },
    "ssd1681_native_two_pass_activation": {
        "registry_normalized_sha256": "7A564122B9272A210C0BA904FA12AB230E306A882BC1992F0CC328D0237B6194",
        "current_raw_sha256": "D01C9FF988A11BF976F412469A6E769BC72DDAAB1D11B7B4D9FAF8EEC15115B7",
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_identity(name: str, path: Path, expected: str) -> None:
    if not path.is_file() or sha(path) != expected:
        raise RuntimeError(f"{name} identity mismatch: {path}")


def extract_function(text: str, marker: str) -> str:
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise RuntimeError(f"unterminated protected function: {marker}")


def protected_function_audit(driver_text: str) -> dict:
    audit = {}
    for name, expected in PROTECTED_FUNCTIONS.items():
        body = extract_function(driver_text, f"static bool {name}")
        observed = hashlib.sha256(body.encode("utf-8")).hexdigest().upper()
        audit[name] = {
            "registry_normalized_sha256": expected["registry_normalized_sha256"],
            "observed_raw_sha256": observed,
            "raw_baseline_locked": observed == expected["current_raw_sha256"],
            "registry_hash_preserved_by_raw_lock": observed == expected["current_raw_sha256"],
        }
    return audit


def canonical_union_oracle() -> dict:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    payload = PAYLOAD.read_bytes()
    width = int(plan["width"])
    height = int(plan["height"])
    row_bytes = width // 8
    transitions = []
    black_points = []
    for frame_index in range(len(plan["entries"])):
        frame = payload[frame_index * 5000:(frame_index + 1) * 5000]
        for y in range(height):
            for x in range(width):
                if not (frame[y * row_bytes + x // 8] & (0x80 >> (x % 8))):
                    black_points.append((x, y))
    for index in range(len(plan["entries"])):
        previous_index = (index - 1) % len(plan["entries"])
        previous = payload[previous_index * 5000:(previous_index + 1) * 5000]
        current = payload[index * 5000:(index + 1) * 5000]
        changed = [(offset, value, current[offset])
                   for offset, (value, current_value) in enumerate(zip(previous, current))
                   if value != current_value]
        if not changed:
            transitions.append({"frame": index, "suppressed": True})
            continue
        byte_start = min(offset % row_bytes for offset, _, _ in changed)
        byte_end = max(offset % row_bytes for offset, _, _ in changed)
        y_start = min(offset // row_bytes for offset, _, _ in changed)
        y_end = max(offset // row_bytes for offset, _, _ in changed)
        exact = all(byte_start <= offset % row_bytes <= byte_end and
                    y_start <= offset // row_bytes <= y_end
                    for offset, _, _ in changed)
        transitions.append({
            "frame": index,
            "previous_frame": previous_index,
            "suppressed": False,
            "x_start_byte": byte_start,
            "x_end_byte": byte_end,
            "y_start": y_start,
            "y_end": y_end,
            "changed_bytes": len(changed),
            "changed_pixels": sum((before ^ after).bit_count() for _, before, after in changed),
            "union_exact": exact,
            "byte_aligned": True,
        })
    max_transition = max((item for item in transitions if not item.get("suppressed")),
                         key=lambda item: item["changed_pixels"])
    return {
        "schema": "companion.comp_req_611.canonical_union_oracle.v1",
        "pixel_format": plan["pixel_format"],
        "frame_count": len(plan["entries"]),
        "cycle_transition_count": len(transitions),
        "transitions": transitions,
        "black_bbox": {
            "x_start": min(x for x, _ in black_points),
            "x_end": max(x for x, _ in black_points),
            "y_start": min(y for _, y in black_points),
            "y_end": max(y for _, y in black_points),
        },
        "max_changed_transition": max_transition,
        "all_changed_black_pixels_reachable": all(
            item.get("union_exact", False) for item in transitions),
        "fixed_r12_corridor_rejected": any(
            not item.get("suppressed", False) and
            (item["y_start"] < 22 or item["y_end"] > 127)
            for item in transitions),
    }


def run_generator(plan: Path, payload: Path, header: Path, evidence: Path,
                  upstream_evidence: Path = UPSTREAM_EVIDENCE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(GENERATOR), "--plan", str(plan), "--payload", str(payload),
         "--header", str(header), "--evidence", str(evidence),
         "--upstream-evidence", str(upstream_evidence)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def negative_fixtures() -> dict[str, bool]:
    source_plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source_payload = PAYLOAD.read_bytes()
    source_evidence = json.loads(UPSTREAM_EVIDENCE.read_text(encoding="utf-8"))
    results: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="comp-req-611-negative-") as temp:
        root = Path(temp)

        def expect_reject(name: str, plan_obj: dict, payload: bytes = source_payload,
                          evidence_obj: dict = source_evidence) -> None:
            p = root / f"{name}.json"
            b = root / f"{name}.bin"
            h = root / f"{name}.h"
            e = root / f"{name}.evidence.json"
            u = root / f"{name}.upstream.json"
            p.write_text(json.dumps(plan_obj), encoding="utf-8")
            b.write_bytes(payload)
            u.write_text(json.dumps(evidence_obj), encoding="utf-8")
            result = run_generator(p, b, h, e, u)
            results[name] = result.returncode != 0

        cases = {
            "old_black_is_one_payload": (lambda x: x.update({"pixel_format": "row_major_msb_first_1_is_black"})),
            "all_dwell_one": (lambda x: [entry.update({"dwell_commits": 1}) for entry in x["entries"]]),
            "swapped_entries": (lambda x: x["entries"].__setitem__(0, x["entries"][1])),
            "skipped_blink_open": (lambda x: x["entries"].pop(12)),
            "adjacent_duplicate_source": (lambda x: x["entries"][1].update({"id": x["entries"][0]["id"]})),
            "ignored_dwell": (lambda x: x.update({"cadence_ms": 1})),
            "stale_plan": (lambda x: x["entries"][0].update({"id": "stale"})),
        }
        for name, mutate in cases.items():
            candidate = json.loads(json.dumps(source_plan))
            mutate(candidate)
            expect_reject(name, candidate)
        expect_reject("stale_payload", source_plan,
                      source_payload[:-1] + bytes([source_payload[-1] ^ 0xFF]))
        evidence_cases = {
            "evidence_status_tampered": lambda x: x.update({"status": "FAIL"}),
            "evidence_check_tampered": lambda x: x["checks"].__setitem__(next(iter(x["checks"])), False),
            "evidence_page_tampered": lambda x: x["page"].update({"sha256": "0" * 64}),
            "evidence_plan_tampered": lambda x: x["canonical_frame_plan"].update({"sha256": "0" * 64}),
            "evidence_payload_tampered": lambda x: x["canonical_frame_plan"].update({"wb55_payload_sha256": "0" * 64}),
        }
        for name, mutate in evidence_cases.items():
            candidate = json.loads(json.dumps(source_evidence))
            mutate(candidate)
            expect_reject(name, source_plan, evidence_obj=candidate)

        runtime_only = json.loads(json.dumps(source_evidence))
        runtime_only.setdefault("runtime_audit", {})["duration_ms"] = 1
        runtime_only["runtime_audit"]["trace"] = ["volatile-only"]
        p = root / "runtime_only_plan.json"
        b = root / "runtime_only_payload.bin"
        h = root / "runtime_only.h"
        e = root / "runtime_only.evidence.json"
        u = root / "runtime_only.upstream.json"
        # Preserve the exact immutable plan bytes; only runtime evidence is
        # changing in this acceptance case.
        p.write_bytes(PLAN.read_bytes())
        b.write_bytes(source_payload)
        u.write_text(json.dumps(runtime_only), encoding="utf-8")
        result = run_generator(p, b, h, e, u)
        results["runtime_only_evidence_change_accepted"] = result.returncode == 0
        results["runtime_only_frame_identity_unchanged"] = (
            result.returncode == 0 and GENERATED_HEADER.read_bytes() == h.read_bytes())
    return results


def build_o2() -> tuple[int, Path]:
    make = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/tools/bin/make.exe")
    toolchain = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin")
    BUILD.mkdir(parents=True, exist_ok=True)
    command = [str(make), "-f", "Makefile", "-B", "-j2", "C_OPT=-O2", "SHELL=cmd.exe",
               f"TOOLCHAIN={toolchain.as_posix()}", "EPAPER_SSD1681_BRINGUP=1",
               "EPAPER_MENU=1", "EPAPER_SSD1681_HAS_BUSY=1", "EPAPER_SSD1681_VERBOSE_TRACE=1",
               "EPAPER_SSD1681_COMP_REQ_611_CANONICAL_SYNC=1",
               f"BUILD_DIR={BUILD.as_posix()}", "TARGET=Companion_Nucleo_WB55RG_Bringup"]
    proc = subprocess.run(command, cwd=ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup",
                          capture_output=True, text=True, check=False)
    log = OUT / "o2-build.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    return proc.returncode, log


def object_call_graph_proof() -> dict:
    toolchain = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin")
    nm = toolchain / "arm-none-eabi-nm.exe"
    objdump = toolchain / "arm-none-eabi-objdump.exe"
    if not nm.is_file() or not objdump.is_file() or not ELF.is_file():
        raise RuntimeError("object call-graph proof tool or ELF is missing")
    result = subprocess.run([str(nm), "-a", "-C", str(ELF)],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    proof_path = OUT / "o2-object-call-graph.txt"
    proof_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    required = {
        "runner_entry": "comp_req_611_canonical_runner_service",
        "baseline_adapter": "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff",
        "movement_adapter": "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff",
        "r12_mapping_helper": "ssd1681_comp_req_611_apply_r12_target_mapping",
    }
    present = {name: symbol in result.stdout for name, symbol in required.items()}
    disassembly = subprocess.run([str(objdump), "-d", "-C", str(ELF)],
                                 cwd=ROOT, capture_output=True, text=True, check=False)
    disassembly_path = OUT / "o2-object-disassembly.txt"
    disassembly_path.write_text(disassembly.stdout + disassembly.stderr, encoding="utf-8")
    def section(symbol: str) -> str:
        marker = f"<{symbol}>:"
        start = disassembly.stdout.find(marker)
        if start < 0:
            return ""
        tail = disassembly.stdout[start:]
        match = re.search(r"\r?\n[0-9a-f]+ <(?!" + re.escape(symbol) + r"\+)",
                          tail, re.IGNORECASE)
        return tail[:match.start()] if match else tail
    movement_section = section("companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff")
    baseline_section = section("companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff")
    present["movement_object_contains_cf"] = (
        "@ 0xcf" in movement_section.lower() or "#207" in movement_section.lower())
    present["baseline_object_contains_ff"] = (
        "@ 0xff" in baseline_section.lower() or "#255" in baseline_section.lower())
    present["movement_object_excludes_fc"] = (
        "@ 0xfc" not in movement_section.lower() and "#252" not in movement_section.lower())
    if not all(present.values()):
        raise RuntimeError(f"object call-graph proof failed: {present}")
    return {"path": str(proof_path), "sha256": sha(proof_path),
            "disassembly_path": str(disassembly_path),
            "disassembly_sha256": sha(disassembly_path), "symbols": present}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, path in (("page", PAGE), ("plan", PLAN),
                       ("payload", PAYLOAD), ("frame_header", FRAME_HEADER),
                       ("owner_acceptance", OWNER_ACCEPTANCE)):
        require_identity(name, path, EXPECTED[name])
    for name, path in (("monitor", MONITOR), ("supervisor", SUPERVISOR),
                       ("log_parser", LOG_PARSER), ("cleanup_hex", CLEANUP_HEX),
                       ("cleanup_elf", CLEANUP_ELF)):
        if not path.is_file():
            raise RuntimeError(f"missing execution artifact: {name}: {path}")
    upstream_evidence = json.loads(UPSTREAM_EVIDENCE.read_text(encoding="utf-8"))
    if (upstream_evidence.get("schema") !=
            "companion.comp_req_608.logical_choreography.verification.v1" or
            upstream_evidence.get("status") != "PASS_OWNER_REVIEW_READY" or
            not isinstance(upstream_evidence.get("checks"), dict) or
            not upstream_evidence["checks"] or
            any(value is not True for value in upstream_evidence["checks"].values())):
        raise RuntimeError("COMP-REQ-608 evidence semantic gate failed")
    evidence_plan = upstream_evidence.get("canonical_frame_plan", {})
    if (upstream_evidence.get("page", {}).get("sha256", "").upper() != EXPECTED["page"] or
            evidence_plan.get("sha256", "").upper() != EXPECTED["plan"] or
            evidence_plan.get("wb55_payload_sha256", "").upper() != EXPECTED["payload"]):
        raise RuntimeError("COMP-REQ-608 evidence deterministic identity failed")
    source = json.loads(PLAN.read_text(encoding="utf-8"))
    if source["pixel_format"] != "row_major_msb_first_1_is_white":
        raise RuntimeError("wrong pixel polarity")
    if len(source["entries"]) != 50 or len(PAYLOAD.read_bytes()) != 250000:
        raise RuntimeError("wrong frame count or payload length")
    generator_run = run_generator(PLAN, PAYLOAD, GENERATED_HEADER, GENERATED_INPUT)
    if generator_run.returncode != 0:
        raise RuntimeError(generator_run.stdout + generator_run.stderr)
    negatives = negative_fixtures()
    if not all(negatives.values()):
        raise RuntimeError(f"negative fixture escaped: {negatives}")
    union_oracle = canonical_union_oracle()
    (OUT / "canonical-union-oracle.json").write_text(
        json.dumps(union_oracle, indent=2) + "\n", encoding="utf-8")
    runner_text = RUNNER.read_text(encoding="utf-8")
    make_text = MAKEFILE.read_text(encoding="utf-8")
    main_text = MAIN.read_text(encoding="utf-8")
    required_runner = ("canonical_frame_provider", "dwell_commits", "dwell_ms",
                       "s_next_due_ms", "no request and no refresh", "single_fast_white",
                       "COMP_REQ_611_FRAME_CADENCE_MS",
                       "companion_epaper_panel_stm32wb_set_temporary_partial_limit",
                       "UINT8_MAX", "s_normal_partial_count",
                       "s_auto_maintenance_count", "s_explicit_cleanup_count",
                       "auto_maintenance=0", "explicit_cleanup=1",
                       "baseline_full_expected=1",
                       "COMP_REQ_611_TRACE_RING_CAPACITY",
                       "observation_ready", "continue=1",
                       "comp_req_611_canonical_runner_request_stop",
                       "comp_req_611_canonical_runner_accept_host_byte",
                       "cached_mode2_0xcf_dynamic_diff",
                       "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff",
                       "window=", "transaction_ms=", "busy_ms=", "control=0x%02X")
    if any(token not in runner_text for token in required_runner):
        raise RuntimeError("runner lacks a required dwell/source/cleanup contract")
    if "COMP_REQ_611_CANONICAL" in runner_text or "screen_framebuffer" in runner_text:
        raise RuntimeError("runner contains an unintended redraw path")
    if "COMPANION_EPAPER_SSD1681_COMP_REQ_611_CANONICAL_SYNC 0" not in main_text:
        raise RuntimeError("611 is not default-off")
    if "EPAPER_SSD1681_COMP_REQ_611_CANONICAL_SYNC" not in make_text:
        raise RuntimeError("611 build switch missing")
    if "COMP_EPAPER_REFRESH_MAINTENANCE" in runner_text:
        raise RuntimeError("611 runner still routes cleanup through ordinary maintenance policy")
    if "companion_epaper_panel_stm32wb_set_temporary_partial_limit(UINT8_MAX)" not in runner_text:
        raise RuntimeError("611 runner does not bind the temporary partial limit after init")
    if ("service_comp_req_611_host_stop" not in main_text or
            "COMP_REQ_611_STOP" not in RUNNER.read_text(encoding="utf-8")):
        raise RuntimeError("611 host stop channel is not connected to the runner")
    driver_text = DRIVER.read_text(encoding="utf-8")
    adapter_start = driver_text.index(
        "bool companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff")
    adapter_end = driver_text.index(
        "static bool ssd1681_native_two_pass_frame", adapter_start)
    adapter_text = driver_text[adapter_start:adapter_end]
    protected_audit = protected_function_audit(driver_text)
    transport_audit = {
        "protected_function_bodies_locked": all(
            value["raw_baseline_locked"] for value in protected_audit.values()),
        "protected_function_audit": protected_audit,
        "accepted_function_present": "static bool ssd1681_native_cached_mode2_movement_activation" in driver_text,
        "accepted_mode2_source_0xcf": "native_mode2_source[] = {0xCFu}" in driver_text,
        "accepted_movement_reset_zero": "ssd1681_native_two_pass_source_reset" not in
            extract_function(driver_text, "static bool ssd1681_native_cached_mode2_movement_activation"),
        "accepted_movement_has_no_0x26": "ssd1681_command_data(0x26u" not in
            extract_function(driver_text, "static bool ssd1681_native_cached_mode2_movement_activation"),
        "public_adapter_calls_accepted_function":
            "ssd1681_native_cached_mode2_movement_activation" in adapter_text,
        "public_adapter_uses_dynamic_difference":
            "ssd1681_window_from_difference()" in adapter_text,
        "public_adapter_uses_r12_vertical_mapping":
            "ssd1681_comp_req_611_apply_r12_target_mapping" in adapter_text and
            "frame_apply_horizontal_mirror" not in adapter_text and
            "frame_apply_target_rotation" not in adapter_text,
        "baseline_uses_single_ff_adapter":
            "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff" in runner_text and
            "baseline_full_0xff" in runner_text,
        "cleanup_uses_single_ff_adapter":
            "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff" in runner_text and
            "cleanup=single_fast_white" in runner_text,
        "public_adapter_has_no_ordinary_partial_control":
            "0xFCu" not in adapter_text and "COMP_EPAPER_REFRESH_PARTIAL" not in adapter_text,
        "runner_calls_public_adapter":
            "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff" in runner_text,
        "runner_never_calls_ordinary_adapter":
            "comp_epaper_panel_adapter_refresh_card" not in runner_text and
            "COMP_EPAPER_REFRESH_PARTIAL" not in runner_text,
        "host_stop_channel_reaches_runner":
            "service_comp_req_611_host_stop" in main_text and
            "comp_req_611_canonical_runner_accept_host_byte" in RUNNER_H.read_text(encoding="utf-8") and
            "COMP_REQ_611_STOP" in RUNNER.read_text(encoding="utf-8"),
        "ordinary_partial_0xfc_is_unreachable_from_611":
            "decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL" in driver_text and
            "? 0xFCu" in driver_text and
            "COMP_EPAPER_REFRESH_PARTIAL" not in runner_text,
        "fixed_r12_corridor_rejected": union_oracle["fixed_r12_corridor_rejected"],
    }
    (OUT / "r12-transport-audit.json").write_text(
        json.dumps(transport_audit, indent=2) + "\n", encoding="utf-8")
    if (not transport_audit["protected_function_bodies_locked"] or
            not transport_audit["accepted_function_present"] or
            not transport_audit["accepted_mode2_source_0xcf"] or
            not transport_audit["accepted_movement_reset_zero"] or
            not transport_audit["accepted_movement_has_no_0x26"] or
            not transport_audit["public_adapter_calls_accepted_function"] or
            not transport_audit["public_adapter_uses_dynamic_difference"] or
            not transport_audit["public_adapter_uses_r12_vertical_mapping"] or
            not transport_audit["baseline_uses_single_ff_adapter"] or
            not transport_audit["cleanup_uses_single_ff_adapter"] or
            not transport_audit["public_adapter_has_no_ordinary_partial_control"] or
            not transport_audit["runner_calls_public_adapter"] or
            not transport_audit["runner_never_calls_ordinary_adapter"] or
            not transport_audit["host_stop_channel_reaches_runner"] or
            not transport_audit["ordinary_partial_0xfc_is_unreachable_from_611"]):
        no_go = {
            "schema": "companion.comp_req_611.lower.no_go.v2",
            "status": "NO_GO_R12_CANONICAL_TRANSPORT_NOT_BOUND",
            "reason": "611 must feed full previous/current union into the accepted R12 cached Mode2 core without reaching ordinary PARTIAL=0xFC.",
            "deterministic_art_identity": {
                "page_sha256": sha(PAGE), "plan_sha256": sha(PLAN),
                "payload_sha256": sha(PAYLOAD), "pixel_format": "row_major_msb_first_1_is_white",
            },
            "latest_runtime_evidence_sha256_informational_only": sha(UPSTREAM_EVIDENCE),
            "protected": {
                "function_bodies": protected_audit,
                "frame_header_sha256": sha(FRAME_HEADER),
                "owner_acceptance_sha256": sha(OWNER_ACCEPTANCE),
            },
            "union_oracle_path": str(OUT / "canonical-union-oracle.json"),
            "transport_audit_path": str(OUT / "r12-transport-audit.json"),
            "required_minimal_main_change": "Bind the 611 runner exclusively to the public previous/current dynamic-diff adapter and accepted cached Mode2 activation.",
            "hardware_contact": 0, "write": 0, "flash": 0, "reset": 0, "popup": 0,
        }
        (OUT / "NO_GO.json").write_text(json.dumps(no_go, indent=2) + "\n", encoding="utf-8")
        (OUT / "MACHINE_READY.json").write_text(json.dumps(no_go, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(no_go["reason"])
    negatives["adjacent_duplicate_refresh"] = (
        "no request and no refresh" in runner_text and
        "if ((int32_t)(now - s_next_due_ms) < 0)" in runner_text)
    negatives["ignored_dwell_runtime"] = (
        "dwell_ms = (uint32_t)comp_req_611_dwell_commits[s_next_frame]" in runner_text and
        "s_next_due_ms = start_ms + dwell_ms" in runner_text)
    if not all(negatives.values()):
        raise RuntimeError(f"runtime negative contract escaped: {negatives}")
    parser_self_test = subprocess.run(
        ["python", str(LOG_PARSER), "--self-test"], cwd=ROOT,
        capture_output=True, text=True, check=False)
    if parser_self_test.returncode != 0:
        raise RuntimeError("611 serial parser self-test failed: " +
                           parser_self_test.stdout + parser_self_test.stderr)
    return_code, build_log = build_o2()
    if return_code != 0 or not HEX.is_file() or not ELF.is_file() or not BIN.is_file():
        raise RuntimeError("O2 build did not produce complete ELF/HEX/BIN")
    object_proof = object_call_graph_proof()
    if not all(value["raw_baseline_locked"] for value in protected_audit.values()):
        raise RuntimeError("protected accepted function body changed")
    if sha(FRAME_HEADER) != EXPECTED["frame_header"]:
        raise RuntimeError("protected frame header changed during build")
    checkonly = {"hardware_contact": 0, "write": 0, "flash": 0, "reset": 0, "popup": 0}
    artifacts = {
        "page_sha256": sha(PAGE), "latest_runtime_evidence_sha256_informational_only": sha(UPSTREAM_EVIDENCE),
        "upstream_verifier_sha256": EXPECTED["verifier"], "plan_sha256": sha(PLAN),
        "payload_sha256": sha(PAYLOAD), "generated_header_sha256": sha(GENERATED_HEADER),
        "input_evidence_sha256": sha(GENERATED_INPUT), "runner_sha256": sha(RUNNER),
        "runner_header_sha256": sha(RUNNER_H), "generator_sha256": sha(GENERATOR),
        "launcher_sha256": sha(LAUNCHER),
        "monitor_sha256": sha(MONITOR), "supervisor_sha256": sha(SUPERVISOR),
        "log_parser_sha256": sha(LOG_PARSER), "cleanup_hex_sha256": sha(CLEANUP_HEX),
        "cleanup_elf_sha256": sha(CLEANUP_ELF),
        "verifier_sha256": sha(Path(__file__)), "makefile_sha256": sha(MAKEFILE),
        "main_sha256": sha(MAIN), "build_log_sha256": sha(build_log),
        "hex_sha256": sha(HEX), "elf_sha256": sha(ELF), "bin_sha256": sha(BIN),
    }
    runtime_contract = {
        "frame_entries": 50,
        "baseline_full": 1,
        "normal_partial": 49,
        "auto_maintenance": 0,
        "explicit_cleanup": 1,
        "temporary_partial_limit": 255,
        "partial_limit_bound_after_target_init": True,
        "baseline_full_expected_flicker": True,
        "automatic_fast_or_maintenance_during_score": 0,
        "serial_log_parser": "verify_comp_req_611_canonical_sync_log.py",
        "qualification_frames": 50,
        "qualification_requires_observation_ready": True,
        "prompt_requires_live_monitor": True,
        "prompt_buttons": ["通过", "失败"],
        "cleanup_single_fast_white": True,
        "restore_application_bytes": 524288,
        "restore_application_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    }
    manifest = {
        "schema": "companion.comp_req_611.lower.machine_ready.v1",
        "status": "MACHINE_READY_CHECKONLY_MAIN_REVIEW_REQUIRED",
        "hardware_contact": 0, "execute_authorized": False,
        "checkonly": checkonly, "previous_609": {"status": "NO_GO", "flash_allowed": False},
        "deterministic_art_identity": {"page_sha256": EXPECTED["page"],
                      "verifier_sha256": EXPECTED["verifier"], "plan_sha256": EXPECTED["plan"],
                      "payload_sha256": EXPECTED["payload"], "frame_count": 50,
                      "frame_bytes": 5000, "payload_bytes": 250000,
                      "pixel_format": "row_major_msb_first_1_is_white"},
        "runtime_evidence": {"latest_sha256_informational_only": sha(UPSTREAM_EVIDENCE)},
        "protected": {
            "function_bodies": protected_audit,
            "frame_header_sha256": EXPECTED["frame_header"],
            "owner_acceptance_sha256": EXPECTED["owner_acceptance"],
        },
        "negative_fixtures": negatives, "runtime_contract": runtime_contract,
        "artifacts": artifacts,
        "object_call_graph_proof": object_proof,
        "execute_command": "pwsh -NoProfile -File tools/run_comp_req_611_canonical_sync.ps1 -Execute -MainReviewArtifact docs/validation/comp-req-611-lower-sync/main-review-authorized.json",
        "hardware_note": "No hardware action is authorized by this MACHINE_READY; return to main for review.",
        "execution_tools": {
            "monitor": str(MONITOR), "supervisor": str(SUPERVISOR),
            "log_parser": str(LOG_PARSER), "cleanup_hex": str(CLEANUP_HEX),
            "cleanup_elf": str(CLEANUP_ELF),
        },
    }
    NO_GO.write_text(json.dumps({
        "schema": "companion.comp_req_611.lower.no_go.v2",
        "status": "SUPERSEDED_BY_MACHINE_READY",
        "superseded_by": str(OUT / "MACHINE_READY.json"),
        "historical_reason": "Pre-adapter transport NO_GO retained for audit only.",
        "hardware_contact": 0,
        "flash_allowed": False,
    }, indent=2) + "\n", encoding="utf-8")
    (OUT / "MACHINE_READY.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
