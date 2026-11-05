"""Render the reproducible, default-off MACHINE_READY manifest for R10 cadence."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-machine-ready-20260722.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_native_guarded_corridor_large_cadence"
RESTORE = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
PROTECTED = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def rel(path: Path) -> str: return path.relative_to(ROOT).as_posix()


def main() -> int:
    paths = {
        "elf": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10NativeGuardedCorridorLargeCadence.elf",
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10NativeGuardedCorridorLargeCadence.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "header": ROOT / "app/companion_pendant/epaper/r10_native_guarded_corridor_large_cadence.h",
        "parser_sha256": ROOT / "tools/verify_wb55_ssd1681_r10_native_guarded_corridor_large_cadence_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r10_native_guarded_corridor_large_cadence.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r10_native_guarded_corridor_large_cadence.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r10_native_guarded_corridor_large_cadence_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r10_native_guarded_corridor_large_cadence.ps1",
        "static_verifier": ROOT / "tools/verify_wb55_ssd1681_r10_native_guarded_corridor_large_cadence_static.py",
        "oracle": ROOT / "tools/verify_wb55_ssd1681_r10_native_guarded_corridor_large_cadence.py",
        "oracle_artifact": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-oracle-20260722.json",
        "static_artifact": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-static-20260722.json",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-work-package-20260722.md",
    }
    missing = [rel(p) for p in paths.values() if not p.is_file()]
    if missing: raise SystemExit("missing MACHINE_READY input: " + ", ".join(missing))
    artifacts = {key: sha(path) for key, path in paths.items()}
    artifacts["parser"] = artifacts["parser_sha256"]
    artifacts["candidate_hex_sha256"] = artifacts["hex"]
    obj = {
        "schema_id": "companion.wb55.ssd1681.r10_native_guarded_corridor_large_cadence.machine_ready.v3",
        "status": "MACHINE_READY_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_OFFLINE_ONLY",
        "authority": "COMP-REQ-357", "candidate": "r10_native_guarded_corridor_large_cadence",
        "hardware_contact": 0, "execute_authorized": False, "authorization_created": False,
        "production_enabled": False,
        "checkonly": {"hardware_contact": 0, "writes": 0, "popup_count": 0, "retry_count": 0, "child_exit_code": 0, "durable_stdout_stderr": True, "ring_bytes": 65536},
        "geometry": {"disk": "solid_centered_integer_24x24_448_pixels", "y": 80, "x_start": 32, "x_end": 64, "step_px": 2, "travel_px": 32, "qualification_frames": 16, "loop_transitions": 32, "loop_unbounded": True},
        "transport": {"baseline_activation_count": 1, "movement_activation_count": 1, "qualification_activation_count": 16, "loop_activation_count_per_record": 1, "candidate_panel_write_formula": "1+16+1*loop_records", "source_activation": ["hardware_reset_low_10ms", "hardware_reset_high_10ms", "ready", "0x3C=0x80", "0x44/0x45/0x4E/0x4F", "CPU_held_current_0x24", "0x22=0xFF", "0x20", "BUSY"], "busy_limit_ms": 600, "transaction_elapsed_field": "transaction_elapsed_ms", "loop_start_to_start_field": "start_delta_ms", "compact_loop_record_max_bytes": 384, "start_to_start_target_ms": 550, "physical_start_to_start_cadence": "UNPROVEN_UNTIL_EXECUTE", "cadence_best_effort": True, "qualification_loop_minimum": 2, "qualification_cadence_measurements_minimum": 1, "finalization_loop_minimum": 2, "cadence_metrics_source": "parsed_records_not_constant", "diff_window": "fixed_guarded_corridor_x_bytes_3_11_y_80_103_216_bytes", "full_corridor_current_bytes_rewrite": True, "full_frame_writes": 0, "prior_position_rewhitened": True, "forbidden": ["0x26", "0x32", "0x37", "0xC7", "0xF7", "custom LUT", "full-frame", "second activation", "third activation", "post-sync", "retry", "maintenance", "production"]},
        "lifecycle": {"preclean": "promptless dual-plane White", "popup": "exactly one canonical Chinese pass/fail after machine qualification, concurrent with loop", "postclean": "promptless dual-plane White", "restore_sha256": RESTORE, "normal_resume": True, "fault_popup_count": 0},
        "protected_acceptance_sha256": PROTECTED,
        "cached_gates": {"broad_historical_suites": "NOT_RUN", "physical_panel_residue": "UNPROVEN_HUMAN_BOUNDARY", "r2_quality_floor": "PRESERVED"},
        "artifacts": artifacts, "artifact_paths": {key: rel(path) for key, path in paths.items()},
    }
    rendered = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(rendered, encoding="utf-8")
    print(rendered, end=""); print(f"MACHINE_READY_SHA256={sha(OUT)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
