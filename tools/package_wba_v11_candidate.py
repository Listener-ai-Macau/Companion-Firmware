#!/usr/bin/env python3
"""Assemble one source-matched WBA app/boot/UI candidate; never flash hardware."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile
import zlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from provision_wba_v11 import Package
from wba_flash_geometry import from_receipt
from wba_resource_geometry import geometry as resource_geometry


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify_ota_envelope(directory: Path, manifest: dict, payload: bytes,
                        geometry, trust: dict, version: int, app_version: int,
                        resource: bool) -> None:
    wire = (directory / "wba_manifest.bin").read_bytes()
    public_xy = (directory / "update-public.xy").read_bytes()
    if (len(wire) != 144 or wire[:4] != b"WUM1" or wire[4] != 1
        or wire[5] != (2 if resource else 1)
        or struct.unpack_from("<H", wire, 6)[0] != (2 if resource else 1)
        or wire[68:72] != bytes([1, 0, 0, 0])
        or wire.hex() != manifest.get("wba_manifest_hex")
        or len(public_xy) != 64
        or hashlib.sha256(public_xy).hexdigest() != trust.get("public_key_sha256")):
        raise RuntimeError("OTA wire/public key is not bound to this build")
    family, board, component, minimum, maximum, size, crc = struct.unpack_from("<7I", wire, 8)
    if ((family, board, component, size, crc) !=
        (0x41425743, geometry.board_target, version, len(payload), zlib.crc32(payload) & 0xFFFFFFFF)
        or wire[36:68] != hashlib.sha256(payload).digest()
        or struct.unpack_from("<I", wire, 72)[0] != trust.get("key_id")
        or struct.unpack_from("<I", wire, 140)[0] != (zlib.crc32(wire[:140]) & 0xFFFFFFFF)
        or (resource and (minimum, maximum) != (app_version, app_version))
        or (not resource and (not payload or len(payload) > geometry.app_bytes))
        or (resource and resource_geometry(len(payload))['staticBytes'] != len(payload))):
        raise RuntimeError("OTA envelope target, bounds or payload does not match selected MCU")
    public = ec.EllipticCurvePublicNumbers(int.from_bytes(public_xy[:32], "big"),
        int.from_bytes(public_xy[32:], "big"), ec.SECP256R1()).public_key()
    signature = encode_dss_signature(int.from_bytes(wire[76:108], "big"),
                                     int.from_bytes(wire[108:140], "big"))
    public.verify(signature, wire[:76], ec.ECDSA(hashes.SHA256()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--boot", type=Path, required=True)
    parser.add_argument("--firmware-ota", type=Path, required=True)
    parser.add_argument("--resource-ota", type=Path, required=True)
    parser.add_argument("--ui-delta", type=Path, required=True)
    parser.add_argument("--previous-ui-profile", type=Path, required=True)
    parser.add_argument("--flash-budget", type=Path, required=True)
    parser.add_argument("--boot-installer-test", type=Path, required=True)
    parser.add_argument("--update-service-test", type=Path, required=True)
    parser.add_argument("--update-confirm-test", type=Path, required=True)
    parser.add_argument("--ota-gatt-test", type=Path, required=True)
    parser.add_argument("--codec-report", type=Path, required=True)
    parser.add_argument("--ui-identity-delta", type=Path)
    parser.add_argument("--recording-identity-test", type=Path)
    parser.add_argument("--shared-pool-test", type=Path)
    parser.add_argument("--flash-migration-test", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    build, boot = args.build.resolve(), args.boot.resolve()
    firmware_ota, resource_ota = args.firmware_ota.resolve(), args.resource_ota.resolve()
    out = args.output.resolve()
    app_receipt, boot_receipt = load(build / "result.json"), load(boot / "result.json")
    geometry = from_receipt(app_receipt)
    if from_receipt(boot_receipt) != geometry:
        raise RuntimeError("resident boot and app target different MCU capacities")
    geometry_evidence = {
        "boot-installer-faults.json": args.boot_installer_test.resolve(),
        "update-service-faults.json": args.update_service_test.resolve(),
        "update-confirm-faults.json": args.update_confirm_test.resolve(),
        "ota-gatt-faults.json": args.ota_gatt_test.resolve(),
    }
    for name, path in geometry_evidence.items():
        evidence = load(path)
        if (not str(evidence.get("status", evidence.get("result", ""))).startswith("PASS")
            or from_receipt(evidence) != geometry):
            raise RuntimeError("test evidence does not match selected MCU: " + name)
        for source, expected in evidence.get("sources", evidence.get("source_sha256", {})).items():
            if sha256(ROOT / source) != expected.lower():
                raise RuntimeError("capacity test source changed: " + source)
    codec_report = load(args.codec_report.resolve())
    if (codec_report.get("result") != "PASS_HOST_CODEC_BITEXACT"
        or codec_report.get("arm_binary_executed") is not False
        or codec_report.get("physical_realtime_timing") != "NOT_RUN"):
        raise RuntimeError("missing scoped host codec optimization comparison")
    for source, expected in codec_report.get("sourceSha256", {}).items():
        if sha256(ROOT / source) != expected.lower():
            raise RuntimeError("codec comparison source changed: " + source)
    previous_ui_profile = load(args.previous_ui_profile.resolve())
    firmware_manifest = load(firmware_ota / "ota_manifest.json")
    resource_manifest = load(resource_ota / "ota_manifest.json")
    ui_delta = load(args.ui_delta.resolve())
    app = build / "companion-v11-board-bringup.bin"
    boot_image = boot / "companion_wba55_v11_boot.bin"
    ui = resource_ota / "ui-partition.bin"
    flash_budget = load(args.flash_budget.resolve())
    budget_identity = flash_budget.get("identity", {})
    if (flash_budget.get("result") != "PASS_FLASH_CAPACITY_SOFTWARE_ONLY"
        or budget_identity.get("appSha256") != sha256(app)
        or budget_identity.get("bootSha256") != sha256(boot_image)
        or budget_identity.get("uiSha256") != sha256(ui)):
        raise RuntimeError("Flash budget is not bound to these app/boot/UI payloads")
    for source, expected in flash_budget.get("sourceSha256", {}).items():
        if sha256(ROOT / source) != expected:
            raise RuntimeError("Flash budget source changed: " + source)

    firmware_version = app_receipt.get("firmware_version")
    if not isinstance(firmware_version, int) or not 0 < firmware_version <= 0xFFFFFFFF:
        raise RuntimeError("invalid firmware version")
    firmware_label = f"{firmware_version >> 16}.{(firmware_version >> 8) & 255}.{firmware_version & 255}"
    ui_generation = app_receipt.get("ui_resource_profile", {}).get("generation")
    if not isinstance(ui_generation, int) or ui_generation <= previous_ui_profile.get("generation", 0):
        raise RuntimeError("candidate UI generation must advance its exact preservation baseline")
    if (
        app_receipt.get("result") != "PASS_PREHARDWARE_SOFTWARE_ONLY"
        or app_receipt.get("firmware_version") != firmware_version
        or app_receipt.get("bin_sha256") != sha256(app)
        or app_receipt.get("hardwareAcceptance") != "NOT_RUN"
        or app_receipt.get("fullChainAcceptance") != "NOT_RUN"
    ):
        raise RuntimeError("app build receipt is not the exact prehardware candidate")
    profile = app_receipt.get("ui_resource_profile", {})
    if ui.stat().st_size != profile.get('uiPartitionBytes') or \
       (app_receipt.get('flash_geometry') is not None and
        app_receipt['flash_geometry'] != boot_receipt.get('flash_geometry')):
        raise RuntimeError('Boot, app and resource bank boundaries differ')
    resource_profile = load(ROOT / ".cache/wba-product-resources/profile.json")
    if (
        profile.get("generation") != ui_generation
        or str(profile.get("uiPartitionSha256", "")).lower() != sha256(ui)
        or resource_profile.get("generation") != ui_generation
        or str(resource_profile.get("uiPartitionSha256", "")).lower() != sha256(ui)
        or ui_delta.get("schema") != "companion.wba.menu-art-delta.v1"
        or ui_delta.get("result") != "PASS_MENU_ART_SCOPE_SOFTWARE_ONLY"
        or ui_delta.get("before", {}).get("generation") != previous_ui_profile.get("generation")
        or str(ui_delta.get("before", {}).get("uiPartitionSha256", "")).lower()
        != str(previous_ui_profile.get("uiPartitionSha256", "")).lower()
        or ui_delta.get("after", {}).get("generation") != ui_generation
        or str(ui_delta.get("after", {}).get("uiPartitionSha256", "")).lower() != sha256(ui)
        or ui_delta.get("stateCount") != resource_profile.get("stateCount")
        or not isinstance(ui_delta.get("nonMenuStateCount"), int)
        or ui_delta.get("nonMenuStateCount", 0) <= 0
        or not isinstance(ui_delta.get("changedStates"), list)
        or not ui_delta.get("changedStates")
        or any(not isinstance(state, str) or not state.startswith("menu_ui_")
               for state in ui_delta.get("changedStates", []))
        or ui_delta.get("unexpectedChangedStates") != []
        or ui_delta.get("hardwareAcceptance") != "NOT_RUN"
        or ui_delta.get("ownerAcceptance") != "NOT_RUN"
    ):
        raise RuntimeError("UI image or preservation delta does not match the app")
    trust = app_receipt.get("update_trust_anchor", {})
    if (
        boot_receipt.get("result") != "PASS"
        or boot_receipt.get("firmware_version") != firmware_version
        or boot_receipt.get("installed_image_size") != app.stat().st_size
        or boot_receipt.get("bin_sha256") != sha256(boot_image)
        or boot_receipt.get("key_id") != trust.get("key_id")
        or boot_receipt.get("public_key_sha256") != trust.get("public_key_sha256")
    ):
        raise RuntimeError("resident boot is not bound to the exact app and trust anchor")
    for manifest, kind, version, image, image_name in (
        (firmware_manifest, "companion-firmware-ota", firmware_version, app, "firmware_ota.bin"),
        (resource_manifest, "companion-resource-ota", ui_generation, ui, "ui-partition.bin"),
    ):
        if (
            manifest.get("package_type") != kind
            or manifest.get("hardware_revision") != geometry.hardware_revision
            or from_receipt(manifest) != geometry
            or manifest.get("component_version") != version
            or manifest.get("dev_only") is not True
            or manifest.get("file", {}).get("sha256") != sha256(image)
            or sha256((firmware_ota if kind.endswith("firmware-ota") else resource_ota) / image_name)
            != sha256(image)
        ):
            raise RuntimeError("signed OTA manifest is not bound to its exact payload")
        verify_ota_envelope(resource_ota if kind == "companion-resource-ota" else firmware_ota,
                            manifest, image.read_bytes(), geometry, trust, version,
                            firmware_version, kind == "companion-resource-ota")

    if out.exists():
        raise RuntimeError("preserve existing candidates; output must not exist")
    out.mkdir(parents=True)

    def copy(source: Path, name: str) -> None:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    copy(app, "companion-v11-board-bringup.bin")
    copy(boot_image, "boot/companion_wba55_v11_boot.bin")
    copy(ROOT / "platform/stm32wba55_companion_v11/README.md", "board-integration.md")
    copy(ROOT / "platform/stm32wba55_companion_v11/SOFTWARE_FEATURE_MATRIX.md",
         "SOFTWARE_FEATURE_MATRIX.md")
    copy(ROOT / "docs/WBA_FLASH_PLAN.md", "flash-plan.md")
    for source_dir, target_dir in ((firmware_ota, "type-ota"), (resource_ota, "resource-ota")):
        for source in sorted(source_dir.iterdir()):
            if source.is_file():
                copy(source, f"{target_dir}/{source.name}")
    copy(build / "result.json", "evidence/app-build.json")
    copy(boot / "result.json", "evidence/boot-build.json")
    copy(args.ui_delta.resolve(), "evidence/ui-menu-art-delta.json")
    copy(args.flash_budget.resolve(), "evidence/flash-budget.json")
    copy(args.codec_report.resolve(), "evidence/codec-optimization-host.json")
    if args.ui_identity_delta:
        identity_delta = load(args.ui_identity_delta.resolve())
        if (identity_delta.get("result") != "PASS_UI_IDENTITY_ONLY"
            or identity_delta.get("before", {}).get("generation") != previous_ui_profile.get("generation")
            or identity_delta.get("before", {}).get("uiPartitionSha256", "").lower() !=
                previous_ui_profile.get("uiPartitionSha256", "").lower()
            or identity_delta.get("after", {}).get("generation") != ui_generation
            or identity_delta.get("after", {}).get("uiPartitionSha256", "").lower() != sha256(ui)):
            raise RuntimeError("UI identity preservation evidence failed")
        copy(args.ui_identity_delta.resolve(), "evidence/ui-identity-delta.json")
    copy(ROOT / ".cache/wba-product-resources/test-result.json", "evidence/ui-resource-test.json")
    fault_evidence = {
        "recording-journal-faults.json": ROOT / ".cache/validation/comp-req-778-recording-journal-host/result.json",
        "recording-service.json": ROOT / ".cache/wba-recording-service-host/result.json",
        "product-recording-integration.json": ROOT / ".cache/wba-product-recording-integration-host/result.json",
        "update-metadata-faults.json": ROOT / ".cache/wba-update-metadata-host/result.json",
        "product-gatt-faults.json": ROOT / ".cache/wba-product-gatt-faults-host/result.json",
        "companion-link-faults.json": ROOT / ".cache/wba-companion-link-host/result.json",
        "menu-feedback-journeys.json": ROOT / ".cache/wba-menu-feedback-host/result.json",
        "menu-renderer-ownership.json": ROOT / ".cache/wba-product-renderer/result.json",
        "menu-runtime-faults.json": ROOT / ".cache/wba-product-runtime/result.json",
        **geometry_evidence,
    }
    if args.recording_identity_test:
        fault_evidence["recording-identity-faults.json"] = args.recording_identity_test.resolve()
    if args.shared_pool_test:
        fault_evidence["shared-pool-faults.json"] = args.shared_pool_test.resolve()
    if args.flash_migration_test:
        fault_evidence["flash-migration-faults.json"] = args.flash_migration_test.resolve()
    for name, source in fault_evidence.items():
        evidence = load(source)
        outcome = str(evidence.get("status", evidence.get("result", "")))
        if not outcome.startswith("PASS"):
            raise RuntimeError(f"fault evidence is not PASS: {source}")
        for name_in_source, expected in evidence.get("sources", evidence.get("source_sha256", evidence.get("sourceSha256", {}))).items():
            if sha256(ROOT / name_in_source) != expected.lower():
                raise RuntimeError("fault test source changed: " + name_in_source)
        copy(source, f"evidence/{name}")
    # These are emitted by the production C link with explicit simulated NOR.
    # Preserve the exact bytes used by the Type parser contract, not a separate
    # hand-authored example. They do not grant physical acceptance.
    link_evidence = load(fault_evidence["companion-link-faults.json"])
    for name in ("discard-preview.bin", "discard-completed.bin"):
        item = link_evidence.get("discard_wire", {}).get(name)
        if not item or item.get("bytes") != 84:
            raise RuntimeError("confirmed discard C wire evidence is missing")
        source = ROOT / item["path"]
        if sha256(source) != item["sha256"].lower():
            raise RuntimeError("confirmed discard C wire evidence changed")
        copy(source, f"evidence/{name}")

    combined = (
        boot_image.read_bytes()
        + bytes([0xFF]) * (0x8000 - boot_image.stat().st_size)
        + app.read_bytes()
    )
    combined_path = out / "companion-v11-initial-boot-and-app.bin"
    combined_path.write_bytes(combined)
    boot_stack, boot_reset = struct.unpack_from("<II", combined, 0)
    app_stack, app_reset = struct.unpack_from("<II", combined, 0x8000)
    if not (
        boot_stack == app_stack == 0x20020000
        and 0x08000000 <= (boot_reset & ~1) < 0x08008000
        and geometry.app_address <= (app_reset & ~1) < geometry.app_end
        and len(combined) <= geometry.nvm_offset
    ):
        raise RuntimeError("combined image vector tables do not match the WBA layout")

    files = {
        str(path.relative_to(out)).replace("\\", "/"): sha256(path)
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema": "companion.wba.v11.prehardware.delivery.v1",
        "mcu": geometry.mcu,
        "internal_flash_geometry": geometry.receipt(),
        **({"flash_geometry": app_receipt["flash_geometry"]}
           if app_receipt.get("flash_geometry") is not None else {}),
        "codec_optimization": app_receipt.get("codec_optimization"),
        "board": "Companion V1.1 2026-09-19",
        "role": "PREHARDWARE_NOT_RELEASE",
        "firmware_version": firmware_label,
        "bin_sha256": sha256(app),
        "load_address": "0x08008000",
        "initial_combined_load_address": "0x08000000",
        "initial_combined_sha256": sha256(combined_path),
        "initial_combined_warning": f"Internal flash boot+app only for {geometry.mcu}; UI{ui_generation} targets external NOR offset 0.",
        "ui_resource_profile": profile,
        "update_trust_anchor": trust,
        "dev_only": True,
        "power_profile": app_receipt.get("power_profile"),
        "low_power": app_receipt.get("low_power"),
        "memory": app_receipt.get("memory"),
        "hardwareAcceptance": "NOT_RUN",
        "fullChainAcceptance": "NOT_RUN",
        "flashed": False,
        "remaining": app_receipt.get("remaining", []),
        "product_ble_linked": app_receipt.get("product_ble_linked"),
        "identity_status_tail_bytes": 16,
        "recording_capacity_tail_bytes": 48,
        "device_status_total_bytes": 84,
        "recording_capacity_layout_version": 3 if app_receipt.get("flash_geometry") is not None else 1,
        "confirmed_recording_discard_schema": 2,
        "confirmed_recording_discard_bytes": 84,
        "files": {**files, combined_path.name: sha256(combined_path)},
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    Package(out)

    archive = out.with_suffix(".zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as bundle:
        for source in sorted(out.rglob("*")):
            if source.is_file():
                bundle.write(source, source.relative_to(out))
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("candidate ZIP CRC failed")
    verification = {
        "result": "PASS_PACKAGE_INTEGRITY_ONLY",
        "archive": str(archive),
        "sha256": sha256(archive),
        "firmwareSha256": sha256(app),
        "uiSha256": sha256(ui),
        "hardwareAcceptance": "NOT_RUN",
        "fullChainAcceptance": "NOT_RUN",
    }
    archive.with_suffix(".verification.json").write_text(
        json.dumps(verification, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(verification, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
