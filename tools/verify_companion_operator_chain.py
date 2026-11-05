#!/usr/bin/env python3
"""Validate the Companion MVP operator chain before final physical signoff.

This tool does not replace the last human observation of real pendant display,
real microphone/storage, and measured current. It proves the full host and
fixture chain in the same order an operator would use it, then records the
remaining physical confirmation as a bounded pending item.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    DISPLAY_VARIANTS,
    card_from_ble_write,
    render_card,
    sha256_hex,
)


EPAPER_MANIFEST = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
RECORDING_FIXTURE = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.7-recording-cache-fixture.json"
BLE_MATRIX = REPO_ROOT / "docs/validation/companion_ble_matrix.json"
OTA_FIXTURES = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"
VALIDATION_ROOT = REPO_ROOT / ".cache/validation"


class ChainError(RuntimeError):
    """Validation failure with compact operator-chain context."""


def now_local() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def rel(path: pathlib.Path | str | None) -> str | None:
    if path is None:
        return None
    resolved = pathlib.Path(path)
    try:
        return resolved.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ChainError(f"missing {label}: {rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_file(pattern: str) -> pathlib.Path | None:
    if not VALIDATION_ROOT.exists():
        return None
    if pattern == "companion-hardware-acceptance-summary.json":
        candidates = VALIDATION_ROOT.glob("companion-hardware-acceptance-*/companion-hardware-acceptance-summary.json")
    elif pattern == "companion-ble-real-bench.json":
        candidates = (
            list(VALIDATION_ROOT.glob("companion-v1-real-ble-gatt-*/companion-ble-real-bench.json"))
            + list(VALIDATION_ROOT.glob("companion-real-ble-gatt-*/companion-ble-real-bench.json"))
            + list(VALIDATION_ROOT.glob("companion-factory-postreset-ble-gatt-*/companion-ble-real-bench.json"))
            + list(VALIDATION_ROOT.glob("companion-hardware-acceptance-*/*/companion-ble-real-bench.json"))
        )
    else:
        candidates = VALIDATION_ROOT.glob(f"companion-*/{pattern}")
    matches = sorted((path for path in candidates if path.is_file()), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def status_of(item: dict[str, Any]) -> str:
    return str(item.get("status", "")).upper()


def operation_names(bench: dict[str, Any]) -> set[str]:
    return {str(item.get("operation")) for item in bench.get("operations", [])}


def matrix_operations(matrix: dict[str, Any]) -> set[str]:
    return set(matrix.get("operation_coverage", {}).keys())


def find_operation(bench: dict[str, Any], name: str) -> dict[str, Any]:
    for item in bench.get("operations", []):
        if item.get("operation") == name:
            return item
    return {}


def render_ble_card_fallback(out_dir: pathlib.Path) -> list[dict[str, Any]]:
    payload = {
        "request_id": 1234567,
        "card_slot": 0,
        "utf8_title_len": len("Operator PASS".encode("utf-8")),
        "utf8_body_len": len("1234567 chain verified".encode("utf-8")),
        "title": "Operator PASS",
        "body": "1234567 chain verified",
        "display_flags": 0x02,
    }
    card = card_from_ble_write(payload)
    fallback_dir = out_dir / "display_fallback"
    fallback_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[dict[str, Any]] = []
    for variant in DISPLAY_VARIANTS.values():
        data = render_card(card, variant)
        path = fallback_dir / f"ble_card_write_{variant.key.replace('.', '_')}.pbm"
        path.write_bytes(data)
        rendered.append(
            {
                "variant": variant.key,
                "path": rel(path),
                "width": variant.width,
                "height": variant.height,
                "sha256": sha256_hex(data),
                "card": card.as_manifest(),
            }
        )
    return rendered


def display_chain(epaper: dict[str, Any], ble_card_rendered: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    fixtures = epaper.get("fixtures", [])
    fixture_ids = {str(item.get("id")) for item in fixtures}
    required = {"boot_default", "recording", "sync_complete"}
    require(required <= fixture_ids, f"e-paper fixtures missing {sorted(required - fixture_ids)}", errors)
    require(len(ble_card_rendered) >= 1, "BLE-written card fallback render missing", errors)
    require(epaper.get("hardware_boundary", {}).get("deferred_to_hardware_gates"), "e-paper hardware boundary missing", errors)
    return {
        "human_action": "Power pendant, observe default card, write a short BLE card, then observe recording and sync-complete cards.",
        "automated_probe": "Rendered default/recording/sync-complete PBM fixtures plus a fresh BLE CardWriteV1 fallback card.",
        "status": "PASS",
        "evidence": {
            "manifest": rel(EPAPER_MANIFEST),
            "required_fixture_ids": sorted(required),
            "ble_card_rendered": ble_card_rendered,
        },
        "physical_boundary": {
            "target_display_not_claimed": True,
            "pending": ["real e-paper SPI timing", "busy-pin handling", "refresh waveform/current observation"],
        },
    }


def recording_chain(recording: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    synthetic = recording.get("synthetic_audio", {})
    chunk_pull = recording.get("chunk_pull", {})
    delete = recording.get("delete_after_sync", {})
    require(synthetic.get("byte_count") == 160000, "synthetic recording byte_count must be 160000", errors)
    require(chunk_pull.get("final_sha256_verified") is True, "recording pull final SHA-256 not verified", errors)
    require(chunk_pull.get("byte_count_verified") == synthetic.get("byte_count"), "recording byte count mismatch", errors)
    require(delete.get("accepted_after_length_and_sha256", {}).get("status") == "deleted", "delete-after-sync not proven", errors)
    require(recording.get("backend", {}).get("later") == "external_spi_nor", "external SPI NOR boundary missing", errors)
    return {
        "human_action": "Press record, stop after a short sample, sync it to host, verify hash, then delete only after host verification.",
        "automated_probe": "Synthetic microphone/cache fixture exercises metadata, chunk pull, CRC/SHA, resume, delete-after-sync, and privacy erase.",
        "status": "PASS",
        "evidence": {
            "fixture": rel(RECORDING_FIXTURE),
            "duration_ms": synthetic.get("duration_ms"),
            "byte_count": synthetic.get("byte_count"),
            "sha256": synthetic.get("sha256"),
            "packet_count": chunk_pull.get("packet_count"),
            "delete_after_sync": delete,
            "backend": recording.get("backend"),
        },
        "physical_boundary": {
            "synthetic_audio_fallback": True,
            "pending": ["real PDM microphone audio quality", "external SPI NOR erase/program timing", "storage current"],
        },
    }


def ble_chain(matrix: dict[str, Any], real_ble: dict[str, Any], hardware: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    required_matrix_ops = {
        "scan_result_parsing",
        "status_read",
        "card_write",
        "recording_list",
        "recording_pull",
        "byte_offset_resume",
        "log_pull",
        "delete",
        "ota_status",
    }
    required_real_ops = {
        "scan",
        "service_discovery",
        "status_read",
        "card_write",
        "recording_control_and_list",
        "settings_write",
        "diagnostics_log_pull",
        "delete_privacy_refusal",
        "ota_readiness",
    }
    v1_ops = {"ble_name_config", "meeting_control", "imu_status", "speaker_control", "wake_word_control"}
    require(status_of(matrix) == "PASS", "BLE fixture matrix status must be PASS", errors)
    require(required_matrix_ops <= matrix_operations(matrix), f"BLE matrix missing {sorted(required_matrix_ops - matrix_operations(matrix))}", errors)
    require(status_of(real_ble) == "PASS", "real BLE bench status must be PASS", errors)
    real_ops = operation_names(real_ble)
    require(required_real_ops <= real_ops, f"real BLE bench missing {sorted(required_real_ops - real_ops)}", errors)
    chunk_refusal_ops = {"recording_chunk_refusal", "recording_chunk_missing_refusal"}
    require(
        bool(chunk_refusal_ops & real_ops),
        f"real BLE bench missing recording chunk refusal evidence {sorted(chunk_refusal_ops)}",
        errors,
    )
    require(v1_ops <= real_ops, f"real BLE V1 feature bench missing {sorted(v1_ops - real_ops)}", errors)
    require(status_of(hardware) == "PASS", "hardware acceptance summary must be PASS", errors)
    chunk_refusal_operation = next((name for name in sorted(chunk_refusal_ops) if name in real_ops), None)
    return {
        "human_action": "Open host BLE tool, scan/connect, read status, write card, sync recording metadata/chunks, export bounded logs, and inspect OTA blocker state.",
        "automated_probe": "Real Bleak bench proves the live NUCLEO Companion GATT surface; fixture matrix proves full recording pull/delete and failure classification.",
        "status": "PASS",
        "evidence": {
            "real_ble_bench": rel(real_ble.get("_path")),
            "hardware_acceptance_summary": rel(hardware.get("_path")),
            "ble_matrix": rel(BLE_MATRIX),
            "real_operation_count": len(real_ble.get("operations", [])),
            "fixture_operations": sorted(required_matrix_ops),
            "v1_feature_operations": sorted(v1_ops),
            "recording_chunk_refusal_operation": chunk_refusal_operation,
        },
        "physical_boundary": {
            "real_board": True,
            "pending": ["real non-empty external-flash recording list on pendant PCB"],
        },
    }


def ota_chain(matrix: dict[str, Any], hardware: dict[str, Any], ota: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ota_status = matrix.get("operation_coverage", {}).get("ota_status", {})
    blockers = set(ota_status.get("blocker_bitmap_names", []))
    required_blockers = {
        "recording_active",
        "transfer_active",
        "diag_export_active",
        "low_battery",
        "wrong_board_target",
        "invalid_hash",
        "interrupted_transfer",
    }
    require(required_blockers <= blockers, f"OTA blockers missing {sorted(required_blockers - blockers)}", errors)
    require(status_of(hardware) == "PASS", "hardware acceptance must prove BLE OTA before operator chain", errors)
    evidence = hardware.get("evidence", {})
    require(bool(evidence.get("ble_ota")), "hardware summary missing BLE OTA evidence path", errors)
    require(
        ota.get("schema_id") == "companion.pendant.ota_manifest_fixture_report.v1",
        "OTA fixture schema mismatch",
        errors,
    )
    return {
        "human_action": "Check OTA readiness, resolve any named blocker, and only then allow update transfer.",
        "automated_probe": "OTA fixture blocker matrix plus executed Companion BLE OTA v2 hardware acceptance evidence.",
        "status": "PASS",
        "evidence": {
            "ota_fixture": rel(OTA_FIXTURES),
            "ble_ota_summary": evidence.get("ble_ota"),
            "required_blockers": sorted(required_blockers),
            "host_messages": ota_status.get("host_messages", {}),
        },
    }


def power_chain(real_ble: dict[str, Any], matrix: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    status_read = find_operation(real_ble, "status_read")
    scan = find_operation(real_ble, "scan")
    card = find_operation(real_ble, "card_write")
    meeting = find_operation(real_ble, "meeting_control")
    battery = status_read.get("battery_charge", {})
    require(bool(status_read), "real BLE status_read missing for power evidence", errors)
    require(bool(scan), "real BLE scan missing for advertising evidence", errors)
    require(battery.get("millivolts") is not None, "battery/external-power voltage missing", errors)

    states = [
        {
            "state": "boot_idle",
            "method": "real NUCLEO BLE status read after wired flash/reset; no inline current meter attached",
            "evidence": rel(real_ble.get("_path")),
            "observed": {
                "active_mode": status_read.get("device_status", {}).get("active_mode"),
                "fault_bitmap": status_read.get("device_status", {}).get("fault_bitmap"),
            },
            "current_ma": None,
            "caveat": "logic state proven; measured idle current pending final physical chain",
        },
        {
            "state": "advertising",
            "method": "real Bleak scan found Companion local name/RSSI before connect",
            "evidence": rel(real_ble.get("_path")),
            "observed": {
                "selected_name": scan.get("selected_name"),
                "rssi": scan.get("rssi"),
            },
            "current_ma": None,
            "caveat": "advertising state proven; advertising current pending meter capture",
        },
        {
            "state": "connected_idle",
            "method": "real service discovery and status read while connected",
            "evidence": rel(real_ble.get("_path")),
            "observed": {
                "operation": "service_discovery",
                "status_read": "PASS",
            },
            "current_ma": None,
            "caveat": "connected state proven; connected idle current pending meter capture",
        },
        {
            "state": "recording",
            "method": "real meeting/recording control state plus synthetic recording-cache payload",
            "evidence": rel(real_ble.get("_path")),
            "observed": {
                "meeting_state_after_start": meeting.get("start", {}).get("state"),
                "meeting_state_after_stop": meeting.get("stop", {}).get("state"),
            },
            "current_ma": None,
            "caveat": "control path proven; real microphone current pending final physical chain",
        },
        {
            "state": "e_paper_refresh",
            "method": "real card_write accepted with refresh_count plus PBM display fallback render",
            "evidence": rel(real_ble.get("_path")),
            "observed": {
                "refresh_count": card.get("card_status", {}).get("refresh_count"),
                "render_state": card.get("card_status", {}).get("render_state"),
            },
            "current_ma": None,
            "caveat": "card state proven; real e-paper refresh waveform/current pending",
        },
        {
            "state": "chunk_transfer",
            "method": "fixture host pulls 160000 bytes with packet CRC and final SHA-256; real board exposes chunk request/refusal path",
            "evidence": rel(BLE_MATRIX),
            "observed": matrix.get("operation_coverage", {}).get("recording_pull", {}),
            "current_ma": None,
            "caveat": "host transfer model proven; full real external-flash transfer current pending",
        },
        {
            "state": "charge_external_power",
            "method": "real BLE battery/charge characteristic while NUCLEO is USB/ST-LINK powered",
            "evidence": rel(real_ble.get("_path")),
            "observed": battery,
            "current_ma": None,
            "caveat": "external power state observed; charger IC/fuel gauge path pending pendant PCB",
        },
    ]
    return {
        "human_action": "Observe boot/advertising/connect/record/refresh/sync/charge power states and record current with caveats.",
        "automated_probe": "Records every required power state with method and evidence; current values are intentionally pending meter capture.",
        "status": "PASS",
        "measurement_method": "mixed real NUCLEO state evidence plus fixture fallback; no inline current meter attached in this automated run",
        "states": states,
        "physical_boundary": {
            "pending": ["inline current measurement", "battery/charger/fuel-gauge validation", "pendant PCB power path"],
        },
    }


def go_no_go() -> dict[str, Any]:
    blockers = [
        "Target e-paper panel is represented by PBM fallback renders; real SPI timing and refresh waveform still need observation.",
        "Recording payload and SPI flash cache are fixture-proven; external SPI NOR hardware timing/power still needs a real module or pendant PCB.",
        "NUCLEO BLE/OTA/wired flash chain is PASS, but pendant PCB battery, charger, fuel gauge, and measured current are not yet captured.",
    ]
    return {
        "decision": "continue_dev_board_iteration_before_first_pendant_pcb",
        "pcb_go": False,
        "reason": "The automated operator chain is coherent, but display, storage, and power are still fallback or dev-board evidence.",
        "required_before_pcb_go": blockers,
        "next_workflow_state": "2.3 waiting for final physical-chain confirmation by human operator",
    }


def acceptance_coverage(steps: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item": 1,
            "criterion": "Display default, recording, sync-complete, and BLE-written short phrase/card.",
            "status": "PASS_FALLBACK_DISPLAY",
            "evidence": steps["display"]["evidence"],
            "final_physical_confirmation": "Observe the same cards on the target e-paper panel.",
        },
        {
            "item": 2,
            "criterion": "Button-triggered recording or explicit synthetic fallback; cache metadata, chunk pull, CRC/hash, delete/privacy.",
            "status": "PASS_SYNTHETIC_RECORDING_FALLBACK",
            "evidence": steps["recording"]["evidence"],
            "final_physical_confirmation": "Press the real button and capture real microphone audio on target storage.",
        },
        {
            "item": 3,
            "criterion": "BLE host status, card write, recording list/pull/delete, bounded log export, OTA status/blockers.",
            "status": "PASS_REAL_BLE_PLUS_FIXTURE_PULL",
            "evidence": steps["ble"]["evidence"],
            "final_physical_confirmation": "Run the same host chain against non-empty real target storage when available.",
        },
        {
            "item": 4,
            "criterion": "Power evidence for boot/idle, advertising, connected idle, recording, refresh, transfer, charge/external power.",
            "status": "PASS_METHOD_RECORDED_CURRENT_PENDING",
            "evidence": {"measurement_method": steps["power"]["measurement_method"], "state_count": len(steps["power"]["states"])},
            "final_physical_confirmation": "Add current measurements from a meter/power analyzer.",
        },
        {
            "item": 5,
            "criterion": "Go/no-go record for PCB or dev-board continuation.",
            "status": "PASS_GO_NO_GO_RECORDED",
            "evidence": steps["go_no_go"],
            "final_physical_confirmation": "Human accepts or overrides the no-go-for-PCB recommendation.",
        },
        {
            "item": 6,
            "criterion": "Issues recorded outside chat.",
            "status": "PASS_RECORDED_IN_ARTIFACT_AND_WORKFLOW_PENDING_UPDATE",
            "evidence": {"report": "this operator-chain report", "next_workflow_state": steps["go_no_go"]["next_workflow_state"]},
            "final_physical_confirmation": "Workflow 2.3 should remain waiting with these pending physical items.",
        },
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    epaper = load_json(EPAPER_MANIFEST, "e-paper manifest")
    recording = load_json(RECORDING_FIXTURE, "recording cache fixture")
    matrix = load_json(BLE_MATRIX, "BLE matrix")
    ota = load_json(OTA_FIXTURES, "OTA fixture manifest")

    hardware_path = args.hardware_acceptance_summary or latest_file("companion-hardware-acceptance-summary.json")
    real_ble_path = args.real_ble_bench or latest_file("companion-ble-real-bench.json")
    if hardware_path is None:
        raise ChainError("missing latest companion-hardware-acceptance-summary.json")
    if real_ble_path is None:
        raise ChainError("missing latest companion-ble-real-bench.json")
    hardware = load_json(pathlib.Path(hardware_path), "hardware acceptance summary")
    real_ble = load_json(pathlib.Path(real_ble_path), "real BLE bench")
    hardware["_path"] = str(pathlib.Path(hardware_path).resolve())
    real_ble["_path"] = str(pathlib.Path(real_ble_path).resolve())

    ble_card_rendered = render_ble_card_fallback(out_dir)
    steps = {
        "display": display_chain(epaper, ble_card_rendered, errors),
        "recording": recording_chain(recording, errors),
        "ble": ble_chain(matrix, real_ble, hardware, errors),
        "ota": ota_chain(matrix, hardware, ota, errors),
        "power": power_chain(real_ble, matrix, errors),
        "go_no_go": go_no_go(),
    }

    chain = [
        {
            "step_id": "1",
            "name": "boot_and_default_display",
            **steps["display"],
        },
        {
            "step_id": "2",
            "name": "connect_and_read_status",
            "human_action": "Open the host BLE tool and connect to Companion.",
            "automated_probe": "Real Bleak scan/service discovery/status read from latest Companion bench.",
            "status": "PASS",
            "evidence": steps["ble"]["evidence"],
        },
        {
            "step_id": "3",
            "name": "write_card_and_recording_states",
            "human_action": "Write a short card, then check recording and synced display states.",
            "automated_probe": "Real card_write accepted plus generated fallback card and required PBM state cards.",
            "status": "PASS",
            "evidence": {
                "real_ble_bench": steps["ble"]["evidence"]["real_ble_bench"],
                "display": steps["display"]["evidence"],
            },
        },
        {
            "step_id": "4",
            "name": "record_sync_delete_privacy",
            **steps["recording"],
        },
        {
            "step_id": "5",
            "name": "host_pull_logs_and_ota_blockers",
            "human_action": "Pull recording data, export bounded diagnostics, and inspect OTA blockers.",
            "automated_probe": "BLE fixture matrix covers pull/log/delete/OTA; hardware summary covers executed BLE OTA.",
            "status": "PASS",
            "evidence": {
                "ble": steps["ble"]["evidence"],
                "ota": steps["ota"]["evidence"],
            },
        },
        {
            "step_id": "6",
            "name": "power_state_table",
            **steps["power"],
        },
        {
            "step_id": "7",
            "name": "pcb_go_no_go",
            "human_action": "Decide whether the evidence is enough for first pendant PCB.",
            "automated_probe": "Machine recommendation records unresolved risks and next workflow state.",
            "status": "PASS",
            "evidence": steps["go_no_go"],
        },
    ]

    report_status = "FAIL" if errors else "PASS"
    report = {
        "schema": "companion.operator_chain.validation.v1",
        "status": report_status,
        "automated_chain_status": report_status,
        "generated_at": now_local(),
        "tool": "tools/verify_companion_operator_chain.py",
        "repo_root": str(REPO_ROOT),
        "firmware_commit": git_commit(),
        "output_dir": str(out_dir),
        "source_artifacts": {
            "epaper_manifest": rel(EPAPER_MANIFEST),
            "recording_fixture": rel(RECORDING_FIXTURE),
            "ble_matrix": rel(BLE_MATRIX),
            "ota_fixtures": rel(OTA_FIXTURES),
            "hardware_acceptance_summary": rel(pathlib.Path(hardware_path)),
            "real_ble_bench": rel(pathlib.Path(real_ble_path)),
        },
        "operator_chain": chain,
        "acceptance_coverage": acceptance_coverage(steps),
        "final_physical_confirmation": {
            "status": "PENDING_HUMAN",
            "only_remaining_gate": True,
            "required_observations": [
                "Observe default, recording, sync-complete, and BLE-written cards on the real e-paper target.",
                "Press the real button and capture real microphone audio into real target storage.",
                "Pull a non-empty recording from real storage and delete only after hash verification.",
                "Measure current for boot/idle, advertising, connected idle, recording, e-paper refresh, chunk transfer, and charge/external-power.",
                "Accept or override the recorded no-go-for-PCB recommendation.",
            ],
        },
        "go_no_go": steps["go_no_go"],
        "errors": errors,
    }
    return report


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Companion Operator Chain",
        "",
        f"- Status: {report['status']}",
        f"- Automated chain: {report['automated_chain_status']}",
        f"- Final physical confirmation: {report['final_physical_confirmation']['status']}",
        f"- Generated: {report['generated_at']}",
        f"- Output dir: `{report['output_dir']}`",
        "",
        "## Operator Chain",
    ]
    for step in report["operator_chain"]:
        lines += [
            "",
            f"### {step['step_id']}. {step['name']}",
            "",
            f"- Status: {step['status']}",
            f"- Human action: {step['human_action']}",
            f"- Automated probe: {step['automated_probe']}",
        ]

    lines += [
        "",
        "## Acceptance Coverage",
    ]
    for item in report["acceptance_coverage"]:
        lines += [
            f"- {item['item']}: {item['status']} - {item['criterion']}",
            f"  - Final physical confirmation: {item['final_physical_confirmation']}",
        ]

    lines += [
        "",
        "## Power Evidence",
        "",
        f"- Method: {next(step for step in report['operator_chain'] if step['name'] == 'power_state_table')['measurement_method']}",
    ]
    power_step = next(step for step in report["operator_chain"] if step["name"] == "power_state_table")
    for state in power_step["states"]:
        lines.append(f"- {state['state']}: method={state['method']}; current_ma={state['current_ma']}; caveat={state['caveat']}")

    lines += [
        "",
        "## Go/No-Go",
        "",
        f"- Decision: {report['go_no_go']['decision']}",
        f"- PCB go: {report['go_no_go']['pcb_go']}",
        f"- Reason: {report['go_no_go']['reason']}",
        "",
        "## Final Physical Confirmation",
    ]
    for item in report["final_physical_confirmation"]["required_observations"]:
        lines.append(f"- {item}")
    if report["errors"]:
        lines += ["", "## Errors"]
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=pathlib.Path, default=VALIDATION_ROOT / f"companion-operator-chain-{stamp}")
    parser.add_argument("--hardware-acceptance-summary", type=pathlib.Path, default=None)
    parser.add_argument("--real-ble-bench", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", help="Print the summary JSON to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args)
        out_dir = pathlib.Path(report["output_dir"])
        summary_json = out_dir / "companion-operator-chain-summary.json"
        summary_md = out_dir / "companion-operator-chain-summary.md"
        report["summary_markdown"] = str(summary_md)
        summary_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary_md.write_text(markdown_report(report), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - CLI should preserve compact failure evidence.
        print(f"FAIL: Companion operator chain validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "PASS":
        print(f"FAIL: Companion operator chain has {len(report['errors'])} error(s).", file=sys.stderr)
        return 1
    print(
        "PASS: Companion operator chain validated; "
        f"final physical confirmation pending. Report: {summary_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
