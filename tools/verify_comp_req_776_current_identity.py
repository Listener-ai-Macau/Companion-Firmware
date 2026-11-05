"""Prove the single active COMP-REQ-776 identity and its historical layers.

Generation 20 is the only active renderer/resource generation.  Generation 18
and the base CEMP remain named lineage inputs, never current evidence.  This
keeps the component-continuity repair traceable without pretending that the
older generation-18 page is still installed on the board.
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
PACKAGE = ROOT / ".cache/validation/comp776-component-clip-fix-20260812"
HISTORICAL_GEN18 = ROOT / ".cache/validation/comp775-r33-expression-coverage-audit"
HISTORICAL_GEN18_SYNC = HISTORICAL_GEN18 / "hardware-sync-noop/SYNC_RECEIPT.json"
HISTORICAL_D308 = ROOT / (
    ".cache/validation/comp775-browser-parity-audit-20260812/"
    "device-single-source-historical.json"
)
COMP775 = ROOT / ".cache/validation/comp775-screen-final-goal-r86-20260812/MACHINE_READY.json"

PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
SOURCE = PACKAGE / "source-pack-5059/source-pack-manifest.json"
GENERATION = PACKAGE / "generation-20-compact/generation.json"
GENERATION_VERIFY = PACKAGE / "generation-20-compact/generation-verification.json"
SYNC_CHANGED = PACKAGE / "hardware-sync/SYNC_RECEIPT.json"
SYNC_NOOP = PACKAGE / "hardware-noop-final/SYNC_RECEIPT.json"
BOOT = PACKAGE / "hardware-noop-final/ordinary-reset-evidence.json"
POINTER = PACKAGE / "pointer-current/MACHINE_READY.json"
DOM = PACKAGE / "DOM_LAYOUT.json"
COMPLETENESS = PACKAGE / "EXPRESSION_COMPLETENESS.json"
COMPONENT_READY = PACKAGE / "MACHINE_READY.json"
INTERACTION_JSON = GENERATED / "companion_browser_interaction_contract.json"
INTERACTION_HEADER = GENERATED / "companion_browser_interaction_contract.h"
BASE_JSON = GENERATED / "companion_browser_cemp_contract.json"
BASE_HEADER = GENERATED / "companion_browser_cemp_contract.h"
APP_BLE = PROJECT / "Core/Src/app_ble.c"
MAIN_C = PROJECT / "Core/Src/main.c"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEX = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.hex"
BIN = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.bin"
DEFAULT_OUTPUT = PACKAGE / "CURRENT_IDENTITY_CHAIN.json"

HOST_TESTS = {
    "display_track_arbiter": "tools/test_display_track_arbiter_host.ps1",
    "overlay_commit_scheduler": "tools/test_overlay_commit_scheduler_host.ps1",
    "screen_composition": "tools/test_screen_composition_journey_host.ps1",
    "display_transaction_arbiter": "tools/test_display_transaction_arbiter_host.ps1",
    "refresh_coverage": "tools/test_refresh_coverage_host.ps1",
    "screen_lifecycle": "tools/test_screen_lifecycle_journey_host.ps1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def define(header: str, name: str) -> str | None:
    match = re.search(
        rf'^#define\s+{re.escape(name)}\s+"?([^"\r\n]+)"?$',
        header,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def run_host_tests() -> tuple[dict[str, dict[str, object]], bool]:
    results: dict[str, dict[str, object]] = {}
    for name, relative in HOST_TESTS.items():
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / relative),
            ],
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

    source = load(SOURCE)
    generation = load(GENERATION)
    generation_verify = load(GENERATION_VERIFY)
    changed = load(SYNC_CHANGED)
    noop = load(SYNC_NOOP)
    boot = load(BOOT)
    pointer = load(POINTER)
    dom = load(DOM)
    complete = load(COMPLETENESS)
    component_ready = load(COMPONENT_READY)
    interaction = load(INTERACTION_JSON)
    base = load(BASE_JSON)
    historical_generation = load(
        HISTORICAL_GEN18 / "generation-18-compact/generation.json"
    )
    historical_generation_sync = load(HISTORICAL_GEN18_SYNC)
    historical_d308 = load(HISTORICAL_D308)
    comp775 = load(COMP775)
    interaction_header = INTERACTION_HEADER.read_text(encoding="utf-8")
    base_header = BASE_HEADER.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    binary = BIN.read_bytes()
    host_results, host_ready = ({}, True) if args.skip_host_tests else run_host_tests()

    page_sha = sha256(PAGE)
    source_sha = source.get("source", {}).get("page_sha256")
    resource_id = generation.get("resource_id")
    component_identity = component_ready.get("identity", {})
    changed_protected = changed.get("protected_partitions", {})
    noop_protected = noop.get("protected_partitions", {})

    checks = {
        "one_active_behavior_and_resource_page": (
            page_sha == source_sha
            == generation.get("page_sha256")
            == generation_verify.get("page_sha256")
            == interaction.get("page_sha256")
            == interaction.get("resource_page_sha256")
            == pointer.get("expected_page_sha256")
            == pointer.get("resource_page_sha256")
            == dom.get("behavior_page_sha256")
            == complete.get("identity", {}).get("resource_page_sha256")
            == define(interaction_header, "COMPANION_BROWSER_INTERACTION_PAGE_SHA256")
        ),
        "one_active_generation_20_resource_id": (
            resource_id == generation_verify.get("resource_id")
            == interaction.get("product_resource_id")
            == pointer.get("product_resource_id")
            == complete.get("identity", {}).get("resource_id")
            == changed.get("target_root", {}).get("resource_id")
            == noop.get("target_root", {}).get("resource_id")
            == define(interaction_header, "COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID")
            and changed.get("active_generation_before") == 19
            and changed.get("active_generation_after") == 20
            and noop.get("active_generation_before") == 20
            and noop.get("active_generation_after") == 20
        ),
        "generation_20_reconstructs_all_5059_states": (
            source.get("status") == "PASS"
            and len(source.get("states", [])) == 5059
            and generation.get("status") == "PASS"
            and generation.get("state_count") == 5059
            and generation_verify.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation_verify.get("states_checked") == 5059
            and generation_verify.get("strict_1bpp") is True
            and complete.get("status") == "MACHINE_READY"
        ),
        "base_cemp_is_named_lineage_not_current_page": (
            base.get("status") == "PASS"
            and base.get("state_map_count") == 2581
            and base.get("browser_page_sha256") != page_sha
            and base.get("cemp_sha256") == component_identity.get("base_cemp_sha256")
            == changed.get("cemp", {}).get("current", {}).get("sha256")
            == define(base_header, "COMPANION_BROWSER_CEMP_SHA256")
        ),
        "generation_18_is_historical_not_active": (
            historical_generation_sync.get("active_generation_after") == 18
            and historical_generation_sync.get("target_root", {}).get("generation") == 18
            and historical_generation_sync.get("target_root", {}).get("resource_id")
            == historical_generation.get("resource_id")
            and historical_generation.get("resource_id") != resource_id
            and historical_generation.get("page_sha256") != page_sha
            and historical_generation.get("resource_id") not in {
                interaction.get("product_resource_id"),
                pointer.get("product_resource_id"),
            }
        ),
        "generated_headers_bind_active_page_resource_and_base": (
            define(interaction_header, "COMPANION_BROWSER_INTERACTION_PAGE_SHA256") == page_sha
            and define(interaction_header, "COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID") == resource_id
            and define(base_header, "COMPANION_BROWSER_PAGE_SHA256") == base.get("browser_page_sha256")
        ),
        "r86_source_consumes_declared_layers": (
            '#include "companion_browser_cemp_contract.h"' in app_ble
            and '#include "companion_browser_interaction_contract.h"' in app_ble
            and "comp_ui_asset_generation_mount(" in app_ble
            and "comp_ui_asset_generation_find(" in app_ble
            and "companion_browser_generation_resource_id" in app_ble
            and "memcmp(s_companion_ui_asset_generation.root.resource_id" in app_ble
        ),
        "current_app_binds_active_resource_and_component_receipt": (
            isinstance(resource_id, str)
            and len(resource_id) == 64
            and binary.count(bytes.fromhex(resource_id)) == 1
            and sha256(BIN) == component_identity.get("app_bin_sha256")
            and sha256(HEX) == component_identity.get("app_hex_sha256")
        ),
        "board_boot_observed_generation_20_exact_frame": (
            boot.get("status") == "MACHINE_READY"
            and boot.get("checks", {}).get("ui_generation_active") is True
            and boot.get("checks", {}).get("browser_runtime_first_frame_exact") is True
            and boot.get("initial_generation_refresh", {}).get("generation") == 20
        ),
        "changed_sync_only_wrote_ui_external_partition": (
            changed.get("external_flash_write_bytes", 0) > 0
            and changed.get("internal_flash_write_bytes") == 0
            and changed.get("recording_partition_write_bytes") == 0
            and changed.get("active_generation_after") == 20
            and all(value == 0 for value in changed_protected.values() if isinstance(value, int))
        ),
        "final_identity_probe_wrote_nothing": (
            noop.get("external_flash_write_bytes") == 0
            and noop.get("internal_flash_write_bytes") == 0
            and noop.get("recording_partition_write_bytes") == 0
            and noop.get("readback_partition_sha256") == component_identity.get("external_partition_sha256")
            and all(value == 0 for value in noop_protected.values() if isinstance(value, int))
        ),
        "current_browser_replays_and_dom_are_machine_ready": (
            pointer.get("verdict") == "MACHINE_READY"
            and pointer.get("browser_errors") == []
            and len(pointer.get("page_loads", [])) == 4
            and all(row.get("body_sha256") == page_sha for row in pointer.get("page_loads", []))
            and dom.get("status") == "MACHINE_READY"
            and dom.get("browser_errors") == []
            and len(dom.get("cases", [])) == 2
            and all(not row["geometry"]["ancestor_clip_violation"] for row in dom.get("cases", []))
        ),
        "historical_d308_is_nonexceptional_and_quarantined": (
            historical_d308.get("status") == "NO_GO"
            and historical_d308.get("generation") == 15
            and historical_d308.get("page_sha256")
            == "D308CB63D287EFADC6DAC70F5E0DDE1BCA3AD13803B5A93E625BBB8505A7DAAE"
            and historical_d308.get("page_sha256") not in {
                page_sha,
                base.get("browser_page_sha256"),
                historical_generation.get("page_sha256"),
            }
        ),
        "current_host_contracts_pass": host_ready,
        "comp_req_775_accepted_receipt_remains_machine_ready": (
            comp775.get("status") == "MACHINE_READY"
            and all(comp775.get("checks", {}).values())
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_776.current_identity_chain.v2",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "identity_graph": {
            "active_behavior_resource_page": {
                "path": str(PAGE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": page_sha,
                "state_count": len(source.get("states", [])),
                "source_manifest_sha256": sha256(SOURCE),
            },
            "active_interaction_contract": {
                "contract_sha256": interaction.get("contract_sha256"),
                "json_sha256": sha256(INTERACTION_JSON),
                "header_sha256": sha256(INTERACTION_HEADER),
            },
            "active_generation_20": {
                "generation": 20,
                "resource_id": resource_id,
                "manifest_sha256": sha256(GENERATION),
                "blob_sha256": generation.get("blob_sha256"),
                "external_partition_sha256": noop.get("readback_partition_sha256"),
            },
            "base_cemp_lineage": {
                "source_page_sha256": base.get("browser_page_sha256"),
                "cemp_sha256": base.get("cemp_sha256"),
                "state_map_count": base.get("state_map_count"),
                "header_sha256": sha256(BASE_HEADER),
            },
            "historical_generation_18": {
                "classification": "superseded_lineage_not_current_evidence",
                "resource_id": historical_generation.get("resource_id"),
                "page_sha256": historical_generation.get("page_sha256"),
            },
            "current_app": {
                "hex_sha256": sha256(HEX),
                "bin_sha256": sha256(BIN),
                "app_ble_sha256": sha256(APP_BLE),
                "main_sha256": sha256(MAIN_C),
                "driver_sha256": sha256(DRIVER),
            },
        },
        "host_contracts": host_results,
        "writes_for_generation_20_install": {
            "ui_external_flash_bytes": changed.get("external_flash_write_bytes"),
            "internal_flash_bytes": changed.get("internal_flash_write_bytes"),
            "recording_partition_bytes": changed.get("recording_partition_write_bytes"),
            "loader_bytes": changed_protected.get("loader_internal_flash_write_bytes"),
        },
        "writes_for_final_identity_probe": {
            "ui_external_flash_bytes": noop.get("external_flash_write_bytes"),
            "internal_flash_bytes": noop.get("internal_flash_write_bytes"),
            "recording_partition_bytes": noop.get("recording_partition_write_bytes"),
            "loader_bytes": noop_protected.get("loader_internal_flash_write_bytes"),
        },
        "historical_d308": {
            "classification": "historical_generation_15_only_not_current_evidence",
            "status": historical_d308.get("status"),
            "page_sha256": historical_d308.get("page_sha256"),
        },
        "hardware_contact": 1,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
