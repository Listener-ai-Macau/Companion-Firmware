"""Create the stable offline-only R11 MACHINE_READY manifest."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r11_native_cached_mode2_throw_arc"
OUT = ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-machine-ready-20260722.json"
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
        "elf": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R11NativeCachedMode2ThrowArc.elf",
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R11NativeCachedMode2ThrowArc.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "header": ROOT / "app/companion_pendant/epaper/r11_native_cached_mode2_throw_arc.h",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log.py",
        "oracle": ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc.py",
        "static": ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_static.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r11_native_cached_mode2_throw_arc_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
        "lifecycle": ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_lifecycle.py",
        "oracle_artifact": ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-oracle-20260722.json",
        "static_artifact": ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-static-20260722.json",
        "lifecycle_artifact": ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-lifecycle-20260722.json",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-work-package-20260722.md",
    }
    missing = [rel(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing MACHINE_READY input: " + ", ".join(missing))
    source = paths["driver"].read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    audit = json.loads(CURRENT_GOAL.read_text(encoding="utf-8"))
    oracle_artifact = json.loads(paths["oracle_artifact"].read_text(encoding="utf-8"))
    static_artifact = json.loads(paths["static_artifact"].read_text(encoding="utf-8"))
    lifecycle_artifact = json.loads(paths["lifecycle_artifact"].read_text(encoding="utf-8"))
    checks = {
        "registry_comp_req_367": "| COMP-REQ-367 |" in registry and "accept 480/reject 481" in registry,
        "current_goal_audit_present": audit.get("codex_goal_status") == "active" and not audit.get("errors"),
        "protected_hash": sha(PROTECTED) == PROTECTED_SHA,
        "restore_hash_contract": RESTORE_SHA == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
        "default_off": "#define COMPANION_EPAPER_SSD1681_R11_NATIVE_CACHED_MODE2_THROW_ARC_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in source,
        "cadence_480": "cadence_limit_ms=480 cadence_target_ms=450" in source and "start_delta_ms > R11_NATIVE_CADENCE_LIMIT_MS" in source,
        "no_physical_authorization": not any(ROOT.glob(".cache/validation/*r11-native-cached-mode2-throw-arc*authorization*.json")),
        "diff_scope": all(token in source for token in ("full_current_rewrite=1", "movement_reset=0", "source_ff=1", "movement_source_cf=1")),
        "oracle_pass": oracle_artifact.get("status") == "PASS"
        and oracle_artifact.get("positive_fixtures", {}).get("cadence_480_accepted", {}).get("accepted") is True
        and oracle_artifact.get("positive_fixtures", {}).get("cadence_480_accepted", {}).get("rejected") is False
        and oracle_artifact.get("negative_fixtures", {}).get("cadence_481_rejected", {}).get("rejected") is True,
        "static_pass": static_artifact.get("status") == "PASS",
        "lifecycle_selftest_checkonly_pass": lifecycle_artifact.get("status") == "PASS"
        and lifecycle_artifact.get("hardware_contact") == 0
        and lifecycle_artifact.get("authorization_created") is False,
    }
    artifacts = {key: sha(path) for key, path in paths.items()}
    artifacts["parser_sha256"] = artifacts["parser"]
    errors = [key for key, value in checks.items() if not value]
    obj = {
        "schema_id": "companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.machine_ready.v2",
        "status": "MACHINE_READY_R11_NATIVE_CACHED_MODE2_THROW_ARC_OFFLINE_ONLY" if not errors else "NO_GO_R11_MACHINE_READY",
        "authority": "COMP-REQ-367",
        "candidate": "r11_native_cached_mode2_throw_arc",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "claim_only_authorized": False,
        "production_enabled": False,
        "lut": {"kind": "official_ssd1681_otp_mode2", "custom_lut_loads": 0, "sha256": "OFFICIAL_OTP_MODE2_NO_CUSTOM_LUT_FILE"},
        "checkonly": {"hardware_contact": 0, "writes": 0, "programmer_calls": 0, "serial_open_count": 0, "reset_count": 0, "refresh_count": 0, "popup_count": 0, "retry_count": 0, "ring_bytes": 65536, "persistent_launcher": True},
        "geometry": {"disk": "solid_centered_integer_24x24_448_pixels", "nodes": [[32,112],[44,91],[56,76],[68,67],[80,64],[92,67],[104,76],[116,91],[128,112]], "path_transitions": 16, "step_px": 12, "travel_px": 96, "apex_px": 48, "corridor": "3-19,64-135", "corridor_bytes": 1224, "full_current_rewrite": True},
        "transport": {"baseline_source_resets": 1, "movement_source_resets": 0, "baseline_source_ff": 1, "movement_source_cf": 1, "qualification_frames": 16, "minimum_contiguous_loops": 2, "real_cadence_required": True, "busy_limit_ms": 600, "transaction_limit_ms": 460, "cadence_accept_ms": "1..480", "cadence_reject_ms": 481, "cadence_target_ms": 450, "telemetry_max_bytes_including_crlf": 192, "ring_bytes": 65536},
        "lifecycle": {"execute_path": "future_hash_bound_one_shot_only", "popup": "not_invoked_offline", "preclean": "future_promptless_dual_plane_white", "postclean": "future_promptless_dual_plane_white", "restore_sha256": RESTORE_SHA, "normal_resume": "future_process_audited", "automatic_retries": 0},
        "future_execute_template": "pwsh -NoProfile -File tools/start_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1 -Execute -OutRoot <FUTURE_FRESH_ROOT> -AuthorizationArtifact <FUTURE_R11_AUTHORIZATION_JSON>",
        "protected_acceptance_sha256": PROTECTED_SHA,
        "checks": checks,
        "artifacts": artifacts,
        "artifact_paths": {key: rel(path) for key, path in paths.items()},
        "errors": errors,
    }
    rendered = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    OUT.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print(f"MACHINE_READY_SHA256={sha(OUT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
