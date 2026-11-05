#!/usr/bin/env python3
"""Create the offline machine receipt for COMP-REQ-775."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BUILD = (
    REPO
    / "cubeide/Companion_Nucleo_WB55RG_Bringup"
    / "build_comp_req_775_recording_resources"
)
OLD_BUILD = (
    REPO
    / "cubeide/Companion_Nucleo_WB55RG_Bringup"
    / "build_comp_req_775_ui_generation_product"
)
ELF_NAME = "Companion_Nucleo_WB55RG_Bringup.elf"
TOOLCHAIN = Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32."
    "14.3.rel1.win32_1.0.100.202602081740/tools/bin"
)
ARTIFACTS = (
    REPO / ".cache/validation/comp-req-775-incremental-sync"
)
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)
EPAPER = REPO / "app/companion_pendant/epaper"
RECORDING = REPO / "app/companion_pendant/recording"
HOST_TESTS = ARTIFACTS / "host-tests"
RECORDING_ARTIFACTS = (
    REPO / ".cache/validation/comp-req-775-recording-resources"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def command(args: list[str]) -> str:
    return subprocess.run(
        args,
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def find_vsdevcmd() -> Path:
    vswhere = Path(
        "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    )
    if vswhere.exists():
        completed = subprocess.run(
            [
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        installations = [
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        ]
        if installations:
            candidate = (
                Path(installations[0]) / "Common7/Tools/VsDevCmd.bat"
            )
            if candidate.exists():
                return candidate
    raise RuntimeError("Visual Studio C build tools are required")


def compile_host_test(
    name: str,
    sources: list[Path],
) -> tuple[Path, dict]:
    HOST_TESTS.mkdir(parents=True, exist_ok=True)
    executable = HOST_TESTS / f"{name}.exe"
    log = HOST_TESTS / f"{name}-compile.log"
    vsdevcmd = find_vsdevcmd()
    quoted_sources = " ".join(f'"{source}"' for source in sources)
    compile_line = (
        f'call "{vsdevcmd}" -arch=x64 -host_arch=x64 >nul && '
        "cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX "
        f'/I"{EPAPER}" /I"{RECORDING}" '
        f'{quoted_sources} /Fe:"{executable}"'
    )
    completed = subprocess.run(
        f'{os.environ.get("COMSPEC", "cmd.exe")} /d /c {compile_line}',
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    compile_output = completed.stdout + completed.stderr
    log.write_text(compile_output, encoding="utf-8", newline="\n")
    if completed.returncode != 0 or not executable.exists():
        raise RuntimeError(
            f"{name} host compile failed; see {log.relative_to(REPO)}"
        )
    return executable, {
        "compile_exit": completed.returncode,
        "compile_log_sha256": sha256(log),
        "executable_sha256": sha256(executable),
        "source_sha256": {
            str(source.relative_to(REPO)).replace("\\", "/"): sha256(source)
            for source in sources
        },
    }


def elf_text_bytes(elf: Path) -> int:
    output = command([str(TOOLCHAIN / "arm-none-eabi-size.exe"), str(elf)])
    return int(output.splitlines()[-1].split()[0])


def objdump_sections(elf: Path) -> dict[str, tuple[int, int, int]]:
    output = command(
        [str(TOOLCHAIN / "arm-none-eabi-objdump.exe"), "-h", str(elf)]
    )
    sections: dict[str, tuple[int, int, int]] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].isdigit():
            sections[fields[1]] = (
                int(fields[2], 16),
                int(fields[3], 16),
                int(fields[4], 16),
            )
    return sections


def require(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        raise RuntimeError(f"offline gate failed: {name}")


def menu_coverage(manifest: dict) -> dict:
    pattern = re.compile(
        r"^menu_ui_(zh_cn|en)_s(\d+)_o(\d+)_"
        r"(normal|ack_i\d+|processing_i\d+)$"
    )
    states = [
        state for state in manifest["states"]
        if state.get("kind") == "menu_ui"
    ]
    matched = []
    for state in states:
        match = pattern.fullmatch(state["id"])
        if match is not None:
            matched.append(match.groups())

    locales = {}
    for locale in ("zh_cn", "en"):
        locale_states = [groups for groups in matched if groups[0] == locale]
        locales[locale] = {
            "states": len(locale_states),
            "screens": sorted({int(groups[1]) for groups in locale_states}),
            "root_normal_offsets": sorted({
                int(groups[2])
                for groups in locale_states
                if groups[1] == "0" and groups[3] == "normal"
            }),
        }

    return {
        "states": len(states),
        "matched_states": len(matched),
        "normal_states": sum(groups[3] == "normal" for groups in matched),
        "ack_states": sum(groups[3].startswith("ack_") for groups in matched),
        "processing_states": sum(
            groups[3].startswith("processing_") for groups in matched
        ),
        "locales": locales,
    }


def main() -> int:
    checks: dict[str, bool] = {}
    old_elf = OLD_BUILD / ELF_NAME
    new_elf = BUILD / ELF_NAME
    old_text = elf_text_bytes(old_elf)
    new_text = elf_text_bytes(new_elf)
    nm = command(
        [
            str(TOOLCHAIN / "arm-none-eabi-nm.exe"),
            "-S",
            "--size-sort",
            str(new_elf),
        ]
    )
    sections = objdump_sections(new_elf)
    vector = sections[".isr_vector"]
    data = sections[".data"]

    base_source = (
        REPO
        / ".cache/validation/comp-req-774-browser-full-source-pack"
    )
    batch_source = (
        ARTIFACTS
        / "offline-initial-batched/current-source-pack"
    )
    base_manifest = load(base_source / "source-pack-manifest.json")
    batch_manifest = load(batch_source / "source-pack-manifest.json")
    menu = menu_coverage(batch_manifest)
    initial = load(
        ARTIFACTS / "offline-initial-batched/sync-receipt.json"
    )
    noop = load(ARTIFACTS / "direct/sync-receipt.json")
    generation1 = load(ARTIFACTS / "generation-1.json")
    generation2 = load(
        ARTIFACTS / "generation-2-one-frame.json"
    )
    equivalence1 = load(
        ARTIFACTS / "generation-1-equivalence.json"
    )
    equivalence2 = load(
        ARTIFACTS / "generation-2-equivalence.json"
    )
    slow_path = load(ARTIFACTS / "SLOW_PATH_BASELINE.json")
    firmware_build = load(ARTIFACTS / "FIRMWARE_BUILD_READY.json")
    delta_path = load(ARTIFACTS / "DELTA_PATH_READY.json")
    recording_manifest_path = (
        RECORDING_ARTIFACTS / "companion_recording_resources.json"
    )
    recording_pack_path = (
        RECORDING_ARTIFACTS / "companion_recording_resources.crrp"
    )
    recording_manifest = load(recording_manifest_path)

    with urllib.request.urlopen(FIXED_URL, timeout=4) as response:
        http_status = response.status

    generation_exe, generation_build = compile_host_test(
        "test_ui_asset_generation",
        [
            EPAPER / "tests/test_ui_asset_generation.c",
            EPAPER / "ui_asset_generation.c",
            EPAPER / "asset_store.c",
        ],
    )
    serial_exe, serial_build = compile_host_test(
        "test_ui_asset_sync_serial",
        [
            EPAPER / "tests/test_ui_asset_sync_serial.c",
            EPAPER / "ui_asset_sync_serial.c",
            EPAPER / "ui_asset_generation.c",
            EPAPER / "asset_store.c",
        ],
    )
    recording_exe, recording_build = compile_host_test(
        "test_companion_recording_resource_pack",
        [
            RECORDING / "tests/test_companion_recording_resource_pack.c",
            RECORDING / "companion_recording_resource_pack.c",
            EPAPER / "asset_store.c",
        ],
    )
    generation_test = command([str(generation_exe)]).strip()
    serial_test = command([str(serial_exe)]).strip()
    recording_pack_check = command([
        sys.executable,
        str(REPO / "tools/build_companion_recording_resources.py"),
        "--check",
    ]).strip()
    recording_test = command([
        str(recording_exe),
        str(recording_pack_path),
    ]).strip()

    require(checks, "fixed_url_http_200", http_status == 200)
    require(
        checks,
        "batched_export_exact_manifest",
        sha256(base_source / "source-pack-manifest.json")
        == sha256(batch_source / "source-pack-manifest.json"),
    )
    require(
        checks,
        "batched_export_exact_frame_bytes",
        sha256(base_source / "frames.bin")
        == sha256(batch_source / "frames.bin"),
    )
    require(
        checks,
        "strict_200x200_1bpp",
        batch_manifest["invariants"]["all_states_are_5000_bytes"]
        and batch_manifest["invariants"]["all_inputs_binary"],
    )
    require(
        checks,
        "state_count_1557",
        batch_manifest["invariants"]["state_count"] == 1557,
    )
    require(
        checks,
        "initial_offline_plan_under_30s",
        initial["status"] == "PASS_OFFLINE_PLAN"
        and initial["elapsed_ms"] <= 30000,
    )
    require(
        checks,
        "same_package_under_10s_zero_write",
        noop["status"] == "PASS_ALREADY_CURRENT"
        and noop["elapsed_ms"] <= 10000
        and noop["external_flash_write_bytes"] == 0
        and noop["internal_flash_write_bytes"] == 0,
    )
    require(
        checks,
        "one_frame_delta_only_one_payload",
        generation2["new_payload_count"] == 1
        and generation2["new_payload_bytes"] > 0
        and generation2["blob_bytes"] < 40000,
    )
    one_frame_blob_sectors = math.ceil(
        generation2["blob_bytes"] / 4096
    )
    require(
        checks,
        "one_frame_delta_bounded_sectors",
        one_frame_blob_sectors == 10,
    )
    require(
        checks,
        "full_state_equivalence",
        equivalence1["status"]
        == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
        and equivalence2["status"]
        == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
        and equivalence1["states_checked"] == 1557
        and equivalence2["states_checked"] == 1557
        and equivalence1["strict_1bpp"]
        and equivalence2["strict_1bpp"],
    )
    require(
        checks,
        "menu_root_scroll_subpages_equivalence_coverage",
        menu["states"] == 206
        and menu["matched_states"] == 206
        and menu["normal_states"] == 60
        and menu["ack_states"] == 124
        and menu["processing_states"] == 22
        and all(
            locale["states"] == 103
            and locale["screens"] == list(range(13))
            and locale["root_normal_offsets"] == list(range(5))
            for locale in menu["locales"].values()
        ),
    )
    require(
        checks,
        "generation_fault_and_rollback_test",
        generation_test.startswith("PASS_UI_ASSET_GENERATION")
        and "crc_preserved=2" in generation_test
        and "malformed_preserved=2" in generation_test,
    )
    require(
        checks,
        "serial_abort_busy_noop_test",
        serial_test.startswith("PASS_UI_ASSET_SYNC_SERIAL")
        and "noop_write_bytes=0" in serial_test,
    )
    require(
        checks,
        "internal_state_map_removed",
        "companion_browser_cemp_state_map" not in nm,
    )
    require(
        checks,
        "recording_static_pack_current_and_source_equivalent",
        recording_pack_check.startswith(
            "PASS_RECORDING_RESOURCE_BUILD"
        )
        and recording_manifest["status"] == "MACHINE_READY_OFFLINE"
        and recording_manifest["pack"]["sha256"]
        == sha256(recording_pack_path)
        and recording_manifest["pack"]["bytes"]
        == recording_pack_path.stat().st_size
        and [
            (resource["name"], resource["bytes"])
            for resource in recording_manifest["resources"]
        ]
        == [
            ("g7_speech_pcm", 112000),
            ("opus16_fixture", 21723),
        ],
    )
    require(
        checks,
        "recording_static_pack_layout_preserves_14m_recording",
        int(
            recording_manifest["placement"]["recording_resources"][
                "base"
            ],
            16,
        )
        == 0x001DC000
        and int(
            recording_manifest["placement"]["recording_resources"][
                "limit"
            ],
            16,
        )
        == 0x001FD000
        and recording_manifest["placement"]["recording_resources"][
            "used_bytes"
        ]
        <= recording_manifest["placement"]["recording_resources"][
            "capacity_bytes"
        ]
        and int(
            recording_manifest["placement"]["flash_test_scratch"]["base"],
            16,
        )
        == 0x001FD000
        and recording_manifest["placement"]["flash_test_scratch"]["bytes"]
        == 0x1000
        and int(
            recording_manifest["placement"]["flash_test_scratch"]["limit"],
            16,
        )
        == 0x001FE000
        and int(
            recording_manifest["placement"]["recording"]["base"], 16
        )
        == 0x00200000
        and int(
            recording_manifest["placement"]["recording"]["limit"], 16
        )
        == 0x01000000,
    )
    require(
        checks,
        "recording_static_pack_mount_read_crc_and_corruption_test",
        recording_test.startswith(
            "PASS_RECORDING_RESOURCE_PACK"
        )
        and "g7=112000" in recording_test
        and "opus=21723" in recording_test
        and "corruption_rejected=1" in recording_test,
    )
    require(
        checks,
        "recording_fixture_arrays_removed_from_product_elf",
        "COMPANION_G7_SPEECH_PCM" not in nm
        and "COMPANION_OPUS16_FIXTURE_BLOB" not in nm
        and "comp_recording_resource_pack_mount" in nm,
    )
    require(
        checks,
        "internal_flash_net_reduction",
        old_text - new_text >= 125000,
    )
    require(
        checks,
        "ota_vector_and_end_in_bounds",
        vector[1] == 0x08007000
        and data[2] + data[0] < 0x08080000,
    )
    require(
        checks,
        "ui_partition_roots_in_bounds",
        (
            generation1["planned_blob_offset"] >= generation1[
                "base_cemp_bytes"
            ]
            if "base_cemp_bytes" in generation1
            else generation1["planned_blob_offset"] >= 1234827
        )
        and generation1["planned_blob_offset"]
        + generation1["blob_bytes"] <= 0x001DC000
        and generation2["planned_blob_offset"]
        + generation2["blob_bytes"] <= 0x001DC000,
    )
    require(
        checks,
        "offline_evidence_hardware_contact_zero",
        initial["hardware_contact"] == 0
        and noop["hardware_contact"] == 0,
    )
    require(
        checks,
        "slow_path_baseline_complete",
        slow_path["status"] == "PASS_SLOW_PATH_BASELINE"
        and slow_path["hardware_contact"] == 0
        and slow_path["write_calls"] == 0
        and slow_path["erase_calls"] == 0
        and all(slow_path["checks"].values()),
    )
    require(
        checks,
        "slow_path_measures_five_full_ota_images",
        slow_path["old_embedded_application_builds"][
            "complete_ota_image_count"
        ]
        == 5
        and slow_path["old_embedded_application_builds"][
            "representative_links_shared_application_runtime"
        ],
    )
    require(
        checks,
        "slow_path_full_cemp_matches_base",
        slow_path["fresh_full_cemp"]["sha256"]
        == initial["base_cemp_sha256"]
        and slow_path["fresh_full_cemp"]["bytes"]
        == initial["base_cemp_bytes"],
    )
    require(
        checks,
        "firmware_rebuilt_under_fixed_driver_contract",
        firmware_build["status"] == "FIRMWARE_BUILD_READY"
        and firmware_build["hardware_contact"] == 0
        and firmware_build["write_calls"] == 0
        and firmware_build["erase_calls"] == 0
        and all(firmware_build["checks"].values())
        and firmware_build["firmware"]["elf_sha256"] == sha256(new_elf)
        and firmware_build["firmware"]["hex_sha256"]
        == sha256(new_elf.with_suffix(".hex")),
    )
    require(
        checks,
        "firmware_build_inputs_still_current",
        all(
            sha256(REPO / relative) == expected
            for relative, expected
            in firmware_build["source_sha256"].items()
        )
        and firmware_build["build"]["log_sha256"]
        == sha256(REPO / firmware_build["build"]["log"]),
    )
    require(
        checks,
        "fresh_delta_rebuild_is_one_frame_only",
        delta_path["status"] == "PASS_DELTA_PATH"
        and delta_path["hardware_contact"] == 0
        and delta_path["internal_flash_write_bytes"] == 0
        and all(delta_path["checks"].values())
        and delta_path["one_frame"]["blob_bytes"]
        == generation2["blob_bytes"]
        and delta_path["one_frame"]["new_payload_bytes"]
        == generation2["new_payload_bytes"],
    )

    receipt = {
        "schema": "companion.comp_req_775.offline_machine.v1",
        "status": "PASS_OFFLINE_HARDWARE_PENDING",
        "checks": checks,
        "fixed_url": FIXED_URL,
        "http_status": http_status,
        "page_sha256": batch_manifest["source"]["page_sha256"],
        "base_cemp_sha256": initial["base_cemp_sha256"],
        "resource_id": generation1["resource_id"],
        "menu_equivalence_coverage": menu,
        "generation": {
            "initial_blob_bytes": generation1["blob_bytes"],
            "one_frame_blob_bytes": generation2["blob_bytes"],
            "one_frame_new_payload_bytes": generation2[
                "new_payload_bytes"
            ],
            "one_frame_blob_sectors": one_frame_blob_sectors,
            "one_frame_changed_state_id": delta_path["one_frame"][
                "changed_state_id"
            ],
            "one_frame_builder_elapsed_ms": delta_path["one_frame"][
                "builder_elapsed_ms"
            ],
        },
        "host_tests": {
            "generation": generation_build | {"stdout": generation_test},
            "serial": serial_build | {"stdout": serial_test},
            "recording_resources": recording_build | {
                "stdout": recording_test,
                "pack_check_stdout": recording_pack_check,
            },
        },
        "performance_ms": {
            "batched_fresh_export": initial["source_pack"]["elapsed_ms"],
            "full_cemp_generation": slow_path["fresh_full_cemp"][
                "total_elapsed_ms"
            ],
            "old_loader_to_four_chunk_failure": slow_path[
                "old_hardware_runtime"
            ]["four_chunk_attempt"]["loader_write_to_failure_ms"],
            "old_loader_asset_product_cycle": slow_path[
                "old_hardware_runtime"
            ]["completed_loader_asset_product_cycle"][
                "loader_write_to_machine_ready_ms"
            ],
            "initial_offline_plan": initial["elapsed_ms"],
            "same_package_noop": noop["elapsed_ms"],
        },
        "slow_path_baseline": {
            "sha256": sha256(
                ARTIFACTS / "SLOW_PATH_BASELINE.json"
            ),
            "complete_ota_image_count": slow_path[
                "old_embedded_application_builds"
            ]["complete_ota_image_count"],
            "total_internal_flash_programmed_bytes": slow_path[
                "old_write_amplification"
            ]["total_internal_flash_programmed_bytes"],
            "historical_external_cemp_bytes": slow_path[
                "old_write_amplification"
            ]["external_cemp_bytes"],
        },
        "firmware": {
            "old_text_bytes": old_text,
            "new_text_bytes": new_text,
            "net_internal_flash_saved": old_text - new_text,
            "elf_sha256": sha256(new_elf),
            "hex_sha256": sha256(new_elf.with_suffix(".hex")),
            "vector_address": f"0x{vector[1]:08X}",
            "load_end": f"0x{data[2] + data[0]:08X}",
            "state_map_linked": False,
            "build_receipt_sha256": sha256(
                ARTIFACTS / "FIRMWARE_BUILD_READY.json"
            ),
            "recording_diagnostic_resources": {
                "pack_sha256": recording_manifest["pack"]["sha256"],
                "pack_bytes": recording_manifest["pack"]["bytes"],
                "external_offset": "0x001DC000",
                "external_limit": "0x001FD000",
                "flash_test_scratch": "0x001FD000..0x001FE000",
                "internal_arrays_linked": False,
            },
        },
        "hardware_contact": 0,
        "remaining_gates": [
            "install this firmware once",
            "real UART external-NOR sync and readback",
            "ordinary-reset first frame and SSD1681 BUSY/fault logs",
            "final canonical Chinese operator comparison",
        ],
    }
    output = ARTIFACTS / "OFFLINE_READY.json"
    output.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(
        "PASS_COMP_REQ_775_OFFLINE "
        f"checks={len(checks)} no_op_ms={noop['elapsed_ms']} "
        f"flash_saved={old_text - new_text} hardware_contact=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
