"""Render and verify the reproducible offline MACHINE_READY manifest."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-machine-ready-20260722.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_native_two_pass_fine_stride"
PROTECTED = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
RESTORE = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def rel(path: Path) -> str: return path.relative_to(ROOT).as_posix()

def main() -> int:
    paths = {
        "elf": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10NativeTwoPassFineStride.elf",
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10NativeTwoPassFineStride.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "header": ROOT / "app/companion_pendant/epaper/r10_native_two_pass_fine_stride.h",
        "parser_sha256": ROOT / "tools/verify_wb55_ssd1681_r10_native_two_pass_fine_stride_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r10_native_two_pass_fine_stride_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1",
        "static_verifier": ROOT / "tools/verify_wb55_ssd1681_r10_native_two_pass_fine_stride_static.py",
        "oracle": ROOT / "tools/verify_wb55_ssd1681_r10_native_two_pass_fine_stride.py",
        "focused_parser": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-oracle-20260722.json",
        "parser_fixtures": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-log-parser-20260722.json",
        "r6_r2_disposition": ROOT / "docs/validation/companion-ssd1681-r10-r6-r2-runtime-disposition-20260722.json",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-work-package-20260722.md",
    }
    missing = [rel(p) for p in paths.values() if not p.is_file()]
    if missing: raise SystemExit("missing MACHINE_READY input: " + ", ".join(missing))
    artifacts = {key: sha(path) for key, path in paths.items()}
    artifacts["parser"] = artifacts["parser_sha256"]
    artifacts["candidate_hex_sha256"] = artifacts["hex"]
    obj = {
        "schema_id": "companion.wb55.ssd1681.r10_native_two_pass_fine_stride.machine_ready.v1",
        "status": "MACHINE_READY_R10_NATIVE_TWO_PASS_FINE_STRIDE_OFFLINE_ONLY",
        "authority": "COMP-REQ-349",
        "candidate": "r10_native_two_pass_fine_stride",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "production_enabled": False,
        "checkonly": {"hardware_contact": 0, "writes": 0, "popup_count": 0, "retry_count": 0, "child_exit_code": 0, "durable_stdout_stderr": True},
        "geometry": {"disk": "solid_12x12_112_pixels", "y": 80, "x_start": 32, "x_end": 64, "step_px": 2, "travel_px": 32, "qualification_frames": 16, "activations_after_baseline": 32},
        "transport": {
            "baseline": "one source-bound activation",
            "movement": "previous-black pass then full previous/current diff pass",
            "source_activation": ["hardware_reset_low_10ms", "hardware_reset_high_10ms", "ready", "0x3C=0x80", "0x44/0x45/0x4E/0x4F", "current_0x24", "0x22=0xFF", "0x20", "BUSY"],
            "baseline_activation_count": 1,
            "qualification_logical_frames": 16,
            "qualification_activation_count": 32,
            "loop_activation_count_per_record": 2,
            "candidate_panel_write_formula": "1+32+2*loop_records",
            "busy_limit_ms": 600,
            "reset_telemetry_separate_from_busy": True,
            "forbidden": ["0x12 candidate startup", "0x26 motion", "0x32", "0x37", "0xC7", "custom LUT", "full-frame candidate write", "third activation", "retry", "maintenance", "production"],
        },
        "restore_sha256": RESTORE,
        "protected_acceptance_sha256": PROTECTED,
        "cached_gates": {"r6_r2_runtime_disposition": "HISTORICAL_ARCHIVED", "unchanged_lifecycle": "REUSED_BY_SCOPE", "broad_suites": "NOT_RUN"},
        "artifacts": artifacts,
        "artifact_paths": {key: rel(path) for key, path in paths.items()},
    }
    rendered = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
        OUT.parent.mkdir(parents=True, exist_ok=True); tmp = OUT.with_suffix(OUT.suffix + ".tmp"); tmp.write_text(rendered, encoding="utf-8"); tmp.replace(OUT)
    print(rendered, end="")
    print(f"MACHINE_READY_SHA256={sha(OUT)}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
