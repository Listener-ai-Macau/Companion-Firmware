import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    app_path = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    app = app_path.read_text(encoding="utf-8")
    pin = subprocess.run(["git", "ls-tree", "HEAD", "third_party/denzic-platform"], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    run = subprocess.run(["pwsh", "-NoProfile", "-File", "tools/run_comp_req_558_diag_host.ps1"], cwd=ROOT, text=True, capture_output=True)
    result_path = ROOT / ".cache/validation/comp-req-558-diag-host/result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    checks = {
        "platform_pin": pin.endswith(PIN + "\tthird_party/denzic-platform"),
        "real_product_pull": "companion_diag_log_pull" in app,
        "gatt_diag_entry": "COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL" in app,
        "runner_pass": run.returncode == 0 and result.get("status") == "PASS",
        "negative_modes": all(x in result.get("stdout", "") for x in ("mode=1", "mode=2", "mode=3", "mode=4", "mode=5")),
        "stop_once": "stop=1" in result.get("stdout", ""),
    }
    artifact = {
        "schema": "companion.comp_req_558.diagnostics_gate.v1",
        "status": "PASS" if all(checks.values()) else "NO_GO",
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip(),
        "platform_pin": PIN,
        "checks": checks,
        "runner": result,
        "source_sha256": {"app_ble": sha(app_path), "platform_adapters": sha(ROOT / "app/companion_pendant/platform/companion_platform_adapters.c")},
        "physical_gate": "CLOSED_UNPROVEN",
        "side_effects": {"hardware": 0, "ble_write": 0, "ota_apply": 0, "popup": 0, "push": 0},
    }
    out = ROOT / ".cache/validation/comp-req-558-diagnostics.json"
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps(artifact, indent=2))
    return 0 if artifact["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
