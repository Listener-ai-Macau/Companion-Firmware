#!/usr/bin/env python3
"""Verify the NUCLEO-WB55RG devboard IOC tracks the user-provided STM32.ioc."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-devboard-ioc-import.json")
DEVBOARD_IOC = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG" / "Companion_Nucleo_WB55RG.ioc"
PRODUCT_IOC = REPO_ROOT / "Companion_Pendant.ioc"
BRINGUP_README = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "README.md"
WORKFLOW_DOC = REPO_ROOT / "docs" / "codex_development_workflow.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
SCHEMA_ID = "companion.devboard_ioc_import.v1"

CAPTURED_EXTERNAL_IOC = {
    "path": "C:/Users/Billy/Desktop/STM32.ioc",
    "sha256": "a2b8eb37321661d4c8e85c36c4c6b717fa58ca93391e0071b5e37e32fc265c53",
    "compatible_sha256": "2bb18e229b99d5517487de08884955eef5ff06c5b2fee382887ef19546c75f10",
    "repo_comparison_sha256": "5d91cbf604f2a23e3250bf3cc7d2b5f8bf4cbda4ec461e5b39896227b62a61de",
    "length_bytes": 9996,
}

IGNORED_PROJECT_METADATA = {
    "ProjectManager.ProjectFileName",
    "ProjectManager.ProjectName",
    "ProjectManager.TargetToolchain",
    "ProjectManager.functionlistsort",
}

ALLOWED_REPO_ENRICHMENTS = {
    "PA13.Mode": "Trace_Asynchronous_SW",
    "PA14.Mode": "Trace_Asynchronous_SW",
    "Mcu.Pin36": "PC5",
    "PC5.GPIOParameters": "GPIO_Label",
    "PC5.GPIO_Label": "EPAPER_BUSY",
    "PC5.Locked": "true",
    "PC5.Signal": "GPIO_Input",
    "Mcu.Pin37": "PC6",
    "NVIC.EXTI9_5_IRQn": "true\\:8\\:0\\:true\\:false\\:true\\:true\\:true\\:true",
    "PC6.GPIOParameters": "GPIO_PuPd,GPIO_Label,GPIO_ModeDefaultEXTI",
    "PC6.GPIO_Label": "TOUCH_INT",
    "PC6.GPIO_ModeDefaultEXTI": "GPIO_MODE_IT_FALLING",
    "PC6.GPIO_PuPd": "GPIO_PULLUP",
    "PC6.Locked": "true",
    "PC6.Signal": "GPXTI6",
}

# CubeMX derives this count from Mcu.Pin* entries. It differs only because the
# repo reserves PC5 for e-paper BUSY in addition to the user's imported IOC.
LOCAL_RESERVATION_COUNTER_KEYS = {"Mcu.PinsNb"}

DEVBOARD_REQUIRED_VALUES = {
    "Mcu.CPN": "STM32WB55RGV6",
    "Mcu.Name": "STM32WB55RGVx",
    "Mcu.Package": "VFQFPN68",
    "Mcu.IPNb": "10",
    "ProjectManager.ProjectFileName": "Companion_Nucleo_WB55RG.ioc",
    "ProjectManager.ProjectName": "Companion_Nucleo_WB55RG",
    "ProjectManager.TargetToolchain": "STM32CubeIDE",
    "I2C3.Timing": "0x00707CBB",
    "SPI2.Mode": "SPI_MODE_MASTER",
    "SPI2.CalculateBaudRate": "16.0 MBits/s",
    "USART1.WordLength": "WORDLENGTH_7B",
}

DEVBOARD_REQUIRED_IPS = {"I2C3", "MEMORYMAP", "NVIC", "QUADSPI", "RCC", "SAI1", "SPI2", "SYS", "USART1", "USB"}

DEVBOARD_REQUIRED_PIN_SIGNALS = {
    "PA2.Signal": "QUADSPI_BK1_NCS",
    "PA3.Signal": "QUADSPI_CLK",
    "PB9.Signal": "QUADSPI_BK1_IO0",
    "PB8.Signal": "QUADSPI_BK1_IO1",
    "PA9.Signal": "SPI2_SCK",
    "PC1.Signal": "SPI2_MOSI",
    "PC2.Signal": "SPI2_MISO",
    "PC6.Signal": "GPXTI6",
    "PA6.Signal": "GPIO_Output",
    "PA8.Signal": "SAI1_SCK_A",
    "PB12.Signal": "SAI1_FS_A",
    "PC3.Signal": "SAI1_SD_A",
    "PB3.Signal": "SAI1_SCK_B",
    "PA4.Signal": "SAI1_FS_B",
    "PA5.Signal": "SAI1_SD_B",
    "PB6.Signal": "USART1_TX",
    "PB7.Signal": "USART1_RX",
    "PA11.Signal": "USB_DM",
    "PA12.Signal": "USB_DP",
}

PRODUCT_REQUIRED_VALUES = {
    "Mcu.CPN": "STM32WB55CEUx",
    "Mcu.Name": "STM32WB55CEUx",
    "Mcu.Package": "UFQFPN48",
    "ProjectManager.ProjectFileName": "Companion_Pendant.ioc",
}


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_ioc(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key] = value
    return values


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatible_items(values: dict[str, str], drop_repo_enrichments: bool) -> list[str]:
    items: list[str] = []
    for key, value in values.items():
        if key in IGNORED_PROJECT_METADATA:
            continue
        if key in LOCAL_RESERVATION_COUNTER_KEYS:
            continue
        if drop_repo_enrichments and key in ALLOWED_REPO_ENRICHMENTS:
            continue
        items.append(f"{key}={value}")
    return sorted(items)


def compatible_sha256(values: dict[str, str], drop_repo_enrichments: bool) -> str:
    payload = "\n".join(compatible_items(values, drop_repo_enrichments)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ip_set(values: dict[str, str]) -> set[str]:
    count = int(values.get("Mcu.IPNb", "0"))
    return {values.get(f"Mcu.IP{index}", "") for index in range(count)}


def check_required_values(values: dict[str, str], required: dict[str, str], label: str, errors: list[str]) -> None:
    for key, expected in required.items():
        require(values.get(key) == expected, f"{label} {key} expected {expected}, got {values.get(key)}", errors)


def check_devboard_ioc(values: dict[str, str], errors: list[str]) -> None:
    check_required_values(values, DEVBOARD_REQUIRED_VALUES, "devboard IOC", errors)
    require(ip_set(values) == DEVBOARD_REQUIRED_IPS, f"devboard IOC IP set drifted: {sorted(ip_set(values))}", errors)
    check_required_values(values, DEVBOARD_REQUIRED_PIN_SIGNALS, "devboard IOC", errors)
    for key, expected in ALLOWED_REPO_ENRICHMENTS.items():
        require(values.get(key) == expected, f"devboard IOC allowed enrichment {key} drifted", errors)
    require("PC10.Signal" not in values, "devboard IOC must keep optional TP_RST pin PC10 free", errors)
    require("Mcu.Pin38" not in values, "devboard IOC must not reserve an unconnected PC10 pin", errors)


def check_product_ioc(values: dict[str, str], errors: list[str]) -> None:
    check_required_values(values, PRODUCT_REQUIRED_VALUES, "product IOC", errors)
    require("STM32_WPAN" in ip_set(values), "product IOC must keep STM32_WPAN generated stack enabled", errors)
    require("RF" in ip_set(values), "product IOC must keep RF enabled", errors)
    require("SPI1" in ip_set(values), "product IOC must keep SPI1 for product e-paper path", errors)
    require(values.get("PB3.Signal") == "SPI1_SCK", "product IOC SPI1/e-paper SCK guard drifted", errors)


def check_external_subset(external: dict[str, str], repo_values: dict[str, str], errors: list[str]) -> None:
    for key, value in external.items():
        if key in IGNORED_PROJECT_METADATA or key in LOCAL_RESERVATION_COUNTER_KEYS:
            continue
        require(repo_values.get(key) == value, f"devboard IOC does not preserve external STM32.ioc {key}={value}", errors)
    extra = sorted(set(repo_values) - set(external) - IGNORED_PROJECT_METADATA)
    unexpected_extra = [key for key in extra if key not in ALLOWED_REPO_ENRICHMENTS]
    require(not unexpected_extra, f"devboard IOC has unexpected local hardware keys: {unexpected_extra}", errors)


def check_live_external(path: pathlib.Path, repo_values: dict[str, str], errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    external_values = parse_ioc(path)
    live = {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "compatible_sha256": compatible_sha256(external_values, drop_repo_enrichments=False),
        "length_bytes": path.stat().st_size,
    }
    require(live["sha256"] == CAPTURED_EXTERNAL_IOC["sha256"], "live external STM32.ioc SHA-256 no longer matches captured source", errors)
    require(
        live["compatible_sha256"] == CAPTURED_EXTERNAL_IOC["compatible_sha256"],
        "live external STM32.ioc compatible hash no longer matches captured source",
        errors,
    )
    require(
        compatible_sha256(external_values, drop_repo_enrichments=False) == CAPTURED_EXTERNAL_IOC["repo_comparison_sha256"],
        "live external STM32.ioc normalized comparison hash no longer matches captured source",
        errors,
    )
    check_external_subset(external_values, repo_values, errors)
    return live


def build_summary(values: dict[str, str]) -> dict[str, Any]:
    return {
        "mcu": values.get("Mcu.CPN"),
        "package": values.get("Mcu.Package"),
        "ip_set": sorted(ip_set(values)),
        "pins": {key: values.get(key) for key in sorted(DEVBOARD_REQUIRED_PIN_SIGNALS)},
        "allowed_repo_enrichments": ALLOWED_REPO_ENRICHMENTS,
        "local_reservation_counter_keys": sorted(LOCAL_RESERVATION_COUNTER_KEYS),
    }


def build_fixture() -> dict[str, Any]:
    devboard_values = parse_ioc(DEVBOARD_IOC)
    product_values = parse_ioc(PRODUCT_IOC)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Capture that the user-provided C:/Users/Billy/Desktop/STM32.ioc devboard pin/peripheral configuration is imported into the repo-owned NUCLEO IOC without overwriting the separate product IOC.",
        "sources": {
            "captured_external_ioc": CAPTURED_EXTERNAL_IOC["path"],
            "devboard_ioc": rel(DEVBOARD_IOC),
            "product_ioc": rel(PRODUCT_IOC),
            "bringup_readme": rel(BRINGUP_README),
            "workflow_doc": rel(WORKFLOW_DOC),
            "bringup_steps": rel(BRINGUP_STEPS),
            "verifier": "tools/verify_devboard_ioc_import.py",
        },
        "captured_external_ioc": CAPTURED_EXTERNAL_IOC,
        "devboard_ioc": {
            "sha256": sha256_file(DEVBOARD_IOC),
            "compatible_sha256": compatible_sha256(devboard_values, drop_repo_enrichments=True),
            "hardware_summary": build_summary(devboard_values),
        },
        "product_ioc_guard": {
            "sha256": sha256_file(PRODUCT_IOC),
            "mcu": product_values.get("Mcu.CPN"),
            "package": product_values.get("Mcu.Package"),
            "must_not_be_overwritten_by_devboard_ioc": True,
        },
        "allowed_differences_from_external_ioc": {
            "ignored_project_metadata": sorted(IGNORED_PROJECT_METADATA),
            "repo_enrichments": ALLOWED_REPO_ENRICHMENTS,
            "local_reservation_counter_keys": sorted(LOCAL_RESERVATION_COUNTER_KEYS),
        },
        "acceptance": {
            "external_hardware_keys_preserved": True,
            "repo_metadata_is_cubeide_owned": True,
            "product_ioc_kept_separate": True,
            "wba_safe_board_facts_stay_in_ioc": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_devboard_ioc_import.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_docs(errors: list[str]) -> None:
    bringup_readme = read(BRINGUP_README, errors)
    workflow = read(WORKFLOW_DOC, errors)
    bringup_steps = read(BRINGUP_STEPS, errors)
    for token in [
        "new development-board `.ioc`",
        "SAI1 Block B, SPI2, I2C3",
        "verify_devboard_ioc_import.py",
    ]:
        require(token in bringup_readme, f"NUCLEO bring-up README missing IOC anchor {token}", errors)
    for token in [
        "STM32.ioc",
        "Companion_Nucleo_WB55RG.ioc",
        "verify_devboard_ioc_import.py",
    ]:
        require(token in workflow, f"workflow doc missing devboard IOC anchor {token}", errors)
        require(token in bringup_steps, f"bringup steps missing devboard IOC anchor {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected devboard IOC import schema", errors)
    require(data.get("status") == "PASS", "devboard IOC import fixture must be PASS", errors)
    require(
        data.get("captured_external_ioc", {}).get("repo_comparison_sha256") == data.get("devboard_ioc", {}).get("compatible_sha256"),
        "devboard IOC compatible hash must match captured external IOC",
        errors,
    )
    guard = data.get("product_ioc_guard", {})
    require(guard.get("mcu") == "STM32WB55CEUx", "product IOC guard must stay on STM32WB55CEUx", errors)
    require(guard.get("package") == "UFQFPN48", "product IOC guard must stay on UFQFPN48", errors)
    require(guard.get("must_not_be_overwritten_by_devboard_ioc") is True, "product IOC guard missing overwrite protection", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "external_hardware_keys_preserved",
        "repo_metadata_is_cubeide_owned",
        "product_ioc_kept_separate",
        "wba_safe_board_facts_stay_in_ioc",
    ]:
        require(acceptance.get(token) is True, f"devboard IOC import acceptance missing {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing devboard IOC import fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic devboard IOC import fixture.")
    parser.add_argument(
        "--external",
        type=pathlib.Path,
        default=pathlib.Path(CAPTURED_EXTERNAL_IOC["path"]),
        help="Optional live external STM32.ioc to compare when present.",
    )
    parser.add_argument("--require-external", action="store_true", help="Fail if --external is missing.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    external_path = args.external
    errors: list[str] = []
    for path in [DEVBOARD_IOC, PRODUCT_IOC, BRINGUP_README, WORKFLOW_DOC, BRINGUP_STEPS]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if args.require_external:
        require(external_path.exists(), f"missing required external IOC {external_path}", errors)

    expected: dict[str, Any] = {}
    if not errors:
        devboard_values = parse_ioc(DEVBOARD_IOC)
        product_values = parse_ioc(PRODUCT_IOC)
        check_devboard_ioc(devboard_values, errors)
        check_product_ioc(product_values, errors)
        compatible = compatible_sha256(devboard_values, drop_repo_enrichments=True)
        require(
            compatible == CAPTURED_EXTERNAL_IOC["repo_comparison_sha256"],
            "repo devboard IOC compatible hash no longer matches captured external STM32.ioc",
            errors,
        )
        live = check_live_external(external_path, devboard_values, errors)
        if args.require_external:
            require(live is not None, f"required external IOC was not checked: {external_path}", errors)
        check_docs(errors)
        expected = build_fixture() if not errors else {}
        if expected:
            check_fixture_data(expected, errors)

    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion devboard IOC import checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion devboard IOC import verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
