#!/usr/bin/env python3
"""Build and identify the one-time COMP-REQ-775 firmware contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup"
BUILD_NAME = "build_comp_req_775_recording_resources"
BUILD = PROJECT / BUILD_NAME
ELF = BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
HEX = ELF.with_suffix(".hex")
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
OUTPUT = ARTIFACTS / "FIRMWARE_BUILD_READY.json"
LOG = ARTIFACTS / "firmware-build.log"
FROZEN_SOURCE_ROOT = (
    REPO
    / ".cache/validation/comp-req-775-menu-hold-milestone-source-pack-v3"
)
FROZEN_BASE = FROZEN_SOURCE_ROOT / "cemp"
FROZEN_CEMP = FROZEN_BASE / "comp_req_771_browser_life.cemp"
FROZEN_CEMP_MANIFEST = FROZEN_BASE / "manifest.json"
FROZEN_SOURCE_MANIFEST = (
    FROZEN_SOURCE_ROOT / "source-pack-manifest.json"
)
FROZEN_PRODUCT_SOURCE_MANIFEST = (
    REPO
    / ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
BROWSER_PAGE = (
    REPO / ".cache/validation/comp-req-628-status-bar/index.html"
)
FROZEN_GENERATION_MANIFEST = (
    REPO
    / ".cache/validation/comp776-component-clip-fix-20260812/"
    "generation-20-compact/generation.json"
)
CONTRACT_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_browser_cemp_contract.py"
)
INTERACTION_CONTRACT_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_browser_interaction_contract.py"
)
INTERACTION_CONTRACT_EXPORTER = (
    REPO
    / "tools/faraday_upper_art/export_comp_req_775_browser_interaction_contract.mjs"
)
REFRESH_PLAYBOOK_VERIFIER = (
    REPO / "tools/verify_companion_epaper_refresh_playbook.py"
)
DISPLAY_ARCHITECTURE_VERIFIER = (
    REPO / "tools/verify_companion_display_runtime_architecture.py"
)
DISPLAY_ARBITER_HOST_TEST = (
    REPO / "tools/test_display_transaction_arbiter_host.ps1"
)
OVERLAY_COMMIT_HOST_TEST = (
    REPO / "tools/test_overlay_commit_scheduler_host.ps1"
)
FROZEN_RESOURCE_PAGE_SHA256 = (
    "5C04FB7AC7B0B1A2585E39BF125DCA970F26AEDF1729D97295C2C1A1C1D69762"
)
FROZEN_CEMP_SHA256 = (
    "9C1761C134A7FE75703A3197140D239BC71FED5AA83EC5B5DC887921A02254F7"
)
FROZEN_STATE_COUNT = 2581
FROZEN_RESOURCE_ID = (
    "027D69E2D438367CD69B51A31390FD98548933FDCDAE974C4EA776548EC24503"
)
MAKE = Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.make."
    "win32_2.2.100.202601091506/tools/bin/make.exe"
)
TOOLCHAIN = Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32."
    "14.3.rel1.win32_1.0.100.202602081740/tools/bin"
)
MAKE_VARIABLES = [
    f"BUILD_DIR={BUILD_NAME}",
    # Keep the OTA App inside its fixed Loader-owned slot while preserving the
    # Makefile's explicit -O3 treatment for the Opus hot path.
    "C_OPT=-Os",
    (
        "BROWSER_SOURCE_PACK_REPO_PATH="
        ".cache/validation/comp-req-775-menu-hold-milestone-source-pack-v3"
    ),
    "BROWSER_CEMP_CONTRACT_PREGENERATED=1",
    "OTA_APP=1",
    "COMPANION_USE_FREERTOS=1",
    "EPAPER_SSD1681_BRINGUP=1",
    "EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT=1",
    "EPAPER_COMP_REQ_638_SOURCE_PACK=1",
    "EPAPER_MENU=1",
    "EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
    "EPAPER_SSD1681_HAS_BUSY=1",
    "EPAPER_SSD1681_USE_SOFTWARE_SPI=1",
    "EPAPER_SSD1681_DIRECT_GPIO_SPI_NOP_COUNT=0",
]
IDENTITY_SOURCES = [
    REPO / "app/companion_pendant/epaper/ui_asset_generation.c",
    REPO / "app/companion_pendant/epaper/ui_asset_generation.h",
    REPO / "app/companion_pendant/epaper/ui_asset_sync_serial.c",
    REPO / "app/companion_pendant/epaper/ui_asset_sync_serial.h",
    REPO / "app/companion_pendant/epaper/display_queue.c",
    REPO / "app/companion_pendant/epaper/display_queue.h",
    REPO / "app/companion_pendant/epaper/tests/test_motion_display_queue.c",
    REPO / "app/companion_pendant/epaper/overlay_commit_scheduler.c",
    REPO / "app/companion_pendant/epaper/overlay_commit_scheduler.h",
    REPO / "app/companion_pendant/epaper/tests/test_overlay_commit_scheduler.c",
    REPO / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
    REPO / "app/companion_pendant/recording/companion_recording_resource_pack.c",
    REPO / "app/companion_pendant/recording/companion_recording_resource_pack.h",
    REPO / "app/companion_pendant/recording/companion_opus16_fixture_blob.h",
    PROJECT / "Core/Src/main.c",
    PROJECT / "Core/Src/app_ble.c",
    PROJECT / "Core/Src/companion_freertos_hooks.c",
    PROJECT / "Core/Src/companion_rtos_watchdog.c",
    PROJECT / "Core/Inc/companion_rtos_watchdog.h",
    PROJECT / "Core/Inc/FreeRTOSConfig.h",
    (
        REPO
        / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/"
        "Applications/BLE/BLE_p2pServer/Core/Src/app_entry.c"
    ),
    PROJECT / "Core/Inc/companion_g7_speech_pcm.h",
    PROJECT / "Makefile",
    REPO / "app/companion_pendant/touch/browser_interaction_runtime.c",
    REPO / "app/companion_pendant/touch/browser_interaction_runtime.h",
    REPO / "tools/build_companion_recording_resources.py",
    FROZEN_CEMP,
    FROZEN_CEMP_MANIFEST,
    FROZEN_SOURCE_MANIFEST,
    FROZEN_PRODUCT_SOURCE_MANIFEST,
    BROWSER_PAGE,
    FROZEN_GENERATION_MANIFEST,
    CONTRACT_GENERATOR,
    INTERACTION_CONTRACT_GENERATOR,
    INTERACTION_CONTRACT_EXPORTER,
    REFRESH_PLAYBOOK_VERIFIER,
    DISPLAY_ARCHITECTURE_VERIFIER,
    DISPLAY_ARBITER_HOST_TEST,
    OVERLAY_COMMIT_HOST_TEST,
    REPO / "docs/companion_display_runtime_architecture.md",
    REPO / "docs/companion_epaper_refresh_playbook.md",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalized_text_sha256(path: Path) -> str:
    normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def relative(path: Path) -> str:
    return str(path.relative_to(REPO)).replace("\\", "/")


def run(args: list[str]) -> str:
    return subprocess.run(
        args,
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def generate_product_browser_contract(
    output_build: Path = BUILD,
    product_source_manifest: Path = FROZEN_PRODUCT_SOURCE_MANIFEST,
    generation_manifest: Path = FROZEN_GENERATION_MANIFEST,
) -> dict:
    generated = output_build / "generated"
    header = generated / "companion_browser_cemp_contract.h"
    receipt = generated / "companion_browser_cemp_contract.json"
    interaction_header = (
        generated / "companion_browser_interaction_contract.h"
    )
    interaction_receipt = (
        generated / "companion_browser_interaction_contract.json"
    )
    interaction_export = (
        generated / "companion_browser_interaction_export.json"
    )
    missing = [
        relative(path)
        for path in (
            FROZEN_CEMP,
            FROZEN_CEMP_MANIFEST,
            FROZEN_SOURCE_MANIFEST,
            product_source_manifest,
            BROWSER_PAGE,
            generation_manifest,
            CONTRACT_GENERATOR,
            INTERACTION_CONTRACT_GENERATOR,
            INTERACTION_CONTRACT_EXPORTER,
        )
        if not path.exists()
    ]
    if missing:
        raise RuntimeError(
            "frozen browser base contract inputs missing: "
            + ", ".join(missing)
        )
    if sha256(FROZEN_CEMP) != FROZEN_CEMP_SHA256:
        raise RuntimeError("frozen browser base CEMP identity changed")
    generation = json.loads(generation_manifest.read_text(encoding="utf-8"))
    expected_resource_id = generation.get("resource_id", "")
    expected_resource_page_sha256 = generation.get("page_sha256", "")
    if (
        generation.get("status") != "PASS"
        or len(expected_resource_id) != 64
        or len(expected_resource_page_sha256) != 64
    ):
        raise RuntimeError("product browser generation identity is invalid")
    generated.mkdir(parents=True, exist_ok=True)
    browser_page_sha256 = normalized_text_sha256(BROWSER_PAGE)
    subprocess.run(
        [
            sys.executable,
            str(CONTRACT_GENERATOR),
            "--cemp",
            str(FROZEN_CEMP),
            "--cemp-manifest",
            str(FROZEN_CEMP_MANIFEST),
            "--source-pack-manifest",
            str(FROZEN_SOURCE_MANIFEST),
            "--output-header",
            str(header),
            "--output-receipt",
            str(receipt),
        ],
        cwd=REPO,
        check=True,
    )
    contract = json.loads(receipt.read_text(encoding="utf-8"))
    if (
        contract.get("status") != "PASS"
        or contract.get("cemp_sha256") != FROZEN_CEMP_SHA256
        or contract.get("state_map_count") != FROZEN_STATE_COUNT
        or contract.get("function_clip_timing_count") != 3
    ):
        raise RuntimeError("generated browser base contract is not frozen baseline")
    subprocess.run(
        [
            "node",
            str(INTERACTION_CONTRACT_EXPORTER),
            "--page",
            relative(BROWSER_PAGE),
            "--output",
            relative(interaction_export),
            "--expected-page-sha256",
            browser_page_sha256,
        ],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(INTERACTION_CONTRACT_GENERATOR),
            "--contract",
            str(interaction_export),
            "--cemp-manifest",
            str(FROZEN_CEMP_MANIFEST),
            "--source-pack-manifest",
            str(product_source_manifest),
            "--generation-manifest",
            str(generation_manifest),
            "--expected-page-sha256",
            browser_page_sha256,
            "--expected-resource-page-sha256",
            expected_resource_page_sha256,
            "--output-header",
            str(interaction_header),
            "--output-receipt",
            str(interaction_receipt),
        ],
        cwd=REPO,
        check=True,
    )
    interaction_contract = json.loads(
        interaction_receipt.read_text(encoding="utf-8")
    )
    if (
        interaction_contract.get("status") != "PASS"
        or interaction_contract.get("page_sha256") != browser_page_sha256
        or interaction_contract.get("trace_count") != 8
        or interaction_contract.get("menu_state_count") != 2110
        or interaction_contract.get("menu_screen_count") != 13
        or interaction_contract.get("menu_row_count") != 63
        or interaction_contract.get("pointer_state_count") != 250
        or interaction_contract.get("product_resource_id") != expected_resource_id
        or interaction_contract.get("life_family_mask") != 0x03FF
        or interaction_contract.get("blink_cadence_ms") != 480
        or interaction_contract.get("blink_first_interval_commits") != 24
        or interaction_contract.get("blink_interval_commits")
        != [24, 32, 40]
        or any(
            count < 100
            for count in interaction_contract.get("life_commit_counts", {}).values()
        )
    ):
        raise RuntimeError(
            "generated browser interaction contract is not frozen baseline"
        )
    return {
        "cemp": contract,
        "interaction": interaction_contract,
    }


def sections() -> dict[str, tuple[int, int, int]]:
    output = run(
        [str(TOOLCHAIN / "arm-none-eabi-objdump.exe"), "-h", str(ELF)]
    )
    result: dict[str, tuple[int, int, int]] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].isdigit():
            result[fields[1]] = (
                int(fields[2], 16),
                int(fields[3], 16),
                int(fields[4], 16),
            )
    return result


def intel_hex_bounds(path: Path) -> tuple[int, int, int]:
    upper = 0
    minimum: int | None = None
    maximum = 0
    programmed = 0
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        if not line.startswith(":"):
            raise ValueError(f"{path}:{line_number}: invalid Intel HEX")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or sum(record) & 0xFF:
            raise ValueError(f"{path}:{line_number}: bad Intel HEX checksum")
        count = record[0]
        address = (record[1] << 8) | record[2]
        record_type = record[3]
        payload = record[4:4 + count]
        if len(payload) != count:
            raise ValueError(f"{path}:{line_number}: truncated Intel HEX")
        if record_type == 0:
            absolute = upper + address
            minimum = absolute if minimum is None else min(minimum, absolute)
            maximum = max(maximum, absolute + count)
            programmed += count
        elif record_type == 4:
            if count != 2:
                raise ValueError(
                    f"{path}:{line_number}: bad extended address"
                )
            upper = int.from_bytes(payload, "big") << 16
        elif record_type == 1:
            break
    if minimum is None:
        raise ValueError(f"{path}: Intel HEX contains no data")
    return minimum, maximum, programmed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force every object to rebuild under the fixed macro contract",
    )
    parser.add_argument(
        "--prepare-contracts-for-build-dir",
        type=Path,
        help=(
            "Generate the deployable base-CEMP/generation browser contracts "
            "for another product build directory, then exit"
        ),
    )
    parser.add_argument("--product-source-manifest", type=Path)
    parser.add_argument("--generation-manifest", type=Path)
    args = parser.parse_args()
    if args.prepare_contracts_for_build_dir is not None:
        output_build = args.prepare_contracts_for_build_dir
        if not output_build.is_absolute():
            output_build = REPO / output_build
        product_source_manifest = (
            args.product_source_manifest or FROZEN_PRODUCT_SOURCE_MANIFEST
        ).resolve()
        generation_manifest = (
            args.generation_manifest or FROZEN_GENERATION_MANIFEST
        ).resolve()
        if (args.product_source_manifest is None) != (
            args.generation_manifest is None
        ):
            raise RuntimeError(
                "product source and generation manifests must be overridden together"
            )
        contract = generate_product_browser_contract(
            output_build.resolve(),
            product_source_manifest,
            generation_manifest,
        )
        generation = json.loads(
            generation_manifest.read_text(encoding="utf-8")
        )
        generation_end = (
            int(generation["planned_blob_offset"])
            + int(generation["blob_bytes"])
        )
        if (
            FROZEN_CEMP.stat().st_size
            > int(generation["planned_blob_offset"])
            or generation_end > 0x1FE000
        ):
            raise RuntimeError(
                "base CEMP plus generation exceeds the 2 MiB UI data area"
            )
        print(
            json.dumps(
                {
                    "status": "PRODUCT_BROWSER_CONTRACTS_READY",
                    "output_build": str(output_build.resolve()),
                    "base_cemp_bytes": FROZEN_CEMP.stat().st_size,
                    "generation_end": generation_end,
                    "partition_bytes": 0x200000,
                    "browser_page_sha256": normalized_text_sha256(BROWSER_PAGE),
                    "resource_page_sha256": generation["page_sha256"],
                    "resource_id": generation["resource_id"],
                    "contracts": contract,
                    "hardware_contact": 0,
                },
                ensure_ascii=True,
            )
        )
        return 0
    if not MAKE.exists():
        raise RuntimeError(f"make not found: {MAKE}")

    subprocess.run(
        [sys.executable, str(REFRESH_PLAYBOOK_VERIFIER)],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(DISPLAY_ARCHITECTURE_VERIFIER)],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(DISPLAY_ARBITER_HOST_TEST)],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(OVERLAY_COMMIT_HOST_TEST)],
        cwd=REPO,
        check=True,
    )

    source_before = {
        relative(path): sha256(path) for path in IDENTITY_SOURCES
    }
    browser_contract = generate_product_browser_contract()
    command = [str(MAKE), "-C", str(PROJECT)]
    if args.force:
        command.append("-B")
    command.extend([*MAKE_VARIABLES, "-j8", "all"])
    started = time.perf_counter_ns()
    completed = subprocess.run(
        command,
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    elapsed_ms = round(
        (time.perf_counter_ns() - started) / 1_000_000
    )
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    LOG.write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
        newline="\n",
    )
    if completed.returncode != 0 or not ELF.exists() or not HEX.exists():
        raise RuntimeError(
            f"firmware build failed; see {relative(LOG)}"
        )
    source_after = {
        relative(path): sha256(path) for path in IDENTITY_SOURCES
    }
    if source_before != source_after:
        changed = sorted(
            path
            for path in source_after
            if source_before.get(path) != source_after[path]
        )
        raise RuntimeError(
            "firmware inputs changed during the build: "
            + ", ".join(changed)
        )

    size_output = run(
        [str(TOOLCHAIN / "arm-none-eabi-size.exe"), str(ELF)]
    )
    size_fields = size_output.splitlines()[-1].split()
    text_bytes, data_bytes, bss_bytes = map(int, size_fields[:3])
    nm = run([str(TOOLCHAIN / "arm-none-eabi-nm.exe"), "-S", str(ELF)])
    image_sections = sections()
    vector = image_sections[".isr_vector"]
    data = image_sections[".data"]
    load_end = data[2] + data[0]
    hex_minimum, hex_maximum, hex_programmed = intel_hex_bounds(HEX)
    symbols = [
        "comp_ui_asset_generation_mount",
        "comp_ui_asset_sync_serial_feed",
        "companion_epaper_panel_stm32wb_ssd1681_init",
        "comp_recording_resource_pack_mount",
        "companion_watchdog_start",
    ]
    checks = {
        "forced_full_build": args.force,
        "source_snapshot_stable_during_build": (
            source_before == source_after
        ),
        "ota_vector_at_0x08007000": vector[1] == 0x08007000,
        "ota_load_end_before_0x08080000": load_end < 0x08080000,
        "hex_programs_only_ota_app_region": (
            hex_minimum >= 0x08007000 and hex_maximum <= 0x08080000
        ),
        "generation_runtime_linked": symbols[0] in nm,
        "serial_sync_runtime_linked": symbols[1] in nm,
        "real_ssd1681_driver_linked": symbols[2] in nm,
        "recording_resource_runtime_linked": symbols[3] in nm,
        "watchdog_runtime_linked": symbols[4] in nm,
        "internal_state_map_absent": (
            "companion_browser_cemp_state_map" not in nm
        ),
        "recording_fixture_arrays_absent": (
            "COMPANION_G7_SPEECH_PCM" not in nm
            and "COMPANION_OPUS16_FIXTURE_BLOB" not in nm
        ),
        "fixed_build_contract_in_log": all(
            value in LOG.read_text(encoding="utf-8")
            for value in (
                "-DCOMPANION_STM32WB_OTA_APP",
                "-DCOMPANION_USE_FREERTOS=1",
                "-DCOMPANION_EPAPER_PANEL_SSD1681_BRINGUP=1",
                "-DCOMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT=1",
                "-DCOMPANION_EPAPER_SSD1681_HAS_BUSY=1",
                "-DCOMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI=1",
                "-DCOMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_NOP_COUNT=0u",
            )
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "firmware build identity failed: " + ", ".join(failed)
        )

    receipt = {
        "schema": "companion.comp_req_775.firmware_build.v1",
        "status": "FIRMWARE_BUILD_READY",
        "checks": checks,
        "build": {
            "force": args.force,
            "elapsed_ms": elapsed_ms,
            "make_variables": MAKE_VARIABLES,
            "log": relative(LOG),
            "log_sha256": sha256(LOG),
            "browser_base_contract": browser_contract,
        },
        "firmware": {
            "elf": relative(ELF),
            "elf_sha256": sha256(ELF),
            "hex": relative(HEX),
            "hex_sha256": sha256(HEX),
            "text_bytes": text_bytes,
            "data_bytes": data_bytes,
            "bss_bytes": bss_bytes,
            "vector_address": f"0x{vector[1]:08X}",
            "load_end": f"0x{load_end:08X}",
            "hex_minimum_address": f"0x{hex_minimum:08X}",
            "hex_maximum_address_exclusive": f"0x{hex_maximum:08X}",
            "hex_programmed_bytes": hex_programmed,
            "linked_symbols": symbols,
        },
        "source_sha256": source_after,
        "hardware_contact": 0,
        "write_calls": 0,
        "erase_calls": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(
        "PASS_COMP_REQ_775_FIRMWARE_BUILD "
        f"elapsed_ms={elapsed_ms} text={text_bytes} "
        f"elf_sha256={receipt['firmware']['elf_sha256']} "
        "hardware_contact=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
