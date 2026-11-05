#!/usr/bin/env python3
"""Successor audit for the active R10 lower-driver work package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-current-goal-audit-r10-20260722.json"
WORK_PACKAGE = ROOT / "docs/validation/companion-ssd1681-r10-r1-execute-work-package-20260722.md"
RUNTIME_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-r10-r1-runtime-disposition-20260722.json"
R2_WORK_PACKAGE = ROOT / "docs/validation/companion-ssd1681-r10-r2-luna-work-package-20260722.md"
R2_EXECUTE_WORK_PACKAGE = ROOT / "docs/validation/companion-ssd1681-r10-r2-execute-work-package-20260722.md"
AUTH = ROOT / ".cache/validation/wb55-r10-ball-r2-authorization.json"
EXPECTED_ROOT = str(ROOT / ".cache/validation/wb55-r10-ball-execute-20260722-r2")
FILES = [
    "app/companion_pendant/epaper/r10_ball_diagnostic.h",
    "tools/verify_wb55_ssd1681_r10_ball_pixel_oracle.py",
    "tools/verify_wb55_ssd1681_r10_ball_static.py",
    "tools/verify_wb55_ssd1681_r10_ball_log.py",
    "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
    "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "docs/validation/companion-ssd1681-r10-r1-execute-work-package-20260722.md",
    "docs/validation/companion-ssd1681-r10-r1-runtime-disposition-20260722.json",
    "docs/validation/companion-ssd1681-r10-r2-luna-work-package-20260722.md",
    "docs/validation/companion-ssd1681-r10-r2-execute-work-package-20260722.md",
]

EXPECTED_AUTH = {
    "status": "AUTHORIZED_R10_BALL_ONCE",
    "r2_execution_status": "AUTHORIZED_R10_R2_ONCE_PENDING_EXECUTE",
    "consumed": False,
    "requirement_id": "COMP-REQ-323",
    "authorization_requirement_id": "COMP-REQ-328",
    "output_root": EXPECTED_ROOT,
}
EXPECTED_HASHES = {
    "lut_sha256": "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD",
    "candidate_hex_sha256": "CB186A2ABB44962316C47315061AF64772273B0A70BBFBA77B6166DD551778A6",
    "elf_sha256": "67066AF4199ED24556B285449839C35C649B05A8B0160031335E0AF9C0C12110",
    "parser_sha256": "54F8ECC31FBC778AB2AFA7FD65F012FB983748290E4A1D0570C1C879FD6A154B",
    "monitor_sha256": "D41458E681BF12FD32A6B7376021CC9A1FB14B610171FC329683B13542A3252A",
    "launcher_sha256": "7239FB33F0BC35887CD46CF85B8B0BBA1788987F73D0A239C20DDBCD14350659",
    "runner_sha256": "0BB9395D36F4F8983E35C5B82C3A1C379863670587CB004F427383AFBA188382",
    "supervisor_sha256": "F712AD30EE4A52D26EEB8168CBB50F12D52C4AEF7DB3A8B0FF7A37BFF65757F1",
    "machine_ready_sha256": "E29DCC1E591B9C1E36088148EF7BC5C1EA96FFBAF20DD86BCB7E4875F556BE11",
    "restore_application_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def authorization_state(work_text: str) -> tuple[bool, dict]:
    report = {"path": str(AUTH.relative_to(ROOT)).replace("\\", "/"), "present": AUTH.is_file()}
    if not AUTH.is_file():
        report["source_absent_after_consumption"] = True
        report["r1_runtime_disposition_present"] = RUNTIME_DISPOSITION.is_file()
        report["r2_offline_work_package_present"] = R2_WORK_PACKAGE.is_file()
        report["r2_execute_work_package_present"] = R2_EXECUTE_WORK_PACKAGE.is_file()
        text = R2_EXECUTE_WORK_PACKAGE.read_text(encoding="utf-8") if R2_EXECUTE_WORK_PACKAGE.is_file() else ""
        report["r2_pending_marker_in_work_package"] = "AUTHORIZED_R10_R2_ONCE_PENDING_EXECUTE" in text
        return bool(report["r1_runtime_disposition_present"] and report["r2_offline_work_package_present"] and report["r2_execute_work_package_present"] and report["r2_pending_marker_in_work_package"]), report
    try:
        value = json.loads(AUTH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        report["error"] = str(error)
        return False, report
    mismatches = {key: {"expected": expected, "actual": value.get(key)}
                  for key, expected in EXPECTED_AUTH.items() if value.get(key) != expected}
    mismatches.update({key: {"expected": expected, "actual": value.get(key)}
                      for key, expected in EXPECTED_HASHES.items() if value.get(key) != expected})
    report.update({"sha256": sha(AUTH), "r2_execution_status": value.get("r2_execution_status"), "mismatches": mismatches})
    return not mismatches, report


def build() -> dict:
    registry = REGISTRY.read_text(encoding="utf-8")
    work_text = WORK_PACKAGE.read_text(encoding="utf-8") if WORK_PACKAGE.is_file() else ""
    ids = {f"COMP-REQ-{n}": f"| COMP-REQ-{n} |" in registry for n in range(318, 329)}
    missing = [path for path in FILES if not (ROOT / path).is_file()]
    old = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
    auth_ok, auth_report = authorization_state(work_text)
    checks = {
        **ids,
        "historical_audit_preserved": old.is_file(),
        "r10_files_present": not missing,
        "r1_work_package_present": WORK_PACKAGE.is_file(),
        "r2_execute_authorization_boundary_recorded": auth_ok,
        "machine_only": "MACHINE_READY" in registry and "no Execute" in registry and "does not Execute" in work_text,
    }
    errors = [name for name, ok in checks.items() if not ok]
    return {
        "schema_id": "companion.current_goal_audit.r10_successor.v2",
        "status": "PASS_R10_ACTIVE_MACHINE_ONLY_AUDIT" if not errors else "R10_AUDIT_INVALID",
        "codex_goal_status": "active_or_owner_goal_managed",
        "authority": "COMP-REQ-323/324/325/327/328",
        "active_boundary": "R10 lower-driver R2 hash-bound one-shot authorization pending only; no execution, production promotion or hardware contact",
        "checks": checks,
        "errors": errors,
        "missing": missing,
        "r1_authorization": auth_report,
        "owned_file_hashes": {path: sha(ROOT / path) for path in FILES if (ROOT / path).is_file()},
        "historical_audit": str(old.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--artifact", type=Path, default=OUT)
    args = ap.parse_args()
    report = build()
    rendered = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if args.write:
        args.artifact.write_bytes(rendered)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered:
        print("FAIL: stale R10 current-goal successor")
        return 1
    if report["errors"]:
        print(f"FAIL: R10 current-goal successor: {report['errors']}")
        return 1
    print(f"PASS: R10 current-goal successor checks={len(report['checks'])} artifact_sha256={sha(args.artifact)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
