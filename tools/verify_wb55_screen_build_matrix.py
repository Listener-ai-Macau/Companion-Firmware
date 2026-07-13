#!/usr/bin/env python3
"""Verify the WB55 screen build matrix covers firmware and asset-provision paths."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "docs/validation/companion-screen-wb55-build-matrix.json"
SCHEMA_ID = "companion.pendant.screen_wb55_build_matrix.v1"
CANDIDATE = current_candidate()

BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
MAIN_C = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
DISPLAY_QUEUE_H = ROOT / "app/companion_pendant/epaper/display_queue.h"
DISPLAY_QUEUE_C = ROOT / "app/companion_pendant/epaper/display_queue.c"
SSD1681_C = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
PANEL_TARGET_C = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb.c"
PRE_ACCEPTANCE = ROOT / "docs/validation/companion-screen-pre-acceptance-health.json"
BUILD_LOG_DIR = ROOT / ".cache/validation/wb55-build-matrix"
DEFAULT_BUILD_LOG = BUILD_LOG_DIR / "default-build.log"
SSD1681_BUILD_LOG = BUILD_LOG_DIR / "ssd1681-build.log"
SCREEN_ASSET_PROVISION_BUILD_LOG = BUILD_LOG_DIR / "screen-asset-provision-build.log"


EXPECTED_BUILD_SIZES = {
    "dry_run_default": {
        "text": 122660,
        "data": 2436,
        "bss": 182183,
        "dec": 307279,
        "hex": "4b04f",
    },
    "ssd1681_real_panel": {
        "text": 137612,
        "data": 2440,
        "bss": 192263,
        "dec": 332315,
        "hex": "5121b",
    },
    "screen_asset_provision": {
        "text": 408316,
        "data": 2433,
        "bss": 192239,
        "dec": 602988,
        "hex": "9336c",
    },
}


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def has(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def parse_size_line(text: str) -> dict[str, Any] | None:
    match = re.search(
        r"(?m)^\s*(?P<text>\d+)\s+(?P<data>\d+)\s+(?P<bss>\d+)\s+"
        r"(?P<dec>\d+)\s+(?P<hex>[0-9a-fA-F]+)\s+"
        r"(?:build/Companion_Nucleo_WB55RG_Bringup|"
        r"build_screen_asset_provision/Companion_Nucleo_WB55RG_ScreenAssetProvision)\.elf\s*$",
        text,
    )
    if match is None:
        return None
    return {
        "text": int(match.group("text")),
        "data": int(match.group("data")),
        "bss": int(match.group("bss")),
        "dec": int(match.group("dec")),
        "hex": match.group("hex").lower(),
    }


def build_log_evidence() -> dict[str, Any]:
    variants = {
        "dry_run_default": {
            "path": DEFAULT_BUILD_LOG,
            "required_markers": [
                "build_nucleo_bringup: acquired build lock",
                "arm-none-eabi-size build/Companion_Nucleo_WB55RG_Bringup.elf",
                "make: Leaving directory",
                "build_nucleo_bringup: released build lock",
            ],
            "forbidden_markers": [
                "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP=1",
                "panel_target_stm32wb_ssd1681.c",
            ],
        },
        "ssd1681_real_panel": {
            "path": SSD1681_BUILD_LOG,
            "required_markers": [
                "build_nucleo_bringup: acquired build lock",
                "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP=1",
                "panel_target_stm32wb_ssd1681.c",
                "arm-none-eabi-size build/Companion_Nucleo_WB55RG_Bringup.elf",
                "make: Leaving directory",
                "build_nucleo_bringup: released build lock",
            ],
            "forbidden_markers": [],
        },
        "screen_asset_provision": {
            "path": SCREEN_ASSET_PROVISION_BUILD_LOG,
            "required_markers": [
                "build_nucleo_bringup: acquired build lock",
                "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP=1",
                "COMPANION_SCREEN_ASSET_PROVISION=1",
                "-Ibuild_screen_asset_provision/generated",
                "panel_target_stm32wb_ssd1681.c",
                "arm-none-eabi-size build_screen_asset_provision/Companion_Nucleo_WB55RG_ScreenAssetProvision.elf",
                "make: Leaving directory",
                "build_nucleo_bringup: released build lock",
            ],
            "forbidden_markers": [],
        },
    }
    evidence: dict[str, Any] = {}
    for name, spec in variants.items():
        path = spec["path"]
        text = read(path) if path.exists() else ""
        size = parse_size_line(text)
        evidence[name] = {
            "path": rel(path),
            "exists": path.exists(),
            "size": size,
            "expected_size": EXPECTED_BUILD_SIZES[name],
            "required_markers": {
                marker: marker in text for marker in spec["required_markers"]
            },
            "forbidden_markers_absent": {
                marker: marker not in text for marker in spec["forbidden_markers"]
            },
        }
    return evidence


def build_contract() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Machine-only contract that the WB55 screen firmware keeps the "
            "default dry-run panel build, the real SSD1681 bring-up build, "
            "and the external ui_assets ScreenAssetProvision build compilable "
            "before hardware acceptance is requested."
        ),
        "sources": {
            "build_script": rel(BUILD_SCRIPT),
            "makefile": rel(MAKEFILE),
            "main": rel(MAIN_C),
            "app_ble": rel(APP_BLE),
            "display_queue_header": rel(DISPLAY_QUEUE_H),
            "display_queue_source": rel(DISPLAY_QUEUE_C),
            "wb55_panel_target": rel(PANEL_TARGET_C),
            "ssd1681_panel_target": rel(SSD1681_C),
        },
        "build_variants": {
            "dry_run_default": {
                "command": "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
                "log": rel(DEFAULT_BUILD_LOG),
                "panel_transport": "comp_epaper_panel_adapter_init_dry_run",
                "ssd1681_source": "excluded",
                "acceptance": "Links without companion_epaper_panel_stm32wb_ssd1681_* symbols.",
            },
            "ssd1681_real_panel": {
                "command": "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force",
                "log": rel(SSD1681_BUILD_LOG),
                "panel_transport": "panel_target_stm32wb_ssd1681.c",
                "ssd1681_source": "included_when_EPAPER_SSD1681_BRINGUP_1",
                "acceptance": "Links the real SSD1681 transport, wait service, menu, touch wait polling, and resource-generation queue diagnostics.",
            },
            "screen_asset_provision": {
                "command": "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force",
                "log": rel(SCREEN_ASSET_PROVISION_BUILD_LOG),
                "panel_transport": "panel_target_stm32wb_ssd1681.c",
                "ssd1681_source": "included_with_asset_provision_target",
                "asset_source": "build_screen_asset_provision/generated/companion_screen_asset_provision_blob.h",
                "acceptance": (
                    f"Links the rev{CANDIDATE.revision} CEMP blob into the one-time "
                    "external ui_assets provision firmware."
                ),
            },
        },
        "build_log_evidence": build_log_evidence(),
        "contracts": {
            "ssd1681_wait_service_guarded": True,
            "makefile_conditional_ssd1681_source": True,
            "build_wrapper_exposes_real_panel_switch": True,
            "build_wrapper_serializes_shared_build_dir": True,
            "queue_generation_compiles_in_all_variants": True,
            "build_logs_prove_all_variants": True,
            "queue_generation_compiles_in_both_variants": True,
            "build_logs_prove_both_variants": True,
            "screen_asset_provision_builds_current_external_assets": True,
            "pre_acceptance_status_remains_runtime_pending_until_logs": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_wb55_screen_build_matrix.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force",
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
        ],
    }


def check_contract(contract: dict[str, Any], errors: list[str]) -> None:
    require(contract.get("schema_id") == SCHEMA_ID, "unexpected schema_id", errors)
    require(contract.get("status") == "PASS", "build matrix contract must be PASS", errors)
    variants = contract.get("build_variants", {})
    require("dry_run_default" in variants, "missing dry-run build variant", errors)
    require("ssd1681_real_panel" in variants, "missing SSD1681 build variant", errors)
    require("screen_asset_provision" in variants, "missing ScreenAssetProvision build variant", errors)
    for command in [
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force",
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force",
    ]:
        require(command in contract.get("validation_commands", []), f"missing validation command {command}", errors)


def check_sources(errors: list[str]) -> None:
    for path in [BUILD_SCRIPT, MAKEFILE, MAIN_C, APP_BLE, DISPLAY_QUEUE_H, DISPLAY_QUEUE_C, SSD1681_C, PANEL_TARGET_C]:
        require(path.exists(), f"missing {rel(path)}", errors)
    if errors:
        return

    build_script = read(BUILD_SCRIPT)
    makefile = read(MAKEFILE)
    main_c = read(MAIN_C)
    app_ble = read(APP_BLE)
    queue_h = read(DISPLAY_QUEUE_H)
    queue_c = read(DISPLAY_QUEUE_C)
    panel_target = read(PANEL_TARGET_C)
    ssd1681 = read(SSD1681_C)

    require(
        has(
            build_script,
            "[switch]$EpaperSsd1681Bringup",
            "[switch]$ScreenAssetProvision",
            "EPAPER_SSD1681_BRINGUP=1",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_screen_asset_provision",
            "TARGET=Companion_Nucleo_WB55RG_ScreenAssetProvision",
        ),
        "build wrapper must expose -EpaperSsd1681Bringup and -ScreenAssetProvision",
        errors,
    )
    require(
        has(
            build_script,
            "Acquire-BuildLock",
            "Release-BuildLock",
            "build_nucleo_bringup.lock",
            ".cache\\locks",
            "owner.json",
            "Get-Process -Id",
            "Waited too long for build lock",
            "Test-PathUnderRoot",
            "Write-Host \"build_nucleo_bringup: acquired build lock",
            "Write-Host \"build_nucleo_bringup: released build lock",
        ),
        "build wrapper must serialize the shared CubeIDE build directory with a bounded stale-safe lock",
        errors,
    )
    require(
        has(makefile, "ifeq ($(EPAPER_SSD1681_BRINGUP),1)", "panel_target_stm32wb_ssd1681.c"),
        "Makefile must include SSD1681 source only under EPAPER_SSD1681_BRINGUP",
        errors,
    )
    require(
        has(
            panel_target,
            "#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP",
            "companion_epaper_panel_stm32wb_ssd1681_init(adapter, expression_assets);",
            "comp_epaper_panel_adapter_init_dry_run(adapter);",
        ),
        "WB55 panel target must select real SSD1681 only behind the bring-up flag",
        errors,
    )
    require(
        has(
            main_c,
            "#ifndef COMPANION_EPAPER_PANEL_SSD1681_BRINGUP",
            "#define COMPANION_EPAPER_PANEL_SSD1681_BRINGUP 0",
            "#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP",
            "companion_epaper_panel_stm32wb_ssd1681_set_wait_service(",
        ),
        "main.c must guard SSD1681 wait-service linkage for the default dry-run build",
        errors,
    )
    require(
        has(
            app_ble,
            "comp_epaper_display_queue_set_resource_revision(",
            "s_companion_screen_asset_mount.pack.revision",
            "queue_generation revision=",
            "display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u",
            "generation_switches=%lu last_stale_discarded=%lu",
        ),
        "app_ble.c must keep resource-generation diagnostics in the screen path",
        errors,
    )
    require(
        has(
            queue_h,
            "uint32_t resource_revision;",
            "uint32_t active_resource_revision;",
            "uint32_t generation_switch_count;",
            "uint32_t last_stale_generation_discarded;",
            "uint32_t stale_generation_discard_count;",
        )
        and has(
            queue_c,
            "(*out_request)->resource_revision = queue->active_resource_revision;",
            "queue->last_stale_generation_discarded = (uint32_t)discarded;",
            "queue->generation_switch_count++;",
            "queue->stale_generation_discard_count += (uint32_t)discarded;",
            "request->resource_revision = queue->active_resource_revision;",
        ),
        "display queue must carry resource generation in all WB55 screen build variants",
        errors,
    )
    require(
        has(
            ssd1681,
            "companion_epaper_panel_stm32wb_ssd1681_set_wait_service",
            "companion_epaper_wait_service_fn wait_service",
            "s_target_context.wait_service(s_target_context.wait_service_context, now);",
            "COMP_EPAPER_REFRESH_DECISION_PARTIAL",
            "COMP_EPAPER_REFRESH_DECISION_FAST",
        ),
        "SSD1681 target must retain real transport and wait-service hooks",
        errors,
    )


def check_pre_acceptance(errors: list[str]) -> None:
    data = json.loads(PRE_ACCEPTANCE.read_text(encoding="utf-8"))
    require(data.get("status") == "NO_GO_RUNTIME_RECHECK_PENDING", "pre-acceptance must still wait for active runtime logs", errors)
    require(
        data.get("resource", {}).get("runtime_status") == CANDIDATE.pending_status,
        "pre-acceptance resource must remain active-candidate runtime pending",
        errors,
    )


def check_build_logs(contract: dict[str, Any], errors: list[str]) -> None:
    evidence = contract.get("build_log_evidence", {})
    for name, expected_size in EXPECTED_BUILD_SIZES.items():
        item = evidence.get(name, {})
        require(item.get("exists") is True, f"{name} build log missing", errors)
        require(item.get("size") == expected_size, f"{name} build size mismatch: {item.get('size')}", errors)
        for marker, present in item.get("required_markers", {}).items():
            require(present is True, f"{name} build log missing marker: {marker}", errors)
        for marker, absent in item.get("forbidden_markers_absent", {}).items():
            require(absent is True, f"{name} build log contains forbidden marker: {marker}", errors)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)
    output = args.json if args.json.is_absolute() else ROOT / args.json

    contract = build_contract()
    errors: list[str] = []
    check_contract(contract, errors)
    check_sources(errors)
    check_build_logs(contract, errors)
    check_pre_acceptance(errors)

    rendered = json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not output.exists():
            errors.append(f"missing {rel(output)}")
        elif output.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(output)}; rerun with --write")

    if errors:
        print("FAIL: WB55 screen build matrix check failed", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 screen build matrix verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
