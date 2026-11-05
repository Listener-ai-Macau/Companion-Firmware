#!/usr/bin/env python3
"""Build WBA callback/core library and run native behavior; never flash a board."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import verify_wba_adapter_m33_compile as m33
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
EPAPER = ROOT / "app/companion_pendant/epaper"
HARNESS = EPAPER / "tests/test_wba_prehardware.c"
CORE = tuple(EPAPER / name for name in (
    "asset_store.c", "emote_asset_pack.c", "emote_player.c",
    "motion_coordinator.c", "screen_composition.c", "overlay_commit_scheduler.c",
))
HOST = (HARNESS, EPAPER / "screen_scheduler_stm32wba.c",
        EPAPER / "screen_assets_stm32wba.c", *CORE)
DEFAULT_PACK = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/"
    "companion-v9-expression-candidate-200x200.cemp"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path, log: Path, *, timeout: int = 60) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False, timeout=timeout)
    output = result.stdout + result.stderr
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(command, ensure_ascii=False) + "\n" + output + "\n")
    if result.returncode != 0:
        raise RuntimeError(f"command exited {result.returncode}: {command[0]}\n{output}")
    return output


def build_host(output: Path, log: Path) -> Path:
    exe = output / ("wba_prehardware.exe" if os.name == "nt" else "wba_prehardware")
    if os.name == "nt":
        devcmd = find_vsdevcmd()
        if devcmd is None:
            raise RuntimeError("Visual Studio C++ Build Tools not found")
        args = ["cl.exe", "/nologo", "/std:c11", "/W4", "/WX", "/utf-8",
                "/D_CRT_SECURE_NO_WARNINGS", f"/I{EPAPER}",
                *(str(path) for path in HOST), f"/Fe:{exe}"]
        script = output / "build_host.cmd"
        script.write_text(
            f'@echo off\ncall "{devcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
            "if errorlevel 1 exit /b %errorlevel%\n" + subprocess.list2cmdline(args) + "\n",
            encoding="utf-8",
        )
        run(["cmd.exe", "/d", "/c", str(script)], output, log)
    else:
        compiler = shutil.which("cc") or shutil.which("clang")
        if compiler is None:
            raise RuntimeError("Native C compiler not found")
        run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", f"-I{EPAPER}",
             *(str(path) for path in HOST), "-o", str(exe)], output, log)
    return exe


def git_revision(path: Path) -> str | None:
    value = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path,
                           capture_output=True, text=True, check=False)
    return value.stdout.strip() if value.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/wba-prehardware")
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK,
                        help="200x200 CEMP replay fixture; never activates it on hardware")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log = output / "build.log"
    log.write_text("WBA prehardware build and native behavior\n", encoding="utf-8")
    report = {
        "schema": "companion.wba.prehardware.v1",
        "result": "FAIL_PREHARDWARE",
        "target_family": "STM32WBA",
        "target_variants": ["WBA55", "WBA65"],
        "selected_product_part": "STM32WBA55CEU6",
        "firmware_flashable": False,
        "hardware_acceptance": "NOT_RUN_HARDWARE_NOT_AVAILABLE",
        "hardware_parity_claimed": False,
        "firmware_git_head": git_revision(ROOT),
        "hardware_git_head": git_revision(ROOT.parent / "Companion-Hardware"),
        "remaining": [
            "Resolve V1.1 EPD reset, battery divider, charger pull-ups and panel identity",
            "Integrate BLE/product runtime beyond the separate V1.1 board diagnostic image",
            "Product security/NVM/OTA layout and signed release packaging",
            "Real LSE/RTC, touch during BUSY, panel residue, microphone and sleep current",
            "Board codec=3 recording -> disconnect/resume -> Type -> real ASR -> both minutes modes",
            "Complete-chain accuracy artifact then blocking owner acceptance prompt",
        ],
    }
    try:
        compiler = shutil.which("arm-none-eabi-gcc")
        archiver = shutil.which("arm-none-eabi-ar")
        if not compiler or not archiver:
            raise RuntimeError("Arm GNU compiler/archiver required")
        report["compiler"] = run([compiler, "--version"], output, log).splitlines()[0]
        sources = (*m33.ADAPTER_SOURCES, *CORE)
        objects = []
        objdir = output / "m33"
        objdir.mkdir(exist_ok=True)
        for source in sources:
            obj = objdir / (source.stem + ".o")
            command = m33.compiler_command(compiler, source, obj)
            run([*command, "-Os"], output, log)
            objects.append(obj)
        # Rebuild from scratch to avoid carrying stale archive members.
        library = output / "libcompanion_wba_prehardware.a"
        library.unlink(missing_ok=True)
        run([archiver, "rcs", str(library), *(str(obj) for obj in objects)], output, log)
        exe = build_host(output, log)
        replay = run([str(exe), str(args.pack.resolve())], output, log)
        (output / "replay.txt").write_text(replay, encoding="utf-8")
        if "PASS_PREHARDWARE:" not in replay:
            raise RuntimeError("native replay success marker missing")
        tracked_inputs = {HARNESS, Path(__file__).resolve(), Path(m33.__file__).resolve(),
                          *sources, *EPAPER.glob("*.h")}
        for directory in m33.INCLUDE_DIRS:
            tracked_inputs.update(directory.glob("*.h"))
        report.update({
            "result": "PASS_PREHARDWARE_SOFTWARE_ONLY",
            "m33_object_count": len(objects),
            "library": {"path": library.name, "sha256": sha256(library)},
            "host_replay": {"path": exe.name, "sha256": sha256(exe)},
            "replay_fixture": {"path": str(args.pack.resolve()),
                               "sha256": sha256(args.pack), "activated": False},
            "source_sha256": {path.relative_to(ROOT).as_posix(): sha256(path)
                              for path in sorted(tracked_inputs)},
        })
        print(replay, end="")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
    finally:
        (output / "prehardware-result.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (output / "README.txt").write_text(
            "WBA PREHARDWARE SOFTWARE PACKAGE\n"
            "The .a is a Cortex-M33 callback/core library, NOT a flashable firmware.\n"
            "The executable replays C logic against fake time/storage on the host.\n"
            "The CEMP is a candidate test fixture, not a replacement for owner-approved resources.\n"
            "Read prehardware-result.json and replay.txt for actual results and source hashes.\n"
            "No WBA board, screen, radio, audio or full-chain acceptance is claimed.\n",
            encoding="utf-8")
    print(f"{report['result']} -> {output / 'prehardware-result.json'}")
    return 0 if report["result"] == "PASS_PREHARDWARE_SOFTWARE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
