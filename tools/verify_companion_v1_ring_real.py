#!/usr/bin/env python3
"""Fill the real WB55 V1 recording catalog past capacity and prove ring eviction.

The gate is deliberately silent: it records ambient board-microphone input but
never starts host or device playback.  It requires an empty starting catalog so
its final delete-all cleanup can only remove recordings created by this run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import shutil
import struct
import subprocess
import time
from types import SimpleNamespace
from typing import Any

from companion_ble_real_bench import (
    SCHEMA_VERSION,
    build_uuid_index,
    load_uuid_table,
    notify_write_wait,
    parse_delete_privacy,
    parse_meeting_status,
    parse_recording_list,
    read_and_parse,
    scan_for_companion,
    utc_now,
)


def resolve_programmer(requested: str) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if requested:
        candidates.append(pathlib.Path(requested))
    discovered = shutil.which("STM32_Programmer_CLI.exe") or shutil.which(
        "STM32_Programmer_CLI"
    )
    if discovered:
        candidates.append(pathlib.Path(discovered))
    candidates.extend(
        [
            pathlib.Path(r"C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"),
            pathlib.Path(
                r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
            ),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError("STM32_Programmer_CLI.exe not found for ring reboot gate")


def reset_board(programmer: pathlib.Path) -> dict[str, Any]:
    command = [
        str(programmer),
        "-c",
        "port=SWD",
        "mode=UR",
        "reset=HWrst",
        "freq=4000",
        "-rst",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "programmer": str(programmer),
        "command": command[1:],
        "exitCode": completed.returncode,
        "stdoutTail": completed.stdout[-2000:],
        "stderrTail": completed.stderr[-2000:],
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from bleak import BleakClient

    started_at = utc_now()
    started_monotonic = time.monotonic()
    uuids = build_uuid_index(load_uuid_table())
    scan_args = SimpleNamespace(
        name=args.name,
        address=args.address,
        timeout=args.timeout,
    )
    device, scan = await scan_for_companion(scan_args, set())
    created_ids: list[int] = []
    snapshots: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {"attempted": False, "emptyAfter": False}
    reboot: dict[str, Any] = {"attempted": False, "catalogInvariant": False}
    test_error: str | None = None
    checks: dict[str, bool] = {}

    client_kwargs: dict[str, Any] = {
        "timeout": args.timeout,
        "winrt": {"use_cached_services": False},
    }
    async with BleakClient(device, **client_kwargs) as client:
        if hasattr(client, "pair"):
            try:
                await client.pair()
            except Exception:
                pass

        before = await read_and_parse(
            client, uuids["recording_list"], parse_recording_list
        )
        before_ids = [int(item["recording_id"]) for item in before.get("entries", [])]
        if args.cleanup_owned_ids:
            expected = {
                int(value)
                for value in args.cleanup_owned_ids.split(",")
                if value.strip()
            }
            if not before_ids:
                return {
                    "schema": "companion_v1.real_ring_cleanup.v1",
                    "result": "PASS owned ring cleanup already complete",
                    "generatedAt": utc_now(),
                    "noAudioPlayback": True,
                    "ownedIds": sorted(expected),
                    "catalogBefore": [],
                    "alreadyClean": True,
                    "catalogAfter": [],
                }
            if set(before_ids) != expected:
                raise RuntimeError(
                    "cleanup ownership mismatch; refusing delete-all: "
                    f"catalog={before_ids} expected={sorted(expected)}"
                )
            delete_request = 0x6EFE_FF00 | (int(time.time()) & 0xFF)
            delete_payload = struct.pack(
                "<BBHIII32s",
                SCHEMA_VERSION,
                2,
                0,
                delete_request,
                0,
                0,
                bytes(32),
            )
            response = await notify_write_wait(
                client,
                uuids["delete_privacy"],
                uuids["delete_privacy"],
                delete_payload,
                parse_delete_privacy,
                lambda value: value["request_id"] == delete_request,
                90.0,
            )
            deadline = time.monotonic() + 120.0
            after_ids = before_ids
            while after_ids and time.monotonic() < deadline:
                await asyncio.sleep(1.0)
                after = await read_and_parse(
                    client, uuids["recording_list"], parse_recording_list
                )
                after_ids = [
                    int(item["recording_id"])
                    for item in after.get("entries", [])
                ]
            passed = (int(response["flags"]) & 1) == 0 and not after_ids
            return {
                "schema": "companion_v1.real_ring_cleanup.v1",
                "result": "PASS owned ring cleanup" if passed else "FAIL owned ring cleanup",
                "generatedAt": utc_now(),
                "noAudioPlayback": True,
                "ownedIds": sorted(expected),
                "catalogBefore": before_ids,
                "response": response,
                "catalogAfter": after_ids,
            }
        if before_ids:
            raise RuntimeError(
                "ring gate refuses destructive cleanup because starting catalog "
                f"is not empty: {before_ids}"
            )

        try:
            request_seed = 0x6000_0000 | (int(time.time() * 1000) & 0x0FFF_FF00)
            for index in range(args.count):
                start_request = request_seed + index * 4
                start_payload = struct.pack(
                    "<BBHIHBB",
                    SCHEMA_VERSION,
                    1,
                    0,
                    start_request,
                    max(4, int(args.seconds) + 2),
                    2,
                    0,
                )
                start = await notify_write_wait(
                    client,
                    uuids["meeting_status"],
                    uuids["meeting_control"],
                    start_payload,
                    parse_meeting_status,
                    lambda value, rid=start_request: value["request_id"] == rid
                    and value["state"] == 1
                    and value["meeting_id"] > 0,
                    args.notify_timeout,
                )
                recording_id = int(start["meeting_id"])
                created_ids.append(recording_id)
                await asyncio.sleep(args.seconds)

                stop_request = start_request + 1
                stop_payload = struct.pack(
                    "<BBHIHBB", SCHEMA_VERSION, 2, 0, stop_request, 0, 2, 0
                )
                stop = await notify_write_wait(
                    client,
                    uuids["meeting_status"],
                    uuids["meeting_control"],
                    stop_payload,
                    parse_meeting_status,
                    lambda value, rid=stop_request, mid=recording_id: value["request_id"] == rid
                    and value["state"] == 2
                    and value["meeting_id"] == mid,
                    max(30.0, args.notify_timeout),
                )

                finalize_request = start_request + 2
                finalize_payload = struct.pack(
                    "<BBHIHBB", SCHEMA_VERSION, 3, 0, finalize_request, 0, 2, 0
                )
                finalize = await notify_write_wait(
                    client,
                    uuids["meeting_status"],
                    uuids["meeting_control"],
                    finalize_payload,
                    parse_meeting_status,
                    lambda value, rid=finalize_request, mid=recording_id: value["request_id"] == rid
                    and value["state"] == 2
                    and value["meeting_id"] == mid,
                    args.notify_timeout,
                )
                listing = await read_and_parse(
                    client, uuids["recording_list"], parse_recording_list
                )
                entries = list(listing.get("entries", []))
                snapshots.append(
                    {
                        "index": index + 1,
                        "recordingId": recording_id,
                        "start": start,
                        "stop": stop,
                        "finalize": finalize,
                        "catalogIds": [int(item["recording_id"]) for item in entries],
                        "entries": entries,
                    }
                )

            final_entries = snapshots[-1]["entries"]
            final_ids = [int(item["recording_id"]) for item in final_entries]
            expected_ids = created_ids[-7:]
            checks = {
                "startedEmpty": len(before_ids) == 0,
                "createdEightUnique": len(created_ids) == args.count
                and len(set(created_ids)) == args.count,
                "monotonicIds": all(b > a for a, b in zip(created_ids, created_ids[1:])),
                "catalogBoundedAtSeven": len(final_ids) == 7,
                "oldestEvicted": created_ids[0] not in final_ids,
                "newestRetained": created_ids[-1] in final_ids,
                "exactLastSeven": set(final_ids) == set(expected_ids),
                "allCodec3Payloads": all(
                    int(item["codec"]) == 3
                    and int(item["total_length"]) > 0
                    and int(item["duration_ms"]) > 0
                    for item in final_entries
                ),
                "noStorageFull": len(snapshots) == args.count,
            }
            if not all(checks.values()):
                raise RuntimeError(f"ring checks failed: {checks}")

            reboot["catalogBefore"] = final_ids
            reboot["attempted"] = True
            await client.disconnect()
            reset = await asyncio.to_thread(reset_board, resolve_programmer(args.programmer))
            reboot["reset"] = reset
            if reset["exitCode"] != 0:
                raise RuntimeError(f"ring reboot reset failed: {reset}")
            await asyncio.sleep(args.reboot_settle_seconds)
            reboot_device, reboot_scan = await scan_for_companion(scan_args, set())
            reboot["scan"] = reboot_scan
            async with BleakClient(reboot_device, **client_kwargs) as reboot_client:
                after_reboot = await read_and_parse(
                    reboot_client, uuids["recording_list"], parse_recording_list
                )
            reboot_ids = [
                int(item["recording_id"])
                for item in after_reboot.get("entries", [])
            ]
            reboot["catalogAfter"] = reboot_ids
            reboot["catalogInvariant"] = reboot_ids == final_ids
            checks["rebootCatalogInvariant"] = reboot["catalogInvariant"]
            if not reboot["catalogInvariant"]:
                raise RuntimeError(
                    f"ring catalog changed across reboot: before={final_ids} after={reboot_ids}"
                )
        except Exception as exc:
            test_error = repr(exc)
        finally:
            # Starting state was proven empty.  Only erase if every current ID
            # belongs to this run; this makes cleanup fail closed if ownership
            # changes unexpectedly while the test is running.
            cleanup_client = client
            cleanup_owned_client = False
            try:
                if not client.is_connected:
                    cleanup_device, cleanup_scan = await scan_for_companion(
                        scan_args, set()
                    )
                    cleanup["scan"] = cleanup_scan
                    cleanup_client = BleakClient(cleanup_device, **client_kwargs)
                    await cleanup_client.connect()
                    cleanup_owned_client = True
                current = await read_and_parse(
                    cleanup_client, uuids["recording_list"], parse_recording_list
                )
                current_ids = [
                    int(item["recording_id"])
                    for item in current.get("entries", [])
                ]
                cleanup["catalogBefore"] = current_ids
                cleanup["ownedByRun"] = set(current_ids).issubset(set(created_ids))
                if current_ids and cleanup["ownedByRun"]:
                    cleanup["attempted"] = True
                    delete_request = 0x6FFF_FF00 | (int(time.time()) & 0xFF)
                    delete_payload = struct.pack(
                        "<BBHIII32s",
                        SCHEMA_VERSION,
                        2,
                        0,
                        delete_request,
                        0,
                        0,
                        bytes(32),
                    )
                    response = await notify_write_wait(
                        cleanup_client,
                        uuids["delete_privacy"],
                        uuids["delete_privacy"],
                        delete_payload,
                        parse_delete_privacy,
                        lambda value: value["request_id"] == delete_request,
                        90.0,
                    )
                    cleanup["response"] = response
                    cleanup["accepted"] = (int(response["flags"]) & 1) == 0
                deadline = time.monotonic() + 120.0
                after_ids = current_ids
                while after_ids and time.monotonic() < deadline:
                    await asyncio.sleep(1.0)
                    after_cleanup = await read_and_parse(
                        cleanup_client,
                        uuids["recording_list"],
                        parse_recording_list,
                    )
                    after_ids = [
                        int(item["recording_id"])
                        for item in after_cleanup.get("entries", [])
                    ]
                cleanup["catalogAfter"] = after_ids
                cleanup["emptyAfter"] = len(cleanup["catalogAfter"]) == 0
            except Exception as exc:
                cleanup["error"] = repr(exc)
            finally:
                if cleanup_owned_client:
                    await cleanup_client.disconnect()

    passed = test_error is None and all(checks.values()) and cleanup["emptyAfter"]
    return {
        "schema": "companion_v1.real_ring_full.v1",
        "result": "PASS real WB55 ring full/evict/cleanup" if passed else "FAIL real WB55 ring full/evict/cleanup",
        "generatedAt": utc_now(),
        "startedAt": started_at,
        "elapsedSeconds": round(time.monotonic() - started_monotonic, 3),
        "noAudioPlayback": True,
        "target": {"address": getattr(device, "address", None), "name": getattr(device, "name", None)},
        "scan": scan,
        "createdIds": created_ids,
        "checks": checks,
        "snapshots": snapshots,
        "reboot": reboot,
        "cleanup": cleanup,
        "error": test_error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="companion")
    parser.add_argument("--address", default=None)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--notify-timeout", type=float, default=8.0)
    parser.add_argument("--programmer", default="")
    parser.add_argument("--reboot-settle-seconds", type=float, default=10.0)
    parser.add_argument(
        "--cleanup-owned-ids",
        default="",
        help="Comma-separated exact current catalog IDs; delete-all is refused unless they match",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.count < 8:
        parser.error("--count must be at least 8 to exceed the seven-entry catalog")
    result: dict[str, Any]
    try:
        result = asyncio.run(run(args))
    except Exception as exc:
        result = {
            "schema": "companion_v1.real_ring_full.v1",
            "result": "FAIL real WB55 ring full/evict/cleanup",
            "generatedAt": utc_now(),
            "noAudioPlayback": True,
            "error": repr(exc),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if str(result.get("result", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
