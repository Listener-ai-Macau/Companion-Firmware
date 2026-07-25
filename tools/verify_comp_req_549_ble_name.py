#!/usr/bin/env python3
"""Build and execute the offline BLE name matrix with auto-discovered MSVC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
GATE_FILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
SOURCES = [
    ROOT / "tools/comp_req_549_ble_name_host_fixture.c",
    ROOT / "app/companion_pendant/platform/companion_ble_name.c",
    ROOT / "app/companion_pendant/platform/companion_ble_name_entry.c",
    ROOT / "app/companion_pendant/gatt/companion_gatt_stm32wb.c",
]
INCLUDES = [
    ROOT / "tools",
    ROOT / "app/companion_pendant/platform",
    ROOT / "app/companion_pendant/gatt",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/auto",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core/template",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/core",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN",
    ROOT / "third_party/STM32CubeWB/Middlewares/ST/STM32_WPAN/ble/svc/Src",
    ROOT / "third_party/STM32CubeWB/Drivers/CMSIS/Core/Include",
    ROOT / "third_party/STM32CubeWB/Drivers/CMSIS/Include",
    ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Inc",
    ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32_WPAN/App",
    ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32_WPAN/Target",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest().upper()


def discover_cl() -> tuple[Path, Path] | None:
    candidates: list[Path] = []
    env_cc = os.environ.get("CC")
    if env_cc:
        candidates.append(Path(env_cc))
    found_on_path = shutil.which("cl.exe")
    if found_on_path:
        candidates.append(Path(found_on_path))
    roots = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    ]
    for root in roots:
        candidates.extend(root.glob(
            "Microsoft Visual Studio/*/BuildTools/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
        candidates.extend(root.glob(
            "Microsoft Visual Studio/*/Community/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
    for compiler in candidates:
        if compiler and compiler.exists():
            vc = compiler.parents[6] / "Auxiliary/Build/vcvars64.bat"
            if vc.exists():
                return compiler, vc
    return None


def vc_env(vcvars: Path) -> dict[str, str]:
    command = f'call "{vcvars}" >nul && set'
    raw = subprocess.check_output(command, shell=True, text=True)
    env = os.environ.copy()
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    return env


def run(command: list[str], env: dict[str, str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(command, cwd=cwd, env=env, text=True,
                          capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def normalize(text: str) -> str:
    return text.replace(str(ROOT), "<ROOT>").replace("\\", "/")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / ".cache/validation/comp-req-549-ble-name.json")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {
        "schema": "comp_req_549_ble_name_runner_v1",
        "source_commit": git("rev-parse", "HEAD"),
        "platform_pin": git("ls-tree", "HEAD", "third_party/denzic-platform").split()[2],
        "gate_default": 0,
        "physical_gates": {
            "hardware": 0, "ble_write": 0, "serial": 0, "ota_transfer": 0,
            "ota_apply": 0, "bonding": 0, "re_pair": 0,
        },
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in SOURCES},
        "route_oracle": {
            "gate_default_zero": "COMPANION_BLE_NAME_PLATFORM_GATE 0" in GATE_FILE.read_text(),
            "legacy_route_present": "companion_v1_apply_ble_name_config" in GATE_FILE.read_text(),
            "new_route_present": "companion_ble_name_product_entry" in GATE_FILE.read_text(),
            "controller_call_in_target_boundary": False,
        },
    }
    found = discover_cl()
    if found is None:
        result["status"] = "NO_GO_HOST_COMPILER"
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2
    compiler, vcvars = found
    try:
        env = vc_env(vcvars)
    except (OSError, subprocess.CalledProcessError) as error:
        result["status"] = "NO_GO_VCVARS"
        result["error"] = type(error).__name__
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2
    result["compiler"] = "auto-discovered-msvc"
    with tempfile.TemporaryDirectory(prefix="comp-req-549-", dir=ROOT / ".cache") as temp:
        build = Path(temp)
        (build / "compiler.h").write_text(
            "#ifndef COMPILER_H__\n#define COMPILER_H__\n"
            "#define __WEAK\n#define PACKED(decl) decl\n"
            "#define __PACKED_STRUCT struct\n#define __PACKED_UNION union\n"
            "#define SECTION(name)\n#define ALIGN_DEF(n)\n#define NO_INIT(var) var\n"
            "#endif\n", encoding="ascii")
        (build / "cmsis_compiler.h").write_text(
            "#ifndef __CMSIS_COMPILER_H\n#define __CMSIS_COMPILER_H\n"
            "#define __STATIC_INLINE static inline\n"
            "#define __STATIC_FORCEINLINE static inline\n"
            "#define __ALIGNED(x)\n#define __WEAK\n"
            "#endif\n", encoding="ascii")
        objects: list[Path] = []
        include_args = ["/I", str(build)] + [item for inc in INCLUDES for item in ("/I", str(inc))]
        for index, source in enumerate(SOURCES):
            obj = build / f"source_{index}.obj"
            command = [str(compiler), "/nologo", "/std:c11", "/O2", "/W4", "/WX",
                       "/Gy", "/D__WEAK=", f"/FI{build / 'compiler.h'}",
                       f"/FI{build / 'cmsis_compiler.h'}",
                       *include_args, "/c", str(source),
                       f"/Fo{obj}"]
            code, stdout, stderr = run(command, env, ROOT)
            result.setdefault("compile", []).append({
                "source": str(source.relative_to(ROOT)), "exit": code,
                "stdout": normalize(stdout), "stderr": normalize(stderr),
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest().upper(),
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest().upper(),
            })
            if code != 0:
                result["status"] = "NO_GO_COMPILE"
                output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                return 2
            objects.append(obj)
        exe = build / "comp_req_549_ble_name_host_fixture.exe"
        link = [str(compiler), "/nologo", *(str(obj) for obj in objects),
                f"/Fe{exe}", "/link", "/OPT:REF", "/INCREMENTAL:NO"]
        code, stdout, stderr = run(link, env, ROOT)
        result["link_exit"] = code
        result["link_stdout"] = normalize(stdout)
        result["link_stderr"] = normalize(stderr)
        if code != 0:
            result["status"] = "NO_GO_LINK"
        else:
            code, stdout, stderr = run([str(exe)], env, ROOT)
            result["fixture_exit"] = code
            result["fixture_stdout"] = stdout.strip()
            result["fixture_stderr_sha256"] = hashlib.sha256(stderr.encode()).hexdigest().upper()
            result["fixture_sha256"] = sha256(exe)
            result["status"] = "PASS" if code == 0 and "BLE_NAME_FIXTURE PASS" in stdout else "NO_GO_FIXTURE"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
