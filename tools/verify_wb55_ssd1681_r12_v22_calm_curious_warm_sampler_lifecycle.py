"""Exercise the R12 host lifecycle without authorization or hardware contact."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1"
SUPERVISOR = ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-lifecycle-20260722.json"


def run(*args: str, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def zero_contact(value: dict[str, object]) -> bool:
    return all(
        value.get(key) == 0
        for key in (
            "hardware_contact",
            "write_counter_sum",
            "programmer_calls",
            "serial_open_count",
            "reset_count",
            "refresh_count",
            "popup_count",
            "retry_count",
        )
    )


def main() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="r12-v22-lifecycle-") as raw_temp:
        temp = Path(raw_temp)
        monitor_root = temp / "monitor-selftest"
        supervisor_root = temp / "supervisor-selftest"
        launcher_self_root = temp / "launcher-selftest"
        check_root = temp / "launcher-checkonly"
        unauthorized_root = temp / "unauthorized-execute"

        monitor = run(str(MONITOR), "-SelfTest", "-OutDir", str(monitor_root))
        supervisor = run(str(SUPERVISOR), "-SelfTest", "-OutRoot", str(supervisor_root))
        launcher_self = run(str(LAUNCHER), "-SelfTest", "-OutRoot", str(launcher_self_root))
        unauthorized = run(str(LAUNCHER), "-Execute", "-OutRoot", str(unauthorized_root))
        checkonly = run(str(LAUNCHER), "-CheckOnly", "-OutRoot", str(check_root), timeout=300)

        monitor_json = load(monitor_root / "monitor-result.json") if (monitor_root / "monitor-result.json").is_file() else {}
        supervisor_json = load(supervisor_root / "prompt-supervisor-check.json") if (supervisor_root / "prompt-supervisor-check.json").is_file() else {}
        launcher_self_json = load(launcher_self_root / "launcher-selftest.json") if (launcher_self_root / "launcher-selftest.json").is_file() else {}
        launch_json = load(check_root / "persistent-launch.json") if (check_root / "persistent-launch.json").is_file() else {}
        stage_json = load(check_root / "stage-run.json") if (check_root / "stage-run.json").is_file() else {}

        checks.update(
            {
                "monitor_selftest_pass": monitor.returncode == 0 and monitor_json.get("status") == "PASS_SELFTEST" and zero_contact(monitor_json),
                "supervisor_selftest_pass": supervisor.returncode == 0 and supervisor_json.get("status") == "PASS_SELFTEST" and zero_contact(supervisor_json),
                "launcher_selftest_pass": launcher_self.returncode == 0 and launcher_self_json.get("status") == "PASS_SELFTEST" and zero_contact(launcher_self_json),
                "unauthorized_execute_rejected_before_root_or_contact": unauthorized.returncode != 0 and not unauthorized_root.exists(),
                "wrong_candidate_rejected": bool(launcher_self_json.get("checks", {}).get("wrong_candidate_rejected")),
                "wrong_hash_rejected": bool(launcher_self_json.get("checks", {}).get("wrong_hash_rejected")),
                "wrong_root_rejected": bool(launcher_self_json.get("checks", {}).get("wrong_root_rejected")),
                "comp_req_370_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_370_rejected")),
                "comp_req_371_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_371_rejected")),
                "comp_req_372_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_372_rejected")),
                "comp_req_373_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_373_rejected")),
                "comp_req_374_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_374_rejected")),
                "comp_req_375_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_375_rejected")),
                "legacy_r11_requirement_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_323_rejected")),
                "wildcard_requirement_rejected": bool(launcher_self_json.get("checks", {}).get("requirement_COMP_REQ_999_rejected")),
                "checkonly_complete_dry_path": checkonly.returncode == 0 and launch_json.get("status") == "READY_NO_HARDWARE_CONTACT",
                "checkonly_zero_contact": zero_contact(launch_json) and stage_json.get("hardware_contact") == 0,
                "checkonly_no_popup_or_retry": launch_json.get("popup_count") == 0 and launch_json.get("retry_count") == 0,
                "no_authorization_claim_spent_or_receipt_created": not any(
                    path.is_file() and any(token in path.name.lower() for token in ("authorization", "claim", "spent", "receipt", "consumed"))
                    for path in temp.rglob("*")
                ),
            }
        )

    errors = [name for name, passed in checks.items() if not passed]
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.lifecycle.v1",
        "status": "PASS" if not errors else "FAIL",
        "candidate": "r12_v22_calm_curious_warm_sampler",
        "mode": "selftest_and_checkonly_only",
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "programmer_calls": 0,
        "serial_open_count": 0,
        "reset_count": 0,
        "refresh_count": 0,
        "popup_count": 0,
        "retry_count": 0,
        "authorization_created": False,
        "claim_created": False,
        "spent_created": False,
        "receipt_created": False,
        "automatic_retries": 0,
        "checks": checks,
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
