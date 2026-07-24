import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
HOST = Path(r"C:\Users\Billy\Desktop\Denzic\.cache\comp-req-481-host\companion_platform_adapters_test.exe")
OUT = ROOT / "docs" / "validation" / "companion-platform-adapters-machine-ready.json"
LOG = ROOT / "docs" / "validation" / "companion-platform-adapters-host-runner.stdout.txt"
WB = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "build"
BLE = ROOT / "cubeide" / "Companion_BLE_Audio_Fixture" / "build"
NM = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740\tools\bin\arm-none-eabi-nm.exe")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def cmd(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main():
    source = [
        ROOT / "app/companion_pendant/platform/companion_platform_adapters.c",
        ROOT / "app/companion_pendant/platform/companion_platform_adapters.h",
        ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
        ROOT / "tools/fixtures/companion_platform_adapters_test.c",
    ]
    link = cmd("git", "ls-tree", "HEAD", "third_party/denzic-platform").stdout.strip()
    head = cmd("git", "rev-parse", "HEAD").stdout.strip()
    status = [
        line for line in cmd("git", "status", "--porcelain").stdout.splitlines()
        if not any(line[3:].replace("\\", "/") == x for x in (
            "docs/validation/companion-platform-adapters-machine-ready.json",
            "docs/validation/companion-platform-adapters-host-runner.stdout.txt",
            "docs/validation/companion-platform-adapters-wb55-build.log",
            "docs/validation/companion-platform-adapters-ble-build.log"))
    ]
    app_obj = WB / "app_ble.o"
    adapter_obj = WB / "companion_platform_adapters.o"
    undefined = cmd(str(NM), "-u", str(app_obj)).stdout if NM.exists() and app_obj.exists() else ""
    defined = cmd(str(NM), "-g", str(adapter_obj)).stdout if NM.exists() and adapter_obj.exists() else ""
    symbols = [
        "companion_platform_device_control_capabilities_event",
        "companion_platform_device_control_settings_event",
        "companion_platform_device_control_invoke_event",
        "companion_platform_diag_encode_chunk",
        "companion_platform_ota_readiness_event",
    ]
    symbol_gate = all(s in undefined and s in defined for s in symbols)
    gen = {}
    for name in ("generate_device_control_v1.py", "generate_observability_v1.py", "generate_ota_manifest_v2.py"):
        result = cmd("python", str(ROOT / "third_party/denzic-platform/tools" / name), "--check")
        gen[name] = result.returncode == 0
    run = subprocess.run([str(HOST)], cwd=HOST.parent, text=True, capture_output=True) if HOST.exists() else None
    stdout = "" if run is None else run.stdout
    LOG.write_text(stdout, encoding="utf-8")
    outputs = {}
    for directory, names in ((WB, ("Companion_Nucleo_WB55RG_Bringup.elf", "Companion_Nucleo_WB55RG_Bringup.hex", "Companion_Nucleo_WB55RG_Bringup.map")),
                             (BLE, ("Companion_BLE_Audio_Fixture.elf", "Companion_BLE_Audio_Fixture.hex", "Companion_BLE_Audio_Fixture.map"))):
        for name in names:
            path = directory / name
            outputs[str(path.relative_to(ROOT)).replace("\\", "/")] = digest(path) if path.exists() else None
    checks = {
        "platform_pin": link.endswith(PIN + "\tthird_party/denzic-platform"),
        "worktree_clean_except_generated_evidence": not status,
        "real_app_ble_call_edges": symbol_gate,
        "generator_drift_zero": all(gen.values()),
        "host_runner_compiled_and_executed": run is not None and run.returncode == 0,
        "ordered_trace_observed": all(x in stdout for x in ("diag positive", "device terminal_count", "ota positive")),
        "wb55_elf_hex_map": all(outputs[k] for k in outputs if "Nucleo" in k),
        "ble_elf_hex_map": all(outputs[k] for k in outputs if "Audio_Fixture" in k),
    }
    artifact = {
        "schema": "companion.platform_adapters.machine_ready.v2",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "source_commit": head,
        "platform_pin": PIN,
        "gitlink": link,
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in source},
        "call_edge_symbols": symbols,
        "nm_app_ble_undefined_sha256": hashlib.sha256(undefined.encode()).hexdigest().upper(),
        "nm_adapter_defined_sha256": hashlib.sha256(defined.encode()).hexdigest().upper(),
        "host_runner": {"path": str(HOST), "sha256": digest(HOST) if HOST.exists() else None, "exit": None if run is None else run.returncode, "stdout_sha256": digest(LOG)},
        "build_outputs_sha256": outputs,
        "generator_checks": gen,
        "checks": checks,
        "side_effects": {"hardware": 0, "ble_write": 0, "ota_transfer": 0, "ota_apply": 0, "programmer": 0, "serial": 0, "popup": 0, "push": 0},
        "physical_gates": {"execute": "OPEN", "hardware": "OPEN", "real_ble": "OPEN", "ota_transfer_apply": "OPEN"},
    }
    OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    return 0 if artifact["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
