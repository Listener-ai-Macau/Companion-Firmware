"""Offline R12 r4 source gate plus complete R3 static regression."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4 as oracle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-static-20260722.json"
ORACLE_SCRIPT = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.py"
ORACLE_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-oracle-20260722.json"
R3_STATIC = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_static.py"
R3_STATIC_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-static-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(script)], cwd=ROOT, capture_output=True, text=True, check=False)


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    oracle_run = run(ORACLE_SCRIPT)
    r3_static_run = run(R3_STATIC)
    oracle_artifact = json.loads(ORACLE_OUT.read_text(encoding="utf-8")) if ORACLE_OUT.is_file() else {}
    r3_static_artifact = json.loads(R3_STATIC_OUT.read_text(encoding="utf-8")) if R3_STATIC_OUT.is_file() else {}
    checks, transport_evidence = oracle.analyze_transport(source)
    negatives = oracle.negative_fixtures(source)
    r3_static_regression_pass = (
        r3_static_run.returncode == 0
        and r3_static_artifact.get("status") == "PASS"
        and not r3_static_artifact.get("errors")
        and all(r3_static_artifact.get("checks", {}).get(key) is True for key in (
            "r12_window_setup_exactly_once_after_baseline_before_qualification",
            "r12_window_setup_exact_44_45_once",
            "r12_window_setup_no_ram_write_or_refresh",
            "r12_movement_counters_exactly_once",
            "r12_movement_has_no_window_or_border_commands",
            "r12_movement_command_order_unchanged",
            "r3_negative_fixtures_rejected",
        ))
    )
    checks.update({
        "r4_oracle_pass": oracle_run.returncode == 0 and oracle_artifact.get("status") == "PASS",
        "r3_static_regression_pass": r3_static_regression_pass,
        "default_off": "#define COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in source,
        "protected_acceptance": sha(PROTECTED) == PROTECTED_SHA,
        "no_execute_or_claim_authority": "COMP-REQ-378" not in source,
    })
    errors = [key for key, value in checks.items() if not value]
    errors.extend(name for name, value in negatives.items() if not value["rejected"])
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.static.v6",
        "status": "PASS" if not errors else "FAIL",
        "future_physical_authorization_requirement_id": "COMP-REQ-378",
        "checks": checks,
        "negative_fixtures": negatives,
        "transport_evidence": transport_evidence,
        "r3_static_regression_pass": r3_static_regression_pass,
        "r3_static_regression_artifact": str(R3_STATIC_OUT.relative_to(ROOT)).replace("\\", "/"),
        "r3_static_regression_artifact_sha256": sha(R3_STATIC_OUT) if R3_STATIC_OUT.is_file() else None,
        "r3_static_verifier_sha256": sha(R3_STATIC),
        "r4_oracle_artifact_sha256": sha(ORACLE_OUT) if ORACLE_OUT.is_file() else None,
        "driver_sha256": sha(SOURCE),
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_count": 0,
        "retry_count": 0,
        "errors": errors,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    if r3_static_run.returncode != 0:
        print(r3_static_run.stdout[-2000:])
        print(r3_static_run.stderr[-2000:])
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
