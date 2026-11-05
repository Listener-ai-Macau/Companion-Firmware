#!/usr/bin/env python3
"""Verify ordinary-reset screen evidence for COMP-REQ-775."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LIFE_PATTERN = re.compile(
    r"\[screen-life\] family=(?P<family>\w+) action=(?P<action>\w+) "
    r"episode=(?P<episode>\d+) phrase=(?P<phrase>\d+) "
    r"phase=(?P<phase>\w+) variation=(?P<variation>\d+) "
    r"dwell_commits=(?P<dwell>\d+) clip=(?P<clip>\S+) "
    r"frame_index=(?P<frame>\d+)"
)
MOUNT_PATTERN = re.compile(
    r"\[screen-assets\] policy=comp_req_638_external_cemp "
    r"store=ready prefix=read:43454D50 activation=allowed "
    r"identity=comp_req_638 mount=ok"
)
DRIVER_PATTERN = re.compile(
    r"accepted_product_driver.*changed=1.*ready_checks=[1-9][0-9]*"
    r".*transport=software_direct_bsrr_diagnostic.*has_busy=1.*result=1"
)
DRIVER_FRAME_PATTERN = re.compile(
    r"\[epaper\] accepted_product_driver request=(?P<request>\d+) "
    r"changed=(?P<changed>[01]) control=0x(?P<control>[0-9A-Fa-f]{2}) "
    r"(?:window=[^ ]+ )?bytes=(?P<bytes>\d+).*"
    r"transport=software_direct_bsrr_diagnostic "
    r"has_busy=1 result=(?P<result>[01])"
)
HOME_PARTIAL_PATTERN = re.compile(
    r"\[epaper\] accepted_product_driver request=\d+ "
    r"changed=1 control=0xCF (?:window=[^ ]+ )?"
    r"bytes=[1-9][0-9]*.*maintenance=0 "
    r"decision=1 reason=1 partial_before=(?P<partial_before>\d+).*"
    r"has_busy=1 result=1"
)
AUTO_MAINTENANCE_PATTERN = re.compile(
    r"\[epaper\] accepted_product_driver request=\d+ "
    r"changed=1 control=0x(?:C7|FF) (?:window=[^ ]+ )?"
    r"bytes=5000.*maintenance=1 "
    r"decision=2 reason=4 partial_before=\d+.*has_busy=1 result=1"
)
CHARGER_CONTENT_SUBMIT_PATTERN = re.compile(
    r"\[epaper\] accepted_product_driver request=\d+ changed=1 "
    r"control=0xCF (?:window=[^ ]+ )?bytes=[1-9][0-9]* "
    r"charger_window=1 .*"
    r"(?:previous_plane_sync=0 .*"
    r"post_sync_command=0x00 post_sync_bytes=0 post_sync_refresh=0 "
    r"(?:blink_phase_parallel=0 )?"
    r"|previous_plane_sync=1 .*"
    r"post_sync_command=0x24 post_sync_bytes=[1-9][0-9]* "
    r"post_sync_refresh=0 blink_phase_parallel=1 )"
    r"maintenance=0 decision=1 reason=1 .*has_busy=1 result=1"
)
INITIAL_PENDING_PATTERN = re.compile(
    r"\[screen\] initial_generation_refresh state=pending "
    r"generation=(?P<generation>\d+) first_visible=full subsequent=partial"
)
INITIAL_SCHEDULED_PATTERN = re.compile(
    r"\[screen\] initial_generation_refresh state=scheduled "
    r"generation=(?P<generation>\d+) request=(?P<request>\d+) refresh=4"
)
INITIAL_COMMITTED_PATTERN = re.compile(
    r"\[screen\] initial_generation_refresh state=committed "
    r"generation=(?P<generation>\d+) request=(?P<request>\d+) "
    r"refresh=4 bytes=(?P<bytes>\d+)"
)
FUNCTION_TIMING_PATTERN = re.compile(
    r"\[screen-assets\] browser_function_timing=ready "
    r"charging=3,3,1 recording=1,1,1 speaker=1,1,1 unit_ms=480"
)
RECORDING_RESOURCE_PATTERN = re.compile(
    r"\[rec-resource\] mount=ok base=0x001DC000 "
    r"pack_bytes=133851 g7_bytes=112000 opus_bytes=21723"
)
FAILURE_PATTERN = re.compile(
    r"^\[(?:epaper|screen|screen-assets|ui-sync|rec-resource)\].*"
    r"(?:\bfault\b|terminal_fault=1|mount=(?:fail|unavailable)|"
    r"result=0|transport=unavailable|ui_generation=base_only|"
    r"selftest.*=fail)",
    re.IGNORECASE | re.MULTILINE,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def verify(
    log: bytes,
    manifest: dict,
    page_sha256: str,
    require_recording_resource: bool = True,
    require_persistent_charging_overlay: bool = False,
) -> dict:
    raw_text = log.decode("utf-8", errors="replace")
    boot_marker = "[boot] Companion NUCLEO-WB55RG bringup"
    boot_index = raw_text.rfind(boot_marker)
    text = raw_text[boot_index:] if boot_index >= 0 else raw_text
    life = LIFE_PATTERN.search(text)
    recording_resource_observed = bool(
        RECORDING_RESOURCE_PATTERN.search(text)
    )
    pending = INITIAL_PENDING_PATTERN.search(text)
    scheduled = INITIAL_SCHEDULED_PATTERN.search(text)
    committed = INITIAL_COMMITTED_PATTERN.search(text)
    driver_frames = list(DRIVER_FRAME_PATTERN.finditer(text))
    home_partial_counts = [
        int(match.group("partial_before"))
        for match in HOME_PARTIAL_PATTERN.finditer(text)
    ]
    automatic_home_maintenance = bool(
        AUTO_MAINTENANCE_PATTERN.search(text)
    )
    charger_latch_marker = (
        "[screen] charger_overlay latch=1 source=device_status "
        "timeline=browser_generated frame=0 refresh=partial"
    )
    charger_latch_count = text.count(charger_latch_marker)
    charger_latch_index = text.find(charger_latch_marker)
    post_charger_text = (
        text[charger_latch_index + len(charger_latch_marker) :]
        if charger_latch_index >= 0 else ""
    )
    post_charger_drivers = list(DRIVER_FRAME_PATTERN.finditer(post_charger_text))
    post_charger_content_submits = list(
        CHARGER_CONTENT_SUBMIT_PATTERN.finditer(post_charger_text)
    )
    post_charger_life = list(LIFE_PATTERN.finditer(post_charger_text))
    overlay_marker = "[epaper] charger_overlay_compose source=cemp_clip_frame "
    overlay_frames = [
        int(frame)
        for frame in re.findall(
            r"\[epaper\] charger_overlay_compose source=cemp_clip_frame "
            r"frame=(\d+) bounds=72,168,56,32 persistent=1",
            post_charger_text,
        )
    ]
    overlay_count = len(overlay_frames)
    driver_overlay_bound = True
    previous_driver_end = 0
    for driver in post_charger_drivers:
        if overlay_marker not in post_charger_text[previous_driver_end : driver.start()]:
            driver_overlay_bound = False
        previous_driver_end = driver.end()
    persistent_charging_checks = {
        "charger_latch_established_once": charger_latch_count == 1,
        "charging_overlay_composed_for_at_least_eight_frames": (
            overlay_count >= 8
        ),
        "browser_charging_timeline_cycles_all_three_frames": (
            set(overlay_frames) == {0, 1, 2}
            and "[screen-charging] frame=1 source=browser_timeline" in post_charger_text
            and "[screen-charging] frame=2 source=browser_timeline" in post_charger_text
        ),
        "every_post_latch_driver_submit_has_overlay": (
            len(post_charger_drivers) >= 8 and driver_overlay_bound
        ),
        "post_latch_life_choreography_continues": (
            len({match.group("frame") for match in post_charger_life}) >= 8
        ),
        "post_latch_refreshes_remain_partial": (
            len(post_charger_drivers) >= 8
            and all(
                match.group("control").upper() == "CF"
                and match.group("changed") == "1"
                and match.group("result") == "1"
                for match in post_charger_drivers
            )
        ),
        "every_ping_pong_submit_carries_charger_content": (
            len(post_charger_drivers) >= 8
            and len(post_charger_content_submits) == len(post_charger_drivers)
        ),
        "finite_charging_scene_absent": (
            "[emote-player] special_started name=charging" not in text
            and "charging_event_complete" not in text
            and "[screen] charging_event complete=1" not in text
        ),
        "watchdog_healthy_during_overlay": (
            "[watchdog] healthy=1" in post_charger_text
        ),
    }
    initial_driver = None
    subsequent_partial = None
    initial_refresh_ordered = False
    if pending and scheduled and committed:
        request_id = scheduled.group("request")
        generation = scheduled.group("generation")
        initial_driver = next(
            (
                match
                for match in driver_frames
                if match.group("request") == request_id
                and match.group("control").upper() == "C7"
                and match.group("result") == "1"
                and int(match.group("bytes")) == 5000
            ),
            None,
        )
        initial_refresh_ordered = bool(
            initial_driver
            and pending.group("generation") == generation
            and committed.group("generation") == generation
            and committed.group("request") == request_id
            and int(committed.group("bytes")) > 0
            and pending.start() < scheduled.start()
            < initial_driver.start() < committed.start()
        )
        if initial_refresh_ordered:
            subsequent_partial = next(
                (
                    match
                    for match in driver_frames
                    if match.start() > committed.start()
                    and match.group("control").upper() == "CF"
                    and match.group("result") == "1"
                    and 0 < int(match.group("bytes")) <= 5000
                ),
                None,
            )
    first_frame = {
        "exact": False,
        "state_id": None,
        "browser_frame_sha256": None,
        "unique_frame_index": None,
        "observed_clip": None,
        "observed_frame_index": None,
    }
    if life:
        frame = int(life.group("frame"))
        candidates = [
            state
            for state in manifest["states"]
            if state.get("kind") == "life"
            and state.get("family") == life.group("family")
            and state.get("life_action") == life.group("action")
            and int(state.get("action_episode", -1))
            == int(life.group("episode"))
            and int(state.get("phrase", -1)) == int(life.group("phrase"))
            and state.get("phase") == life.group("phase")
            and int(state.get("variation", -1))
            == int(life.group("variation"))
            and int(state.get("dwell_commits", -1))
            == int(life.group("dwell"))
        ]
        if len(candidates) == 1:
            state = candidates[0]
            first_frame = {
                "exact": (
                    life.group("clip") == f"frame_{frame:04d}"
                    and manifest["source"]["page_sha256"] == page_sha256
                ),
                "state_id": state["id"],
                "browser_frame_sha256": state["browser_frame_sha256"],
                # The runtime clip index belongs to the immutable base CEMP;
                # expanded generations keep their own source-pack index.
                "unique_frame_index": state["unique_frame_index"],
                "observed_clip": life.group("clip"),
                "observed_frame_index": frame,
            }
    checks = {
        "boot_window_anchor_seen": boot_index >= 0,
        "ui_generation_active": (
            "[screen-assets] ui_generation=active" in text
        ),
        "base_cemp_mount_ok": bool(MOUNT_PATTERN.search(text)),
        "recording_resource_pack_mount_ok": (
            recording_resource_observed or not require_recording_resource
        ),
        "browser_function_timing_ready": bool(
            FUNCTION_TIMING_PATTERN.search(text)
        ),
        "initial_generation_full_refresh_ordered": initial_refresh_ordered,
        "subsequent_choreography_uses_partial_refresh": bool(
            subsequent_partial
        ),
        "home_choreography_crosses_legacy_limit_without_full": (
            max(home_partial_counts, default=-1) >= 5
            and not automatic_home_maintenance
        ),
        "real_busy_path_observed": bool(DRIVER_PATTERN.search(text)),
        "browser_runtime_first_frame_exact": bool(first_frame["exact"]),
        "no_runtime_fault": not bool(FAILURE_PATTERN.search(text)),
        "persistent_charging_overlay_contract": (
            all(persistent_charging_checks.values())
            if require_persistent_charging_overlay else True
        ),
    }
    return {
        "schema": "companion.comp_req_775.boot_log_evidence.v2",
        "status": (
            "MACHINE_READY" if all(checks.values()) else "FAILED"
        ),
        "checks": checks,
        "recording_resource_pack": {
            "required": require_recording_resource,
            "observed": recording_resource_observed,
        },
        "initial_generation_refresh": {
            "generation": (
                int(scheduled.group("generation")) if scheduled else None
            ),
            "request_id": (
                int(scheduled.group("request")) if scheduled else None
            ),
            "full_driver_control": (
                initial_driver.group("control").upper()
                if initial_driver else None
            ),
            "subsequent_partial_control": (
                subsequent_partial.group("control").upper()
                if subsequent_partial else None
            ),
        },
        "home_choreography_refresh": {
            "maximum_partial_before": max(home_partial_counts, default=None),
            "automatic_full_maintenance_observed": (
                automatic_home_maintenance
            ),
        },
        "first_browser_frame": first_frame,
        "persistent_charging_overlay": {
            "required": require_persistent_charging_overlay,
            "checks": persistent_charging_checks,
            "latch_count": charger_latch_count,
            "overlay_compose_count": overlay_count,
            "overlay_frames": overlay_frames,
            "post_latch_driver_submit_count": len(post_charger_drivers),
            "post_latch_charger_content_submit_count": len(
                post_charger_content_submits
            ),
            "post_latch_distinct_life_frame_count": len(
                {match.group("frame") for match in post_charger_life}
            ),
        },
        "log_sha256": sha256(log),
        "hardware_contact": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--page-sha256", required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--allow-missing-recording-resource",
        action="store_true",
        help=(
            "Only for the registered boot-chain recovery before the CRRP "
            "pack can be installed; final boot evidence must omit this flag."
        ),
    )
    parser.add_argument(
        "--require-persistent-charging-overlay",
        action="store_true",
        help=(
            "Require one charger latch, source-backed bounded overlay on every "
            "post-latch submit, continuing life choreography, partial-only "
            "refreshes, and no finite charging scene handoff."
        ),
    )
    args = parser.parse_args()
    evidence = verify(
        args.log.read_bytes(),
        json.loads(args.source_manifest.read_text(encoding="utf-8")),
        args.page_sha256,
        require_recording_resource=not args.allow_missing_recording_resource,
        require_persistent_charging_overlay=(
            args.require_persistent_charging_overlay
        ),
    )
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if evidence["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
