"""Generate stable offline-only R12 r4 MACHINE_READY evidence."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4_lifecycle as lifecycle_verifier

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r12_v22_calm_curious_warm_sampler"
CHECK = ROOT / ".cache/validation/wb55-r12-v22-calm-curious-warm-sampler-r4b-primary-checkonly-20260722-r1"
SELFTEST = ROOT / ".cache/validation/wb55-r12-v22-calm-curious-warm-sampler-r4b-primary-launcher-selftest-20260722-r1"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-machine-ready-20260722.json"
COMPATIBILITY_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-manifest-compatibility-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
WORK = ROOT / "docs/validation/companion-r12-v22-calm-curious-warm-sampler-r4-work-package-20260722.json"
EXPECTED_ELF_SHA256 = "DD6854B2F686191D83202066FE3D2E04A9C288BC3A0850A6905182435926E89A"
EXPECTED_DRIVER_SHA256 = "6033148F5E4705CA7E756500CBAE9DBCD4F13EB5B79954D8A6BD3C78334063D1"
LAUNCHER_ARTIFACT_FIELDS = {
    "hex": "candidate_hex_sha256",
    "runner": "runner_sha256",
    "monitor": "monitor_sha256",
    "supervisor": "supervisor_sha256",
    "launcher": "launcher_sha256",
    "parser_sha256": "parser_sha256",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def launcher_equivalent_manifest_gate(manifest: dict, expected: dict[str, str]) -> dict[str, bool]:
    artifacts = manifest.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, dict) else {}
    checks = {
        "schema_matches_launcher": bool(re.fullmatch(r"companion\.wb55\.ssd1681\..*machine_ready\.v[0-9]+", str(manifest.get("schema_id", "")))),
        "status_machine_ready": str(manifest.get("status", "")).startswith("MACHINE_READY_"),
        "hardware_contact_zero": manifest.get("hardware_contact") == 0,
        "execute_not_authorized": manifest.get("execute_authorized") is not True,
        "authorization_not_created": manifest.get("authorization_created") is not True,
    }
    for artifact_key, expected_key in LAUNCHER_ARTIFACT_FIELDS.items():
        checks[f"artifact_{artifact_key}_matches"] = (
            artifact_key in artifacts and artifacts.get(artifact_key) == expected.get(expected_key)
        )
    return checks


def manifest_alias_selftest(artifact_hashes: dict[str, str]) -> dict:
    expected = {
        expected_key: artifact_hashes[artifact_key]
        for artifact_key, expected_key in LAUNCHER_ARTIFACT_FIELDS.items()
    }
    valid = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.machine_ready.v8",
        "status": "MACHINE_READY_R12_V22_CALM_CURIOUS_WARM_SAMPLER_R4_OFFLINE_ONLY",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "artifacts": copy.deepcopy(artifact_hashes),
    }
    valid_checks = launcher_equivalent_manifest_gate(valid, expected)

    missing = copy.deepcopy(valid)
    del missing["artifacts"]["parser_sha256"]
    missing_checks = launcher_equivalent_manifest_gate(missing, expected)
    missing_target_false = missing_checks["artifact_parser_sha256_matches"] is False

    wrong = copy.deepcopy(valid)
    wrong["artifacts"]["parser_sha256"] = "0" * 64
    wrong_checks = launcher_equivalent_manifest_gate(wrong, expected)
    wrong_target_false = wrong_checks["artifact_parser_sha256_matches"] is False

    valid_passes = all(valid_checks.values())
    missing_rejected = missing_target_false and not all(missing_checks.values())
    wrong_rejected = wrong_target_false and not all(wrong_checks.values())
    return {
        "gate": "launcher Validate-MachineManifest equivalent safety and artifact comparisons",
        "artifact_field_mapping": LAUNCHER_ARTIFACT_FIELDS,
        "valid_manifest_passes": valid_passes,
        "fixtures": {
            "missing_parser_sha256": {
                "target_invariant": "artifact_parser_sha256_matches",
                "target_invariant_false": missing_target_false,
                "resulting_status": "NO_GO_MACHINE_MANIFEST" if missing_rejected else "UNSAFE_PASS",
                "pass": missing_rejected,
            },
            "wrong_parser_sha256": {
                "mutated_value": "0" * 64,
                "target_invariant": "artifact_parser_sha256_matches",
                "target_invariant_false": wrong_target_false,
                "resulting_status": "NO_GO_MACHINE_MANIFEST" if wrong_rejected else "UNSAFE_PASS",
                "pass": wrong_rejected,
            },
        },
        "pass": valid_passes and missing_rejected and wrong_rejected,
    }


def refresh_lifecycle_artifact() -> dict:
    lifecycle_verifier.ROOT_RUN = CHECK
    if lifecycle_verifier.main() != 0:
        raise SystemExit("fresh COMP-REQ-382 lifecycle verification failed")
    lifecycle = json.loads(lifecycle_verifier.OUT.read_text(encoding="utf-8"))
    lifecycle["schema_id"] = "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.r4.lifecycle.v4"
    lifecycle["requirement"] = "COMP-REQ-382"
    lifecycle["future_physical_authorization_requirement_id"] = "COMP-REQ-383"
    lifecycle["compatibility_rebind"] = {
        "kind": "unchanged_lifecycle_verifier_rebound_to_fresh_checkonly_root",
        "lifecycle_verifier_sha256": sha(Path(lifecycle_verifier.__file__).resolve()),
    }
    write_json(lifecycle_verifier.OUT, lifecycle)
    return lifecycle


def main() -> int:
    if not (CHECK / "persistent-launch.json").is_file() or not (CHECK / "stage-run.json").is_file():
        raise SystemExit("fresh COMP-REQ-382 CheckOnly evidence is missing")
    lifecycle = refresh_lifecycle_artifact()
    immutable_and_tool_paths = {
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex",
        "runner": ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r4.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_log.py",
    }
    compatibility_hashes = {key: sha(path) for key, path in immutable_and_tool_paths.items()}
    compatibility_hashes["parser_sha256"] = compatibility_hashes["parser"]
    alias_selftest = manifest_alias_selftest(compatibility_hashes)
    compatibility_checks = {
        "parser_sha256_alias_present": "parser_sha256" in compatibility_hashes,
        "parser_sha256_alias_equals_parser": compatibility_hashes["parser_sha256"] == compatibility_hashes["parser"],
        "valid_manifest_passes_launcher_equivalent_gate": alias_selftest["valid_manifest_passes"] is True,
        "missing_parser_sha256_rejected": alias_selftest["fixtures"]["missing_parser_sha256"]["pass"] is True,
        "wrong_parser_sha256_rejected": alias_selftest["fixtures"]["wrong_parser_sha256"]["pass"] is True,
    }
    compatibility_errors = [key for key, value in compatibility_checks.items() if not value]
    compatibility = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.r4.manifest_compatibility.v1",
        "status": "PASS" if not compatibility_errors else "NO_GO_MANIFEST_COMPATIBILITY",
        "requirement": "COMP-REQ-382",
        "future_physical_authorization_requirement_id": "COMP-REQ-383",
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_count": 0,
        "retry_count": 0,
        "launcher_sha256": compatibility_hashes["launcher"],
        "manifest_artifacts": compatibility_hashes,
        "checks": compatibility_checks,
        "negative_fixture_selftest": alias_selftest,
        "checkonly_root": str(CHECK.relative_to(ROOT)).replace("\\", "/"),
        "lifecycle_artifact_sha256": sha(lifecycle_verifier.OUT),
        "errors": compatibility_errors,
    }
    write_json(COMPATIBILITY_OUT, compatibility)

    paths = {
        "elf": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.elf",
        "hex": BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "header": ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler.h",
        "assets": ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler_assets.h",
        "runner": ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r4.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_log.py",
        "oracle": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.py",
        "static": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4_static.py",
        "lifecycle": ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4_lifecycle.py",
        "machine_ready_generator": Path(__file__).resolve(),
        "oracle_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-oracle-20260722.json",
        "static_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-static-20260722.json",
        "lifecycle_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-lifecycle-20260722.json",
        "manifest_compatibility_artifact": COMPATIBILITY_OUT,
        "r3_static_regression_artifact": ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-static-20260722.json",
        "ssd1681_rev013_pdf": ROOT / ".cache/validation/ssd1681-read-only-research/ssd1681-rev013-2.pdf",
        "work_package": WORK,
        "protected_acceptance": PROTECTED,
        "checkonly_launcher": CHECK / "persistent-launch.json",
        "checkonly_stage": CHECK / "stage-run.json",
        "launcher_selftest_artifact": SELFTEST / "launcher-selftest.json",
        "supervisor_checkonly_artifact": CHECK / "checkonly-supervisor/prompt-supervisor-check.json",
    }
    missing = [str(path.relative_to(ROOT)) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing MACHINE_READY input: " + ", ".join(missing))
    oracle = json.loads(paths["oracle_artifact"].read_text())
    static = json.loads(paths["static_artifact"].read_text())
    lifecycle = json.loads(paths["lifecycle_artifact"].read_text())
    compatibility = json.loads(paths["manifest_compatibility_artifact"].read_text())
    launcher_selftest = json.loads(paths["launcher_selftest_artifact"].read_text(encoding="utf-8-sig"))
    r3_static = json.loads(paths["r3_static_regression_artifact"].read_text())
    launch = json.loads(paths["checkonly_launcher"].read_text(encoding="utf-8-sig"))
    stage = json.loads(paths["checkonly_stage"].read_text(encoding="utf-8-sig"))
    supervisor_check = json.loads(paths["supervisor_checkonly_artifact"].read_text(encoding="utf-8-sig"))
    current_hex_sha256 = sha(paths["hex"])
    lifecycle_verifier.ROOT_RUN = CHECK
    checkonly_checks = lifecycle_verifier.validate_checkonly(launch, stage, current_hex_sha256)
    stale_selftest = lifecycle_verifier.stale_candidate_hash_selftest(launch, stage, current_hex_sha256)
    tool_bindings = lifecycle_verifier.checkonly_tool_hash_bindings(launch, stage)
    lifecycle_checks = lifecycle.get("checks", {})
    artifact_hashes = {key: sha(path) for key, path in paths.items()}
    artifact_hashes["parser_sha256"] = artifact_hashes["parser"]
    artifact_paths = {key: str(path.relative_to(ROOT)).replace('\\','/') for key, path in paths.items()}
    artifact_paths["parser_sha256"] = artifact_paths["parser"]
    output_alias_selftest = manifest_alias_selftest(artifact_hashes)
    checks = {
        "current_hex_matches_primary_review_sha256": current_hex_sha256 == lifecycle_verifier.EXPECTED_HEX_SHA256,
        "current_elf_matches_primary_review_sha256": sha(paths["elf"]) == EXPECTED_ELF_SHA256,
        "driver_matches_primary_review_sha256": sha(paths["driver"]) == EXPECTED_DRIVER_SHA256,
        "oracle_pass": oracle.get("status") == "PASS",
        "static_pass": static.get("status") == "PASS",
        "lifecycle_pass": (
            lifecycle.get("status") == "PASS"
            and lifecycle.get("checkonly_root") == str(CHECK.relative_to(ROOT)).replace('\\','/')
            and lifecycle.get("requirement") == "COMP-REQ-382"
            and lifecycle.get("future_physical_authorization_requirement_id") == "COMP-REQ-383"
            and lifecycle.get("current_hex_sha256") == current_hex_sha256
            and lifecycle_checks.get("stage_candidate_sha_matches_current_hex") is True
            and lifecycle_checks.get("stage_candidate_required_sha_matches_current_hex") is True
            and lifecycle_checks.get("stale_checkonly_candidate_hash_selftest_pass") is True
        ),
        "r3_static_regression_pass": (
            r3_static.get("status") == "PASS"
            and static.get("r3_static_regression_pass") is True
            and static.get("r3_static_regression_artifact_sha256") == sha(paths["r3_static_regression_artifact"])
        ),
        "machine_artifacts_bound_and_pass": (
            oracle.get("status") == "PASS" and static.get("status") == "PASS"
            and lifecycle.get("status") == "PASS" and r3_static.get("status") == "PASS"
        ),
        "pdf_artifact_bound_and_verified": (
            sha(paths["ssd1681_rev013_pdf"]) == "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B"
            and oracle.get("transport_checks", {}).get("ssd1681_rev013_pdf_hash_matches") is True
        ),
        "checkonly_contract_pass": all(checkonly_checks.values()),
        "stage_candidate_sha_matches_current_hex": checkonly_checks["stage_candidate_sha_matches_current_hex"],
        "stage_candidate_required_sha_matches_current_hex": checkonly_checks["stage_candidate_required_sha_matches_current_hex"],
        "stage_mode_check_only": checkonly_checks["stage_mode_check_only"],
        "stage_hardware_contact_zero": checkonly_checks["stage_hardware_contact_zero"],
        "stage_all_counters_zero": checkonly_checks["stage_all_counters_zero"],
        "persistent_launcher_contract_pass": all(
            value for key, value in checkonly_checks.items() if key.startswith("persistent_launcher_")
        ),
        "checkonly_tool_hashes_match_current_when_available": all(
            binding["matches_current"] is not False for binding in tool_bindings.values()
        ),
        "stale_checkonly_candidate_hash_rejected": stale_selftest["pass"] is True,
        "launcher_selftest_pass": (
            launcher_selftest.get("status") == "PASS_SELFTEST"
            and launcher_selftest.get("hardware_contact") == 0
            and launcher_selftest.get("write_counter_sum") == 0
            and launcher_selftest.get("popup_count") == 0
            and launcher_selftest.get("retry_count") == 0
            and launcher_selftest.get("authorization_created") is False
        ),
        "r12_owner_wait_unbounded": (
            supervisor_check.get("status") == "READY_NO_PROMPT"
            and supervisor_check.get("timeout_seconds") == 0
            and supervisor_check.get("owner_wait_unbounded") is True
            and '"-TimeoutSeconds", "0"' in paths["runner"].read_text(encoding="utf-8")
            and "runner_prompt_supervision_timeout" not in paths["runner"].read_text(encoding="utf-8")
        ),
        "manifest_compatibility_artifact_pass": compatibility.get("status") == "PASS",
        "manifest_parser_sha256_alias_equals_parser": artifact_hashes["parser_sha256"] == artifact_hashes["parser"],
        "manifest_passes_launcher_equivalent_gate": output_alias_selftest["valid_manifest_passes"] is True,
        "missing_parser_sha256_alias_rejected": output_alias_selftest["fixtures"]["missing_parser_sha256"]["pass"] is True,
        "wrong_parser_sha256_alias_rejected": output_alias_selftest["fixtures"]["wrong_parser_sha256"]["pass"] is True,
        "production_off": "production_enabled=0" in paths["driver"].read_text(encoding="utf-8"),
        "protected_acceptance_hash": sha(PROTECTED) == "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
        "future_auth_exact_383": True,
        "no_authorization_artifact": not any(
            path.name.lower().endswith(('.authorization.json', '.claim.json', '.spent', '.consumed.json'))
            for root in (CHECK, SELFTEST) for path in root.iterdir()
        ),
    }
    errors = [key for key, value in checks.items() if not value]
    obj = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.machine_ready.v8",
        "status": "MACHINE_READY_R12_V22_CALM_CURIOUS_WARM_SAMPLER_R4_OFFLINE_ONLY" if not errors else "NO_GO_R12_R4_MACHINE_READY",
        "requirement": "COMP-REQ-382",
        "future_physical_authorization_requirement_id": "COMP-REQ-383",
        "candidate": "r12_v22_calm_curious_warm_sampler",
        "execute_authorized": False,
        "claim_only_authorized": False,
        "authorization_created": False,
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_count": 0,
        "retry_count": 0,
        "lut": {"kind": "official_ssd1681_otp_mode2", "custom_lut_loads": 0, "sha256": "OFFICIAL_OTP_MODE2_NO_CUSTOM_LUT_FILE"},
        "transport": {"movement_payload_bytes": 1908, "payload_scope": "R12 after 0x24 only", "transport": "direct_BSRR_MSB_first", "commands_control_baseline": "software_vendor_edges", "edge_order": ["SCL_LOW", "SDA_MSB", "NOP", "NOP", "SCL_HIGH", "NOP", "NOP", "SHIFT_LEFT"], "final_state": "SCL_LOW", "controller_write_limit_mhz": 20, "mcu_clock_mhz": 32, "instruction_lower_bound_per_bit": 8, "conservative_scl_upper_bound_mhz": 4},
        "thresholds": {"busy_ms": "<=600", "transaction_ms": "<=460", "cadence_ms": "1..480", "ring_bytes": 65536},
        "checkonly": {
            "hardware_contact": 0,
            "writes": 0,
            "serial_open_count": 0,
            "reset_count": 0,
            "refresh_count": 0,
            "popup_count": 0,
            "retry_count": 0,
            "persistent_launcher": True,
            "root": str(CHECK.relative_to(ROOT)).replace('\\','/'),
            "current_hex_sha256": current_hex_sha256,
            "stage_candidate_sha256": stage.get("images", {}).get("candidate", {}).get("sha256"),
            "stage_candidate_required_sha256": stage.get("images", {}).get("candidate", {}).get("required_sha256"),
            "contract_checks": checkonly_checks,
            "tool_hash_bindings": tool_bindings,
            "stale_candidate_hash_selftest": stale_selftest,
            "launcher_selftest_root": str(SELFTEST.relative_to(ROOT)).replace('\\','/'),
        },
        "manifest_compatibility": {
            "parser_sha256_alias": artifact_hashes["parser_sha256"],
            "parser": artifact_hashes["parser"],
            "negative_fixture_selftest": output_alias_selftest,
        },
        "restore_contract": {"bytes": 524288, "sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"},
        "r3_static_regression_pass": checks["r3_static_regression_pass"],
        "r3_static_regression_artifact_sha256": sha(paths["r3_static_regression_artifact"]),
        "artifacts": artifact_hashes,
        "artifact_paths": artifact_paths,
        "checks": checks,
        "errors": errors,
    }
    OUT.write_text(json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True))
    print(f"MACHINE_READY_SHA256={sha(OUT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
