#!/usr/bin/env python3
"""Fail-closed evidence gate for a Companion V1.1 WBA55 board-arrival run.

This tool never opens a probe, BLE connection, GUI, or remote service.  It
binds separately produced artifacts to one factory kit and reports the next
eligible stage.  Hardware and product acceptance remain NOT_RUN until their
explicit artifacts are supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile


KIT_SCHEMA = "companion.wba.factory-kit.v1"
INSTALL_SCHEMA = "companion.wba.factory-install.v1"
TYPE_CHECK_SCHEMA = "companion.wba.v11.type-device-check.v1"
FULL_CHAIN_SCHEMA = "companion.wba.v11.full-chain-acceptance.v1"
EXPECTED_BOARD = "companion-v1.1-wba55"
EXPECTED_FIRMWARE_VERSION = 0x00010127
EXPECTED_UI_GENERATION = 57


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def resolve_member(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    if Path(name).is_absolute() or not target.is_relative_to(root.resolve()):
        raise ValueError(f"kit member escapes kit root: {name}")
    return target


def pass_text(value: object) -> bool:
    return isinstance(value, str) and value.startswith("PASS")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_kit(root: Path, errors: list[str]) -> dict:
    manifest_path = root / "kit-manifest.json"
    if not manifest_path.is_file():
        errors.append(f"missing kit manifest: {manifest_path}")
        return {}
    manifest = load_json(manifest_path)
    require(manifest.get("schema") == KIT_SCHEMA, "unexpected kit schema", errors)
    require(manifest.get("result") == "PASS_SOFTWARE_PACKAGE_ONLY", "kit is not software-package ready", errors)
    require(manifest.get("hardwareAcceptance") == "NOT_RUN", "kit must not claim hardware acceptance", errors)
    require(manifest.get("fullChainAcceptance") == "NOT_RUN", "kit must not claim full-chain acceptance", errors)
    require(manifest.get("flashed") is False, "factory kit must be unflashed evidence", errors)
    require(manifest.get("firmware_version") == "1.1.39", "unexpected factory firmware version", errors)
    require(manifest.get("ui_generation") == EXPECTED_UI_GENERATION, "unexpected UI generation", errors)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        errors.append("kit manifest has no payload hashes")
        return manifest
    for name, expected in files.items():
        try:
            path = resolve_member(root, str(name))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"missing kit payload: {name}")
        elif sha256(path) != str(expected).lower():
            errors.append(f"kit payload hash mismatch: {name}")
    msi = root / "type" / "Companion-Type-x64.msi"
    if msi.is_file():
        require(sha256(msi) == str(manifest.get("type_msi_sha256", "")).lower(),
                "Type MSI is not the kit-bound candidate", errors)
    else:
        errors.append("kit is missing type/Companion-Type-x64.msi")
    return manifest


def check_install(path: Path, kit_root: Path, errors: list[str]) -> dict:
    report = load_json(path)
    require(report.get("schema") == INSTALL_SCHEMA, "unexpected install-result schema", errors)
    require(report.get("result") in {"PASS_INSTALL_READBACK_ONLY", "ALREADY_INSTALLED_READBACK_VERIFIED"},
            "install result is not exact-readback verified", errors)
    require(report.get("reset_to_app") is True, "installed target was not reset to the app", errors)
    require(report.get("hardwareAcceptance") == "NOT_RUN", "install receipt must not claim hardware acceptance", errors)
    require(report.get("fullChainAcceptance") == "NOT_RUN", "install receipt must not claim full-chain acceptance", errors)
    require(isinstance(report.get("uid"), str) and re.fullmatch(r"[0-9a-f]{24}", report["uid"]) is not None,
            "install receipt has no valid 96-bit MCU UID", errors)
    firmware_manifest = kit_root / "firmware" / "manifest.json"
    if firmware_manifest.is_file():
        require(report.get("package_manifest_sha256") == sha256(firmware_manifest),
                "install receipt belongs to a different firmware package", errors)
    else:
        errors.append("kit firmware manifest is missing")
    if report.get("result") == "PASS_INSTALL_READBACK_ONLY":
        require(report.get("protected_regions_unchanged") is True,
                "new install did not prove protected regions unchanged", errors)
        require(isinstance(report.get("after_internal_sha256"), str),
                "new install has no final MCU readback hash", errors)
        require(isinstance(report.get("after_nor_sha256"), str),
                "new install has no final NOR readback hash", errors)
    return report


def check_type_device(path: Path, kit: dict, install: dict, errors: list[str]) -> dict:
    report = load_json(path)
    require(report.get("schema") == TYPE_CHECK_SCHEMA, "unexpected Type device-check schema", errors)
    require(pass_text(report.get("result")), "Type device check does not start with PASS", errors)
    require(report.get("board") == EXPECTED_BOARD, "Type device check names the wrong board", errors)
    require(report.get("firmwareVersion") == EXPECTED_FIRMWARE_VERSION,
            "Type read back a different firmware version", errors)
    require(report.get("buildId") == 0x20261004, "Type read back a different firmware build id", errors)
    require(report.get("boardId") == 0x57424155, "Type did not read the WBA55 V1.1 board id", errors)
    require(report.get("hardwareRevision") == "COMPANION-WBA55-V1.1",
            "Type did not resolve the WBA55 V1.1 hardware revision", errors)
    require(report.get("deviceId") not in (None, ""), "Type device check has no durable device id", errors)
    require(isinstance(report.get("mcuUid"), str) and
            re.fullmatch(r"[0-9a-f]{24}", report["mcuUid"]) is not None,
            "Type did not read a valid 96-bit MCU UID", errors)
    require(report.get("uiGeneration") == kit.get("ui_generation"),
            "Type did not read the installed UI generation", errors)
    checks = report.get("checks")
    if not isinstance(checks, dict):
        errors.append("Type device check has no checks object")
    else:
        for name in ("bluetooth", "firmware", "gatt", "recordingCatalog", "clock", "imu", "speaker"):
            require(checks.get(name) == "PASS", f"Type device check did not pass {name}", errors)
        for name in ("display", "touch", "power"):
            require(checks.get(name) in {"PASS", "MANUAL_REQUIRED"},
                    f"Type device check must explicitly mark {name} PASS or MANUAL_REQUIRED", errors)
    return report


def mode_ready(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return (value.get("status") == "minutesReady" and value.get("quality") == "final" and
            isinstance(value.get("markdown"), str) and bool(value["markdown"].strip()))


def check_full_chain(path: Path, type_report: dict, errors: list[str]) -> dict:
    report = load_json(path)
    require(report.get("schema") == FULL_CHAIN_SCHEMA, "unexpected full-chain schema", errors)
    require(pass_text(report.get("result")), "full-chain result does not start with PASS", errors)
    require(report.get("captureSource", report.get("source")) == "board_device",
            "full chain was not captured from the board", errors)
    require(report.get("hostMic") is False, "full chain used or failed to exclude the host microphone", errors)
    require(report.get("codec") == 3, "full chain did not use codec=3", errors)
    require(report.get("nonSeed") is True, "full chain did not prove non-seed capture", errors)
    require(report.get("disconnectResume") is True, "full chain did not pass active BLE disconnect/resume", errors)
    require(report.get("deviceId") == type_report.get("deviceId"),
            "full chain belongs to a different device", errors)
    identity = report.get("hardwareIdentity")
    require(isinstance(identity, dict) and identity.get("verified") is True and
            identity.get("firmwareVersion") == EXPECTED_FIRMWARE_VERSION and
            identity.get("buildId") == 0x20261004 and identity.get("boardId") == 0x57424155 and
            identity.get("hardwareRevision") == "COMPANION-WBA55-V1.1" and
            identity.get("mcuUid") == type_report.get("mcuUid") and
            identity.get("uiGeneration") == type_report.get("uiGeneration"),
            "full chain lacks the expected WBA55 V1.1 hardware identity", errors)
    storage = report.get("boardStorage")
    require(isinstance(storage, dict) and storage.get("finalized") is True,
            "full chain did not prove finalized board storage", errors)
    pull = report.get("typePull")
    require(isinstance(pull, dict) and pull.get("complete") is True and
            pull.get("decodable") is True and pull.get("nonSilent") is True,
            "Type pull is incomplete, undecodable, or silent", errors)
    asr = report.get("asr")
    require(isinstance(asr, dict) and asr.get("real") is True and
            isinstance(asr.get("transcriptChars"), int) and asr["transcriptChars"] > 0,
            "full chain lacks a non-empty real-ASR result", errors)
    dual = report.get("dualMode")
    require(isinstance(dual, dict) and mode_ready(dual.get("offlineStore")) and mode_ready(dual.get("onlineLive")),
            "offlineStore and onlineLive minutes are not both ready", errors)
    accuracy = report.get("minutesAccuracy")
    require(isinstance(accuracy, dict) and accuracy.get("pass") is True,
            "minutesAccuracy did not pass", errors)
    return report


def evaluate(kit_root: Path, install_path: Path | None = None,
             type_path: Path | None = None, chain_path: Path | None = None) -> tuple[dict, int]:
    errors: list[str] = []
    kit = check_kit(kit_root, errors)
    install: dict = {}
    type_report: dict = {}
    chain: dict = {}
    hardware_binding = "NOT_RUN"
    stage = "READY_FOR_INSTALL"
    if install_path is not None:
        install = check_install(install_path, kit_root, errors)
        stage = "READY_FOR_TYPE_DEVICE_CHECK"
    if type_path is not None:
        if not install:
            errors.append("Type device check requires an install result")
        type_report = check_type_device(type_path, kit, install, errors)
        stage = "READY_FOR_FULL_CHAIN"
        if install:
            hardware_binding = ("PROVEN" if type_report.get("mcuUid") == install.get("uid")
                                else "NOT_PROVEN_NO_MCU_UID_OVER_GATT")
            if hardware_binding != "PROVEN":
                stage = "BLOCKED_HARDWARE_IDENTITY_BINDING"
    if chain_path is not None:
        if not type_report:
            errors.append("full-chain acceptance requires a Type device-check result")
        chain = check_full_chain(chain_path, type_report, errors)
        stage = "READY_FOR_OWNER_REVIEW"
        checks = type_report.get("checks", {}) if isinstance(type_report, dict) else {}
        if any(checks.get(name) == "MANUAL_REQUIRED" for name in ("display", "touch", "power")):
            stage = "READY_FOR_MANUAL_HARDWARE_CHECKS"
        if hardware_binding != "PROVEN":
            stage = "BLOCKED_HARDWARE_IDENTITY_BINDING"
    if errors:
        stage = ("BLOCKED_HARDWARE_IDENTITY_BINDING"
                 if hardware_binding == "NOT_PROVEN_NO_MCU_UID_OVER_GATT" else "FAIL")
    report = {
        "schema": "companion.wba.v11.board-arrival-gate.v1",
        "result": stage,
        "kit": str(kit_root.resolve()),
        "installResult": str(install_path.resolve()) if install_path else None,
        "typeDeviceCheck": str(type_path.resolve()) if type_path else None,
        "fullChainAcceptance": str(chain_path.resolve()) if chain_path else None,
        "hardwareIdentityBinding": hardware_binding,
        "ownerAcceptance": "NOT_RUN",
        "errors": errors,
    }
    return report, 1 if errors else 0


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="companion-wba-arrival-") as temp:
        root = Path(temp)
        (root / "type").mkdir()
        (root / "firmware").mkdir()
        (root / "type/Companion-Type-x64.msi").write_bytes(b"msi")
        (root / "firmware/manifest.json").write_text("{}\n", encoding="utf-8")
        files = {
            "type/Companion-Type-x64.msi": sha256(root / "type/Companion-Type-x64.msi"),
            "firmware/manifest.json": sha256(root / "firmware/manifest.json"),
        }
        kit = {"schema": KIT_SCHEMA, "result": "PASS_SOFTWARE_PACKAGE_ONLY",
               "hardwareAcceptance": "NOT_RUN", "fullChainAcceptance": "NOT_RUN", "flashed": False,
               "firmware_version": "1.1.39", "ui_generation": 57,
               "type_msi_sha256": files["type/Companion-Type-x64.msi"], "files": files}
        (root / "kit-manifest.json").write_text(json.dumps(kit), encoding="utf-8")
        install = {"schema": INSTALL_SCHEMA, "result": "PASS_INSTALL_READBACK_ONLY",
                   "uid": "0123456789abcdef01234567", "package_manifest_sha256": files["firmware/manifest.json"],
                   "hardwareAcceptance": "NOT_RUN", "fullChainAcceptance": "NOT_RUN", "reset_to_app": True,
                   "protected_regions_unchanged": True, "after_internal_sha256": "a", "after_nor_sha256": "b"}
        device = {"schema": TYPE_CHECK_SCHEMA, "result": "PASS_TYPE_DEVICE_CHECK", "board": EXPECTED_BOARD,
                  "firmwareVersion": EXPECTED_FIRMWARE_VERSION, "buildId": 0x20261004,
                  "boardId": 0x57424155, "hardwareRevision": "COMPANION-WBA55-V1.1", "deviceId": "ble-id",
                  "mcuUid": install["uid"], "uiGeneration": EXPECTED_UI_GENERATION,
                  "checks": {name: "PASS" for name in
                  ("bluetooth", "firmware", "gatt", "recordingCatalog", "clock", "imu", "speaker", "display", "touch", "power")}}
        chain = {"schema": FULL_CHAIN_SCHEMA, "result": "PASS_WBA_FULL_CHAIN", "captureSource": "board_device",
                 "hostMic": False, "codec": 3, "nonSeed": True, "disconnectResume": True, "deviceId": "ble-id",
                 "hardwareIdentity": {"verified": True, "firmwareVersion": EXPECTED_FIRMWARE_VERSION,
                                      "buildId": 0x20261004, "boardId": 0x57424155,
                                      "hardwareRevision": "COMPANION-WBA55-V1.1",
                                      "mcuUid": install["uid"], "uiGeneration": EXPECTED_UI_GENERATION},
                 "boardStorage": {"finalized": True}, "typePull": {"complete": True, "decodable": True, "nonSilent": True},
                 "asr": {"real": True, "transcriptChars": 12},
                 "dualMode": {"offlineStore": {"status": "minutesReady", "quality": "final", "markdown": "# offline"},
                              "onlineLive": {"status": "minutesReady", "quality": "final", "markdown": "# online"}},
                 "minutesAccuracy": {"pass": True}}
        paths = []
        for name, value in (("install.json", install), ("device.json", device), ("chain.json", chain)):
            path = root / name
            path.write_text(json.dumps(value), encoding="utf-8")
            paths.append(path)
        report, code = evaluate(root, *paths)
        if code or report["result"] != "READY_FOR_OWNER_REVIEW":
            raise AssertionError(report)
        device.pop("mcuUid")
        paths[1].write_text(json.dumps(device), encoding="utf-8")
        report, code = evaluate(root, *paths)
        if (code != 1 or report["result"] != "BLOCKED_HARDWARE_IDENTITY_BINDING" or
                report["hardwareIdentityBinding"] != "NOT_PROVEN_NO_MCU_UID_OVER_GATT"):
            raise AssertionError(report)
        device["mcuUid"] = install["uid"]
        device["checks"]["display"] = "MANUAL_REQUIRED"
        paths[1].write_text(json.dumps(device), encoding="utf-8")
        report, code = evaluate(root, *paths)
        if code or report["result"] != "READY_FOR_MANUAL_HARDWARE_CHECKS":
            raise AssertionError(report)
        device["checks"]["display"] = "PASS"
        paths[1].write_text(json.dumps(device), encoding="utf-8")
        chain["minutesAccuracy"] = {"pass": False}
        paths[2].write_text(json.dumps(chain), encoding="utf-8")
        report, code = evaluate(root, *paths)
        if code != 1 or "minutesAccuracy did not pass" not in report["errors"]:
            raise AssertionError(report)
    print("SELF_TEST_OK: WBA board-arrival gate accepts the complete contract and rejects failed accuracy.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path)
    parser.add_argument("--install-result", type=Path)
    parser.add_argument("--type-device-check", type=Path)
    parser.add_argument("--full-chain-acceptance", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.kit is None:
        parser.error("--kit is required unless --self-test is used")
    report, code = evaluate(args.kit, args.install_result, args.type_device_check, args.full_chain_acceptance)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
