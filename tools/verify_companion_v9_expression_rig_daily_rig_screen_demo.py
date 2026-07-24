#!/usr/bin/env python3
"""Close machine evidence for the continuous Daily v9 Rig screen demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_ACCEPTANCE_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
DEFAULT_PARITY = ROOT / "docs/validation/companion-v9-expression-rig-target-frame-parity-20260718.json"
DEFAULT_SERIAL_SUMMARY = ROOT / "docs/validation/artifacts/companion-v9-expression-rig-target-frame-parity-20260718/device-serial-rev106-continuous/nucleo-serial-summary.json"
DEFAULT_SERIAL_LOG = ROOT / "docs/validation/artifacts/companion-v9-expression-rig-target-frame-parity-20260718/device-serial-rev106-continuous/nucleo-serial-raw.log"
DEFAULT_IMAGE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_daily_rig_screen_asset_provision_loop/Companion_Nucleo_WB55RG_DailyRigScreenAssetProvision_loop.hex"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-daily-rig-screen-demo-machine-rev106-continuous-20260718.json"

STORY_ORDER = ("daily_left", "daily_right", "daily_up", "daily_down")
ATTENTION_BY_STORY = {
    "daily_left": 1,
    "daily_right": 2,
    "daily_up": 3,
    "daily_down": 4,
}
PHASE_IDS = {
    "entry": 0,
    "prepare": 1,
    "lead": 2,
    "response": 3,
    "accent": 4,
    "hold": 5,
    "release": 6,
    "return": 7,
    "settle": 8,
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def expected_first_cycle(parity: dict[str, object]) -> list[dict[str, object]]:
    score = parity.get("score")
    frames = parity.get("frames")
    require(isinstance(score, dict) and score.get("shared_frame_count") == 60 and
            score.get("steps_per_story") == 15 and tuple(score.get("stories", ())) == STORY_ORDER,
            "pixel-parity report does not cover the shared four-story Daily cycle")
    require(isinstance(frames, list), "pixel-parity report is missing frame metadata")
    expected: list[dict[str, object]] = []
    for story_index, story in enumerate(STORY_ORDER):
        story_rows = [frame for frame in frames if frame.get("story") == story]
        require(len(story_rows) == 15, f"pixel-parity report is missing {story} frames")
        story_rows.sort(key=lambda frame: int(frame["step_index"]))
        require([int(frame["step_index"]) for frame in story_rows] == list(range(15)),
                f"pixel-parity report has unordered {story} steps")
        for frame in story_rows:
            expected.append({
                "story_index": story_index,
                "attention": ATTENTION_BY_STORY[story],
                "step": int(frame["step_index"]),
                "phase": str(frame["phase"]),
                "duration": int(frame["duration_ms"]),
            })
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parity", type=pathlib.Path, default=DEFAULT_PARITY)
    parser.add_argument("--serial-summary", type=pathlib.Path, default=DEFAULT_SERIAL_SUMMARY)
    parser.add_argument("--serial-log", type=pathlib.Path, default=DEFAULT_SERIAL_LOG)
    parser.add_argument("--image", type=pathlib.Path, default=DEFAULT_IMAGE)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()

    parity_path = args.parity.resolve()
    summary_path = args.serial_summary.resolve()
    log_path = args.serial_log.resolve()
    image_path = args.image.resolve()
    write_path = args.write.resolve()
    for path, label in ((parity_path, "pixel-parity report"),
                        (summary_path, "serial summary"),
                        (log_path, "serial log"),
                        (image_path, "demo image"),
                        (LOCKED_SOURCE, "locked v9 source"),
                        (PROTECTED_ACCEPTANCE, "protected acceptance")):
        require(path.is_file(), f"missing {label}: {path}")

    require(sha256(LOCKED_SOURCE) == LOCKED_SOURCE_SHA256,
            "locked v9 source hash changed")
    require(sha256(PROTECTED_ACCEPTANCE) == PROTECTED_ACCEPTANCE_SHA256,
            "protected special-system owner acceptance hash changed")
    parity = load_json(parity_path)
    require(parity.get("status") == "PASS", "browser/target pixel parity did not pass")
    pixel_parity = parity.get("pixel_parity")
    require(isinstance(pixel_parity, dict) and pixel_parity.get("mismatched_pixels") == 0,
            "browser and target logical frames are not pixel-identical")
    expected_rows = expected_first_cycle(parity)

    summary = load_json(summary_path)
    require(summary.get("status") == "PASS" and summary.get("mode") == "capture" and
            summary.get("port") == "COM13" and int(summary.get("bytes_read", 0)) > 0,
            "device serial capture is not a non-empty COM13 PASS")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    require(re.search(r"\[screen-assets-provision\] result=pass action=(?:written|already_current) crc=0x4CB00ADD", log),
            "device did not provision or verify the intended rev106 CRIG payload")
    require("[daily-rig-demo] source=external_nor_crig header=ready bytes=3267 profile_revision=106 mount=pass presentation=pass partial_limit=255 cemp_fallback=disabled" in log,
            "device did not mount the required external-NOR continuous Rig source")
    starts = list(re.finditer(
        r"\[daily-rig-demo\] start replay=continuous_story_cycle stories=4 "
        r"source=external_nor_crig renderer=component_compositor "
        r"initial_dwell_ms=2600 minimum_dwell_ms=750", log))
    require(starts, "device did not start the shared continuous Daily component replay")
    active_replay = log[starts[-1].start():]
    require("[daily-rig-demo] result=blocked" not in active_replay,
            "device blocked the active continuous Daily replay")

    step_pattern = re.compile(
        r"\[daily-rig-demo\] cycle=(?P<cycle>\d+) story=(?P<story>\d+) "
        r"attention=(?P<attention>\d+) step=(?P<step>\d+) phase=(?P<phase>[a-z]+) "
        r"phase_id=(?P<phase_id>\d+) score_duration_ms=(?P<score_duration>\d+) "
        r"presentation_duration_ms=(?P<presentation_duration>\d+) "
        r"refresh_elapsed_ms=(?P<refresh_elapsed>\d+) "
        r"post_refresh_delay_ms=(?P<post_delay>\d+) layers=(?P<layers>\d+) "
        r"panel=(?P<panel>\d+) bytes=(?P<bytes>\d+)")
    observed_rows = [
        {key: value if key == "phase" else int(value)
         for key, value in match.groupdict().items()}
        for match in step_pattern.finditer(active_replay)
    ]
    first_cycle = [row for row in observed_rows if row["cycle"] == 0]
    require(len(first_cycle) == 60, "device did not finish one four-story 60-frame cycle")
    require(all(row["layers"] == 13 and row["panel"] == 0 for row in first_cycle),
            "device did not use the 13-layer component compositor for every first-cycle frame")
    require(first_cycle[0]["bytes"] == 10000,
            "device did not use exactly one initial 10000-byte full baseline")
    require(all(row["bytes"] < 10000 for row in first_cycle[1:]) and
            all(row["bytes"] < 10000 for row in observed_rows[1:]),
            "device performed a whole-frame refresh after the boot baseline")
    require(all(row["refresh_elapsed"] + row["post_delay"] == row["presentation_duration"]
                for row in observed_rows),
            "device wall-clock dwell accounting differs from the shared panel score")

    observed_contract = [
        (row["story"], row["attention"], row["step"], row["phase"],
         row["phase_id"], row["presentation_duration"])
        for row in first_cycle
    ]
    expected_contract = [
        (row["story_index"], row["attention"], row["step"], row["phase"],
         PHASE_IDS[row["phase"]], row["duration"])
        for row in expected_rows
    ]
    require(observed_contract == expected_contract,
            "device story/step/phase/dwell order differs from the browser panel score")
    rollover = next((row for row in observed_rows
                     if row["cycle"] == 1 and row["story"] == 0 and row["step"] == 0), None)
    require(rollover is not None and rollover["attention"] == ATTENTION_BY_STORY["daily_left"] and
            rollover["phase"] == "entry" and rollover["phase_id"] == PHASE_IDS["entry"] and
            rollover["presentation_duration"] == 2600 and rollover["bytes"] < 10000,
            "device did not restart the next browser-identical cycle without a full refresh")
    require(re.search(
        r"\[daily-rig-demo\] cycle=0 result=pass stories=4 frames=60 composed=60 "
        r"rejected_copies=0 full_frame_refreshes=1 partial_or_holds=59", active_replay),
        "device did not finish the first 60-frame cycle with one full baseline and 59 partial-or-hold steps")

    report = {
        "schema": "companion.v9_expression_rig_daily_rig_screen_demo_machine.v3",
        "status": "PASS_MACHINE_SCREEN_DEMO_REV106_CONTINUOUS",
        "scope": "Dedicated continuous four-story Daily display demonstration only; normal product runtime remains inactive and charging/error remain fail-closed.",
        "locked_inputs": {
            "v9_source": {"path": relative(LOCKED_SOURCE), "sha256": sha256(LOCKED_SOURCE)},
            "protected_owner_acceptance": {
                "path": relative(PROTECTED_ACCEPTANCE),
                "sha256": sha256(PROTECTED_ACCEPTANCE),
            },
        },
        "browser_target_logical_parity": {
            "path": relative(parity_path),
            "sha256": sha256(parity_path),
            "status": parity["status"],
            "frame_count": 60,
            "mismatched_pixels": pixel_parity["mismatched_pixels"],
            "panel_presentation": {
                "replay_mode": "continuous_story_cycle",
                "story_order": list(STORY_ORDER),
                "initial_dwell_ms": 2600,
                "minimum_dwell_ms": 750,
            },
        },
        "flash_image": {
            "path": relative(image_path),
            "sha256": sha256(image_path),
            "bytes": image_path.stat().st_size,
            "target": "NUCLEO-WB55RG Cortex-M4",
        },
        "device_serial": {
            "summary": {"path": relative(summary_path), "sha256": sha256(summary_path)},
            "raw_log": {"path": relative(log_path), "sha256": sha256(log_path)},
            "port": summary["port"],
            "bytes_read": summary["bytes_read"],
            "crig_provisioned_or_verified": True,
            "external_nor_mount": "pass",
            "cemp_fallback": "disabled",
            "renderer": "component_compositor",
            "replay_mode": "continuous_story_cycle",
            "first_cycle_frames": first_cycle,
            "first_cycle_frame_count": len(first_cycle),
            "rollover_entry": rollover,
            "composed_frames_at_cycle_boundary": 60,
            "rejected_frame_provider_copies": 0,
            "full_frame_refreshes": 1,
            "later_whole_frame_refreshes": 0,
            "first_cycle_partial_or_holds": 59,
            "automatic_maintenance_cleanup": "disabled_for_compile_time_demo_only",
        },
        "regression_contract": {
            "prior_owner_failure": "docs/validation/companion-v9-expression-rig-daily-rig-screen-owner-acceptance-20260718.json",
            "latest_live_observation": "COMP-REQ-112: the former one-shot board replay visibly moved, then stopped after settle.",
            "repaired_behavior": "Browser and target share a continuous left-right-up-down score cycle with one boot full baseline only.",
        },
        "human_acceptance": {
            "status": "PENDING",
            "boundary": "Machine checks prove the shared continuous logical sequence and device playback. Screen appearance, orientation, ghosting and perceived liveliness still require the canonical Chinese operator review.",
        },
        "forbidden_runtime_paths": [
            "whole-face CEMP/PBM timeline",
            "whole-face card loop",
            "code-drawn face",
            "legacy art",
            "custom LUT",
        ],
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: continuous Daily Rig screen demo machine evidence -> {relative(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
