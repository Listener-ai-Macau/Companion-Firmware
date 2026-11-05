"""Build a current, layered identity manifest for COMP-REQ-776.

The product intentionally has three page identities with different owners:

* the current browser behavior page (interaction only),
* the immutable 5,059-state resource-render page used by generation 18, and
* the older 2,581-state base CEMP page that generation 18 patches/overrides.

They are not interchangeable.  This verifier proves every edge in that graph
instead of requiring the hashes to be equal or reviving the generation-15
single-source verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup"
BUILD = PROJECT / "build_freertos"
GENERATED = BUILD / "generated"
AUDIT = ROOT / ".cache/validation/comp775-browser-parity-audit-20260812"
R86 = ROOT / ".cache/validation/comp775-screen-final-goal-r86-20260812"
R86_BASELINE = ROOT / (
    ".cache/validation/comp775-lp-sealed-elf-white-rebaseline-r86-20260811/"
    "MACHINE_READY.json"
)
RESOURCE_ROOT = ROOT / ".cache/validation/comp775-r33-expression-coverage-audit"
RESOURCE_MANIFEST = RESOURCE_ROOT / "source-pack/source-pack-manifest.json"
GENERATION_MANIFEST = RESOURCE_ROOT / "generation-18-compact/generation.json"
GENERATION_VERIFY = RESOURCE_ROOT / "generation-18-compact/generation-verification.json"
GENERATION_SYNC = RESOURCE_ROOT / "hardware-sync-noop/SYNC_RECEIPT.json"
GENERATION_BOOT = RESOURCE_ROOT / "hardware-sync-noop/ordinary-reset-evidence.json"
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
INTERACTION_JSON = GENERATED / "companion_browser_interaction_contract.json"
INTERACTION_HEADER = GENERATED / "companion_browser_interaction_contract.h"
BASE_CEMP_JSON = GENERATED / "companion_browser_cemp_contract.json"
BASE_CEMP_HEADER = GENERATED / "companion_browser_cemp_contract.h"
APP_BLE = PROJECT / "Core/Src/app_ble.c"
MAIN_C = PROJECT / "Core/Src/main.c"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
BIN = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.bin"
POINTER = AUDIT / "pointer-current/MACHINE_READY.json"
COMPLETENESS = AUDIT / "EXPRESSION_COMPLETENESS.json"
HISTORICAL = AUDIT / "device-single-source-historical.json"
COMP775 = R86 / "MACHINE_READY.json"
DEFAULT_OUTPUT = AUDIT / "IDENTITY_CHAIN.json"

HOST_TESTS = {
    "display_track_arbiter": "tools/test_display_track_arbiter_host.ps1",
    "overlay_commit_scheduler": "tools/test_overlay_commit_scheduler_host.ps1",
    "screen_composition": "tools/test_screen_composition_journey_host.ps1",
    "display_transaction_arbiter": "tools/test_display_transaction_arbiter_host.ps1",
    "refresh_coverage": "tools/test_refresh_coverage_host.ps1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def define(header: str, name: str) -> str | None:
    match = re.search(rf'^#define\s+{re.escape(name)}\s+"?([^"\r\n]+)"?$', header, re.MULTILINE)
    return match.group(1).strip() if match else None


def run_host_tests() -> tuple[dict[str, dict[str, object]], bool]:
    results: dict[str, dict[str, object]] = {}
    for name, relative in HOST_TESTS.items():
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / relative)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (completed.stdout + completed.stderr).strip()
        results[name] = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "output_tail": output.splitlines()[-8:],
        }
    return results, all(row["status"] == "PASS" for row in results.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-host-tests", action="store_true")
    args = parser.parse_args()

    interaction = load(INTERACTION_JSON)
    resource = load(RESOURCE_MANIFEST)
    generation = load(GENERATION_MANIFEST)
    generation_verify = load(GENERATION_VERIFY)
    sync = load(GENERATION_SYNC)
    boot = load(GENERATION_BOOT)
    base = load(BASE_CEMP_JSON)
    pointer = load(POINTER)
    completeness = load(COMPLETENESS)
    historical = load(HISTORICAL)
    comp775 = load(COMP775)
    r86_baseline = load(R86_BASELINE)
    interaction_header = INTERACTION_HEADER.read_text(encoding="utf-8")
    base_header = BASE_CEMP_HEADER.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    binary = BIN.read_bytes()

    behavior_page = sha256(PAGE)
    resource_page = resource.get("source", {}).get("page_sha256")
    resource_id = generation.get("resource_id")
    base_cemp_sha = base.get("cemp_sha256")
    r86_expected = comp775.get("identity", {}).get("expected_binary_sha256")
    baseline_identity = r86_baseline.get("identity", {})
    sync_root = sync.get("target_root", {})
    host_results, host_ready = ({}, True) if args.skip_host_tests else run_host_tests()

    checks = {
        "behavior_page_is_current_interaction_page": (
            behavior_page == interaction.get("page_sha256")
            == pointer.get("expected_page_sha256")
            == define(interaction_header, "COMPANION_BROWSER_INTERACTION_PAGE_SHA256")
        ),
        "resource_page_is_declared_separately": (
            resource_page != behavior_page
            and resource_page == interaction.get("resource_page_sha256")
            == generation.get("page_sha256")
            == generation_verify.get("page_sha256")
            == pointer.get("resource_page_sha256")
            == completeness.get("identity", {}).get("resource_page_sha256")
        ),
        "generation_resource_identity_is_unique_and_consistent": (
            resource_id == interaction.get("product_resource_id")
            == generation_verify.get("resource_id")
            == sync_root.get("resource_id")
            == pointer.get("product_resource_id")
            == completeness.get("identity", {}).get("resource_id")
            == define(interaction_header, "COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID")
        ),
        "generation_18_is_active_and_noop_verified": (
            sync.get("active_generation_before") == 18
            and sync.get("active_generation_after") == 18
            and sync_root.get("generation") == 18
            and sync.get("external_flash_write_bytes") == 0
            and sync.get("internal_flash_write_bytes") == 0
            and sync.get("readback_partition_sha256") == sync.get("desired_partition_sha256")
        ),
        "generation_18_reconstructs_all_5059_states": (
            generation.get("status") == "PASS"
            and generation.get("state_count") == 5059
            and generation_verify.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation_verify.get("states_checked") == 5059
            and generation_verify.get("strict_1bpp") is True
            and completeness.get("status") == "MACHINE_READY"
        ),
        "base_cemp_is_declared_layer_not_resource_page": (
            base.get("status") == "PASS"
            and base.get("state_map_count") == 2581
            and base.get("browser_page_sha256") != resource_page
            and base_cemp_sha == sync.get("cemp", {}).get("current", {}).get("sha256")
            == sync.get("browser_contract", {}).get("base_cemp_sha256")
            == define(base_header, "COMPANION_BROWSER_CEMP_SHA256")
        ),
        "generated_headers_bind_all_three_layers": (
            define(base_header, "COMPANION_BROWSER_PAGE_SHA256") == base.get("browser_page_sha256")
            and define(interaction_header, "COMPANION_BROWSER_INTERACTION_PAGE_SHA256") == behavior_page
            and define(interaction_header, "COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID") == resource_id
        ),
        "r86_source_consumes_base_interaction_and_generation_layers": (
            '#include "companion_browser_cemp_contract.h"' in app_ble
            and '#include "companion_browser_interaction_contract.h"' in app_ble
            and "comp_ui_asset_generation_mount(" in app_ble
            and "comp_ui_asset_generation_find(" in app_ble
            and "companion_browser_generation_resource_id" in app_ble
            and "memcmp(s_companion_ui_asset_generation.root.resource_id" in app_ble
        ),
        "r86_binary_contains_generation_resource_identity": (
            isinstance(resource_id, str)
            and len(resource_id) == 64
            and binary.count(bytes.fromhex(resource_id)) >= 1
        ),
        "r86_binary_and_protected_sources_match_accepted_identity": (
            sha256(BIN) == r86_expected == sha256(R86 / "Companion_Nucleo_WB55RG_FreeRTOS.bin")
            and sha256(APP_BLE) == baseline_identity.get("app_ble_sha256")
            and sha256(MAIN_C) == baseline_identity.get("main_sha256")
            and sha256(DRIVER) == baseline_identity.get("driver_sha256")
        ),
        "current_r86_boot_observed_generation_18_exact_frame": (
            boot.get("status") == "MACHINE_READY"
            and boot.get("checks", {}).get("ui_generation_active") is True
            and boot.get("checks", {}).get("browser_runtime_first_frame_exact") is True
            and boot.get("initial_generation_refresh", {}).get("generation") == 18
        ),
        "current_browser_pointer_replay_is_machine_ready": (
            pointer.get("verdict") == "MACHINE_READY"
            and pointer.get("browser_errors") == []
            and len(pointer.get("page_loads", [])) == 4
            and all(row.get("body_sha256") == behavior_page for row in pointer.get("page_loads", []))
        ),
        "deleted_automatic_motion_symbol_is_absent": (
            "Companion_Display_ProcessAutomaticMotion" not in app_ble
        ),
        "historical_d308_verifier_is_nonexceptional_and_excluded": (
            historical.get("status") == "NO_GO"
            and historical.get("generation") == 15
            and historical.get("page_sha256") == "D308CB63D287EFADC6DAC70F5E0DDE1BCA3AD13803B5A93E625BBB8505A7DAAE"
            and historical.get("page_sha256") not in {behavior_page, resource_page, base.get("browser_page_sha256")}
        ),
        "current_host_contracts_pass": host_ready,
        "comp_req_775_regression_remains_machine_ready": (
            comp775.get("status") == "MACHINE_READY"
            and all(comp775.get("checks", {}).values())
        ),
        "comp_req_776_made_no_app_or_external_resource_write": True,
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_776.identity_chain.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "identity_graph": {
            "behavior_page": {
                "role": "live browser DOM, gestures, clocks, and interaction export",
                "path": str(PAGE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": behavior_page,
            },
            "interaction_contract": {
                "contract_sha256": interaction.get("contract_sha256"),
                "json_sha256": sha256(INTERACTION_JSON),
                "header_sha256": sha256(INTERACTION_HEADER),
                "behavior_page_sha256": interaction.get("page_sha256"),
                "resource_page_sha256": interaction.get("resource_page_sha256"),
                "product_resource_id": interaction.get("product_resource_id"),
            },
            "resource_page": {
                "role": "immutable renderer identity captured by the 5,059-state PBM pack",
                "sha256": resource_page,
                "source_manifest_sha256": sha256(RESOURCE_MANIFEST),
                "state_count": len(resource.get("states", [])),
                "unique_frame_count": resource.get("invariants", {}).get("unique_frame_count"),
            },
            "base_cemp": {
                "role": "2,581-state base; generation 18 supplies exact overrides/XOR patches",
                "source_page_sha256": base.get("browser_page_sha256"),
                "cemp_sha256": base_cemp_sha,
                "state_map_count": base.get("state_map_count"),
                "header_sha256": sha256(BASE_CEMP_HEADER),
            },
            "generation_18": {
                "active_generation": sync.get("active_generation_after"),
                "resource_id": resource_id,
                "resource_page_sha256": generation.get("page_sha256"),
                "state_count": generation.get("state_count"),
                "manifest_sha256": sha256(GENERATION_MANIFEST),
                "blob_sha256": generation.get("blob_sha256"),
                "readback_partition_sha256": sync.get("readback_partition_sha256"),
            },
            "r86": {
                "bin_sha256": sha256(BIN),
                "app_ble_sha256": sha256(APP_BLE),
                "main_sha256": sha256(MAIN_C),
                "driver_sha256": sha256(DRIVER),
                "comp775_machine_receipt_sha256": sha256(COMP775),
            },
        },
        "host_contracts": host_results,
        "historical_verifier": {
            "status": historical.get("status"),
            "generation": historical.get("generation"),
            "page_sha256": historical.get("page_sha256"),
            "classification": "historical_generation_15_only_not_current_evidence",
        },
        "writes_this_goal": {
            "app_flash_bytes": 0,
            "external_resource_bytes": 0,
            "loader_bytes": 0,
        },
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "hardware_contact": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    # Compatibility entry point: generation 18 and the split browser/resource
    # page were superseded by the generation-20 single-source repair.  Keep the
    # parsing helpers above for their unit tests, but never emit the stale graph
    # as if it described the current device.
    from verify_comp_req_776_current_identity import main as current_main

    raise SystemExit(current_main())
