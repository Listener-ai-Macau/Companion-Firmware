#!/usr/bin/env python3
"""Aggregate offline evidence for the COMP-REQ-775 resource OTA split."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EPAPER = REPO / "app/companion_pendant/epaper"
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
TOOLCHAIN = Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32."
    "14.3.rel1.win32_1.0.100.202602081740/tools/bin"
)
APP_BUILD = (
    REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup/"
    "build_comp_req_775_resource_ota_reserve"
)
APP_ELF = APP_BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
LOADER = (
    REPO / "tools/external_loader/wb55_spi1_nor/build/"
    "Companion_WB55_SPI1_NOR_UI_2MiB.stldr"
)
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"VERIFY_RESOURCE_OTA_FAILED: {message}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_vsdevcmd() -> Path:
    vswhere = Path(
        "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    )
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
    candidate = (
        Path(completed.stdout.strip()) / "Common7/Tools/VsDevCmd.bat"
    )
    require(candidate.exists(), "Visual Studio C compiler is missing")
    return candidate


def compile_and_run_target_test() -> dict[str, object]:
    output_dir = ARTIFACTS / "offline-tests"
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = output_dir / "test_ui_asset_ota_target.exe"
    log = output_dir / "test_ui_asset_ota_target-compile.log"
    sources = [
        EPAPER / "tests/test_ui_asset_ota_target.c",
        EPAPER / "ui_asset_ota_target.c",
        EPAPER / "ui_asset_generation.c",
        EPAPER / "asset_store.c",
    ]
    quoted_sources = " ".join(f'"{source}"' for source in sources)
    line = (
        f'call "{find_vsdevcmd()}" -arch=x64 -host_arch=x64 >nul && '
        "cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX "
        f'/I"{EPAPER}" {quoted_sources} /Fe:"{executable}"'
    )
    completed = subprocess.run(
        f'{os.environ.get("COMSPEC", "cmd.exe")} /d /c {line}',
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    log.write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
        newline="\n",
    )
    require(completed.returncode == 0 and executable.exists(),
            "resource OTA target host compile failed")
    test = subprocess.run(
        [str(executable)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    require(
        test.startswith("PASS_UI_ASSET_OTA_TARGET")
        and "noop_write_bytes=0" in test
        and "offset_mismatch_erase_count=0" in test
        and "crc_preserved=1" in test
        and "abort_preserved=1" in test,
        "resource OTA target behavior test failed",
    )
    return {
        "output": test,
        "compile_log_sha256": sha256(log),
        "executable_sha256": sha256(executable),
        "source_sha256": {
            str(path.relative_to(REPO)).replace("\\", "/"): sha256(path)
            for path in sources
        },
    }


def app_layout() -> dict[str, object]:
    require(APP_ELF.exists(), "normal OTA App ELF is missing")
    completed = subprocess.run(
        [str(TOOLCHAIN / "arm-none-eabi-objdump.exe"), "-h", str(APP_ELF)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    sections: dict[str, tuple[int, int, int]] = {}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].isdigit():
            sections[fields[1]] = (
                int(fields[2], 16),
                int(fields[3], 16),
                int(fields[4], 16),
            )
    require(".isr_vector" in sections, "App vector section is missing")
    vector = sections[".isr_vector"][1]
    load_end = max(
        lma + size
        for size, _vma, lma in sections.values()
        if 0x08000000 <= lma < 0x08100000 and size > 0
    )
    require(vector == 0x08007000, "App vector moved outside OTA contract")
    require(load_end <= 0x08080000, "App load image exceeds OTA partition")
    target_object = APP_BUILD / "ui_asset_ota_target.o"
    require(target_object.exists(), "resource target was not compiled")
    return {
        "elf": str(APP_ELF.relative_to(REPO)).replace("\\", "/"),
        "elf_sha256": sha256(APP_ELF),
        "vector": f"0x{vector:08X}",
        "load_end": f"0x{load_end:08X}",
        "resource_target_object_sha256": sha256(target_object),
    }


def loader_contract() -> dict[str, object]:
    sys.path.insert(
        0, str(REPO / "tools/external_loader/wb55_spi1_nor")
    )
    from verify_loader import parse_elf

    return parse_elf(LOADER)


def stlink_transaction_test() -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(
                REPO
                / "tools/faraday_upper_art/"
                "test_sync_companion_ui_assets_stlink.py"
            ),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    require(
        receipt["status"] == "MACHINE_READY"
        and receipt["hardware_contact"] == 0
        and all(receipt["checks"].values()),
        "ST-LINK transaction fault injection failed",
    )
    return receipt


def stlink_hardware_lock_guard() -> bool:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/sync_companion_ui_assets_stlink.py"),
            "--bundle",
            str(ARTIFACTS / "resource-ota/generation-1.cuot"),
            "--allow-hardware",
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = result.stdout + result.stderr
    require(
        result.returncode != 0
        and "must run inside the Companion-WB55 workflow lock" in output,
        "ST-LINK hardware mode did not fail closed on a missing workflow lock",
    )
    return True


def stlink_inherited_lock_guards() -> dict[str, bool]:
    evidence_path = ARTIFACTS / "fake-held-lock-for-offline-test.json"
    run_id = "offline-lock-guard-test"
    evidence_path.write_text(
        json.dumps(
            {
                "status": "HELD",
                "resource": "Companion-WB55",
                "run_id": run_id,
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["COMPANION_WB55_LOCK_RUN_ID"] = run_id
    env["COMPANION_WB55_LOCK_EVIDENCE_PATH"] = str(evidence_path)
    env.pop("COMPANION_WB55_SWD_MUTEX_HELD", None)
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools/sync_companion_ui_assets_stlink.py"),
                "--bundle",
                str(ARTIFACTS / "resource-ota/generation-1.cuot"),
                "--allow-hardware",
                "--workflow-lock-held",
                "--swd-mutex-held",
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
    finally:
        evidence_path.unlink(missing_ok=True)
    output = result.stdout + result.stderr
    require(
        result.returncode != 0
        and "inherited SWD mutex acknowledgement is not active" in output,
        "inherited SWD mutex guard did not fail before hardware contact",
    )
    return {
        "workflow_lock_evidence_required": True,
        "inherited_swd_mutex_environment_required": True,
    }


def external_loader_runner_check_only() -> dict[str, object]:
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(REPO / "tools/run_comp_req_775_external_loader_sync.ps1"),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    require(
        receipt["status"] == "CHECK_ONLY"
        and receipt["hardware_contact"] == 0
        and receipt["preflight"]["http_status"] == 200
        and receipt["preflight"]["page_sha256"]
        == receipt["preflight"]["http_body_sha256"]
        and receipt["preflight"]["existing_app_ota_loader_unchanged"]
        and receipt["preflight"]["external_loader_exact_2mib"]
        and receipt["preflight"]["recording_resource_pack_sha256"]
        == sha256(
            REPO
            / ".cache/validation/comp-req-775-recording-resources/"
            "companion_recording_resources.crrp"
        ),
        "External Loader runner check-only preflight failed",
    )
    return receipt


def boot_log_verifier_test() -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(
                REPO
                / "tools/faraday_upper_art/"
                "test_comp_req_775_boot_log_verifier.py"
            ),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    require(
        receipt["status"] == "MACHINE_READY"
        and receipt["hardware_contact"] == 0
        and all(receipt["checks"].values()),
        "ordinary-reset boot-log verifier fixtures failed",
    )
    return receipt


def menu_log_verifier_test() -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(
                REPO
                / "tools/faraday_upper_art/"
                "test_comp_req_775_menu_log_verifier.py"
            ),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    require(
        receipt["status"] == "MACHINE_READY"
        and receipt["hardware_contact"] == 0
        and all(receipt["checks"].values()),
        "menu-boundary log verifier fixtures failed",
    )
    return receipt


def performance_chain_runner_checks() -> dict[str, object]:
    root = ARTIFACTS / "resource-ota"
    cases = [
        (
            "probe",
            [
                "-BundlePath",
                str(root / "generation-2.cuot"),
                "-PerformanceProbe",
            ],
            False,
        ),
        (
            "restore",
            [
                "-BundlePath",
                str(root / "generation-3-restore.cuot"),
                "-CaptureMenuBoundary",
            ],
            True,
        ),
        (
            "final_noop",
            [
                "-BundlePath",
                str(root / "generation-3-noop.cuot"),
            ],
            True,
        ),
    ]
    receipts: dict[str, object] = {}
    for name, arguments, fixed_target in cases:
        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(
                    REPO
                    / "tools/run_comp_req_775_external_loader_sync.ps1"
                ),
                *arguments,
            ],
            cwd=REPO,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        receipt = json.loads(result.stdout)
        require(
            receipt["status"] == "CHECK_ONLY"
            and receipt["hardware_contact"] == 0
            and receipt["preflight"]["fixed_page_target"] is fixed_target,
            f"{name} runner preflight failed",
        )
        receipts[name] = receipt
    require(
        receipts["probe"]["performance_probe"] is True
        and receipts["probe"]["capture_menu_boundary"] is False
        and receipts["restore"]["performance_probe"] is False
        and receipts["restore"]["capture_menu_boundary"] is True,
        "performance probe/restore runner roles are not isolated",
    )
    return receipts


def acceptance_controller_check_only() -> dict[str, object]:
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(
                REPO
                / "tools/run_comp_req_775_external_loader_acceptance.ps1"
            ),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    stages = receipt["stages"]
    require(
        receipt["status"] == "CHECK_ONLY"
        and receipt["hardware_contact"] == 0
        and stages["initial"]["preflight"]["fixed_page_target"]
        and stages["probe"]["performance_probe"]
        and not stages["probe"]["capture_menu_boundary"]
        and stages["restore"]["capture_menu_boundary"]
        and stages["restore"]["preflight"]["fixed_page_target"]
        and stages["noop"]["preflight"]["fixed_page_target"],
        "full External Loader acceptance controller preflight failed",
    )
    noop_result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(
                REPO
                / "tools/run_comp_req_775_external_loader_acceptance.ps1"
            ),
            "-ResumePhase",
            "noop",
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    noop_receipt = json.loads(noop_result.stdout)
    require(
        noop_receipt["status"] == "CHECK_ONLY"
        and noop_receipt["hardware_contact"] == 0
        and noop_receipt["resume_phase"] == "noop"
        and list(noop_receipt["stages"]) == ["noop"],
        "final no-op-only resume preflight failed",
    )
    receipt["noop_resume"] = noop_receipt
    return receipt


def hardware_summary_verifier_test() -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(
                REPO
                / "tools/faraday_upper_art/"
                "test_comp_req_775_hardware_summary.py"
            ),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    receipt = json.loads(result.stdout)
    require(
        receipt["status"] == "MACHINE_READY"
        and receipt["hardware_contact"] == 0
        and all(receipt["checks"].values()),
        "hardware-summary verifier fault injection failed",
    )
    return receipt


def main() -> None:
    offline_fixed = load(ARTIFACTS / "OFFLINE_READY.json")
    generation = load(
        ARTIFACTS / "resource-ota/generation-2-receipt.json"
    )
    delta = load(
        ARTIFACTS / "stlink-sync/generation-2-dry-run.json"
    )
    noop = load(ARTIFACTS / "stlink-sync/noop-dry-run.json")
    restore = load(
        ARTIFACTS / "stlink-sync/generation-3-restore-dry-run.json"
    )
    final_noop = load(
        ARTIFACTS / "stlink-sync/generation-3-noop-dry-run.json"
    )
    static_pack_path = (
        REPO
        / ".cache/validation/comp-req-775-recording-resources/"
        "companion_recording_resources.crrp"
    )
    static_pack = static_pack_path.read_bytes()
    generation_one = (
        ARTIFACTS / "stlink-sync/synthetic-generation-1.bin"
    ).read_bytes()
    static_region = generation_one[0x001DC000:0x001FD000]
    require(
        len(static_pack) == 133851
        and static_region[: len(static_pack)] == static_pack
        and static_region[len(static_pack) :] == bytes(
            [0xFF]
        ) * (len(static_region) - len(static_pack)),
        "generation-1 partition does not contain the exact CRRP pack",
    )
    require(
        generation["status"] == "MACHINE_READY"
        and generation["format"]["magic"] == "CUOT"
        and generation["bundle"]["bytes"] == 38604
        and generation["generation"]["blob_bytes"] == 38508,
        "real generation-2 CUOT receipt is invalid",
    )
    require(
        delta["status"] == "MACHINE_READY"
        and delta["hardware_contact"] == 0
        and delta["active_generation_before"] == 1
        and delta["active_generation_after"] == 2
        and len(delta["changed_data_sectors"]) == 10
        and delta["inactive_root_last"] == "0x1FF000"
        and delta["external_flash_write_bytes"] == 45056
        and delta["internal_flash_write_bytes"] == 0
        and delta["recording_partition_write_bytes"] == 0
        and delta["recording_resource_pack"]["pack_sha256"]
        == sha256(static_pack_path)
        and delta["recording_resource_pack"]["changed_sector_count"] == 0,
        "single-frame ST-LINK sector plan is invalid",
    )
    require(
        noop["status"] == "MACHINE_READY"
        and noop["hardware_contact"] == 0
        and noop["noop"] is True
        and noop["commands"] == []
        and noop["external_flash_write_bytes"] == 0
        and noop["internal_flash_write_bytes"] == 0
        and noop["recording_resource_pack"]["changed_sector_count"] == 0,
        "same-resource zero-write plan is invalid",
    )
    require(
        restore["status"] == "MACHINE_READY"
        and restore["hardware_contact"] == 0
        and restore["active_generation_before"] == 2
        and restore["active_generation_after"] == 3
        and len(restore["changed_data_sectors"]) == 10
        and restore["inactive_root_last"] == "0x1FE000"
        and restore["external_flash_write_bytes"] == 45056
        and restore["target_root"]["resource_id"]
        == offline_fixed["resource_id"],
        "generation-3 fixed-page restore plan is invalid",
    )
    require(
        final_noop["status"] == "MACHINE_READY"
        and final_noop["hardware_contact"] == 0
        and final_noop["active_generation_before"] == 3
        and final_noop["active_generation_after"] == 3
        and final_noop["noop"] is True
        and final_noop["external_flash_write_bytes"] == 0
        and final_noop["internal_flash_write_bytes"] == 0,
        "generation-3 final no-op plan is invalid",
    )
    ota_loader_status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "cubeide/Companion_BLE_Ota_Loader",
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    require(ota_loader_status == "", "existing App OTA Loader was modified")
    try:
        with urllib.request.urlopen(FIXED_URL, timeout=4) as response:
            http_status = response.status
    except OSError:
        http_status = 0

    transaction = stlink_transaction_test()
    lock_guard = stlink_hardware_lock_guard()
    inherited_lock_guards = stlink_inherited_lock_guards()
    runner_check = external_loader_runner_check_only()
    boot_log_test = boot_log_verifier_test()
    menu_log_test = menu_log_verifier_test()
    performance_runner_checks = performance_chain_runner_checks()
    acceptance_controller = acceptance_controller_check_only()
    hardware_summary_test = hardware_summary_verifier_test()
    receipt = {
        "schema": "companion.comp_req_775.resource_ota_offline.v1",
        "status": "MACHINE_READY_OFFLINE",
        "checks": {
            "existing_app_ota_loader_unchanged": True,
            "resource_ota_target_fault_injection": True,
            "resource_ota_same_generation_zero_write": True,
            "resource_ota_wrong_base_rejected_before_write": True,
            "resource_ota_wrong_offset_rejected_before_erase": True,
            "resource_ota_crc_and_abort_preserve_old_generation": True,
            "external_loader_exact_2mib": True,
            "external_loader_recording_partition_unaddressable": True,
            "single_frame_blob_then_root_last": True,
            "stlink_root_last_fault_injection": True,
            "stlink_exact_recording_resource_pack_in_2mib": True,
            "stlink_static_resource_partial_write_preserves_ui": True,
            "stlink_static_resource_same_pack_zero_write": True,
            "stlink_hardware_lock_required_before_contact": lock_guard,
            "stlink_inherited_lock_evidence_required": all(
                inherited_lock_guards.values()
            ),
            "external_loader_runner_fixed_page_preflight": True,
            "ordinary_reset_boot_log_verifier_fault_injection": True,
            "menu_boundary_log_verifier_fault_injection": True,
            "one_frame_probe_exact_fixed_page_restore_chain": True,
            "final_restored_resource_zero_write_plan": True,
            "single_command_hardware_acceptance_controller_preflight": True,
            "hardware_summary_cross_stage_fault_injection": True,
            "normal_app_ota_layout_preserved": True,
            "fixed_browser_http_200": http_status == 200,
        },
        "app": app_layout(),
        "external_loader": loader_contract(),
        "target_test": compile_and_run_target_test(),
        "tooling_sha256": {
            "tools/sync_companion_ui_assets_stlink.py": sha256(
                REPO / "tools/sync_companion_ui_assets_stlink.py"
            ),
            "tools/faraday_upper_art/build_ui_asset_ota_bundle.py": sha256(
                REPO
                / "tools/faraday_upper_art/build_ui_asset_ota_bundle.py"
            ),
            "tools/external_loader/wb55_spi1_nor/loader.c": sha256(
                REPO / "tools/external_loader/wb55_spi1_nor/loader.c"
            ),
            "tools/run_comp_req_775_external_loader_sync.ps1": sha256(
                REPO / "tools/run_comp_req_775_external_loader_sync.ps1"
            ),
            "tools/run_comp_req_775_external_loader_acceptance.ps1": sha256(
                REPO
                / "tools/run_comp_req_775_external_loader_acceptance.ps1"
            ),
            "tools/faraday_upper_art/verify_comp_req_775_boot_log.py": sha256(
                REPO
                / "tools/faraday_upper_art/"
                "verify_comp_req_775_boot_log.py"
            ),
            "tools/faraday_upper_art/verify_comp_req_775_menu_log.py": sha256(
                REPO
                / "tools/faraday_upper_art/"
                "verify_comp_req_775_menu_log.py"
            ),
            "tools/faraday_upper_art/verify_comp_req_775_hardware_summary.py": (
                sha256(
                    REPO
                    / "tools/faraday_upper_art/"
                    "verify_comp_req_775_hardware_summary.py"
                )
            ),
        },
        "cuot": generation,
        "stlink_single_frame_plan": delta,
        "stlink_noop_plan": noop,
        "stlink_fixed_page_restore_plan": restore,
        "stlink_final_noop_plan": final_noop,
        "stlink_transaction_fault_injection": transaction,
        "stlink_lock_guards": inherited_lock_guards,
        "external_loader_runner_check_only": runner_check,
        "boot_log_verifier_test": boot_log_test,
        "menu_log_verifier_test": menu_log_test,
        "performance_chain_runner_check_only": performance_runner_checks,
        "acceptance_controller_check_only": acceptance_controller,
        "hardware_summary_verifier_test": hardware_summary_test,
        "fixed_browser": {
            "url": FIXED_URL,
            "http_status": http_status,
        },
        "product_resource_gatt": {
            "binding_enabled": False,
            "reason": (
                "requires scheduled asynchronous sector preparation; "
                "must not block a BLE attribute callback"
            ),
            "existing_app_ota_behavior_changed": False,
        },
        "hardware_contact": 0,
        "write_calls": 0,
        "erase_calls": 0,
    }
    output = ARTIFACTS / "RESOURCE_OTA_OFFLINE_READY.json"
    output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
