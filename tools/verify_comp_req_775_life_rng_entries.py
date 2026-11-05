#!/usr/bin/env python3
"""Verify hardware-random authored life entrances from physical WB55 logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re


LIFE = re.compile(
    r"^\[screen-life\] family=(?P<family>\w+) action=(?P<action>\w+) "
    r"episode=(?P<episode>\d+) phrase=(?P<phrase>\d+) "
    r"phase=(?P<phase>\w+) variation=(?P<variation>\d+) "
    r"dwell_commits=(?P<dwell>\d+) clip=(?P<clip>\S+) "
    r"frame_index=(?P<frame>\d+)$"
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", type=pathlib.Path)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--bin", required=True, dest="binary", type=pathlib.Path)
    parser.add_argument("--expected-bin-sha256", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    life_states = [state for state in manifest["states"] if state.get("kind") == "life"]
    failures: list[str] = []
    entries: list[dict[str, object]] = []

    for log in args.logs:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        enter = next((i for i, line in enumerate(lines)
                      if line.startswith("[screen-life] enter family=")), -1)
        match = None
        if enter >= 0:
            match = next((LIFE.match(line) for line in lines[enter + 1:]
                          if LIFE.match(line)), None)
        if match is None:
            failures.append(f"{log}: no authored life beat after daily entry")
            continue
        row = match.groupdict()
        episode = int(row["episode"])
        phrase = int(row["phrase"])
        variation = int(row["variation"])
        dwell = int(row["dwell"])
        candidates = [
            state for state in life_states
            if state.get("family") == row["family"]
            and state.get("life_action") == row["action"]
            and int(state.get("action_episode", -1)) == episode
            and int(state.get("phrase", -1)) == phrase
            and state.get("phase") == row["phase"]
            and int(state.get("variation", -1)) == variation
            and int(state.get("dwell_commits", -1)) == dwell
        ]
        bad_tokens = [
            token for token in ("browser_state_override", "HardFault", "MemManage",
                                "BusFault", "UsageFault", "healthy=0")
            if any(token in line for line in lines)
        ]
        if len(candidates) != 1:
            failures.append(f"{log}: entry tuple maps to {len(candidates)} manifest states")
        if not 0 <= episode < 8:
            failures.append(f"{log}: entry episode {episode} outside authored RNG range 0..7")
        if not 1 <= dwell <= 4:
            failures.append(f"{log}: dwell {dwell} outside 1..4")
        if bad_tokens:
            failures.append(f"{log}: fault/fallback tokens {bad_tokens}")
        entries.append({
            "log": str(log.resolve()),
            "episode": episode,
            "family": row["family"],
            "action": row["action"],
            "phrase": phrase,
            "phase": row["phase"],
            "variation": variation,
            "dwell_commits": dwell,
            "runtime_clip": row["clip"],
            "runtime_frame_index": int(row["frame"]),
            "manifest_matches": len(candidates),
            "fault_tokens": bad_tokens,
        })

    distinct = sorted({int(entry["episode"]) for entry in entries})
    binary_sha = sha256(args.binary)
    checks = {
        "three_physical_reset_logs": len(args.logs) >= 3 and len(entries) == len(args.logs),
        "every_entry_is_source_pack_authored": len(entries) == len(args.logs)
        and all(entry["manifest_matches"] == 1 for entry in entries),
        "hardware_entries_are_not_fixed": len(distinct) >= 2,
        "entry_episode_is_bounded_zero_to_seven": len(entries) == len(args.logs)
        and all(0 <= int(entry["episode"]) < 8 for entry in entries),
        "dwell_is_one_to_four": len(entries) == len(args.logs)
        and all(1 <= int(entry["dwell_commits"]) <= 4 for entry in entries),
        "no_fallback_or_fault_tokens": len(entries) == len(args.logs)
        and all(not entry["fault_tokens"] for entry in entries),
        "binary_identity_matches": binary_sha == args.expected_bin_sha256.upper(),
    }
    ready = not failures and all(checks.values())
    receipt = {
        "schema": "companion.comp_req_775.life_rng_physical.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "failures": failures,
        "distinct_entry_episodes": distinct,
        "entries": entries,
        "identity": {
            "binary": str(args.binary.resolve()),
            "binary_sha256": binary_sha,
            "expected_binary_sha256": args.expected_bin_sha256.upper(),
            "manifest": str(args.manifest.resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
