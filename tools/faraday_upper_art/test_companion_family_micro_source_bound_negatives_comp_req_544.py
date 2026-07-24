#!/usr/bin/env python3
"""Small fail-closed tamper matrix for the COMP-REQ-544 evidence binding."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-browser-family-micro-choreography-comp-req-544"


def digest(path: Path) -> str:
    value = path.read_bytes()
    if path.suffix in {".json", ".html", ".mjs", ".py", ".ps1"}:
        value = value.decode().replace("\r\n", "\n").encode()
    return hashlib.sha256(value).hexdigest().upper()


def gate(machine: dict, packet: dict, page_sha: str, blink: dict) -> bool:
    return (
        machine.get("status") == "MACHINE_READY"
        and machine.get("owner_gate") == "PENDING"
        and packet.get("status") == "READY_DEFAULT_OFF"
        and packet.get("execute_authorized") is False
        and packet.get("candidate_sha256") == page_sha
        and blink.get("status") == "PASS"
        and blink.get("checks", {}).get("sparse_interval_ge_8000") is True
    )


def main() -> int:
    machine = json.loads((VALIDATION / "MACHINE_READY.json").read_text())
    packet = json.loads((VALIDATION / "owner-review-packet.json").read_text())
    blink = json.loads((VALIDATION / "blink-cadence-result.json").read_text())
    page = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
    page_sha = digest(page)
    assert gate(machine, packet, page_sha, blink)
    mutations = {}
    for name, mutate in {
        "machine_status": lambda m, p, b: m.__setitem__("status", "NO_GO"),
        "packet_execute": lambda m, p, b: p.__setitem__("execute_authorized", True),
        "packet_page_hash": lambda m, p, b: p.__setitem__("candidate_sha256", "0" * 64),
        "blink_interval": lambda m, p, b: b["checks"].__setitem__("sparse_interval_ge_8000", False),
    }.items():
        m, p, b = copy.deepcopy(machine), copy.deepcopy(packet), copy.deepcopy(blink)
        mutate(m, p, b)
        mutations[name] = not gate(m, p, page_sha, b)
    result = {"schema": "companion.family-micro-negatives.comp-req-544.v1", "status": "PASS" if all(mutations.values()) else "NO_GO", "cases": mutations}
    payload = json.dumps(result, indent=2, sort_keys=True).encode() + b"\n"
    output = VALIDATION / "source-bound-negatives.json"
    output.write_bytes(payload)
    print(json.dumps({"status": result["status"], "cases": len(mutations), "sha256": hashlib.sha256(payload).hexdigest().upper()}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
