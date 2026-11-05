#!/usr/bin/env python3
"""Compile every callback-only STM32WBA adapter for the Cortex-M33 baseline."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "epaper"
TOUCH_ROOT = REPO_ROOT / "app" / "companion_pendant" / "touch"
POWER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "power"
STORAGE_ROOT = REPO_ROOT / "app" / "companion_pendant" / "storage"
DEFAULT_FIXTURE = pathlib.Path(
    "docs/validation/companion-screen-wba-adapter-m33-compile.json"
)
SCHEMA_ID = "companion.pendant.wba_adapter_m33_compile.v1"

ADAPTER_SOURCES = (
    EPAPER_ROOT / "panel_target_stm32wba.c",
    EPAPER_ROOT / "screen_scheduler_stm32wba.c",
    EPAPER_ROOT / "screen_gatt_stm32wba.c",
    EPAPER_ROOT / "screen_assets_stm32wba.c",
    EPAPER_ROOT / "expression_frame_placement.c",
    TOUCH_ROOT / "touch_target_stm32wba_ft6336.c",
    POWER_ROOT / "power_target_stm32wba.c",
    STORAGE_ROOT / "spi_nor_stm32wba.c",
    EPAPER_ROOT / "pet_behavior_user_data_stm32wba.c",
)
INCLUDE_DIRS = (EPAPER_ROOT, TOUCH_ROOT, POWER_ROOT, STORAGE_ROOT)
COMPILE_FLAGS = (
    "-std=c11",
    "-mcpu=cortex-m33",
    "-mthumb",
    "-mfloat-abi=soft",
    "-ffreestanding",
    "-fno-common",
    "-ffunction-sections",
    "-fdata-sections",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Wconversion",
    "-Wshadow",
    "-Wdouble-promotion",
    "-Wformat=2",
    "-pedantic",
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_STATIC_M33_COMPILE_CONTRACT",
        "purpose": (
            "Require the callback-only WBA screen, touch, power, asset, SPI-NOR, "
            "pet-memory adapters, and portable expression-frame placement to compile as strict freestanding Cortex-M33 C "
            "before a CubeWBA project exists."
        ),
        "targets": {
            "shared_baseline": "WBA55",
            "expanded_target": "WBA65",
            "architecture": "Arm Cortex-M33",
            "floating_point_abi": "soft shared baseline",
        },
        "compiler_contract": {
            "executable": "arm-none-eabi-gcc",
            "dumpmachine": "arm-none-eabi",
            "compile_only": True,
            "flags": list(COMPILE_FLAGS),
            "warnings_are_errors": True,
        },
        "adapter_sources": [rel(path) for path in ADAPTER_SOURCES],
        "include_boundaries": [rel(path) for path in INCLUDE_DIRS],
        "claims": {
            "all_adapter_objects_must_compile": True,
            "cube_wba_project_claimed": False,
            "wba_hardware_parity_claimed": False,
            "real_panel_refresh_claimed": False,
        },
        "required_future_evidence": [
            "A separate selected-target CubeWBA IOC/project and build wrapper.",
            "WBA55 or WBA65 target pin, clock, DMA, BLE, storage, and scheduler glue.",
            "Real panel, FT6336, LSE/RTC, BLE sleep, current, and visual evidence.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_wba_adapter_m33_compile.py",
            "python .\\tools\\verify_wba_adapter_m33_compile.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def compiler_command(
    compiler: str,
    source: pathlib.Path,
    object_path: pathlib.Path,
) -> list[str]:
    return [
        compiler,
        *COMPILE_FLAGS,
        *(f"-I{path}" for path in INCLUDE_DIRS),
        "-c",
        str(source),
        "-o",
        str(object_path),
    ]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def compiler_error(completed: subprocess.CompletedProcess[str]) -> str:
    return (
        completed.stderr.strip()
        or completed.stdout.strip()
        or f"exit {completed.returncode}"
    )


def check_compiler(errors: list[str]) -> str | None:
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        errors.append("missing arm-none-eabi-gcc for WBA Cortex-M33 adapter compile")
        return None

    machine = run_command([compiler, "-dumpmachine"])
    require(
        machine.returncode == 0 and machine.stdout.strip() == "arm-none-eabi",
        "arm-none-eabi-gcc did not report the arm-none-eabi target",
        errors,
    )
    return compiler


def check_adapter_objects(compiler: str, errors: list[str]) -> list[str]:
    compiled: list[str] = []
    with tempfile.TemporaryDirectory(prefix="companion_wba_adapter_m33_") as tmp:
        output_root = pathlib.Path(tmp)
        for index, source in enumerate(ADAPTER_SOURCES, start=1):
            if not source.exists():
                errors.append(f"missing WBA adapter source {rel(source)}")
                continue
            object_path = output_root / f"{index:02d}_{source.stem}.o"
            completed = run_command(compiler_command(compiler, source, object_path))
            if completed.returncode != 0:
                errors.append(
                    f"Cortex-M33 compile failed for {rel(source)}: "
                    f"{compiler_error(completed)}"
                )
                continue
            require(
                object_path.exists() and object_path.stat().st_size > 0,
                f"Cortex-M33 compile produced no object for {rel(source)}",
                errors,
            )
            if object_path.exists() and object_path.stat().st_size > 0:
                compiled.append(rel(source))
    return compiled


def check_fail_closed(compiler: str, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="companion_wba_adapter_gate_selftest_") as tmp:
        root = pathlib.Path(tmp)
        broken_source = root / "intentional_compile_failure.c"
        broken_object = root / "intentional_compile_failure.o"
        broken_source.write_text(
            "#error COMPANION_WBA_ADAPTER_GATE_SELF_TEST\n",
            encoding="ascii",
        )
        completed = run_command(
            compiler_command(compiler, broken_source, broken_object)
        )
        output = completed.stdout + completed.stderr
        require(
            completed.returncode != 0
            and "COMPANION_WBA_ADAPTER_GATE_SELF_TEST" in output,
            "compile gate self-test did not reject an intentional source error",
            errors,
        )
        require(
            not broken_object.exists(),
            "compile gate self-test unexpectedly produced an object",
            errors,
        )


def check_fixture(
    path: pathlib.Path,
    expected: dict[str, Any],
    write: bool,
    errors: list[str],
) -> None:
    rendered = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if write and not errors:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return
    require(path.exists(), f"missing fixture {rel(path)}", errors)
    if path.exists():
        require(
            path.read_text(encoding="utf-8") == rendered,
            f"{rel(path)} is stale; rerun with --write-fixture",
            errors,
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    fixture = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []
    compiler = check_compiler(errors)
    compiled: list[str] = []
    if compiler is not None and not errors:
        compiled = check_adapter_objects(compiler, errors)
        if args.self_test:
            check_fail_closed(compiler, errors)
    require(
        len(compiled) == len(ADAPTER_SOURCES),
        f"compiled {len(compiled)}/{len(ADAPTER_SOURCES)} WBA adapter objects",
        errors,
    )
    check_fixture(fixture, expected, args.write_fixture, errors)

    if errors:
        print("FAIL: STM32WBA adapter Cortex-M33 compile gate failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    suffix = " including fail-closed self-test" if args.self_test else ""
    print(
        "PASS: compiled "
        f"{len(compiled)} STM32WBA adapter objects for Cortex-M33{suffix} "
        f"-> {rel(fixture)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
