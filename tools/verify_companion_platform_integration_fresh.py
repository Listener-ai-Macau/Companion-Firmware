import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
VCVARS = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def git_blob_sha256(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                            capture_output=True)
    return hashlib.sha256(result.stdout).hexdigest().upper() if result.returncode == 0 else ""


def canonical_worktree_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()


def run(args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--verifier-commit", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--manifest-commit", required=True)
    ap.add_argument("--manifest-path", default="docs/validation/companion-platform-adapters-500-manifest.json")
    ns = ap.parse_args()
    run_dir = Path(ns.run_dir).resolve()
    if run_dir.is_relative_to(ROOT):
        raise SystemExit("NO_GO: run artifacts must be outside the repository")
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ns.manifest_path
    manifest_result = subprocess.run(["git", "show", f"{ns.manifest_commit}:{manifest_path}"],
                                     cwd=ROOT, capture_output=True)
    if manifest_result.returncode != 0:
        raise SystemExit("NO_GO: immutable COMP-REQ-500 manifest is not committed")
    manifest = json.loads(manifest_result.stdout.decode("utf-8"))
    source_paths = [
        "app/companion_pendant/platform/companion_platform_adapters.c",
        "app/companion_pendant/platform/companion_platform_adapters.h",
        "app/companion_pendant/platform/companion_product_entry_glue.c",
        "app/companion_pendant/platform/companion_product_entry_glue.h",
        "app/companion_pendant/platform/companion_product_identity.c",
        "app/companion_pendant/platform/companion_product_identity.h",
        "app/companion_pendant/platform/companion_product_transport.c",
        "app/companion_pendant/platform/companion_product_transport.h",
        "app/companion_pendant/gatt/companion_gatt_stm32wb.c",
        "app/companion_pendant/gatt/companion_gatt_stm32wb.h",
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
        "cubeide/Companion_BLE_Ota_Loader/Src/companion_ota_v1.c",
        "cubeide/Companion_BLE_Ota_Loader/Src/companion_ota_v1.h",
        "tools/fixtures/companion_platform_adapters_test.c",
        "tools/fixtures/companion_gatt_host_stubs.c",
    ]
    status_before = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=ROOT,
                                   capture_output=True).stdout
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    verifier_path = "tools/verify_companion_platform_integration_fresh.py"
    verifier_blob = git_blob_sha256(ns.verifier_commit, verifier_path)
    verifier_worktree_blob = canonical_worktree_sha(ROOT / verifier_path)
    gitlink = run(["git", "ls-tree", ns.source_commit, "third_party/denzic-platform"]).stdout.strip()
    drift = run(["git", "diff", "--quiet", ns.source_commit, "--", *source_paths]).returncode
    isolated = ROOT / ".cache" / "comp-req-531-fresh-host"
    shutil.rmtree(isolated, ignore_errors=True)
    isolated.mkdir(parents=True, exist_ok=True)
    try:
        exe = isolated / "companion_platform_adapters_test.exe"
        sources = [ROOT / p for p in [
            "tools/fixtures/companion_platform_adapters_test.c",
            "tools/fixtures/companion_gatt_host_stubs.c",
            "app/companion_pendant/platform/companion_platform_adapters.c",
            "app/companion_pendant/platform/companion_product_entry_glue.c",
            "app/companion_pendant/platform/companion_product_identity.c",
            "app/companion_pendant/platform/companion_product_transport.c",
            "app/companion_pendant/gatt/companion_gatt_stm32wb.c",
            "third_party/denzic-platform/device_control/embedded/c/src/denzic_device_control_v1.c",
            "third_party/denzic-platform/observability/embedded/c/src/denzic_diag_log_gatt_v1.c",
            "third_party/denzic-platform/ota/embedded/c/src/denzic_ota_orchestration_v1.c"]]
        command = (
            f'call "{VCVARS}" >nul && cd /d "{isolated}" && cl /nologo /O2 /Brepro /W4 /WX /wd4100 /wd4311 /wd4312 /DSTM32WB55xx '
            f'/D_CRT_SECURE_NO_WARNINGS /FI"{ROOT / "tools/fixtures/companion_gatt_msvc_compat.h"}" /I"{ROOT / "tools/fixtures"}" /I"{ROOT / "app/companion_pendant/platform"}" '
            f'/I"{ROOT / "app/companion_pendant/gatt"}" '
            f'/I"{ROOT / "third_party/denzic-platform/device_control/embedded/c/include"}" '
            f'/I"{ROOT / "third_party/denzic-platform/observability/embedded/c/include"}" '
            f'/I"{ROOT / "third_party/denzic-platform/ota/embedded/c/include"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/auto"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/template"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Drivers/CMSIS/Include"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Drivers/CMSIS/Core/Include"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Drivers/CMSIS/Device/ST/STM32WBxx/Include"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Drivers/STM32WBxx_HAL_Driver/Inc"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/svc/Src"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/svc/Inc"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32_WPAN/App"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Inc"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl"}" '
            f'/I"{ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/utilities"}" '
            f'/FI"{ROOT / "third_party/STM32CubeWB/Drivers/STM32WBxx_HAL_Driver/Inc/stm32wbxx_hal_rtc.h"}" '
            + " ".join(f'"{p}"' for p in sources) + f' /Fe:{exe.name}'
        )
        compile = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                 shell=True)
        if compile.returncode != 0:
            print(compile.stderr, flush=True)
        host = subprocess.run([str(exe)], cwd=ROOT, text=True, capture_output=True) \
            if compile.returncode == 0 and exe.exists() else None
        stdout = "" if host is None else host.stdout
        (run_dir / "host.stdout.txt").write_text(stdout, encoding="utf-8")
        validation = run_dir
        (validation / "comp-req-531-host.stdout.txt").write_text(stdout, encoding="utf-8")
        (validation / "comp-req-531-host.compile.stdout.txt").write_text(compile.stdout, encoding="utf-8")
        (validation / "comp-req-531-host.compile.stderr.txt").write_text(compile.stderr, encoding="utf-8")
        wrapper_commands = [
            ["pwsh", "-NoProfile", "-File", "tools/build_nucleo_bringup.ps1", "-EpaperSsd1681R7VisualRuntimeDiagnostic", "-Force", "-Optimization", "O2"],
            ["pwsh", "-NoProfile", "-File", "tools/build_companion_ble_audio_fixture.ps1", "-Force"],
        ]
        wrappers = []
        for args in wrapper_commands:
            result = run(args)
            label = "wb55" if len(wrappers) == 0 else "ble"
            (validation / f"comp-req-531-{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
            (validation / f"comp-req-531-{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")
            wrappers.append({"command": args, "exit": result.returncode,
                             "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest().upper(),
                             "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest().upper()})
        outputs = {}
        for directory, names in [
            (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime",
             ["Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.elf", "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.hex", "Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.map"]),
            (ROOT / "cubeide/Companion_BLE_Audio_Fixture/build",
             ["Companion_BLE_Audio_Fixture.elf", "Companion_BLE_Audio_Fixture.hex", "Companion_BLE_Audio_Fixture.map"]),
        ]:
            for name in names:
                p = directory / name
                outputs[str(p.relative_to(ROOT)).replace("\\", "/")] = sha(p) if p.exists() else None
        generators = {}
        for name in ["generate_device_control_v1.py", "generate_observability_v1.py", "generate_ota_manifest_v2.py"]:
            r = run(["python", f"third_party/denzic-platform/tools/{name}", "--check"])
            generators[name] = r.returncode == 0
        object_paths = {
            "wb55_app_ble_o": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/app_ble.o",
            "wb55_adapter_o": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_platform_adapters.o",
            "wb55_glue_o": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_product_entry_glue.o",
            "ble_glue_o": ROOT / "cubeide/Companion_BLE_Audio_Fixture/build/companion_product_entry_glue.o",
            "wb55_transport_o": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/companion_product_transport.o",
            "ble_transport_o": ROOT / "cubeide/Companion_BLE_Audio_Fixture/build/companion_product_transport.o",
        }
        object_hashes = {name: sha(path) if path.exists() else None for name, path in object_paths.items()}
        status_after = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=ROOT,
                                      capture_output=True).stdout
        checks = {
            "source_commit_exact": run(["git", "cat-file", "-e", ns.source_commit]).returncode == 0,
            "verifier_commit_exact": run(["git", "cat-file", "-e", ns.verifier_commit]).returncode == 0,
            "manifest_commit_exact": run(["git", "cat-file", "-e", ns.manifest_commit]).returncode == 0,
            "manifest_source_binding": manifest.get("source_commit") == ns.source_commit,
            "manifest_verifier_binding": manifest.get("verifier_commit") == ns.verifier_commit,
            "manifest_platform_binding": manifest.get("platform_pin") == PIN,
            "clean_head_observed": bool(head),
            "final_worktree_clean": status_before == status_after and len(status_before) == 0,
            "tracked_status_unchanged": status_before == status_after,
            "source_drift_zero": drift == 0,
            "platform_pin": gitlink.endswith(PIN + "\tthird_party/denzic-platform"),
            "fresh_host_compile": compile.returncode == 0,
            "fresh_host_execution": host is not None and host.returncode == 0,
            "observed_traces": all(x in stdout for x in ["diag positive", "device terminal_count", "ota positive", "adapter_observer begin=", "ordered_trace=begin>callback>mutation>readback>terminal"]),
            "verifier_blob_exact": bool(verifier_blob) and verifier_blob == verifier_worktree_blob,
            "transport_object_outputs": all(object_hashes.get(k) for k in ("wb55_transport_o", "ble_transport_o")),
            "transport_map_binding": all("companion_product_transport.o" in (ROOT / p).read_text(encoding="utf-8") for p in ("cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.map", "cubeide/Companion_BLE_Audio_Fixture/build/Companion_BLE_Audio_Fixture.map")),
            "generators_clean": all(generators.values()),
            "wb55_wrapper": wrappers[0]["exit"] == 0,
            "ble_wrapper": wrappers[1]["exit"] == 0,
            "all_firmware_outputs": all(outputs.values()),
            "production_ota_fail_closed_without_loader_candidate": "68240" not in (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8"),
        }
        artifact = {
            "schema": "companion.platform_adapters.machine_ready.fresh.v3",
            "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
            "validated_source_commit": ns.source_commit,
            "verifier_commit": ns.verifier_commit,
            "verifier_blob_sha256": verifier_worktree_blob,
            "evidence_head": head,
            "manifest_commit": ns.manifest_commit,
            "manifest_sha256": hashlib.sha256(manifest_result.stdout).hexdigest().upper(),
            "platform_pin": PIN,
            "gitlink": gitlink,
            "source_sha256": {p: sha(ROOT / p) for p in source_paths},
            "host_runner": {"compile_command_sha256": hashlib.sha256(command.encode()).hexdigest().upper(),
                            "exe_sha256": sha(exe) if exe.exists() else None,
            "stdout_sha256": sha(run_dir / "host.stdout.txt"),
                            "compile_stdout_sha256": hashlib.sha256(compile.stdout.encode()).hexdigest().upper(),
                            "compile_stderr_sha256": hashlib.sha256(compile.stderr.encode()).hexdigest().upper(),
                            "exit": None if host is None else host.returncode},
            "wrappers": wrappers,
            "build_outputs_sha256": outputs,
            "object_outputs_sha256": object_hashes,
            "map_bindings": {
                "wb55_transport_object": "companion_product_transport.o" in (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_visual_runtime/Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime.map").read_text(encoding="utf-8"),
                "ble_transport_object": "companion_product_transport.o" in (ROOT / "cubeide/Companion_BLE_Audio_Fixture/build/Companion_BLE_Audio_Fixture.map").read_text(encoding="utf-8"),
            },
            "retained_logs_sha256": {
                str(path.relative_to(run_dir)).replace("\\", "/"): sha(path)
                for path in validation.glob("*.txt") if path.exists()
            },
            "generator_checks": generators,
            "checks": checks,
            "side_effects": {"hardware": 0, "ble_write": 0, "ota_transfer": 0, "ota_apply": 0,
                              "programmer": 0, "serial": 0, "popup": 0, "push": 0},
            "physical_gates": {"execute": "CLOSED_NOT_AUTHORIZED", "hardware": "CLOSED_NOT_AUTHORIZED", "real_ble": "CLOSED_NOT_AUTHORIZED",
                                "ota_transfer_apply": "CLOSED_NOT_AUTHORIZED"},
        }
        (run_dir / "machine-ready.json").write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(artifact, indent=2, sort_keys=True))
        return 0 if artifact["status"] == "MACHINE_READY" else 2
    finally:
        shutil.rmtree(isolated, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
