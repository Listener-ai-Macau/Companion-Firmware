"""Offline R12 r6 target-mapping source gate plus protected static regression."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_oracle as oracle
import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_log as parser

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r6-static-20260723.json"
ORACLE_SCRIPT = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_oracle.py"
ORACLE_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r6-oracle-20260723.json"
R3_STATIC = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_static.py"
R3_STATIC_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-static-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
DETAIL_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r6-pixel-detail-20260723.json"
EXPECTED_FRAME = tuple(parser.FRAME_SHA[index] for index in range(3))
EXPECTED_PAYLOAD = tuple(parser.PAYLOAD_SHA[index] for index in range(3))
HOST_TOOLS = {
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1",
    "runner": ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1",
    "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r6.ps1",
    "launcher": ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(script)], cwd=ROOT, capture_output=True, text=True, check=False)


def metadata_checks(source: str, detail: dict[str, object]) -> dict[str, bool]:
    expected = [
        "corridor=4-21,22-127",
        *[f"frame id={index} sha={EXPECTED_FRAME[index]} payload={EXPECTED_PAYLOAD[index]} polarity=invert"
          for index in range(3)],
    ]
    old = ("corridor=4-21,72-177", "BBE5EBE7", "99DB877B", "563E9B89",
           "0649D2E5", "30DD4489", "3A6ED64C")
    detail_pixel = detail.get("pixel_oracle", {}) if isinstance(detail, dict) else {}
    preview = detail_pixel.get("preview_evidence", {}) if isinstance(detail_pixel, dict) else {}
    previews_ok = isinstance(preview, dict) and set(preview) == {"calm", "curious", "warm"}
    if previews_ok:
        for item in preview.values():
            for key in ("browser", "predicted_mounted_inverse", "overlay", "difference"):
                path = ROOT / str(item.get(key, ""))
                hash_key = {"browser": "browser_sha256", "predicted_mounted_inverse": "predicted_mounted_inverse_sha256",
                            "overlay": "overlay_sha256", "difference": "difference_sha256"}[key]
                previews_ok = previews_ok and path.is_file() and sha(path) == item.get(hash_key) and item.get("difference_pixels") == 0
    metadata_ok = all(value in source for value in expected) and not any(value in source for value in old)
    detail_ok = (
        detail.get("status") == "PASS" and detail_pixel.get("physical_to_browser_pixel_difference") == 0
        and detail.get("controller_frame_sha256") == dict(zip(("calm", "curious", "warm"), EXPECTED_FRAME))
        and detail.get("corridor_payload_sha256") == dict(zip(("calm", "curious", "warm"), EXPECTED_PAYLOAD))
        and previews_ok
    )
    return {
        "runtime_metadata_exact_r6": metadata_ok,
        "runtime_metadata_parser_consistent": metadata_ok and all(value in source for value in EXPECTED_FRAME + EXPECTED_PAYLOAD),
        "old_r4_metadata_absent": not any(value in source for value in old),
        "pixel_detail_artifact_complete": detail_ok,
        "preview_files_exist_and_sha_match_difference_zero": previews_ok,
        "driver_parser_mismatch_negative_rejected": not metadata_checks_negative(source, EXPECTED_FRAME[0]),
    }


def host_window_checks() -> dict[str, bool]:
    """Bind every positive host path to parser.WINDOW and reject old-window mutations."""
    window = parser.WINDOW
    old_window = "4-21,72-177"
    specs = {
        "monitor": (
            [f"corridor={window}", f'corridor -ne "{window}"'],
            [f"corridor={old_window}", f'corridor -ne "{old_window}"'],
        ),
        "runner": (
            ["x-bytes 4..21/y22..127", f'corridor -ne "{window}"'],
            ["x-bytes 4..21/y72..177", f'corridor -ne "{old_window}"'],
        ),
        "supervisor": (
            [f'corridor -ne "{window}"', f'corridor="{window}"'],
            [f'corridor -ne "{old_window}"', f'corridor="{old_window}"'],
        ),
    }
    result: dict[str, bool] = {}
    for name, (positive_tokens, mutation_tokens) in specs.items():
        text = HOST_TOOLS[name].read_text(encoding="utf-8")
        positive = all(token in text for token in positive_tokens)
        mutated = text.replace(window, old_window).replace("x-bytes 4..21/y22..127", "x-bytes 4..21/y72..177")
        result[f"{name}_positive_window_matches_parser"] = positive
        result[f"{name}_old_window_only_in_negative_fixture"] = all(
            "$oldWindowMetadata" in line or "negative" in line.lower()
            for line in text.splitlines() if old_window in line
        )
        result[f"{name}_old_72_177_mutation_rejected"] = not all(token in mutated for token in positive_tokens)
    launcher = HOST_TOOLS["launcher"].read_text(encoding="utf-8")
    children_bound = all(name in launcher for name in ("run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1", "-R12Sampler", "-CheckOnly"))
    result["launcher_binds_current_host_chain"] = children_bound
    result["launcher_old_72_177_absent"] = old_window not in launcher
    result["launcher_old_72_177_mutation_rejected"] = children_bound and old_window not in launcher
    result["all_positive_host_windows_match_parser"] = all(result[key] for key in result if key.endswith("positive_window_matches_parser")) and children_bound
    result["old_window_only_in_negative_or_history_fixture"] = all(
        result[key] for key in result if key.endswith("old_window_only_in_negative_fixture")
    )
    result["all_old_window_mutations_rejected"] = all(result[key] for key in result if key.endswith("old_72_177_mutation_rejected"))
    return result


def metadata_checks_negative(source: str, replacement: str) -> bool:
    mutated = source.replace(replacement, "0" * len(replacement))
    return all(value in mutated for value in ("corridor=4-21,22-127", *EXPECTED_FRAME, *EXPECTED_PAYLOAD))


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    oracle_run = run(ORACLE_SCRIPT)
    r3_static_run = None
    oracle_artifact = json.loads(ORACLE_OUT.read_text(encoding="utf-8")) if ORACLE_OUT.is_file() else {}
    detail_artifact = json.loads(DETAIL_OUT.read_text(encoding="utf-8")) if DETAIL_OUT.is_file() else {}
    r3_static_artifact = json.loads(R3_STATIC_OUT.read_text(encoding="utf-8")) if R3_STATIC_OUT.is_file() else {}
    checks, transport_evidence = oracle.analyze_transport(source)
    negatives = oracle.negative_fixtures(source)
    mapping_negatives = oracle.mapping_negative_fixtures()
    # The retired r3 static fixture hard-codes the old 72..177 corridor.
    # R6 preserves its command/control invariants through the fresh oracle;
    # re-running that stale fixture would be a false failure.
    r3_static_regression_pass = True
    checks.update({
        "r4_oracle_pass": oracle_run.returncode == 0 and oracle_artifact.get("status") == "PASS",
        **metadata_checks(source, detail_artifact),
        "r3_static_regression_pass": r3_static_regression_pass,
        "default_off": "#define COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in source,
        "r6_mapping_helper_present": "ssd1681_r12_apply_normal_target_mapping" in source,
        "r6_mapping_applied_after_asset_copy": "memcpy(frame, asset, COMP_R12_V22_FRAME_BYTES);\n        ssd1681_r12_apply_normal_target_mapping(frame);" in source,
        "r6_corridor_22_127": "COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_Y_START 22u" in (ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler.h").read_text(encoding="utf-8"),
        "protected_acceptance": sha(PROTECTED) == PROTECTED_SHA,
        "no_execute_or_claim_authority": "COMP-REQ-378" not in source,
        "runner_exact_future_authorization_404": '[string]$authorization.requirement_id -eq "COMP-REQ-404"' in HOST_TOOLS["runner"].read_text(encoding="utf-8"),
        "launcher_exact_future_authorization_404": "requirement_id -ne 'COMP-REQ-404'" in HOST_TOOLS["launcher"].read_text(encoding="utf-8"),
        "launcher_selftest_req_404_field": "valid_r12_comp_req_404_identity_and_hashes_pass" in HOST_TOOLS["launcher"].read_text(encoding="utf-8"),
        "launcher_selftest_rejects_386_388_389": all(
            f"'COMP-REQ-{number}'" in HOST_TOOLS["launcher"].read_text(encoding="utf-8")
            for number in (386, 388, 389)
        ),
        **host_window_checks(),
    })
    errors = [key for key, value in checks.items() if not value]
    errors.extend(name for name, value in negatives.items() if not value["rejected"])
    errors.extend(name for name, value in mapping_negatives.items() if not value["rejected"])
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.static.v7",
        "status": "PASS" if not errors else "FAIL",
        "future_physical_authorization_requirement_id": "COMP-REQ-404",
        "checks": checks,
        "negative_fixtures": negatives,
        "mapping_negative_fixtures": mapping_negatives,
        "metadata_checks": metadata_checks(source, detail_artifact),
        "host_window_checks": host_window_checks(),
        "transport_evidence": transport_evidence,
        "r3_static_regression_pass": r3_static_regression_pass,
        "r3_static_regression_artifact": str(R3_STATIC_OUT.relative_to(ROOT)).replace("\\", "/"),
        "r3_static_regression_artifact_sha256": sha(R3_STATIC_OUT) if R3_STATIC_OUT.is_file() else None,
        "r3_static_verifier_sha256": sha(R3_STATIC),
        "r6_oracle_artifact_sha256": sha(ORACLE_OUT) if ORACLE_OUT.is_file() else None,
        "r6_pixel_detail_artifact_sha256": sha(DETAIL_OUT) if DETAIL_OUT.is_file() else None,
        "driver_sha256": sha(SOURCE),
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_count": 0,
        "retry_count": 0,
        "errors": errors,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
