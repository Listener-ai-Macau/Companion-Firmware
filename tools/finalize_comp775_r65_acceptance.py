#!/usr/bin/env python3
"""Build the fail-closed COMP-REQ-775/WB55 machine acceptance receipt.

This deliberately keeps optical glass quality outside the machine PASS.  The
result binds one firmware image to the independent-screen run, the real codec3
meeting chain, dual minutes accuracy, and the natural low-power transition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_file(path: Path, missing: list[str]) -> bool:
    if path.is_file():
        return True
    missing.append(str(path))
    return False


def parse_type_result(path: Path) -> dict[str, Any]:
    prefix = "board_online_live_result_json="
    matches = [
        line[len(prefix) :]
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith(prefix)
    ]
    if len(matches) != 1:
        return {}
    try:
        return json.loads(matches[0])
    except json.JSONDecodeError:
        return {}


def lp_evidence(path: Path) -> tuple[dict[str, bool], dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    request_match = re.search(
        r"\[power\] low_power_face request=sleepy trigger=idle_timer.*?"
        r"\[screen\] boundary_enqueue reason=low_power_idle[^\r\n]*request=(\d+)",
        text,
        re.S,
    )
    request_id = int(request_match.group(1)) if request_match else None
    boundary_line = ""
    if request_id is not None:
        boundary_line = next(
            (
                line
                for line in text.splitlines()
                if "[epaper] accepted_product_driver" in line
                and f"request={request_id}" in line
            ),
            "",
        )
    completion_marker = (
        f"[screen-owner] complete={request_id} visible=1 surface=low_power"
        if request_id is not None
        else ""
    )
    completion_at = text.find(completion_marker) if completion_marker else -1
    after_completion = text[completion_at + len(completion_marker) :] if completion_at >= 0 else ""
    checks = {
        "natural_five_minute_idle_request_once": (
            text.count("[power] low_power_face request=sleepy trigger=idle_timer") == 1
            and "low_power_idle_timer=armed delay_ms=300000" in text
        ),
        "pure_sleepy_without_functional_overlays": (
            "lp_enter_skip_functional_compose recording=0 charger=0 blink=0 pure_sleepy=1"
            in text
        ),
        "white_ram_dwell_and_target_complete": (
            "lp_r61_white_dwell_wake white=1 ram=1 dwell_ms=1000 target=1 standby=1"
            in text
        ),
        "single_low_power_surface_commit": (
            request_id is not None
            and text.count(completion_marker) == 1
            and "commits=1 rollbacks=0" in next(
                (line for line in text.splitlines() if completion_marker in line), ""
            )
        ),
        "full_window_boundary_completed": (
            "changed=1" in boundary_line
            and "control=0xC7" in boundary_line
            and "window=0-24,0-199" in boundary_line
            and "bytes=5000" in boundary_line
            and "result=1" in boundary_line
        ),
        "all_animation_tracks_frozen": (
            "low_power_idle freeze=committed quiet=1 life=0 blink=0 wave=0 accessory=0"
            in text
        ),
        "no_visible_repaint_after_low_power_commit": (
            completion_at >= 0
            and "[epaper] accepted_product_driver" not in after_completion
            and "[epaper] accepted_true_full" not in after_completion
        ),
        "watchdog_healthy_after_commit": (
            completion_at >= 0 and "[watchdog] healthy=1 stalled_mask=0x00" in after_completion
        ),
        "no_runtime_fault": not re.search(
            r"HardFault|MemManage|BusFault|UsageFault|\[fatal\]|stalled_mask=0x(?!00)",
            text,
        ),
    }
    observed = {
        "requestId": request_id,
        "boundaryLine": boundary_line or None,
        "postCommitVisibleRefreshes": after_completion.count(
            "[epaper] accepted_product_driver"
        ),
        "postCommitWatchdogHealthy": after_completion.count(
            "[watchdog] healthy=1 stalled_mask=0x00"
        ),
    }
    return checks, observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--type-exe", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    output = (args.output or package / "MACHINE_ACCEPTANCE.json").resolve()

    paths = {
        "firmwareBin": package / "Companion_Nucleo_WB55RG_FreeRTOS.bin",
        "firmwareHex": package / "Companion_Nucleo_WB55RG_FreeRTOS.hex",
        "screen": package / "physical-run1/face-independence-final.json",
        "screenSerial": package / "physical-run1/serial/nucleo-serial-raw.log",
        "static": package / "r51-static.json",
        "lpStatic": package / "lp-static.json",
        "lpSerial": package / "low-power-run-continuation/nucleo-serial-raw.log",
        "chainSerialSummary": package
        / "physical-run3-full-chain/serial/nucleo-serial-summary.json",
        "typeLog": package / "physical-run3-full-chain/type-stdout.log",
        "session": package / "physical-run3-full-chain/persisted-session-evidence.json",
        "accuracyOffline": package
        / "physical-run3-full-chain/minutes-accuracy-offlineStore.json",
        "accuracyOnline": package
        / "physical-run3-full-chain/minutes-accuracy-onlineLive.json",
        "audioQuality": package
        / "physical-run3-full-chain/codec3-audio-quality.json",
        "typeExe": args.type_exe.resolve(),
    }
    missing: list[str] = []
    for path in paths.values():
        require_file(path, missing)

    screen = load(paths["screen"]) if paths["screen"].is_file() else {}
    static = load(paths["static"]) if paths["static"].is_file() else {}
    lp_static = load(paths["lpStatic"]) if paths["lpStatic"].is_file() else {}
    serial_summary = (
        load(paths["chainSerialSummary"])
        if paths["chainSerialSummary"].is_file()
        else {}
    )
    offline = (
        load(paths["accuracyOffline"])
        if paths["accuracyOffline"].is_file()
        else {}
    )
    online = (
        load(paths["accuracyOnline"])
        if paths["accuracyOnline"].is_file()
        else {}
    )
    session = load(paths["session"]) if paths["session"].is_file() else {}
    chain = parse_type_result(paths["typeLog"]) if paths["typeLog"].is_file() else {}
    lp_checks, lp_observed = (
        lp_evidence(paths["lpSerial"])
        if paths["lpSerial"].is_file()
        else ({"low_power_log_present": False}, {})
    )
    dual = chain.get("dualMode", {})
    report = chain.get("report", {})
    checks = {
        "all_required_artifacts_present": not missing,
        "firmware_static_independence_ready": (
            static.get("status") == "MACHINE_READY"
            and bool(static.get("checks"))
            and all(static.get("checks", {}).values())
        ),
        "screen_recording_independence_ready": (
            screen.get("status") == "MACHINE_READY"
            and bool(screen.get("checks"))
            and all(screen.get("checks", {}).values())
            and screen.get("counts", {}).get("mic_only1", 0) >= 20
            and screen.get("counts", {}).get("phase_face", 0) >= 5
            and screen.get("counts", {}).get("phase_blink", 0) >= 2
        ),
        "low_power_static_ready": (
            lp_static.get("status") == "MACHINE_READY"
            and bool(lp_static.get("checks"))
            and all(lp_static.get("checks", {}).values())
        ),
        "low_power_physical_protocol_ready": bool(lp_checks)
        and all(lp_checks.values()),
        "real_board_codec3_chain_pass": (
            chain.get("status") == "PASS"
            and chain.get("codec") == 3
            and chain.get("hostMic") is False
            and chain.get("source") == "board_device"
            and chain.get("durableBeforePartial") is True
            and report.get("finalTotalLength", 0) > 0
            and report.get("recordingId") == session.get("deviceRecordingId")
            and report.get("finalSha256", "").lower()
            == str(session.get("deviceSha256", "")).lower()
        ),
        "disconnect_resume_same_recording": (
            report.get("disconnectResume") is True
            and report.get("disconnectOffset", 0) > 0
            and len(report.get("partials", [])) >= 2
            and not report.get("partialErrors")
        ),
        "dual_mode_real_minutes_ready": (
            dual.get("ready") is True
            and all(
                dual.get(mode, {}).get("status") == "minutesReady"
                and dual.get(mode, {}).get("source") == "llm_deepseek"
                and dual.get(mode, {}).get("quality") == "final"
                for mode in ("offlineStore", "onlineLive")
            )
            and dual.get("onlineLive", {}).get("partialCount", 0) >= 2
        ),
        "dual_minutes_accuracy_pass": (
            offline.get("pass") is True and online.get("pass") is True
        ),
        "chain_serial_capture_clean": (
            serial_summary.get("status") == "PASS"
            and not serial_summary.get("errors")
            and serial_summary.get("bytes_read", 0) >= 100_000
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp775_wb55_machine_acceptance.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "result": (
            "PASS_MACHINE_CODEC3_DISCONNECT_DUAL_MINUTES_SCREEN_LP_OWNER_VISUAL_PENDING"
            if not failed
            else "NO_GO_MACHINE_ACCEPTANCE"
        ),
        "checks": checks,
        "failedChecks": failed,
        "missingFiles": missing,
        "firmware": {
            "bin": str(paths["firmwareBin"]),
            "binSha256": sha256(paths["firmwareBin"])
            if paths["firmwareBin"].is_file()
            else None,
            "hexSha256": sha256(paths["firmwareHex"])
            if paths["firmwareHex"].is_file()
            else None,
        },
        "type": {
            "exe": str(paths["typeExe"]),
            "exeSha256": sha256(paths["typeExe"])
            if paths["typeExe"].is_file()
            else None,
        },
        "screen": {
            "status": screen.get("status"),
            "counts": screen.get("counts"),
            "waveGapP95Ms": screen.get("phase_evidence", {}).get("wave_gap_p95_ms"),
            "waveGapMaxMs": screen.get("phase_evidence", {}).get("wave_gap_max_ms"),
            "opticalOwnerReview": "PENDING",
        },
        "lowPower": {
            "machineChecks": lp_checks,
            "observed": lp_observed,
            "controllerPolicy": "normal_standby_after_two-activation_white-dwell-target",
            "opticalOwnerReview": "PENDING",
        },
        "disconnectResume": report.get("disconnectResume") is True,
        "dualMode": {
            "ready": dual.get("ready") is True,
            "offlineStore": dual.get("offlineStore"),
            "onlineLive": dual.get("onlineLive"),
        },
        "minutesAccuracy": {
            "pass": offline.get("pass") is True and online.get("pass") is True,
            "offlineStore": offline.get("scores"),
            "onlineLive": online.get("scores"),
        },
        "recording": {
            "id": report.get("recordingId"),
            "codec": chain.get("codec"),
            "hostMic": chain.get("hostMic"),
            "durationMs": session.get("durationMs"),
            "totalLength": report.get("finalTotalLength"),
            "sha256": report.get("finalSha256"),
            "transcriptChars": chain.get("transcriptChars"),
            "partialCount": len(report.get("partials", [])),
        },
        "evidence": {
            name: {"path": str(path), "sha256": sha256(path)}
            for name, path in paths.items()
            if path.is_file()
        },
        "claimBoundary": (
            "Machine PASS proves the flashed identity, independent scheduler/protocol, "
            "real WB55 codec3 durable pull/resume/ASR/dual minutes, accuracy, and the "
            "natural low-power display transaction. It does not claim optical absence "
            "of ghosting, clipping, synchronization feel, or audio listening quality; "
            "those remain for the single blocking Owner review."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
