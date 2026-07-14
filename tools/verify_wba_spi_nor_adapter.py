#!/usr/bin/env python3
"""Verify the callback-only STM32WBA 1-1-1 SPI NOR adapter."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
STORAGE_ROOT = REPO_ROOT / "app" / "companion_pendant" / "storage"
EPAPER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "epaper"
HEADER = STORAGE_ROOT / "spi_nor_stm32wba.h"
SOURCE = STORAGE_ROOT / "spi_nor_stm32wba.c"
HARNESS = REPO_ROOT / "tools" / "fixtures" / "wba_spi_nor_adapter_test.c"
SCREEN_ASSETS_SOURCE = EPAPER_ROOT / "screen_assets_stm32wba.c"
ASSET_STORE_SOURCE = EPAPER_ROOT / "asset_store.c"
DEFAULT_FIXTURE = pathlib.Path(
    "docs/validation/companion-wba-spi-nor-adapter.json"
)
SCHEMA_ID = "companion.pendant.wba_spi_nor_adapter.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_NATIVE_BEHAVIOR_AND_PORTABLE_CONTRACT",
        "purpose": (
            "Use one ordinary 1-1-1 SPI NOR core across WB55, WBA55 and "
            "WBA65, with WB55 SPI1 as the development-board proving path."
        ),
        "sources": {
            "adapter_header": rel(HEADER),
            "adapter_source": rel(SOURCE),
            "native_harness": rel(HARNESS),
            "screen_assets_adapter": rel(SCREEN_ASSETS_SOURCE),
        },
        "targets": {
            "selected_baseline": "WBA55",
            "compatible_target": "WBA65",
            "development_proving_target": "WB55_SPI1",
            "transport": "spi_nor_1_1_1",
            "address_width_bits": 24,
            "max_supported_capacity_bytes": 16 * 1024 * 1024,
            "cube_wba_binding_present": False,
            "hardware_parity_claimed": False,
        },
        "command_contract": {
            "release_powerdown": "0xAB",
            "enable_reset": "0x66",
            "reset_device": "0x99",
            "read_jedec_id": "0x9F",
            "read_status1": "0x05",
            "write_enable": "0x06",
            "read_data": "0x03",
            "page_program": "0x02",
            "erase_4k": "0x20",
            "erase_64k": "0xD8",
            "page_size": 256,
            "erase_size": 4096,
            "block_erase_size": 65536,
        },
        "native_behavior": {
            "valid_jedec_probe": True,
            "invalid_jedec_rejected": True,
            "failed_probe_diagnostics_preserved": True,
            "xtx_reset_normalization": True,
            "cross_page_program_splits": True,
            "readback_matches": True,
            "range_checks": True,
            "aligned_erase": True,
            "aligned_64k_erase": True,
            "unaligned_64k_erase_rejected": True,
            "out_of_range_64k_erase_rejected": True,
            "busy_timeout": True,
            "logical_screen_assets_partition_binding": True,
            "fail_closed_self_test": True,
        },
        "boundary": {
            "hal_free": True,
            "pin_free": True,
            "callbacks": ["chip_select", "transfer", "now_ms", "delay_ms"],
            "screen_layer_transport_agnostic": True,
            "wb55_qspi_backend_replaced": True,
            "wb55_flash_transport": "SPI1",
            "wb55_epaper_transport": "SPI2",
        },
        "required_future_evidence": [
            "Selected STM32WBA55/WBA65 package, CubeWBA project, SPI instance and pins.",
            "Real WBA JEDEC, read/program/erase and reset-cycle logs.",
            "Final external-Flash partition map for ui_assets, recording and OTA staging.",
            "Resource-pack mount/CRC/frame read plus current and low-power evidence.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_wba_spi_nor_adapter.py",
            "python .\\tools\\verify_wba_spi_nor_adapter.py --self-test",
            "python .\\tools\\verify_wba_adapter_m33_compile.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_code(errors: list[str]) -> None:
    for path in (HEADER, SOURCE, HARNESS, SCREEN_ASSETS_SOURCE, ASSET_STORE_SOURCE):
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if errors:
        return

    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    combined = header + "\n" + source
    for token in (
        "companion_spi_nor_stm32wba_chip_select_fn_t",
        "companion_spi_nor_stm32wba_transfer_fn_t",
        "companion_spi_nor_stm32wba_probe",
        "companion_spi_nor_stm32wba_wait_ready",
        "companion_spi_nor_stm32wba_read",
        "companion_spi_nor_stm32wba_program",
        "companion_spi_nor_stm32wba_erase_4k",
        "companion_spi_nor_stm32wba_erase_64k",
        "companion_spi_nor_stm32wba_partition_read",
    ):
        require(token in combined, f"WBA SPI NOR adapter missing {token}", errors)
    for token in (
        "NOR_CMD_WRITE_ENABLE 0x06u",
        "NOR_CMD_READ_STATUS1 0x05u",
        "NOR_CMD_READ_JEDEC_ID 0x9Fu",
        "NOR_CMD_RELEASE_POWERDOWN 0xABu",
        "NOR_CMD_ENABLE_RESET 0x66u",
        "NOR_CMD_RESET_DEVICE 0x99u",
        "NOR_CMD_READ_DATA 0x03u",
        "NOR_CMD_PAGE_PROGRAM 0x02u",
        "NOR_CMD_SECTOR_ERASE_4K 0x20u",
        "NOR_CMD_BLOCK_ERASE_64K 0xD8u",
        "NOR_PAGE_SIZE 256u",
        "NOR_SECTOR_SIZE 4096u",
        "NOR_BLOCK_SIZE 65536u",
    ):
        require(token in source, f"WBA SPI NOR source missing {token}", errors)
    for token in (
        "HAL_",
        "GPIO",
        "QUADSPI",
        "OCTOSPI",
        "OSPI",
        "SPI_HandleTypeDef",
        '#include "stm32wba',
        "PA0",
        "PB0",
        "PC0",
    ):
        require(
            token.lower() not in combined.lower(),
            f"WBA SPI NOR adapter leaked target implementation token {token}",
            errors,
        )
    screen_assets = SCREEN_ASSETS_SOURCE.read_text(encoding="utf-8")
    for token in ("HAL_", "QSPI", "OSPI", "SPI_HandleTypeDef"):
        require(
            token not in screen_assets,
            f"screen-assets layer leaked storage transport token {token}",
            errors,
        )


def find_vsdevcmd() -> pathlib.Path | None:
    install_dir = os.environ.get("VSINSTALLDIR")
    if install_dir:
        candidate = pathlib.Path(install_dir) / "Common7" / "Tools" / "VsDevCmd.bat"
        if candidate.exists():
            return candidate
    roots = (
        pathlib.Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    )
    for root in roots:
        matches = sorted(
            root.glob("Microsoft Visual Studio/*/*/Common7/Tools/VsDevCmd.bat"),
            reverse=True,
        )
        if matches:
            return matches[0]
    return None


def run_command(command: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def compile_native(output_root: pathlib.Path, errors: list[str]) -> pathlib.Path | None:
    vsdevcmd = find_vsdevcmd()
    if vsdevcmd is None:
        errors.append("missing Visual Studio VsDevCmd.bat for native C behavior test")
        return None
    executable = output_root / "wba_spi_nor_adapter_test.exe"
    arguments = [
        "cl.exe",
        "/nologo",
        "/W4",
        "/WX",
        "/std:c11",
        "/TC",
        f"/I{STORAGE_ROOT}",
        f"/I{EPAPER_ROOT}",
        str(HARNESS),
        str(SOURCE),
        str(SCREEN_ASSETS_SOURCE),
        str(ASSET_STORE_SOURCE),
        f"/Fe:{executable}",
    ]
    compiler_command = subprocess.list2cmdline(arguments)
    build_script = output_root / "build_wba_spi_nor_adapter.cmd"
    build_script.write_text(
        "@echo off\n"
        f'call "{vsdevcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
        "if errorlevel 1 exit /b %errorlevel%\n"
        f"{compiler_command}\n",
        encoding="ascii",
    )
    completed = run_command(
        ["cmd.exe", "/d", "/c", str(build_script)],
        output_root,
    )
    require(
        completed.returncode == 0,
        "native adapter compile failed: "
        + (completed.stderr.strip() or completed.stdout.strip()),
        errors,
    )
    require(
        executable.exists() and executable.stat().st_size > 0,
        "native adapter compile produced no executable",
        errors,
    )
    return executable if executable.exists() else None


def check_native_behavior(self_test: bool, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="companion_wba_spi_nor_") as tmp:
        output_root = pathlib.Path(tmp)
        executable = compile_native(output_root, errors)
        if executable is None or errors:
            return
        completed = run_command([str(executable)], output_root)
        output = completed.stdout + completed.stderr
        require(completed.returncode == 0, "native adapter behavior failed: " + output.strip(), errors)
        for token in (
            "PASS probe jedec=0xEF4014 size=1048576",
            "PASS probe_diagnostics raw_jedec=0xFFFFFF transfer=1",
            "PASS xtx_reset normalization=1",
            "PASS page_program splits=3",
            "PASS bounds_and_erase",
            "PASS erase_64k blocks=1",
            "PASS timeout",
            "PASS screen_assets_partition transport=spi_nor_1_1_1",
            "PASS: WBA SPI NOR adapter native behavior",
        ):
            require(token in output, f"native adapter behavior missing {token}", errors)
        if self_test:
            failed = run_command([str(executable), "--force-fail"], output_root)
            failed_output = failed.stdout + failed.stderr
            require(
                failed.returncode != 0
                and "INTENTIONAL_WBA_SPI_NOR_SELF_TEST_FAILURE" in failed_output,
                "native adapter verifier did not fail closed",
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
    check_code(errors)
    if not errors:
        check_native_behavior(args.self_test, errors)
    check_fixture(fixture, expected, args.write_fixture, errors)
    if errors:
        print("FAIL: STM32WBA SPI NOR adapter checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    suffix = " including fail-closed self-test" if args.self_test else ""
    print(
        "PASS: STM32WBA 1-1-1 SPI NOR adapter native behavior verified"
        f"{suffix} -> {rel(fixture)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
