"""Create the stable offline-only R12 MACHINE_READY manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r12_v22_calm_curious_warm_sampler"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-machine-ready-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
CURRENT_GOAL = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
RESTORE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    paths = {
        "elf": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.elf",
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "header": ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler.h",
        "asset_header": ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler_assets.h",
        "asset_generator": ROOT / "tools/generate_r12_v22_asset_header.py",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_log.py",
        "oracle": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.py",
        "static": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_static.py",
        "lifecycle": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_lifecycle.py",
        "machine_ready_generator": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_machine_ready.py",
        "build_helper": ROOT / "tools/build_nucleo_bringup.ps1",
        "makefile": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
        "oracle_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-oracle-20260722.json",
        "static_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-static-20260722.json",
        "lifecycle_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-lifecycle-20260722.json",
        "work_package": ROOT / "docs/validation/companion-r12-v22-calm-curious-warm-sampler-r3-work-package-20260722.json",
        "current_goal_audit": CURRENT_GOAL,
        "product_registry": REGISTRY,
        "protected_acceptance": PROTECTED,
    }
    missing = [rel(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing MACHINE_READY input: " + ", ".join(missing))
    source = paths["driver"].read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    audit = json.loads(CURRENT_GOAL.read_text(encoding="utf-8"))
    oracle = json.loads(paths["oracle_artifact"].read_text(encoding="utf-8"))
    static = json.loads(paths["static_artifact"].read_text(encoding="utf-8"))
    lifecycle = json.loads(paths["lifecycle_artifact"].read_text(encoding="utf-8"))
    checks = {
        "registry_comp_req_375_present": "\n| COMP-REQ-375 |" in registry and "\n| COMP-REQ-376 |" not in registry,
        "registry_comp_req_370_preserved": "COMP-REQ-370" in registry and "accept 480/reject 481" in registry,
        "current_goal_audit_pass": audit.get("codex_goal_status") == "active" and not audit.get("errors"),
        "protected_hash": sha(PROTECTED) == PROTECTED_SHA,
        "restore_hash_contract": RESTORE_SHA == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
        "default_off": "#define COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in source,
        "baseline_full_5000": "baseline frame=0 window=0-24,0-199 bytes=5000" in source,
        "movement_corridor_1908": "corridor=4-21,72-177 corridor_bytes=1908" in source,
        "three_frame_path": "frames=calm,curious,warm path=0-1-2-1-0" in source,
        "cadence_480": "cadence_ms=480" in source and "start_delta_ms > R11_NATIVE_CADENCE_LIMIT_MS" in source,
        "oracle_pass": oracle.get("status") == "PASS",
        "oracle_pixel_difference_zero": oracle.get("pixel_oracle", {}).get("source_to_logical_pixel_difference") == 0,
        "oracle_changed_pixels": [item["changed_pixels"] for item in oracle.get("transitions", [])[:4]] == [765, 846, 846, 765],
        "oracle_negative_fixtures": bool(oracle.get("negative_fixtures")) and all(oracle["negative_fixtures"].values()),
        "static_pass": static.get("status") == "PASS" and not static.get("errors"),
        "static_fixed_window_cache": all(static.get("checks", {}).get(key) is True for key in (
            "r12_window_setup_exactly_once_after_baseline_before_qualification",
            "r12_window_setup_exact_44_45_once",
            "r12_window_setup_no_ram_write_or_refresh",
            "r12_movement_counters_exactly_once",
            "r12_movement_has_no_window_or_border_commands",
            "r12_movement_command_order_unchanged",
            "r3_negative_fixtures_rejected",
        )),
        "lifecycle_checkonly_pass": lifecycle.get("status") == "PASS",
        "checkonly_zero_contact": all(lifecycle.get(key) == 0 for key in (
            "hardware_contact", "write_counter_sum", "programmer_calls", "serial_open_count",
            "reset_count", "refresh_count", "popup_count", "retry_count")),
        "no_authorization_created": lifecycle.get("authorization_created") is False and
                                    lifecycle.get("claim_created") is False and lifecycle.get("spent_created") is False and
                                    lifecycle.get("receipt_created") is False,
        "future_auth_exact_376": static.get("future_physical_authorization_requirement_id") == "COMP-REQ-376",
    }
    artifacts = {key: sha(path) for key, path in paths.items()}
    artifacts["parser_sha256"] = artifacts["parser"]
    errors = [key for key, value in checks.items() if not value]
    obj = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.machine_ready.v4",
        "status": "MACHINE_READY_R12_V22_CALM_CURIOUS_WARM_SAMPLER_OFFLINE_ONLY" if not errors else "NO_GO_R12_MACHINE_READY",
        "replaces_rejected_second_machine_ready": True,
        "authority": "COMP-REQ-375", "future_physical_authorization_requirement_id": "COMP-REQ-376",
        "candidate": "r12_v22_calm_curious_warm_sampler", "hardware_contact": 0,
        "execute_authorized": False, "authorization_created": False, "claim_only_authorized": False,
        "production_enabled": False,
        "lut": {"kind": "official_ssd1681_otp_mode2", "custom_lut_loads": 0,
                "sha256": "OFFICIAL_OTP_MODE2_NO_CUSTOM_LUT_FILE"},
        "checkonly": {"hardware_contact": 0, "writes": 0, "programmer_calls": 0, "serial_open_count": 0,
                      "reset_count": 0, "refresh_count": 0, "popup_count": 0, "retry_count": 0,
                      "ring_bytes": 65536, "persistent_launcher": True},
        "frames": {"format": "200x200_1bpp", "ids": {"0": "calm", "1": "curious", "2": "warm"},
                   "path": [0, 1, 2, 1, 0], "qualification_transitions": 16, "qualification_cycles": 4},
        "transport": {"baseline": {"window": "0-24,0-199", "bytes": 5000, "reset": 1,
                                     "ready_checks": 1, "command": "0x24", "control": "0xFF",
                                     "refresh": "0x20", "activations": 1},
                      "one_time_corridor_window_setup": {"after_baseline": True,
                                                          "before_qualification": True,
                                                          "commands": ["0x44", "0x45"],
                                                          "ram_writes": 0, "refreshes": 0,
                                                          "border_writes": 0},
                      "movement": {"window": "4-21,72-177", "bytes": 1908, "reset": 0,
                                   "ready_checks": 1, "command": "0x24", "control": "0xCF",
                                   "refresh": "0x20", "activations": 1,
                                   "counter_commands": ["0x4E", "0x4F"],
                                   "window_commands": 0, "border_commands": 0},
                      "busy_limit_ms": 600, "transaction_limit_ms": 460,
                      "cadence_accept_ms": "1..480", "cadence_reject_ms": 481,
                      "cadence_target_ms": 450, "telemetry_max_bytes_including_crlf": 192,
                      "ring_bytes": 65536},
        "lifecycle": {"execute_path": "future_hash_bound_one_shot_only",
                      "authorization_requirement_id": "COMP-REQ-376", "popup": "not_invoked_offline",
                      "preclean": "future_promptless_dual_plane_white",
                      "postclean": "future_promptless_dual_plane_white", "restore_sha256": RESTORE_SHA,
                      "normal_resume": "future_process_audited", "automatic_retries": 0},
        "future_execute_template": "pwsh -NoProfile -File tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1 -Execute -OutRoot <FUTURE_FRESH_ROOT> -AuthorizationArtifact <FUTURE_COMP_REQ_376_AUTHORIZATION_JSON>",
        "protected_acceptance_sha256": PROTECTED_SHA, "checks": checks, "artifacts": artifacts,
        "artifact_paths": {key: rel(path) for key, path in paths.items()}, "errors": errors,
    }
    rendered = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    OUT.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print(f"MACHINE_READY_SHA256={sha(OUT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
